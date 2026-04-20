#!/usr/bin/env python3
"""Train a lightweight logistic regression for RV/TR research."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.rvtr_ml import add_split_column, feature_columns, one_hot_session_columns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train RV/TR logistic regression.")
    parser.add_argument("--label-table", required=True, help="Path to rvtr_label_table_trainable_v1.csv.gz.")
    parser.add_argument("--output-dir", required=True, help="Directory to write model artifacts into.")
    parser.add_argument("--max-iter", type=int, default=80, help="Maximum Newton iterations.")
    parser.add_argument("--ridge", type=float, default=1e-3, help="L2 regularization strength.")
    return parser.parse_args()


def _write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip" if path.suffix == ".gz" else None)


def _value_counts_dict(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts(dropna=False)
    result: dict[str, int] = {}
    for key, value in counts.items():
        if pd.isna(key):
            norm_key = "<NA>"
        else:
            norm_key = str(key)
        result[norm_key] = int(value)
    return result


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))


def _prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    base = df.loc[:, feature_columns() + ["session"]].copy()
    base = one_hot_session_columns(base)
    feature_cols = [col for col in base.columns if col != "session"]
    base = base.loc[:, feature_cols].apply(pd.to_numeric, errors="coerce")
    return base, feature_cols


def _standardize(train_x: pd.DataFrame, other_frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], pd.Series, pd.Series]:
    mean = train_x.mean(axis=0)
    std = train_x.std(axis=0, ddof=0).replace(0.0, 1.0).fillna(1.0)
    train_std = (train_x - mean) / std
    transformed = {name: (frame - mean) / std for name, frame in other_frames.items()}
    return train_std, transformed, mean, std


def _fit_logistic_newton(x: np.ndarray, y: np.ndarray, sample_weight: np.ndarray, max_iter: int, ridge: float) -> np.ndarray:
    weights = np.zeros(x.shape[1], dtype=float)
    ridge_mask = np.ones_like(weights)
    ridge_mask[0] = 0.0
    identity = np.eye(x.shape[1], dtype=float)
    for _ in range(max_iter):
        z = x @ weights
        p = _sigmoid(z)
        v = sample_weight * p * (1.0 - p)
        grad = x.T @ (sample_weight * (p - y)) + ridge * ridge_mask * weights
        hess = x.T @ (x * v[:, None]) + ridge * np.diag(ridge_mask)
        step = np.linalg.solve(hess + 1e-8 * identity, grad)
        next_weights = weights - step
        if np.linalg.norm(step) <= 1e-6 * (1.0 + np.linalg.norm(weights)):
            weights = next_weights
            break
        weights = next_weights
    return weights


def _auc_score(y_true: np.ndarray, y_score: np.ndarray) -> float:
    pos = int((y_true == 1).sum())
    neg = int((y_true == 0).sum())
    if pos == 0 or neg == 0:
        return float("nan")
    order = np.argsort(y_score, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1, dtype=float)
    pos_ranks = ranks[y_true == 1].sum()
    return float((pos_ranks - pos * (pos + 1) / 2.0) / (pos * neg))


def _split_metrics(y_true: np.ndarray, y_score: np.ndarray) -> dict[str, Any]:
    if len(y_true) == 0:
        return {"row_count": 0}
    pred = (y_score >= 0.5).astype(int)
    return {
        "row_count": int(len(y_true)),
        "positive_count": int(y_true.sum()),
        "negative_count": int((1 - y_true).sum()),
        "accuracy": float((pred == y_true).mean()),
        "logloss": float(-np.mean(y_true * np.log(np.clip(y_score, 1e-9, 1.0)) + (1 - y_true) * np.log(np.clip(1.0 - y_score, 1e-9, 1.0)))),
        "auc": _auc_score(y_true, y_score),
        "predicted_positive_rate": float(pred.mean()),
    }


def _apply_trainable_subset(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "label_rvtr_v1" in work.columns:
        work = work[work["label_rvtr_v1"].isin(["rv", "tr"])].copy()
    if "group_status" in work.columns:
        work = work[work["group_status"].astype(str).eq("complete_unique_pair")].copy()
    if "hard_gate_passed" in work.columns:
        work = work[work["hard_gate_passed"].fillna(False).astype(bool)].copy()
    else:
        work = work.iloc[0:0].copy()
    required_features = feature_columns() + ["session"]
    missing_feature_cols = [col for col in required_features if col not in work.columns]
    if missing_feature_cols:
        work = work.iloc[0:0].copy()
    else:
        feature_null_mask = work.loc[:, feature_columns()].isna().any(axis=1)
        feature_null_mask |= work["session"].isna()
        work = work.loc[~feature_null_mask].copy()
    return work


def _compute_trainable_subset_and_diagnostics(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    stage_counts: list[dict[str, Any]] = []
    work = df.copy()
    stage_counts.append({"stage": "raw", "row_count": int(len(work))})
    label_counts_raw = _value_counts_dict(work["label_rvtr_v1"]) if "label_rvtr_v1" in work.columns else {}
    group_status_counts_raw = _value_counts_dict(work["group_status"]) if "group_status" in work.columns else {}
    hard_gate_counts_raw = _value_counts_dict(work["hard_gate_passed"]) if "hard_gate_passed" in work.columns else {}

    if "label_rvtr_v1" in work.columns:
        work = work[work["label_rvtr_v1"].isin(["rv", "tr"])].copy()
    stage_counts.append({"stage": "after_label_filter", "row_count": int(len(work))})

    if "group_status" in work.columns:
        work = work[work["group_status"].astype(str).eq("complete_unique_pair")].copy()
    stage_counts.append({"stage": "after_group_status_filter", "row_count": int(len(work))})

    if "hard_gate_passed" in work.columns:
        work = work[work["hard_gate_passed"].fillna(False).astype(bool)].copy()
    else:
        work = work.iloc[0:0].copy()
    stage_counts.append({"stage": "after_hard_gate_filter", "row_count": int(len(work))})

    required_features = feature_columns() + ["session"]
    missing_feature_cols = [col for col in required_features if col not in work.columns]
    if missing_feature_cols:
        work = work.iloc[0:0].copy()
    else:
        feature_null_mask = work.loc[:, feature_columns()].isna().any(axis=1)
        feature_null_mask |= work["session"].isna()
        work = work.loc[~feature_null_mask].copy()
    stage_counts.append({"stage": "after_feature_non_null_filter", "row_count": int(len(work))})
    stage_counts.append({"stage": "final_trainable", "row_count": int(len(work))})

    diagnostics = {
        "raw_row_count": int(stage_counts[0]["row_count"]),
        "after_label_filter_row_count": int(stage_counts[1]["row_count"]),
        "after_group_status_filter_row_count": int(stage_counts[2]["row_count"]),
        "after_hard_gate_filter_row_count": int(stage_counts[3]["row_count"]),
        "after_feature_non_null_filter_row_count": int(stage_counts[4]["row_count"]),
        "final_trainable_row_count": int(stage_counts[5]["row_count"]),
        "missing_feature_columns": missing_feature_cols,
        "label_counts_raw": label_counts_raw,
        "group_status_counts_raw": group_status_counts_raw,
        "hard_gate_counts_raw": hard_gate_counts_raw,
    }
    return work, diagnostics


def _write_trainable_diagnostics(df_final: pd.DataFrame, diagnostics: dict[str, Any], output_dir: Path) -> None:
    diagnostics_out = dict(diagnostics)
    diagnostics_out["label_counts_final"] = _value_counts_dict(df_final["label_rvtr_v1"]) if "label_rvtr_v1" in df_final.columns else {}

    if not df_final.empty:
        split_counts_final = _value_counts_dict(add_split_column(df_final.copy())["split"])
    else:
        split_counts_final = {}
    diagnostics_out["split_counts_final"] = split_counts_final
    diagnostics_out["train_row_count"] = int(split_counts_final.get("train", 0))
    diagnostics_out["valid_row_count"] = int(split_counts_final.get("valid", 0))
    diagnostics_out["holdout_row_count"] = int(split_counts_final.get("holdout", 0))

    (output_dir / "rvtr_trainable_diagnostics.json").write_text(json.dumps(diagnostics_out, indent=2, sort_keys=True), encoding="utf-8")

    stage_counts_df = pd.DataFrame(
        [
            {"stage": "raw", "row_count": diagnostics_out["raw_row_count"]},
            {"stage": "after_label_filter", "row_count": diagnostics_out["after_label_filter_row_count"]},
            {"stage": "after_group_status_filter", "row_count": diagnostics_out["after_group_status_filter_row_count"]},
            {"stage": "after_hard_gate_filter", "row_count": diagnostics_out["after_hard_gate_filter_row_count"]},
            {"stage": "after_feature_non_null_filter", "row_count": diagnostics_out["after_feature_non_null_filter_row_count"]},
            {"stage": "final_trainable", "row_count": diagnostics_out["final_trainable_row_count"]},
        ]
    )
    _write_csv(output_dir / "rvtr_trainable_stage_counts.csv", stage_counts_df)

    label_distribution = pd.DataFrame(
        [{"label_rvtr_v1": key, "row_count": value} for key, value in diagnostics_out["label_counts_final"].items()]
    )
    _write_csv(output_dir / "rvtr_trainable_label_distribution.csv", label_distribution)

    group_distribution = pd.DataFrame(
        [{"group_status": key, "row_count": value} for key, value in diagnostics_out["group_status_counts_raw"].items()]
    )
    _write_csv(output_dir / "rvtr_trainable_group_status_distribution.csv", group_distribution)

    split_distribution = pd.DataFrame([{"split": key, "row_count": value} for key, value in split_counts_final.items()])
    _write_csv(output_dir / "rvtr_trainable_split_distribution.csv", split_distribution)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_df = pd.read_csv(args.label_table, compression="gzip")
    subset_df, diagnostics = _compute_trainable_subset_and_diagnostics(raw_df)
    _write_trainable_diagnostics(subset_df, diagnostics, output_dir)
    df = add_split_column(subset_df)
    if df.empty:
        raise ValueError("Training table is empty after filtering rv/tr rows.")

    split_masks = {
        "train": df["split"].eq("train"),
        "valid": df["split"].eq("valid"),
        "holdout": df["split"].eq("holdout"),
    }
    if split_masks["train"].sum() == 0:
        raise ValueError("No train rows found for 2024 split.")

    feature_frame, feature_cols = _prepare_features(df)
    y = (df["label_rvtr_v1"].astype(str) == "rv").astype(int).to_numpy()

    train_x = feature_frame.loc[split_masks["train"], feature_cols].astype(float)
    valid_x = feature_frame.loc[split_masks["valid"], feature_cols].astype(float)
    holdout_x = feature_frame.loc[split_masks["holdout"], feature_cols].astype(float)
    train_x_std, transformed, mean, std = _standardize(train_x, {"valid": valid_x, "holdout": holdout_x})

    train_y = y[split_masks["train"].to_numpy()]
    valid_y = y[split_masks["valid"].to_numpy()]
    holdout_y = y[split_masks["holdout"].to_numpy()]

    pos = float(train_y.sum())
    neg = float(len(train_y) - pos)
    pos_weight = len(train_y) / (2.0 * pos) if pos > 0 else 1.0
    neg_weight = len(train_y) / (2.0 * neg) if neg > 0 else 1.0
    sample_weight = np.where(train_y == 1, pos_weight, neg_weight).astype(float)

    x_train = np.column_stack([np.ones(len(train_x_std), dtype=float), train_x_std.to_numpy(dtype=float)])
    weights = _fit_logistic_newton(x_train, train_y.astype(float), sample_weight, args.max_iter, args.ridge)

    coef_std = weights[1:]
    intercept_std = float(weights[0])
    coef_original = coef_std / std.to_numpy(dtype=float)
    intercept_original = float(intercept_std - np.sum(coef_std * mean.to_numpy(dtype=float) / std.to_numpy(dtype=float)))

    def _predict(frame: pd.DataFrame) -> np.ndarray:
        if frame.empty:
            return np.array([], dtype=float)
        x = np.column_stack([np.ones(len(frame), dtype=float), frame.loc[:, feature_cols].to_numpy(dtype=float)])
        x[:, 1:] = (x[:, 1:] - mean.to_numpy(dtype=float)) / std.to_numpy(dtype=float)
        return _sigmoid(x @ weights)

    train_score = _predict(train_x)
    valid_score = _predict(valid_x)
    holdout_score = _predict(holdout_x)
    all_score = _predict(feature_frame.loc[:, feature_cols].astype(float))

    coef_df = pd.DataFrame(
        {
            "feature": ["intercept"] + feature_cols,
            "coef_standardized": [intercept_std] + coef_std.tolist(),
            "coef_original": [intercept_original] + coef_original.tolist(),
        }
    )
    coef_df["abs_coef_original"] = coef_df["coef_original"].abs()
    coef_df["sign"] = np.sign(coef_df["coef_original"]).astype(int)
    _write_csv(output_dir / "rvtr_logit_v1_coef.csv", coef_df.sort_values("abs_coef_original", ascending=False, kind="mergesort"))

    metrics = {
        "ridge": float(args.ridge),
        "max_iter": int(args.max_iter),
        "feature_count": int(len(feature_cols)),
        "train": _split_metrics(train_y, train_score),
        "valid": _split_metrics(valid_y, valid_score),
        "holdout": _split_metrics(holdout_y, holdout_score),
    }
    (output_dir / "rvtr_logit_v1_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    predictions = df.loc[:, [
        c
        for c in [
            "decision_group_id_v1",
            "source_run_dir",
            "band_token",
            "timestamp",
            "touch_side",
            "session",
            "month",
            "label_rvtr_v1",
            "split",
            "pnl_rv_pips",
            "pnl_tr_pips",
            "label_gap_rv_minus_tr_pips",
        ]
        if c in df.columns
    ]].copy()
    predictions["y_true_rv"] = y
    predictions["score_rv"] = all_score
    predictions["score_tr"] = 1.0 - all_score
    predictions["predicted_label"] = np.where(predictions["score_rv"] >= 0.5, "rv", "tr")
    predictions["predicted_correct"] = predictions["predicted_label"].eq(predictions["label_rvtr_v1"])
    _write_csv(output_dir / "rvtr_logit_v1_predictions.csv.gz", predictions)

    print(
        "RV/TR logistic training completed:",
        f"rows={len(df)}",
        f"features={len(feature_cols)}",
        f"out={output_dir}",
    )


if __name__ == "__main__":
    main()
