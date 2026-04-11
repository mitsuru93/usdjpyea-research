"""Shared helpers for post-run bucket/joint research reports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_FEATURES = [
    "dist_from_ema_pips",
    "pre10_change_pips",
    "pre30_change_pips",
    "pre60_change_pips",
    "net10_change_pips",
    "rsi14",
    "atr5_pips",
    "atr14_pips",
    "atr_ratio_5_14",
    "macd_line",
    "macd_hist",
    "bb_width_ratio_to_close",
]

DEFAULT_FEATURE_PAIRS = [
    ("pre60_change_pips", "net10_change_pips"),
    ("dist_from_ema_pips", "atr_ratio_5_14"),
    ("pre60_change_pips", "rsi14"),
    ("net10_change_pips", "rsi14"),
    ("dist_from_ema_pips", "macd_hist"),
]

DEFAULT_SLICE_MODES = ["overall", "by_family", "by_direction", "by_session"]
DEFAULT_QUANTILE_BUCKET_COUNT = 5
MIN_UNSTABLE_SAMPLE_SIZE = 5


def ensure_required_files(run_dir: Path) -> dict[str, Path]:
    """Validate expected run artifacts and return canonical paths."""
    required = {
        "candidates": run_dir / "candidates.csv",
        "metadata": run_dir / "run_metadata.yaml",
    }

    summary_files = sorted(run_dir.glob("summary_*.csv"))
    if not summary_files:
        raise FileNotFoundError(f"No summary_*.csv files found under: {run_dir}")

    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required run artifacts in {run_dir}: {missing}")

    return {**required, "summaries": summary_files}


def build_quantile_buckets(series: pd.Series, bucket_count: int) -> pd.Series:
    """Build qcut labels with deterministic string bucket names."""
    valid = series.dropna()
    if valid.empty:
        return pd.Series(pd.NA, index=series.index, dtype="object")

    q = max(1, int(bucket_count))
    codes, bins = pd.qcut(valid, q=q, labels=False, retbins=True, duplicates="drop")
    labels = [f"q{i + 1}:{bins[i]:.6g}..{bins[i + 1]:.6g}" for i in range(len(bins) - 1)]
    mapped = codes.map(lambda idx: labels[int(idx)] if pd.notna(idx) else pd.NA)

    output = pd.Series(pd.NA, index=series.index, dtype="object")
    output.loc[valid.index] = mapped.astype("object")
    return output


def build_fixed_buckets(series: pd.Series, bins: list[float]) -> pd.Series:
    """Build fixed bins with explicit labels."""
    if len(bins) < 2:
        raise ValueError("fixed_bins must contain at least two edges")

    labels = [f"bin{i + 1}:{bins[i]:.6g}..{bins[i + 1]:.6g}" for i in range(len(bins) - 1)]
    return pd.cut(series, bins=bins, labels=labels, include_lowest=True).astype("object")


def summarize_bucket_metrics(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Return core trade metrics grouped by explicit columns."""
    if df.empty:
        return pd.DataFrame(
            columns=group_cols
            + [
                "trade_count",
                "win_count",
                "loss_count",
                "timeout_count",
                "win_rate",
                "avg_pnl_pips",
                "total_pnl_pips",
            ]
        )

    grouped = df.groupby(group_cols, dropna=False)
    rows: list[dict] = []
    for key, part in grouped:
        if not isinstance(key, tuple):
            key = (key,)

        row = dict(zip(group_cols, key))
        trade_count = int(len(part))
        win_count = int((part["outcome_status"] == "win").sum())
        loss_count = int((part["outcome_status"] == "loss").sum())
        timeout_count = int((part["outcome_status"] == "timeout").sum())
        row.update(
            {
                "trade_count": trade_count,
                "win_count": win_count,
                "loss_count": loss_count,
                "timeout_count": timeout_count,
                "win_rate": (win_count / trade_count) if trade_count else 0.0,
                "avg_pnl_pips": float(part["pnl_pips"].mean()) if trade_count else 0.0,
                "total_pnl_pips": float(part["pnl_pips"].sum()) if trade_count else 0.0,
            }
        )
        rows.append(row)

    out = pd.DataFrame(rows)
    return out.sort_values(group_cols).reset_index(drop=True)


def sanitize_filename_token(value: str) -> str:
    """Safe, deterministic token for output file names."""
    return value.replace("/", "_").replace(" ", "_")
