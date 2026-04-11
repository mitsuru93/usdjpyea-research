"""Single-feature bucket report generation for post-run analysis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from research.analysis.report_utils import (
    DEFAULT_SLICE_MODES,
    build_fixed_buckets,
    build_quantile_buckets,
    sanitize_filename_token,
    summarize_bucket_metrics,
)

SLICE_TO_GROUP_COL = {
    "overall": None,
    "by_family": "candidate_family",
    "by_direction": "direction",
    "by_session": "session",
}


def generate_bucket_reports(
    df: pd.DataFrame,
    output_dir: Path,
    selected_features: list[str],
    quantile_bucket_count: int,
    slice_modes: list[str] | None = None,
    bucket_mode: str = "quantile",
    fixed_bins_by_feature: dict[str, list[float]] | None = None,
) -> list[Path]:
    """Write bucket CSVs and return generated file paths."""
    fixed_bins_by_feature = fixed_bins_by_feature or {}
    modes = slice_modes or DEFAULT_SLICE_MODES

    output_paths: list[Path] = []
    for feature in selected_features:
        if feature not in df.columns:
            continue

        work = df.copy()
        if bucket_mode == "fixed" and feature in fixed_bins_by_feature:
            work["bucket"] = build_fixed_buckets(work[feature], fixed_bins_by_feature[feature])
            bucket_mode_used = "fixed"
        else:
            work["bucket"] = build_quantile_buckets(work[feature], quantile_bucket_count)
            bucket_mode_used = "quantile"

        work = work[work["bucket"].notna()].copy()
        if work.empty:
            continue

        feature_token = sanitize_filename_token(feature)
        for mode in modes:
            if mode not in SLICE_TO_GROUP_COL:
                continue

            slice_col = SLICE_TO_GROUP_COL[mode]
            group_cols = ["bucket"] if slice_col is None else [slice_col, "bucket"]
            report = summarize_bucket_metrics(work, group_cols)
            report.insert(0, "feature", feature)
            report.insert(1, "bucket_mode", bucket_mode_used)

            out_path = output_dir / f"bucket_{mode}__{feature_token}.csv"
            report.to_csv(out_path, index=False)
            output_paths.append(out_path)

    return output_paths
