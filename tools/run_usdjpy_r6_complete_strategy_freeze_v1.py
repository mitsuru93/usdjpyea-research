#!/usr/bin/env python3
"""USDJPY R6 complete-strategy freeze evaluator.

This evaluator consumes only the accepted R4 and R5 artifacts for 2024 H1.
It audits all 32 Entry/Exit combinations, applies the preregistered common
eligibility gates, ranks eligible complete strategies, applies definition,
family, and redundancy controls, freezes at most five strategies, and emits a
machine-readable plan for one joint candidate-specific unused H2 validation.

It never reads H2 or 2025 market data and performs no Entry/Exit optimization.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

EXPECTED_POLICIES = {
    "T0_fixed_time_cap",
    "S1_static_stop_2atr",
    "B1_bracket_1p5_3atr",
    "C1_chandelier_3atr",
}
MONTHS = [f"2024-{month:02d}" for month in range(1, 7)]
DAILY_CALENDAR = pd.date_range("2024-01-01", "2024-06-30", freq="D", tz="UTC")
KEY_COLUMNS = ["candidate_id", "policy_id"]
R4_IDENTITY_COLUMNS = ["candidate_id", "family", "definition_sha256", "horizon_bars"]
R5_IDENTITY_COLUMNS = [
    "candidate_id",
    "family",
    "definition_sha256",
    "time_cap_bars",
    "policy_id",
    "mechanism",
]
GATE_COLUMNS = [
    "gate_minimum_aggregate_trades",
    "gate_minimum_monthly_trades",
    "gate_avg_default_net_pips_positive",
    "gate_avg_severe_net_pips_positive",
    "gate_default_profit_factor_above_one",
    "gate_severe_profit_factor_above_one",
    "gate_default_positive_months",
    "gate_severe_positive_months",
    "gate_excluding_best_two_days_positive",
    "gate_quarters_default_positive",
    "gate_quarters_severe_positive",
    "gate_rolling2_default_positive",
    "gate_rolling2_severe_positive",
    "gate_rolling3_default_positive",
    "gate_rolling3_severe_positive",
    "gate_largest_absolute_day_share",
    "gate_largest_absolute_month_share",
    "gate_top_two_positive_days_share",
    "gate_direction_absolute_contribution_share",
    "gate_execution_evidence",
]
RANK_COMPONENTS = [
    "aggregate_avg_severe_net_pips",
    "aggregate_severe_profit_factor",
    "minimum_quarterly_avg_severe_net_pips",
    "minimum_rolling_3month_avg_severe_net_pips",
    "severe_positive_months",
    "total_excluding_best_two_utc_days_per_trade",
    "one_minus_largest_absolute_day_share",
    "one_minus_largest_absolute_month_share",
    "one_minus_top_two_positive_days_share",
    "one_minus_direction_absolute_contribution_share",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r4-release-zip", required=True)
    parser.add_argument("--r5-release-zip", required=True)
    parser.add_argument("--r4-selected", required=True)
    parser.add_argument("--r5-exit-trades", required=True)
    parser.add_argument("--r5-exit-summary", required=True)
    parser.add_argument("--r5-acceptance", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_write(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def csv_write(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def deterministic_gzip_csv_write(path: Path, frame: pd.DataFrame) -> None:
    raw = frame.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode("utf-8")
    with path.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as gz_handle:
            gz_handle.write(raw)


def profit_factor(series: pd.Series) -> float:
    positive = float(series[series > 0].sum())
    negative = float(-series[series < 0].sum())
    if negative == 0.0:
        return float("inf") if positive > 0.0 else 0.0
    return positive / negative


def ratio_or_zero(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0.0 else float(numerator / denominator)


def mean_for_months(group: pd.DataFrame, months: Iterable[str], column: str) -> float:
    selected = group[group["entry_month"].isin(list(months))]
    if selected.empty:
        return float("nan")
    return float(selected[column].mean())


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    raise TypeError(f"Expected bool, got {type(value).__name__}: {value!r}")


def exact_entry_set(group: pd.DataFrame) -> frozenset[str]:
    timestamps = pd.to_datetime(group["entry_ts"], utc=True, errors="raise")
    return frozenset(ts.isoformat() for ts in timestamps)


def strategy_id(candidate_id: str, policy_id: str) -> str:
    return f"{candidate_id}__{policy_id}"


def main() -> None:
    args = parse_args()
    paths = {name: Path(value) for name, value in vars(args).items() if name != "output_dir"}
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(paths["config"].read_text(encoding="utf-8"))
    r5_acceptance = json.loads(paths["r5_acceptance"].read_text(encoding="utf-8"))
    r4 = pd.read_csv(paths["r4_selected"])
    trades = pd.read_csv(paths["r5_exit_trades"], compression="gzip")
    summary = pd.read_csv(paths["r5_exit_summary"])

    # Frozen input hashes.
    expected_inputs = config["inputs"]
    input_hashes = {
        "r4_release_zip": sha256_file(paths["r4_release_zip"]),
        "r5_release_zip": sha256_file(paths["r5_release_zip"]),
        "r4_selected": sha256_file(paths["r4_selected"]),
        "r5_exit_trades": sha256_file(paths["r5_exit_trades"]),
        "r5_exit_summary": sha256_file(paths["r5_exit_summary"]),
        "r5_acceptance": sha256_file(paths["r5_acceptance"]),
        "config": sha256_file(paths["config"]),
    }
    assert input_hashes["r4_release_zip"] == expected_inputs["r4_release_asset_sha256"]
    assert input_hashes["r5_release_zip"] == expected_inputs["r5_release_asset_sha256"]
    assert input_hashes["r4_selected"] == expected_inputs["r4_selected_representatives_sha256"]
    assert input_hashes["r5_exit_trades"] == expected_inputs["r5_exit_trades_sha256"]
    assert input_hashes["r5_exit_summary"] == expected_inputs["r5_exit_summary_sha256"]
    assert input_hashes["r5_acceptance"] == expected_inputs["r5_acceptance_sha256"]

    required_trade_columns = set(R5_IDENTITY_COLUMNS) | {
        "entry_ts",
        "entry_month",
        "entry_date_utc",
        "side",
        "default_net_pips",
        "severe_net_pips",
    }
    missing_trade_columns = sorted(required_trade_columns - set(trades.columns))
    assert not missing_trade_columns, missing_trade_columns
    required_summary_columns = set(R5_IDENTITY_COLUMNS) | {
        "trades",
        "avg_default_net_pips",
        "avg_severe_net_pips",
        "default_profit_factor",
        "severe_profit_factor",
        "total_excluding_best_two_utc_days",
    }
    missing_summary_columns = sorted(required_summary_columns - set(summary.columns))
    assert not missing_summary_columns, missing_summary_columns
    assert set(R4_IDENTITY_COLUMNS).issubset(r4.columns)

    surface = config["surface_contract"]
    assert len(r4) == surface["representatives"]
    assert r4["definition_sha256"].nunique() == surface["representatives"]
    assert trades["candidate_id"].nunique() == surface["representatives"]
    assert trades["policy_id"].nunique() == surface["policies"]
    assert set(trades["policy_id"].unique()) == EXPECTED_POLICIES
    assert set(summary["policy_id"].unique()) == EXPECTED_POLICIES
    assert len(summary) == surface["complete_strategy_combinations"]
    assert not summary.duplicated(KEY_COLUMNS).any()

    # R4 identity must remain unchanged in R5.
    r4_identity = r4[R4_IDENTITY_COLUMNS].copy().rename(columns={"horizon_bars": "time_cap_bars"})
    r4_identity["time_cap_bars"] = r4_identity["time_cap_bars"].astype(int)
    r5_candidate_identity = (
        trades[["candidate_id", "family", "definition_sha256", "time_cap_bars"]]
        .drop_duplicates()
        .sort_values("candidate_id")
        .reset_index(drop=True)
    )
    r5_candidate_identity["time_cap_bars"] = r5_candidate_identity["time_cap_bars"].astype(int)
    pd.testing.assert_frame_equal(
        r4_identity.sort_values("candidate_id").reset_index(drop=True),
        r5_candidate_identity,
        check_dtype=False,
    )

    execution_fields = config["eligibility"]["execution_evidence"]
    execution_evidence = {
        "all_entry_sets_exact": bool_value(r5_acceptance["all_policy_entry_sets_exact"]),
        "all_exit_timestamps_no_later_than_time_cap": bool_value(
            r5_acceptance["all_exits_no_later_than_time_cap"]
        ),
        "all_cost_fields_exact": bool_value(r5_acceptance["R2_cost_fields_exact"]),
        "same_bar_ambiguity_adverse_first": bool_value(
            r5_acceptance["same_bar_bracket_adverse_first"]
        ),
        "chandelier_prior_completed_data_only": bool_value(
            r5_acceptance["chandelier_prior_completed_data_only"]
        )
        and bool_value(r5_acceptance["chandelier_stop_never_loosens"]),
    }
    assert execution_evidence == execution_fields
    execution_gate = all(execution_evidence.values()) and r5_acceptance["status"] == "PASS"

    eligibility = config["eligibility"]
    gate_thresholds = {
        "minimum_aggregate_trades": int(eligibility["minimum_aggregate_trades"]),
        "minimum_monthly_trades": int(eligibility["minimum_monthly_trades"]),
        "minimum_default_positive_months": int(
            eligibility["aggregate"]["minimum_default_positive_months"]
        ),
        "minimum_severe_positive_months": int(
            eligibility["aggregate"]["minimum_severe_positive_months"]
        ),
        "required_quarters_default_positive": int(
            eligibility["quarters"]["required_default_positive"]
        ),
        "required_quarters_severe_positive": int(
            eligibility["quarters"]["required_severe_positive"]
        ),
        "required_rolling2_default_positive": int(
            eligibility["rolling_2month"]["required_default_positive"]
        ),
        "required_rolling2_severe_positive": int(
            eligibility["rolling_2month"]["required_severe_positive"]
        ),
        "required_rolling3_default_positive": int(
            eligibility["rolling_3month"]["required_default_positive"]
        ),
        "required_rolling3_severe_positive": int(
            eligibility["rolling_3month"]["required_severe_positive"]
        ),
        "maximum_largest_absolute_day_share": float(
            eligibility["concentration"]["maximum_largest_absolute_day_share"]
        ),
        "maximum_largest_absolute_month_share": float(
            eligibility["concentration"]["maximum_largest_absolute_month_share"]
        ),
        "maximum_top_two_days_share_of_positive_daily_pips": float(
            eligibility["concentration"][
                "maximum_top_two_days_share_of_positive_daily_pips"
            ]
        ),
        "maximum_direction_absolute_contribution_share": float(
            eligibility["concentration"][
                "maximum_direction_absolute_contribution_share"
            ]
        ),
    }

    audit_rows: list[dict[str, Any]] = []
    cached_daily_severe: dict[str, pd.Series] = {}
    cached_entry_sets: dict[str, frozenset[str]] = {}

    grouped = trades.groupby(KEY_COLUMNS, sort=True, observed=True)
    assert grouped.ngroups == surface["complete_strategy_combinations"]

    for (candidate_id, policy_id), group in grouped:
        group = group.copy()
        first = group.iloc[0]
        identity = group[R5_IDENTITY_COLUMNS].drop_duplicates()
        assert len(identity) == 1
        sid = strategy_id(str(candidate_id), str(policy_id))

        monthly = (
            group.groupby("entry_month", observed=True)
            .agg(
                trades=("default_net_pips", "size"),
                total_default_net_pips=("default_net_pips", "sum"),
                total_severe_net_pips=("severe_net_pips", "sum"),
            )
            .reindex(MONTHS, fill_value=0)
        )
        daily = group.groupby("entry_date_utc", observed=True).agg(
            total_default_net_pips=("default_net_pips", "sum"),
            total_severe_net_pips=("severe_net_pips", "sum"),
        )
        direction = group.groupby("side", observed=True)["default_net_pips"].sum()

        quarter_default = [
            mean_for_months(group, MONTHS[0:3], "default_net_pips"),
            mean_for_months(group, MONTHS[3:6], "default_net_pips"),
        ]
        quarter_severe = [
            mean_for_months(group, MONTHS[0:3], "severe_net_pips"),
            mean_for_months(group, MONTHS[3:6], "severe_net_pips"),
        ]
        rolling2_default = [
            mean_for_months(group, MONTHS[start : start + 2], "default_net_pips")
            for start in range(5)
        ]
        rolling2_severe = [
            mean_for_months(group, MONTHS[start : start + 2], "severe_net_pips")
            for start in range(5)
        ]
        rolling3_default = [
            mean_for_months(group, MONTHS[start : start + 3], "default_net_pips")
            for start in range(4)
        ]
        rolling3_severe = [
            mean_for_months(group, MONTHS[start : start + 3], "severe_net_pips")
            for start in range(4)
        ]

        day_default = daily["total_default_net_pips"]
        day_abs_denominator = float(day_default.abs().sum())
        month_abs_denominator = float(monthly["total_default_net_pips"].abs().sum())
        positive_day_denominator = float(day_default[day_default > 0].sum())
        direction_abs_denominator = float(direction.abs().sum())

        best_two_days = float(day_default.nlargest(2).sum())
        total_excluding_best_two = float(group["default_net_pips"].sum() - best_two_days)
        largest_absolute_day_share = ratio_or_zero(
            float(day_default.abs().max()), day_abs_denominator
        )
        largest_absolute_month_share = ratio_or_zero(
            float(monthly["total_default_net_pips"].abs().max()), month_abs_denominator
        )
        top_two_positive_days_share = ratio_or_zero(
            float(day_default[day_default > 0].nlargest(2).sum()), positive_day_denominator
        )
        direction_share = ratio_or_zero(
            float(direction.abs().max()), direction_abs_denominator
        )

        row: dict[str, Any] = {
            "strategy_id": sid,
            "candidate_id": str(candidate_id),
            "family": str(first["family"]),
            "definition_sha256": str(first["definition_sha256"]),
            "time_cap_bars": int(first["time_cap_bars"]),
            "policy_id": str(policy_id),
            "mechanism": str(first["mechanism"]),
            "trades": int(len(group)),
            "minimum_monthly_trades": int(monthly["trades"].min()),
            "aggregate_avg_default_net_pips": float(group["default_net_pips"].mean()),
            "aggregate_total_default_net_pips": float(group["default_net_pips"].sum()),
            "aggregate_default_profit_factor": profit_factor(group["default_net_pips"]),
            "aggregate_avg_severe_net_pips": float(group["severe_net_pips"].mean()),
            "aggregate_total_severe_net_pips": float(group["severe_net_pips"].sum()),
            "aggregate_severe_profit_factor": profit_factor(group["severe_net_pips"]),
            "default_positive_months": int(
                (monthly["total_default_net_pips"] > 0).sum()
            ),
            "severe_positive_months": int(
                (monthly["total_severe_net_pips"] > 0).sum()
            ),
            "quarter_default_positive": int(sum(value > 0 for value in quarter_default)),
            "quarter_severe_positive": int(sum(value > 0 for value in quarter_severe)),
            "minimum_quarterly_avg_default_net_pips": float(min(quarter_default)),
            "minimum_quarterly_avg_severe_net_pips": float(min(quarter_severe)),
            "rolling2_default_positive": int(
                sum(value > 0 for value in rolling2_default)
            ),
            "rolling2_severe_positive": int(
                sum(value > 0 for value in rolling2_severe)
            ),
            "minimum_rolling_2month_avg_default_net_pips": float(min(rolling2_default)),
            "minimum_rolling_2month_avg_severe_net_pips": float(min(rolling2_severe)),
            "rolling3_default_positive": int(
                sum(value > 0 for value in rolling3_default)
            ),
            "rolling3_severe_positive": int(
                sum(value > 0 for value in rolling3_severe)
            ),
            "minimum_rolling_3month_avg_default_net_pips": float(min(rolling3_default)),
            "minimum_rolling_3month_avg_severe_net_pips": float(min(rolling3_severe)),
            "total_excluding_best_two_utc_days": total_excluding_best_two,
            "total_excluding_best_two_utc_days_per_trade": ratio_or_zero(
                total_excluding_best_two, float(len(group))
            ),
            "largest_absolute_day_share": largest_absolute_day_share,
            "largest_absolute_month_share": largest_absolute_month_share,
            "top_two_days_share_of_positive_daily_pips": top_two_positive_days_share,
            "direction_absolute_contribution_share": direction_share,
            "one_minus_largest_absolute_day_share": 1.0 - largest_absolute_day_share,
            "one_minus_largest_absolute_month_share": 1.0 - largest_absolute_month_share,
            "one_minus_top_two_positive_days_share": 1.0 - top_two_positive_days_share,
            "one_minus_direction_absolute_contribution_share": 1.0 - direction_share,
        }

        row.update(
            {
                "gate_minimum_aggregate_trades": row["trades"]
                >= gate_thresholds["minimum_aggregate_trades"],
                "gate_minimum_monthly_trades": row["minimum_monthly_trades"]
                >= gate_thresholds["minimum_monthly_trades"],
                "gate_avg_default_net_pips_positive": row[
                    "aggregate_avg_default_net_pips"
                ]
                > 0,
                "gate_avg_severe_net_pips_positive": row[
                    "aggregate_avg_severe_net_pips"
                ]
                > 0,
                "gate_default_profit_factor_above_one": row[
                    "aggregate_default_profit_factor"
                ]
                > 1,
                "gate_severe_profit_factor_above_one": row[
                    "aggregate_severe_profit_factor"
                ]
                > 1,
                "gate_default_positive_months": row["default_positive_months"]
                >= gate_thresholds["minimum_default_positive_months"],
                "gate_severe_positive_months": row["severe_positive_months"]
                >= gate_thresholds["minimum_severe_positive_months"],
                "gate_excluding_best_two_days_positive": row[
                    "total_excluding_best_two_utc_days"
                ]
                > 0,
                "gate_quarters_default_positive": row["quarter_default_positive"]
                >= gate_thresholds["required_quarters_default_positive"],
                "gate_quarters_severe_positive": row["quarter_severe_positive"]
                >= gate_thresholds["required_quarters_severe_positive"],
                "gate_rolling2_default_positive": row["rolling2_default_positive"]
                >= gate_thresholds["required_rolling2_default_positive"],
                "gate_rolling2_severe_positive": row["rolling2_severe_positive"]
                >= gate_thresholds["required_rolling2_severe_positive"],
                "gate_rolling3_default_positive": row["rolling3_default_positive"]
                >= gate_thresholds["required_rolling3_default_positive"],
                "gate_rolling3_severe_positive": row["rolling3_severe_positive"]
                >= gate_thresholds["required_rolling3_severe_positive"],
                "gate_largest_absolute_day_share": row["largest_absolute_day_share"]
                <= gate_thresholds["maximum_largest_absolute_day_share"],
                "gate_largest_absolute_month_share": row[
                    "largest_absolute_month_share"
                ]
                <= gate_thresholds["maximum_largest_absolute_month_share"],
                "gate_top_two_positive_days_share": row[
                    "top_two_days_share_of_positive_daily_pips"
                ]
                <= gate_thresholds[
                    "maximum_top_two_days_share_of_positive_daily_pips"
                ],
                "gate_direction_absolute_contribution_share": row[
                    "direction_absolute_contribution_share"
                ]
                <= gate_thresholds[
                    "maximum_direction_absolute_contribution_share"
                ],
                "gate_execution_evidence": execution_gate,
            }
        )
        failures = [gate for gate in GATE_COLUMNS if not bool(row[gate])]
        row["eligible"] = len(failures) == 0
        row["failure_reasons"] = "|".join(failures)
        audit_rows.append(row)

        day_severe = daily["total_severe_net_pips"].copy()
        day_severe.index = pd.to_datetime(day_severe.index, utc=True)
        cached_daily_severe[sid] = day_severe.reindex(DAILY_CALENDAR, fill_value=0.0)
        cached_entry_sets[sid] = exact_entry_set(group)

    audit = pd.DataFrame(audit_rows).sort_values(KEY_COLUMNS).reset_index(drop=True)
    assert len(audit) == surface["complete_strategy_combinations"]
    assert not audit.duplicated(KEY_COLUMNS).any()
    assert all(column in audit.columns for column in GATE_COLUMNS)
    exact_eligibility = audit[GATE_COLUMNS].all(axis=1)
    assert (audit["eligible"] == exact_eligibility).all()

    # Reconcile the frozen R5 summary with the trade-ledger calculations.
    check_columns = [
        "trades",
        "avg_default_net_pips",
        "avg_severe_net_pips",
        "default_profit_factor",
        "severe_profit_factor",
        "total_excluding_best_two_utc_days",
    ]
    computed_for_reconciliation = audit[
        KEY_COLUMNS
        + [
            "trades",
            "aggregate_avg_default_net_pips",
            "aggregate_avg_severe_net_pips",
            "aggregate_default_profit_factor",
            "aggregate_severe_profit_factor",
            "total_excluding_best_two_utc_days",
        ]
    ].rename(
        columns={
            "aggregate_avg_default_net_pips": "avg_default_net_pips",
            "aggregate_avg_severe_net_pips": "avg_severe_net_pips",
            "aggregate_default_profit_factor": "default_profit_factor",
            "aggregate_severe_profit_factor": "severe_profit_factor",
        }
    )
    reconciled = summary[KEY_COLUMNS + check_columns].merge(
        computed_for_reconciliation,
        on=KEY_COLUMNS,
        how="outer",
        suffixes=("_r5", "_r6"),
        validate="one_to_one",
    )
    assert len(reconciled) == surface["complete_strategy_combinations"]
    assert (reconciled["trades_r5"] == reconciled["trades_r6"]).all()
    for column in check_columns[1:]:
        assert np.allclose(
            reconciled[f"{column}_r5"],
            reconciled[f"{column}_r6"],
            rtol=0,
            atol=1e-9,
            equal_nan=True,
        ), column

    eligible = audit[audit["eligible"]].copy()
    percentile_columns: list[str] = []
    for component in RANK_COMPONENTS:
        percentile_column = f"pct_{component}"
        eligible[percentile_column] = eligible[component].rank(
            method="average", ascending=True, pct=True
        )
        percentile_columns.append(percentile_column)
    if not eligible.empty:
        eligible["selection_score"] = eligible[percentile_columns].mean(axis=1)
        eligible = eligible.sort_values(
            [
                "selection_score",
                "aggregate_avg_severe_net_pips",
                "minimum_quarterly_avg_severe_net_pips",
                "total_excluding_best_two_utc_days_per_trade",
                "candidate_id",
                "policy_id",
            ],
            ascending=[False, False, False, False, True, True],
            kind="mergesort",
        ).reset_index(drop=True)
        eligible.insert(0, "eligible_rank", range(1, len(eligible) + 1))
    else:
        eligible["selection_score"] = pd.Series(dtype=float)
        eligible.insert(0, "eligible_rank", pd.Series(dtype=int))

    # Complete eligible pairwise similarity grid.
    pairwise_rows: list[dict[str, Any]] = []
    for left_index in range(len(eligible)):
        for right_index in range(left_index + 1, len(eligible)):
            left = eligible.iloc[left_index]
            right = eligible.iloc[right_index]
            left_sid = str(left["strategy_id"])
            right_sid = str(right["strategy_id"])
            left_daily = cached_daily_severe[left_sid].to_numpy(dtype=float)
            right_daily = cached_daily_severe[right_sid].to_numpy(dtype=float)
            if float(np.std(left_daily)) == 0.0 or float(np.std(right_daily)) == 0.0:
                correlation = 0.0
            else:
                correlation = float(np.corrcoef(left_daily, right_daily)[0, 1])
            left_entries = cached_entry_sets[left_sid]
            right_entries = cached_entry_sets[right_sid]
            union_count = len(left_entries | right_entries)
            jaccard = ratio_or_zero(len(left_entries & right_entries), union_count)
            redundant = (
                correlation >= float(config["redundancy"]["daily_severe_net_pearson_threshold"])
                and jaccard
                >= float(config["redundancy"]["entry_timestamp_jaccard_threshold"])
            )
            pairwise_rows.append(
                {
                    "left_eligible_rank": int(left["eligible_rank"]),
                    "left_strategy_id": left_sid,
                    "left_candidate_id": str(left["candidate_id"]),
                    "left_policy_id": str(left["policy_id"]),
                    "right_eligible_rank": int(right["eligible_rank"]),
                    "right_strategy_id": right_sid,
                    "right_candidate_id": str(right["candidate_id"]),
                    "right_policy_id": str(right["policy_id"]),
                    "daily_severe_net_pnl_pearson": correlation,
                    "entry_timestamp_intersection": len(left_entries & right_entries),
                    "entry_timestamp_union": union_count,
                    "entry_timestamp_jaccard": jaccard,
                    "redundant_both_thresholds": redundant,
                }
            )
    pairwise = pd.DataFrame(pairwise_rows)
    expected_pair_rows = len(eligible) * (len(eligible) - 1) // 2
    assert len(pairwise) == expected_pair_rows

    pair_lookup: dict[frozenset[str], dict[str, Any]] = {
        frozenset([row["left_strategy_id"], row["right_strategy_id"]]): row
        for row in pairwise_rows
    }

    # Traverse the deterministic ranking and apply all freeze controls.
    selected_rows: list[pd.Series] = []
    selected_definitions: set[str] = set()
    selected_family_counts: dict[str, int] = {}
    decision_rows: list[dict[str, Any]] = []
    maximum_frozen = int(surface["maximum_frozen_strategies"])
    maximum_per_family = int(surface["maximum_per_family"])

    for _, candidate in eligible.iterrows():
        sid = str(candidate["strategy_id"])
        decision = "not_considered_after_freeze_limit"
        blocker = ""
        blocker_correlation = math.nan
        blocker_jaccard = math.nan

        if len(selected_rows) < maximum_frozen:
            definition = str(candidate["definition_sha256"])
            family = str(candidate["family"])
            if definition in selected_definitions:
                decision = "skip_definition_cap"
                blocker = definition
            elif selected_family_counts.get(family, 0) >= maximum_per_family:
                decision = "skip_family_cap"
                blocker = family
            else:
                redundant_with = None
                for retained in selected_rows:
                    retained_sid = str(retained["strategy_id"])
                    pair = pair_lookup[frozenset([sid, retained_sid])]
                    if bool(pair["redundant_both_thresholds"]):
                        redundant_with = retained_sid
                        blocker_correlation = float(pair["daily_severe_net_pnl_pearson"])
                        blocker_jaccard = float(pair["entry_timestamp_jaccard"])
                        break
                if redundant_with is not None:
                    decision = "skip_pairwise_redundancy"
                    blocker = redundant_with
                else:
                    decision = "freeze"
                    selected_rows.append(candidate)
                    selected_definitions.add(definition)
                    selected_family_counts[family] = selected_family_counts.get(family, 0) + 1

        decision_rows.append(
            {
                "eligible_rank": int(candidate["eligible_rank"]),
                "strategy_id": sid,
                "candidate_id": str(candidate["candidate_id"]),
                "policy_id": str(candidate["policy_id"]),
                "family": str(candidate["family"]),
                "definition_sha256": str(candidate["definition_sha256"]),
                "decision": decision,
                "blocker": blocker,
                "blocker_daily_severe_correlation": blocker_correlation,
                "blocker_entry_timestamp_jaccard": blocker_jaccard,
            }
        )

    frozen = pd.DataFrame(selected_rows).copy()
    if not frozen.empty:
        frozen.insert(0, "freeze_rank", range(1, len(frozen) + 1))
    else:
        frozen = eligible.head(0).copy()
        frozen.insert(0, "freeze_rank", pd.Series(dtype=int))
    decisions = pd.DataFrame(decision_rows)

    assert len(frozen) <= maximum_frozen
    assert frozen["definition_sha256"].nunique() == len(frozen)
    assert (frozen.groupby("family").size() <= maximum_per_family).all()

    if len(frozen) >= 2:
        retained_ids = set(frozen["strategy_id"])
        retained_pairs = pairwise[
            pairwise["left_strategy_id"].isin(retained_ids)
            & pairwise["right_strategy_id"].isin(retained_ids)
        ]
        assert not retained_pairs["redundant_both_thresholds"].any()

    family_rows: list[dict[str, Any]] = []
    families = sorted(set(audit["family"]))
    for family in families:
        family_rows.append(
            {
                "family": family,
                "audited_combinations": int((audit["family"] == family).sum()),
                "eligible_combinations": int((eligible["family"] == family).sum()),
                "frozen_strategies": int((frozen["family"] == family).sum()),
                "maximum_per_family": maximum_per_family,
            }
        )
    family_summary = pd.DataFrame(family_rows)

    h2_config = config["h2_validation_preregistration"]
    h2_strategies: list[dict[str, Any]] = []
    for _, row in frozen.iterrows():
        h2_strategies.append(
            {
                "freeze_rank": int(row["freeze_rank"]),
                "eligible_rank": int(row["eligible_rank"]),
                "strategy_id": str(row["strategy_id"]),
                "candidate_id": str(row["candidate_id"]),
                "family": str(row["family"]),
                "entry_definition_sha256": str(row["definition_sha256"]),
                "policy_id": str(row["policy_id"]),
                "mechanism": str(row["mechanism"]),
                "time_cap_bars": int(row["time_cap_bars"]),
                "entry_specification": "unchanged accepted R4 definition",
                "exit_specification": "unchanged accepted R5 policy and selected time cap",
            }
        )

    forbidden = set(h2_config["previously_opened_complete_strategies_forbidden"])
    assert all(item["strategy_id"] not in forbidden for item in h2_strategies)
    assert all(item["candidate_id"] not in forbidden for item in h2_strategies)

    h2_plan = {
        "version": config["version"],
        "research_stage": "V1_candidate_specific_unused_H2_validation_plan",
        "source_stage": config["research_stage"],
        "validation_period": h2_config["validation_period"],
        "joint_single_run": bool(h2_config["joint_single_run"]),
        "maximum_strategies": int(h2_config["maximum_strategies"]),
        "strategy_count": len(h2_strategies),
        "entry_exit_parameters_unchanged": bool(
            h2_config["entry_exit_parameters_unchanged"]
        ),
        "candidate_specific_unused_only": bool(
            h2_config["candidate_specific_unused_only"]
        ),
        "previously_opened_complete_strategies_forbidden": sorted(forbidden),
        "individual_strategy_gates": h2_config["individual_strategy_gates"],
        "decision": h2_config["decision"],
        "reporting": h2_config["reporting"],
        "strategies": h2_strategies,
        "research_firewall": {
            "H2_rows_parsed_in_R6": 0,
            "2025_access": False,
            "Core_promotion": False,
            "MT4_promotion": False,
        },
    }

    # Write primary tabular outputs before acceptance and metadata.
    audit_output_columns = [
        "strategy_id",
        "candidate_id",
        "family",
        "definition_sha256",
        "time_cap_bars",
        "policy_id",
        "mechanism",
        "trades",
        "minimum_monthly_trades",
        "aggregate_avg_default_net_pips",
        "aggregate_total_default_net_pips",
        "aggregate_default_profit_factor",
        "aggregate_avg_severe_net_pips",
        "aggregate_total_severe_net_pips",
        "aggregate_severe_profit_factor",
        "default_positive_months",
        "severe_positive_months",
        "quarter_default_positive",
        "quarter_severe_positive",
        "minimum_quarterly_avg_default_net_pips",
        "minimum_quarterly_avg_severe_net_pips",
        "rolling2_default_positive",
        "rolling2_severe_positive",
        "minimum_rolling_2month_avg_default_net_pips",
        "minimum_rolling_2month_avg_severe_net_pips",
        "rolling3_default_positive",
        "rolling3_severe_positive",
        "minimum_rolling_3month_avg_default_net_pips",
        "minimum_rolling_3month_avg_severe_net_pips",
        "total_excluding_best_two_utc_days",
        "total_excluding_best_two_utc_days_per_trade",
        "largest_absolute_day_share",
        "largest_absolute_month_share",
        "top_two_days_share_of_positive_daily_pips",
        "direction_absolute_contribution_share",
        "one_minus_largest_absolute_day_share",
        "one_minus_largest_absolute_month_share",
        "one_minus_top_two_positive_days_share",
        "one_minus_direction_absolute_contribution_share",
    ] + GATE_COLUMNS + ["eligible", "failure_reasons"]
    csv_write(output_dir / "complete_strategy_audit_all_32.csv", audit[audit_output_columns])
    csv_write(output_dir / "eligible_complete_strategies.csv", eligible)
    csv_write(output_dir / "frozen_complete_strategies.csv", frozen)
    csv_write(output_dir / "redundancy_decisions.csv", decisions)
    deterministic_gzip_csv_write(output_dir / "eligible_pairwise_similarity.csv.gz", pairwise)
    csv_write(output_dir / "family_freeze_summary.csv", family_summary)
    canonical_json_write(output_dir / "h2_validation_plan.json", h2_plan)

    acceptance: dict[str, Any] = {
        "status": "PASS",
        "accepted_R4_and_R5_release_zip_digests_match": True,
        "selected_representative_and_R5_input_digests_match": True,
        "audit_rows_exactly_32": len(audit) == surface["complete_strategy_combinations"],
        "all_common_gates_calculated_for_all_32": all(
            column in audit.columns and audit[column].notna().all() for column in GATE_COLUMNS
        ),
        "eligibility_is_exact_gate_conjunction": bool(
            (audit["eligible"] == audit[GATE_COLUMNS].all(axis=1)).all()
        ),
        "ranking_only_contains_eligible": bool(eligible["eligible"].all()),
        "ten_equal_percentile_rank_components": len(percentile_columns) == 10
        and all(column in eligible.columns for column in percentile_columns),
        "all_eligible_pairwise_similarities_reported": len(pairwise)
        == expected_pair_rows,
        "frozen_at_most_five": len(frozen) <= maximum_frozen,
        "frozen_definition_sha256_unique": frozen["definition_sha256"].nunique()
        == len(frozen),
        "frozen_family_cap_two": bool(
            (frozen.groupby("family").size() <= maximum_per_family).all()
        ),
        "frozen_pairwise_redundancy_clear": True
        if len(frozen) < 2
        else not bool(retained_pairs["redundant_both_thresholds"].any()),
        "no_eligibility_threshold_relaxation": surface["relaxation_if_too_few"] is False,
        "h2_plan_exactly_matches_frozen_strategies": [
            item["strategy_id"] for item in h2_strategies
        ]
        == list(frozen["strategy_id"]),
        "forbidden_previously_opened_complete_strategies_absent": all(
            item["strategy_id"] not in forbidden and item["candidate_id"] not in forbidden
            for item in h2_strategies
        ),
        "H2_rows_parsed_zero": config["research_firewall"]["H2_rows_parsed"] == 0,
        "2025_access_false": config["research_firewall"]["2025_access"] is False,
        "R4_representatives_unchanged": True,
        "R5_policies_and_parameters_unchanged": set(trades["policy_id"].unique())
        == EXPECTED_POLICIES
        and config["research_firewall"]["R5_policy_changes"] is False
        and config["research_firewall"]["policy_parameter_optimization"] is False,
        "Core_and_MT4_promotion_false": config["research_firewall"]["Core_promotion"]
        is False
        and config["research_firewall"]["MT4_promotion"] is False,
    }
    assert all(value is True for key, value in acceptance.items() if key != "status")
    canonical_json_write(output_dir / "r6_acceptance.json", acceptance)

    required_outputs = list(config["required_outputs"])
    for name in required_outputs:
        if name == "run_metadata.json":
            continue
        path = output_dir / name
        assert path.is_file() and path.stat().st_size > 0, name

    output_hashes = {
        name: sha256_file(output_dir / name)
        for name in required_outputs
        if name != "run_metadata.json"
    }
    metadata = {
        "version": config["version"],
        "research_stage": config["research_stage"],
        "status": "PASS",
        "audit_rows": len(audit),
        "eligible_complete_strategies": len(eligible),
        "eligible_pairwise_comparisons": len(pairwise),
        "frozen_complete_strategies": len(frozen),
        "frozen_strategy_ids": list(frozen["strategy_id"]),
        "input_sha256": input_hashes,
        "output_sha256": output_hashes,
        "ranking_components": RANK_COMPONENTS,
        "ranking_component_weights": "equal",
        "gate_thresholds": gate_thresholds,
        "execution_evidence": execution_evidence,
        "H2_rows_parsed": 0,
        "2025_artifact_access": False,
        "R4_reselection": False,
        "R5_policy_changes": False,
        "policy_parameter_optimization": False,
        "Core_promotion": False,
        "MT4_promotion": False,
        "next_stage": config["next_stage"],
    }
    canonical_json_write(output_dir / "run_metadata.json", metadata)

    for name in required_outputs:
        path = output_dir / name
        assert path.is_file() and path.stat().st_size > 0, name

    print(
        json.dumps(
            {
                "R6": "PASS",
                "audit": len(audit),
                "eligible": len(eligible),
                "frozen": len(frozen),
                "pairwise": len(pairwise),
                "frozen_strategy_ids": list(frozen["strategy_id"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
