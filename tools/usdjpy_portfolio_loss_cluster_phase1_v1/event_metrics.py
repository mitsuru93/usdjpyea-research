from .base import *

def event_equity_stats(events: pd.DataFrame, d: pd.DataFrame, states: pd.DataFrame) -> pd.DataFrame:
    event_for_trade = d.set_index("trade_id").portfolio_event_id
    s = states[["trade_id", "observation_utc", "executable_pips"]].copy()
    s["portfolio_event_id"] = s.trade_id.map(event_for_trade)
    close_map = d.set_index("trade_id").close_utc
    pnl_map = d.set_index("trade_id").realized_pl_jpy
    rows = []
    for eid, g in s.groupby("portfolio_event_id"):
        tids = g.trade_id.unique().tolist()
        times = pd.DatetimeIndex(sorted(g.observation_utc.unique()))
        vals = []
        for ts in times:
            open_marks = g[(g.observation_utc.eq(ts)) & (g.trade_id.map(close_map).gt(ts))].executable_pips.sum() * 10.0
            realized = sum(float(pnl_map[tid]) for tid in tids if close_map[tid] <= ts)
            vals.append(float(realized + open_marks))
        arr = np.asarray(vals, dtype=float)
        peaks = np.maximum.accumulate(np.r_[0.0, arr])[1:]
        dd = peaks - arr
        min_i = int(np.argmin(arr)) if len(arr) else 0
        rec = None
        if len(arr):
            target = peaks[min_i]
            after = np.flatnonzero(arr[min_i:] >= target - 1e-9)
            if len(after):
                rec = float((times[min_i + int(after[0])] - times[min_i]).total_seconds() / 60.0)
        rows.append({
            "portfolio_event_id": int(eid),
            "maximum_adverse_portfolio_excursion_jpy": float(-arr.min()) if len(arr) and arr.min() < 0 else 0.0,
            "maximum_event_drawdown_jpy": float(dd.max()) if len(dd) else 0.0,
            "recovery_time_min": rec,
        })
    return events.merge(pd.DataFrame(rows), on="portfolio_event_id", how="left", validate="one_to_one")

