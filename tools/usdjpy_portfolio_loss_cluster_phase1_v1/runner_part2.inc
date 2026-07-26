    lofo = family_lofo(d, s, candidates, candidate_results)
    fam_rows = []
    for family, g in lofo.groupby("family"):
        pooled = cand[cand.family.eq(family)].sort_values(["positive_net_folds", "M15_snapshot_DD_reduction_jpy", "net_improvement_jpy", "winner_retention", "simplicity"], ascending=[False, False, False, False, True]).iloc[0]
        fam_rows.append({
            "family": family, "representative_candidate": pooled.candidate_id,
            "LOFO_positive_net_folds": int((g.held_out_net_improvement_jpy > 0).sum()),
            "LOFO_positive_DD_folds": int((g.held_out_realized_dd_reduction_jpy > 0).sum()),
            "LOFO_net_improvement_jpy": float(g.held_out_net_improvement_jpy.sum()),
            "pooled_net_improvement_jpy": float(pooled.net_improvement_jpy),
            "pooled_realized_DD_reduction_jpy": float(pooled.realized_DD_reduction_jpy),
            "pooled_M15_snapshot_DD_reduction_jpy": float(pooled.M15_snapshot_DD_reduction_jpy),
            "winner_damage_jpy": float(pooled.winner_damage_jpy), "winner_retention": float(pooled.winner_retention),
            "positive_net_folds": int(pooled.positive_net_folds), "top20_winner_loss_jpy": float(pooled.top20_winner_loss_jpy),
            "simplicity": int(pooled.simplicity),
        })
    family_rank = pd.DataFrame(fam_rows).sort_values(["LOFO_positive_net_folds", "LOFO_positive_DD_folds", "LOFO_net_improvement_jpy", "pooled_M15_snapshot_DD_reduction_jpy", "winner_retention", "simplicity"], ascending=[False, False, False, False, False, True]).reset_index(drop=True)
    family_rank.insert(0, "rank", np.arange(1, len(family_rank)+1))
    family_rank["weakness"] = np.select([
        family_rank.winner_retention.lt(0.90), family_rank.LOFO_positive_net_folds.lt(3), family_rank.LOFO_positive_DD_folds.lt(3)
    ], ["winner_damage_high", "net_effect_not_fold_portable", "DD_reduction_not_fold_portable"], default="no_primary_weakness")

    oracle_cluster = d.merge(losses[["trade_id", "loss_clustered"]], on="trade_id", how="left")
    oracle_avoided = float(-oracle_cluster.loc[(~oracle_cluster.winner) & oracle_cluster.loss_clustered.fillna(False), "realized_pl_jpy"].sum())
    oracle = {"name": "PERFECT_LOSS_CLUSTER_AVOIDANCE_ORACLE", "avoided_gross_loss_jpy": oracle_avoided, "lost_gross_profit_jpy": 0.0, "net_improvement_jpy": oracle_avoided, "classification": "ORACLE_UPPER_BOUND_NOT_IMPLEMENTABLE"}

    concurrent = group_report(entry, d, "concurrent_exposure")
    drawdown = group_report(entry, d, "drawdown_band")
    overlap = group_report(entry, d, "B02_F05_overlap")
    session_chain = group_report(entry, d, "session_loss_chain_size")
    shock = group_report(entry, d, "volatility_state")
    loss_atlas = d.merge(losses, on="trade_id", how="left").groupby(["fold", "loss_cluster_size"], dropna=False).agg(trade_count=("trade_id", "size"), gross_loss_jpy=("realized_pl_jpy", lambda x: float(-x[x<0].sum())), gross_profit_jpy=("realized_pl_jpy", lambda x: float(x[x>0].sum())), net_profit_jpy=("realized_pl_jpy", "sum")).reset_index()

    robustness = {
        "cluster_permutation_test": permutation_cluster_test(d, entry),
        "candidate_event_bootstrap": {cid: r["event_bootstrap"] for cid, r in candidate_results.items()},
        "LOFO": lofo.to_dict("records"),
        "event_window_sensitivity": {},
        "matched_cohort_note": "concurrent vs standalone tables are stratified by fold/strategy/side/session in fold_strategy_side_session_metrics.csv; no causal claim from pooled difference",
        "shock_authority_note": "common four-fold shock state uses causal completed/open M15 movement contract; it is not labeled raw-tick shock. 2023 raw-tick equivalence is not asserted.",
    }
    for w in [15, 30, 60]:
        ev, mp = primary_portfolio_events(d, w)
        robustness["event_window_sensitivity"][str(w)] = {"event_count": int(len(ev)), "loss_cluster_event_count": int(ev.loss_cluster.sum()), "gross_loss_in_loss_cluster_events_jpy": float(ev.loc[ev.loss_cluster, "gross_loss_jpy"].sum())}

    base_recovery = baseline_recovery_episodes(d, baseline_w)
    selected_recovery = []
    for cid in family_rank.head(3).representative_candidate:
        c = next(z for z in candidates if z.candidate_id == cid)
        w, _ = replay_candidate(d, c)
        ep = baseline_recovery_episodes(d, w); ep["candidate_id"] = cid; selected_recovery.append(ep)
    recovery = pd.concat([base_recovery.assign(candidate_id="BASELINE")] + selected_recovery, ignore_index=True)

    write_json(a.out_dir / "source_inventory.json", source_inventory)
    write_json(a.out_dir / "trade_identity_audit.json", identity)
    write_json(a.out_dir / "portfolio_event_contract.json", protocol["portfolio_event_contract"])
    entry.to_csv(a.out_dir / "concurrent_exposure_ledger.csv.gz", index=False, compression="gzip")
    events.to_csv(a.out_dir / "portfolio_event_ledger.csv.gz", index=False, compression="gzip")
    loss_atlas.to_csv(a.out_dir / "loss_cluster_atlas.csv", index=False)
    drawdown.to_csv(a.out_dir / "drawdown_add_analysis.csv", index=False)
    overlap.to_csv(a.out_dir / "b02_f05_overlap_analysis.csv", index=False)
    session_chain.to_csv(a.out_dir / "session_loss_chain_analysis.csv", index=False)
    shock.to_csv(a.out_dir / "shock_adjacent_exposure_analysis.csv", index=False)
    concurrent.to_csv(a.out_dir / "concurrent_exposure_analysis.csv", index=False)
    cand.to_csv(a.out_dir / "counterfactual_exposure_control_metrics.csv", index=False)
    slices.to_csv(a.out_dir / "fold_strategy_side_session_metrics.csv.gz", index=False, compression="gzip")
    lofo.to_csv(a.out_dir / "leave_one_fold_out_results.csv", index=False)
    family_rank.to_csv(a.out_dir / "candidate_family_ranking.csv", index=False)
    pd.concat(audit_frames, ignore_index=True).to_csv(a.out_dir / "counterfactual_decision_audit.csv.gz", index=False, compression="gzip")
    recovery.to_csv(a.out_dir / "drawdown_recovery_survival.csv", index=False)
    baseline_curve.to_csv(a.out_dir / "baseline_M15_snapshot_equity_curve.csv.gz", index=False, compression="gzip")
    write_json(a.out_dir / "robustness_report.json", robustness)

    top3 = family_rank.head(3).to_dict("records")
    result = {
        "schema_version": "usdjpy_portfolio_loss_cluster_phase1_result_v1",
        "status": "PHASE1_COMPLETE_NO_PRODUCTION_IMPLEMENTATION",
        "population": identity, "baseline": baseline, "oracle": oracle,
        "candidate_top3": top3, "candidate_family_ranking": family_rank.to_dict("records"),
        "key_cluster_facts": {
            "portfolio_event_count": int(len(events)), "loss_cluster_event_count": int(events.loss_cluster.sum()),
            "gross_loss_in_loss_cluster_events_jpy": float(events.loc[events.loss_cluster, "gross_loss_jpy"].sum()),
            "loss_cluster_loss_coverage": float(events.loc[events.loss_cluster, "gross_loss_jpy"].sum() / total_loss),
            "concurrent_entry_count": int(entry.concurrent_exposure.sum()), "same_direction_overlap_count": int(entry.same_direction_overlap.sum()),
            "opposite_direction_overlap_count": int(entry.opposite_direction_overlap.sum()), "B02_F05_overlap_count": int(entry.B02_F05_overlap.sum()),
            "drawdown_add_count": int(entry.drawdown_add.sum()), "recovery_interference_count": int(entry.recovery_interference.sum()),
            "shock_or_post_shock_entry_count": int(entry.volatility_state.isin(["shock", "post_shock"]).sum()),
        },
        "boundaries": {"Entry_logic_changed": False, "Exit_logic_changed": False, "SL_TP_changed": False, "MT4_implementation": False, "2025H1_accessed": False, "2025H2_accessed": False, "production_authorized": False},
        "execution": {"research_sha": a.research_sha, "core_sha": a.core_sha, "workflow_run_id": a.workflow_run_id},
    }
    write_json(a.out_dir / "result.json", result)

    report = [
        "# USDJPY B02/F05 Portfolio Loss-Cluster Study Phase 1", "", f"Status: `{result['status']}`", "",
        "## Population", "", f"- trades: {len(d):,}", f"- B02 / F05: {identity['strategy_counts']['B02']:,} / {identity['strategy_counts']['F05']:,}", f"- winners / losers: {identity['winner_count']:,} / {identity['loser_count']:,}", f"- concurrent-entry trades: {identity['trades_entered_with_concurrent_position']:,}", f"- B02/F05 overlap entries: {identity['trades_entered_with_B02_F05_overlap']:,}", "",
        "## Loss clusters", "", f"- primary portfolio events: {len(events):,}", f"- events with at least two losses: {int(events.loss_cluster.sum()):,}", f"- gross loss covered by those events: ¥{events.loc[events.loss_cluster, 'gross_loss_jpy'].sum():,.0f} ({events.loc[events.loss_cluster, 'gross_loss_jpy'].sum()/total_loss:.1%})", f"- perfect loss-cluster avoidance oracle: +¥{oracle_avoided:,.0f}; not implementable", "",
        "## Candidate family ranking", "", "| Rank | Family | Representative | LOFO net-positive folds | LOFO DD-positive folds | LOFO net | Pooled DD reduction | Winner retention | Weakness |", "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in family_rank.itertuples(index=False):
        report.append(f"| {r.rank} | {r.family} | `{r.representative_candidate}` | {r.LOFO_positive_net_folds}/4 | {r.LOFO_positive_DD_folds}/4 | ¥{r.LOFO_net_improvement_jpy:,.0f} | ¥{r.pooled_M15_snapshot_DD_reduction_jpy:,.0f} | {r.winner_retention:.1%} | {r.weakness} |")
    report += ["", "## Boundaries", "", "- Entry/Exit/SL/TP unchanged.", "- No MT4 implementation.", "- 2025H1 and 2025H2 not accessed.", "- M15 shock state is a four-fold common completed/open-bar contract and is not represented as raw-tick shock authority.", ""]
    (a.out_dir / "phase1_result_report.md").write_text("\n".join(report), encoding="utf-8")

    next_text = ["# Next-step recommendation", "", "The top three families require a preregistered Phase 2 confirmation using the exact representative specifications and unchanged four-fold source lineage.", "", "Before any MT4 implementation:", "", "1. Re-run only the frozen top-three representatives with event-level bootstrap and session/month breadth gates.", "2. Require winner retention, top-winner retention and DD reduction to pass separately in at least three folds.", "3. For shock exposure, acquire or explicitly declare raw-tick authority by year; do not relabel the common M15 shock state as tick-exact.", "4. Only a passed Phase 2 candidate may proceed to Research/MT4 parity and later 2025H1 binding gate.", ""]
    (a.out_dir / "next_step_recommendation.md").write_text("\n".join(next_text), encoding="utf-8")

    failures = {"failures": [], "wasted_processing": [], "repairs": [], "recurrence_prevention": ["source assets verified by SHA before evaluation", "PR preflight computes no outcomes", "full scientific run occurs only after preregistration merge", "2025 and MT4 hard boundaries asserted in receipt"]}
    write_json(a.out_dir / "execution_failures.json", failures)
    receipt = {
        "schema_version": "usdjpy_portfolio_loss_cluster_phase1_execution_receipt_v1", "status": result["status"],
        "research_sha": a.research_sha, "core_sha": a.core_sha, "workflow_run_id": a.workflow_run_id,
        "protocol_sha256": sha256_file(a.protocol), "source_inventory": source_inventory,
        "reproduction_command": "python tools/evaluate_usdjpy_portfolio_loss_cluster_phase1_v1.py --protocol configs/research/usdjpy_portfolio_loss_cluster_phase1_prereg_v1.json --source-trades materialized/usdjpy_b02_f05_source_trade_ledger_v2.csv --trade-diagnostics impact_pre/trade_level_diagnostic_ledger.csv.gz --states materialized/usdjpy_b02_f05_entry_exit_state_ledger_v2.csv.gz --m15-2023 inputs/2023/normalized/usdjpy_2023_m15_bid_utc_rakuten_mt4_v1.csv.gz --m15-2024h1 inputs/2024h1/m15_utc_2024h1.csv --events-2024h2 inputs/2024h2/h2_baseline/fx2_usdjpy_f05_extatr_h2_baseline_v1.csv --out-dir portfolio_loss_cluster_output",
        "boundaries": result["boundaries"],
    }
    write_json(a.out_dir / "execution_receipt.json", receipt)
    manifest = {}
    for p in sorted(a.out_dir.iterdir()):
        if p.is_file(): manifest[p.name] = {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
    write_json(a.out_dir / "artifact_manifest.json", {"schema_version": "usdjpy_portfolio_loss_cluster_phase1_artifact_manifest_v1", "files": manifest})
    print(json.dumps({"status": result["status"], "top3": [r["family"] for r in top3], "trades": len(d)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
