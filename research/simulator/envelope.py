"""Envelope computation and touch detection for simulator v1."""

from __future__ import annotations

import pandas as pd

EMA_SPAN = 20
DEVIATION_RATE = 0.00070  # 0.070%


def add_envelope_columns(
    df: pd.DataFrame,
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Add EMA20 envelope columns and touch flags.

    Touch detection is simple and bar-based:
    - touch_upper: bar high >= upper_envelope
    - touch_lower: bar low <= lower_envelope
    """
    result = df.copy()
    result["ema20"] = result[close_col].ewm(span=EMA_SPAN, adjust=False).mean()
    result["upper_env"] = result["ema20"] * (1.0 + DEVIATION_RATE)
    result["lower_env"] = result["ema20"] * (1.0 - DEVIATION_RATE)
    result["touch_upper"] = result[high_col] >= result["upper_env"]
    result["touch_lower"] = result[low_col] <= result["lower_env"]
    return result
