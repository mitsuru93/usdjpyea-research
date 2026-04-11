"""Session tagging for USDJPY research (JST based)."""

from __future__ import annotations

import pandas as pd

JST_OFFSET_HOURS = 9
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


def add_session_columns(df: pd.DataFrame, datetime_col: str = "datetime") -> pd.DataFrame:
    """Add JST time/session columns.

    Assumes input datetime is UTC timestamp.
    """
    result = df.copy()
    jst_dt = result[datetime_col] + pd.to_timedelta(JST_OFFSET_HOURS, unit="h")
    result["jst_datetime"] = jst_dt
    result["session"] = jst_dt.dt.hour.map(classify_jst_session)
    result["month"] = jst_dt.dt.to_period("M").astype(str)
    return result
