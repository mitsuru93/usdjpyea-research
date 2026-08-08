#!/usr/bin/env python3
from __future__ import annotations
from usdjpy_integration_001_support import *

def build_matrices(out, ctx):
    globals().update(ctx)
    availability = [
        {
            "slot": "N1", "study_id": "USDJPY-HYP-039", "candidate_id": "C1_SHORT_DUKASCOPY_NATIVE_16BAR_UNCHANGED",
            "formal_status": "ACTIVE_IMPLEMENTATION_NOT_COMPLETE", "availability": "PENDING_CANDIDATE_EVIDENCE",
            "evidence": "Research preregistration is merged; Core PR #505 exists but no merged/released formal candidate output was found.",
            "accepted_input": False, "blocking_fields": ["formal_decision", "common_trade_ledger", "validation_artifact_digest", "2025H1_result"],
        },
        {
            "slot": "N2", "study_id": "USDJPY-HYP-040", "candidate_id": "A_EXACT_EXECUTABLE_12BAR_UNCHANGED",
            "formal_status": "PREREGISTERED_ONLY", "availability": "PENDING_CANDIDATE_EVIDENCE",
            "evidence": "HYP-040 preregistration is on Research main; no immutable candidate output or 2025H1 result was found.",
            "accepted_input": False, "blocking_fields": ["Core_parity", "MT4_result", "common_trade_ledger", "validation_artifact_digest", "formal_decision"],
        },
        {
            "slot": "F", "study_id": "F05_V2", "candidate_id": None,
            "formal_status": "NO_SELECTED_CANDIDATE_OR_NO_CHANGE_DECISION_AVAILABLE", "availability": "PENDING_CANDIDATE_EVIDENCE",
            "evidence": "No completed F05 v2 selected candidate or formal no-change decision was found on merged main, immutable Release, or hash-pinned artifact.",
            "accepted_input": False, "blocking_fields": ["candidate_id_or_no_change", "formal_decision", "common_trade_ledger", "validation_artifact_digest"],
        },
        {
            "slot": "B", "study_id": "B02_V2", "candidate_id": None,
            "formal_status": "NO_SELECTED_CANDIDATE_OR_NO_CHANGE_DECISION_AVAILABLE", "availability": "PENDING_CANDIDATE_EVIDENCE",
            "evidence": "No completed B02 v2 selected candidate or formal no-change decision was found on merged main, immutable Release, or hash-pinned artifact.",
            "accepted_input": False, "blocking_fields": ["candidate_id_or_no_change", "formal_decision", "common_trade_ledger", "validation_artifact_digest"],
        },
    ]
    availability_df = pd.DataFrame(availability)
    availability_df.to_csv(out / "candidate_availability_matrix.csv", index=False, lineterminator="\n")
    write_json(out / "candidate_availability_matrix.json", availability)

    avail_map = {r["slot"]: bool(r["accepted_input"]) for r in availability}
    combo_rows = []
    for combo_id, components in requested_combinations():
        pending = [c for c in components if c in avail_map and not avail_map[c]]
        if combo_id == "BASELINE":
            classification = recovery_classification(h25_metrics, hist_metrics, h25_metrics, integrity_pass=True, margin_pass=True)
            combo_rows.append({
                "combination_id": combo_id, "components": "+".join(components), "status": "CALCULATED",
                "pending_components": "", "2023_2024_net_jpy": hist_metrics["net_jpy"], "2023_2024_pf": hist_metrics["profit_factor"],
                "2025H1_net_jpy": h25_metrics["net_jpy"], "2025H1_pf": h25_metrics["profit_factor"],
                "2025H1_tick_equity_dd_jpy": tick_authority["maximum_tick_equity_drawdown_jpy"],
                "2025H1_minimum_equity_jpy": tick_authority["minimum_equity_jpy"],
                "minimum_margin_level_percent": tick_authority["minimum_margin_level_percent"],
                "maximum_concurrent_positions": tick_authority["maximum_open_orders"],
                "maximum_concurrent_lots": tick_authority["maximum_open_lots"],
                "classification": classification, "formal_candidate_status": "BASELINE_AUTHORITY",
            })
        else:
            combo_rows.append({
                "combination_id": combo_id, "components": "+".join(components), "status": "NOT_CALCULATED_PENDING_CANDIDATE_EVIDENCE",
                "pending_components": "+".join(pending), "2023_2024_net_jpy": None, "2023_2024_pf": None,
                "2025H1_net_jpy": None, "2025H1_pf": None, "2025H1_tick_equity_dd_jpy": None,
                "2025H1_minimum_equity_jpy": None, "minimum_margin_level_percent": None,
                "maximum_concurrent_positions": None, "maximum_concurrent_lots": None,
                "classification": None, "formal_candidate_status": "PENDING_CANDIDATE_EVIDENCE",
            })
    combos = pd.DataFrame(combo_rows)
    combos.to_csv(out / "combination_matrix.csv", index=False, lineterminator="\n")
    write_json(out / "combination_matrix.json", combo_rows)

    # Non-additive exposure diagnostics plus additive strategy attribution.
    exposure = {r["exposure_bucket"]: {"trades": int(r["trades"]), "net_jpy": float(r["net_jpy"])} for r in h25_metrics["exposure_buckets"]}
    residual = {
        "period": "2025H1",
        "combination": "B02+F05 baseline",
        "remaining_net_loss_jpy": -20808.0,
        "additive_strategy_attribution": {
            "B02": -6964.0,
            "F05": -13844.0,
            "Short_Pullback": None,
            "Asian_Range_Sweep": None,
        },
        "exclusive_exposure_bucket_attribution": exposure,
        "transaction_cost": {
            "spread_cost_jpy": -float(len(h25) * 5.0),
            "basis": "463 trades × 0.5 pip fixed spread × JPY 10/pip",
            "commission_jpy": None,
            "swap_jpy": None,
            "gate": "STOP_COMPONENT_COMPLETE_COST_ATTRIBUTION_BECAUSE_COMMISSION_AND_SWAP_ARE_NULL",
        },
        "margin_restriction": {
            "blocked_entries": 0,
            "stopout_breached": False,
            "attributed_net_effect_jpy": 0.0,
        },
        "chronology_conflict": {
            "negative_holding_period_rows": h25_metrics["chronology_negative_holding_periods"],
            "trade_failures": case["trade_failure_count"],
            "decision_utc_trace": None,
            "gate": "STOP_DECISION_CHRONOLOGY_TRACE_BECAUSE_LEGACY_BASELINE_HAS_NO_DECISION_UTC_EVENT",
        },
        "required_improvement_to_zero_jpy": 20808.0,
        "strategy_specific_required_improvement_if_solved_independently": {
            "B02": 6964.0,
            "F05": 13844.0,
            "portfolio_total": 20808.0,
        },
        "interpretation": "Strategy attribution and exclusive exposure buckets are each internally additive, but they are different decompositions and must not be summed together.",
    }
    write_json(out / "residual_loss_decomposition.json", residual)

    comparison_rows = [
        {"period": "2023_2024", "combination_id": "BASELINE", "status": "CALCULATED", **{k: hist_metrics.get(k) for k in ["trades", "net_jpy", "profit_factor", "worst_1_business_day_jpy", "worst_5_business_days_jpy", "worst_20_business_days_jpy", "worst_calendar_month_jpy"]}},
        {"period": "2025H1", "combination_id": "BASELINE", "status": "CALCULATED", **{k: h25_metrics.get(k) for k in ["trades", "net_jpy", "profit_factor", "worst_1_business_day_jpy", "worst_5_business_days_jpy", "worst_20_business_days_jpy", "worst_calendar_month_jpy"]}},
    ]
    pd.DataFrame([comparison_rows[0]]).to_csv(out / "2023_2024_comparison.csv", index=False, lineterminator="\n")
    pd.DataFrame([comparison_rows[1]]).to_csv(out / "2025H1_comparison.csv", index=False, lineterminator="\n")

    risk = [{
        "combination_id": "BASELINE",
        "2023_2024_net_jpy": hist_metrics["net_jpy"],
        "2023_2024_pf": hist_metrics["profit_factor"],
        "2025H1_net_jpy": h25_metrics["net_jpy"],
        "2025H1_pf": h25_metrics["profit_factor"],
        "2025H1_tick_dd_jpy": tick_authority["maximum_tick_equity_drawdown_jpy"],
        "2025H1_min_equity_jpy": tick_authority["minimum_equity_jpy"],
        "2025H1_worst_20d_jpy": h25_metrics["worst_20_business_days_jpy"],
        "minimum_margin_level_percent": tick_authority["minimum_margin_level_percent"],
        "strategy_concentration": "F05 accounts for 66.53% of 2025H1 net loss",
        "implementation_complexity": "LOW_EXISTING_BASELINE",
        "source_broker_portability": "Rakuten MT4 authority; 2023 deterministic historical lineage",
        "formal_status": "BASELINE_AUTHORITY",
        "classification": "NO_RECOVERY",
    }]
    pd.DataFrame(risk).to_csv(out / "risk_tradeoff_matrix.csv", index=False, lineterminator="\n")
    return {"availability": availability, "availability_df": availability_df, "combos": combos, "residual": residual, "risk": risk}
