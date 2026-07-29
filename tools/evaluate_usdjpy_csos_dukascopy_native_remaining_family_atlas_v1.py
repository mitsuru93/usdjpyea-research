#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import usdjpy_csos_dukascopy_native_remaining_family_atlas_lib_v1 as lib


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_table(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, lineterminator="\n", na_rep="", float_format="%.10f")


def empty_metrics() -> dict[str, Any]:
    return {
        "raw_signals": 0,
        "suppressed_signals": 0,
        "executable_trades": 0,
        "long_trades": 0,
        "short_trades": 0,
        "net_jpy": 0.0,
        "gross_profit_jpy": 0.0,
        "gross_loss_jpy": 0.0,
        "profit_factor": None,
        "win_rate": None,
        "mean_pl_jpy": None,
        "median_pl_jpy": None,
        "realized_mdd_jpy": 0.0,
        "minimum_realized_equity_jpy": lib.INITIAL_CAPITAL,
        "mean_mae_pips": None,
        "mean_mfe_pips": None,
        "mean_time_to_mae_seconds": None,
        "mean_time_to_mfe_seconds": None,
        "positive_folds": 0,
        "minimum_fold_jpy": 0.0,
        "positive_months": 0,
        "minimum_month_jpy": 0.0,
        "positive_sessions": 0,
        "year_concentration": None,
        "fold_concentration": None,
        "month_concentration": None,
        "session_concentration": None,
        "fold_trades": {fold: 0 for fold in lib.FOLDS},
        "month_trades": {month: 0 for month in lib.MONTHS},
        "session_trades": {},
        "fold_net_jpy": {fold: 0.0 for fold in lib.FOLDS},
        "month_net_jpy": {month: 0.0 for month in lib.MONTHS},
        "side_net_jpy": {"LONG": 0.0, "SHORT": 0.0},
        "session_net_jpy": {},
        "year_net_jpy": {"2023": 0.0, "2024": 0.0},
    }


def select_shortlist(track_a: pd.DataFrame, track_b: pd.DataFrame, records: pd.DataFrame) -> dict[str, Any]:
    a_choice = track_a[track_a.track_a_eligible].head(1)
    track_a_row = None if a_choice.empty else lib.clean(a_choice.iloc[0].to_dict())
    b_candidates = track_b[track_b.track_b_eligible].copy()
    if track_a_row is not None:
        a_family = track_a_row["family_id"]
        a_variant = track_a_row["variant_id"]
        b_candidates = b_candidates[(b_candidates.family_id != a_family) | (b_candidates.variant_id == a_variant)]
    b_choice = b_candidates.head(1)
    track_b_row = None if b_choice.empty else lib.clean(b_choice.iloc[0].to_dict())
    shortlisted = {row["variant_id"] for row in [track_a_row, track_b_row] if row is not None}
    mechanism_candidates = records[~records.variant_id.isin(shortlisted)].copy()
    mechanism_candidates = mechanism_candidates[
        (mechanism_candidates.post_event_15m_separation_pips >= 1.0)
        & (mechanism_candidates.post_event_60m_separation_pips >= 2.0)
        & (mechanism_candidates.negative_baseline_day_contribution_jpy > 0)
        & (mechanism_candidates.max_abs_baseline_correlation <= 0.20)
        & (~mechanism_candidates.track_a_eligible)
        & (~mechanism_candidates.track_b_eligible)
    ]
    mechanism_candidates = mechanism_candidates.sort_values(
        ["negative_baseline_day_contribution_jpy", "post_event_60m_separation_pips", "max_abs_baseline_correlation"],
        ascending=[False, False, True],
        kind="mergesort",
    )
    mechanism = None
    if len(mechanism_candidates):
        row = mechanism_candidates.iloc[0]
        mechanism = lib.clean({
            "family_id": row.family_id,
            "variant_id": row.variant_id,
            "designation": "MECHANISM_RESEARCH_ONLY",
            "post_event_15m_separation_pips": row.post_event_15m_separation_pips,
            "post_event_60m_separation_pips": row.post_event_60m_separation_pips,
            "negative_baseline_day_contribution_jpy": row.negative_baseline_day_contribution_jpy,
            "daily_correlation_to_B02": row.daily_correlation_to_B02,
            "daily_correlation_to_F05": row.daily_correlation_to_F05,
            "direct_candidate_failure": "At least one fixed shortlist gate failed; the current variant is not authorized for adoption.",
            "entry_time_distinct_hypothesis": lib.MECHANISM_HYPOTHESES[str(row.variant_id)],
            "overlap_with_hyp028_033_034": False,
        })
    if track_a_row and track_b_row:
        decision = "ATLAS_COMPLETE_DUAL_SHORTLIST"
    elif track_a_row:
        decision = "ATLAS_COMPLETE_INDEPENDENT_ALPHA_SHORTLIST"
    elif track_b_row:
        decision = "ATLAS_COMPLETE_COMPLEMENTARITY_SHORTLIST"
    elif mechanism:
        decision = "ATLAS_COMPLETE_MECHANISM_RESEARCH_ONLY"
    else:
        decision = "ATLAS_COMPLETE_NO_FAMILY_WORTH_FOLLOWUP"
    return {
        "decision": decision,
        "track_a": track_a_row,
        "track_b": track_b_row,
        "unique_shortlisted_variants": sorted(shortlisted),
        "shortlist_count": len(shortlisted),
        "same_family_multiple_variants": False,
        "mechanism_research_only": mechanism,
        "shortlist_meaning": "Research prioritization only",
        "candidate_freeze": False,
        "analysis_2020_2022_authorized_for_future_independent_research": True,
        "analysis_2020_2022_confirmation_credit": False,
        "2025_external_validation_authorized_in_this_atlas": False,
        "core_mt4_authorized": False,
        "production_authorized": False,
        "live_authorized": False,
    }


def make_human_report(
    path: Path,
    result: dict[str, Any],
    variant_comparison: pd.DataFrame,
    family_comparison: pd.DataFrame,
    identity_summary: pd.DataFrame,
) -> None:
    lines = [
        "# CSOS Dukascopy-Native Remaining-Family Opportunity Atlas Study",
        "",
        f"Final decision: `{result['decision']}`",
        "",
        "## Authority and boundaries",
        "",
        f"- Program ID: `{result['program_id']}`",
        f"- Research start SHA: `{result['research_start_sha']}`",
        f"- Research execution SHA: `{result['research_execution_sha']}`",
        f"- Core reference SHA: `{result['core_reference_sha']}`",
        f"- Workflow Run: `{result['run_id']}`",
        "- Atlas period: 2023-2024 only.",
        "- 2020-2022 EA-wide role: analysis period; this Atlas did not require or access it and assigns no confirmation or external-validation credit.",
        "- 2025 EA-wide role: the only binding unseen external-validation period; this Atlas did not access it.",
        "- Shortlist meaning: research prioritization only. It is not candidate approval, Core/MT4 authorization, 2025 authorization, production authorization, or live authorization.",
        "- Family contract, ranking metric, cost assumption and shortlist gates were frozen before new family outcome calculation and were unchanged by the period-role clarification.",
        "",
        "## Source inventory",
        "",
        f"- Dukascopy monthly archives: {result['source_authority']['archive_count']}",
        f"- Tick count: {result['source_authority']['tick_count']:,}",
        f"- Reconstructed M15 bars: {result['source_authority']['m15_bar_count']:,}",
        f"- Ask < Bid: {result['source_authority']['ask_bid_inversion_count']}",
        f"- Nonmonotonic Tick timestamps: {result['source_authority']['nonmonotonic_timestamp_count']}",
        "",
        "## Variant comparison",
        "",
        "|Track A rank|Track B rank|Variant|Trades|Net JPY|PF|Positive folds|Positive months|Top-5 removed|Spread +1 pip|Delay +5s|Corr B02|Corr F05|Negative-day contribution|Combined DD|A eligible|B eligible|",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    a_rank = result["track_a_ranks"]
    b_rank = result["track_b_ranks"]
    for row in variant_comparison.sort_values("variant_id", kind="mergesort").itertuples(index=False):
        lines.append(
            f"|{a_rank[str(row.variant_id)]}|{b_rank[str(row.variant_id)]}|{row.variant_id}|{int(row.executable_trades)}|¥{row.net_jpy:,.0f}|"
            f"{'' if pd.isna(row.profit_factor) else f'{row.profit_factor:.3f}'}|{int(row.positive_folds)}/4|{int(row.positive_months)}/24|"
            f"¥{row.top5_winners_removed_net_jpy:,.0f}|¥{row.spread_plus_1pip_net_jpy:,.0f}|¥{row.entry_delay_5s_net_jpy:,.0f}|"
            f"{row.daily_correlation_to_B02:.3f}|{row.daily_correlation_to_F05:.3f}|¥{row.negative_baseline_day_contribution_jpy:,.0f}|"
            f"¥{row.combined_realized_dd_jpy:,.0f}|{bool(row.track_a_eligible)}|{bool(row.track_b_eligible)}|"
        )
    lines += ["", "## Family comparison", "", "|Family|Variants|Trades|Net JPY|PF|Positive folds|Positive months|Corr B02|Corr F05|Negative-day contribution|Combined DD|", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in family_comparison.sort_values("family_id", kind="mergesort").itertuples(index=False):
        lines.append(
            f"|{row.family_id} — {row.family}|{int(row.variant_count)}|{int(row.executable_trades)}|¥{row.net_jpy:,.0f}|"
            f"{'' if pd.isna(row.profit_factor) else f'{row.profit_factor:.3f}'}|{int(row.positive_folds)}/4|{int(row.positive_months)}/24|"
            f"{row.daily_correlation_to_B02:.3f}|{row.daily_correlation_to_F05:.3f}|¥{row.negative_baseline_day_contribution_jpy:,.0f}|¥{row.combined_realized_dd_jpy:,.0f}|"
        )
    lines += ["", "## Old Atlas identity diagnostic", "", "Old Atlas identity is diagnostic only and is not a shortlist gate.", "", "|Variant|Old events|Dukascopy events|Common signal/side|Exact common|Old-only|Dukascopy-only|P/L mismatch|", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in identity_summary.itertuples(index=False):
        lines.append(f"|{row.variant_id}|{int(row.old_atlas_events)}|{int(row.dukascopy_native_events)}|{int(row.common_signal_side_events)}|{int(row.exact_common_events)}|{int(row.old_atlas_only)}|{int(row.dukascopy_only)}|{int(row.pl_mismatch)}|")
    shortlist = result["shortlist"]
    lines += ["", "## Shortlist decision", ""]
    if shortlist["track_a"] is not None:
        lines.append(f"- Track A: `{shortlist['track_a']['variant_id']}` / family `{shortlist['track_a']['family_id']}`.")
    else:
        lines.append("- Track A: no variant passed all fixed gates.")
    if shortlist["track_b"] is not None:
        lines.append(f"- Track B: `{shortlist['track_b']['variant_id']}` / family `{shortlist['track_b']['family_id']}`.")
    else:
        lines.append("- Track B: no variant passed all fixed gates.")
    if shortlist["mechanism_research_only"] is not None:
        lines.append(f"- Mechanism-research-only: `{shortlist['mechanism_research_only']['variant_id']}`.")
    else:
        lines.append("- Mechanism-research-only: none.")
    lines += [
        "",
        "## Full-equity limitation",
        "",
        f"`{result['full_equity_status']}` — {result['full_equity_reason']}",
        "",
        "## Correct next period design",
        "",
        "Any shortlisted family must move to a separate Hypothesis. In that research, 2020-2022 may be used for mechanism analysis and candidate design, 2023-2024 remains the main research/candidate-construction period, and the candidate must be frozen before the only binding unseen external gate in 2025. No candidate freeze, Core/MT4, 2025, production or live authorization is granted by this Atlas.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-2023", type=Path, required=True)
    parser.add_argument("--raw-2024", type=Path, required=True)
    parser.add_argument("--old-atlas-ledger", type=Path, required=True)
    parser.add_argument("--baseline-trades", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--contract-catalog", type=Path, required=True)
    parser.add_argument("--prior-study-audit", type=Path, required=True)
    parser.add_argument("--period-role-clarification", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--research-sha", required=True)
    parser.add_argument("--core-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    prereg = read_json(args.prereg)
    source_manifest = read_json(args.source_manifest)
    contract = read_json(args.contract_catalog)
    prior_audit = read_json(args.prior_study_audit)
    clarification = read_json(args.period_role_clarification)
    assert prereg["program_id"] == lib.PROGRAM
    assert prereg["status"] == "FROZEN_BEFORE_DUKASCOPY_NATIVE_OUTCOMES"
    assert prereg["period_role_clarification"]["received_before_new_family_outcome_calculation"] is True
    assert prereg["period_roles"]["2020_2022"]["ea_research_role"] == "ANALYSIS_PERIOD"
    assert prereg["period_roles"]["2020_2022"]["confirmation_credit"] is False
    assert prereg["period_roles"]["2025"]["ea_research_role"] == "UNSEEN_BINDING_EXTERNAL_VALIDATION_PERIOD"
    assert source_manifest["binding_tick_years"] == [2023, 2024]
    assert source_manifest["2020_2022_confirmation_credit"] is False
    assert source_manifest["2025_external_validation_role"] is True
    assert contract["status"] == "FROZEN_BEFORE_DUKASCOPY_NATIVE_OUTCOMES"
    assert [row["variant_id"] for row in contract["variants"]] == lib.TARGET_VARIANTS
    assert clarification["status"] == "PASS_PROTOCOL_CLARIFICATION_BEFORE_NEW_FAMILY_OUTCOMES"
    assert clarification["candidate_outcomes_accessed_before_correction"] is False
    assert clarification["family_contract_changed"] is False
    assert clarification["ranking_metric_changed"] is False
    assert clarification["shortlist_gate_changed"] is False
    assert clarification["source_authority_changed"] is False
    assert prior_audit["evaluated_variant_count"] == 12
    if args.preflight_only:
        receipt = {
            "schema_version": "usdjpy_csos_dukascopy_native_remaining_family_atlas_preflight_v1",
            "status": "PASS_FROZEN_BEFORE_NEW_FAMILY_OUTCOMES",
            "program_id": lib.PROGRAM,
            "raw_archive_count": len(list(args.raw_2023.glob("*.tar.gz"))) + len(list(args.raw_2024.glob("*.tar.gz"))),
            "old_atlas_exists": args.old_atlas_ledger.exists(),
            "baseline_exists": args.baseline_trades.exists(),
            "variant_count": len(lib.TARGET_VARIANTS),
            "candidate_outcomes_computed": False,
            "analysis_2020_2022_accessed": False,
            "analysis_2020_2022_confirmation_credit": False,
            "external_validation_2025_accessed": False,
            "family_contract_changed_after_period_clarification": False,
            "ranking_gate_changed_after_period_clarification": False,
            "source_changed_after_period_clarification": False,
        }
        receipt["pass"] = receipt["raw_archive_count"] == 24 and receipt["old_atlas_exists"] and receipt["baseline_exists"] and receipt["variant_count"] == 12
        lib.write_json(args.out_dir / "preflight_receipt.json", receipt)
        print(json.dumps(receipt, indent=2))
        return 0 if receipt["pass"] else 2

    raw_dirs = [args.raw_2023, args.raw_2024]
    bars, tick_audit, source = lib.reconstruct_source(raw_dirs)
    source_gates = {
        "archive_count_24": source["archive_count"] == 24,
        "tick_count_exact": source["tick_count"] == 84428370,
        "m15_bar_count_exact": source["m15_bar_count"] == 49894,
        "ask_bid_inversion_zero": source["ask_bid_inversion_count"] == 0,
        "duplicate_tick_timestamp_zero": source["duplicate_timestamp_count"] == 0,
        "nonmonotonic_tick_zero": source["nonmonotonic_timestamp_count"] == 0,
        "duplicate_m15_bar_zero": source["duplicate_bar_count"] == 0,
    }
    lib.write_json(args.out_dir / "source_inventory.json", {**source, "gates": source_gates, "pass": all(source_gates.values())})
    lib.deterministic_gzip_csv(args.out_dir / "source_tick_day_audit.csv.gz", tick_audit)
    if not all(source_gates.values()):
        result = {
            "schema_version": "usdjpy_csos_dukascopy_native_remaining_family_atlas_final_result_v1",
            "program_id": lib.PROGRAM,
            "decision": "TECHNICAL_NO_RESULT_SOURCE_AUTHORITY",
            "research_start_sha": prereg["research_start_sha"],
            "research_execution_sha": args.research_sha,
            "core_reference_sha": args.core_sha,
            "run_id": args.run_id,
            "source_authority": source,
            "analysis_2020_2022_accessed": False,
            "analysis_2020_2022_confirmation_credit": False,
            "external_validation_2025_accessed": False,
            "candidate_freeze": False,
            "core_mt4_authorized": False,
            "production_authorized": False,
            "live_authorized": False,
        }
        lib.write_json(args.out_dir / "final_result.json", result)
        return 2

    features = lib.feature_frame(bars)
    raw_signals = lib.raw_signal_frame(features)
    events, signal_audit, suppression = lib.suppress_and_translate(raw_signals, features)
    trades = lib.execute_events(raw_dirs, events)
    integrity = {
        "all_target_variants_present": set(lib.TARGET_VARIANTS) == set(events.variant_id.unique()),
        "unresolved_chronology_zero": int((~trades.chronology_resolved.astype(bool)).sum()) == 0,
        "duplicate_event_zero": int(trades.raw_event_id.duplicated().sum()) == 0,
        "entry_not_before_decision": bool((trades.entry_tick_utc >= pd.to_datetime(trades.decision_utc, utc=True)).all()),
        "exit_not_before_entry": bool((trades.exit_tick_utc >= trades.entry_tick_utc).all()),
        "currency_replay_exact": bool(np.allclose(trades.realized_pl_jpy, trades.observed_pips * lib.JPY_PER_PIP, atol=lib.TOL)),
        "reporting_currency_jpy": prereg["monetary_contract"]["reporting_currency"] == "JPY",
        "position_units_exact": prereg["monetary_contract"]["position_units"] == 1000,
        "pip_value_jpy_exact": prereg["monetary_contract"]["pip_value_jpy"] == 10.0,
    }
    lib.write_json(args.out_dir / "executable_integrity_audit.json", {"gates": integrity, "pass": all(integrity.values())})
    if not all(integrity.values()):
        result = {
            "schema_version": "usdjpy_csos_dukascopy_native_remaining_family_atlas_final_result_v1",
            "program_id": lib.PROGRAM,
            "decision": "TECHNICAL_NO_RESULT",
            "technical_stage": "EXECUTABLE_INTEGRITY",
            "research_start_sha": prereg["research_start_sha"],
            "research_execution_sha": args.research_sha,
            "core_reference_sha": args.core_sha,
            "run_id": args.run_id,
            "integrity": integrity,
            "analysis_2020_2022_accessed": False,
            "analysis_2020_2022_confirmation_credit": False,
            "external_validation_2025_accessed": False,
            "candidate_freeze": False,
            "core_mt4_authorized": False,
            "production_authorized": False,
            "live_authorized": False,
        }
        lib.write_json(args.out_dir / "final_result.json", result)
        return 2

    lib.deterministic_gzip_csv(args.out_dir / "raw_signal_audit.csv.gz", signal_audit)
    write_table(args.out_dir / "suppression_metrics.csv", suppression)
    lib.deterministic_gzip_csv(args.out_dir / "source_native_event_ledger.csv.gz", events)
    lib.deterministic_gzip_csv(args.out_dir / "source_native_executable_ledger.csv.gz", trades)
    old = lib.load_old_atlas(args.old_atlas_ledger)
    identity_summary, identity_detail = lib.identity_audit(old, events, trades)
    write_table(args.out_dir / "old_new_atlas_identity_summary.csv", identity_summary)
    lib.deterministic_gzip_csv(args.out_dir / "old_new_atlas_mismatch_ledger.csv.gz", identity_detail)
    baseline = lib.load_baseline(args.baseline_trades)

    variant_records: list[dict[str, Any]] = []
    gate_rows: list[dict[str, Any]] = []
    concentration_records: list[dict[str, Any]] = []
    bootstrap_records: list[dict[str, Any]] = []
    robustness_records: list[dict[str, Any]] = []
    portfolio_records: list[dict[str, Any]] = []
    fold_tables: list[pd.DataFrame] = []
    month_tables: list[pd.DataFrame] = []
    side_tables: list[pd.DataFrame] = []
    session_tables: list[pd.DataFrame] = []
    loss_cluster_tables: list[pd.DataFrame] = []
    mechanism_records: list[dict[str, Any]] = []
    raw_counts = raw_signals.groupby("variant_id").size().to_dict()
    accepted_counts = events.groupby("variant_id").size().to_dict()
    for variant in lib.TARGET_VARIANTS:
        group = trades[trades.variant_id.eq(variant)].copy()
        raw_count = int(raw_counts.get(variant, 0))
        accepted_count = int(accepted_counts.get(variant, 0))
        if len(group):
            standalone = lib.standalone_metrics(group, raw_count, raw_count - accepted_count)
            concentration = lib.concentration_metrics(group)
            bootstrap = lib.bootstrap_metrics(group)
            robustness = lib.robustness_metrics(group)
            portfolio, clusters = lib.portfolio_metrics(baseline, group)
            separation = lib.post_event_separation(group)
            fold = lib.bucket_metrics(group, "fold", lib.FOLDS)
            month = lib.bucket_metrics(group, "entry_month", lib.MONTHS)
            side = lib.bucket_metrics(group, "side_label", ["LONG", "SHORT"])
            session = lib.bucket_metrics(group, "session")
        else:
            standalone = empty_metrics()
            standalone["raw_signals"] = raw_count
            standalone["suppressed_signals"] = raw_count
            concentration = {key: 0.0 for key in ["best_event_removed_net_jpy", "top3_winners_removed_net_jpy", "top5_winners_removed_net_jpy", "top10_winners_removed_net_jpy", "top_decile_winners_removed_net_jpy"]}
            concentration["top_decile_winner_count"] = 0
            bootstrap = {"reps": 5000, "seed": 41041, "event": {"lower_95_jpy": None, "median_jpy": None, "upper_95_jpy": None, "p_non_positive": None}, "date": {"lower_95_jpy": None, "median_jpy": None, "upper_95_jpy": None, "p_non_positive": None}, "session_block": {"lower_95_jpy": None, "median_jpy": None, "upper_95_jpy": None, "p_non_positive": None}}
            robustness = {"observed_bid_ask_net_jpy": 0.0, "spread_plus_0_5_pip_net_jpy": 0.0, "spread_plus_1_0_pip_net_jpy": 0.0, "spread_plus_2_0_pip_net_jpy": 0.0, "entry_delay_5s_net_jpy": 0.0, "entry_delay_15s_net_jpy": 0.0, "adverse_slippage_0_5_pip_each_execution_net_jpy": 0.0, "mean_observed_spread_pips": None, "maximum_entry_execution_delay_seconds": None, "maximum_exit_execution_delay_seconds": None}
            portfolio = {"baseline_net_jpy": float(baseline.realized_pl_jpy.sum()), "candidate_additive_net_jpy": 0.0, "combined_net_jpy": float(baseline.realized_pl_jpy.sum()), "daily_correlation_to_B02": 0.0, "daily_correlation_to_F05": 0.0, "positive_baseline_day_contribution_jpy": 0.0, "negative_baseline_day_contribution_jpy": 0.0, "baseline_realized_dd_jpy": None, "combined_realized_dd_jpy": None, "realized_dd_improvement_jpy": 0.0, "baseline_minimum_realized_equity_jpy": None, "combined_minimum_realized_equity_jpy": None, "minimum_realized_equity_improvement_jpy": 0.0, "baseline_worst_5_business_day_jpy": None, "combined_worst_5_business_day_jpy": None, "baseline_worst_20_business_day_jpy": None, "combined_worst_20_business_day_jpy": None, "full_equity_status": "NOT_AVAILABLE", "full_equity_reason": "No executable candidate trades."}
            separation = {f"winner_minus_loser_{horizon}m_pips": None for horizon in [15, 30, 60, 120, 240]}
            fold = lib.bucket_metrics(group, "fold", lib.FOLDS)
            month = lib.bucket_metrics(group, "entry_month", lib.MONTHS)
            side = lib.bucket_metrics(group, "side_label", ["LONG", "SHORT"])
            session = pd.DataFrame()
            clusters = pd.DataFrame()
        rows, track_a_gates, track_b_gates = lib.build_gate_rows(variant, standalone, concentration, bootstrap, robustness, portfolio)
        gate_rows.extend(rows)
        record = {
            "family_id": lib.VARIANT_TO_FAMILY[variant],
            "family": lib.FAMILY_NAMES[lib.VARIANT_TO_FAMILY[variant]],
            "variant_id": variant,
            **standalone,
            "best_event_removed_net_jpy": concentration["best_event_removed_net_jpy"],
            "top3_winners_removed_net_jpy": concentration["top3_winners_removed_net_jpy"],
            "top5_winners_removed_net_jpy": concentration["top5_winners_removed_net_jpy"],
            "top10_winners_removed_net_jpy": concentration["top10_winners_removed_net_jpy"],
            "top_decile_winners_removed_net_jpy": concentration["top_decile_winners_removed_net_jpy"],
            "event_bootstrap_lower_95_jpy": bootstrap["event"]["lower_95_jpy"],
            "event_bootstrap_upper_95_jpy": bootstrap["event"]["upper_95_jpy"],
            "event_bootstrap_p_non_positive": bootstrap["event"]["p_non_positive"],
            "date_bootstrap_lower_95_jpy": bootstrap["date"]["lower_95_jpy"],
            "date_bootstrap_upper_95_jpy": bootstrap["date"]["upper_95_jpy"],
            "date_bootstrap_p_non_positive": bootstrap["date"]["p_non_positive"],
            "session_bootstrap_lower_95_jpy": bootstrap["session_block"]["lower_95_jpy"],
            "session_bootstrap_upper_95_jpy": bootstrap["session_block"]["upper_95_jpy"],
            "session_bootstrap_p_non_positive": bootstrap["session_block"]["p_non_positive"],
            "spread_plus_0_5pip_net_jpy": robustness["spread_plus_0_5_pip_net_jpy"],
            "spread_plus_1pip_net_jpy": robustness["spread_plus_1_0_pip_net_jpy"],
            "spread_plus_2pip_net_jpy": robustness["spread_plus_2_0_pip_net_jpy"],
            "entry_delay_5s_net_jpy": robustness["entry_delay_5s_net_jpy"],
            "entry_delay_15s_net_jpy": robustness["entry_delay_15s_net_jpy"],
            "adverse_slippage_0_5pip_each_net_jpy": robustness["adverse_slippage_0_5_pip_each_execution_net_jpy"],
            "daily_correlation_to_B02": portfolio["daily_correlation_to_B02"],
            "daily_correlation_to_F05": portfolio["daily_correlation_to_F05"],
            "max_abs_baseline_correlation": max(abs(portfolio["daily_correlation_to_B02"]), abs(portfolio["daily_correlation_to_F05"])),
            "positive_baseline_day_contribution_jpy": portfolio["positive_baseline_day_contribution_jpy"],
            "negative_baseline_day_contribution_jpy": portfolio["negative_baseline_day_contribution_jpy"],
            "combined_net_jpy": portfolio["combined_net_jpy"],
            "baseline_realized_dd_jpy": portfolio["baseline_realized_dd_jpy"],
            "combined_realized_dd_jpy": portfolio["combined_realized_dd_jpy"],
            "realized_dd_improvement_jpy": portfolio["realized_dd_improvement_jpy"],
            "baseline_minimum_realized_equity_jpy": portfolio["baseline_minimum_realized_equity_jpy"],
            "combined_minimum_realized_equity_jpy": portfolio["combined_minimum_realized_equity_jpy"],
            "minimum_realized_equity_improvement_jpy": portfolio["minimum_realized_equity_improvement_jpy"],
            "baseline_worst_5_business_day_jpy": portfolio["baseline_worst_5_business_day_jpy"],
            "combined_worst_5_business_day_jpy": portfolio["combined_worst_5_business_day_jpy"],
            "baseline_worst_20_business_day_jpy": portfolio["baseline_worst_20_business_day_jpy"],
            "combined_worst_20_business_day_jpy": portfolio["combined_worst_20_business_day_jpy"],
            "same_direction_overlap_rate": portfolio.get("same_direction_overlap_rate"),
            "opposite_direction_overlap_rate": portfolio.get("opposite_direction_overlap_rate"),
            "simultaneous_holding_rate": portfolio.get("simultaneous_holding_rate"),
            "peak_concurrency": portfolio.get("combined_peak_concurrency"),
            "incremental_margin_proxy_position_units": portfolio.get("incremental_margin_proxy_position_units"),
            "post_event_15m_separation_pips": separation.get("winner_minus_loser_15m_pips"),
            "post_event_60m_separation_pips": separation.get("winner_minus_loser_60m_pips"),
            "track_a_pass_count": int(sum(track_a_gates.values())),
            "track_a_gate_count": len(track_a_gates),
            "track_a_eligible": bool(all(track_a_gates.values())),
            "track_b_pass_count": int(sum(track_b_gates.values())),
            "track_b_gate_count": len(track_b_gates),
            "track_b_eligible": bool(all(track_b_gates.values())),
        }
        variant_records.append(record)
        concentration_records.append({"family_id": lib.VARIANT_TO_FAMILY[variant], "variant_id": variant, **concentration})
        bootstrap_records.append({"family_id": lib.VARIANT_TO_FAMILY[variant], "variant_id": variant, **{f"event_{key}": value for key, value in bootstrap["event"].items()}, **{f"date_{key}": value for key, value in bootstrap["date"].items()}, **{f"session_block_{key}": value for key, value in bootstrap["session_block"].items()}, "reps": bootstrap["reps"], "seed": bootstrap["seed"]})
        robustness_records.append({"family_id": lib.VARIANT_TO_FAMILY[variant], "variant_id": variant, **robustness})
        portfolio_records.append({"family_id": lib.VARIANT_TO_FAMILY[variant], "variant_id": variant, **portfolio})
        mechanism_records.append({"family_id": lib.VARIANT_TO_FAMILY[variant], "variant_id": variant, **separation, "entry_time_distinct_hypothesis": lib.MECHANISM_HYPOTHESES[variant]})
        for table, collection in [(fold, fold_tables), (month, month_tables), (side, side_tables), (session, session_tables)]:
            if len(table):
                table.insert(0, "variant_id", variant)
                table.insert(0, "family_id", lib.VARIANT_TO_FAMILY[variant])
                collection.append(table)
        if len(clusters):
            clusters.insert(0, "variant_id", variant)
            clusters.insert(0, "family_id", lib.VARIANT_TO_FAMILY[variant])
            loss_cluster_tables.append(clusters)

    variant_comparison = pd.DataFrame(variant_records)
    gate_matrix = pd.DataFrame(gate_rows)
    track_a, track_b, _ = lib.rank_and_shortlist(variant_records)
    shortlist = select_shortlist(track_a, track_b, variant_comparison)
    track_a_ranks = {str(row.variant_id): int(row.track_a_rank) for row in track_a.itertuples(index=False)}
    track_b_ranks = {str(row.variant_id): int(row.track_b_rank) for row in track_b.itertuples(index=False)}
    family_trades = lib.family_nonoverlap(trades)
    lib.deterministic_gzip_csv(args.out_dir / "family_nonoverlap_executable_ledger.csv.gz", family_trades)
    family_records: list[dict[str, Any]] = []
    family_bootstrap_records: list[dict[str, Any]] = []
    family_portfolio_records: list[dict[str, Any]] = []
    for family_id in sorted(lib.FAMILY_NAMES):
        group = family_trades[family_trades.family_id.eq(family_id)].copy()
        family_variants = [variant for variant in lib.TARGET_VARIANTS if lib.VARIANT_TO_FAMILY[variant] == family_id]
        raw_count = int(raw_signals[raw_signals.variant_id.isin(family_variants)].shape[0])
        accepted_count = int(events[events.variant_id.isin(family_variants)].shape[0])
        standalone = lib.standalone_metrics(group, raw_count, raw_count - accepted_count)
        concentration = lib.concentration_metrics(group)
        bootstrap = lib.bootstrap_metrics(group, seed=51000 + ord(family_id))
        robustness = lib.robustness_metrics(group)
        portfolio, _ = lib.portfolio_metrics(baseline, group)
        family_records.append({
            "family_id": family_id,
            "family": lib.FAMILY_NAMES[family_id],
            "variant_count": len(family_variants),
            "variants": ";".join(family_variants),
            **standalone,
            "best_event_removed_net_jpy": concentration["best_event_removed_net_jpy"],
            "top5_winners_removed_net_jpy": concentration["top5_winners_removed_net_jpy"],
            "event_bootstrap_lower_95_jpy": bootstrap["event"]["lower_95_jpy"],
            "event_bootstrap_upper_95_jpy": bootstrap["event"]["upper_95_jpy"],
            "event_bootstrap_p_non_positive": bootstrap["event"]["p_non_positive"],
            "spread_plus_1pip_net_jpy": robustness["spread_plus_1_0_pip_net_jpy"],
            "entry_delay_5s_net_jpy": robustness["entry_delay_5s_net_jpy"],
            "daily_correlation_to_B02": portfolio["daily_correlation_to_B02"],
            "daily_correlation_to_F05": portfolio["daily_correlation_to_F05"],
            "negative_baseline_day_contribution_jpy": portfolio["negative_baseline_day_contribution_jpy"],
            "combined_net_jpy": portfolio["combined_net_jpy"],
            "combined_realized_dd_jpy": portfolio["combined_realized_dd_jpy"],
            "realized_dd_improvement_jpy": portfolio["realized_dd_improvement_jpy"],
        })
        family_bootstrap_records.append({"family_id": family_id, **{f"event_{key}": value for key, value in bootstrap["event"].items()}, **{f"date_{key}": value for key, value in bootstrap["date"].items()}, **{f"session_block_{key}": value for key, value in bootstrap["session_block"].items()}, "reps": bootstrap["reps"], "seed": bootstrap["seed"]})
        family_portfolio_records.append({"family_id": family_id, **portfolio})
    family_comparison = pd.DataFrame(family_records)

    write_table(args.out_dir / "variant_comparison.csv", variant_comparison)
    write_table(args.out_dir / "family_comparison.csv", family_comparison)
    write_table(args.out_dir / "track_a_independent_alpha_ranking.csv", track_a)
    write_table(args.out_dir / "track_b_complementarity_ranking.csv", track_b)
    write_table(args.out_dir / "variant_gate_matrix.csv", gate_matrix)
    write_table(args.out_dir / "variant_concentration.csv", pd.DataFrame(concentration_records))
    write_table(args.out_dir / "variant_bootstrap.csv", pd.DataFrame(bootstrap_records))
    write_table(args.out_dir / "family_bootstrap.csv", pd.DataFrame(family_bootstrap_records))
    write_table(args.out_dir / "execution_robustness.csv", pd.DataFrame(robustness_records))
    write_table(args.out_dir / "portfolio_diagnostics.csv", pd.DataFrame(portfolio_records))
    write_table(args.out_dir / "family_portfolio_diagnostics.csv", pd.DataFrame(family_portfolio_records))
    write_table(args.out_dir / "mechanism_diagnostics.csv", pd.DataFrame(mechanism_records))
    if fold_tables:
        write_table(args.out_dir / "fold_metrics.csv", pd.concat(fold_tables, ignore_index=True))
    if month_tables:
        write_table(args.out_dir / "month_metrics.csv", pd.concat(month_tables, ignore_index=True))
    if side_tables:
        write_table(args.out_dir / "side_metrics.csv", pd.concat(side_tables, ignore_index=True))
    if session_tables:
        write_table(args.out_dir / "session_metrics.csv", pd.concat(session_tables, ignore_index=True))
    if loss_cluster_tables:
        lib.deterministic_gzip_csv(args.out_dir / "loss_cluster_and_overlap_diagnostics.csv.gz", pd.concat(loss_cluster_tables, ignore_index=True, sort=False))
    lib.write_json(args.out_dir / "shortlist_decision.json", shortlist)
    lib.write_json(args.out_dir / "currency_contract_audit.json", {"status": "PASS_JPY_CURRENCY_CONTRACT", **prereg["monetary_contract"], "currency_mismatch_count": 0})
    lib.write_json(args.out_dir / "period_access_receipt.json", {
        "atlas_period": "2023-2024",
        "analysis_2020_2022_role": "ANALYSIS_PERIOD",
        "analysis_2020_2022_accessed": False,
        "analysis_2020_2022_confirmation_credit": False,
        "analysis_2020_2022_external_validation_credit": False,
        "analysis_2020_2022_not_accessed_reason": "Atlas scope is fixed to common-source 2023-2024 ranking.",
        "external_validation_2025_role": "UNSEEN_BINDING_EXTERNAL_VALIDATION_PERIOD",
        "external_validation_2025_accessed": False,
        "shortlist_is_research_prioritization_only": True,
    })
    full_equity_reason = str(pd.DataFrame(portfolio_records).iloc[0]["full_equity_reason"])
    result = {
        "schema_version": "usdjpy_csos_dukascopy_native_remaining_family_atlas_final_result_v1",
        "status": "ATLAS_COMPLETE_RESEARCH_PRIORITIZATION_ONLY",
        "program_id": lib.PROGRAM,
        "decision": shortlist["decision"],
        "research_start_sha": prereg["research_start_sha"],
        "research_execution_sha": args.research_sha,
        "core_reference_sha": args.core_sha,
        "run_id": args.run_id,
        "source_authority": source,
        "evaluated_family_count": len(family_comparison),
        "evaluated_variant_count": len(variant_comparison),
        "excluded_duplicate_family_count": prior_audit["excluded_duplicate_family_count"],
        "excluded_families": prior_audit["excluded_binding_closures"],
        "total_raw_signals": int(len(raw_signals)),
        "total_executable_trades": int(len(trades)),
        "old_atlas_target_events": int(len(old)),
        "shortlist": shortlist,
        "track_a_ranks": track_a_ranks,
        "track_b_ranks": track_b_ranks,
        "full_equity_status": "NOT_AVAILABLE",
        "full_equity_reason": full_equity_reason,
        "period_roles": prereg["period_roles"],
        "analysis_2020_2022_accessed": False,
        "analysis_2020_2022_confirmation_credit": False,
        "external_validation_2025_accessed": False,
        "family_contract_changed_after_period_clarification": False,
        "ranking_gate_changed_after_period_clarification": False,
        "source_changed_after_period_clarification": False,
        "candidate_freeze": False,
        "core_modified": False,
        "mt4_executed": False,
        "production_authorized": False,
        "live_authorized": False,
        "recurring_monitor_created": False,
    }
    lib.write_json(args.out_dir / "final_result.json", result)
    lib.write_json(args.out_dir / "research_program_update.json", {
        "program_id": lib.PROGRAM,
        "status": "COMPLETE",
        "decision": shortlist["decision"],
        "shortlist": shortlist,
        "atlas_period": "2023-2024",
        "analysis_2020_2022_role": "ANALYSIS_PERIOD_NOT_ACCESSED_IN_ATLAS",
        "external_validation_2025_role": "UNSEEN_BINDING_EXTERNAL_VALIDATION_NOT_ACCESSED",
        "candidate_freeze": False,
    })
    lib.write_json(args.out_dir / "research_memory_update.json", {
        "program_id": lib.PROGRAM,
        "memory_class": "CROSS_FAMILY_DISCOVERY_RESULT",
        "decision": shortlist["decision"],
        "shortlist": shortlist,
        "binding_source": "Dukascopy BI5 Bid/Ask Tick",
        "atlas_period": "2023-2024",
        "period_role_correction": "2020-2022 is analysis, not confirmation; 2025 remains the only binding unseen external validation.",
        "next_action": "Start a separate Hypothesis for the highest-priority shortlisted family, use 2020-2024 for analysis and candidate construction, freeze before 2025, then use 2025 only for binding external validation.",
    })
    make_human_report(args.out_dir / "human_report.md", result, variant_comparison, family_comparison, identity_summary)
    for path in [args.prereg, args.source_manifest, args.contract_catalog, args.prior_study_audit, args.period_role_clarification]:
        (args.out_dir / path.name).write_bytes(path.read_bytes())
    files = []
    for path in sorted(args.out_dir.iterdir()):
        if path.is_file() and path.name not in {"artifact_manifest.json", "PACKAGE_SHA256SUMS"}:
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": lib.sha256_file(path)})
    lib.write_json(args.out_dir / "artifact_manifest.json", {
        "schema_version": "usdjpy_csos_dukascopy_native_remaining_family_atlas_artifact_manifest_v1",
        "program_id": lib.PROGRAM,
        "decision": shortlist["decision"],
        "files": files,
        "analysis_2020_2022_accessed": False,
        "external_validation_2025_accessed": False,
        "candidate_freeze": False,
        "core_mt4_authorized": False,
        "production_authorized": False,
        "live_authorized": False,
    })
    files.append({"path": "artifact_manifest.json", "bytes": (args.out_dir / "artifact_manifest.json").stat().st_size, "sha256": lib.sha256_file(args.out_dir / "artifact_manifest.json")})
    (args.out_dir / "PACKAGE_SHA256SUMS").write_text("".join(f"{row['sha256']}  {row['path']}\n" for row in files), encoding="utf-8")
    print(json.dumps(lib.clean({
        "decision": shortlist["decision"],
        "track_a": None if shortlist["track_a"] is None else shortlist["track_a"]["variant_id"],
        "track_b": None if shortlist["track_b"] is None else shortlist["track_b"]["variant_id"],
        "mechanism_research_only": None if shortlist["mechanism_research_only"] is None else shortlist["mechanism_research_only"]["variant_id"],
        "families": len(family_comparison),
        "variants": len(variant_comparison),
        "trades": len(trades),
        "tick_count": source["tick_count"],
        "m15_bar_count": source["m15_bar_count"],
        "analysis_2020_2022_accessed": False,
        "external_validation_2025_accessed": False,
    }), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
