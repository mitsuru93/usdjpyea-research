from .base import *
from .events import *
from .exposure import *
from .event_metrics import *
from .metrics import *
from .candidate_rules import *
from .robustness import *

def preflight(protocol: Path, out_dir: Path) -> None:
    p = json.loads(protocol.read_text(encoding="utf-8"))
    assert p["status"] == "FROZEN_BEFORE_OUTCOME_EXECUTION"
    assert p["development_folds"] == FOLDS
    assert p["protected_periods"] == ["2025H1", "2025H2"]
    assert p["candidate_grid"]["candidate_count"] == len(candidate_set())
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "preflight_result.json", {"schema_version": "usdjpy_portfolio_loss_cluster_phase1_preflight_v1", "status": "PASS_NO_OUTCOMES", "outcomes_computed": False, "portfolio_replay_computed": False, "MT4_accessed": False, "2025H1_accessed": False, "2025H2_accessed": False, "protocol_sha256": sha256_file(protocol), "candidate_count": len(candidate_set())})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--source-trades", type=Path)
    ap.add_argument("--trade-diagnostics", type=Path)
    ap.add_argument("--states", type=Path)
    ap.add_argument("--m15-2023", type=Path)
    ap.add_argument("--m15-2024h1", type=Path)
    ap.add_argument("--events-2024h2", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--research-sha", default="UNKNOWN")
    ap.add_argument("--core-sha", default="UNKNOWN")
    ap.add_argument("--workflow-run-id", default="LOCAL")
    ap.add_argument("--preflight-only", action="store_true")
    a = ap.parse_args()
    if a.preflight_only:
        preflight(a.protocol, a.out_dir); return
    for required in [a.source_trades, a.trade_diagnostics, a.states, a.m15_2023, a.m15_2024h1, a.events_2024h2]:
        if required is None: raise SystemExit("scientific mode requires all data inputs")
    protocol = json.loads(a.protocol.read_text(encoding="utf-8"))
    assert protocol["status"] == "FROZEN_BEFORE_OUTCOME_EXECUTION"
    a.out_dir.mkdir(parents=True, exist_ok=True)

    d = load_trade_diag(a.trade_diagnostics)
    source_trades = pd.read_csv(a.source_trades)
    source_trades["entry_utc"] = pd.to_datetime(source_trades.entry_utc, utc=True)
    source_trades["trade_id"] = source_trades.fold.astype(str) + "|" + source_trades.strategy.astype(str) + "|" + source_trades.entry_utc.astype(str) + "|" + source_trades.side.astype(int).astype(str)
    assert len(source_trades) == 1882 and source_trades.trade_id.nunique() == 1882
    assert set(source_trades.trade_id) == set(d.trade_id)
    assert sha256_file(a.source_trades) == "98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca"
    s = load_states(a.states)
    assert sha256_file(a.states) == "2caddc38cdb16ce7504fe1e3b625f8425ccc6f7d579d02590f9ee92bbf013eda"
    market = load_market(a.m15_2023, a.m15_2024h1, a.events_2024h2)
    me = market_at_entries(d, market)
    events, event_map = primary_portfolio_events(d, 60)
    d["portfolio_event_id"] = d.trade_id.map(event_map)
    losses = loss_clusters(d, 60)
    entry = build_entry_ledger(d, s, me, event_map, losses)
    chains = add_session_loss_chains(d)
    d = d.merge(chains, on="trade_id", validate="one_to_one")
    entry = entry.merge(chains, on="trade_id", validate="one_to_one")
    d = d.merge(entry[["trade_id", "volatility_state", "shock_elapsed_min", "shock"]], on="trade_id", validate="one_to_one")
    events = event_equity_stats(events, d, s)

    baseline_w = pd.Series(1.0, index=d.trade_id)
    baseline = realized_metrics(d, baseline_w)
    baseline_snapshot_dd, baseline_curve = snapshot_dd(d, s, baseline_w)
    baseline["maximum_M15_snapshot_drawdown_jpy"] = baseline_snapshot_dd
    total_loss = float(-d.loc[~d.winner, "realized_pl_jpy"].sum())
    total_profit = float(d.loc[d.winner, "realized_pl_jpy"].sum())

    identity = {
        "total_trades": int(len(d)), "strategy_counts": d.strategy.value_counts().sort_index().to_dict(),
        "fold_counts": d.fold.value_counts().reindex(FOLDS).astype(int).to_dict(),
        "side_counts": {"Long": int(d.side.gt(0).sum()), "Short": int(d.side.lt(0).sum())},
        "winner_count": int(d.winner.sum()), "loser_count": int((~d.winner).sum()),
        "trades_entered_with_concurrent_position": int(entry.concurrent_exposure.sum()),
        "trades_entered_with_B02_F05_overlap": int(entry.B02_F05_overlap.sum()),
        "duplicate_trade_ids": int(d.trade_id.duplicated().sum()), "identity_mismatch": int(set(d.trade_id) != set(s.trade_id)),
        "missing": {
            "lot": "not a variable field in canonical common ledger; fixed source contract 0.01 lot, normalized exposure=1.0",
            "MFE_MAE": "available at common M15 observation precision; not represented as raw-tick extrema for 2023",
            "run_artifact_build_identity": "source-level lineage fields, not duplicated per trade row",
        },
        "timestamp_precision": "15-minute canonical observation grid; 2024 event timestamps retain UTC event time",
        "timezone": "UTC; 2023 uses historical-2024-compatible clock transformer, 2024 source unmodified",
    }
    source_inventory = {
        "schema_version": "usdjpy_portfolio_loss_cluster_phase1_source_inventory_v1",
        "research_main_at_start": "57dded3efa003c1644e4bae49a239d7a21b21429",
        "core_main_at_start": "aca45ab891d9a6da272b5111a99142d99e874929",
        "source_release": "f05-failed-reclaim-historical-authorities-v1",
        "source_authorities": [
            {"folds": ["2023H1", "2023H2"], "core_run_id": 29997167048, "core_artifact_id": 8559483151, "asset": "usdjpy-2023-canonical-baseline-prep-v1.zip", "sha256": "22d66bf76c60362b78e9badff2113bc196b80e3657f5083ae470d1d62df70c01"},
            {"folds": ["2024H1"], "core_run_id": 29787357305, "core_artifact_id": 8479048161, "asset": "mt4-usdjpy-2024h1-event-audit-v1.zip", "sha256": "e078758343995c8254244dd36385c93a61a7124cb5037beb458afdf5d0e208e5"},
            {"folds": ["2024H2"], "core_run_id": 29873856877, "core_artifact_id": 8512432416, "asset": "mt4-usdjpy-f05-extatr-h2-validation-v1.zip", "sha256": "9c5846e8b6e47b4b981a3ceeec856391311d3864a8cd7c2bef7caf7d21e6375b"},
        ],
        "canonical_trade_ledger_sha256": "98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca",
        "canonical_state_ledger_sha256": "2caddc38cdb16ce7504fe1e3b625f8425ccc6f7d579d02590f9ee92bbf013eda",
        "input_sha256": {"source_trades": sha256_file(a.source_trades), "trade_diagnostics": sha256_file(a.trade_diagnostics), "states": sha256_file(a.states), "m15_2023": sha256_file(a.m15_2023), "m15_2024h1": sha256_file(a.m15_2024h1), "events_2024h2": sha256_file(a.events_2024h2)},
        "period_firewall": {"2025H1_accessed": False, "2025H2_accessed": False, "MT4_new_execution": False},
    }

    candidates = candidate_set()
    candidate_rows = []
    all_slice = []
    candidate_results: dict[str, dict[str, Any]] = {}
    audit_frames = []
    top_winners = set(d.nlargest(20, "realized_pl_jpy").trade_id)
    for c in candidates:
        w, aud = replay_candidate(d, c)
        audit_frames.append(aud)
        m = realized_metrics(d, w)
        snap_dd, _ = snapshot_dd(d, s, w)
        gp_c = float((d.loc[d.winner, "realized_pl_jpy"] * d.loc[d.winner, "trade_id"].map(w).fillna(0)).sum())
        gl_c = float(-(d.loc[~d.winner, "realized_pl_jpy"] * d.loc[~d.winner, "trade_id"].map(w).fillna(0)).sum())
        avoided = total_loss - gl_c
        lost_profit = total_profit - gp_c
        top_loss = float(sum(float(d.set_index("trade_id").loc[tid, "realized_pl_jpy"]) * (1.0 - float(w.get(tid, 0.0))) for tid in top_winners))
        fold_slice = metrics_by_slice(d, w, c.candidate_id)
        all_slice.append(fold_slice)
        folds = fold_slice[fold_slice.dimension.eq("fold")]
        winner_by_fold = {str(r.fold): float(r.winner_retention) if pd.notna(r.winner_retention) else None for r in folds.itertuples(index=False)}
        result = {
            "candidate_id": c.candidate_id, "family": c.family, "rule": c.rule, "value": c.value,
            **m,
            "maximum_M15_snapshot_drawdown_jpy": snap_dd,
            "avoided_gross_loss_jpy": avoided, "lost_gross_profit_jpy": lost_profit,
            "net_improvement_jpy": avoided - lost_profit,
            "realized_DD_reduction_jpy": float(baseline["maximum_realized_drawdown_jpy"] - m["maximum_realized_drawdown_jpy"]),
            "M15_snapshot_DD_reduction_jpy": float(baseline_snapshot_dd - snap_dd),
            "trade_reduction_count": int((w == 0).sum()), "exposure_reduction_equivalent": float((1.0 - w).sum()),
            "winner_damage_jpy": lost_profit, "winner_retention": gp_c / total_profit if total_profit else 1.0,
            "top20_winner_loss_jpy": top_loss,
            "positive_net_folds": int((folds.net_improvement_jpy > 0).sum()),
            "nonnegative_net_folds": int((folds.net_improvement_jpy >= 0).sum()),
            "positive_net_months": int((fold_slice[fold_slice.dimension.eq("month")].net_improvement_jpy > 0).sum()),
            "negative_net_months": int((fold_slice[fold_slice.dimension.eq("month")].net_improvement_jpy < 0).sum()),
            "event_bootstrap": event_bootstrap(d, w),
            "winner_retention_by_fold": winner_by_fold,
            "simplicity": c.simplicity,
        }
        candidate_results[c.candidate_id] = result
        row = result.copy(); row["event_bootstrap_ci95_jpy"] = json.dumps(row.pop("event_bootstrap")["ci95_jpy"]); row["winner_retention_by_fold"] = json.dumps(row["winner_retention_by_fold"], sort_keys=True)
        candidate_rows.append(row)

    cand = pd.DataFrame(candidate_rows)
    slices = pd.concat(all_slice, ignore_index=True)
