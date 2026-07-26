from .candidate_rules import *

def event_bootstrap(d: pd.DataFrame, weights: pd.Series, n: int = 2000) -> dict[str, Any]:
    x = d.copy()
    x["weight"] = x.trade_id.map(weights).fillna(0.0)
    x["delta"] = x.realized_pl_jpy * (x.weight - 1.0)
    ev = x.groupby(["fold", "portfolio_event_id"], as_index=False).delta.sum()
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(n):
        total = 0.0
        for fold in FOLDS:
            a = ev.loc[ev.fold.eq(fold), "delta"].to_numpy()
            total += float(rng.choice(a, len(a), replace=True).sum()) if len(a) else 0.0
        vals.append(total)
    return {
        "replicates": n, "observed_net_improvement_jpy": float(ev.delta.sum()),
        "ci95_jpy": [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))],
        "probability_nonpositive": float(np.mean(np.asarray(vals) <= 0)),
        "resampling_unit": "portfolio_event_stratified_by_fold",
    }


def permutation_cluster_test(d: pd.DataFrame, entry: pd.DataFrame, n: int = 2000) -> dict[str, Any]:
    z = d[["trade_id", "fold", "strategy", "side_label", "winner"]].merge(entry[["trade_id", "standalone_60m"]], on="trade_id", validate="one_to_one")
    z["loss"] = (~z.winner).astype(float)
    obs = float(z.loc[~z.standalone_60m, "loss"].mean() - z.loc[z.standalone_60m, "loss"].mean())
    rng = np.random.default_rng(SEED)
    vals = []
    strata = list(z.groupby(["fold", "strategy", "side_label"]).groups.values())
    for _ in range(n):
        y = z.loss.to_numpy().copy()
        for idx in strata:
            ii = np.asarray(list(idx), dtype=int)
            y[ii] = rng.permutation(y[ii])
        vals.append(float(y[~z.standalone_60m.to_numpy()].mean() - y[z.standalone_60m.to_numpy()].mean()))
    arr = np.asarray(vals)
    return {"observed_cluster_minus_standalone_loss_rate": obs, "permutations": n, "two_sided_p": float((np.abs(arr) >= abs(obs)).mean()), "strata": ["fold", "strategy", "side"]}


def baseline_recovery_episodes(d: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    x = d.copy(); x["weight"] = x.trade_id.map(weights).fillna(0.0); x = x[x.weight.gt(0)].sort_values(["close_utc", "trade_id"])
    x["pnl"] = x.realized_pl_jpy * x.weight
    balance = 0.0; peak = 0.0; start = None; trough = 0.0; rows = []; eid = 0
    for r in x.itertuples(index=False):
        balance += float(r.pnl); peak = max(peak, balance)
        dd = peak - balance
        if dd > 0 and start is None:
            start = r.close_utc; trough = dd
        elif start is not None:
            trough = max(trough, dd)
        if start is not None and dd <= 1e-9:
            rows.append({"drawdown_episode_id": eid, "start_utc": iso(start), "recovery_utc": iso(r.close_utc), "maximum_drawdown_jpy": trough, "recovery_time_min": (r.close_utc - start).total_seconds()/60.0, "censored": False})
            eid += 1; start = None; trough = 0.0
    if start is not None:
        rows.append({"drawdown_episode_id": eid, "start_utc": iso(start), "recovery_utc": None, "maximum_drawdown_jpy": trough, "recovery_time_min": None, "censored": True})
    return pd.DataFrame(rows)


def family_lofo(d: pd.DataFrame, states: pd.DataFrame, candidates: list[Candidate], candidate_results: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    by_family: dict[str, list[Candidate]] = {}
    for c in candidates: by_family.setdefault(c.family, []).append(c)
    for family, specs in by_family.items():
        for held in FOLDS:
            train = set(FOLDS) - {held}
            ranked = []
            for c in specs:
                w, _ = replay_candidate(d, c, train)
                tm = realized_metrics(d[d.fold.isin(train)], w)
                basew = pd.Series(1.0, index=d.trade_id)
                bm = realized_metrics(d[d.fold.isin(train)], basew)
                gp_base = float(d[d.fold.isin(train) & d.winner].realized_pl_jpy.sum())
                gp_cand = float((d[d.fold.isin(train) & d.winner].realized_pl_jpy * d[d.fold.isin(train) & d.winner].trade_id.map(w).fillna(0)).sum())
                retention = gp_cand / gp_base if gp_base else 1.0
                dd_red = float(bm["maximum_realized_drawdown_jpy"] - tm["maximum_realized_drawdown_jpy"])
                net_delta = float(tm["net_profit_jpy"] - bm["net_profit_jpy"])
                eligible = retention >= 0.90 and dd_red > 0
                ranked.append((eligible, dd_red, net_delta, retention, -c.simplicity, c.candidate_id, c))
            ranked.sort(reverse=True, key=lambda z: z[:-1])
            chosen = ranked[0][-1]
            wh, _ = replay_candidate(d, chosen, {held})
            gh = d[d.fold.eq(held)]
            hm = realized_metrics(gh, wh)
            hb = realized_metrics(gh, pd.Series(1.0, index=d.trade_id))
            rows.append({"family": family, "held_out_fold": held, "selected_candidate": chosen.candidate_id, "held_out_net_improvement_jpy": float(hm["net_profit_jpy"] - hb["net_profit_jpy"]), "held_out_realized_dd_reduction_jpy": float(hb["maximum_realized_drawdown_jpy"] - hm["maximum_realized_drawdown_jpy"]), "held_out_winner_retention": candidate_results[chosen.candidate_id]["winner_retention_by_fold"].get(held), "train_selection_rule": "winner_retention>=0.90 then max realized DD reduction, net improvement, simplicity"})
    return pd.DataFrame(rows)


def group_report(entry: pd.DataFrame, d: pd.DataFrame, flag: str) -> pd.DataFrame:
    x = d.merge(entry[["trade_id", flag]], on="trade_id", validate="one_to_one")
    total_loss = float(-x.loc[~x.winner, "realized_pl_jpy"].sum())
    rows = []
    for val, g in x.groupby(flag, dropna=False):
        gp = float(g.loc[g.realized_pl_jpy > 0, "realized_pl_jpy"].sum()); gl = float(-g.loc[g.realized_pl_jpy < 0, "realized_pl_jpy"].sum())
        rows.append({flag: val, "trade_count": int(len(g)), "winner_count": int(g.winner.sum()), "loser_count": int((~g.winner).sum()), "gross_profit_jpy": gp, "gross_loss_jpy": gl, "net_profit_jpy": float(g.realized_pl_jpy.sum()), "profit_factor": None if gl == 0 else gp/gl, "win_rate": float(g.winner.mean()), "average_pnl_jpy": float(g.realized_pl_jpy.mean()), "median_pnl_jpy": float(g.realized_pl_jpy.median()), "total_loss_coverage": gl/total_loss if total_loss else 0.0})
    return pd.DataFrame(rows)

