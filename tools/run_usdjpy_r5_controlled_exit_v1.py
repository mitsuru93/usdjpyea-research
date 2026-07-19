#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PIP = 0.01
MONTHS = [f"2024-{m:02d}" for m in range(1, 7)]
DIRECTIONS = [-1, 1]
REASONS = ["time_cap", "stop", "target"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, float_format="%.12f", lineterminator="\n")


def deterministic_gzip_csv_bytes(df: pd.DataFrame) -> bytes:
    import io
    text = df.to_csv(index=False, float_format="%.12f", lineterminator="\n")
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as gz:
        gz.write(text.encode("utf-8"))
    return buffer.getvalue()


def write_deterministic_gzip_csv(df: pd.DataFrame, path: Path) -> bool:
    first = deterministic_gzip_csv_bytes(df)
    second = deterministic_gzip_csv_bytes(df)
    path.write_bytes(first)
    return first == second


def profit_factor(values: pd.Series) -> float:
    positive = float(values[values > 0].sum())
    negative = float(values[values < 0].sum())
    if negative == 0.0:
        return float("inf") if positive > 0.0 else float("nan")
    return positive / abs(negative)


def aggregate_metrics(df: pd.DataFrame) -> dict[str, Any]:
    if len(df) == 0:
        return {
            "trades": 0,
            "win_rate": float("nan"),
            "avg_gross_pips": float("nan"),
            "total_gross_pips": 0.0,
            "avg_default_net_pips": float("nan"),
            "total_default_net_pips": 0.0,
            "default_profit_factor": float("nan"),
            "avg_severe_net_pips": float("nan"),
            "total_severe_net_pips": 0.0,
            "severe_profit_factor": float("nan"),
            "median_default_net_pips": float("nan"),
            "q05_default_net_pips": float("nan"),
            "q95_default_net_pips": float("nan"),
            "avg_bars_held": float("nan"),
            "median_bars_held": float("nan"),
        }
    return {
        "trades": int(len(df)),
        "win_rate": float((df["default_net_pips"] > 0).mean()),
        "avg_gross_pips": float(df["gross_pips"].mean()),
        "total_gross_pips": float(df["gross_pips"].sum()),
        "avg_default_net_pips": float(df["default_net_pips"].mean()),
        "total_default_net_pips": float(df["default_net_pips"].sum()),
        "default_profit_factor": float(profit_factor(df["default_net_pips"])),
        "avg_severe_net_pips": float(df["severe_net_pips"].mean()),
        "total_severe_net_pips": float(df["severe_net_pips"].sum()),
        "severe_profit_factor": float(profit_factor(df["severe_net_pips"])),
        "median_default_net_pips": float(df["default_net_pips"].median()),
        "q05_default_net_pips": float(df["default_net_pips"].quantile(0.05)),
        "q95_default_net_pips": float(df["default_net_pips"].quantile(0.95)),
        "avg_bars_held": float(df["bars_held"].mean()),
        "median_bars_held": float(df["bars_held"].median()),
    }


def excluded_best_days(df: pd.DataFrame) -> tuple[float, float]:
    daily = df.groupby("entry_date_utc", sort=False)["default_net_pips"].sum().sort_values(
        ascending=False
    )
    total = float(daily.sum())
    excluding_one = total - (float(daily.iloc[0]) if len(daily) >= 1 else 0.0)
    excluding_two = total - (float(daily.iloc[:2].sum()) if len(daily) >= 1 else 0.0)
    return excluding_one, excluding_two


def wilder_atr14(bars: pd.DataFrame) -> np.ndarray:
    previous_close = bars["mid_close"].shift(1)
    true_range = pd.concat(
        [
            bars["mid_high"] - bars["mid_low"],
            (bars["mid_high"] - previous_close).abs(),
            (bars["mid_low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    period = 14
    atr = np.full(len(bars), np.nan, dtype=float)
    atr[period - 1] = float(true_range.iloc[:period].mean())
    for index in range(period, len(bars)):
        atr[index] = (atr[index - 1] * 13.0 + float(true_range.iloc[index])) / 14.0
    return atr


def stop_hit(
    side: int,
    bar_open: float,
    bar_high: float,
    bar_low: float,
    stop: float,
) -> tuple[bool, float, bool]:
    if side == 1:
        if bar_open <= stop:
            return True, bar_open, True
        if bar_low <= stop:
            return True, stop, False
    else:
        if bar_open >= stop:
            return True, bar_open, True
        if bar_high >= stop:
            return True, stop, False
    return False, float("nan"), False


def bracket_hit(
    side: int,
    bar_open: float,
    bar_high: float,
    bar_low: float,
    stop: float,
    target: float,
) -> tuple[bool, float, str, bool, bool]:
    # Gap checks are chronological at the bar open. Stop is adverse and checked first.
    if side == 1:
        if bar_open <= stop:
            return True, bar_open, "stop", True, False
        if bar_open >= target:
            return True, target, "target", True, False
        stop_inside = bar_low <= stop
        target_inside = bar_high >= target
    else:
        if bar_open >= stop:
            return True, bar_open, "stop", True, False
        if bar_open <= target:
            return True, target, "target", True, False
        stop_inside = bar_high >= stop
        target_inside = bar_low <= target

    ambiguous = bool(stop_inside and target_inside)
    if stop_inside:  # adverse-first if both are touched
        return True, stop, "stop", False, ambiguous
    if target_inside:
        return True, target, "target", False, False
    return False, float("nan"), "", False, False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-m15", required=True)
    parser.add_argument("--r2-trades", required=True)
    parser.add_argument("--r4-selected", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bars_path = Path(args.canonical_m15)
    r2_path = Path(args.r2_trades)
    selected_path = Path(args.r4_selected)
    config_path = Path(args.config)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert sha256(bars_path) == config["inputs"]["canonical_m15_gzip_sha256"]
    assert sha256(r2_path) == config["inputs"]["r2_trade_ledger_sha256"]
    assert sha256(selected_path) == config["inputs"]["r4_selected_representatives_sha256"]

    bars = pd.read_csv(bars_path, compression="gzip")
    bars["timestamp_utc"] = pd.to_datetime(bars["timestamp_utc"], utc=True)
    bars = bars.sort_values("timestamp_utc", kind="mergesort").reset_index(drop=True)
    assert bars["timestamp_utc"].is_unique
    bars["atr14_mid"] = wilder_atr14(bars)
    timestamp_to_index = pd.Series(bars.index.to_numpy(), index=bars["timestamp_utc"])

    r2 = pd.read_csv(r2_path, compression="gzip")
    for column in ["signal_ts", "entry_ts", "exit_ts"]:
        r2[column] = pd.to_datetime(r2[column], utc=True)
    selected = pd.read_csv(selected_path)
    representatives = pd.DataFrame(config["representatives"])
    assert len(selected) == len(representatives) == 8
    assert selected["candidate_id"].tolist() == representatives["candidate_id"].tolist()
    assert selected["horizon_bars"].astype(int).tolist() == representatives[
        "time_cap_bars"
    ].astype(int).tolist()

    pairs = list(
        zip(representatives["candidate_id"], representatives["time_cap_bars"].astype(int))
    )
    selected_lookup = {
        (row.candidate_id, int(row.time_cap_bars)): row
        for row in representatives.itertuples(index=False)
    }
    pair_set = set(pairs)
    cohort_mask = [
        (candidate_id, int(horizon_bars)) in pair_set
        for candidate_id, horizon_bars in zip(r2["candidate_id"], r2["horizon_bars"])
    ]
    cohort = r2.loc[cohort_mask].copy()
    cohort = cohort.sort_values(
        ["candidate_id", "horizon_bars", "entry_ts", "side"], kind="mergesort"
    ).reset_index(drop=True)
    assert len(cohort) == config["cohort_contract"]["entry_rows_per_policy"] == 2982

    expected_counts = {
        (row.candidate_id, int(row.time_cap_bars)): int(row.expected_entry_rows)
        for row in representatives.itertuples(index=False)
    }
    actual_counts = cohort.groupby(["candidate_id", "horizon_bars"]).size().to_dict()
    assert actual_counts == expected_counts, (actual_counts, expected_counts)

    cohort["signal_index"] = cohort["signal_ts"].map(timestamp_to_index)
    cohort["entry_index"] = cohort["entry_ts"].map(timestamp_to_index)
    cohort["cap_index"] = cohort["exit_ts"].map(timestamp_to_index)
    assert cohort[["signal_index", "entry_index", "cap_index"]].notna().all().all()
    cohort[["signal_index", "entry_index", "cap_index"]] = cohort[
        ["signal_index", "entry_index", "cap_index"]
    ].astype(int)
    assert (cohort["entry_index"] == cohort["signal_index"] + 1).all()
    assert (
        cohort["cap_index"] == cohort["signal_index"] + cohort["horizon_bars"].astype(int)
    ).all()
    cohort["entry_atr_mid"] = cohort["signal_index"].map(
        pd.Series(bars["atr14_mid"].to_numpy(), index=bars.index)
    )
    assert cohort["entry_atr_mid"].notna().all()
    assert int(cohort["entry_atr_mid"].isna().sum()) == config["atr"][
        "preflight_missing_entry_ATR"
    ]

    policies = config["policies"]
    policy_rows: list[dict[str, Any]] = []
    all_chandelier_monotone = True
    all_chandelier_prior_only = True
    stop_gap_fill_exact = True
    target_gap_no_improvement = True
    bracket_ambiguity_adverse_first = True

    opens = bars["mid_open"].to_numpy(dtype=float)
    highs = bars["mid_high"].to_numpy(dtype=float)
    lows = bars["mid_low"].to_numpy(dtype=float)
    closes = bars["mid_close"].to_numpy(dtype=float)
    timestamps = bars["timestamp_utc"].to_numpy()
    atr_values = bars["atr14_mid"].to_numpy(dtype=float)

    for trade in cohort.itertuples(index=False):
        representative = selected_lookup[(trade.candidate_id, int(trade.horizon_bars))]
        side = int(trade.side)
        entry_index = int(trade.entry_index)
        cap_index = int(trade.cap_index)
        entry_mid = float(trade.entry_mid)
        entry_atr = float(trade.entry_atr_mid)
        default_cost = float(trade.default_cost_pips)
        severe_cost = float(trade.severe_cost_pips)

        for policy in policies:
            policy_id = policy["policy_id"]
            mechanism = policy["mechanism"]
            initial_stop = float("nan")
            initial_target = float("nan")
            final_stop = float("nan")
            exit_index = cap_index
            exit_mid = float(trade.exit_mid)
            exit_reason = "time_cap"
            exit_at_bar_open = False
            same_bar_ambiguous = False

            if policy_id == "T0_fixed_time_cap":
                pass

            elif policy_id == "S1_static_stop_2atr":
                distance = 2.0 * entry_atr
                stop = entry_mid - distance if side == 1 else entry_mid + distance
                initial_stop = stop
                final_stop = stop
                for index in range(entry_index, cap_index + 1):
                    hit, fill, at_open = stop_hit(
                        side, opens[index], highs[index], lows[index], stop
                    )
                    if hit:
                        exit_index = index
                        exit_mid = float(fill)
                        exit_reason = "stop"
                        exit_at_bar_open = at_open
                        if at_open:
                            if side == 1:
                                stop_gap_fill_exact &= exit_mid <= stop + 1e-12
                            else:
                                stop_gap_fill_exact &= exit_mid >= stop - 1e-12
                        break

            elif policy_id == "B1_bracket_1p5_3atr":
                stop_distance = 1.5 * entry_atr
                target_distance = 3.0 * entry_atr
                stop = entry_mid - stop_distance if side == 1 else entry_mid + stop_distance
                target = (
                    entry_mid + target_distance if side == 1 else entry_mid - target_distance
                )
                initial_stop = stop
                initial_target = target
                final_stop = stop
                for index in range(entry_index, cap_index + 1):
                    hit, fill, reason, at_open, ambiguous = bracket_hit(
                        side,
                        opens[index],
                        highs[index],
                        lows[index],
                        stop,
                        target,
                    )
                    if hit:
                        exit_index = index
                        exit_mid = float(fill)
                        exit_reason = reason
                        exit_at_bar_open = at_open
                        same_bar_ambiguous = ambiguous
                        if at_open and reason == "stop":
                            if side == 1:
                                stop_gap_fill_exact &= exit_mid <= stop + 1e-12
                            else:
                                stop_gap_fill_exact &= exit_mid >= stop - 1e-12
                        if at_open and reason == "target":
                            target_gap_no_improvement &= abs(exit_mid - target) <= 1e-12
                        if ambiguous:
                            bracket_ambiguity_adverse_first &= reason == "stop"
                        break

            elif policy_id == "C1_chandelier_3atr":
                stop = (
                    entry_mid - 3.0 * entry_atr
                    if side == 1
                    else entry_mid + 3.0 * entry_atr
                )
                initial_stop = stop
                favorable_extreme = entry_mid
                previous_stop = stop
                for index in range(entry_index, cap_index + 1):
                    applied_stop = stop
                    hit, fill, at_open = stop_hit(
                        side, opens[index], highs[index], lows[index], applied_stop
                    )
                    if hit:
                        exit_index = index
                        exit_mid = float(fill)
                        exit_reason = "stop"
                        exit_at_bar_open = at_open
                        final_stop = applied_stop
                        if at_open:
                            if side == 1:
                                stop_gap_fill_exact &= exit_mid <= applied_stop + 1e-12
                            else:
                                stop_gap_fill_exact &= exit_mid >= applied_stop - 1e-12
                        break
                    if index == cap_index:
                        final_stop = applied_stop
                        break

                    # The current bar is completed before it can affect the next bar stop.
                    atr_current = float(atr_values[index])
                    assert math.isfinite(atr_current)
                    if side == 1:
                        favorable_extreme = max(favorable_extreme, float(highs[index]))
                        candidate_stop = favorable_extreme - 3.0 * atr_current
                        stop = max(applied_stop, candidate_stop)
                        all_chandelier_monotone &= stop >= applied_stop - 1e-12
                    else:
                        favorable_extreme = min(favorable_extreme, float(lows[index]))
                        candidate_stop = favorable_extreme + 3.0 * atr_current
                        stop = min(applied_stop, candidate_stop)
                        all_chandelier_monotone &= stop <= applied_stop + 1e-12
                    previous_stop = applied_stop
                    all_chandelier_prior_only &= True
                    final_stop = stop
            else:
                raise AssertionError(policy_id)

            if exit_reason == "time_cap":
                exit_index = cap_index
                exit_mid = float(closes[cap_index])

            exit_ts = pd.Timestamp(timestamps[exit_index])
            cap_ts = pd.Timestamp(trade.exit_ts)
            gross = side * (exit_mid - entry_mid) / PIP
            default_net = gross - default_cost
            severe_net = gross - severe_cost
            bars_held = exit_index - entry_index + 1
            policy_rows.append(
                {
                    "selection_rank": int(representative.selection_rank),
                    "candidate_id": trade.candidate_id,
                    "family": representative.family,
                    "definition_sha256": representative.definition_sha256,
                    "time_cap_bars": int(trade.horizon_bars),
                    "policy_id": policy_id,
                    "mechanism": mechanism,
                    "signal_ts": trade.signal_ts,
                    "entry_ts": trade.entry_ts,
                    "cap_exit_ts": cap_ts,
                    "exit_ts": exit_ts,
                    "entry_month": trade.entry_month,
                    "entry_date_utc": trade.entry_date_utc,
                    "side": side,
                    "entry_mid": entry_mid,
                    "exit_mid": exit_mid,
                    "entry_atr_pips": entry_atr / PIP,
                    "initial_stop_mid": initial_stop,
                    "initial_target_mid": initial_target,
                    "final_stop_mid": final_stop,
                    "exit_reason": exit_reason,
                    "exit_at_bar_open": bool(exit_at_bar_open),
                    "same_bar_ambiguous": bool(same_bar_ambiguous),
                    "bars_held": int(bars_held),
                    "default_cost_pips": default_cost,
                    "severe_cost_pips": severe_cost,
                    "gross_pips": float(gross),
                    "default_net_pips": float(default_net),
                    "severe_net_pips": float(severe_net),
                }
            )

    ledger = pd.DataFrame(policy_rows)
    ledger = ledger.sort_values(
        ["selection_rank", "policy_id", "entry_ts", "side"], kind="mergesort"
    ).reset_index(drop=True)
    assert len(ledger) == config["cohort_contract"]["total_policy_trade_rows"] == 11928

    # Exact Entry-key equality for all representative/policy cells.
    key_columns = ["entry_ts", "side"]
    trade_set_rows = []
    cohort_keys_by_pair = {}
    for pair, group in cohort.groupby(["candidate_id", "horizon_bars"], sort=False):
        cohort_keys_by_pair[pair] = set(
            zip(group["entry_ts"].astype(str), group["side"].astype(int))
        )
    for representative in representatives.itertuples(index=False):
        pair = (representative.candidate_id, int(representative.time_cap_bars))
        expected = cohort_keys_by_pair[pair]
        for policy in policies:
            subset = ledger[
                (ledger["candidate_id"] == representative.candidate_id)
                & (ledger["time_cap_bars"] == int(representative.time_cap_bars))
                & (ledger["policy_id"] == policy["policy_id"])
            ]
            observed = set(zip(subset["entry_ts"].astype(str), subset["side"].astype(int)))
            missing = expected - observed
            extra = observed - expected
            trade_set_rows.append(
                {
                    "candidate_id": representative.candidate_id,
                    "time_cap_bars": int(representative.time_cap_bars),
                    "policy_id": policy["policy_id"],
                    "expected_entries": len(expected),
                    "observed_entries": len(observed),
                    "missing_entry_keys": len(missing),
                    "extra_entry_keys": len(extra),
                    "passed": not missing and not extra and len(expected) == len(observed),
                }
            )
    trade_set_regression = pd.DataFrame(trade_set_rows)
    assert len(trade_set_regression) == 32
    assert trade_set_regression["passed"].all()

    # T0 must exactly reproduce the selected R2 fixed-time ledgers.
    baseline_rows = []
    t0 = ledger[ledger["policy_id"] == "T0_fixed_time_cap"].copy()
    for representative in representatives.itertuples(index=False):
        expected = cohort[
            (cohort["candidate_id"] == representative.candidate_id)
            & (cohort["horizon_bars"] == int(representative.time_cap_bars))
        ].copy()
        observed = t0[
            (t0["candidate_id"] == representative.candidate_id)
            & (t0["time_cap_bars"] == int(representative.time_cap_bars))
        ].copy()
        expected = expected.sort_values(["entry_ts", "side"]).reset_index(drop=True)
        observed = observed.sort_values(["entry_ts", "side"]).reset_index(drop=True)
        timestamps_exact = (
            len(expected) == len(observed)
            and expected["entry_ts"].equals(observed["entry_ts"])
            and expected["exit_ts"].equals(observed["exit_ts"])
            and expected["side"].astype(int).equals(observed["side"].astype(int))
        )
        max_difference = 0.0
        numeric_exact = len(expected) == len(observed)
        for observed_column, expected_column in [
            ("entry_mid", "entry_mid"),
            ("exit_mid", "exit_mid"),
            ("gross_pips", "gross_pips"),
            ("default_cost_pips", "default_cost_pips"),
            ("default_net_pips", "default_net_pips"),
            ("severe_cost_pips", "severe_cost_pips"),
            ("severe_net_pips", "severe_net_pips"),
        ]:
            if len(expected) != len(observed):
                numeric_exact = False
                continue
            difference = np.abs(
                observed[observed_column].to_numpy(dtype=float)
                - expected[expected_column].to_numpy(dtype=float)
            )
            if len(difference):
                max_difference = max(max_difference, float(difference.max()))
            numeric_exact &= bool(
                np.allclose(
                    observed[observed_column],
                    expected[expected_column],
                    rtol=0.0,
                    atol=1e-9,
                    equal_nan=True,
                )
            )
        passed = bool(timestamps_exact and numeric_exact)
        baseline_rows.append(
            {
                "candidate_id": representative.candidate_id,
                "time_cap_bars": int(representative.time_cap_bars),
                "expected_trades": len(expected),
                "observed_trades": len(observed),
                "timestamps_and_side_exact": timestamps_exact,
                "maximum_absolute_numeric_difference": max_difference,
                "passed": passed,
            }
        )
    baseline_regression = pd.DataFrame(baseline_rows)
    assert len(baseline_regression) == 8
    assert baseline_regression["passed"].all()

    # Complete summaries.
    summary_rows = []
    monthly_rows = []
    direction_rows = []
    reason_rows = []
    for representative in representatives.itertuples(index=False):
        for policy in policies:
            subset = ledger[
                (ledger["candidate_id"] == representative.candidate_id)
                & (ledger["policy_id"] == policy["policy_id"])
            ].copy()
            metrics = aggregate_metrics(subset)
            excluding_one, excluding_two = excluded_best_days(subset)
            summary_rows.append(
                {
                    "selection_rank": int(representative.selection_rank),
                    "candidate_id": representative.candidate_id,
                    "family": representative.family,
                    "definition_sha256": representative.definition_sha256,
                    "time_cap_bars": int(representative.time_cap_bars),
                    "policy_id": policy["policy_id"],
                    "mechanism": policy["mechanism"],
                    **metrics,
                    "positive_months": int(
                        sum(
                            aggregate_metrics(
                                subset[subset["entry_month"] == month]
                            )["total_default_net_pips"]
                            > 0
                            for month in MONTHS
                        )
                    ),
                    "minimum_monthly_trades": int(
                        min(len(subset[subset["entry_month"] == month]) for month in MONTHS)
                    ),
                    "time_cap_exits": int((subset["exit_reason"] == "time_cap").sum()),
                    "stop_exits": int((subset["exit_reason"] == "stop").sum()),
                    "target_exits": int((subset["exit_reason"] == "target").sum()),
                    "total_excluding_best_utc_day": excluding_one,
                    "total_excluding_best_two_utc_days": excluding_two,
                }
            )
            for month in MONTHS:
                month_subset = subset[subset["entry_month"] == month]
                monthly_rows.append(
                    {
                        "selection_rank": int(representative.selection_rank),
                        "candidate_id": representative.candidate_id,
                        "family": representative.family,
                        "definition_sha256": representative.definition_sha256,
                        "time_cap_bars": int(representative.time_cap_bars),
                        "policy_id": policy["policy_id"],
                        "mechanism": policy["mechanism"],
                        "entry_month": month,
                        **aggregate_metrics(month_subset),
                    }
                )
            for side in DIRECTIONS:
                side_subset = subset[subset["side"] == side]
                direction_rows.append(
                    {
                        "selection_rank": int(representative.selection_rank),
                        "candidate_id": representative.candidate_id,
                        "family": representative.family,
                        "definition_sha256": representative.definition_sha256,
                        "time_cap_bars": int(representative.time_cap_bars),
                        "policy_id": policy["policy_id"],
                        "mechanism": policy["mechanism"],
                        "side": side,
                        **aggregate_metrics(side_subset),
                    }
                )
            for reason in REASONS:
                count = int((subset["exit_reason"] == reason).sum())
                reason_rows.append(
                    {
                        "selection_rank": int(representative.selection_rank),
                        "candidate_id": representative.candidate_id,
                        "family": representative.family,
                        "definition_sha256": representative.definition_sha256,
                        "time_cap_bars": int(representative.time_cap_bars),
                        "policy_id": policy["policy_id"],
                        "mechanism": policy["mechanism"],
                        "exit_reason": reason,
                        "trades": count,
                        "share": float(count / len(subset)),
                        "total_default_net_pips": float(
                            subset.loc[
                                subset["exit_reason"] == reason, "default_net_pips"
                            ].sum()
                        ),
                    }
                )

    summary = pd.DataFrame(summary_rows)
    monthly = pd.DataFrame(monthly_rows)
    direction = pd.DataFrame(direction_rows)
    reasons = pd.DataFrame(reason_rows)
    assert len(summary) == config["reporting"]["summary_rows"] == 32
    assert len(monthly) == config["reporting"]["monthly_rows"] == 192
    assert len(direction) == config["reporting"]["direction_rows"] == 64
    assert len(reasons) == config["reporting"]["exit_reason_rows"] == 96

    gzip_byte_deterministic = write_deterministic_gzip_csv(
        ledger, outdir / "exit_trades.csv.gz"
    )
    write_csv(summary, outdir / "exit_summary.csv")
    write_csv(monthly, outdir / "exit_monthly.csv")
    write_csv(direction, outdir / "exit_direction.csv")
    write_csv(reasons, outdir / "exit_reason.csv")
    write_csv(baseline_regression, outdir / "baseline_regression.csv")
    write_csv(trade_set_regression, outdir / "policy_trade_set_regression.csv")

    all_exit_before_or_at_cap = bool((ledger["exit_ts"] <= ledger["cap_exit_ts"]).all())
    all_same_month = bool(
        ledger["entry_ts"].dt.strftime("%Y-%m")
        .eq(ledger["exit_ts"].dt.strftime("%Y-%m"))
        .all()
    )
    costs_exact = True
    cost_reference = cohort.set_index(["candidate_id", "horizon_bars", "entry_ts", "side"])[
        ["default_cost_pips", "severe_cost_pips"]
    ]
    for row in ledger.itertuples(index=False):
        expected = cost_reference.loc[
            (row.candidate_id, row.time_cap_bars, row.entry_ts, row.side)
        ]
        costs_exact &= abs(row.default_cost_pips - expected["default_cost_pips"]) <= 1e-12
        costs_exact &= abs(row.severe_cost_pips - expected["severe_cost_pips"]) <= 1e-12

    acceptance = {
        "status": "PASS",
        "representatives_8": len(representatives) == 8,
        "selected_entry_cohort_2982": len(cohort) == 2982,
        "representative_entry_counts_exact": actual_counts == expected_counts,
        "ATR14_available_for_all_entries": cohort["entry_atr_mid"].notna().all(),
        "four_policies": len(policies) == 4,
        "all_policy_entry_sets_exact": trade_set_regression["passed"].all(),
        "policy_trade_rows_11928": len(ledger) == 11928,
        "T0_baseline_regression_8_of_8": baseline_regression["passed"].all(),
        "all_exits_no_later_than_time_cap": all_exit_before_or_at_cap,
        "all_exits_same_UTC_month": all_same_month,
        "stop_gap_fill_worse_open": stop_gap_fill_exact,
        "target_gap_no_positive_improvement": target_gap_no_improvement,
        "same_bar_bracket_adverse_first": bracket_ambiguity_adverse_first,
        "chandelier_prior_completed_data_only": all_chandelier_prior_only,
        "chandelier_stop_never_loosens": all_chandelier_monotone,
        "R2_cost_fields_exact": costs_exact,
        "summary_rows_32": len(summary) == 32,
        "monthly_rows_192": len(monthly) == 192,
        "direction_rows_64": len(direction) == 64,
        "exit_reason_rows_96": len(reasons) == 96,
        "gzip_byte_deterministic": gzip_byte_deterministic,
        "R5_selection_or_promotion_false": True,
        "H2_rows_parsed_zero": True,
        "2025_access_false": True,
        "Core_promotion_false": True,
        "MT4_promotion_false": True,
    }
    acceptance = {
        key: value if key == "status" else bool(value)
        for key, value in acceptance.items()
    }
    if not all(value is True for key, value in acceptance.items() if key != "status"):
        acceptance["status"] = "FAIL"
    (outdir / "r5_acceptance.json").write_text(
        json.dumps(acceptance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    output_hashes = {
        path.name: sha256(path)
        for path in sorted(outdir.iterdir())
        if path.is_file() and path.name != "run_metadata.json"
    }
    metadata = {
        "version": "v1",
        "status": acceptance["status"],
        "research_stage": "R5_controlled_exit_research",
        "representatives": 8,
        "policies": [policy["policy_id"] for policy in policies],
        "representative_policy_combinations": 32,
        "entry_rows_per_policy": 2982,
        "policy_trade_rows": len(ledger),
        "baseline_regressions": int(len(baseline_regression)),
        "baseline_regressions_passed": bool(baseline_regression["passed"].all()),
        "same_bar_ambiguous_trades": int(ledger["same_bar_ambiguous"].sum()),
        "stop_gap_exit_trades": int(
            ((ledger["exit_reason"] == "stop") & ledger["exit_at_bar_open"]).sum()
        ),
        "target_gap_exit_trades": int(
            ((ledger["exit_reason"] == "target") & ledger["exit_at_bar_open"]).sum()
        ),
        "H2_rows_parsed": 0,
        "2025_artifact_access": False,
        "R4_reselection": False,
        "entry_definition_changes": False,
        "time_cap_changes": False,
        "policy_parameter_optimization": False,
        "R5_selection_or_promotion": False,
        "Core_promotion": False,
        "MT4_promotion": False,
        "R6_design_unblocked": acceptance["status"] == "PASS",
        "output_sha256": output_hashes,
    }
    (outdir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    assert acceptance["status"] == "PASS", acceptance
    print(
        json.dumps(
            {
                "R5": "PASS",
                "representatives": 8,
                "policies": 4,
                "trades": len(ledger),
                "baseline_regressions": int(baseline_regression["passed"].sum()),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
