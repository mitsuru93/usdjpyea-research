#!/usr/bin/env python3
"""Distill trained RV/TR logistic coefficients into hand-written total-score weights."""

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
    parser.add_argument("--coef-csv", required=True, help="Path to rvtr_logit_v1_coef.csv")
    parser.add_argument("--output-dir", required=True, help="Directory to write distilled artifacts into.")
    return parser.parse_args()


def _load_coef_frame(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "feature" not in df.columns or "coef_original" not in df.columns:
        raise ValueError(f"Coefficient CSV missing required columns: {path}")
    return df


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    coef_df = _load_coef_frame(Path(args.coef_csv).resolve())
    work = coef_df.copy()
    work = work[work["feature"].astype(str).str.lower() != "intercept"].copy()
    work["coef_original"] = pd.to_numeric(work["coef_original"], errors="coerce").fillna(0.0)
    work["abs_coef_original"] = work["coef_original"].abs()
    scale = float(work["abs_coef_original"].max()) if not work.empty else 1.0
    if scale <= 1e-9:
        scale = 1.0

    work["normalized_weight"] = work["coef_original"] / scale
    work["preferred_label"] = work["normalized_weight"].map(lambda x: "rv" if x >= 0.0 else "tr")
    work["weight_strength"] = work["normalized_weight"].abs()
    work["rv_score_weight"] = work["normalized_weight"]
    work["tr_score_weight"] = -work["normalized_weight"]

    rv_weights = {
        str(row.feature): float(row.rv_score_weight)
        for row in work.itertuples(index=False)
        if abs(float(row.rv_score_weight)) > 1e-12
    }
    tr_weights = {
        str(row.feature): float(row.tr_score_weight)
        for row in work.itertuples(index=False)
        if abs(float(row.tr_score_weight)) > 1e-12
    }

    distilled_payload = {
        "decision_policy_family": "total_score_rvtr_v2_ml",
        "score_bundle": "sf_ctx_base_v1",
        "entry_threshold": 0.75,
        "margin_threshold": 0.10,
        "no_entry_threshold": 0.25,
        "rv_score_weights": rv_weights,
        "tr_score_weights": tr_weights,
        "distillation": {
            "source_coef_csv": str(Path(args.coef_csv).resolve()),
            "normalization_scale": scale,
            "feature_count": int(len(work)),
        },
        "notes": "Research-only distilled total-score weights derived from RV/TR logistic coefficients.",
    }
    with (output_dir / "distilled_total_score_rvtr_v2.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(distilled_payload, f, sort_keys=False)

    feature_importance = work.loc[
        :, ["feature", "coef_original", "normalized_weight", "rv_score_weight", "tr_score_weight", "preferred_label", "weight_strength"]
    ].copy()
    feature_importance["abs_normalized_weight"] = feature_importance["normalized_weight"].abs()
    feature_importance = feature_importance.sort_values("abs_normalized_weight", ascending=False, kind="mergesort")
    feature_importance.to_csv(output_dir / "distilled_feature_importance.csv", index=False)

    print(
        "RV/TR score distillation completed:",
        f"features={len(feature_importance)}",
        f"scale={scale:.6f}",
        f"out={output_dir}",
    )


if __name__ == "__main__":
    main()
