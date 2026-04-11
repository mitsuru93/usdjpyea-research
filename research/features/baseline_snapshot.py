"""Decision-time baseline snapshot extraction for candidate rows."""

from __future__ import annotations

import pandas as pd

FEATURE_SET_VERSION = "feature_set_v1"

SNAPSHOT_COLUMNS = [
    "datetime",
    "close",
    "ema20",
    "dist_from_ema_pips",
    "upper_env",
    "lower_env",
    "touch_upper",
    "touch_lower",
    "pre10_change_pips",
    "pre30_change_pips",
    "pre60_change_pips",
    "net10_change_pips",
    "rsi14",
    "atr5_pips",
    "atr14_pips",
    "atr_ratio_5_14",
    "macd_line",
    "macd_signal",
    "macd_hist",
    "bb_width",
    "bb_width_ratio_to_close",
    "month",
    "session",
    "input_timezone_mode",
]

RENAME_MAP = {
    "datetime": "timestamp",
    "upper_env": "envelope_upper",
    "lower_env": "envelope_lower",
}


def build_baseline_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Return timestamp-keyed decision-time feature snapshot table."""
    missing = [col for col in SNAPSHOT_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Cannot build baseline snapshot. Missing columns: {missing}")

    snapshot = df[SNAPSHOT_COLUMNS].copy().rename(columns=RENAME_MAP)
    snapshot = snapshot.drop_duplicates(subset=["timestamp"], keep="last")
    return snapshot
