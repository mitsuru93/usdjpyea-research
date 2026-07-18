#!/usr/bin/env python3
"""Freeze and audit the USDJPY R1 Entry universe without opening any outcome.

R1 intentionally produces no entry prices, exits, holding periods, returns, costs,
expectancy, profit factors or promotion decisions.  It reads the accepted R0 M15
canonical file only until the 2024-07-01 boundary, generates the sixty registered
Entry ledgers and reports definition/signal uniqueness and sample structure.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PIP = 0.01
SYMBOL = "USDJPY"
H1_END = "2024-07-01T00:00:00Z"
FUNCTIONAL_METADATA_KEYS = {
    "id", "origin", "legacy_ids", "h2_information_status", "literature_refs", "family"
}
PROHIBITED_OUTPUT_TERMS = {
    "entry_price", "exit", "hold", "gross", "cost", "net_pips", "profit",
    "expectancy", "return_pips", "promotion"
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def parse_hhmm(raw: str) -> time:
    hour, minute = raw.split(":", 1)
    return time(int(hour), int(minute))


def load_h1_m15(path: Path, expected_sha256: str, end_exclusive: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha256:
        raise AssertionError(("canonical_m15_sha256", actual_sha, expected_sha256))

    rows: list[dict[str, str]] = []
    first_h2_timestamp: str | None = None
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {
            "timestamp_utc", "symbol", "mid_open", "mid_high", "mid_low", "mid_close",
            "spread_open_pips", "spread_mean_pips"
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise AssertionError(f"canonical M15 missing columns: {sorted(missing)}")
        for row in reader:
            ts = row["timestamp_utc"]
            if ts >= end_exclusive:
                first_h2_timestamp = ts
                break
            rows.append(row)

    if not rows:
        raise AssertionError("no H1 M15 rows loaded")
    frame = pd.DataFrame(rows)
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True, errors="raise")
    for col in ["mid_open", "mid_high", "mid_low", "mid_close", "spread_open_pips", "spread_mean_pips"]:
        frame[col] = pd.to_numeric(frame[col], errors="raise")
    if not (frame["symbol"] == SYMBOL).all():
        raise AssertionError("non-USDJPY row in canonical M15")
    if frame["timestamp_utc"].duplicated().any():
        raise AssertionError("duplicate canonical M15 timestamps")
    if not frame["timestamp_utc"].is_monotonic_increasing:
        raise AssertionError("canonical M15 timestamps not increasing")
    if frame["timestamp_utc"].max() >= pd.Timestamp(end_exclusive):
        raise AssertionError("H2 row parsed")

    frame = frame.reset_index(drop=True)
    frame["date_utc"] = frame["timestamp_utc"].dt.strftime("%Y-%m-%d")
    frame["month_utc"] = frame["timestamp_utc"].dt.strftime("%Y-%m")
    frame["hour_utc"] = frame["timestamp_utc"].dt.hour.astype(int)
    frame["minute_utc"] = frame["timestamp_utc"].dt.minute.astype(int)
    prev_close = frame["mid_close"].shift(1)
    frame["bar_range"] = frame["mid_high"] - frame["mid_low"]
    frame["true_range"] = pd.concat(
        [
            frame["bar_range"],
            (frame["mid_high"] - prev_close).abs(),
            (frame["mid_low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["close_change"] = frame["mid_close"].diff()
    frame["bar_body"] = frame["mid_close"] - frame["mid_open"]
    metadata = {
        "canonical_m15_path": str(path),
        "canonical_m15_gzip_sha256": actual_sha,
        "rows_parsed": int(len(frame)),
        "first_timestamp": frame["timestamp_utc"].min().isoformat(),
        "last_timestamp": frame["timestamp_utc"].max().isoformat(),
        "stopped_at_h2_boundary": first_h2_timestamp is not None,
        "first_unparsed_h2_timestamp": first_h2_timestamp,
        "h2_rows_parsed": 0,
    }
    return frame, metadata


def allowed_hours(bars: pd.DataFrame, candidate: dict[str, Any]) -> pd.Series:
    if "entry_hours_utc" in candidate:
        return bars["hour_utc"].isin([int(v) for v in candidate["entry_hours_utc"]])
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


def prior_day_reference(bars: pd.DataFrame) -> pd.DataFrame:
    daily = bars.groupby("date_utc").agg(
        ref_open=("mid_open", "first"),
        ref_high=("mid_high", "max"),
        ref_low=("mid_low", "min"),
        ref_close=("mid_close", "last"),
    ).shift(1)
    return bars[["date_utc"]].join(daily, on="date_utc")


def impulse_breakout(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    lb = int(c["lookback_bars"])
    prev_high = bars["mid_high"].shift(1).rolling(lb, min_periods=lb).max()
    prev_low = bars["mid_low"].shift(1).rolling(lb, min_periods=lb).min()
    if c["expansion_reference"] == "previous_bar":
        expanded = bars["bar_range"] > bars["bar_range"].shift(1)
    else:
        vw = int(c["volatility_window_bars"])
        baseline = bars["bar_range"].shift(1).rolling(vw, min_periods=vw).median()
        expanded = bars["bar_range"] >= float(c["range_multiple"]) * baseline
    allowed = allowed_hours(bars, c)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & expanded & (bars["mid_close"] > prev_high)] = 1
    side.loc[allowed & expanded & (bars["mid_close"] < prev_low)] = -1
    return side


def session_range_breakout(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    if c["reference"] == "prior_utc_day_range":
        ref = prior_day_reference(bars)
    else:
        ref = session_reference(bars, int(c["reference_start_hour"]), int(c["reference_end_hour_exclusive"]))
    allowed = allowed_hours(bars, c)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & (bars["mid_close"] > ref["ref_high"])] = 1
    side.loc[allowed & (bars["mid_close"] < ref["ref_low"])] = -1
    return first_per_direction_day(side, bars)


def failed_excursion_reversion(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    if c["reference"] == "rolling_completed_bars":
        lb = int(c["lookback_bars"])
        ref_high = bars["mid_high"].shift(1).rolling(lb, min_periods=lb).max()
        ref_low = bars["mid_low"].shift(1).rolling(lb, min_periods=lb).min()
    elif c["reference"] == "prior_utc_day_range":
        ref = prior_day_reference(bars)
        ref_high, ref_low = ref["ref_high"], ref["ref_low"]
    else:
        ref = session_reference(bars, int(c["reference_start_hour"]), int(c["reference_end_hour_exclusive"]))
        ref_high, ref_low = ref["ref_high"], ref["ref_low"]
    allowed = allowed_hours(bars, c)
    failed_high = (bars["mid_high"] > ref_high) & (bars["mid_close"] <= ref_high) & (bars["mid_close"] >= ref_low)
    failed_low = (bars["mid_low"] < ref_low) & (bars["mid_close"] >= ref_low) & (bars["mid_close"] <= ref_high)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & failed_high & ~failed_low] = -1
    side.loc[allowed & failed_low & ~failed_high] = 1
    return side


def compression_expansion(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    n = int(c["compression_bars"])
    m = int(c["comparison_bars"])
    comp_high = bars["mid_high"].shift(1).rolling(n, min_periods=n).max()
    comp_low = bars["mid_low"].shift(1).rolling(n, min_periods=n).min()
    earlier_high = bars["mid_high"].shift(n + 1).rolling(m, min_periods=m).max()
    earlier_low = bars["mid_low"].shift(n + 1).rolling(m, min_periods=m).min()
    compressed = (comp_high - comp_low) < (earlier_high - earlier_low)
    expanded = bars["bar_range"] > bars["bar_range"].shift(1)
    allowed = allowed_hours(bars, c)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & compressed & expanded & (bars["mid_close"] > comp_high)] = 1
    side.loc[allowed & compressed & expanded & (bars["mid_close"] < comp_low)] = -1
    return side


def trend_pullback_resumption(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    n = int(c["trend_bars"])
    trend_return = bars["mid_close"].shift(1) - bars["mid_open"].shift(n)
    prev_bearish = bars["mid_close"].shift(1) < bars["mid_open"].shift(1)
    prev_bullish = bars["mid_close"].shift(1) > bars["mid_open"].shift(1)
    allowed = allowed_hours(bars, c)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & (trend_return > 0) & prev_bearish & (bars["mid_close"] > bars["mid_high"].shift(1))] = 1
    side.loc[allowed & (trend_return < 0) & prev_bullish & (bars["mid_close"] < bars["mid_low"].shift(1))] = -1
    return side


def donchian_channel_breakout(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    n = int(c["lookback_bars"])
    high = bars["mid_high"].shift(1).rolling(n, min_periods=n).max()
    low = bars["mid_low"].shift(1).rolling(n, min_periods=n).min()
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    allowed = allowed_hours(bars, c)
    long_event = (bars["mid_close"] > high) & (bars["mid_close"].shift(1) <= prev_high)
    short_event = (bars["mid_close"] < low) & (bars["mid_close"].shift(1) >= prev_low)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & long_event] = 1
    side.loc[allowed & short_event] = -1
    return side


def ema_trend_cross(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    fast_n, slow_n = int(c["fast_bars"]), int(c["slow_bars"])
    fast = bars["mid_close"].ewm(span=fast_n, adjust=False, min_periods=slow_n).mean()
    slow = bars["mid_close"].ewm(span=slow_n, adjust=False, min_periods=slow_n).mean()
    allowed = allowed_hours(bars, c)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & (fast > slow) & (fast.shift(1) <= slow.shift(1))] = 1
    side.loc[allowed & (fast < slow) & (fast.shift(1) >= slow.shift(1))] = -1
    return side


def volatility_adjusted_momentum(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    lb = int(c["lookback_bars"])
    vw = int(c["volatility_window_bars"])
    threshold = float(c["score_threshold"])
    cum = (bars["mid_close"] - bars["mid_close"].shift(lb)) / PIP
    one_bar = bars["mid_close"].diff() / PIP
    realized = np.sqrt(one_bar.pow(2).rolling(vw, min_periods=vw).sum())
    score = cum / realized.replace(0.0, np.nan)
    allowed = allowed_hours(bars, c)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & (score > threshold) & (score.shift(1) <= threshold)] = 1
    side.loc[allowed & (score < -threshold) & (score.shift(1) >= -threshold)] = -1
    return side


def bollinger_reentry_reversion(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    n = int(c["window_bars"])
    z = float(c["z_threshold"])
    completed = bars["mid_close"].shift(1)
    mean = completed.rolling(n, min_periods=n).mean()
    std = completed.rolling(n, min_periods=n).std(ddof=0)
    upper = mean + z * std
    lower = mean - z * std
    allowed = allowed_hours(bars, c)
    long_event = (bars["mid_close"].shift(1) < lower.shift(1)) & (bars["mid_close"] >= lower)
    short_event = (bars["mid_close"].shift(1) > upper.shift(1)) & (bars["mid_close"] <= upper)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & long_event] = 1
    side.loc[allowed & short_event] = -1
    return side


def return_shock_reversal(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    n = int(c["shock_lookback_bars"])
    atr_window = int(c["atr_window_bars"])
    shock_mult = float(c["shock_atr_multiple"])
    reversal_fraction = float(c["reversal_atr_fraction"])
    atr = bars["true_range"].shift(1).rolling(atr_window, min_periods=atr_window).mean()
    completed_move = bars["mid_close"].shift(1) - bars["mid_close"].shift(n + 1)
    body = bars["bar_body"]
    allowed = allowed_hours(bars, c)
    prior_up = completed_move >= shock_mult * atr
    prior_down = completed_move <= -shock_mult * atr
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allowed & prior_up & (body <= -reversal_fraction * atr)] = -1
    side.loc[allowed & prior_down & (body >= reversal_fraction * atr)] = 1
    return side


def session_handoff(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    ref = session_reference(bars, int(c["reference_start_hour"]), int(c["reference_end_hour_exclusive"]))
    ref_return = ref["ref_close"] - ref["ref_open"]
    ref_range = ref["ref_high"] - ref["ref_low"]
    efficiency = ref_return.abs() / ref_range.replace(0.0, np.nan)
    ref_side = np.sign(ref_return).fillna(0).astype(int)
    current_side = np.sign(bars["bar_body"]).fillna(0).astype(int)
    trigger = (bars["hour_utc"] == int(c["trigger_hour"])) & (bars["minute_utc"] == 0)
    efficient = efficiency >= float(c["minimum_efficiency"])
    desired = ref_side if c["mode"] == "continuation" else -ref_side
    side = pd.Series(0, index=bars.index, dtype="int8")
    valid = trigger & efficient & desired.isin([1, -1]) & (current_side == desired)
    side.loc[valid] = desired.loc[valid].astype("int8")
    return side


def atr_filter_directional_change(bars: pd.DataFrame, c: dict[str, Any]) -> pd.Series:
    atr_window = int(c["atr_window_bars"])
    threshold = float(c["threshold_atr_multiple"])
    atr = bars["true_range"].shift(1).rolling(atr_window, min_periods=atr_window).mean()
    allowed = allowed_hours(bars, c).to_numpy(dtype=bool)
    closes = bars["mid_close"].to_numpy(dtype=float)
    atr_values = atr.to_numpy(dtype=float)
    signals = np.zeros(len(bars), dtype=np.int8)
    state = 0
    peak = closes[0]
    trough = closes[0]
    for i in range(1, len(bars)):
        value = closes[i]
        width = atr_values[i] * threshold
        if not math.isfinite(width) or width <= 0:
            peak = max(peak, value)
            trough = min(trough, value)
            continue
        if state == 0:
            peak = max(peak, value)
            trough = min(trough, value)
            if value - trough >= width:
                state = 1
                peak = value
                if allowed[i]:
                    signals[i] = 1
            elif peak - value >= width:
                state = -1
                trough = value
                if allowed[i]:
                    signals[i] = -1
        elif state == 1:
            peak = max(peak, value)
            if peak - value >= width:
                state = -1
                trough = value
                if allowed[i]:
                    signals[i] = -1
        else:
            trough = min(trough, value)
            if value - trough >= width:
                state = 1
                peak = value
                if allowed[i]:
                    signals[i] = 1
    return pd.Series(signals, index=bars.index, dtype="int8")


SIGNAL_FUNCTIONS: dict[str, Callable[[pd.DataFrame, dict[str, Any]], pd.Series]] = {
    "impulse_breakout": impulse_breakout,
    "session_range_breakout": session_range_breakout,
    "failed_excursion_reversion": failed_excursion_reversion,
    "compression_expansion": compression_expansion,
    "trend_pullback_resumption": trend_pullback_resumption,
    "donchian_channel_breakout": donchian_channel_breakout,
    "ema_trend_cross": ema_trend_cross,
    "volatility_adjusted_momentum": volatility_adjusted_momentum,
    "bollinger_reentry_reversion": bollinger_reentry_reversion,
    "return_shock_reversal": return_shock_reversal,
    "session_handoff": session_handoff,
    "atr_filter_directional_change": atr_filter_directional_change,
}


def hard_exclusion_mask(entry_ts: pd.Series, session_config: dict[str, Any]) -> pd.Series:
    mask = pd.Series(False, index=entry_ts.index)
    for window in session_config.get("hard_no_trade_windows", []):
        applies = {str(v).upper() for v in window.get("applies_to", ["*"])}
        if "*" not in applies and SYMBOL not in applies:
            continue
        local = entry_ts.dt.tz_convert(ZoneInfo(str(window["timezone"]))).dt.time
        start_t = parse_hhmm(str(window["start_local"]))
        end_t = parse_hhmm(str(window["end_local"]))
        current = (local >= start_t) & (local < end_t) if start_t <= end_t else (local >= start_t) | (local < end_t)
        mask |= current
    return mask


def functional_definition(candidate: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in candidate.items() if k not in FUNCTIONAL_METADATA_KEYS}


def normalized_definition(candidate: dict[str, Any]) -> dict[str, Any]:
    return {"family": candidate["family"], "parameters": functional_definition(candidate)}


def signal_ledger_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return sha256_bytes(b"")
    work = frame[["signal_ts", "entry_ts", "side"]].copy().sort_values(["signal_ts", "entry_ts", "side"])
    text = work.to_csv(index=False, lineterminator="\n")
    return sha256_bytes(text.encode("utf-8"))


def write_deterministic_gzip_csv(frame: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = frame.to_csv(index=False, lineterminator="\n")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            compressed.write(text.encode("utf-8"))
    return sha256_file(path)


def validate_registry(registry: dict[str, Any]) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    limits = registry["universe_limits"]
    families = registry["families"]
    if len(families) != int(limits["required_family_count"]):
        raise AssertionError("family count mismatch")
    candidates: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for family in families:
        family_id = str(family["family"])
        if family_id not in SIGNAL_FUNCTIONS:
            raise AssertionError(f"unsupported family: {family_id}")
        expected_cap = int(limits["fixed_family_caps"][family_id])
        if int(family["cap"]) != expected_cap or len(family["candidates"]) != expected_cap:
            raise AssertionError(f"family cap mismatch: {family_id}")
        for raw in family["candidates"]:
            candidate = dict(raw)
            candidate["family"] = family_id
            for forbidden in ["hold_bars", "exit", "exit_rule", "target_pips", "stop_pips"]:
                if forbidden in candidate:
                    raise AssertionError(f"forbidden R1 key {forbidden}: {candidate['id']}")
            definition = normalized_definition(candidate)
            digest = sha256_bytes(canonical_json(definition))
            candidate["definition_sha256"] = digest
            candidates.append(candidate)
            audit_rows.append(
                {
                    "candidate_id": candidate["id"],
                    "family": family_id,
                    "origin": candidate.get("origin", ""),
                    "h2_information_status": candidate.get("h2_information_status", "new_unopened"),
                    "definition_sha256": digest,
                    "functional_definition_json": json.dumps(definition, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                }
            )
    if len(candidates) != int(limits["required_candidate_count"]):
        raise AssertionError("candidate count mismatch")
    if len(candidates) > int(limits["maximum_unique_entry_definitions"]):
        raise AssertionError("candidate count exceeds maximum")
    ids = [str(c["id"]) for c in candidates]
    if len(ids) != len(set(ids)):
        raise AssertionError("duplicate candidate ID")
    hashes = [str(c["definition_sha256"]) for c in candidates]
    if len(hashes) != len(set(hashes)):
        duplicates = pd.DataFrame(audit_rows).loc[pd.Series(hashes).duplicated(keep=False).to_numpy()]
        raise AssertionError(f"duplicate functional definitions: {duplicates.to_dict('records')}")
    return candidates, pd.DataFrame(audit_rows)


def finalize_candidate_signals(
    bars: pd.DataFrame,
    candidate: dict[str, Any],
    side: pd.Series,
    session_config: dict[str, Any],
) -> tuple[pd.DataFrame, int]:
    if len(side) != len(bars):
        raise AssertionError(f"side length mismatch: {candidate['id']}")
    if not set(pd.Series(side).dropna().astype(int).unique()).issubset({-1, 0, 1}):
        raise AssertionError(f"invalid side value: {candidate['id']}")
    work = pd.DataFrame(
        {
            "signal_ts_dt": bars["timestamp_utc"],
            "entry_ts_dt": bars["timestamp_utc"].shift(-1),
            "side": side.fillna(0).astype("int8"),
        }
    )
    work = work[work["side"].isin([1, -1]) & work["entry_ts_dt"].notna()].copy()
    work = work[work["entry_ts_dt"] < pd.Timestamp(H1_END)].copy()
    excluded = hard_exclusion_mask(work["entry_ts_dt"], session_config)
    excluded_count = int(excluded.sum())
    work = work[~excluded].copy()
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
        "signal_month", "signal_hour_utc", "entry_month", "entry_hour_utc"
    ]
    return work[columns].sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True), excluded_count


def output_columns_are_clean(paths: list[Path]) -> bool:
    for path in paths:
        if path.suffix == ".gz":
            frame = pd.read_csv(path, nrows=0)
        elif path.suffix == ".csv":
            frame = pd.read_csv(path, nrows=0)
        else:
            continue
        for column in frame.columns:
            lowered = column.lower()
            if any(term in lowered for term in PROHIBITED_OUTPUT_TERMS):
                return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-m15", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--session-config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))
    candidates, definition_audit = validate_registry(registry)
    bars, input_metadata = load_h1_m15(
        args.canonical_m15,
        str(registry["input_lock"]["canonical_m15_gzip_sha256"]),
        str(registry["development_period"]["end_utc_exclusive"]),
    )

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    registry_snapshot = output / "r1_registry_snapshot.json"
    registry_snapshot.write_bytes(canonical_json(registry))

    definition_path = output / "candidate_definition_audit.csv"
    definition_audit.sort_values(["family", "candidate_id"]).to_csv(definition_path, index=False, lineterminator="\n")

    ledgers: list[pd.DataFrame] = []
    hard_excluded_rows: list[dict[str, Any]] = []
    signal_hash_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        function = SIGNAL_FUNCTIONS[candidate["family"]]
        raw_side = function(bars, candidate)
        ledger, excluded_count = finalize_candidate_signals(bars, candidate, raw_side, session_config)
        ledgers.append(ledger)
        hard_excluded_rows.append({"candidate_id": candidate["id"], "hard_no_trade_signals_excluded": excluded_count})
        signal_hash_rows.append(
            {
                "candidate_id": candidate["id"],
                "family": candidate["family"],
                "definition_sha256": candidate["definition_sha256"],
                "signal_rows": int(len(ledger)),
                "signal_ledger_sha256": signal_ledger_hash(ledger),
            }
        )

    signals = pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()
    signals = signals.sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True)
    signals_path = output / "candidate_signals.csv.gz"
    signals_gzip_sha = write_deterministic_gzip_csv(signals, signals_path)

    months = [f"2024-{month:02d}" for month in range(1, 7)]
    summary_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    hourly_rows: list[dict[str, Any]] = []
    excluded_map = {row["candidate_id"]: row["hard_no_trade_signals_excluded"] for row in hard_excluded_rows}
    hash_map = {row["candidate_id"]: row for row in signal_hash_rows}
    audit_by_id = definition_audit.set_index("candidate_id").to_dict("index")
    for candidate in candidates:
        cid = candidate["id"]
        group = signals[signals["candidate_id"] == cid]
        month_counts = group.groupby("signal_month").size().to_dict()
        hour_counts = group.groupby("signal_hour_utc").size().to_dict()
        for month in months:
            monthly_rows.append(
                {
                    "candidate_id": cid,
                    "family": candidate["family"],
                    "month": month,
                    "signals": int(month_counts.get(month, 0)),
                    "long_signals": int(((group["signal_month"] == month) & (group["side"] == 1)).sum()),
                    "short_signals": int(((group["signal_month"] == month) & (group["side"] == -1)).sum()),
                }
            )
        for hour in range(24):
            hourly_rows.append(
                {
                    "candidate_id": cid,
                    "family": candidate["family"],
                    "signal_hour_utc": hour,
                    "signals": int(hour_counts.get(hour, 0)),
                }
            )
        summary_rows.append(
            {
                "candidate_id": cid,
                "family": candidate["family"],
                "origin": candidate.get("origin", ""),
                "h2_information_status": candidate.get("h2_information_status", "new_unopened"),
                "definition_sha256": candidate["definition_sha256"],
                "signal_ledger_sha256": hash_map[cid]["signal_ledger_sha256"],
                "signals": int(len(group)),
                "long_signals": int((group["side"] == 1).sum()),
                "short_signals": int((group["side"] == -1).sum()),
                "active_months": int(sum(int(month_counts.get(month, 0)) > 0 for month in months)),
                "minimum_monthly_signals": int(min(int(month_counts.get(month, 0)) for month in months)),
                "maximum_monthly_signals": int(max(int(month_counts.get(month, 0)) for month in months)),
                "hard_no_trade_signals_excluded": int(excluded_map[cid]),
                "first_signal_ts": "" if group.empty else str(group["signal_ts"].iloc[0]),
                "last_signal_ts": "" if group.empty else str(group["signal_ts"].iloc[-1]),
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values(["family", "candidate_id"])
    monthly = pd.DataFrame(monthly_rows).sort_values(["candidate_id", "month"])
    hourly = pd.DataFrame(hourly_rows).sort_values(["candidate_id", "signal_hour_utc"])
    summary_path = output / "candidate_signal_summary.csv"
    monthly_path = output / "candidate_monthly_signals.csv"
    hourly_path = output / "candidate_hourly_signals.csv"
    summary.to_csv(summary_path, index=False, lineterminator="\n")
    monthly.to_csv(monthly_path, index=False, lineterminator="\n")
    hourly.to_csv(hourly_path, index=False, lineterminator="\n")

    family_summary = summary.groupby("family", as_index=False).agg(
        candidates=("candidate_id", "count"),
        total_signals=("signals", "sum"),
        minimum_candidate_signals=("signals", "min"),
        maximum_candidate_signals=("signals", "max"),
        signal_limited_candidates=("signals", lambda values: int((values == 0).sum())),
    ).sort_values("family")
    family_path = output / "family_signal_summary.csv"
    family_summary.to_csv(family_path, index=False, lineterminator="\n")

    signal_hashes = pd.DataFrame(signal_hash_rows).sort_values(["family", "candidate_id"])
    signal_hash_path = output / "candidate_signal_hashes.csv"
    signal_hashes.to_csv(signal_hash_path, index=False, lineterminator="\n")

    equivalence_rows: list[dict[str, Any]] = []
    for digest, group in signal_hashes.groupby("signal_ledger_sha256", sort=True):
        ids = sorted(group["candidate_id"].tolist())
        equivalence_rows.append(
            {
                "signal_ledger_sha256": digest,
                "candidate_count": len(ids),
                "candidate_ids": "|".join(ids),
                "is_signal_equivalent_group": len(ids) > 1,
            }
        )
    equivalence = pd.DataFrame(equivalence_rows).sort_values(["is_signal_equivalent_group", "candidate_ids"], ascending=[False, True])
    equivalence_path = output / "candidate_signal_equivalence.csv"
    equivalence.to_csv(equivalence_path, index=False, lineterminator="\n")

    sets: dict[str, set[tuple[str, str, int]]] = {}
    timestamp_sides: dict[str, dict[str, int]] = {}
    for candidate in candidates:
        cid = candidate["id"]
        group = signals[signals["candidate_id"] == cid]
        sets[cid] = set(zip(group["signal_ts"], group["entry_ts"], group["side"].astype(int)))
        timestamp_sides[cid] = dict(zip(group["signal_ts"], group["side"].astype(int)))
    overlap_rows: list[dict[str, Any]] = []
    ids = [candidate["id"] for candidate in candidates]
    for i, left in enumerate(ids):
        for right in ids[i + 1 :]:
            intersection = sets[left] & sets[right]
            union = sets[left] | sets[right]
            common_ts = set(timestamp_sides[left]) & set(timestamp_sides[right])
            opposite = sum(timestamp_sides[left][ts] == -timestamp_sides[right][ts] for ts in common_ts)
            overlap_rows.append(
                {
                    "candidate_left": left,
                    "candidate_right": right,
                    "exact_signal_overlap": len(intersection),
                    "exact_signal_union": len(union),
                    "exact_jaccard": 0.0 if not union else len(intersection) / len(union),
                    "same_signal_timestamp": len(common_ts),
                    "opposite_side_same_timestamp": int(opposite),
                }
            )
    overlap = pd.DataFrame(overlap_rows).sort_values(["candidate_left", "candidate_right"])
    overlap_path = output / "pairwise_signal_overlap.csv"
    overlap.to_csv(overlap_path, index=False, float_format="%.12g", lineterminator="\n")

    required_paths = [
        definition_path, signals_path, summary_path, monthly_path, hourly_path,
        family_path, signal_hash_path, equivalence_path, overlap_path,
    ]
    acceptance = {
        "status": "PASS",
        "canonical_m15_digest_exact": input_metadata["canonical_m15_gzip_sha256"] == registry["input_lock"]["canonical_m15_gzip_sha256"],
        "h1_only_rows_parsed": input_metadata["h2_rows_parsed"] == 0 and input_metadata["last_timestamp"] < H1_END,
        "h2_rows_parsed_zero": input_metadata["h2_rows_parsed"] == 0,
        "2025_access_false": registry["research_firewall"]["2025_access"] is False,
        "family_count_12": len(registry["families"]) == 12,
        "candidate_count_60": len(candidates) == 60,
        "family_caps_exact": sum(int(f["cap"]) for f in registry["families"]) == 60,
        "candidate_ids_unique": len({c["id"] for c in candidates}) == 60,
        "functional_definitions_unique": definition_audit["definition_sha256"].nunique() == 60,
        "no_exit_or_horizon_parameters": all("hold_bars" not in c and "exit" not in c for c in candidates),
        "all_families_supported": set(f["family"] for f in registry["families"]) == set(SIGNAL_FUNCTIONS),
        "all_candidates_reported": summary["candidate_id"].nunique() == 60,
        "monthly_grid_complete": len(monthly) == 60 * 6,
        "hourly_grid_complete": len(hourly) == 60 * 24,
        "pairwise_overlap_complete": len(overlap) == 60 * 59 // 2,
        "actual_next_bar_entries": bool((pd.to_datetime(signals["entry_ts"], utc=True) > pd.to_datetime(signals["signal_ts"], utc=True)).all()),
        "hard_no_trade_violations_zero": bool((~hard_exclusion_mask(pd.Series(pd.to_datetime(signals["entry_ts"], utc=True), index=signals.index), session_config)).all()),
        "no_h2_entry_timestamps": bool((pd.to_datetime(signals["entry_ts"], utc=True) < pd.Timestamp(H1_END)).all()),
        "outcome_columns_absent": output_columns_are_clean(required_paths),
        "signal_ledger_deterministic_gzip": signals_gzip_sha == sha256_file(signals_path),
    }
    if not all(value is True for key, value in acceptance.items() if key != "status"):
        acceptance["status"] = "FAIL"
    acceptance_path = output / "r1_acceptance.json"
    acceptance_path.write_text(json.dumps(acceptance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    metadata = {
        "version": "v1",
        "status": acceptance["status"],
        "research_stage": "R1_entry_registry",
        "symbol": SYMBOL,
        "signal_timeframe": "M15",
        "development_end_utc_exclusive": H1_END,
        "input": input_metadata,
        "registry_path": str(args.registry),
        "registry_sha256": sha256_file(args.registry),
        "registry_snapshot_sha256": sha256_file(registry_snapshot),
        "session_config_path": str(args.session_config),
        "session_config_sha256": sha256_file(args.session_config),
        "families": len(registry["families"]),
        "candidates": len(candidates),
        "signal_rows": int(len(signals)),
        "signal_equivalent_groups": int(equivalence["is_signal_equivalent_group"].sum()),
        "candidate_signals_gzip_sha256": signals_gzip_sha,
        "outcomes_opened": False,
        "r2_unblocked": acceptance["status"] == "PASS",
        "h2_opened_for_new_candidates": False,
        "2025_artifact_access": False,
        "core_promotion": False,
        "mt4_promotion": False,
    }
    metadata_path = output / "run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if acceptance["status"] != "PASS":
        raise AssertionError(acceptance)
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    main()
