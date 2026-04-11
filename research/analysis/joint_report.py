"""Simple two-feature joint pivot report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from research.analysis.report_utils import build_quantile_buckets, sanitize_filename_token


def generate_joint_reports(
    df: pd.DataFrame,
    output_dir: Path,
    selected_feature_pairs: list[tuple[str, str]],
    quantile_bucket_count: int,
) -> list[Path]:
    """Generate average pnl and trade count pivots for each feature pair."""
    output_paths: list[Path] = []

    for feature_x, feature_y in selected_feature_pairs:
        if feature_x not in df.columns or feature_y not in df.columns:
            continue

        work = df.copy()
        work["bucket_x"] = build_quantile_buckets(work[feature_x], quantile_bucket_count)
        work["bucket_y"] = build_quantile_buckets(work[feature_y], quantile_bucket_count)
        work = work[work["bucket_x"].notna() & work["bucket_y"].notna()].copy()
        if work.empty:
            continue

        avg_pnl = pd.pivot_table(
            work,
            values="pnl_pips",
            index="bucket_x",
            columns="bucket_y",
            aggfunc="mean",
            dropna=False,
        )
        trade_count = pd.pivot_table(
            work,
            values="pnl_pips",
            index="bucket_x",
            columns="bucket_y",
            aggfunc="count",
            dropna=False,
        )

        x_token = sanitize_filename_token(feature_x)
        y_token = sanitize_filename_token(feature_y)

        avg_path = output_dir / f"joint__{x_token}__{y_token}__avg_pnl.csv"
        count_path = output_dir / f"joint__{x_token}__{y_token}__trade_count.csv"

        avg_pnl.to_csv(avg_path)
        trade_count.to_csv(count_path)

        output_paths.extend([avg_path, count_path])

    return output_paths
