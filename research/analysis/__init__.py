"""Post-run analysis package for feature bucket/joint reports."""

from research.analysis.bucket_report import generate_bucket_reports
from research.analysis.joint_report import generate_joint_reports
from research.analysis.report_utils import (
    DEFAULT_FEATURE_PAIRS,
    DEFAULT_FEATURES,
    DEFAULT_QUANTILE_BUCKET_COUNT,
    DEFAULT_SLICE_MODES,
    MIN_UNSTABLE_SAMPLE_SIZE,
    ensure_required_files,
)

__all__ = [
    "DEFAULT_FEATURE_PAIRS",
    "DEFAULT_FEATURES",
    "DEFAULT_QUANTILE_BUCKET_COUNT",
    "DEFAULT_SLICE_MODES",
    "MIN_UNSTABLE_SAMPLE_SIZE",
    "ensure_required_files",
    "generate_bucket_reports",
    "generate_joint_reports",
]
