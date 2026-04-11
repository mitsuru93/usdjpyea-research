"""Feature pipeline for attaching decision-time snapshots to candidates."""

from __future__ import annotations

import pandas as pd

from research.features.baseline_snapshot import FEATURE_SET_VERSION, build_baseline_snapshot
from research.features.indicator_set import add_indicator_columns


def build_feature_frame(tagged_env_df: pd.DataFrame) -> pd.DataFrame:
    """Build a decision-time feature frame keyed by timestamp."""
    with_indicators = add_indicator_columns(tagged_env_df)
    return build_baseline_snapshot(with_indicators)


def attach_features_to_candidates(candidates_df: pd.DataFrame, feature_df: pd.DataFrame) -> pd.DataFrame:
    """Attach decision-time features to candidate rows by candidate timestamp.

    Candidate columns are canonical when names overlap (e.g. session/month),
    so merge output remains stable with no _x/_y suffix columns.
    """
    if candidates_df.empty:
        return candidates_df.copy()

    overlapping_cols = [
        col for col in feature_df.columns if col != "timestamp" and col in candidates_df.columns
    ]
    feature_cols = feature_df.drop(columns=overlapping_cols, errors="ignore")

    merged = candidates_df.merge(feature_cols, on="timestamp", how="left", validate="many_to_one")
    return merged


__all__ = [
    "FEATURE_SET_VERSION",
    "attach_features_to_candidates",
    "build_feature_frame",
]
