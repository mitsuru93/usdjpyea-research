"""CSV loader for simple OHLC research datasets.

Design goals:
- Practical support for common OHLC CSV layouts.
- Clear failure when required schema cannot be inferred safely.
- Conservative behavior: no guessing beyond explicit aliases.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_FIELDS = ("datetime", "open", "high", "low", "close")
COLUMN_ALIASES = {
    "datetime": ["datetime", "timestamp", "time", "date", "datestamp", "dt"],
    "open": ["open", "o"],
    "high": ["high", "h"],
    "low": ["low", "l"],
    "close": ["close", "c"],
}


def _normalize_column_name(name: str) -> str:
    return name.strip().lower().replace(" ", "").replace("_", "")


def _infer_column_mapping(columns: list[str]) -> dict[str, str]:
    normalized_to_original = {_normalize_column_name(col): col for col in columns}
    mapping: dict[str, str] = {}

    for required_field, aliases in COLUMN_ALIASES.items():
        matches = [
            normalized_to_original[alias]
            for alias in aliases
            if alias in normalized_to_original
        ]
        if len(matches) == 1:
            mapping[required_field] = matches[0]
        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous mapping for '{required_field}'. "
                f"Matched columns: {matches}. Please provide an unambiguous schema."
            )

    missing = [field for field in REQUIRED_FIELDS if field not in mapping]
    if missing:
        raise ValueError(
            "Could not infer required OHLC columns. "
            f"Missing: {missing}. Available columns: {columns}. "
            "Supported aliases: "
            f"{COLUMN_ALIASES}."
        )

    return mapping


def load_ohlc_csv(path: str | Path) -> pd.DataFrame:
    """Load OHLC CSV into a normalized DataFrame.

    Returns DataFrame with standardized columns:
    - datetime (source timeline timestamp parsed from input)
    - open, high, low, close (float)
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    raw_df = pd.read_csv(csv_path)
    if raw_df.empty:
        raise ValueError(f"Input CSV is empty: {csv_path}")

    mapping = _infer_column_mapping(list(raw_df.columns))
    df = raw_df.rename(columns={v: k for k, v in mapping.items()})[list(REQUIRED_FIELDS)].copy()

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    if df["datetime"].isna().any():
        bad_rows = int(df["datetime"].isna().sum())
        raise ValueError(f"Failed to parse datetime in {bad_rows} rows.")

    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any():
            bad_rows = int(df[col].isna().sum())
            raise ValueError(f"Failed to parse numeric values in column '{col}' for {bad_rows} rows.")

    if df.duplicated(subset=["datetime"]).any():
        raise ValueError("Detected duplicate datetime rows. Please de-duplicate input data first.")

    df = df.sort_values("datetime").reset_index(drop=True)
    return df
