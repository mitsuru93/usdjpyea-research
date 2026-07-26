from .base import *

def primary_portfolio_events(d: pd.DataFrame, gap_min: int = 60) -> tuple[pd.DataFrame, pd.Series]:
    x = d.sort_values(["entry_utc", "strategy", "trade_id"], kind="mergesort").reset_index(drop=True)
    event_ids = np.full(len(x), -1, dtype=int)
    events: list[list[int]] = []
    current: list[int] = []
    current_end: pd.Timestamp | None = None
    for i, r in x.iterrows():
        if current_end is None or r.entry_utc <= current_end + pd.Timedelta(minutes=gap_min):
            current.append(i)
            current_end = r.close_utc if current_end is None else max(current_end, r.close_utc)
        else:
            events.append(current)
            current = [i]
            current_end = r.close_utc
    if current:
        events.append(current)
    rows = []
    for eid, ids in enumerate(events):
        event_ids[ids] = eid
        g = x.loc[ids]
        rows.append({
            "portfolio_event_id": eid,
            "start_utc": iso(g.entry_utc.min()),
            "end_utc": iso(g.close_utc.max()),
            "trade_count": int(len(g)),
            "B02_count": int(g.strategy.eq("B02").sum()),
            "F05_count": int(g.strategy.eq("F05").sum()),
            "long_count": int(g.side.gt(0).sum()),
            "short_count": int(g.side.lt(0).sum()),
            "strategies": "+".join(sorted(g.strategy.unique())),
            "same_direction": bool(g.side.nunique() == 1),
            "gross_profit_jpy": float(g.loc[g.realized_pl_jpy > 0, "realized_pl_jpy"].sum()),
            "gross_loss_jpy": float(-g.loc[g.realized_pl_jpy < 0, "realized_pl_jpy"].sum()),
            "net_profit_jpy": float(g.realized_pl_jpy.sum()),
            "winner_count": int(g.winner.sum()),
            "loser_count": int((~g.winner).sum()),
            "loss_cluster": bool((~g.winner).sum() >= 2),
            "entry_span_min": float((g.entry_utc.max() - g.entry_utc.min()).total_seconds() / 60.0),
            "fold": "+".join(sorted(g.fold.unique())),
            "months": "+".join(sorted(g.month.unique())),
        })
    mapping = pd.Series(event_ids, index=x.trade_id, name="portfolio_event_id")
    return pd.DataFrame(rows), mapping


def loss_clusters(d: pd.DataFrame, gap_min: int = 60) -> pd.DataFrame:
    losses = d[~d.winner].sort_values(["close_utc", "trade_id"]).copy()
    cid = -1
    prev: pd.Timestamp | None = None
    ids = []
    for r in losses.itertuples(index=False):
        if prev is None or (r.close_utc - prev).total_seconds() / 60.0 > gap_min:
            cid += 1
        ids.append(cid)
        prev = r.close_utc
    losses["loss_cluster_id"] = ids
    sizes = losses.groupby("loss_cluster_id").size().rename("loss_cluster_size")
    losses = losses.join(sizes, on="loss_cluster_id")
    losses["loss_clustered"] = losses.loss_cluster_size.ge(2)
    return losses[["trade_id", "loss_cluster_id", "loss_cluster_size", "loss_clustered"]]


def state_lookup(states: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    idx = pd.MultiIndex.from_frame(states[["trade_id", "observation_utc"]])
    return (
        pd.Series(states.executable_pips.to_numpy(), index=idx),
        pd.Series(states.running_min_pips.to_numpy(), index=idx),
        pd.Series(states.running_max_pips.to_numpy(), index=idx),
    )

