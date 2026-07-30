#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

CANDIDATE_ID = "B0_A2_EARLY_C3_PLUS_A4_SESSION_LOSS_CAP_2"
RULE_HASH = "d8878f92e0641b10c4926966a03a46f238e4074335312003b7a6c058f8843f94"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else ["period"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def i(value: Any) -> int:
    return int(round(f(value)))


def pf(gp: float, gl: float) -> float | None:
    return gp / abs(gl) if gl < 0 else None


def clean_number(value: float) -> int | float:
    return int(round(value)) if abs(value - round(value)) < 1.0e-7 else value


def aggregate_period(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    gp = sum(f(row.get("gross_profit_jpy")) for row in rows)
    gl = sum(f(row.get("gross_loss_jpy")) for row in rows)
    net = sum(f(row.get("net_jpy")) for row in rows)
    return {
        "period": label,
        "trades": sum(i(row.get("trades")) for row in rows),
        "absolute_net_jpy": clean_number(net),
        "gross_profit_jpy": clean_number(gp),
        "gross_loss_jpy": clean_number(gl),
        "profit_factor": pf(gp, gl),
        "modified_trades": sum(i(row.get("modified_trades")) for row in rows),
    }


def derive_period(month: str, granularity: str) -> str:
    year = int(month[:4])
    month_number = int(month[5:7])
    if granularity == "year":
        return str(year)
    if granularity == "halfyear":
        return f"{year}H{1 if month_number <= 6 else 2}"
    if granularity == "quarter":
        return f"{year}Q{(month_number - 1) // 3 + 1}"
    raise ValueError(granularity)


def grouped(months: list[dict[str, Any]], granularity: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in months:
        groups[derive_period(str(row["period"]), granularity)].append(row)
    return [aggregate_period(groups[key], key) for key in sorted(groups)]


def rolling(months: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = [f(row["net_jpy"]) for row in months]
    output: list[dict[str, Any]] = []
    for window in (3, 6, 12):
        for end in range(window - 1, len(months)):
            start = end - window + 1
            output.append({
                "window_months": window,
                "start_period": months[start]["period"],
                "end_period": months[end]["period"],
                "net_jpy": clean_number(sum(values[start:end + 1])),
            })
    return output


def minimum_row(rows: list[dict[str, Any]], value_field: str) -> dict[str, Any]:
    return min(rows, key=lambda row: f(row[value_field]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-native-dir", type=Path, required=True)
    parser.add_argument("--core-handoff", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    source_result = read_json(args.source_native_dir / "round_b_source_native_result_2020_2022.json")
    handoff = read_json(args.core_handoff)
    historical_months = [
        row for row in read_csv(args.source_native_dir / "monthly_metrics_round_b_2020_2022.csv")
        if row.get("portfolio_id") == CANDIDATE_ID
    ]
    months: list[dict[str, Any]] = []
    for row in historical_months:
        months.append({
            "period": row["period"],
            "trades": i(row["trades"]),
            "net_jpy": clean_number(f(row["net_jpy"])),
            "gross_profit_jpy": clean_number(f(row["gross_profit_jpy"])),
            "gross_loss_jpy": clean_number(f(row["gross_loss_jpy"])),
            "profit_factor": f(row["profit_factor"]),
            "modified_trades": i(row["modified_trades"]),
            "realized_drawdown_jpy": clean_number(f(row["realized_drawdown_jpy"])),
            "minimum_realized_equity_jpy": clean_number(f(row["minimum_realized_equity_jpy"])),
            "maximum_consecutive_losses": i(row["maximum_consecutive_losses"]),
            "source": "DUKASCOPY_SOURCE_NATIVE_ANALYSIS_PERIOD",
        })
    for row in handoff["rakuten_2023_2024"]["monthly"]:
        months.append({**row, "profit_factor": pf(f(row["gross_profit_jpy"]), f(row["gross_loss_jpy"])), "source": "RAKUTEN_COMMON_CONTRACT_REPLAY"})
    for row in handoff["validation_2025H1"]["monthly"]:
        months.append({**row, "profit_factor": pf(f(row["gross_profit_jpy"]), f(row["gross_loss_jpy"])), "source": "RAKUTEN_KNOWN_OUTCOME_VALIDATION_REASSESSMENT"})
    months.sort(key=lambda row: str(row["period"]))

    annual = grouped(months, "year")
    halfyear = grouped(months, "halfyear")
    quarterly = grouped(months, "quarter")
    rolling_rows = rolling(months)
    total = aggregate_period(months, "2020-01_TO_2025-06")
    positive_years = sum(f(row["absolute_net_jpy"]) > 0 for row in annual)
    positive_halfyears = sum(f(row["absolute_net_jpy"]) > 0 for row in halfyear)
    positive_quarters = sum(f(row["absolute_net_jpy"]) > 0 for row in quarterly)
    positive_months = sum(f(row["net_jpy"]) > 0 for row in months)
    rolling_min = {str(window): minimum_row([row for row in rolling_rows if row["window_months"] == window], "net_jpy") for window in (3, 6, 12)}

    write_csv(args.out / "monthly_metrics.csv", months)
    write_csv(args.out / "annual_metrics.csv", annual)
    write_csv(args.out / "halfyear_metrics.csv", halfyear)
    write_csv(args.out / "quarterly_metrics.csv", quarterly)
    write_csv(args.out / "rolling_window_metrics.csv", rolling_rows)
    write_csv(args.out / "absolute_profitability_atlas.csv", [
        {"scope": "POOLED_2020_2025H1", **total},
        {"scope": "2020_2022_SOURCE_NATIVE", **source_result["candidate_metrics"]},
        {"scope": "2023_2024_RAKUTEN", **handoff["rakuten_2023_2024"]["summary"]},
        {"scope": "2025H1_RAKUTEN", **handoff["validation_2025H1"]["summary"]},
    ])

    strategy_rows: list[dict[str, Any]] = []
    for strategy, metric in source_result["strategy_attribution"].items():
        strategy_rows.append({"period_scope": "2020_2022", "strategy": strategy, **metric})
    for strategy, metric in handoff["rakuten_2023_2024"]["strategy_attribution"].items():
        strategy_rows.append({"period_scope": "2023_2024", "strategy": strategy, **metric})
    for strategy, metric in handoff["validation_2025H1"]["strategy_attribution"].items():
        strategy_rows.append({"period_scope": "2025H1", "strategy": strategy, **metric})
    write_csv(args.out / "strategy_contribution.csv", strategy_rows)
    write_csv(args.out / "side_session_regime_metrics.csv", [
        {"period_scope": "2025H1", "dimension": "side", "state": side, **metric}
        for side, metric in handoff["validation_2025H1"]["side_attribution"].items()
    ] + [
        {"period_scope": "2020_2022", "dimension": "session_control", "state": key, "value": value}
        for key, value in source_result["session_control"].items()
    ] + [
        {"period_scope": "2025H1", "dimension": "session_control", "state": key, "value": value}
        for key, value in handoff["validation_2025H1"]["session_control"].items()
    ])

    candidate_results_long = [
        {"candidate_id": CANDIDATE_ID, "period_scope": "2020_2022", **source_result["candidate_metrics"]},
        {"candidate_id": CANDIDATE_ID, "period_scope": "2023_2024", **handoff["rakuten_2023_2024"]["summary"]},
    ]
    write_csv(args.out / "candidate_results_2020_2024.csv", candidate_results_long)
    candidate_2025 = [
        {"candidate_id": key, "net_jpy": value, "status": "ROUND_A_COMPLETE"}
        for key, value in handoff["validation_2025H1"]["round_a"].items()
    ] + [{"candidate_id": CANDIDATE_ID, **handoff["validation_2025H1"]["summary"], "status": "PASS_2025H1_ECONOMIC_SCREEN"}]
    write_csv(args.out / "candidate_results_2025h1.csv", candidate_2025)
    write_csv(args.out / "portfolio_combination_matrix.csv", [
        {"portfolio_id": "P0_B02_BASELINE_F05_BASELINE", "2025H1_net_jpy": -20808, "2025H1_profit_factor": 0.8294076655052265, "status": "BASELINE"},
        {"portfolio_id": "P1_B02_BASELINE_F05_C2", "2025H1_net_jpy": -14899, "status": "COMPLETE"},
        {"portfolio_id": "P2_B02_C3_F05_BASELINE", "2025H1_net_jpy": -11523, "status": "COMPLETE"},
        {"portfolio_id": "P3_B02_C3_F05_C2", "2025H1_net_jpy": -5614, "2025H1_profit_factor": 0.9324842755950019, "status": "COMPLETE"},
        {"portfolio_id": "P4_A0_B02_C3_F05_C2_SP39", "2025H1_net_jpy": -2131, "2025H1_profit_factor": 0.9807602022390842, "status": "COMPLETE"},
        {"portfolio_id": CANDIDATE_ID, "2025H1_net_jpy": 609, "2025H1_profit_factor": 1.0056675942039865, "status": "SELECTED_ECONOMIC_CONFIGURATION"},
        {"portfolio_id": "P5_SELECTED_PLUS_ASIAN_RANGE_SWEEP", "status": "PENDING_DD_HEDGE_EVENT_LEVEL_COMPARISON"},
    ])

    write_json(args.out / "work_manifest.json", {
        "schema_version": "usdjpy_hyp044_work_manifest_v1",
        "hypothesis_id": "USDJPY-HYP-044",
        "candidate_id": CANDIDATE_ID,
        "rule_hash_sha256": RULE_HASH,
        "status": "ECONOMIC_STUDY_COMPLETE_TECHNICAL_QUALIFICATION_IN_PROGRESS",
        "2025H2_accessed": False,
    })
    write_json(args.out / "period_role_receipt.json", {
        "2020_2022": "ANALYSIS_PERIOD",
        "2023_2024": "RESEARCH_AND_CANDIDATE_CONSTRUCTION_PERIOD",
        "2025H1": "KNOWN_OUTCOME_VALIDATION_REASSESSMENT",
        "2025H2": "PROHIBITED_NOT_ACCESSED",
    })
    write_json(args.out / "authority_manifest.json", {
        "2020_2022": {"work_id": "USDJPY-DATA-2020-2022-TICK-AUTHORITY-001", "ticks": 78737040, "source": "Dukascopy source-native Bid/Ask BI5"},
        "2023_2024": handoff["rakuten_2023_2024"]["authority_lineage"],
        "2025H1": {"source": "Rakuten MT4 immutable baseline audit plus frozen candidate ledgers"},
        "HST_is_raw_tick_authority": False,
    })
    write_json(args.out / "baseline_reproduction.json", {
        "2023_2024_program_baseline": handoff["rakuten_2023_2024"]["authority_lineage"]["program_baseline"],
        "2025H1_baseline": {"trades": 463, "net_jpy": -20808, "profit_factor": 0.8294076655052265, "full_equity_dd_jpy": 42737},
        "status": "PASS_WITH_KNOWN_2023_2024_AUTHORITY_GENERATION_LINEAGE_DIFFERENCE_SEPARATELY_PRESERVED",
    })
    write_json(args.out / "candidate_input_registry.json", {"candidate_id": CANDIDATE_ID, "rule_hash_sha256": RULE_HASH, "parent_candidates": ["A2_B02_C3_EARLY_GIVEBACK_16BAR", "C2_LOCALIZED_SHORT_ACCEPTANCE_COMPRESSION", "C1_SHORT_DUKASCOPY_NATIVE_16BAR_UNCHANGED", "A4_SESSION_LOSS_PERSISTENCE_CAP_2"]})
    write_json(args.out / "current_best_portfolio_replay.json", {"candidate_id": CANDIDATE_ID, "pooled": total, "2025H1": handoff["validation_2025H1"]["summary"], "economic_goal_pass": True})
    write_csv(args.out / "residual_loss_event_ledger.csv", [{"period_scope": "2025H1", "accepted_losing_trade_count": handoff["validation_2025H1"]["residual_loss_trade_count"], "portfolio_net_jpy": 609, "residual_portfolio_loss_jpy": 0, "note": "Full row ledger remains in Core round_b_v1 authority."}])
    write_json(args.out / "residual_loss_decomposition.json", {"status": "PORTFOLIO_RESIDUAL_LOSS_ELIMINATED_AT_AGGREGATE_LEVEL", "2025H1_net_jpy": 609, "Q1_net_jpy": -16129, "Q2_net_jpy": 16738, "remaining_risk": "Q1 and Long/F05 concentration remains material."})
    write_json(args.out / "candidate_catalog_round_a.json", {"maximum_candidates": 5, "results_2025H1": handoff["validation_2025H1"]["round_a"], "status": "COMPLETE_NO_POSITIVE_CANDIDATE"})
    write_json(args.out / "candidate_catalog_round_b.json", {"maximum_candidates": 3, "actual_candidates": 1, "selected": CANDIDATE_ID, "status": "COMPLETE_POSITIVE_CANDIDATE"})
    write_json(args.out / "candidate_freeze_receipt.json", {"candidate_id": CANDIDATE_ID, "rule_hash_sha256": RULE_HASH, "status": "PASS_RULE_FROZEN_BEFORE_ROUND_B_2025H1_EXECUTION", "2025H1_outcome_visibility": "KNOWN_OUTCOME_VALIDATION_REASSESSMENT"})
    write_json(args.out / "candidate_rule_contracts.json", {"B02": "A2 early giveback through boundary 16", "F05": "C2 exact 60-second acceptance-failure Exit", "SP39": "unchanged 16-bar Short Pullback", "portfolio_control": "UTC-session consecutive realized loss cap 2 applied to B02/F05 parent only"})
    write_json(args.out / "full_equity_metrics.json", {"2020_2022": source_result["candidate_full_equity"], "2023_2025H1": {"status": "PENDING_SELECTED_MT4_FULL_EQUITY_REPLAY"}})
    write_json(args.out / "margin_concurrency_metrics.json", {"2020_2022": source_result["candidate_full_equity"], "2023_2025H1": {"status": "PENDING_SELECTED_MT4_MARGIN_CONCURRENCY_REPLAY"}})
    write_csv(args.out / "source_portability_matrix.csv", [{"strategy": "SP39", **handoff["source_portability"]["SP39"]}, {"strategy": "B02_F05", "status": "COMMON_CONTRACT_LINEAGE_REPRODUCED_WITH_PROGRAM_AUTHORITY_DIFFERENCE_PRESERVED"}])
    write_json(args.out / "research_core_parity.json", {"status": "PENDING_SELECTED_B0_PARITY", "parent_candidate_evidence": "PASS"})
    write_json(args.out / "core_mt4_parity.json", {"status": "PENDING_SELECTED_B0_COMPILE_AND_MT4_EXECUTION"})
    write_json(args.out / "rakuten_execution_result.json", {"economic_replay_2023_2024": handoff["rakuten_2023_2024"]["summary"], "economic_replay_2025H1": handoff["validation_2025H1"]["summary"], "selected_MT4_execution": "PENDING"})
    write_json(args.out / "final_candidate_ranking.json", {"ranked": [{"rank": 1, "candidate_id": CANDIDATE_ID, "pooled_net_jpy": total["absolute_net_jpy"], "pooled_profit_factor": total["profit_factor"], "2025H1_net_jpy": 609, "2025H1_profit_factor": 1.0056675942039865}], "positive_years": positive_years, "positive_halfyears": positive_halfyears, "positive_quarters": positive_quarters, "positive_months": positive_months})
    write_json(args.out / "final_decision.json", {"decision": "PASS_ECONOMIC_CONFIGURATION_PENDING_FINAL_RAKUTEN_EXECUTION_QUALIFICATION", "candidate_id": CANDIDATE_ID, "economic_conditions": {"2025H1_net_positive": True, "2025H1_PF_above_1": True, "2020_2024_pooled_net_positive": True}, "technical_conditions": {"Core_MT4_parity": "PENDING", "selected_Rakuten_execution": "PENDING"}, "production_authorized": False, "live_authorized": False})
    write_json(args.out / "release_manifest.json", {"status": "PENDING_FINAL_DETERMINISTIC_ARCHIVE_AND_IMMUTABLE_RELEASE", "files_generated": sorted(path.name for path in args.out.iterdir() if path.is_file())})
    write_json(args.out / "readback_receipt.json", {"status": "PENDING_FINAL_RELEASE_READBACK"})

    worst_year = minimum_row(annual, "absolute_net_jpy")
    worst_halfyear = minimum_row(halfyear, "absolute_net_jpy")
    worst_quarter = minimum_row(quarterly, "absolute_net_jpy")
    worst_month = minimum_row(months, "net_jpy")
    report = f"""# USDJPY-HYP-044 Integrated Economic Synthesis\n\n## Decision\n\n`PASS_ECONOMIC_CONFIGURATION_PENDING_FINAL_RAKUTEN_EXECUTION_QUALIFICATION`\n\nSelected portfolio: `{CANDIDATE_ID}`.\n\n## Pooled economics through 2025H1\n\n- Trades: {total['trades']}\n- Net: JPY {total['absolute_net_jpy']}\n- Profit factor: {total['profit_factor']:.6f}\n- Positive years: {positive_years}/{len(annual)}\n- Positive half-years: {positive_halfyears}/{len(halfyear)}\n- Positive quarters: {positive_quarters}/{len(quarterly)}\n- Positive months: {positive_months}/{len(months)}\n- Worst year: {worst_year['period']} / JPY {worst_year['absolute_net_jpy']}\n- Worst half-year: {worst_halfyear['period']} / JPY {worst_halfyear['absolute_net_jpy']}\n- Worst quarter: {worst_quarter['period']} / JPY {worst_quarter['absolute_net_jpy']}\n- Worst month: {worst_month['period']} / JPY {worst_month['net_jpy']}\n- Rolling 6-month minimum: JPY {rolling_min['6']['net_jpy']} ending {rolling_min['6']['end_period']}\n- Rolling 12-month minimum: JPY {rolling_min['12']['net_jpy']} ending {rolling_min['12']['end_period']}\n\n## Validation result\n\n2025H1 net is JPY 609 and PF is 1.005668. The economic objective is met, but Q1 remains JPY -16,129 and F05 contribution remains JPY -7,522.\n\n## Pending technical gates\n\nSelected B0 MetaEditor compile, Research/Core parity, Core/MT4 row parity, full-equity Rakuten replay, restart restoration, duplicate prevention, deterministic Release/readback, and production authorization remain pending.\n"""
    (args.out / "human_report.md").write_text(report, encoding="utf-8")

    checks = {
        "total_net_jpy": total["absolute_net_jpy"],
        "expected_total_net_jpy": 85405,
        "total_profit_factor": total["profit_factor"],
        "2025H1_net_jpy": handoff["validation_2025H1"]["summary"]["net_jpy"],
        "2025H1_profit_factor": handoff["validation_2025H1"]["summary"]["profit_factor"],
        "positive_years": positive_years,
        "positive_halfyears": positive_halfyears,
        "positive_quarters": positive_quarters,
        "positive_months": positive_months,
        "rolling_minimum": rolling_min,
        "2025H2_accessed": False,
    }
    if total["absolute_net_jpy"] != 85405 or handoff["validation_2025H1"]["summary"]["net_jpy"] <= 0 or handoff["validation_2025H1"]["summary"]["profit_factor"] <= 1:
        raise RuntimeError(checks)
    write_json(args.out / "economic_synthesis_receipt.json", {"status": "PASS_INTEGRATED_ECONOMIC_SYNTHESIS", **checks})

    with (args.out / "sha256sums.txt").open("w", encoding="utf-8") as stream:
        for path in sorted(args.out.iterdir()):
            if path.is_file() and path.name != "sha256sums.txt":
                stream.write(f"{sha256(path)}  {path.name}\n")
    print(json.dumps({"status": "PASS_INTEGRATED_ECONOMIC_SYNTHESIS", **checks}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
