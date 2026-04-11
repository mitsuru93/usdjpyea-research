"""Session tagging for USDJPY research (JST reporting based)."""

from __future__ import annotations

import pandas as pd

JST_OFFSET_HOURS = 9
INPUT_TIMEZONE_MODES = {"UTC", "JST"}
SESSION_BOUNDS = {
    "ASIA": (3, 9),
    "TOKYO": (9, 16),
    "LONDON": (16, 21),
}


def classify_jst_session(hour: int) -> str:
    """Classify JST hour into one of ASIA/TOKYO/LONDON/NY.

    NY crosses midnight and therefore includes 21:00-23:59 and 00:00-02:59 JST.
    """
    if SESSION_BOUNDS["ASIA"][0] <= hour < SESSION_BOUNDS["ASIA"][1]:
        return "ASIA"
    if SESSION_BOUNDS["TOKYO"][0] <= hour < SESSION_BOUNDS["TOKYO"][1]:
        return "TOKYO"
    if SESSION_BOUNDS["LONDON"][0] <= hour < SESSION_BOUNDS["LONDON"][1]:
        return "LONDON"
    return "NY"


def add_session_columns(
    df: pd.DataFrame,
    datetime_col: str = "datetime",
    input_timezone_mode: str = "UTC",
) -> pd.DataFrame:
    """Add session columns derived from explicit input timeline mode.

    Raw datetime remains unchanged as source timeline.

    input_timezone_mode:
    - UTC: derive JST as raw + 9h
    - JST: treat raw as already JST
    """
    mode = input_timezone_mode.upper()
    if mode not in INPUT_TIMEZONE_MODES:
        raise ValueError(
            f"Unsupported input_timezone_mode='{input_timezone_mode}'. "
            f"Allowed: {sorted(INPUT_TIMEZONE_MODES)}"
        )

    result = df.copy()
    if mode == "UTC":
        jst_dt = result[datetime_col] + pd.to_timedelta(JST_OFFSET_HOURS, unit="h")
    else:
        jst_dt = result[datetime_col]

    result["jst_datetime"] = jst_dt
    result["session"] = jst_dt.dt.hour.map(classify_jst_session)
    result["month"] = jst_dt.dt.to_period("M").astype(str)
    result["input_timezone_mode"] = mode
    return result
