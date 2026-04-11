"""Feature engineering package for pre-MT4 research."""

from research.features.baseline_snapshot import FEATURE_SET_VERSION
from research.features.feature_pipeline import attach_features_to_candidates, build_feature_frame

__all__ = [
    "FEATURE_SET_VERSION",
    "attach_features_to_candidates",
    "build_feature_frame",
]
