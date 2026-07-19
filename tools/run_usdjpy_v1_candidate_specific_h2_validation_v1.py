#!/usr/bin/env python3
"""Validate the five frozen USDJPY R6 complete strategies on fixed reusable 2024 H2.

The evaluator first proves exact H1 signal parity with accepted R1 and exact H1
fixed-time trade parity with accepted R5. Only after those regressions pass does
it calculate candidate-specific H2 outcomes. It performs no H2 ranking or
parameter optimization and never reads 2025 data.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from datetime import time
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PIP = 0.01
SYMBOL = "USDJPY"
H1_START = pd.Timestamp("2024-01-01T00:00:00Z")
H1_END = pd.Timestamp("2024-07-01T00:00:00Z")
H2_START = H1_END
H2_END = pd.Timestamp("2025-01-01T00:00:00Z")
H2_MONTHS = [f"2024-{month:02d}" for month in range(7, 13)]
QUARTERS = {"2024-Q3": H2_MONTHS[:3], "2024-Q4": H2_MONTHS[3:]}
FUNCTIONAL_METADATA_KEYS = {
    "id", "origin", "legacy_ids", "h2_information_status", "literature_refs", "family"
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def parse_hhmm(raw: str) -> time:
    hour, minute = raw.split(":", 1)
    return time(int(hour), int(minute))


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0.0:
        return math.inf if gains > 0.0 else 0.0
    return gains / losses


def deterministic_gzip(payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as handle:
        handle.write(payload)
    return buffer.getvalue()


def write_csv(frame: pd.DataFrame, path: Path, float_format: str = "%.12f") -> None:
    path.write_text(frame.to_csv(index=False, lineterminator="\n", na_rep="", float_format=float_format), encoding="utf-8")


def write_gzip_csv(frame: pd.DataFrame, path: Path, float_format: str = "%.12f") -> None:
    payload = frame.to_csv(index=False, lineterminator="\n", na_rep="", float_format=float_format).encode("utf-8")
    path.write_bytes(deterministic_gzip(payload))


def normalized_definition(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": candidate["family"],
        "parameters": {key: value for key, value in candidate.items() if key not in FUNCTIONAL_METADATA_KEYS},
    }


def allowed_hours(bars: pd.DataFrame, candidate: dict[str, Any]) -> pd.Series:
    if "entry_hours_utc" in candidate:
        entry_ts = bars["timestamp_utc"].shift(-1)
        return entry_ts.dt.hour.isin([int(value) for value in candidate["entry_hours_utc"]])
    if "entry_start_hour" in candidate:
        return (
            (bars["hour_utc"] >= int(candidate["entry_start_hour"]))
            & (bars["hour_utc"] <= int(candidate["entry_end_hour_inclusive"]))
        )
    return pd.Series(True, index=bars.index)


def first_per_direction_day(side: pd.Series, bars: pd.DataFrame) -> pd.Series:
    keep = pd.Series(0, index=side.index, dtype="int8")
    selected = pd.DataFrame({"side": side, "date": bars["date_utc"], "ts": bars["timestamp_utc"]})
    selected = selected[selected["side"].isin([1, -1])]
    if selected.empty:
        return keep
    first_idx = selected.sort_values("ts").groupby(["date", "side"], sort=False).head(1).index
    keep.loc[first_idx] = side.loc[first_idx].astype("int8")
    return keep


def session_reference(bars: pd.DataFrame, start_hour: int, end_hour: int) -> pd.DataFrame:
    ref = bars[(bars["hour_utc"] >= start_hour) & (bars["hour_utc"] < end_hour)]
    daily = ref.groupby("date_utc").agg(
        ref_open=("mid_open", "first"),
        ref_high=("mid_high", "max"),
        ref_low=("mid_low", "min"),
        ref_close=("mid_close", "last"),
    )
    return bars[["date_utc"]].join(daily, on="date_utc")


def session_range_breakout(bars: pd.DataFrame, candidate: dict[str, Any]) -> pd.Series:
    ref = session_reference(
        bars,
        int(candidate["reference_start_hour"]),
        int(candidate["reference_end_hour_exclusive"]),
    )
    allowed = allowed_hours(bars, candidate)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & (bars["mid_close"] > ref["ref_high"])] = 1
    side.loc[allowed & (bars["mid_close"] < ref["ref_low"])] = -1
    return first_per_direction_day(side, bars)


def trend_pullback_resumption(bars: pd.DataFrame, candidate: dict[str, Any]) -> pd.Series:
    bars_count = int(candidate["trend_bars"])
    trend_return = bars["mid_close"].shift(1) - bars["mid_open"].shift(bars_count)
    prev_bearish = bars["mid_close"].shift(1) < bars["mid_open"].shift(1)
    prev_bullish = bars["mid_close"].shift(1) > bars["mid_open"].shift(1)
    allowed = allowed_hours(bars, candidate)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & (trend_return > 0) & prev_bearish & (bars["mid_close"] > bars["mid_high"].shift(1))] = 1
    side.loc[allowed & (trend_return < 0) & prev_bullish & (bars["mid_close"] < bars["mid_low"].shift(1))] = -1
    return side


def donchian_channel_breakout(bars: pd.DataFrame, candidate: dict[str, Any]) -> pd.Series:
    bars_count = int(candidate["lookback_bars"])
    high = bars["mid_high"].shift(1).rolling(bars_count, min_periods=bars_count).max()
    low = bars["mid_low"].shift(1).rolling(bars_count, min_periods=bars_count).min()
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    allowed = allowed_hours(bars, candidate)
    long_event = (bars["mid_close"] > high) & (bars["mid_close"].shift(1) <= prev_high)
    short_event = (bars["mid_close"] < low) & (bars["mid_close"].shift(1) >= prev_low)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & long_event] = 1
    side.loc[allowed & short_event] = -1
    return side


def volatility_adjusted_momentum(bars: pd.DataFrame, candidate: dict[str, Any]) -> pd.Series:
    lookback = int(candidate["lookback_bars"])
    volatility_window = int(candidate["volatility_window_bars"])
    threshold = float(candidate["score_threshold"])
    cumulative = (bars["mid_close"] - bars["mid_close"].shift(lookback)) / PIP
    one_bar = bars["mid_close"].diff() / PIP
    realized = np.sqrt(one_bar.pow(2).rolling(volatility_window, min_periods=volatility_window).sum())
    score = cumulative / realized.replace(0.0, np.nan)
    allowed = allowed_hours(bars, candidate)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & (score > threshold) & (score.shift(1) <= threshold)] = 1
    side.loc[allowed & (score < -threshold) & (score.shift(1) >= -threshold)] = -1
    return side


SIGNAL_FUNCTIONS: dict[str, Callable[[pd.DataFrame, dict[str, Any]], pd.Series]] = {
    "session_range_breakout": session_range_breakout,
    "trend_pullback_resumption": trend_pullback_resumption,
    "donchian_channel_breakout": donchian_channel_breakout,
    "volatility_adjusted_momentum": volatility_adjusted_momentum,
}


def hard_exclusion_mask(entry_ts: pd.Series, session_config: dict[str, Any]) -> pd.Series:
    mask = pd.Series(False, index=entry_ts.index)
    for window in session_config.get("hard_no_trade_windows", []):
        applies = {str(value).upper() for value in window.get("applies_to", ["*"])}
        if "*" not in applies and SYMBOL not in applies:
            continue
        local = entry_ts.dt.tz_convert(ZoneInfo(str(window["timezone"]))).dt.time
        start_time = parse_hhmm(str(window["start_local"]))
        end_time = parse_hhmm(str(window["end_local"]))
        current = (
            (local >= start_time) & (local < end_time)
            if start_time <= end_time
            else (local >= start_time) | (local < end_time)
        )
        mask |= current
    return mask


def load_bars(path: Path, expected_sha256: str) -> pd.DataFrame:
    assert sha256_file(path) == expected_sha256
    bars = pd.read_csv(path, compression="gzip")
    required = {
        "timestamp_utc", "symbol", "mid_open", "mid_high", "mid_low", "mid_close",
        "spread_open_pips", "spread_mean_pips",
    }
    assert required.issubset(bars.columns), sorted(required - set(bars.columns))
    bars = bars[list(required)].copy()
    bars["timestamp_utc"] = pd.to_datetime(bars["timestamp_utc"], utc=True, errors="raise")
    numeric = ["mid_open", "mid_high", "mid_low", "mid_close", "spread_open_pips", "spread_mean_pips"]
    for column in numeric:
        bars[column] = pd.to_numeric(bars[column], errors="raise")
    assert (bars["symbol"] == SYMBOL).all()
    assert not bars["timestamp_utc"].duplicated().any()
    assert bars["timestamp_utc"].is_monotonic_increasing
    assert bars["timestamp_utc"].min() < H1_END
    assert bars["timestamp_utc"].max() < H2_END
    bars = bars.reset_index(drop=True)
    bars["date_utc"] = bars["timestamp_utc"].dt.strftime("%Y-%m-%d")
    bars["month_utc"] = bars["timestamp_utc"].dt.strftime("%Y-%m")
    bars["hour_utc"] = bars["timestamp_utc"].dt.hour.astype(int)
    bars["minute_utc"] = bars["timestamp_utc"].dt.minute.astype(int)
    previous_close = bars["mid_close"].shift(1)
    bars["bar_range"] = bars["mid_high"] - bars["mid_low"]
    bars["true_range"] = pd.concat(
        [
            bars["bar_range"],
            (bars["mid_high"] - previous_close).abs(),
            (bars["mid_low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    bars["close_change"] = bars["mid_close"].diff()
    bars["bar_body"] = bars["mid_close"] - bars["mid_open"]
    return bars


def flatten_candidates(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for family_block in registry["families"]:
        family = str(family_block["family"])
        for raw in family_block["candidates"]:
            candidate = dict(raw)
            candidate["family"] = family
            digest = sha256_bytes(canonical_json(normalized_definition(candidate)))
            candidate["definition_sha256"] = digest
            assert candidate["id"] not in candidates
            candidates[str(candidate["id"])] = candidate
    return candidates


def finalize_signals(
    bars: pd.DataFrame,
    candidate: dict[str, Any],
    raw_side: pd.Series,
    session_config: dict[str, Any],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    work = pd.DataFrame(
        {
            "signal_ts_dt": bars["timestamp_utc"],
            "entry_ts_dt": bars["timestamp_utc"].shift(-1),
            "side": raw_side.fillna(0).astype("int8"),
        }
    )
    work = work[work["side"].isin([1, -1]) & work["entry_ts_dt"].notna()].copy()
    work = work[(work["entry_ts_dt"] >= start) & (work["entry_ts_dt"] < end)].copy()
    work = work[~hard_exclusion_mask(work["entry_ts_dt"], session_config)].copy()
    work["candidate_id"] = candidate["id"]
    work["family"] = candidate["family"]
    work["definition_sha256"] = candidate["definition_sha256"]
    work["signal_ts"] = work["signal_ts_dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    work["entry_ts"] = work["entry_ts_dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    work["signal_month"] = work["signal_ts_dt"].dt.strftime("%Y-%m")
    work["signal_hour_utc"] = work["signal_ts_dt"].dt.hour.astype(int)
    work["entry_month"] = work["entry_ts_dt"].dt.strftime("%Y-%m")
    work["entry_hour_utc"] = work["entry_ts_dt"].dt.hour.astype(int)
    columns = [
        "candidate_id", "family", "definition_sha256", "signal_ts", "entry_ts", "side",
        "signal_month", "signal_hour_utc", "entry_month", "entry_hour_utc",
    ]
    return work[columns].sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True)


def signal_key_hash(frame: pd.DataFrame) -> str:
    work = frame[["signal_ts", "entry_ts", "side"]].copy().sort_values(["signal_ts", "entry_ts", "side"])
    return sha256_bytes(work.to_csv(index=False, lineterminator="\n").encode("utf-8"))


def normalize_timestamp_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    work = frame.copy()
    for column in columns:
        work[column] = pd.to_datetime(work[column], utc=True, errors="raise").dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return work


def build_fixed_time_trades(
    bars: pd.DataFrame,
    signals: pd.DataFrame,
    strategy_specs: list[dict[str, Any]],
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> pd.DataFrame:
    timestamp_to_index = pd.Series(bars.index.to_numpy(), index=bars["timestamp_utc"]).to_dict()
    opens = bars["mid_open"].to_numpy(float)
    closes = bars["mid_close"].to_numpy(float)
    spreads = bars["spread_mean_pips"].to_numpy(float)
    timestamps = bars["timestamp_utc"].tolist()
    months = bars["month_utc"].to_numpy(str)
    dates = bars["date_utc"].to_numpy(str)
    spec_by_candidate = {row["candidate_id"]: row for row in strategy_specs}
    frames: list[pd.DataFrame] = []
    for candidate_id, group in signals.groupby("candidate_id", sort=False):
        spec = spec_by_candidate[str(candidate_id)]
        horizon = int(spec["time_cap_bars"])
        work = group.copy()
        work["entry_ts_dt"] = pd.to_datetime(work["entry_ts"], utc=True)
        work["signal_ts_dt"] = pd.to_datetime(work["signal_ts"], utc=True)
        work["entry_index"] = work["entry_ts_dt"].map(timestamp_to_index)
        assert work["entry_index"].notna().all()
        entry_indices = work["entry_index"].astype(int).to_numpy()
        exit_indices = entry_indices + horizon - 1
        valid = exit_indices < len(bars)
        valid &= np.array([timestamps[index] < period_end for index in exit_indices.clip(max=len(bars)-1)])
        valid &= np.array([timestamps[index] >= period_start for index in entry_indices])
        valid &= months[entry_indices] == months[exit_indices.clip(max=len(bars)-1)]
        positions = np.where(valid)[0]
        if len(positions) == 0:
            continue
        entry_indices = entry_indices[positions]
        exit_indices = exit_indices[positions]
        selected = work.iloc[positions].reset_index(drop=True)
        sides = selected["side"].astype(int).to_numpy()
        entry_mid = opens[entry_indices]
        exit_mid = closes[exit_indices]
        entry_spread = spreads[entry_indices]
        default_cost = np.maximum(0.5, entry_spread)
        severe_cost = default_cost * 3.0 + 1.0
        gross = sides * (exit_mid - entry_mid) / PIP
        frame = pd.DataFrame(
            {
                "freeze_rank": int(spec["freeze_rank"]),
                "strategy_id": spec["strategy_id"],
                "candidate_id": candidate_id,
                "family": spec["family"],
                "definition_sha256": spec["entry_definition_sha256"],
                "time_cap_bars": horizon,
                "policy_id": spec["policy_id"],
                "mechanism": spec["mechanism"],
                "signal_ts": selected["signal_ts"].to_numpy(),
                "entry_ts": selected["entry_ts"].to_numpy(),
                "exit_ts": [timestamps[index].strftime("%Y-%m-%dT%H:%M:%SZ") for index in exit_indices],
                "entry_month": months[entry_indices],
                "entry_date_utc": dates[entry_indices],
                "entry_quarter": np.where(np.isin(months[entry_indices], H2_MONTHS[:3]), "2024-Q3", "2024-Q4"),
                "side": sides,
                "entry_mid": entry_mid,
                "exit_mid": exit_mid,
                "entry_spread_pips": entry_spread,
                "bars_held": horizon,
                "gross_pips": gross,
                "default_cost_pips": default_cost,
                "severe_cost_pips": severe_cost,
                "default_net_pips": gross - default_cost,
                "severe_net_pips": gross - severe_cost,
            }
        )
        frames.append(frame)
    if not frames:
        raise AssertionError("no fixed-time trade rows")
    return pd.concat(frames, ignore_index=True).sort_values(["freeze_rank", "entry_ts", "side"]).reset_index(drop=True)


def compare_h1_signals(actual: pd.DataFrame, accepted_path: Path, candidate_ids: list[str]) -> pd.DataFrame:
    accepted = pd.read_csv(accepted_path, compression="gzip")
    accepted = accepted[accepted["candidate_id"].isin(candidate_ids)].copy()
    accepted = normalize_timestamp_columns(accepted, ["signal_ts", "entry_ts"])
    columns = [
        "candidate_id", "family", "definition_sha256", "signal_ts", "entry_ts", "side",
        "signal_month", "signal_hour_utc", "entry_month", "entry_hour_utc",
    ]
    accepted = accepted[columns].sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True)
    actual = actual[columns].sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True)
    # pandas dtype is not part of the accepted signal contract; normalize integer columns
    # before exact row comparison (accepted CSV loads side as int64, regenerated uses int8).
    for frame in (accepted, actual):
        frame["side"] = frame["side"].astype("int64")
        frame["signal_hour_utc"] = frame["signal_hour_utc"].astype("int64")
        frame["entry_hour_utc"] = frame["entry_hour_utc"].astype("int64")
    rows: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        left = accepted[accepted["candidate_id"] == candidate_id].reset_index(drop=True)
        right = actual[actual["candidate_id"] == candidate_id].reset_index(drop=True)
        rows.append(
            {
                "candidate_id": candidate_id,
                "accepted_rows": len(left),
                "regenerated_rows": len(right),
                "accepted_signal_key_sha256": signal_key_hash(left),
                "regenerated_signal_key_sha256": signal_key_hash(right),
                "exact_full_rows": left.equals(right),
                "passed": left.equals(right),
            }
        )
    result = pd.DataFrame(rows)
    assert result["passed"].all(), result.to_dict("records")
    return result


def compare_h1_trades(actual: pd.DataFrame, accepted_path: Path, candidate_ids: list[str]) -> pd.DataFrame:
    accepted = pd.read_csv(accepted_path, compression="gzip")
    accepted = accepted[(accepted["candidate_id"].isin(candidate_ids)) & (accepted["policy_id"] == "T0_fixed_time_cap")].copy()
    accepted = normalize_timestamp_columns(accepted, ["signal_ts", "entry_ts", "exit_ts"])
    actual = normalize_timestamp_columns(actual, ["signal_ts", "entry_ts", "exit_ts"])
    key_columns = [
        "candidate_id", "family", "definition_sha256", "time_cap_bars", "policy_id",
        "signal_ts", "entry_ts", "exit_ts", "side", "bars_held",
    ]
    numeric_columns = [
        "entry_mid", "exit_mid", "default_cost_pips", "severe_cost_pips",
        "gross_pips", "default_net_pips", "severe_net_pips",
    ]
    rows: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        left = accepted[accepted["candidate_id"] == candidate_id].sort_values(["entry_ts", "side"]).reset_index(drop=True)
        right = actual[actual["candidate_id"] == candidate_id].sort_values(["entry_ts", "side"]).reset_index(drop=True)
        key_equal = len(left) == len(right) and left[key_columns].equals(right[key_columns])
        numeric_equal = len(left) == len(right) and all(
            np.allclose(left[column].to_numpy(float), right[column].to_numpy(float), rtol=0.0, atol=1e-9, equal_nan=True)
            for column in numeric_columns
        )
        payload_columns = key_columns + numeric_columns
        left_payload = left[payload_columns].to_csv(index=False, lineterminator="\n", float_format="%.10f").encode("utf-8")
        right_payload = right[payload_columns].to_csv(index=False, lineterminator="\n", float_format="%.10f").encode("utf-8")
        rows.append(
            {
                "candidate_id": candidate_id,
                "accepted_rows": len(left),
                "regenerated_rows": len(right),
                "exact_keys": key_equal,
                "numeric_fields_equal_at_1e_9": numeric_equal,
                "accepted_trade_projection_sha256": sha256_bytes(left_payload),
                "regenerated_trade_projection_sha256": sha256_bytes(right_payload),
                "passed": key_equal and numeric_equal,
            }
        )
    result = pd.DataFrame(rows)
    assert result["passed"].all(), result.to_dict("records")
    return result


def aggregate_block(frame: pd.DataFrame) -> dict[str, float | int]:
    if frame.empty:
        return {
            "trades": 0,
            "avg_default_net_pips": 0.0,
            "total_default_net_pips": 0.0,
            "default_profit_factor": 0.0,
            "avg_severe_net_pips": 0.0,
            "total_severe_net_pips": 0.0,
            "severe_profit_factor": 0.0,
        }
    return {
        "trades": int(len(frame)),
        "avg_default_net_pips": float(frame["default_net_pips"].mean()),
        "total_default_net_pips": float(frame["default_net_pips"].sum()),
        "default_profit_factor": profit_factor(frame["default_net_pips"]),
        "avg_severe_net_pips": float(frame["severe_net_pips"].mean()),
        "total_severe_net_pips": float(frame["severe_net_pips"].sum()),
        "severe_profit_factor": profit_factor(frame["severe_net_pips"]),
    }


def concentration_metrics(frame: pd.DataFrame) -> dict[str, float]:
    monthly = frame.groupby("entry_month", sort=True)["default_net_pips"].sum().reindex(H2_MONTHS, fill_value=0.0)
    month_denominator = float(monthly.abs().sum())
    largest_month_share = 0.0 if month_denominator == 0.0 else float(monthly.abs().max() / month_denominator)
    daily = frame.groupby("entry_date_utc", sort=True)["default_net_pips"].sum()
    positives = daily[daily > 0].sort_values(ascending=False)
    positive_denominator = float(positives.sum())
    top_two_share = 0.0 if positive_denominator == 0.0 else float(positives.head(2).sum() / positive_denominator)
    total_ex_best_two = float(frame["default_net_pips"].sum() - daily.sort_values(ascending=False).head(2).sum())
    direction = frame.groupby("side", sort=True)["default_net_pips"].sum().reindex([-1, 1], fill_value=0.0)
    direction_denominator = float(direction.abs().sum())
    direction_share = 0.0 if direction_denominator == 0.0 else float(direction.abs().max() / direction_denominator)
    return {
        "total_excluding_best_two_utc_entry_dates": total_ex_best_two,
        "largest_absolute_month_contribution_share": largest_month_share,
        "top_two_utc_entry_dates_share_of_positive_daily_pips": top_two_share,
        "direction_absolute_contribution_share": direction_share,
    }


def build_reports(trades: pd.DataFrame, strategy_specs: list[dict[str, Any]], gates: dict[str, Any]) -> dict[str, Any]:
    summary_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    quarterly_rows: list[dict[str, Any]] = []
    daily_rows: list[dict[str, Any]] = []
    direction_rows: list[dict[str, Any]] = []
    gate_rows: list[dict[str, Any]] = []
    full_dates = pd.date_range(H2_START, H2_END - pd.Timedelta(days=1), freq="D", tz="UTC").strftime("%Y-%m-%d")

    for spec in strategy_specs:
        strategy_id = spec["strategy_id"]
        group = trades[trades["strategy_id"] == strategy_id].copy()
        aggregate = aggregate_block(group)
        concentration = concentration_metrics(group)
        monthly_metrics: dict[str, dict[str, Any]] = {}
        for month in H2_MONTHS:
            current = group[group["entry_month"] == month]
            block = aggregate_block(current)
            monthly_metrics[month] = block
            monthly_rows.append({"freeze_rank": spec["freeze_rank"], "strategy_id": strategy_id, "month": month, **block})
        quarter_metrics: dict[str, dict[str, Any]] = {}
        for quarter, months in QUARTERS.items():
            current = group[group["entry_month"].isin(months)]
            block = aggregate_block(current)
            quarter_metrics[quarter] = block
            quarterly_rows.append({"freeze_rank": spec["freeze_rank"], "strategy_id": strategy_id, "quarter": quarter, **block})
        daily = group.groupby("entry_date_utc", sort=True).agg(
            trades=("default_net_pips", "size"),
            default_net_pips=("default_net_pips", "sum"),
            severe_net_pips=("severe_net_pips", "sum"),
        ).reindex(full_dates, fill_value=0.0)
        for date, row in daily.iterrows():
            daily_rows.append(
                {
                    "freeze_rank": spec["freeze_rank"],
                    "strategy_id": strategy_id,
                    "entry_date_utc": date,
                    "trades": int(row["trades"]),
                    "default_net_pips": float(row["default_net_pips"]),
                    "severe_net_pips": float(row["severe_net_pips"]),
                }
            )
        for side in [-1, 1]:
            current = group[group["side"] == side]
            direction_rows.append({"freeze_rank": spec["freeze_rank"], "strategy_id": strategy_id, "side": side, **aggregate_block(current)})

        default_positive_months = sum(monthly_metrics[m]["total_default_net_pips"] > 0 for m in H2_MONTHS)
        severe_positive_months = sum(monthly_metrics[m]["total_severe_net_pips"] > 0 for m in H2_MONTHS)
        q_default = all(quarter_metrics[q]["total_default_net_pips"] > 0 for q in QUARTERS)
        q_severe = all(quarter_metrics[q]["total_severe_net_pips"] > 0 for q in QUARTERS)
        summary_rows.append(
            {
                "freeze_rank": spec["freeze_rank"],
                "strategy_id": strategy_id,
                "candidate_id": spec["candidate_id"],
                "family": spec["family"],
                "definition_sha256": spec["entry_definition_sha256"],
                "time_cap_bars": spec["time_cap_bars"],
                **aggregate,
                "default_positive_months": default_positive_months,
                "severe_positive_months": severe_positive_months,
                "Q3_and_Q4_default_positive": q_default,
                "Q3_and_Q4_severe_positive": q_severe,
                **concentration,
            }
        )

        gate_values = {
            "gate_minimum_trades": aggregate["trades"] >= int(gates["minimum_trades"]),
            "gate_avg_default_positive": aggregate["avg_default_net_pips"] > 0,
            "gate_avg_severe_positive": aggregate["avg_severe_net_pips"] > 0,
            "gate_default_profit_factor": aggregate["default_profit_factor"] > 1,
            "gate_severe_profit_factor": aggregate["severe_profit_factor"] > 1,
            "gate_default_positive_months": default_positive_months >= int(gates["minimum_default_positive_months"]),
            "gate_severe_positive_months": severe_positive_months >= int(gates["minimum_severe_positive_months"]),
            "gate_Q3_Q4_default_positive": q_default,
            "gate_Q3_Q4_severe_positive": q_severe,
            "gate_excluding_best_two_days_positive": concentration["total_excluding_best_two_utc_entry_dates"] > 0,
            "gate_largest_absolute_month_share": concentration["largest_absolute_month_contribution_share"] <= float(gates["maximum_largest_absolute_month_contribution_share"]),
            "gate_top_two_positive_days_share": concentration["top_two_utc_entry_dates_share_of_positive_daily_pips"] <= float(gates["maximum_top_two_utc_entry_dates_share_of_positive_daily_pips"]),
            "gate_direction_absolute_contribution_share": concentration["direction_absolute_contribution_share"] <= float(gates["maximum_direction_absolute_contribution_share"]),
        }
        failed = [key for key, value in gate_values.items() if not value]
        gate_rows.append(
            {
                "freeze_rank": spec["freeze_rank"],
                "strategy_id": strategy_id,
                **gate_values,
                "passed": not failed,
                "failure_reasons": "|".join(failed),
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values("freeze_rank").reset_index(drop=True)
    monthly = pd.DataFrame(monthly_rows).sort_values(["freeze_rank", "month"]).reset_index(drop=True)
    quarterly = pd.DataFrame(quarterly_rows).sort_values(["freeze_rank", "quarter"]).reset_index(drop=True)
    daily = pd.DataFrame(daily_rows).sort_values(["freeze_rank", "entry_date_utc"]).reset_index(drop=True)
    direction = pd.DataFrame(direction_rows).sort_values(["freeze_rank", "side"]).reset_index(drop=True)
    gate_results = pd.DataFrame(gate_rows).sort_values("freeze_rank").reset_index(drop=True)

    weight = 1.0 / len(strategy_specs)
    portfolio_daily = daily.groupby("entry_date_utc", sort=True).agg(
        default_net_pips=("default_net_pips", "sum"),
        severe_net_pips=("severe_net_pips", "sum"),
    ) * weight
    portfolio_daily["month"] = pd.Index(portfolio_daily.index).str.slice(0, 7)
    portfolio_monthly = portfolio_daily.groupby("month")[["default_net_pips", "severe_net_pips"]].sum().reindex(H2_MONTHS, fill_value=0.0)

    def maximum_drawdown(values: pd.Series) -> float:
        cumulative = values.cumsum()
        drawdown = cumulative.cummax() - cumulative
        return float(drawdown.max()) if not drawdown.empty else 0.0

    portfolio = pd.DataFrame(
        [
            {
                "strategy_count": len(strategy_specs),
                "strategy_weight": weight,
                "total_default_pips": float(portfolio_daily["default_net_pips"].sum()),
                "total_severe_pips": float(portfolio_daily["severe_net_pips"].sum()),
                "positive_default_months": int((portfolio_monthly["default_net_pips"] > 0).sum()),
                "positive_severe_months": int((portfolio_monthly["severe_net_pips"] > 0).sum()),
                "maximum_default_drawdown_pips": maximum_drawdown(portfolio_daily["default_net_pips"]),
                "maximum_severe_drawdown_pips": maximum_drawdown(portfolio_daily["severe_net_pips"]),
                "individual_gate_role": False,
            }
        ]
    )
    return {
        "summary": summary,
        "monthly": monthly,
        "quarterly": quarterly,
        "daily": daily,
        "direction": direction,
        "gate_results": gate_results,
        "portfolio": portfolio,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r0-release-zip", required=True, type=Path)
    parser.add_argument("--r1-release-zip", required=True, type=Path)
    parser.add_argument("--r5-release-zip", required=True, type=Path)
    parser.add_argument("--r6-release-zip", required=True, type=Path)
    parser.add_argument("--canonical-m15", required=True, type=Path)
    parser.add_argument("--r1-registry", required=True, type=Path)
    parser.add_argument("--r1-signals", required=True, type=Path)
    parser.add_argument("--r5-exit-trades", required=True, type=Path)
    parser.add_argument("--r6-frozen", required=True, type=Path)
    parser.add_argument("--r6-h2-plan", required=True, type=Path)
    parser.add_argument("--r6-acceptance", required=True, type=Path)
    parser.add_argument("--session-config", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    input_hashes = {
        "r0_release_zip": sha256_file(args.r0_release_zip),
        "r1_release_zip": sha256_file(args.r1_release_zip),
        "r5_release_zip": sha256_file(args.r5_release_zip),
        "r6_release_zip": sha256_file(args.r6_release_zip),
        "canonical_m15": sha256_file(args.canonical_m15),
        "r1_registry": sha256_file(args.r1_registry),
        "r1_signals": sha256_file(args.r1_signals),
        "r5_exit_trades": sha256_file(args.r5_exit_trades),
        "r6_frozen": sha256_file(args.r6_frozen),
        "r6_h2_plan": sha256_file(args.r6_h2_plan),
        "r6_acceptance": sha256_file(args.r6_acceptance),
        "session_config": sha256_file(args.session_config),
        "config": sha256_file(args.config),
    }
    assert input_hashes["r0_release_zip"] == config["inputs"]["r0"]["release_asset_sha256"]
    assert input_hashes["r1_release_zip"] == config["inputs"]["r1"]["release_asset_sha256"]
    assert input_hashes["r5_release_zip"] == config["inputs"]["r5"]["release_asset_sha256"]
    assert input_hashes["r6_release_zip"] == config["inputs"]["r6"]["release_asset_sha256"]
    assert input_hashes["canonical_m15"] == config["inputs"]["r0"]["canonical_m15_gzip_sha256"]
    assert input_hashes["r1_registry"] == config["inputs"]["r1"]["registry_snapshot_sha256"]
    assert input_hashes["r1_signals"] == config["inputs"]["r1"]["h1_signal_ledger_sha256"]
    assert input_hashes["r5_exit_trades"] == config["inputs"]["r5"]["exit_trades_sha256"]
    assert input_hashes["r6_frozen"] == config["inputs"]["r6"]["frozen_complete_strategies_sha256"]
    assert input_hashes["r6_h2_plan"] == config["inputs"]["r6"]["h2_validation_plan_sha256"]
    assert input_hashes["r6_acceptance"] == config["inputs"]["r6"]["r6_acceptance_sha256"]

    r6_acceptance = json.loads(args.r6_acceptance.read_text())
    assert r6_acceptance["status"] == "PASS"
    assert all(value is True for key, value in r6_acceptance.items() if key != "status")
    r6_plan = json.loads(args.r6_h2_plan.read_text())
    assert r6_plan["strategy_count"] == 5
    assert r6_plan["strategies"] == config["strategies"]
    assert set(config["forbidden_previously_opened_complete_strategies"]).isdisjoint(
        {row["strategy_id"] for row in config["strategies"]}
    )
    r6_frozen = pd.read_csv(args.r6_frozen)
    assert list(r6_frozen["strategy_id"]) == [row["strategy_id"] for row in config["strategies"]]

    registry = json.loads(args.r1_registry.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))
    all_candidates = flatten_candidates(registry)
    strategy_specs = sorted(config["strategies"], key=lambda row: int(row["freeze_rank"]))
    candidate_ids = [row["candidate_id"] for row in strategy_specs]
    candidates = [all_candidates[candidate_id] for candidate_id in candidate_ids]
    for spec, candidate in zip(strategy_specs, candidates):
        assert spec["family"] == candidate["family"]
        assert spec["entry_definition_sha256"] == candidate["definition_sha256"]
        assert spec["policy_id"] == "T0_fixed_time_cap"
        assert spec["mechanism"] == "fixed_time"

    bars = load_bars(args.canonical_m15, config["inputs"]["r0"]["canonical_m15_gzip_sha256"])
    h1_ledgers: list[pd.DataFrame] = []
    h2_ledgers: list[pd.DataFrame] = []
    for candidate in candidates:
        function = SIGNAL_FUNCTIONS[candidate["family"]]
        raw_side = function(bars, candidate)
        h1_ledgers.append(finalize_signals(bars, candidate, raw_side, session_config, H1_START, H1_END))
        h2_ledgers.append(finalize_signals(bars, candidate, raw_side, session_config, H2_START, H2_END))
    h1_signals = pd.concat(h1_ledgers, ignore_index=True).sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True)
    h2_signals = pd.concat(h2_ledgers, ignore_index=True).sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True)

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    h1_signal_regression = compare_h1_signals(h1_signals, args.r1_signals, candidate_ids)
    write_csv(h1_signal_regression, output / "h1_signal_regression.csv")

    h1_trades = build_fixed_time_trades(bars, h1_signals, strategy_specs, H1_START, H1_END)
    h1_trade_regression = compare_h1_trades(h1_trades, args.r5_exit_trades, candidate_ids)
    write_csv(h1_trade_regression, output / "h1_trade_regression.csv")

    # H2 trade outcomes are calculated only after both regression assertions above have passed.
    h2_trades = build_fixed_time_trades(bars, h2_signals, strategy_specs, H2_START, H2_END)
    reports = build_reports(h2_trades, strategy_specs, config["individual_strategy_gates"])

    write_gzip_csv(h2_signals, output / "h2_candidate_signals.csv.gz")
    write_gzip_csv(h2_trades, output / "h2_candidate_trades.csv.gz")
    write_csv(reports["summary"], output / "h2_candidate_summary.csv")
    write_csv(reports["monthly"], output / "h2_candidate_monthly.csv")
    write_csv(reports["quarterly"], output / "h2_candidate_quarterly.csv")
    write_csv(reports["daily"], output / "h2_daily_net_pips.csv")
    write_csv(reports["direction"], output / "h2_direction_attribution.csv")
    write_csv(reports["gate_results"], output / "h2_gate_results.csv")
    write_csv(reports["portfolio"], output / "h2_joint_portfolio_diagnostic.csv")

    passed_ids = reports["gate_results"].loc[reports["gate_results"]["passed"], "strategy_id"].tolist()
    failed_ids = reports["gate_results"].loc[~reports["gate_results"]["passed"], "strategy_id"].tolist()
    decision = {
        "version": "v1",
        "status": "PASS",
        "h2_exposure_ordinal": config["h2_exposure_log"]["current_exposure_ordinal"],
        "strategy_count": 5,
        "passed_strategy_count": len(passed_ids),
        "failed_strategy_count": len(failed_ids),
        "passed_strategy_ids": passed_ids,
        "failed_strategy_ids": failed_ids,
        "decision": "advance_passed_strategies_to_parity" if passed_ids else "return_to_H1_new_preregistered_branch",
        "H2_reusable_fixed_validation_gate": True,
        "same_failed_exact_strategy_rescue": False,
        "2025_access": False,
        "Core_promotion_in_V1": False,
        "MT4_promotion_in_V1": False,
    }
    (output / "h2_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n")

    required = config["required_outputs"]
    acceptance = {
        "status": "PASS",
        "exact_input_digests_match": True,
        "R6_cohort_exactly_five_and_unchanged": len(strategy_specs) == 5 and r6_plan["strategies"] == strategy_specs,
        "forbidden_previously_opened_complete_strategies_absent": set(config["forbidden_previously_opened_complete_strategies"]).isdisjoint({row["strategy_id"] for row in strategy_specs}),
        "H1_signal_regressions_5_of_5": len(h1_signal_regression) == 5 and bool(h1_signal_regression["passed"].all()),
        "H1_T0_trade_regressions_5_of_5": len(h1_trade_regression) == 5 and bool(h1_trade_regression["passed"].all()),
        "H2_signal_candidates_exactly_five": h2_signals["candidate_id"].nunique() == 5,
        "H2_trade_strategies_exactly_five": h2_trades["strategy_id"].nunique() == 5,
        "monthly_grid_5_by_6": len(reports["monthly"]) == 30,
        "quarterly_grid_5_by_2": len(reports["quarterly"]) == 10,
        "direction_grid_5_by_2": len(reports["direction"]) == 10,
        "daily_grid_5_by_184": len(reports["daily"]) == 5 * 184,
        "gate_rows_exactly_five": len(reports["gate_results"]) == 5,
        "pass_fail_is_exact_gate_conjunction": all(
            bool(row["passed"]) == all(bool(row[column]) for column in reports["gate_results"].columns if column.startswith("gate_"))
            for _, row in reports["gate_results"].iterrows()
        ),
        "joint_portfolio_diagnostic_not_individual_gate": reports["portfolio"].iloc[0]["individual_gate_role"] in [False, np.bool_(False)],
        "H2_ranking_false": config["research_firewall"]["H2_ranking"] is False,
        "H2_parameter_optimization_false": config["research_firewall"]["H2_parameter_optimization"] is False,
        "reusable_H2_policy_preserved": config["reusable_validation_policy"]["new_H1_optimized_or_hypothesis_branch_may_reuse_same_H2"] is True,
        "H2_exposure_ordinal_2_logged": config["h2_exposure_log"]["current_exposure_ordinal"] == 2,
        "2025_access_false": config["research_firewall"]["2025_access"] is False,
        "Core_and_MT4_promotion_false": config["research_firewall"]["Core_promotion"] is False and config["research_firewall"]["MT4_promotion"] is False,
    }
    assert all(value is True for key, value in acceptance.items() if key != "status"), acceptance
    (output / "v1_acceptance.json").write_text(json.dumps(acceptance, indent=2, sort_keys=True) + "\n")

    output_hashes = {
        name: sha256_file(output / name)
        for name in required
        if name not in {"run_metadata.json"} and (output / name).is_file()
    }
    metadata = {
        "version": "v1",
        "research_stage": config["research_stage"],
        "status": "PASS",
        "H2_exposure_ordinal": 2,
        "input_sha256": input_hashes,
        "output_sha256": output_hashes,
        "H1_signal_regressions_passed": int(h1_signal_regression["passed"].sum()),
        "H1_trade_regressions_passed": int(h1_trade_regression["passed"].sum()),
        "H2_signal_rows": int(len(h2_signals)),
        "H2_trade_rows": int(len(h2_trades)),
        "passed_strategy_count": len(passed_ids),
        "failed_strategy_count": len(failed_ids),
        "passed_strategy_ids": passed_ids,
        "failed_strategy_ids": failed_ids,
        "H2_ranking": False,
        "H2_parameter_optimization": False,
        "H2_reusable_fixed_validation_gate": True,
        "2025_artifact_access": False,
        "Core_promotion": False,
        "MT4_promotion": False,
        "next_stage": decision["decision"],
    }
    (output / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    for name in required:
        assert (output / name).is_file() and (output / name).stat().st_size > 0, name
    print(json.dumps({"V1": "PASS", "H2_exposure": 2, "trades": len(h2_trades), "passed": len(passed_ids), "failed": len(failed_ids)}, sort_keys=True))


if __name__ == "__main__":
    main()
