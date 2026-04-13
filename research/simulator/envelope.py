"""Envelope computation and touch detection for simulator v1."""

from __future__ import annotations

import math
import pandas as pd

EMA_SPAN = 20
DEVIATION_RATE = 0.00070  # 0.070%
DEFAULT_BAND_MODEL = "percent"
DEFAULT_ATR_PERIOD = 14
DEFAULT_STD_PERIOD = 20
DEFAULT_RANGE_PERIOD = 20
DEFAULT_VOL_PERIOD = 20
DEFAULT_PIP_SIZE = 0.01

SUPPORTED_BAND_MODELS = {
    "percent",
    "fixed_pips",
    "atr",
    "stddev",
    "range_mean",
    "range_median",
    "range_percentile",
    "realized_vol_cc",
    "parkinson",
    "garman_klass",
    "rogers_satchell",
    "max_percent_fixed_floor",
    "min_atr_fixed_cap",
    "max_atr_fixed_floor",
}


def _rolling_true_range(df: pd.DataFrame, *, close_col: str, high_col: str, low_col: str) -> pd.Series:
    prev_close = df[close_col].shift(1)
    tr = pd.concat(
        [
            (df[high_col] - df[low_col]).abs(),
            (df[high_col] - prev_close).abs(),
            (df[low_col] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def _rolling_band(series: pd.Series, window: int, agg: str = "mean") -> pd.Series:
    win = max(int(window), 1)
    if agg == "mean":
        return series.rolling(window=win, min_periods=1).mean()
    if agg == "median":
        return series.rolling(window=win, min_periods=1).median()
    raise ValueError(f"Unsupported rolling agg='{agg}'")


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
    band_std_k: float = 1.0,
    band_std_period: int = DEFAULT_STD_PERIOD,
    band_std_source: str = "close",
    band_range_period: int = DEFAULT_RANGE_PERIOD,
    band_range_k: float = 1.0,
    band_range_percentile: float = 0.75,
    band_vol_period: int = DEFAULT_VOL_PERIOD,
    band_vol_k: float = 1.0,
    band_fixed_floor_pips: float = 8.0,
    band_fixed_cap_pips: float = 15.0,
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
    fixed_dev = float(band_pips) * float(pip_size)
    floor_dev = float(band_fixed_floor_pips) * float(pip_size)
    cap_dev = float(band_fixed_cap_pips) * float(pip_size)

    def _compute_atr_dev() -> pd.Series:
        atr = _rolling_band(
            _rolling_true_range(result, close_col=close_col, high_col=high_col, low_col=low_col),
            int(band_atr_period),
            "mean",
        )
        return atr * float(band_atr_k)

    def _returns_std_dev() -> pd.Series:
        src = str(band_std_source).strip().lower()
        if src == "returns":
            returns = result[close_col].pct_change().fillna(0.0)
            std_ret = returns.rolling(window=max(int(band_std_period), 1), min_periods=1).std().fillna(0.0)
            return result["ema20"] * std_ret * float(band_std_k)
        if src == "close":
            close_std = result[close_col].rolling(window=max(int(band_std_period), 1), min_periods=1).std().fillna(0.0)
            return close_std * float(band_std_k)
        else:
            raise ValueError("band_std_source must be 'close' or 'returns'")

    def _range_series() -> pd.Series:
        return (result[high_col] - result[low_col]).abs()

    def _realized_vol_price_dev(model: str) -> pd.Series:
        period = max(int(band_vol_period), 1)
        eps = 1e-12
        log_hl = (result[high_col].clip(lower=eps) / result[low_col].clip(lower=eps)).apply(math.log)
        log_hc = (result[high_col].clip(lower=eps) / result[close_col].shift(1).clip(lower=eps)).apply(math.log)
        log_lc = (result[low_col].clip(lower=eps) / result[close_col].shift(1).clip(lower=eps)).apply(math.log)
        log_co = (result[close_col].clip(lower=eps) / result[close_col].shift(1).clip(lower=eps)).apply(math.log)
        log_ho = (result[high_col].clip(lower=eps) / result[close_col].shift(1).clip(lower=eps)).apply(math.log)
        log_lo = (result[low_col].clip(lower=eps) / result[close_col].shift(1).clip(lower=eps)).apply(math.log)
        if model == "realized_vol_cc":
            var = (log_co**2).rolling(window=period, min_periods=1).mean()
        elif model == "parkinson":
            var = ((log_hl**2) / (4.0 * math.log(2.0))).rolling(window=period, min_periods=1).mean()
        elif model == "garman_klass":
            gk_term = 0.5 * (log_hl**2) - ((2.0 * math.log(2.0) - 1.0) * (log_co**2))
            var = gk_term.rolling(window=period, min_periods=1).mean()
        elif model == "rogers_satchell":
            rs_term = (log_ho * (log_ho - log_co)) + (log_lo * (log_lo - log_co))
            var = rs_term.rolling(window=period, min_periods=1).mean()
        else:
            raise ValueError(f"Unsupported realized-vol model='{model}'")
        sigma = var.clip(lower=0.0).pow(0.5).fillna(0.0)
        return result["ema20"] * sigma * float(band_vol_k)

    if normalized_model == "percent":
        deviation = result["ema20"] * float(band_percent)
    elif normalized_model == "fixed_pips":
        deviation = fixed_dev
    elif normalized_model == "atr":
        deviation = _compute_atr_dev()
    elif normalized_model == "stddev":
        deviation = _returns_std_dev()
    elif normalized_model == "range_mean":
        deviation = _rolling_band(_range_series(), int(band_range_period), "mean") * float(band_range_k)
    elif normalized_model == "range_median":
        deviation = _rolling_band(_range_series(), int(band_range_period), "median") * float(band_range_k)
    elif normalized_model == "range_percentile":
        quantile = min(max(float(band_range_percentile), 0.0), 1.0)
        deviation = (
            _range_series()
            .rolling(window=max(int(band_range_period), 1), min_periods=1)
            .quantile(quantile)
            .fillna(0.0)
            * float(band_range_k)
        )
    elif normalized_model in {"realized_vol_cc", "parkinson", "garman_klass", "rogers_satchell"}:
        deviation = _realized_vol_price_dev(normalized_model)
    elif normalized_model == "max_percent_fixed_floor":
        deviation = (result["ema20"] * float(band_percent)).clip(lower=floor_dev)
    elif normalized_model == "min_atr_fixed_cap":
        deviation = _compute_atr_dev().clip(upper=cap_dev)
    elif normalized_model == "max_atr_fixed_floor":
        deviation = _compute_atr_dev().clip(lower=floor_dev)
    else:
        raise ValueError(f"Unsupported band_model='{band_model}'. Allowed: {sorted(SUPPORTED_BAND_MODELS)}")

    result["upper_env"] = result["ema20"] + deviation
    result["lower_env"] = result["ema20"] - deviation
    result["touch_upper"] = result[high_col] >= result["upper_env"]
    result["touch_lower"] = result[low_col] <= result["lower_env"]
    return result
