#!/usr/bin/env python3
"""Evaluate preregistered USDJPY A1+hold6 and E3+hold6 on the full H2 block.

The evaluator:
- reproduces both candidates on the authoritative H1 block first;
- generates H2 signals on contiguous H1+H2 history;
- retains only trades whose signal, entry and exit lie inside H2;
- applies the frozen common H2 gate without optimization.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

import run_usdjpy_h1_multi_family_screen as base
import run_usdjpy_h1_multi_family_screen_v2 as v2


EXPECTED_H2_MONTHS = [
    "2024-07",
    "2024-08",
    "2024-09",
    "2024-10",
    "2024-11",
    "2024-12",
]
FLOAT_TOLERANCE = 1e-9


def load_block(
    labeled_paths: list[tuple[str, Path]],
    block_name: str,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames: list[pd.DataFrame] = []
    coverage_rows: list[dict[str, Any]] = []
    for month, path in sorted(dict(labeled_paths).items()):
        bars, coverage = v2.load_bars(month, path)
        coverage["block"] = block_name
        frames.append(bars)
        coverage_rows.append(coverage)
    if not frames:
        raise ValueError(f"no bars supplied for {block_name}")
    bars = pd.concat(frames, ignore_index=True)
    bars = bars.sort_values(["timestamp_utc", "_priority", "_path"])
    before = len(bars)
    bars = bars.drop_duplicates("timestamp_utc", keep="last")
    bars = bars.sort_values("timestamp_utc").reset_index(drop=True)
    if bars["timestamp_utc"].duplicated().any():
        raise AssertionError(f"duplicate timestamps remain in {block_name}")
    coverage_rows.append(
        {
            "block": block_name,
            "month": "ALL",
            "files": int(sum(int(row["files"]) for row in coverage_rows)),
            "rows_before_dedup": int(before),
            "rows_after_dedup": int(len(bars)),
            "duplicate_rows_removed": int(before - len(bars)),
            "start": bars["timestamp_utc"].min().isoformat(),
            "end": bars["timestamp_utc"].max().isoformat(),
        }
    )
    return bars, coverage_rows


def find_candidate_specs(
    registry: dict[str, Any],
    candidate_ids: list[str],
) -> dict[str, tuple[str, dict[str, Any]]]:
    found: dict[str, tuple[str, dict[str, Any]]] = {}
    for family_block in registry["families"]:
        family = str(family_block["family"])
        for raw_candidate in family_block["candidates"]:
            candidate = dict(raw_candidate)
            candidate_id = str(candidate["id"])
            if candidate_id in candidate_ids:
                candidate["base_spread_pips"] = float(
                    registry["costs"]["base_spread_pips"]
                )
                found[candidate_id] = (family, candidate)
    missing = sorted(set(candidate_ids) - set(found))
    if missing:
        raise ValueError(f"candidate IDs missing from registry: {missing}")
    return found


def validate_frozen_specs(
    specs: dict[str, tuple[str, dict[str, Any]]],
) -> None:
    a_family, a1 = specs["A1_impulse_breakout_lb3_hold6"]
    e_family, e3 = specs["E3_trend_24h_resumption_hold6"]
    assert a_family == "m15_impulse_breakout"
    assert int(a1["lookback_bars"]) == 3
    assert int(a1["hold_bars"]) == 6
    assert list(a1["entry_hours_utc"]) == [13, 14, 15, 16]
    assert str(a1["impulse_rule"]) == "signal_range_gt_previous_bar_range"
    assert e_family == "higher_timeframe_trend_continuation"
    assert int(e3["trend_bars"]) == 96
    assert int(e3["hold_bars"]) == 6
    assert list(e3["entry_hours_utc"]) == list(range(7, 17))


def generate_candidate_trades(
    bars: pd.DataFrame,
    family: str,
    candidate: dict[str, Any],
    session_config: dict[str, Any],
) -> pd.DataFrame:
    if family == "m15_impulse_breakout":
        side = v2.impulse_breakout(bars, candidate)
    elif family == "higher_timeframe_trend_continuation":
        side = v2.trend_continuation(bars, candidate)
    else:
        raise ValueError(f"unsupported H2 family: {family}")
    return v2.finalize_signals(
        bars,
        side,
        candidate,
        family,
        session_config,
    )


def h1_regression(
    h1_bars: pd.DataFrame,
    specs: dict[str, tuple[str, dict[str, Any]]],
    registry: dict[str, Any],
    session_config: dict[str, Any],
    expected: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    events = set(str(x) for x in registry["event_dates_utc"])
    for candidate_id in expected:
        family, candidate = specs[candidate_id]
        trades = generate_candidate_trades(
            h1_bars,
            family,
            candidate,
            session_config,
        )
        result, _ = base.evaluate_candidate(
            trades,
            candidate_id,
            family,
            events,
            registry["h1_retention_screen"],
        )
        expected_row = expected[candidate_id]
        row: dict[str, Any] = {
            "candidate_id": candidate_id,
            "status": "passed",
        }
        for metric, expected_value in expected_row.items():
            actual_value = result[metric]
            if isinstance(expected_value, int):
                if int(actual_value) != int(expected_value):
                    raise AssertionError(
                        f"H1 regression mismatch {candidate_id} {metric}: "
                        f"{actual_value} != {expected_value}"
                    )
                row[metric] = int(actual_value)
            else:
                if not math.isclose(
                    float(actual_value),
                    float(expected_value),
                    rel_tol=0.0,
                    abs_tol=FLOAT_TOLERANCE,
                ):
                    raise AssertionError(
                        f"H1 regression mismatch {candidate_id} {metric}: "
                        f"{actual_value} != {expected_value}"
                    )
                row[metric] = float(actual_value)
        rows.append(row)
    return pd.DataFrame(rows)


def monthly_metrics(
    trades: pd.DataFrame,
    candidate_id: str,
    family: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for month in EXPECTED_H2_MONTHS:
        group = trades[trades["entry_month"] == month]
        default = base.summarize(group, "default_net_pips")
        severe = base.summarize(group, "severe_net_pips")
        rows.append(
            {
                "candidate_id": candidate_id,
                "family": family,
                "month": month,
                **default,
                "severe_win_rate": severe["win_rate"],
                "severe_avg_net_pips": severe["avg_net_pips"],
                "severe_total_net_pips": severe["total_net_pips"],
                "severe_profit_factor": severe["profit_factor"],
            }
        )
    return pd.DataFrame(rows)


def candidate_h2_result(
    trades: pd.DataFrame,
    candidate_id: str,
    family: str,
    event_dates: set[str],
    gates: dict[str, Any],
    session_config: dict[str, Any],
) -> tuple[
    dict[str, Any],
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    monthly = monthly_metrics(trades, candidate_id, family)
    default = base.summarize(trades, "default_net_pips")
    severe = base.summarize(trades, "severe_net_pips")
    event_excluded = trades[~trades["entry_date_utc"].isin(event_dates)]
    event_metrics = base.summarize(event_excluded, "default_net_pips")
    daily = (
        trades.groupby("entry_date_utc", sort=True)["default_net_pips"]
        .sum()
        .sort_values(ascending=False)
    )
    best_two_total = float(daily.head(2).sum()) if len(daily) else 0.0
    total_ex_best_two = float(default["total_net_pips"] - best_two_total)
    positive_months = int((monthly["avg_net_pips"] > 0.0).sum())
    minimum_monthly_trades = int(monthly["trades"].min())
    hard_violations = int(
        base.hard_exclusion_mask(
            trades["entry_ts"],
            session_config,
            base.SYMBOL,
        ).sum()
    )

    result: dict[str, Any] = {
        "candidate_id": candidate_id,
        "family": family,
        **default,
        "positive_months": positive_months,
        "minimum_monthly_trades": minimum_monthly_trades,
        "severe_avg_net_pips": severe["avg_net_pips"],
        "severe_total_net_pips": severe["total_net_pips"],
        "severe_profit_factor": severe["profit_factor"],
        "event_excluded_trades": event_metrics["trades"],
        "event_excluded_avg_net_pips": event_metrics["avg_net_pips"],
        "event_excluded_total_net_pips": event_metrics["total_net_pips"],
        "event_excluded_profit_factor": event_metrics["profit_factor"],
        "best_two_days_total_net_pips": best_two_total,
        "total_excluding_best_two_days": total_ex_best_two,
        "best_day": str(daily.index[0]) if len(daily) else "",
        "best_day_net_pips": float(daily.iloc[0]) if len(daily) else 0.0,
        "hard_no_trade_violations": hard_violations,
    }

    checks = {
        "all_six_source_months_accepted": bool(
            gates["all_six_source_months_accepted"]
        ),
        "positive_months": positive_months
        >= int(gates["positive_months_gte"]),
        "aggregate_avg": result["avg_net_pips"]
        > float(gates["aggregate_avg_net_pips_gt"]),
        "aggregate_pf": result["profit_factor"]
        >= float(gates["aggregate_profit_factor_gte"]),
        "event_excluded_avg": result["event_excluded_avg_net_pips"]
        > float(gates["event_excluded_avg_net_pips_gt"]),
        "event_excluded_pf": result["event_excluded_profit_factor"]
        >= float(gates["event_excluded_profit_factor_gte"]),
        "ex_best_two": result["total_excluding_best_two_days"]
        > float(gates["total_excluding_best_two_days_gt"]),
        "aggregate_trades": result["trades"]
        >= int(gates["aggregate_trades_gte"]),
        "monthly_trades": result["minimum_monthly_trades"]
        >= int(gates["minimum_monthly_trades_gte"]),
        "severe_avg": result["severe_avg_net_pips"]
        >= float(gates["severe_avg_net_pips_gte"]),
        "severe_pf": result["severe_profit_factor"]
        >= float(gates["severe_profit_factor_gte"]),
        "hard_no_trade": hard_violations
        == int(gates["hard_no_trade_violations_eq"]),
        "h1_regression": bool(gates["h1_regression_required"]),
    }
    result["promotion_pass"] = bool(all(checks.values()))
    result["failed_checks"] = ",".join(
        key for key, passed in checks.items() if not passed
    )

    gate_rows = pd.DataFrame(
        [
            {
                "candidate_id": candidate_id,
                "gate": gate,
                "passed": bool(passed),
            }
            for gate, passed in checks.items()
        ]
    )

    direction_rows: list[dict[str, Any]] = []
    for side_value, label in [(1, "long"), (-1, "short")]:
        group = trades[trades["side"] == side_value]
        default_direction = base.summarize(group, "default_net_pips")
        severe_direction = base.summarize(group, "severe_net_pips")
        direction_rows.append(
            {
                "candidate_id": candidate_id,
                "direction": label,
                **default_direction,
                "severe_avg_net_pips": severe_direction["avg_net_pips"],
                "severe_total_net_pips": severe_direction["total_net_pips"],
                "severe_profit_factor": severe_direction["profit_factor"],
            }
        )
    direction = pd.DataFrame(direction_rows)

    daily_frame = (
        trades.groupby("entry_date_utc", as_index=False)
        .agg(
            trades=("default_net_pips", "size"),
            default_net_pips=("default_net_pips", "sum"),
            severe_net_pips=("severe_net_pips", "sum"),
        )
        .assign(candidate_id=candidate_id)
    )
    return result, monthly, gate_rows, direction, daily_frame


def comparison_payload(
    trades_by_candidate: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    a_id = "A1_impulse_breakout_lb3_hold6"
    e_id = "E3_trend_24h_resumption_hold6"
    a1 = trades_by_candidate[a_id]
    e3 = trades_by_candidate[e_id]
    a_keys = set(zip(a1["entry_ts"].astype("int64"), a1["side"].astype(int)))
    e_keys = set(zip(e3["entry_ts"].astype("int64"), e3["side"].astype(int)))
    overlap = a_keys & e_keys

    a_daily = a1.groupby("entry_date_utc")["default_net_pips"].sum().rename("A1")
    e_daily = e3.groupby("entry_date_utc")["default_net_pips"].sum().rename("E3")
    daily = pd.concat([a_daily, e_daily], axis=1).fillna(0.0).sort_index()
    correlation = None
    if (
        len(daily) >= 2
        and daily["A1"].std(ddof=0) > 0
        and daily["E3"].std(ddof=0) > 0
    ):
        correlation = float(daily["A1"].corr(daily["E3"]))

    a_days = set(a1["entry_date_utc"])
    e_days = set(e3["entry_date_utc"])
    return {
        "exact_entry_timestamp_direction_overlap": int(len(overlap)),
        "overlap_share_of_a1": float(len(overlap) / len(a1)) if len(a1) else 0.0,
        "overlap_share_of_e3": float(len(overlap) / len(e3)) if len(e3) else 0.0,
        "daily_net_pips_correlation": correlation,
        "a1_trade_days": int(len(a_days)),
        "e3_trade_days": int(len(e_days)),
        "union_trade_days": int(len(a_days | e_days)),
        "shared_trade_days": int(len(a_days & e_days)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--h1-bars",
        action="append",
        required=True,
        type=base.parse_labeled_path,
    )
    parser.add_argument(
        "--h2-bars",
        action="append",
        required=True,
        type=base.parse_labeled_path,
    )
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--eval-config", required=True, type=Path)
    parser.add_argument("--session-config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    eval_config = json.loads(args.eval_config.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))

    assert registry["symbol"] == eval_config["symbol"] == base.SYMBOL
    assert registry["timeframe"] == eval_config["timeframe"] == "M15"
    assert session_config.get("hard_no_trade_windows")
    candidate_ids = list(eval_config["candidate_ids"])
    assert candidate_ids == [
        "A1_impulse_breakout_lb3_hold6",
        "E3_trend_24h_resumption_hold6",
    ]
    assert eval_config["history_policy"] == (
        "generate_h2_signals_on_contiguous_h1_plus_h2_bars_then_retain_entries_and_exits_inside_h2"
    )

    specs = find_candidate_specs(registry, candidate_ids)
    validate_frozen_specs(specs)

    h1_bars, h1_coverage = load_block(args.h1_bars, "H1")
    h2_only_bars, h2_coverage = load_block(args.h2_bars, "H2")
    all_bars = pd.concat([h1_bars, h2_only_bars], ignore_index=True)
    all_bars = all_bars.sort_values(["timestamp_utc", "_priority", "_path"])
    all_bars = all_bars.drop_duplicates("timestamp_utc", keep="last")
    all_bars = all_bars.sort_values("timestamp_utc").reset_index(drop=True)

    h1_regression_df = h1_regression(
        h1_bars,
        specs,
        registry,
        session_config,
        eval_config["expected_h1_regression"],
    )

    h2_start = pd.Timestamp(eval_config["h2_block"]["start_utc"])
    h2_end = pd.Timestamp(eval_config["h2_block"]["end_utc_exclusive"])
    event_dates = set(str(x) for x in eval_config["intervention_dates_utc"])
    gates = dict(eval_config["gates"])

    summary_rows: list[dict[str, Any]] = []
    monthly_frames: list[pd.DataFrame] = []
    gate_frames: list[pd.DataFrame] = []
    direction_frames: list[pd.DataFrame] = []
    daily_frames: list[pd.DataFrame] = []
    trades_by_candidate: dict[str, pd.DataFrame] = {}

    for candidate_id in candidate_ids:
        family, candidate = specs[candidate_id]
        generated = generate_candidate_trades(
            all_bars,
            family,
            candidate,
            session_config,
        )
        trades = generated[
            (generated["timestamp_utc"] >= h2_start)
            & (generated["entry_ts"] >= h2_start)
            & (generated["entry_ts"] < h2_end)
            & (generated["exit_ts"] >= h2_start)
            & (generated["exit_ts"] < h2_end)
        ].copy()
        if trades.empty:
            raise AssertionError(f"no H2 trades for {candidate_id}")
        trades_by_candidate[candidate_id] = trades
        result, monthly, gate_rows, direction, daily = candidate_h2_result(
            trades,
            candidate_id,
            family,
            event_dates,
            gates,
            session_config,
        )
        summary_rows.append(result)
        monthly_frames.append(monthly)
        gate_frames.append(gate_rows)
        direction_frames.append(direction)
        daily_frames.append(daily)

    summary = pd.DataFrame(summary_rows)
    monthly = pd.concat(monthly_frames, ignore_index=True)
    gate_results = pd.concat(gate_frames, ignore_index=True)
    direction = pd.concat(direction_frames, ignore_index=True)
    daily = pd.concat(daily_frames, ignore_index=True)
    trades_out = pd.concat(trades_by_candidate.values(), ignore_index=True)
    comparison = comparison_payload(trades_by_candidate)

    pass_ids = summary.loc[
        summary["promotion_pass"],
        "candidate_id",
    ].tolist()
    if len(pass_ids) == 2:
        decision = "both_advance"
    elif len(pass_ids) == 1:
        decision = "one_advances"
    else:
        decision = "neither_advances"

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(h1_coverage + h2_coverage).to_csv(
        out / "source_bar_coverage.csv",
        index=False,
    )
    h1_regression_df.to_csv(out / "h1_regression.csv", index=False)
    summary.to_csv(out / "h2_candidate_summary.csv", index=False)
    monthly.to_csv(out / "h2_candidate_monthly.csv", index=False)
    gate_results.to_csv(out / "h2_gate_results.csv", index=False)
    direction.to_csv(out / "h2_direction_attribution.csv", index=False)
    daily.to_csv(out / "h2_daily_net_pips.csv", index=False)
    trades_out.to_csv(out / "h2_candidate_trades.csv", index=False)

    decision_payload = {
        "decision": decision,
        "advancing_candidates": pass_ids,
        "candidate_pass": {
            row["candidate_id"]: bool(row["promotion_pass"])
            for _, row in summary.iterrows()
        },
        "comparison": comparison,
    }
    (out / "h2_decision.json").write_text(
        json.dumps(decision_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metadata = {
        "version": eval_config["version"],
        "registry": str(args.registry),
        "eval_config": str(args.eval_config),
        "session_config": str(args.session_config),
        "candidate_ids": candidate_ids,
        "history_policy": eval_config["history_policy"],
        "h2_start_utc": h2_start.isoformat(),
        "h2_end_utc_exclusive": h2_end.isoformat(),
        "h1_regression": "passed",
        "h2_months": EXPECTED_H2_MONTHS,
        "parameter_changes_after_h2_open": False,
        "exit_optimization_performed": False,
    }
    (out / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(summary.to_string(index=False))
    print(json.dumps(decision_payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
