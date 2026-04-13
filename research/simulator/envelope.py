"""Envelope computation and touch detection for simulator v1."""

from __future__ import annotations

import pandas as pd

EMA_SPAN = 20
DEVIATION_RATE = 0.00070  # 0.070%
DEFAULT_BAND_MODEL = "percent"
DEFAULT_ATR_PERIOD = 14
DEFAULT_PIP_SIZE = 0.01


def add_envelope_columns(
    df: pd.DataFrame,
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
    *,
    ema_span: int = EMA_SPAN,
    band_model: str = DEFAULT_BAND_MODEL,
    band_percent: float = DEVIATION_RATE,
    band_pips: float = 10.0,
    band_atr_k: float = 1.0,
    band_atr_period: int = DEFAULT_ATR_PERIOD,
    pip_size: float = DEFAULT_PIP_SIZE,
) -> pd.DataFrame:
    """Add EMA20 envelope columns and touch flags.

    Touch detection is simple and bar-based:
    - touch_upper: bar high >= upper_envelope
    - touch_lower: bar low <= lower_envelope
    """
    result = df.copy()
    result["ema20"] = result[close_col].ewm(span=max(int(ema_span), 1), adjust=False).mean()
    normalized_model = str(band_model).strip().lower()
    if normalized_model == "percent":
        deviation = result["ema20"] * float(band_percent)
    elif normalized_model == "fixed_pips":
        deviation = float(band_pips) * float(pip_size)
    elif normalized_model == "atr":
        prev_close = result[close_col].shift(1)
        tr = pd.concat(
            [
                (result[high_col] - result[low_col]).abs(),
                (result[high_col] - prev_close).abs(),
                (result[low_col] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(window=max(int(band_atr_period), 1), min_periods=1).mean()
        deviation = atr * float(band_atr_k)
    else:
        raise ValueError(f"Unsupported band_model='{band_model}'. Allowed: ['percent', 'fixed_pips', 'atr']")

    result["upper_env"] = result["ema20"] + deviation
    result["lower_env"] = result["ema20"] - deviation
    result["touch_upper"] = result[high_col] >= result["upper_env"]
    result["touch_lower"] = result[low_col] <= result["lower_env"]
    return result
