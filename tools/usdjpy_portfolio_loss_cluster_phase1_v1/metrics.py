from .base import *

def realized_metrics(d: pd.DataFrame, weights: pd.Series) -> dict[str, float | int | None]:
    x = d[["trade_id", "close_utc", "realized_pl_jpy", "winner"]].copy()
    x["weight"] = x.trade_id.map(weights).fillna(0.0)
    x["candidate_pl"] = x.realized_pl_jpy * x.weight
    x = x[x.weight.gt(0)].sort_values(["close_utc", "trade_id"])
    cum = x.candidate_pl.cumsum()
    peak = cum.cummax().clip(lower=0)
    dd = peak - cum
    gp = float(x.loc[x.candidate_pl > 0, "candidate_pl"].sum())
    gl = float(-x.loc[x.candidate_pl < 0, "candidate_pl"].sum())
    return {
        "trade_count": int(x.weight.eq(1).sum()),
        "partial_trade_count": int(x.weight.between(0, 1, inclusive="neither").sum()),
        "exposure_equivalent_trade_count": float(x.weight.sum()),
        "gross_profit_jpy": gp, "gross_loss_jpy": gl, "net_profit_jpy": float(x.candidate_pl.sum()),
        "profit_factor": None if gl == 0 else gp / gl,
        "win_rate": float((x.candidate_pl > 0).mean()) if len(x) else None,
        "average_pnl_jpy": float(x.candidate_pl.mean()) if len(x) else None,
        "median_pnl_jpy": float(x.candidate_pl.median()) if len(x) else None,
        "maximum_realized_drawdown_jpy": float(dd.max()) if len(dd) else 0.0,
    }


def snapshot_dd(d: pd.DataFrame, states: pd.DataFrame, weights: pd.Series) -> tuple[float, pd.DataFrame]:
    w = weights[weights.gt(0)]
    if w.empty:
        return 0.0, pd.DataFrame(columns=["utc", "equity_delta_jpy", "drawdown_jpy"])
    dm = d.set_index("trade_id")
    s = states[states.trade_id.isin(w.index)].copy()
    s["weight"] = s.trade_id.map(w)
    s["close_utc"] = s.trade_id.map(dm.close_utc)
    s = s[s.observation_utc.lt(s.close_utc)]
    unrealized = (s.executable_pips * 10.0 * s.weight).groupby(s.observation_utc).sum()
    exits = d[d.trade_id.isin(w.index)].copy()
    exits["candidate_pl"] = exits.realized_pl_jpy * exits.trade_id.map(w)
    exit_by_ts = exits.groupby("close_utc").candidate_pl.sum().sort_index()
    times = pd.DatetimeIndex(sorted(set(unrealized.index).union(exit_by_ts.index)))
    realized = exit_by_ts.reindex(times, fill_value=0.0).cumsum()
    u = unrealized.reindex(times, fill_value=0.0)
    eq = realized + u
    peak = eq.cummax().clip(lower=0)
    dd = peak - eq
    curve = pd.DataFrame({"utc": times, "equity_delta_jpy": eq.to_numpy(), "drawdown_jpy": dd.to_numpy()})
    return float(dd.max()) if len(dd) else 0.0, curve

