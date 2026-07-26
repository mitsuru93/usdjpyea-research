from .base import *
from .events import *

def build_entry_ledger(d: pd.DataFrame, states: pd.DataFrame, market_entries: pd.DataFrame, event_map: pd.Series, loss_map: pd.DataFrame) -> pd.DataFrame:
    mark, runmin, runmax = state_lookup(states)
    x = d.merge(market_entries[["trade_id", "abs_open_move_pips", "volatility_state", "shock_elapsed_min", "shock"]], on="trade_id", how="left", validate="one_to_one")
    x = x.merge(loss_map, on="trade_id", how="left", validate="one_to_one")
    x["portfolio_event_id"] = x.trade_id.map(event_map)
    x = x.sort_values(["entry_utc", "strategy", "trade_id"], kind="mergesort").reset_index(drop=True)
    exits = x.sort_values(["close_utc", "strategy", "trade_id"], kind="mergesort")
    exit_rows = list(exits.itertuples(index=False))
    exit_i = 0
    open_pos: dict[str, Any] = {}
    realized = 0.0
    realized_peak = 0.0
    loss_streak = 0
    prev_loss_time: pd.Timestamp | None = None
    prev_entry_time: pd.Timestamp | None = None
    session_entries: dict[str, int] = {}
    session_losses: dict[str, int] = {}
    rows = []

    for r in x.itertuples(index=False):
        ts = r.entry_utc
        while exit_i < len(exit_rows) and exit_rows[exit_i].close_utc <= ts:
            z = exit_rows[exit_i]
            if z.trade_id in open_pos:
                realized += float(z.realized_pl_jpy)
                realized_peak = max(realized_peak, realized)
                if float(z.realized_pl_jpy) < 0:
                    loss_streak += 1
                    prev_loss_time = z.close_utc
                    session_losses[z.exit_session_key] = session_losses.get(z.exit_session_key, 0) + 1
                else:
                    loss_streak = 0
                del open_pos[z.trade_id]
            exit_i += 1
        opens = list(open_pos.values())
        same = [p for p in opens if int(p.side) == int(r.side)]
        opp = [p for p in opens if int(p.side) != int(r.side)]
        b02 = [p for p in opens if p.strategy == "B02"]
        f05 = [p for p in opens if p.strategy == "F05"]
        marks = []
        recovering = 0
        ages = []
        prices = [float(r.entry_bid)]
        for p in opens:
            key = (p.trade_id, ts)
            cur = float(mark.get(key, np.nan))
            mn = float(runmin.get(key, np.nan))
            if not np.isnan(cur):
                marks.append(cur * 10.0)
                if cur <= 0 and cur - mn >= 5.0:
                    recovering += 1
            ages.append((ts - p.entry_utc).total_seconds() / 60.0)
            prices.append(float(p.entry_bid))
        unrealized = float(np.nansum(marks))
        snapshot_equity_delta = realized + unrealized
        skey = r.entry_session_key
        same_session_count = session_entries.get(skey, 0)
        row = {
            "trade_id": r.trade_id, "fold": r.fold, "strategy": r.strategy,
            "entry_utc": iso(ts), "close_utc": iso(r.close_utc), "side": int(r.side),
            "lot": 0.01, "normalized_exposure": 1.0, "entry_price": float(r.entry_bid),
            "realized_pl_jpy": float(r.realized_pl_jpy), "mfe_pips": float(r.mfe_pips), "mae_pips": float(r.mae_pips),
            "session": r.session, "month": r.month, "winner": bool(r.winner),
            "portfolio_event_id": int(r.portfolio_event_id),
            "loss_cluster_id": None if pd.isna(r.loss_cluster_id) else int(r.loss_cluster_id),
            "loss_cluster_size": 0 if pd.isna(r.loss_cluster_size) else int(r.loss_cluster_size),
            "open_position_count": len(opens), "B02_position_count": len(b02), "F05_position_count": len(f05),
            "gross_exposure": float(len(opens)), "net_directional_exposure": float(sum(int(p.side) for p in opens)),
            "long_exposure": float(sum(int(p.side) > 0 for p in opens)), "short_exposure": float(sum(int(p.side) < 0 for p in opens)),
            "same_direction_entry_count": len(same), "opposite_direction_entry_count": len(opp),
            "cross_strategy_open": bool(any(p.strategy != r.strategy for p in opens)),
            "strategy_concentration": 0.0 if not opens else max(len(b02), len(f05)) / len(opens),
            "entry_price_dispersion_pips": float((max(prices) - min(prices)) / PIP),
            "average_entry_age_min": float(np.mean(ages)) if ages else 0.0,
            "maximum_entry_age_min": float(max(ages)) if ages else 0.0,
            "unrealized_pnl_jpy": unrealized, "realized_pnl_jpy": realized,
            "portfolio_realized_drawdown_jpy": float(realized_peak - realized),
            "portfolio_snapshot_equity_delta_jpy": snapshot_equity_delta,
            "current_loss_streak": int(loss_streak),
            "time_since_previous_entry_min": None if prev_entry_time is None else float((ts - prev_entry_time).total_seconds() / 60.0),
            "time_since_previous_loss_min": None if prev_loss_time is None else float((ts - prev_loss_time).total_seconds() / 60.0),
            "same_session_entry_count": int(same_session_count),
            "same_session_prior_loss_count": int(session_losses.get(skey, 0)),
            "recovery_interference": bool(recovering > 0), "recovering_open_position_count": int(recovering),
            "volatility_state": r.volatility_state if isinstance(r.volatility_state, str) else "unknown",
            "shock_elapsed_min": None if pd.isna(r.shock_elapsed_min) else float(r.shock_elapsed_min),
            "shock": bool(r.shock) if not pd.isna(r.shock) else False,
        }
        rows.append(row)
        open_pos[r.trade_id] = r
        session_entries[skey] = same_session_count + 1
        prev_entry_time = ts
    out = pd.DataFrame(rows)
    for w in [1, 5, 15, 30, 60]:
        prev_gap = pd.to_numeric(out.time_since_previous_entry_min, errors="coerce")
        next_gap = pd.to_datetime(out.entry_utc, utc=True).shift(-1) - pd.to_datetime(out.entry_utc, utc=True)
        out[f"entry_cluster_{w}m"] = prev_gap.le(w) | next_gap.dt.total_seconds().div(60).le(w)
    out["standalone_60m"] = out.open_position_count.eq(0) & ~out.entry_cluster_60m
    out["concurrent_exposure"] = out.open_position_count.gt(0)
    out["same_direction_overlap"] = out.same_direction_entry_count.gt(0)
    out["opposite_direction_overlap"] = out.opposite_direction_entry_count.gt(0)
    out["B02_F05_overlap"] = out.cross_strategy_open
    out["drawdown_add"] = out.portfolio_realized_drawdown_jpy.gt(0)
    out["drawdown_band"] = pd.cut(out.portfolio_realized_drawdown_jpy, [-1, 0, 500, 1500, 3000, np.inf], labels=["equity_peak", "minor", "moderate", "deep", "extreme"])
    return out


def add_session_loss_chains(d: pd.DataFrame) -> pd.DataFrame:
    x = d.sort_values(["close_utc", "trade_id"], kind="mergesort").copy()
    chain_id = -1
    pos = 0
    prev_key = None
    rows = []
    for r in x.itertuples(index=False):
        key = r.exit_session_key
        if key != prev_key or bool(r.winner):
            pos = 0
        if not bool(r.winner):
            if pos == 0:
                chain_id += 1
            pos += 1
            rows.append({"trade_id": r.trade_id, "session_loss_chain_id": chain_id, "session_loss_chain_position": pos})
        else:
            rows.append({"trade_id": r.trade_id, "session_loss_chain_id": None, "session_loss_chain_position": 0})
        prev_key = key
    out = pd.DataFrame(rows)
    sizes = out.dropna(subset=["session_loss_chain_id"]).groupby("session_loss_chain_id").size().rename("session_loss_chain_size")
    return out.join(sizes, on="session_loss_chain_id").fillna({"session_loss_chain_size": 0})

