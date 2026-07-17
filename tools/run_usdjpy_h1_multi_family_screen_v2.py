#!/usr/bin/env python3
"""Corrected H1 multi-family screen entry-timing and spread semantics.

This wrapper reuses the fixed candidate registry and reporting logic from
run_usdjpy_h1_multi_family_screen.py, while correcting two implementation
mismatches found in run 29546116205:

1. `entry_hours_utc` applies to the next-bar entry timestamp, not the signal
   bar timestamp.
2. Transaction cost uses the entry bar's `spread_mean_pips`, matching the
   canonical session-baseline implementation.

Session-range candidates keep their explicitly defined signal-close windows.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import run_usdjpy_h1_multi_family_screen as base


def load_bars(month: str, root: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    paths = sorted(root.rglob("M15/USDJPY_M15.csv.gz"))
    if not paths:
        raise FileNotFoundError(f"no M15/USDJPY_M15.csv.gz under {root}")

    frames: list[pd.DataFrame] = []
    for path in paths:
        frame = pd.read_csv(path)
        required = {
            "timestamp_utc",
            "mid_open",
            "mid_high",
            "mid_low",
            "mid_close",
            "spread_mean_pips",
        }
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{path} missing columns: {sorted(missing)}")
        frame = frame[list(required)].copy()
        frame["_path"] = str(path)
        frame["_priority"] = (
            1 if "baseline_aggregate_repair" in str(path) else 0
        )
        frames.append(frame)

    bars = pd.concat(frames, ignore_index=True)
    bars["timestamp_utc"] = pd.to_datetime(
        bars["timestamp_utc"], utc=True, errors="coerce"
    )
    numeric = [
        "mid_open",
        "mid_high",
        "mid_low",
        "mid_close",
        "spread_mean_pips",
    ]
    for col in numeric:
        bars[col] = pd.to_numeric(bars[col], errors="coerce")
    bars = bars.dropna(
        subset=[
            "timestamp_utc",
            "mid_open",
            "mid_high",
            "mid_low",
            "mid_close",
            "spread_mean_pips",
        ]
    )

    before = len(bars)
    bars = bars.sort_values(["timestamp_utc", "_priority", "_path"])
    bars = bars.drop_duplicates("timestamp_utc", keep="last")
    bars = bars.sort_values("timestamp_utc").reset_index(drop=True)
    bars["month"] = month
    bars["date_utc"] = bars["timestamp_utc"].dt.strftime("%Y-%m-%d")
    bars["hour_utc"] = bars["timestamp_utc"].dt.hour.astype(int)
    bars["bar_range_pips"] = (
        bars["mid_high"] - bars["mid_low"]
    ) / base.PIP

    coverage = {
        "month": month,
        "files": len(paths),
        "rows_before_dedup": int(before),
        "rows_after_dedup": int(len(bars)),
        "duplicate_rows_removed": int(before - len(bars)),
        "start": bars["timestamp_utc"].min().isoformat(),
        "end": bars["timestamp_utc"].max().isoformat(),
    }
    return bars, coverage


def entry_hour_allowed(
    bars: pd.DataFrame, candidate: dict
) -> pd.Series:
    entry_ts = bars["timestamp_utc"].shift(-1)
    return entry_ts.dt.hour.isin(candidate["entry_hours_utc"])


def finalize_signals(
    bars: pd.DataFrame,
    side: pd.Series,
    candidate: dict,
    family: str,
    session_config: dict,
) -> pd.DataFrame:
    hold = int(candidate["hold_bars"])
    work = bars.copy()
    work["side"] = side.fillna(0).astype(int)
    work["entry_ts"] = work["timestamp_utc"].shift(-1)
    work["entry_mid"] = work["mid_open"].shift(-1)
    work["entry_spread_pips"] = work["spread_mean_pips"].shift(-1)
    work["exit_ts"] = work["timestamp_utc"].shift(-hold)
    work["exit_mid"] = work["mid_close"].shift(-hold)

    trades = work[
        work["side"].isin([1, -1])
        & work["entry_ts"].notna()
        & work["exit_ts"].notna()
        & work["entry_mid"].notna()
        & work["exit_mid"].notna()
        & work["entry_spread_pips"].notna()
    ].copy()
    if trades.empty:
        return trades

    excluded = base.hard_exclusion_mask(
        trades["entry_ts"], session_config, base.SYMBOL
    )
    trades = trades[~excluded].copy()
    trades["candidate_id"] = candidate["id"]
    trades["family"] = family
    trades["hold_bars"] = hold
    trades["entry_date_utc"] = trades["entry_ts"].dt.strftime("%Y-%m-%d")
    trades["entry_month"] = trades["entry_ts"].dt.strftime("%Y-%m")
    trades["gross_pips"] = (
        trades["side"]
        * (trades["exit_mid"] - trades["entry_mid"])
        / base.PIP
    )
    base_spread = float(candidate.get("base_spread_pips", 0.5))
    spread = trades["entry_spread_pips"].clip(lower=base_spread)
    trades["default_cost_pips"] = spread
    trades["severe_cost_pips"] = spread * 3.0 + 1.0
    trades["default_net_pips"] = (
        trades["gross_pips"] - trades["default_cost_pips"]
    )
    trades["severe_net_pips"] = (
        trades["gross_pips"] - trades["severe_cost_pips"]
    )
    return trades


def impulse_breakout(
    bars: pd.DataFrame, candidate: dict
) -> pd.Series:
    lookback = int(candidate["lookback_bars"])
    prev_high = (
        bars["mid_high"]
        .shift(1)
        .rolling(lookback, min_periods=lookback)
        .max()
    )
    prev_low = (
        bars["mid_low"]
        .shift(1)
        .rolling(lookback, min_periods=lookback)
        .min()
    )
    expanded = bars["bar_range_pips"] > bars["bar_range_pips"].shift(1)
    allowed = entry_hour_allowed(bars, candidate)
    side = pd.Series(0, index=bars.index, dtype=int)
    side.loc[
        allowed & expanded & (bars["mid_close"] > prev_high)
    ] = 1
    side.loc[
        allowed & expanded & (bars["mid_close"] < prev_low)
    ] = -1
    return side


def failed_excursion(
    bars: pd.DataFrame, candidate: dict
) -> pd.Series:
    if candidate["reference"] == "rolling_completed_bars":
        lookback = int(candidate["lookback_bars"])
        ref_high = (
            bars["mid_high"]
            .shift(1)
            .rolling(lookback, min_periods=lookback)
            .max()
        )
        ref_low = (
            bars["mid_low"]
            .shift(1)
            .rolling(lookback, min_periods=lookback)
            .min()
        )
        allowed = entry_hour_allowed(bars, candidate)
    else:
        ref = base.session_reference(
            bars,
            int(candidate["reference_start_hour"]),
            int(candidate["reference_end_hour_exclusive"]),
        )
        ref_high = ref["ref_high"]
        ref_low = ref["ref_low"]
        # These fields define the signal-close window, not entry hours.
        allowed = (
            bars["hour_utc"] >= int(candidate["entry_start_hour"])
        ) & (
            bars["hour_utc"] <= int(candidate["entry_end_hour_inclusive"])
        )

    failed_high = (
        (bars["mid_high"] > ref_high)
        & (bars["mid_close"] <= ref_high)
        & (bars["mid_close"] >= ref_low)
    )
    failed_low = (
        (bars["mid_low"] < ref_low)
        & (bars["mid_close"] >= ref_low)
        & (bars["mid_close"] <= ref_high)
    )
    side = pd.Series(0, index=bars.index, dtype=int)
    side.loc[allowed & failed_high & ~failed_low] = -1
    side.loc[allowed & failed_low & ~failed_high] = 1
    return side


def compression_expansion(
    bars: pd.DataFrame, candidate: dict
) -> pd.Series:
    compression_bars = int(candidate["compression_bars"])
    comparison_bars = int(candidate["comparison_bars"])
    comp_high = (
        bars["mid_high"]
        .shift(1)
        .rolling(compression_bars, min_periods=compression_bars)
        .max()
    )
    comp_low = (
        bars["mid_low"]
        .shift(1)
        .rolling(compression_bars, min_periods=compression_bars)
        .min()
    )
    comp_range = comp_high - comp_low
    earlier_high = (
        bars["mid_high"]
        .shift(compression_bars + 1)
        .rolling(comparison_bars, min_periods=comparison_bars)
        .max()
    )
    earlier_low = (
        bars["mid_low"]
        .shift(compression_bars + 1)
        .rolling(comparison_bars, min_periods=comparison_bars)
        .min()
    )
    compressed = comp_range < (earlier_high - earlier_low)
    expanded = bars["bar_range_pips"] > bars["bar_range_pips"].shift(1)
    allowed = entry_hour_allowed(bars, candidate)
    side = pd.Series(0, index=bars.index, dtype=int)
    side.loc[
        allowed
        & compressed
        & expanded
        & (bars["mid_close"] > comp_high)
    ] = 1
    side.loc[
        allowed
        & compressed
        & expanded
        & (bars["mid_close"] < comp_low)
    ] = -1
    return side


def trend_continuation(
    bars: pd.DataFrame, candidate: dict
) -> pd.Series:
    trend_bars = int(candidate["trend_bars"])
    trend_return = (
        bars["mid_close"].shift(1)
        - bars["mid_open"].shift(trend_bars)
    )
    prev_bearish = (
        bars["mid_close"].shift(1) < bars["mid_open"].shift(1)
    )
    prev_bullish = (
        bars["mid_close"].shift(1) > bars["mid_open"].shift(1)
    )
    allowed = entry_hour_allowed(bars, candidate)
    side = pd.Series(0, index=bars.index, dtype=int)
    side.loc[
        allowed
        & (trend_return > 0)
        & prev_bearish
        & (bars["mid_close"] > bars["mid_high"].shift(1))
    ] = 1
    side.loc[
        allowed
        & (trend_return < 0)
        & prev_bullish
        & (bars["mid_close"] < bars["mid_low"].shift(1))
    ] = -1
    return side


def main() -> int:
    base.load_bars = load_bars
    base.finalize_signals = finalize_signals
    base.impulse_breakout = impulse_breakout
    base.failed_excursion = failed_excursion
    base.compression_expansion = compression_expansion
    base.trend_continuation = trend_continuation
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
