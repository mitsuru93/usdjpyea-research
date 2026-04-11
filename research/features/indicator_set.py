"""Compact, explicit indicator set for pre-MT4 research features.

All calculations are decision-time safe (bar-close basis) and avoid forward leakage.
"""

from __future__ import annotations

import pandas as pd

PIP_SIZE = 0.01  # USDJPY pip size


def add_indicator_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add compact indicator columns using pandas only."""
    result = df.copy()

    close = result["close"]
    high = result["high"]
    low = result["low"]

    # EMA / envelope-distance features.
    result["ema20"] = close.ewm(span=20, adjust=False).mean()
    result["dist_from_ema_pips"] = (close - result["ema20"]) / PIP_SIZE

    # Momentum over different horizons (signed pips).
    result["pre10_change_pips"] = (close - close.shift(10)) / PIP_SIZE
    result["pre30_change_pips"] = (close - close.shift(30)) / PIP_SIZE
    result["pre60_change_pips"] = (close - close.shift(60)) / PIP_SIZE

    # Net movement over the previous 10 fully closed bars (excluding current bar move).
    one_bar_diff = close.diff()
    result["net10_change_pips"] = one_bar_diff.shift(1).rolling(10).sum() / PIP_SIZE

    # RSI14 (Wilder smoothing via alpha=1/period).
    delta = close.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = losses.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    result["rsi14"] = rsi.fillna(100.0).where(avg_loss != 0.0, 100.0)

    # ATR with true range.
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr5_pips"] = true_range.rolling(5, min_periods=5).mean() / PIP_SIZE
    result["atr14_pips"] = true_range.rolling(14, min_periods=14).mean() / PIP_SIZE
    result["atr_ratio_5_14"] = result["atr5_pips"] / result["atr14_pips"].replace(0.0, pd.NA)

    # MACD (12, 26, 9).
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    result["macd_line"] = ema12 - ema26
    result["macd_signal"] = result["macd_line"].ewm(span=9, adjust=False).mean()
    result["macd_hist"] = result["macd_line"] - result["macd_signal"]

    # Bollinger width (20, 2 std).
    bb_mid = close.rolling(20, min_periods=20).mean()
    bb_std = close.rolling(20, min_periods=20).std(ddof=0)
    bb_upper = bb_mid + (2.0 * bb_std)
    bb_lower = bb_mid - (2.0 * bb_std)
    result["bb_width"] = bb_upper - bb_lower
    result["bb_width_ratio_to_close"] = result["bb_width"] / close.replace(0.0, pd.NA)

    return result
