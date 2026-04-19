#!/usr/bin/env python3
"""Distill RV/TR logistic coefficients into hand-written score weights."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Distill RV/TR logistic coefficients into score weights.")
    parser.add_argument("--coef-csv", required=True, help="Path to rvtr_logit_v1_coef.csv.")
    parser.add_argument("--output-dir", required=True, help="Directory to write distilled score artifacts into.")
    return parser.parse_args()


def _write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    coef_df = pd.read_csv(args.coef_csv)
    work = coef_df[coef_df["feature"].astype(str) != "intercept"].copy()
    work["coef_original"] = pd.to_numeric(work["coef_original"], errors="coerce").fillna(0.0)
    work["abs_coef_original"] = work["coef_original"].abs()
    work = work.sort_values("abs_coef_original", ascending=False, kind="mergesort")

    max_abs = float(work["abs_coef_original"].max()) if not work.empty else 1.0
    scale = max_abs / 10.0 if max_abs > 0 else 1.0
    work["normalized_weight"] = work["coef_original"] / scale if scale else work["coef_original"]
    work["rv_score_weight"] = work["normalized_weight"].clip(lower=0.0)
    work["tr_score_weight"] = (-work["normalized_weight"]).clip(lower=0.0)
    work["direction"] = work["coef_original"].map(lambda x: "rv" if x >= 0 else "tr")

    feature_importance = work.loc[:, [
        "feature",
        "coef_original",
        "abs_coef_original",
        "normalized_weight",
        "direction",
        "rv_score_weight",
        "tr_score_weight",
    ]]
    _write_csv(output_dir / "distilled_feature_importance.csv", feature_importance)

    rv_weights = {str(row.feature): float(row.rv_score_weight) for row in feature_importance.itertuples(index=False)}
    tr_weights = {str(row.feature): float(row.tr_score_weight) for row in feature_importance.itertuples(index=False)}
    payload = {
        "decision_policy_family": "total_score_rvtr_v2_ml",
        "decision_policy_version": "v2_ml",
        "entry_threshold": 0.0,
        "margin_threshold": 0.0,
        "rv_score_weights": rv_weights,
        "tr_score_weights": tr_weights,
        "notes": [
            "Distilled from logistic coefficients for explainable RV/TR research scoring.",
            "Positive coefficients support RV; negative coefficients support TR.",
            "Weights remain hand-readable and comparable to total_score_rvtr_v1 style inputs.",
        ],
    }
    (output_dir / "distilled_total_score_rvtr_v2.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    print(
        "RV/TR score distillation completed:",
        f"features={len(feature_importance)}",
        f"scale={scale:.6f}",
        f"out={output_dir}",
    )


if __name__ == "__main__":
    main()
