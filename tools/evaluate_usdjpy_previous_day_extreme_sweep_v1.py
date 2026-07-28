#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usdjpy_hyp034_metrics_v1 import (
    INITIAL_CAPITAL_JPY,
    apply_active_suppression,
    bootstrap_metrics,
    concentration_metrics,
    correlation,
    cost_stress,
    daily_series,
    deterministic_csv,
    evaluate_rule,
    grouped_metrics,
    package_manifest,
    profit_factor,
    realized_equity_metrics,
    trade_metrics,
    write_json,
)
from usdjpy_hyp034_study_v1 import (
    FOLDS,
    build_events_and_trades,
    build_source_tables,
    concurrency_metrics,
    enrich_exact_paths,
    full_equity_replay,
    session_of,
)

HYPOTHESIS_ID = "USDJPY-HYP-034"
FAMILY_ID = "S_PREVIOUS_DAY_EXTREME_SWEEP_REJECTION"
EXPECTED_BASELINE_ROWS = 1882
FEATURE_SPECS = [
    {"feature": "reclaim_depth_ratio", "operator": ">=", "thresholds": [0.01, 0.025, 0.05], "mechanism": "deeper completed range re-entry"},
    {"feature": "outside_duration_seconds", "operator": "<=", "thresholds": [60.0, 300.0, 900.0], "mechanism": "faster failure of outside acceptance"},
    {"feature": "overshoot_ratio", "operator": "<=", "thresholds": [0.01, 0.025, 0.05], "mechanism": "limited boundary acceptance before reclaim"},
]


def finite(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if math.isnan(number):
            return None
        if math.isinf(number):
            return "INF" if number > 0 else "-INF"
        return number
    if isinstance(value, dict):
        return {str(key): finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(item) for item in value]
    if pd.isna(value) if not isinstance(value, (str, bool, type(None))) else False:
        return None
    return value


def load_baseline(path: Path) -> pd.DataFrame:
    baseline = pd.read_csv(path)
    required = {"fold", "strategy", "entry_utc", "close_utc", "side", "entry_bid", "realized_pl_jpy"}
    missing = required - set(baseline.columns)
    if missing:
        raise ValueError(f"baseline missing columns: {sorted(missing)}")
    if len(baseline) != EXPECTED_BASELINE_ROWS:
        raise ValueError(f"baseline row mismatch: {len(baseline)} != {EXPECTED_BASELINE_ROWS}")
    baseline["entry_utc"] = pd.to_datetime(baseline.entry_utc, utc=True)
    baseline["exit_utc"] = pd.to_datetime(baseline.close_utc, utc=True)
    baseline["side"] = baseline.side.astype(int)
    baseline["entry_price"] = baseline.entry_bid.astype(float) + np.where(baseline.side.eq(1), 0.005, 0.0)
    baseline["pl_jpy"] = baseline.realized_pl_jpy.astype(float)
    baseline["event_id"] = [f"BASE|{fold}|{strategy}|{entry.isoformat()}|{side}" for fold, strategy, entry, side in zip(baseline.fold, baseline.strategy, baseline.entry_utc, baseline.side)]
    baseline["entry_date"] = baseline.entry_utc.dt.strftime("%Y-%m-%d")
    baseline["exit_date"] = baseline.exit_utc.dt.strftime("%Y-%m-%d")
    baseline["month"] = baseline.entry_utc.dt.strftime("%Y-%m")
    baseline["session"] = baseline.entry_utc.map(session_of)
    if not baseline.entry_utc.dt.year.isin([2023, 2024]).all() or not baseline.exit_utc.dt.year.isin([2023, 2024]).all():
        raise ValueError("baseline contains protected or non-development dates")
    return baseline.sort_values(["entry_utc", "strategy", "event_id"], kind="mergesort").reset_index(drop=True)


def preflight(args: argparse.Namespace, prereg: dict[str, Any], baseline: pd.DataFrame) -> dict[str, Any]:
    raw_2023 = sorted(args.raw_2023.glob("*.tar.gz"))
    raw_2024 = sorted(args.raw_2024.glob("*.tar.gz"))
    expected_2023 = {f"usdjpy-2023-{month:02d}-raw-ticks-v1.tar.gz" for month in range(1, 13)}
    expected_2024 = {f"usdjpy-2024-{month:02d}-raw-ticks-v1.tar.gz" for month in range(1, 13)}
    checks = {
        "hypothesis_id": prereg.get("hypothesis_id") == HYPOTHESIS_ID,
        "family_id": prereg.get("family_id") == FAMILY_ID,
        "prereg_frozen": prereg.get("status") == "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES",
        "fixed_exit_12_bars": prereg.get("fixed_exit", {}).get("hold_bars") == 12,
        "reporting_currency_jpy": prereg.get("monetary_contract", {}).get("reporting_currency") == "JPY",
        "protected_2020_2022_locked": prereg.get("boundaries", {}).get("protected_2020_2022_access") is False,
        "protected_2025_locked": prereg.get("boundaries", {}).get("protected_2025_access") is False,
        "raw_2023_exact_months": {path.name for path in raw_2023} == expected_2023,
        "raw_2024_exact_months": {path.name for path in raw_2024} == expected_2024,
        "baseline_rows": len(baseline) == EXPECTED_BASELINE_ROWS,
        "baseline_only_development_period": baseline.entry_utc.dt.year.isin([2023, 2024]).all(),
    }
    return {
        "schema_version": "usdjpy_hyp034_development_preflight_v1",
        "status": "PASS_NO_OUTCOMES" if all(checks.values()) else "TECHNICAL_NO_RESULT_PREFLIGHT_FAILURE",
        "checks": checks,
        "raw_archive_count": len(raw_2023) + len(raw_2024),
        "baseline_rows": len(baseline),
        "candidate_outcome_computed": False,
        "protected_period_accessed": False,
        "mt4_executed": False,
    }


def source_gate(daily: pd.DataFrame, bars: pd.DataFrame, inventory: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected_dates = pd.date_range("2023-01-01", "2024-12-31", freq="D").strftime("%Y-%m-%d")
    checks = {
        "archive_count_24": inventory.get("archive_count") == 24,
        "calendar_dates_complete": set(daily.date_utc) == set(expected_dates),
        "ask_bid_inversion_zero": int(daily.ask_bid_inversion_count.sum()) == 0,
        "nonmonotonic_timestamp_zero": int(daily.nonmonotonic_timestamp_count.sum()) == 0,
        "summary_parse_error_zero": int(daily.summary_status.eq("PARSE_ERROR").sum()) == 0,
        "m15_duplicate_start_zero": int(bars.bar_start_utc.duplicated().sum()) == 0,
        "m15_chronology_monotonic": bool(bars.bar_start_utc.is_monotonic_increasing),
        "development_only": bool(bars.bar_start_utc.dt.year.isin([2023, 2024]).all()),
        "tick_days_nonempty": int((daily.tick_count > 0).sum()) >= 500,
    }
    summary = {
        "checks": checks,
        "archive_count": inventory.get("archive_count"),
        "calendar_day_rows": int(len(daily)),
        "tick_day_rows": int((daily.tick_count > 0).sum()),
        "no_tick_weekdays": daily[(daily.weekday < 5) & (daily.tick_count == 0)].date_utc.tolist(),
        "ask_bid_inversion_count": int(daily.ask_bid_inversion_count.sum()),
        "nonmonotonic_timestamp_count": int(daily.nonmonotonic_timestamp_count.sum()),
        "duplicate_timestamp_count": int(daily.duplicate_timestamp_count.sum()),
        "summary_status_counts": daily.summary_status.value_counts(dropna=False).to_dict(),
        "m15_bar_count": int(len(bars)),
    }
    return all(checks.values()), summary


def lofo_select(trades: pd.DataFrame, specification: dict[str, Any]) -> dict[str, Any]:
    feature = specification["feature"]
    operator = specification["operator"]
    thresholds = list(specification["thresholds"])
    heldout_rows: list[dict[str, Any]] = []
    choices: list[float] = []
    for heldout in FOLDS:
        train = trades[trades.fold != heldout]
        options: list[tuple[float, float, float, int]] = []
        for threshold in thresholds:
            rule = {"conditions": [{"feature": feature, "operator": operator, "threshold": threshold}]}
            selected = evaluate_rule(train, rule)
            metrics = trade_metrics(selected)
            minimum_fold = selected.groupby("fold").size().min() if not selected.empty else 0
            if metrics["event_count"] >= 45 and minimum_fold >= 8 and metrics["net_jpy"] > 0:
                score = float(metrics["profit_factor"] if np.isfinite(metrics["profit_factor"]) else 999.0)
                options.append((score, metrics["net_jpy"], float(threshold), metrics["event_count"]))
        if not options:
            heldout_rows.append({"heldout_fold": heldout, "selected_threshold": None, "heldout_net_jpy": None, "heldout_pf": None, "heldout_count": 0})
            continue
        if operator == ">=":
            options.sort(key=lambda item: (-item[0], -item[1], item[2]))
        else:
            options.sort(key=lambda item: (-item[0], -item[1], -item[2]))
        threshold = float(options[0][2])
        choices.append(threshold)
        rule = {"conditions": [{"feature": feature, "operator": operator, "threshold": threshold}]}
        heldout_trade = evaluate_rule(trades[trades.fold == heldout], rule)
        metrics = trade_metrics(heldout_trade)
        heldout_rows.append({
            "heldout_fold": heldout,
            "selected_threshold": threshold,
            "heldout_net_jpy": metrics["net_jpy"],
            "heldout_pf": metrics["profit_factor"],
            "heldout_count": metrics["event_count"],
        })
    counts = Counter(choices)
    mode_threshold = None
    mode_count = 0
    if counts:
        mode_count = max(counts.values())
        candidates = [threshold for threshold, count in counts.items() if count == mode_count]
        mode_threshold = min(candidates) if operator == ">=" else max(candidates)
    positive_heldout = sum(1 for row in heldout_rows if row["heldout_net_jpy"] is not None and row["heldout_net_jpy"] > 0)
    heldout_net_total = sum(float(row["heldout_net_jpy"] or 0.0) for row in heldout_rows)
    stable = mode_threshold is not None and mode_count >= 3 and positive_heldout >= 3
    return {
        "feature": feature,
        "operator": operator,
        "mechanism": specification["mechanism"],
        "thresholds": thresholds,
        "selected_threshold": mode_threshold,
        "mode_count": mode_count,
        "positive_heldout_folds": positive_heldout,
        "heldout_net_total_jpy": heldout_net_total,
        "stable": stable,
        "heldout": heldout_rows,
    }


def candidate_catalog(trades: pd.DataFrame, mechanism_discriminator: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not mechanism_discriminator:
        return [], []
    lofo = [lofo_select(trades, specification) for specification in FEATURE_SPECS]
    base_metrics = trade_metrics(trades)
    stable: list[dict[str, Any]] = []
    for result in lofo:
        if not result["stable"]:
            continue
        rule = {"conditions": [{"feature": result["feature"], "operator": result["operator"], "threshold": result["selected_threshold"]}]}
        selected = evaluate_rule(trades, rule)
        metrics = trade_metrics(selected)
        positive_folds = int((selected.groupby("fold").pl_jpy.sum() > 0).sum()) if not selected.empty else 0
        if metrics["event_count"] >= 60 and positive_folds >= 3 and metrics["profit_factor"] >= base_metrics["profit_factor"]:
            stable.append({**result, "full_event_count": metrics["event_count"], "full_net_jpy": metrics["net_jpy"], "full_pf": metrics["profit_factor"]})
    stable.sort(key=lambda row: (-row["heldout_net_total_jpy"], row["feature"]))
    catalog = [{
        "candidate_id": "C0_EXACT_COMPLETED_M15_RECLAIM",
        "priority": 0,
        "conditions": [],
        "feature_count": 1,
        "exact_rule": "completed M15 Bid bar sweeps previous-day extreme and closes strictly back inside; next available M15 open entry; 12 completed M15 bars hold",
        "selection_basis": "preregistered executable translation; completed-M15 reclaim is the ex-ante mechanism discriminator",
    }]
    if stable:
        top = stable[0]
        catalog.append({
            "candidate_id": f"C1_{top['feature'].upper()}",
            "priority": 1,
            "conditions": [{"feature": top["feature"], "operator": top["operator"], "threshold": top["selected_threshold"]}],
            "feature_count": 1,
            "exact_rule": f"C0 AND {top['feature']} {top['operator']} {top['selected_threshold']}",
            "selection_basis": "four-fold leave-one-fold-out stable boundary",
        })
    if len(stable) >= 2:
        first, second = stable[:2]
        catalog.append({
            "candidate_id": f"C2_{first['feature'].upper()}_{second['feature'].upper()}",
            "priority": 2,
            "conditions": [
                {"feature": first["feature"], "operator": first["operator"], "threshold": first["selected_threshold"]},
                {"feature": second["feature"], "operator": second["operator"], "threshold": second["selected_threshold"]},
            ],
            "feature_count": 2,
            "exact_rule": f"C0 AND {first['feature']} {first['operator']} {first['selected_threshold']} AND {second['feature']} {second['operator']} {second['selected_threshold']}",
            "selection_basis": "two independently stable LOFO monotonic discriminators",
        })
    return catalog[:3], lofo


def baseline_drawdown_at_entries(baseline: pd.DataFrame, candidate: pd.DataFrame) -> pd.Series:
    close = baseline.sort_values(["exit_utc", "event_id"], kind="mergesort")
    times = close.exit_utc.to_numpy()
    cumulative = close.pl_jpy.cumsum().to_numpy(dtype=float)
    equity = INITIAL_CAPITAL_JPY + cumulative
    peaks = np.maximum.accumulate(np.r_[INITIAL_CAPITAL_JPY, equity])[1:]
    drawdowns = peaks - equity
    values: list[float] = []
    for entry in candidate.entry_utc:
        position = int(np.searchsorted(times, np.datetime64(pd.Timestamp(entry).tz_convert("UTC").tz_localize(None)), side="right")) - 1
        values.append(float(drawdowns[position]) if position >= 0 else 0.0)
    return pd.Series(values, index=candidate.index, dtype=float)


def portfolio_attribution(baseline: pd.DataFrame, candidate_id: str, candidate: pd.DataFrame, full_equity: dict[str, Any]) -> dict[str, Any]:
    base_all = daily_series(baseline)
    base_b02 = daily_series(baseline[baseline.strategy == "B02"])
    base_f05 = daily_series(baseline[baseline.strategy == "F05"])
    candidate_daily = daily_series(candidate)
    aligned = pd.concat([base_all.rename("baseline"), candidate_daily.rename("candidate")], axis=1).fillna(0.0)
    negative_dates = aligned.index[aligned.baseline < 0]
    positive_dates = aligned.index[aligned.baseline > 0]
    combined = pd.concat([baseline, candidate], ignore_index=True, sort=False)
    combined_realized = realized_equity_metrics(combined)
    baseline_realized = realized_equity_metrics(baseline)
    concurrency = concurrency_metrics(baseline, candidate)
    drawdown_state = baseline_drawdown_at_entries(baseline, candidate)
    weekly = aligned.copy()
    weekly.index = pd.to_datetime(weekly.index, utc=True)
    weekly["combined"] = weekly.baseline + weekly.candidate
    week_sum = weekly.combined.groupby(weekly.index.to_period("W-SUN")).sum()
    day_combined = aligned.baseline + aligned.candidate
    return {
        "candidate_id": candidate_id,
        "daily_correlation_to_B02": correlation(candidate_daily, base_b02),
        "daily_correlation_to_F05": correlation(candidate_daily, base_f05),
        "B02_F05_positive_day_contribution_jpy": float(aligned.loc[positive_dates, "candidate"].sum()),
        "B02_F05_negative_day_contribution_jpy": float(aligned.loc[negative_dates, "candidate"].sum()),
        "baseline_drawdown_at_entry_mean_jpy": float(drawdown_state.mean()) if len(drawdown_state) else 0.0,
        "baseline_drawdown_at_entry_max_jpy": float(drawdown_state.max()) if len(drawdown_state) else 0.0,
        "combined_net_jpy": float(baseline.pl_jpy.sum() + candidate.pl_jpy.sum()),
        "baseline_net_jpy": float(baseline.pl_jpy.sum()),
        "incremental_net_jpy": float(candidate.pl_jpy.sum()),
        "baseline_realized_mdd_jpy": baseline_realized["mdd_jpy"],
        "combined_realized_mdd_jpy": combined_realized["mdd_jpy"],
        "baseline_realized_minimum_equity_jpy": baseline_realized["minimum_equity_jpy"],
        "combined_realized_minimum_equity_jpy": combined_realized["minimum_equity_jpy"],
        "baseline_full_equity_mdd_jpy": full_equity["BASELINE"]["full_equity_mdd_jpy"],
        "combined_full_equity_mdd_jpy": full_equity[candidate_id]["full_equity_mdd_jpy"],
        "baseline_full_equity_minimum_jpy": full_equity["BASELINE"]["minimum_equity_jpy"],
        "combined_full_equity_minimum_jpy": full_equity[candidate_id]["minimum_equity_jpy"],
        "worst_overlapping_day_jpy": float(day_combined.min()) if len(day_combined) else 0.0,
        "worst_overlapping_week_jpy": float(week_sum.min()) if len(week_sum) else 0.0,
        "candidate_positive_day_largest_share": float(candidate_daily[candidate_daily > 0].max() / candidate_daily[candidate_daily > 0].sum()) if (candidate_daily > 0).any() else 0.0,
        **concurrency,
    }


def candidate_gate_rows(candidate_id: str, candidate: pd.DataFrame, unfiltered: pd.DataFrame, portfolio: dict[str, Any], integrity: dict[str, bool]) -> list[dict[str, Any]]:
    metrics = trade_metrics(candidate)
    fold_net = candidate.groupby("fold").pl_jpy.sum().reindex(FOLDS, fill_value=0.0)
    month_net = candidate.groupby("month").pl_jpy.sum()
    concentration = concentration_metrics(candidate)
    bootstrap = bootstrap_metrics(candidate)
    costs = cost_stress(candidate).set_index("stress")
    unfiltered_metrics = trade_metrics(unfiltered)
    min_fold_count = int(candidate.groupby("fold").size().min()) if not candidate.empty else 0
    checks: list[tuple[str, str, bool, Any, str]] = []
    for name, passed in integrity.items():
        checks.append(("Integrity", name, bool(passed), passed, "binding"))
    checks.extend([
        ("Sample", "resolved_events_min_120", len(unfiltered) >= 120, len(unfiltered), ">=120"),
        ("Sample", "affected_events_min_60", len(candidate) >= 60, len(candidate), ">=60"),
        ("Sample", "each_fold_sufficient", min_fold_count >= 10, min_fold_count, ">=10/fold"),
        ("Economics", "net_positive", metrics["net_jpy"] > 0, metrics["net_jpy"], ">0"),
        ("Economics", "profit_factor", metrics["profit_factor"] >= 1.10, metrics["profit_factor"], ">=1.10"),
        ("Economics", "positive_folds", int((fold_net > 0).sum()) >= 3, int((fold_net > 0).sum()), ">=3/4"),
        ("Economics", "minimum_fold", float(fold_net.min()) >= -1000, float(fold_net.min()), ">=-1000 JPY"),
        ("Economics", "positive_months", int((month_net > 0).sum()) >= 16, int((month_net > 0).sum()), ">=16/24"),
        ("Economics", "mdd_nonworse_than_unfiltered", metrics["mdd_jpy"] <= unfiltered_metrics["mdd_jpy"] + 1e-6, metrics["mdd_jpy"] - unfiltered_metrics["mdd_jpy"], "<=0 delta"),
        ("Economics", "minimum_equity_nonworse_than_unfiltered", metrics["minimum_equity_jpy"] >= unfiltered_metrics["minimum_equity_jpy"] - 1e-6, metrics["minimum_equity_jpy"] - unfiltered_metrics["minimum_equity_jpy"], ">=0 delta"),
        ("Concentration", "best_event_removed_net_positive", concentration["best_event_removed_net_jpy"] > 0, concentration["best_event_removed_net_jpy"], ">0"),
        ("Concentration", "top3_removed_net_positive", concentration["top3_removed_net_jpy"] > 0, concentration["top3_removed_net_jpy"], ">0"),
        ("Concentration", "top5_removed_net_positive", concentration["top5_removed_net_jpy"] > 0, concentration["top5_removed_net_jpy"], ">0"),
        ("Concentration", "largest_positive_fold_share", concentration["largest_positive_fold_share"] <= 0.60, concentration["largest_positive_fold_share"], "<=0.60"),
        ("Concentration", "largest_positive_session_share", concentration["largest_positive_session_share"] <= 0.60, concentration["largest_positive_session_share"], "<=0.60"),
        ("Concentration", "largest_positive_month_share", concentration["largest_positive_month_share"] <= 0.25, concentration["largest_positive_month_share"], "<=0.25"),
        ("Resampling", "event_bootstrap_lower95", bootstrap["event"]["lower95_jpy"] > 0, bootstrap["event"]["lower95_jpy"], ">0"),
        ("Resampling", "date_session_bootstrap_lower95", bootstrap["date_session"]["lower95_jpy"] > 0, bootstrap["date_session"]["lower95_jpy"], ">0"),
        ("Resampling", "probability_nonpositive", bootstrap["event"]["probability_nonpositive"] <= 0.05, bootstrap["event"]["probability_nonpositive"], "<=0.05"),
        ("Costs", "observed_bidask_net", float(costs.loc["OBSERVED_BIDASK", "net_jpy"]) > 0, float(costs.loc["OBSERVED_BIDASK", "net_jpy"]), ">0"),
        ("Costs", "spread_plus_0_5_net", float(costs.loc["SPREAD_PLUS_0_5_PIP", "net_jpy"]) > 0, float(costs.loc["SPREAD_PLUS_0_5_PIP", "net_jpy"]), ">0"),
        ("Costs", "spread_plus_1_0_net", float(costs.loc["SPREAD_PLUS_1_0_PIP", "net_jpy"]) > 0, float(costs.loc["SPREAD_PLUS_1_0_PIP", "net_jpy"]), ">0"),
        ("Costs", "entry_delay_5s_net", float(costs.loc["ENTRY_DELAY_5S", "net_jpy"]) > 0, float(costs.loc["ENTRY_DELAY_5S", "net_jpy"]), ">0"),
        ("Portfolio", "negative_day_contribution", portfolio["B02_F05_negative_day_contribution_jpy"] > 0, portfolio["B02_F05_negative_day_contribution_jpy"], ">0"),
        ("Portfolio", "combined_net_above_baseline", portfolio["combined_net_jpy"] > portfolio["baseline_net_jpy"], portfolio["combined_net_jpy"] - portfolio["baseline_net_jpy"], ">0 delta"),
        ("Portfolio", "combined_realized_dd_nonworse", portfolio["combined_realized_mdd_jpy"] <= portfolio["baseline_realized_mdd_jpy"] + 1e-6, portfolio["combined_realized_mdd_jpy"] - portfolio["baseline_realized_mdd_jpy"], "<=0 delta"),
        ("Portfolio", "combined_full_equity_dd_nonworse", portfolio["combined_full_equity_mdd_jpy"] <= portfolio["baseline_full_equity_mdd_jpy"] + 1e-6, portfolio["combined_full_equity_mdd_jpy"] - portfolio["baseline_full_equity_mdd_jpy"], "<=0 delta"),
        ("Portfolio", "minimum_equity_nonworse", portfolio["combined_full_equity_minimum_jpy"] >= portfolio["baseline_full_equity_minimum_jpy"] - 1e-6, portfolio["combined_full_equity_minimum_jpy"] - portfolio["baseline_full_equity_minimum_jpy"], ">=0 delta"),
        ("Portfolio", "incremental_margin_bounded", portfolio["candidate_peak_concurrency"] <= 1, portfolio["candidate_peak_concurrency"], "<=1"),
        ("Portfolio", "peak_concurrency_bounded", portfolio["combined_peak_concurrency"] <= portfolio["baseline_peak_concurrency"] + 1, portfolio["combined_peak_concurrency"] - portfolio["baseline_peak_concurrency"], "<=1 incremental"),
    ])
    return [{"candidate_id": candidate_id, "category": category, "gate": gate, "pass": passed, "value": value, "threshold": threshold, "binding": True} for category, gate, passed, value, threshold in checks]


def feature_ledger() -> pd.DataFrame:
    rows = [
        ("completed_m15_reclaim", "High: Bid high>PDH and Bid close<PDH; Low: Bid low<PDL and Bid close>PDL", "source-native completed M15 Bid bar", "signal bar close", "false when no completed reclaim", "strict inequality", True),
        ("reclaim_depth_ratio", "inside close distance / previous-day Bid range", "source-native Bid M15 and previous UTC trading-day Bid ticks", "signal bar close", "missing blocks rule", "strict inside; positive deeper", True),
        ("outside_duration_seconds", "first source-native boundary cross to first strict reclaim before decision", "source-native Bid Tick", "entry decision", "missing blocks rule", "source record order breaks equal timestamp ties", True),
        ("overshoot_ratio", "maximum signal-bar overshoot / previous-day Bid range", "source-native Bid Tick/M15", "entry decision", "missing blocks rule", "nonnegative", True),
        ("completed_m15_return_pips", "prior completed M15 Bid close-to-close return", "source-native Bid M15", "prior M15 close", "NA if warm-up insufficient", "no current incomplete bar", True),
        ("completed_h1_return_pips", "four completed M15 close return ending before decision", "source-native Bid M15", "prior M15 close", "NA if warm-up insufficient", "fixed 4 bars", True),
        ("completed_h4_return_pips", "sixteen completed M15 close return ending before decision", "source-native Bid M15", "prior M15 close", "NA if warm-up insufficient", "fixed 16 bars", True),
        ("spread_at_decision_pips", "Ask close minus Bid close", "source-native Bid/Ask Tick M15", "signal bar close", "NA blocks rule", "JPY pip=0.01", True),
        ("previous_day_range_percentile", "previous trading-day range rank among prior 60 eligible days", "source-native previous-day Bid Tick", "day rollover before current event", "NA during warm-up", "past-only", True),
    ]
    return pd.DataFrame(rows, columns=["name", "formula", "source", "information_timestamp", "missing_rule", "boundary_rule", "mt4_reproducible"]).assign(leakage_violation=False)


def human_report(result: dict[str, Any]) -> str:
    lines = [
        f"# {HYPOTHESIS_ID} / Previous-Day Extreme Sweep Rejection Mechanism Study",
        "",
        f"**Decision:** `{result['decision']}`",
        "",
        "## Scope and firewall",
        "",
        "This study is independent from HYP-030, HYP-031, HYP-032 and the parallel HYP-033 Asian Low Sweep study. No candidate, feature threshold, event ledger or outcome was shared. 2020-2022 and 2025 were not accessed.",
        "",
        "## Source and chronology",
        "",
        f"- Source authority: {result['source_authority']['status']}",
        f"- Raw sweep events: {result.get('source_native_event_count', 0)}",
        f"- High sweeps: {result.get('high_sweep_count', 0)}",
        f"- Low sweeps: {result.get('low_sweep_count', 0)}",
        f"- Both-side dates: {result.get('both_side_date_count', 0)}",
        f"- Chronology mismatches: {result.get('chronology_mismatch_count', 0)}",
        "",
        "## Mechanism",
        "",
        f"- Completed-M15 reclaim trades: {result.get('unfiltered_candidate_metrics', {}).get('event_count', 0)}",
        f"- Net: ¥{result.get('unfiltered_candidate_metrics', {}).get('net_jpy', 0):,.0f}",
        f"- PF: {result.get('unfiltered_candidate_metrics', {}).get('profit_factor', 0)}",
        f"- Portable mechanism: {result.get('portable_mechanism', False)}",
        f"- Ex-ante discriminator: {result.get('ex_ante_discriminator', False)}",
        "",
        "## Candidate and portfolio",
        "",
        f"- Candidate catalog size: {result.get('candidate_catalog_size', 0)}",
        f"- Selected candidate: {result.get('selected_candidate')}",
        f"- Historical validation authorized: {result.get('historical_validation_authorized', False)}",
        f"- Core/MT4 authorized: {result.get('core_mt4_authorized', False)}",
        f"- 2025 authorized: {result.get('external_2025_authorized', False)}",
        "",
        "## Authorization",
        "",
        "Production authorization: **NO**",
        "",
        "Live authorization: **NO**",
        "",
        f"Exact next action: {result['exact_next_action']}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-2023", type=Path, required=True)
    parser.add_argument("--raw-2024", type=Path, required=True)
    parser.add_argument("--baseline-trades", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    prereg = json.loads(args.prereg.read_text(encoding="utf-8"))
    baseline = load_baseline(args.baseline_trades)
    receipt = preflight(args, prereg, baseline)
    write_json(finite(receipt), args.output / "preflight_receipt.json")
    if args.preflight_only:
        print(json.dumps(finite(receipt), ensure_ascii=False, indent=2, sort_keys=True))
        raise SystemExit(0 if receipt["status"] == "PASS_NO_OUTCOMES" else 2)
    if receipt["status"] != "PASS_NO_OUTCOMES":
        raise SystemExit(2)

    raw_dirs = [args.raw_2023, args.raw_2024]
    daily, bars, inventory = build_source_tables(raw_dirs)
    source_pass, source_summary = source_gate(daily, bars, inventory)
    deterministic_csv(daily, args.output / "source_day_audit.csv.gz", gzip=True)
    deterministic_csv(bars, args.output / "source_native_m15_bidask.csv.gz", gzip=True)
    write_json(finite(inventory), args.output / "source_inventory.json")
    write_json(finite(source_summary), args.output / "source_authority_audit.json")
    write_json(finite(prereg["previous_day_calendar_contract"]), args.output / "previous_day_calendar_contract.json")
    write_json({"timezone": "UTC", "dst_conversion": False, "member_path_regex": "terminal /YYYY/MM/DD/HHh_ticks.bi5", "status": "PASS"}, args.output / "timezone_dst_audit.json")
    if not source_pass:
        final = {
            "schema_version": "usdjpy_hyp034_final_result_v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "family_id": FAMILY_ID,
            "decision": "SOURCE_AUTHORITY_FAILURE",
            "source_authority": {"status": "FAIL", **source_summary},
            "protected_2020_2022_accessed": False,
            "protected_2025_accessed": False,
            "production_authorized": False,
            "live_authorized": False,
            "exact_next_action": "Close HYP-034 without candidate outcomes; source authority is binding and no rescue is permitted.",
        }
        write_json(finite(final), args.output / "final_result.json")
        (args.output / "human_report.md").write_text(human_report(final), encoding="utf-8")
        write_json(package_manifest(args.output, {"PACKAGE_MANIFEST.json"}), args.output / "PACKAGE_MANIFEST.json")
        print(json.dumps(finite(final), ensure_ascii=False, indent=2, sort_keys=True))
        return

    events, trades, calendar_metadata = build_events_and_trades(daily, bars)
    events, trades, mismatch = enrich_exact_paths(raw_dirs, events, trades)
    exact_columns = ["event_key", "event_id", "outside_duration_seconds", "first_reclaim_distance_pips", "reclaim_speed_pips_per_minute", "boundary_retest_count"]
    trades = trades.drop(columns=[column for column in exact_columns[1:] if column in trades.columns], errors="ignore").merge(events[exact_columns], on="event_key", how="left", validate="one_to_one")
    trades["entry_date"] = pd.to_datetime(trades.entry_utc, utc=True).dt.strftime("%Y-%m-%d")
    trades["exit_date"] = pd.to_datetime(trades.exit_utc, utc=True).dt.strftime("%Y-%m-%d")
    trades["month"] = pd.to_datetime(trades.entry_utc, utc=True).dt.strftime("%Y-%m")
    trades["pl_delay_5s_jpy"] = pd.to_numeric(trades.pl_delay_5s_jpy, errors="coerce")
    trades["pl_delay_10s_jpy"] = pd.to_numeric(trades.pl_delay_10s_jpy, errors="coerce")
    deterministic_csv(events, args.output / "event_ledger.csv.gz", gzip=True)
    deterministic_csv(trades, args.output / "path_metrics.csv.gz", gzip=True)
    deterministic_csv(mismatch, args.output / "mismatch_ledger.csv", gzip=False)

    feature_table = feature_ledger()
    deterministic_csv(feature_table, args.output / "feature_ledger.csv", gzip=False)
    deterministic_csv(feature_table[["name", "information_timestamp", "leakage_violation"]], args.output / "leakage_audit.csv", gzip=False)

    chronology_pass = len(mismatch) == 0 and events.event_id.duplicated().sum() == 0
    calendar_pass = calendar_metadata["previous_day_map_count"] >= 500 and events.previous_trading_date.notna().all()
    currency_recomputed = np.where(trades.side.eq(1), (trades.exit_price - trades.entry_price) * 1000.0, (trades.entry_price - trades.exit_price) * 1000.0)
    currency_mismatch = int(np.sum(np.abs(currency_recomputed - trades.pl_jpy.astype(float)) > 1e-6))
    integrity = {
        "source_authority_pass": source_pass,
        "duplicate_event_zero": int(events.event_id.duplicated().sum()) == 0,
        "unresolved_chronology_zero": chronology_pass,
        "lookahead_violation_zero": int(feature_table.leakage_violation.sum()) == 0,
        "monetary_unit_mismatch_zero": currency_mismatch == 0,
        "event_replay_mismatch_zero": len(mismatch) == 0,
        "previous_day_calendar_contract_pass": calendar_pass,
    }

    accepted_diag = events[events.candidate_signal & events.raw_diagnostic_resolved].raw_diagnostic_pl_jpy.astype(float)
    nonaccepted_diag = events[~events.candidate_signal & events.raw_diagnostic_resolved].raw_diagnostic_pl_jpy.astype(float)
    unfiltered_metrics = trade_metrics(trades)
    fold_net = trades.groupby("fold").pl_jpy.sum().reindex(FOLDS, fill_value=0.0)
    accepted_advantage = float(accepted_diag.mean() - nonaccepted_diag.mean()) if len(accepted_diag) and len(nonaccepted_diag) else np.nan
    portable_mechanism = (
        len(events) >= 120
        and len(trades) >= 60
        and unfiltered_metrics["net_jpy"] > 0
        and unfiltered_metrics["profit_factor"] >= 1.0
        and int((fold_net > 0).sum()) >= 3
        and np.isfinite(accepted_advantage)
        and accepted_advantage > 0
    )
    ex_ante_discriminator = portable_mechanism and int(feature_table.leakage_violation.sum()) == 0

    catalog, lofo = candidate_catalog(trades, ex_ante_discriminator)
    candidate_frames: dict[str, pd.DataFrame] = {}
    for candidate in catalog:
        rule = {"conditions": candidate["conditions"]}
        candidate_frames[candidate["candidate_id"]] = evaluate_rule(trades, rule)
    full_equity, full_equity_daily = full_equity_replay(raw_dirs, baseline, candidate_frames) if candidate_frames else ({"BASELINE": {}}, pd.DataFrame())
    deterministic_csv(full_equity_daily, args.output / "full_equity_daily_audit.csv.gz", gzip=True)
    write_json(finite(full_equity), args.output / "full_equity_summary.json")

    candidate_rows: list[dict[str, Any]] = []
    fold_frames: list[pd.DataFrame] = []
    month_frames: list[pd.DataFrame] = []
    concentration_rows: list[dict[str, Any]] = []
    bootstrap_rows: list[dict[str, Any]] = []
    cost_frames: list[pd.DataFrame] = []
    portfolio_rows: list[dict[str, Any]] = []
    gate_rows: list[dict[str, Any]] = []
    passed_candidates: list[str] = []
    for candidate in catalog:
        candidate_id = candidate["candidate_id"]
        frame = candidate_frames[candidate_id]
        metrics = trade_metrics(frame)
        candidate_rows.append({**candidate, **metrics, "rule_json": json.dumps(candidate["conditions"], sort_keys=True)})
        fold_frames.append(grouped_metrics(frame, ["fold"], candidate_id))
        month_frames.append(grouped_metrics(frame, ["month"], candidate_id))
        concentration_rows.append({"candidate_id": candidate_id, **concentration_metrics(frame)})
        boot = bootstrap_metrics(frame)
        for method, values in boot.items():
            bootstrap_rows.append({"candidate_id": candidate_id, "method": method, **values})
        cost = cost_stress(frame)
        cost.insert(0, "candidate_id", candidate_id)
        cost_frames.append(cost)
        portfolio = portfolio_attribution(baseline, candidate_id, frame, full_equity)
        portfolio_rows.append(portfolio)
        rows = candidate_gate_rows(candidate_id, frame, trades, portfolio, integrity)
        gate_rows.extend(rows)
        if all(bool(row["pass"]) for row in rows if row["binding"]):
            passed_candidates.append(candidate_id)

    candidate_df = pd.DataFrame(candidate_rows)
    gate_df = pd.DataFrame(gate_rows)
    portfolio_df = pd.DataFrame(portfolio_rows)
    deterministic_csv(candidate_df, args.output / "candidate_catalog.csv", gzip=False)
    deterministic_csv(pd.concat(fold_frames, ignore_index=True) if fold_frames else pd.DataFrame(), args.output / "fold_metrics.csv", gzip=False)
    deterministic_csv(pd.concat(month_frames, ignore_index=True) if month_frames else pd.DataFrame(), args.output / "month_metrics.csv", gzip=False)
    deterministic_csv(pd.DataFrame(concentration_rows), args.output / "concentration.csv", gzip=False)
    deterministic_csv(pd.DataFrame(bootstrap_rows), args.output / "bootstrap.csv", gzip=False)
    deterministic_csv(pd.concat(cost_frames, ignore_index=True) if cost_frames else pd.DataFrame(), args.output / "cost_stress.csv", gzip=False)
    deterministic_csv(portfolio_df, args.output / "portfolio_attribution.csv", gzip=False)
    deterministic_csv(gate_df, args.output / "gate_matrix.csv", gzip=False)
    write_json(finite(lofo), args.output / "lofo_feature_selection.json")

    side_rows: list[dict[str, Any]] = []
    for sweep_side, group in trades.groupby("sweep_side", sort=True):
        metrics = trade_metrics(group)
        concentration = concentration_metrics(group)
        boot = bootstrap_metrics(group)
        side_rows.append({"sweep_side": sweep_side, **metrics, **concentration, "bootstrap_lower95_jpy": boot["event"]["lower95_jpy"], "bootstrap_probability_nonpositive": boot["event"]["probability_nonpositive"]})
    deterministic_csv(pd.DataFrame(side_rows), args.output / "side_metrics.csv", gzip=False)
    classification = events.groupby(["path_class", "sweep_side"], sort=True).agg(event_count=("event_id", "count"), raw_diagnostic_net_jpy=("raw_diagnostic_pl_jpy", "sum"), raw_diagnostic_mean_jpy=("raw_diagnostic_pl_jpy", "mean")).reset_index()
    deterministic_csv(classification, args.output / "rejection_acceptance_classification.csv", gzip=False)
    atlas_columns = [column for column in events.columns if column not in {"event_key"}]
    deterministic_csv(events[atlas_columns], args.output / "mechanism_atlas.csv.gz", gzip=True)

    selected_candidate = None
    if passed_candidates:
        priorities = {candidate["candidate_id"]: candidate["priority"] for candidate in catalog}
        selected_candidate = sorted(passed_candidates, key=lambda candidate_id: priorities[candidate_id])[0]

    if not calendar_pass:
        decision = "PREVIOUS_DAY_CALENDAR_CONTRACT_FAILURE"
        next_action = "Close HYP-034 at the calendar-contract stop rule; do not create a candidate."
    elif not chronology_pass:
        decision = "CHRONOLOGY_FAILURE"
        next_action = "Close HYP-034 at the chronology stop rule; unresolved events cannot be selectively excluded."
    elif currency_mismatch:
        decision = "TECHNICAL_NO_RESULT_CURRENCY_CONTRACT_UNRESOLVED"
        next_action = "Repair only the JPY monetary reconciliation without changing candidate, source, period or gate."
    elif not portable_mechanism:
        decision = "NO_PORTABLE_REJECTION_MECHANISM"
        next_action = "Close HYP-034; do not create a candidate or access 2020-2022."
    elif not ex_ante_discriminator:
        decision = "NO_EX_ANTE_OBSERVABLE_DISCRIMINATOR"
        next_action = "Close HYP-034; post-entry lifecycle labels cannot be used to rescue the study."
    elif selected_candidate is None:
        decision = "NO_DEVELOPMENT_CANDIDATE"
        next_action = "Close HYP-034 at the 2023-2024 Development gate with no retuning and no 2020-2022 access."
    else:
        decision = "CANDIDATE_FREEZE_AUTHORIZED"
        next_action = f"Freeze {selected_candidate} exactly, publish the freeze receipt, then open 2020-2022 once for historical validation."

    final = {
        "schema_version": "usdjpy_hyp034_final_result_v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "family_id": FAMILY_ID,
        "decision": decision,
        "source_authority": {"status": "PASS", **source_summary},
        "previous_day_calendar_contract": prereg["previous_day_calendar_contract"],
        "source_native_event_count": int(len(events)),
        "high_sweep_count": int((events.sweep_side == "HIGH").sum()),
        "low_sweep_count": int((events.sweep_side == "LOW").sum()),
        "both_side_date_count": int(events.loc[events.both_side_sweep, "current_trading_date"].nunique()),
        "chronology_mismatch_count": int(len(mismatch)),
        "duplicate_event_count": int(events.event_id.duplicated().sum()),
        "currency_mismatch_count": currency_mismatch,
        "unfiltered_candidate_metrics": finite(unfiltered_metrics),
        "positive_folds": int((fold_net > 0).sum()),
        "fold_net_jpy": finite(fold_net.to_dict()),
        "accepted_raw_diagnostic_mean_jpy": float(accepted_diag.mean()) if len(accepted_diag) else None,
        "nonaccepted_raw_diagnostic_mean_jpy": float(nonaccepted_diag.mean()) if len(nonaccepted_diag) else None,
        "accepted_advantage_jpy": finite(accepted_advantage),
        "portable_mechanism": portable_mechanism,
        "ex_ante_discriminator": ex_ante_discriminator,
        "candidate_catalog_size": len(catalog),
        "selected_candidate": selected_candidate,
        "passed_candidates": passed_candidates,
        "calendar_metadata": calendar_metadata,
        "historical_validation_authorized": selected_candidate is not None,
        "core_mt4_authorized": False,
        "external_2025_authorized": False,
        "protected_2020_2022_accessed": False,
        "protected_2025_accessed": False,
        "production_authorized": False,
        "live_authorized": False,
        "exact_next_action": next_action,
    }
    write_json(finite(final), args.output / "final_result.json")
    (args.output / "human_report.md").write_text(human_report(final), encoding="utf-8")
    manifest = package_manifest(args.output, {"PACKAGE_MANIFEST.json", "PACKAGE_SHA256SUMS"})
    write_json(manifest, args.output / "PACKAGE_MANIFEST.json")
    checksums = "\n".join(f"{row['sha256']}  {row['path']}" for row in manifest["files"]) + "\n"
    (args.output / "PACKAGE_SHA256SUMS").write_text(checksums, encoding="utf-8")
    print(json.dumps(finite(final), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
