#!/usr/bin/env python3
"""Evaluate fixed, no-lookahead long-horizon market states for USDJPY RQ-020B.

This stage is descriptive. It rebuilds the unchanged fixed-five cohort, verifies the
accepted 2023 historical-2024-compatible lineage and exact 2024 regressions, then
reports fixed 5-day/20-day state effects across four development half-years.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usdjpy_fixed5_portability_lib_v1 import (
    IDS,
    build_signals,
    build_trades,
    enrich,
    historical_ledger,
    load23,
    load24,
    server_to_hist_utc,
)

EXPECTED = {
    "m15_2023": "4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78",
    "canonical_ledger_2023": "33d08d580d584f533bc5f9dda510184fb86c668608f76f8e9b7c014924c5f1b8",
}

FOLDS = {
    "2023H1": ("2023-01-01", "2023-07-01"),
    "2023H2": ("2023-07-01", "2024-01-01"),
    "2024H1": ("2024-01-01", "2024-07-01"),
    "2024H2": ("2024-07-01", "2025-01-01"),
}

FEATURE_COLUMNS = {
    "market_direction_agreement": "market_direction_agreement",
    "trade_alignment_agreement": "trade_alignment_agreement",
    "path_efficiency_5d": "path_efficiency_5d_bin",
    "path_efficiency_20d": "path_efficiency_20d_bin",
    "realized_volatility_ratio_5d_to_20d": "volatility_ratio_bin",
    "range_position_20d": "range_position_20d_bin",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((payload + "\n").encode("utf-8")).hexdigest()


def parse_fixed_cohort(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    registry = json.loads((root / "workr1/r1_registry_snapshot.json").read_text(encoding="utf-8"))
    candidates: dict[str, dict[str, Any]] = {}
    for family in registry["families"]:
        for candidate in family["candidates"]:
            if candidate["id"] in IDS:
                candidates[candidate["id"]] = candidate
    if set(candidates) != set(IDS):
        raise RuntimeError(f"fixed candidate set mismatch: {sorted(candidates)}")

    frozen = pd.read_csv(root / "workr6/frozen_complete_strategies.csv")
    specs: list[dict[str, Any]] = []
    for row in frozen.itertuples(index=False):
        if row.candidate_id in IDS:
            specs.append(
                {
                    "freeze_rank": int(row.freeze_rank),
                    "strategy_id": row.strategy_id,
                    "candidate_id": row.candidate_id,
                    "family": row.family,
                    "entry_definition_sha256": row.definition_sha256,
                    "time_cap_bars": int(row.time_cap_bars),
                }
            )
    if {row["candidate_id"] for row in specs} != set(IDS):
        raise RuntimeError("frozen strategy set does not contain the exact fixed five")
    return candidates, specs


def canonical_2023_bars(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path)
    return enrich(
        pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(source["timestamp_utc"], utc=True),
                "symbol": "USDJPY",
                "mid_open": source["open"],
                "mid_high": source["high"],
                "mid_low": source["low"],
                "mid_close": source["close"],
                "spread_open_pips": 0.5,
                "spread_mean_pips": 0.5,
            }
        )
    )


def compare_ledger(actual: pd.DataFrame, accepted: pd.DataFrame) -> dict[str, Any]:
    keys = [
        "trade_key",
        "strategy",
        "signal_utc",
        "entry_utc",
        "side",
        "entry_index",
        "cap_bars",
        "closed",
        "close_index",
        "close_utc",
    ]
    numeric = [
        "entry_bid",
        "entry_price",
        "close_bid",
        "close_price",
        "gross_pips",
        "realized_pl_jpy",
    ]
    expected = accepted.copy()
    observed = actual.copy()
    for frame in (expected, observed):
        frame["close_utc"] = frame["close_utc"].fillna("")
        frame["closed"] = frame["closed"].astype(bool)
    exact_keys = len(expected) == len(observed) and expected[keys].equals(observed[keys])
    exact_numeric = len(expected) == len(observed) and all(
        np.allclose(
            pd.to_numeric(expected[column], errors="coerce"),
            pd.to_numeric(observed[column], errors="coerce"),
            rtol=0,
            atol=1e-9,
            equal_nan=True,
        )
        for column in numeric
    )
    return {
        "rows": len(expected),
        "exact_keys": bool(exact_keys),
        "numeric": bool(exact_numeric),
        "passed": bool(exact_keys and exact_numeric),
    }


def regress_signals(actual: pd.DataFrame, accepted: pd.DataFrame, period: str) -> pd.DataFrame:
    columns = [
        "candidate_id",
        "family",
        "definition_sha256",
        "signal_ts",
        "entry_ts",
        "side",
        "signal_month",
        "signal_hour_utc",
        "entry_month",
        "entry_hour_utc",
    ]
    rows: list[dict[str, Any]] = []
    for candidate_id in IDS:
        expected = (
            accepted.loc[accepted["candidate_id"] == candidate_id, columns]
            .sort_values(["signal_ts", "side"])
            .reset_index(drop=True)
        )
        observed = (
            actual.loc[actual["candidate_id"] == candidate_id, columns]
            .sort_values(["signal_ts", "side"])
            .reset_index(drop=True)
        )
        for frame in (expected, observed):
            frame[["side", "signal_hour_utc", "entry_hour_utc"]] = frame[
                ["side", "signal_hour_utc", "entry_hour_utc"]
            ].astype("int64")
        rows.append(
            {
                "period": period,
                "candidate_id": candidate_id,
                "accepted": len(expected),
                "actual": len(observed),
                "passed": bool(expected.equals(observed)),
            }
        )
    return pd.DataFrame(rows)


def regress_trades(actual: pd.DataFrame, accepted: pd.DataFrame, period: str) -> pd.DataFrame:
    expected_all = accepted.loc[
        accepted["candidate_id"].isin(IDS)
        & (accepted["policy_id"] == "T0_fixed_time_cap")
    ].copy()
    keys = [
        "candidate_id",
        "family",
        "definition_sha256",
        "time_cap_bars",
        "policy_id",
        "signal_ts",
        "entry_ts",
        "exit_ts",
        "side",
        "bars_held",
    ]
    numeric = [
        "entry_mid",
        "exit_mid",
        "default_cost_pips",
        "severe_cost_pips",
        "gross_pips",
        "default_net_pips",
        "severe_net_pips",
    ]
    for frame in (actual, expected_all):
        for column in ["signal_ts", "entry_ts", "exit_ts"]:
            frame[column] = pd.to_datetime(frame[column], utc=True).dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

    rows: list[dict[str, Any]] = []
    for candidate_id in IDS:
        expected = (
            expected_all.loc[expected_all["candidate_id"] == candidate_id]
            .sort_values(["entry_ts", "side"])
            .reset_index(drop=True)
        )
        observed = (
            actual.loc[actual["candidate_id"] == candidate_id]
            .sort_values(["entry_ts", "side"])
            .reset_index(drop=True)
        )
        exact_keys = len(expected) == len(observed) and expected[keys].equals(observed[keys])
        exact_numeric = len(expected) == len(observed) and all(
            np.allclose(
                expected[column].to_numpy(float),
                observed[column].to_numpy(float),
                rtol=0,
                atol=1e-9,
                equal_nan=True,
            )
            for column in numeric
        )
        rows.append(
            {
                "period": period,
                "candidate_id": candidate_id,
                "accepted": len(expected),
                "actual": len(observed),
                "exact_keys": bool(exact_keys),
                "numeric": bool(exact_numeric),
                "passed": bool(exact_keys and exact_numeric),
            }
        )
    return pd.DataFrame(rows)


def sign_label(values: pd.Series, positive: str, negative: str) -> pd.Series:
    return pd.Series(
        np.select([values > 0, values < 0], [positive, negative], default="ZERO"),
        index=values.index,
        dtype="object",
    )


def efficiency_bin(values: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [values < 0.20, values < 0.40],
            ["LOW_LT_0_20", "MID_0_20_TO_0_40"],
            default="HIGH_GE_0_40",
        ),
        index=values.index,
        dtype="object",
    ).where(values.notna())


def volatility_ratio_bin(values: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [values < 0.80, values <= 1.20],
            ["LOW_LT_0_80", "NEUTRAL_0_80_TO_1_20"],
            default="HIGH_GT_1_20",
        ),
        index=values.index,
        dtype="object",
    ).where(values.notna())


def range_position_bin(values: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [values < (1.0 / 3.0), values < (2.0 / 3.0)],
            ["LOWER_THIRD", "MIDDLE_THIRD"],
            default="UPPER_THIRD",
        ),
        index=values.index,
        dtype="object",
    ).where(values.notna())


def calculate_market_features(bars: pd.DataFrame) -> pd.DataFrame:
    market = bars.copy().sort_values("timestamp_utc").reset_index(drop=True)
    close = market["mid_close"].astype(float)
    close_diff = close.diff()

    ret_5d = close - close.shift(480)
    ret_20d = close - close.shift(1920)
    abs_path_5d = close_diff.abs().rolling(480, min_periods=480).sum()
    abs_path_20d = close_diff.abs().rolling(1920, min_periods=1920).sum()
    efficiency_5d = ret_5d.abs() / abs_path_5d.replace(0.0, np.nan)
    efficiency_20d = ret_20d.abs() / abs_path_20d.replace(0.0, np.nan)

    rms_5d = np.sqrt(close_diff.pow(2).rolling(480, min_periods=480).mean())
    rms_20d = np.sqrt(close_diff.pow(2).rolling(1920, min_periods=1920).mean())
    volatility_ratio = rms_5d / rms_20d.replace(0.0, np.nan)

    high_20d = market["mid_high"].rolling(1920, min_periods=1920).max()
    low_20d = market["mid_low"].rolling(1920, min_periods=1920).min()
    range_position = (close - low_20d) / (high_20d - low_20d).replace(0.0, np.nan)

    direction_5d = sign_label(ret_5d, "UP", "DOWN")
    direction_20d = sign_label(ret_20d, "UP", "DOWN")
    direction_agreement = direction_5d + "_" + direction_20d
    direction_agreement = direction_agreement.where(
        (direction_5d != "ZERO") & (direction_20d != "ZERO"), "ZERO_INVOLVED"
    )

    return pd.DataFrame(
        {
            "signal_ts": market["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "return_5d_pips": ret_5d / 0.01,
            "return_20d_pips": ret_20d / 0.01,
            "market_direction_agreement": direction_agreement,
            "path_efficiency_5d": efficiency_5d,
            "path_efficiency_5d_bin": efficiency_bin(efficiency_5d),
            "path_efficiency_20d": efficiency_20d,
            "path_efficiency_20d_bin": efficiency_bin(efficiency_20d),
            "volatility_ratio_5d_to_20d": volatility_ratio,
            "volatility_ratio_bin": volatility_ratio_bin(volatility_ratio),
            "range_position_20d": range_position,
            "range_position_20d_bin": range_position_bin(range_position),
        }
    )


def fold_for_timestamp(timestamp: pd.Timestamp) -> str | None:
    for fold, (start, end) in FOLDS.items():
        if pd.Timestamp(start, tz="UTC") <= timestamp < pd.Timestamp(end, tz="UTC"):
            return fold
    return None


def attach_market_states(trades: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    merged = trades.merge(features, on="signal_ts", how="left", validate="many_to_one")
    signal_time = pd.to_datetime(merged["signal_ts"], utc=True)
    merged["fold"] = [fold_for_timestamp(value) for value in signal_time]

    aligned_5d = merged["side"].astype(float) * merged["return_5d_pips"]
    aligned_20d = merged["side"].astype(float) * merged["return_20d_pips"]
    side_5d = sign_label(aligned_5d, "ALIGN", "OPPOSE")
    side_20d = sign_label(aligned_20d, "ALIGN", "OPPOSE")
    merged["trade_alignment_agreement"] = side_5d + "_" + side_20d
    merged.loc[
        (side_5d == "ZERO") | (side_20d == "ZERO"), "trade_alignment_agreement"
    ] = "ZERO_INVOLVED"

    merged["continuation_default_net_pips"] = merged["default_net_pips"]
    merged["reversal_default_net_pips"] = -merged["gross_pips"] - merged["default_cost_pips"]
    merged["continuation_severe_net_pips"] = merged["severe_net_pips"]
    merged["reversal_severe_net_pips"] = -merged["gross_pips"] - merged["severe_cost_pips"]
    merged["action_advantage_pips"] = 2.0 * merged["gross_pips"]

    required_features = list(FEATURE_COLUMNS.values())
    merged["feature_complete"] = merged[required_features].notna().all(axis=1)
    return merged


def profit_factor(values: pd.Series) -> float | None:
    gains = float(values.loc[values > 0].sum())
    losses = float(-values.loc[values < 0].sum())
    if losses == 0:
        return None if gains == 0 else math.inf
    return gains / losses


def top_two_positive_date_share(group: pd.DataFrame, action_column: str) -> float:
    daily = group.groupby("entry_date_utc", sort=False)[action_column].sum()
    positive = daily.loc[daily > 0].sort_values(ascending=False)
    total = float(positive.sum())
    return 0.0 if total == 0 else float(positive.head(2).sum() / total)


def action_metrics(group: pd.DataFrame, action: str, cost: str) -> dict[str, Any]:
    column = f"{action}_{cost}_net_pips"
    values = group[column].astype(float)
    return {
        "net_pips": float(values.sum()),
        "profit_factor": profit_factor(values),
        "win_rate": float((values > 0).mean()) if len(values) else None,
        "positive_dates": int((group.groupby("entry_date_utc")[column].sum() > 0).sum()),
        "negative_dates": int((group.groupby("entry_date_utc")[column].sum() < 0).sum()),
        "top_two_positive_date_share": top_two_positive_date_share(group, column),
    }


def preferred_action(group: pd.DataFrame) -> str:
    advantage = float(group["action_advantage_pips"].sum())
    if advantage > 1e-12:
        return "continuation"
    if advantage < -1e-12:
        return "reversal"
    return "tie"


def state_fold_rows(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    complete = trades.loc[trades["feature_complete"] & trades["fold"].notna()].copy()
    for feature_family, column in FEATURE_COLUMNS.items():
        for (state, fold), group in complete.groupby([column, "fold"], sort=True):
            continuation_default = action_metrics(group, "continuation", "default")
            continuation_severe = action_metrics(group, "continuation", "severe")
            reversal_default = action_metrics(group, "reversal", "default")
            reversal_severe = action_metrics(group, "reversal", "severe")
            action = preferred_action(group)
            rows.append(
                {
                    "feature_family": feature_family,
                    "state": state,
                    "fold": fold,
                    "trades": int(len(group)),
                    "strategies": int(group["candidate_id"].nunique()),
                    "preferred_action": action,
                    "action_advantage_pips": float(group["action_advantage_pips"].sum()),
                    **{
                        f"continuation_default_{key}": value
                        for key, value in continuation_default.items()
                    },
                    **{
                        f"continuation_severe_{key}": value
                        for key, value in continuation_severe.items()
                    },
                    **{
                        f"reversal_default_{key}": value
                        for key, value in reversal_default.items()
                    },
                    **{
                        f"reversal_severe_{key}": value
                        for key, value in reversal_severe.items()
                    },
                }
            )
    return pd.DataFrame(rows)


def state_strategy_fold_rows(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    complete = trades.loc[trades["feature_complete"] & trades["fold"].notna()].copy()
    for feature_family, column in FEATURE_COLUMNS.items():
        grouped = complete.groupby([column, "fold", "candidate_id"], sort=True)
        for (state, fold, candidate_id), group in grouped:
            rows.append(
                {
                    "feature_family": feature_family,
                    "state": state,
                    "fold": fold,
                    "candidate_id": candidate_id,
                    "trades": int(len(group)),
                    "preferred_action": preferred_action(group),
                    "action_advantage_pips": float(group["action_advantage_pips"].sum()),
                    "continuation_default_net_pips": float(
                        group["continuation_default_net_pips"].sum()
                    ),
                    "continuation_severe_net_pips": float(
                        group["continuation_severe_net_pips"].sum()
                    ),
                    "reversal_default_net_pips": float(
                        group["reversal_default_net_pips"].sum()
                    ),
                    "reversal_severe_net_pips": float(
                        group["reversal_severe_net_pips"].sum()
                    ),
                }
            )
    return pd.DataFrame(rows)


def leave_one_strategy_out_rows(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    complete = trades.loc[trades["feature_complete"] & trades["fold"].notna()].copy()
    for feature_family, column in FEATURE_COLUMNS.items():
        for (state, fold), group in complete.groupby([column, "fold"], sort=True):
            full_action = preferred_action(group)
            present = sorted(group["candidate_id"].unique())
            for excluded in IDS:
                reduced = group.loc[group["candidate_id"] != excluded]
                reduced_action = preferred_action(reduced) if len(reduced) else "empty"
                rows.append(
                    {
                        "feature_family": feature_family,
                        "state": state,
                        "fold": fold,
                        "excluded_candidate_id": excluded,
                        "excluded_was_present": excluded in present,
                        "remaining_trades": int(len(reduced)),
                        "remaining_strategies": int(reduced["candidate_id"].nunique()),
                        "full_preferred_action": full_action,
                        "reduced_preferred_action": reduced_action,
                        "same_action": bool(
                            full_action in {"continuation", "reversal"}
                            and reduced_action == full_action
                        ),
                        "reduced_action_advantage_pips": float(
                            reduced["action_advantage_pips"].sum()
                        )
                        if len(reduced)
                        else 0.0,
                    }
                )
    return pd.DataFrame(rows)


def evaluate_state_gate(state_fold: pd.DataFrame, leave_one_out: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (feature_family, state), group in state_fold.groupby(
        ["feature_family", "state"], sort=True
    ):
        by_fold = group.set_index("fold")
        all_folds = set(by_fold.index) == set(FOLDS)
        actions = by_fold["preferred_action"].tolist() if all_folds else []
        same_action = (
            all_folds
            and len(set(actions)) == 1
            and actions[0] in {"continuation", "reversal"}
        )
        action = actions[0] if same_action else None

        min_trades_pass = all_folds and bool((by_fold["trades"] >= 30).all())
        min_strategies_pass = all_folds and bool((by_fold["strategies"] >= 3).all())
        default_positive = False
        severe_positive = False
        if same_action and action is not None:
            default_positive = bool((by_fold[f"{action}_default_net_pips"] > 0).all())
            severe_positive = bool((by_fold[f"{action}_severe_net_pips"] > 0).all())

        loo = leave_one_out.loc[
            (leave_one_out["feature_family"] == feature_family)
            & (leave_one_out["state"] == state)
        ]
        expected_loo_rows = len(FOLDS) * len(IDS)
        loo_pass = len(loo) == expected_loo_rows and bool(loo["same_action"].all())

        passed = bool(
            all_folds
            and min_trades_pass
            and min_strategies_pass
            and same_action
            and default_positive
            and severe_positive
            and loo_pass
        )
        rows.append(
            {
                "feature_family": feature_family,
                "state": state,
                "all_four_folds_present": all_folds,
                "minimum_trades_each_fold_pass": min_trades_pass,
                "minimum_strategies_each_fold_pass": min_strategies_pass,
                "same_preferred_action_all_four_folds": same_action,
                "preferred_action": action,
                "preferred_action_default_positive_each_fold": default_positive,
                "preferred_action_severe_positive_each_fold": severe_positive,
                "leave_one_strategy_out_same_action_each_fold": loo_pass,
                "minimum_fold_trades": int(by_fold["trades"].min()) if all_folds else 0,
                "minimum_fold_strategies": int(by_fold["strategies"].min()) if all_folds else 0,
                "passed": passed,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["passed", "feature_family", "state"], ascending=[False, True, True]
    )


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()

    root = args.input_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_STATE_OUTCOME_EVALUATION":
        raise RuntimeError("protocol was not frozen before state outcome evaluation")

    candidates, specs = parse_fixed_cohort(root)

    m15_2023 = root / "work23/normalized/usdjpy_2023_m15_bid_utc_rakuten_mt4_v1.csv.gz"
    if file_sha256(m15_2023) != EXPECTED["m15_2023"]:
        raise RuntimeError("2023 normalized M15 identity mismatch")

    canonical_2023 = canonical_2023_bars(m15_2023)
    historical_2023 = load23(m15_2023)
    raw_2023 = pd.read_csv(m15_2023)
    true_utc = pd.to_datetime(raw_2023["timestamp_utc"], utc=True)
    server_time = pd.to_datetime(raw_2023["first_timestamp_mt4_server"], utc=True)
    historical_time = pd.DatetimeIndex([server_to_hist_utc(value) for value in server_time])
    transform = {
        "rows": len(raw_2023),
        "shifted_rows": int((historical_time != true_utc).sum()),
        "duplicates": int(historical_time.duplicated().sum()),
        "monotonic": bool(historical_time.is_monotonic_increasing),
    }
    if transform != {"rows": 24825, "shifted_rows": 1543, "duplicates": 0, "monotonic": True}:
        raise RuntimeError(f"2023 transform gate failed: {transform}")

    accepted_ledger_path = root / "work23/baseline/usdjpy_2023_canonical_baseline_expected_trade_ledger_v1.csv"
    if file_sha256(accepted_ledger_path) != EXPECTED["canonical_ledger_2023"]:
        raise RuntimeError("2023 canonical baseline ledger identity mismatch")
    start_2023 = pd.Timestamp("2023-01-01", tz="UTC")
    end_2023 = pd.Timestamp("2024-01-01", tz="UTC")
    canonical_ledger = historical_ledger(canonical_2023, candidates, start_2023, end_2023)
    canonical_reconciliation = compare_ledger(canonical_ledger, pd.read_csv(accepted_ledger_path))
    if not canonical_reconciliation["passed"]:
        raise RuntimeError("2023 canonical baseline reconciliation failed")

    historical_ledger_2023 = historical_ledger(historical_2023, candidates, start_2023, end_2023)
    closed_2023 = historical_ledger_2023.loc[historical_ledger_2023["closed"]]
    historical_baseline = {
        "opened": len(historical_ledger_2023),
        "closed": len(closed_2023),
        "B02": int((historical_ledger_2023["strategy"] == "B02").sum()),
        "F05": int((historical_ledger_2023["strategy"] == "F05").sum()),
        "net_jpy": float(closed_2023["realized_pl_jpy"].sum()),
        "B02_net_jpy": float(closed_2023.loc[closed_2023["strategy"] == "B02", "realized_pl_jpy"].sum()),
        "F05_net_jpy": float(closed_2023.loc[closed_2023["strategy"] == "F05", "realized_pl_jpy"].sum()),
    }
    expected_baseline = {
        "opened": 961,
        "closed": 960,
        "B02": 230,
        "F05": 731,
        "net_jpy": -9279.0,
        "B02_net_jpy": -12459.0,
        "F05_net_jpy": 3180.0,
    }
    if historical_baseline != expected_baseline:
        raise RuntimeError(f"historical-compatible baseline mismatch: {historical_baseline}")

    bars_2024 = load24(root / "workr0/canonical/bars/M15/USDJPY_M15.csv.gz")
    signals: dict[str, pd.DataFrame] = {}
    trades: dict[str, pd.DataFrame] = {}
    signal_regressions: list[pd.DataFrame] = []
    trade_regressions: list[pd.DataFrame] = []

    for period, start, end, signal_file, trade_file in [
        ("2024H1", "2024-01-01", "2024-07-01", "workr1/candidate_signals.csv.gz", "workr5/exit_trades.csv.gz"),
        ("2024H2", "2024-07-01", "2025-01-01", "workh2/h2_candidate_signals.csv.gz", "workh2/h2_candidate_trades.csv.gz"),
    ]:
        period_start = pd.Timestamp(start, tz="UTC")
        period_end = pd.Timestamp(end, tz="UTC")
        signals[period] = pd.concat(
            [build_signals(bars_2024, candidates[item], period_start, period_end) for item in IDS],
            ignore_index=True,
        )
        trades[period] = build_trades(bars_2024, signals[period], specs, period_start, period_end)
        signal_regressions.append(regress_signals(signals[period], pd.read_csv(root / signal_file), period))
        trade_regressions.append(regress_trades(trades[period], pd.read_csv(root / trade_file), period))

    signal_regression = pd.concat(signal_regressions, ignore_index=True)
    trade_regression = pd.concat(trade_regressions, ignore_index=True)
    if not signal_regression["passed"].all() or not trade_regression["passed"].all():
        raise RuntimeError("2024 fixed-five exact regression failed")

    signals_2023 = pd.concat(
        [build_signals(historical_2023, candidates[item], start_2023, end_2023) for item in IDS],
        ignore_index=True,
    )
    trades_2023 = build_trades(historical_2023, signals_2023, specs, start_2023, end_2023)

    all_bars = pd.concat(
        [historical_2023, bars_2024.loc[bars_2024["timestamp_utc"] >= pd.Timestamp("2024-01-01", tz="UTC")]],
        ignore_index=True,
    ).sort_values("timestamp_utc").reset_index(drop=True)
    if all_bars["timestamp_utc"].duplicated().any() or not all_bars["timestamp_utc"].is_monotonic_increasing:
        raise RuntimeError("cross-year market bar sequence is not unique and monotonic")

    all_trades = pd.concat([trades_2023, trades["2024H1"], trades["2024H2"]], ignore_index=True)
    market_features = calculate_market_features(all_bars)
    state_trades = attach_market_states(all_trades, market_features)

    missing_by_fold = (
        state_trades.groupby("fold", dropna=False)["feature_complete"]
        .agg(total="size", complete="sum")
        .reset_index()
    )
    missing_by_fold["missing"] = missing_by_fold["total"] - missing_by_fold["complete"]

    fold_rows = state_fold_rows(state_trades)
    strategy_rows = state_strategy_fold_rows(state_trades)
    leave_one_out = leave_one_strategy_out_rows(state_trades)
    gate_rows = evaluate_state_gate(fold_rows, leave_one_out)
    passed = gate_rows.loc[gate_rows["passed"]]

    write_csv(signal_regression, output / "usdjpy_rq020b_2024_signal_regression_v1.csv")
    write_csv(trade_regression, output / "usdjpy_rq020b_2024_trade_regression_v1.csv")
    write_csv(missing_by_fold, output / "usdjpy_rq020b_feature_coverage_v1.csv")
    write_csv(fold_rows, output / "usdjpy_rq020b_state_fold_metrics_v1.csv")
    write_csv(strategy_rows, output / "usdjpy_rq020b_state_strategy_fold_metrics_v1.csv")
    write_csv(leave_one_out, output / "usdjpy_rq020b_state_leave_one_strategy_out_v1.csv")
    write_csv(gate_rows, output / "usdjpy_rq020b_state_gate_v1.csv")

    result = {
        "schema_version": "usdjpy_rq020b_long_horizon_regime_result_v1",
        "status": "RETAIN_DESCRIPTIVE_STATE_SET_FOR_SEPARATE_ROUTER_REVIEW" if len(passed) else "CLOSED_NO_STABLE_LONG_HORIZON_STATE",
        "decision": "RETAIN_DESCRIPTIVE_STATE_SET_FOR_SEPARATE_ROUTER_REVIEW; DO_NOT_AUTO_PREREGISTER_ROUTER" if len(passed) else "CLOSE_RQ_020B_NO_STABLE_LONG_HORIZON_STATE; DO_NOT_OPEN_RQ_020C",
        "research_question": "USDJPY-RQ-020B",
        "protocol": {
            "path": str(args.protocol),
            "sha256": file_sha256(args.protocol),
            "schema_version": protocol["schema_version"],
        },
        "lineage": "USDJPY_HISTORICAL_2024_LEGACY_CONTRACT_APPLIED_TO_2023_V1",
        "transform": transform,
        "canonical_2023_baseline_reconciliation": canonical_reconciliation,
        "historical_2024_compatible_2023_baseline": historical_baseline,
        "2024_fixed_five_regression_all_pass": True,
        "fixed_cohort": IDS,
        "feature_families": list(FEATURE_COLUMNS),
        "folds": list(FOLDS),
        "state_gate_count": int(len(gate_rows)),
        "passed_state_count": int(len(passed)),
        "passed_states": passed.to_dict("records"),
        "feature_coverage": missing_by_fold.to_dict("records"),
        "algebraic_reversal_disclosure": protocol["fixed_action_accounting"]["disclosure"],
        "boundaries": {
            "historical_2024_source_mutated": False,
            "parameters_or_bins_optimized": False,
            "feature_interactions_tested": False,
            "strategy_subset_selected": False,
            "router_preregistered": False,
            "MT4_accessed": False,
            "2025_accessed": False,
            "live_orders": False,
        },
    }
    result_path = output / "usdjpy_rq020b_long_horizon_regime_result_v1.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["output_sha256"] = {
        path.name: file_sha256(path)
        for path in sorted(output.iterdir())
        if path.is_file() and path != result_path
    }
    result["result_payload_sha256_before_manifest"] = json_sha256(result)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
