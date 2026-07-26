from .base import *
from .events import *
from .exposure import *
from .event_metrics import *
from .metrics import *

@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    family: str
    rule: str
    value: float | int | str | None
    simplicity: int


def candidate_set() -> list[Candidate]:
    out: list[Candidate] = []
    out += [Candidate(f"MAX_CONCURRENT_{n}", "concurrent_position_cap", "max_concurrent", n, 1) for n in [1, 2, 3]]
    out += [Candidate(f"SAME_DIRECTION_CAP_{n}", "same_direction_exposure_cap", "same_direction_cap", n, 1) for n in [1, 2, 3]]
    out += [Candidate("B02_F05_EXCLUSIVE", "B02_F05_exclusivity", "cross_strategy_exclusive", None, 1)]
    out += [Candidate("B02_PRIORITY_SIMULTANEOUS", "strategy_priority_routing", "simultaneous_priority", "B02", 2), Candidate("F05_PRIORITY_SIMULTANEOUS", "strategy_priority_routing", "simultaneous_priority", "F05", 2)]
    out += [Candidate(f"ENTRY_COOLDOWN_{n}M", "entry_cooldown", "entry_cooldown", n, 1) for n in [5, 15, 30, 60]]
    out += [Candidate(f"LOSS_COOLDOWN_{n}M", "loss_cooldown", "loss_cooldown", n, 1) for n in [15, 30, 60]]
    out += [Candidate(f"DRAWDOWN_BLOCK_{n}JPY", "drawdown_aware_exposure_reduction", "dd_block", n, 1) for n in [500, 1000, 2000]]
    out += [Candidate(f"SESSION_LOSS_CAP_{n}", "session_loss_cap", "session_loss_cap", n, 1) for n in [2, 3]]
    out += [Candidate("SHOCK_TOTAL_CAP_1", "shock_exposure_cap", "shock_cap", 1, 2), Candidate("SHOCK_COOLDOWN_30M", "shock_exposure_cap", "shock_cooldown", 30, 2), Candidate("SHOCK_COOLDOWN_60M", "shock_exposure_cap", "shock_cooldown", 60, 2)]
    out += [Candidate("HALF_SIZE_WHEN_OPEN", "adaptive_position_sizing", "half_open", None, 2), Candidate("HALF_SIZE_SAME_DIRECTION", "adaptive_position_sizing", "half_same", None, 2), Candidate("HALF_SIZE_DD_1000", "adaptive_position_sizing", "half_dd", 1000, 2)]
    return out


def replay_candidate(d: pd.DataFrame, c: Candidate, fold_filter: set[str] | None = None) -> tuple[pd.Series, pd.DataFrame]:
    x = d[d.fold.isin(fold_filter) if fold_filter else pd.Series(True, index=d.index)].copy()
    x = x.sort_values(["entry_utc", "strategy", "trade_id"], kind="mergesort")
    weights = pd.Series(0.0, index=d.trade_id, dtype=float)
    accepted: dict[str, dict[str, Any]] = {}
    realized = 0.0
    peak = 0.0
    last_entry: pd.Timestamp | None = None
    last_loss: pd.Timestamp | None = None
    session_losses: dict[str, int] = {}
    audit = []

    for ts, group in x.groupby("entry_utc", sort=True):
        closed = sorted([p for p in accepted.values() if p["close_utc"] <= ts], key=lambda p: (p["close_utc"], p["trade_id"]))
        for p in closed:
            pnl = p["pnl"] * p["weight"]
            realized += pnl
            peak = max(peak, realized)
            if pnl < 0:
                last_loss = p["close_utc"]
                session_losses[p["exit_session_key"]] = session_losses.get(p["exit_session_key"], 0) + 1
            del accepted[p["trade_id"]]
        order = group.copy()
        if c.rule == "simultaneous_priority":
            priority = str(c.value)
            order["_priority"] = np.where(order.strategy.eq(priority), 0, 1)
            order = order.sort_values(["_priority", "strategy", "trade_id"])
        simultaneous_strategies = set(group.strategy)
        for r in order.itertuples(index=False):
            opens = list(accepted.values())
            same = [p for p in opens if int(p["side"]) == int(r.side)]
            other_strategy = [p for p in opens if p["strategy"] != r.strategy]
            dd = peak - realized
            allowed = True
            reason = "accepted"
            weight = 1.0
            if c.rule == "max_concurrent" and len(opens) >= int(c.value): allowed, reason = False, "max_concurrent"
            elif c.rule == "same_direction_cap" and len(same) >= int(c.value): allowed, reason = False, "same_direction_cap"
            elif c.rule == "cross_strategy_exclusive" and other_strategy: allowed, reason = False, "cross_strategy_exclusive"
            elif c.rule == "simultaneous_priority" and len(simultaneous_strategies) > 1 and r.strategy != str(c.value): allowed, reason = False, "simultaneous_lower_priority"
            elif c.rule == "entry_cooldown" and last_entry is not None and (ts - last_entry).total_seconds() / 60.0 < float(c.value): allowed, reason = False, "entry_cooldown"
            elif c.rule == "loss_cooldown" and last_loss is not None and (ts - last_loss).total_seconds() / 60.0 < float(c.value): allowed, reason = False, "loss_cooldown"
            elif c.rule == "dd_block" and dd >= float(c.value): allowed, reason = False, "drawdown_block"
            elif c.rule == "session_loss_cap" and session_losses.get(r.entry_session_key, 0) >= int(c.value): allowed, reason = False, "session_loss_cap"
            elif c.rule == "shock_cap" and r.volatility_state in {"shock", "post_shock"} and len(opens) >= int(c.value): allowed, reason = False, "shock_cap"
            elif c.rule == "shock_cooldown" and pd.notna(r.shock_elapsed_min) and float(r.shock_elapsed_min) <= float(c.value): allowed, reason = False, "shock_cooldown"
            if allowed:
                if c.rule == "half_open" and len(opens) > 0: weight = 0.5; reason = "half_size_open"
                elif c.rule == "half_same" and len(same) > 0: weight = 0.5; reason = "half_size_same"
                elif c.rule == "half_dd" and dd >= float(c.value): weight = 0.5; reason = "half_size_dd"
                weights.loc[r.trade_id] = weight
                accepted[r.trade_id] = {"trade_id": r.trade_id, "close_utc": r.close_utc, "pnl": float(r.realized_pl_jpy), "weight": weight, "side": int(r.side), "strategy": r.strategy, "exit_session_key": r.exit_session_key}
                last_entry = ts
            audit.append({"candidate_id": c.candidate_id, "trade_id": r.trade_id, "entry_utc": iso(ts), "accepted_weight": weight if allowed else 0.0, "decision_reason": reason, "open_before": len(opens), "same_direction_before": len(same), "realized_dd_before_jpy": dd})
    return weights, pd.DataFrame(audit)


def metrics_by_slice(d: pd.DataFrame, weights: pd.Series, candidate_id: str) -> pd.DataFrame:
    x = d.copy()
    x["weight"] = x.trade_id.map(weights).fillna(0.0)
    x["candidate_pl_jpy"] = x.realized_pl_jpy * x.weight
    x["delta_jpy"] = x.candidate_pl_jpy - x.realized_pl_jpy
    rows = []
    dims = [
        ("fold", ["fold"]), ("strategy", ["strategy"]), ("side", ["side_label"]), ("session", ["session"]),
        ("fold_strategy", ["fold", "strategy"]), ("fold_side", ["fold", "side_label"]), ("fold_session", ["fold", "session"]), ("month", ["month"]),
    ]
    for label, cols in dims:
        for keys, g in x.groupby(cols, dropna=False):
            if not isinstance(keys, tuple): keys = (keys,)
            vals = {c: k for c, k in zip(cols, keys)}
            base_gp = float(g.loc[g.realized_pl_jpy > 0, "realized_pl_jpy"].sum())
            base_gl = float(-g.loc[g.realized_pl_jpy < 0, "realized_pl_jpy"].sum())
            cand_gp = float(g.loc[g.candidate_pl_jpy > 0, "candidate_pl_jpy"].sum())
            cand_gl = float(-g.loc[g.candidate_pl_jpy < 0, "candidate_pl_jpy"].sum())
            rows.append({
                "candidate_id": candidate_id, "dimension": label, **vals,
                "baseline_trades": int(len(g)), "candidate_exposure_equivalent": float(g.weight.sum()),
                "baseline_net_jpy": float(g.realized_pl_jpy.sum()), "candidate_net_jpy": float(g.candidate_pl_jpy.sum()), "net_improvement_jpy": float(g.delta_jpy.sum()),
                "avoided_gross_loss_jpy": base_gl - cand_gl, "lost_gross_profit_jpy": base_gp - cand_gp,
                "winner_retention": None if base_gp == 0 else cand_gp / base_gp,
                "baseline_pf": None if base_gl == 0 else base_gp / base_gl, "candidate_pf": None if cand_gl == 0 else cand_gp / cand_gl,
            })
    return pd.DataFrame(rows)

