#!/usr/bin/env python3
"""Train a lightweight RV/TR logistic model from the label table."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.rvtr_ml import feature_columns, one_hot_session_columns, prepare_trainable_label_table


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a regularized RV/TR logistic regression model.")
    parser.add_argument("--label-table", required=True, help="Path to rvtr_label_table_trainable_v1.csv.gz")
    parser.add_argument("--output-dir", required=True, help="Directory to write model artifacts into.")
    parser.add_argument("--l2", type=float, default=1.0, help="L2 regularization strength.")
    return parser.parse_args()


def _safe_read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-9, 1.0 - 1e-9)
    return np.log(p / (1.0 - p))


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-z))


def _weighted_log_loss(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> float:
    p = np.clip(p, 1e-9, 1.0 - 1e-9)
    return float(np.average(-(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)), weights=w))


def _balanced_accuracy(y: np.ndarray, pred: np.ndarray) -> float:
    pos = y == 1
    neg = y == 0
    tpr = float((pred[pos] == 1).mean()) if pos.any() else 0.0
    tnr = float((pred[neg] == 0).mean()) if neg.any() else 0.0
    return 0.5 * (tpr + tnr)


def _brier_score(y: np.ndarray, p: np.ndarray, w: np.ndarray) -> float:
    return float(np.average((p - y) ** 2, weights=w))


def _roc_auc(y: np.ndarray, score: np.ndarray, w: np.ndarray) -> float:
    y = y.astype(int)
    order = np.argsort(score)
    y_sorted = y[order]
    w_sorted = w[order]
    pos_w = float(w_sorted[y_sorted == 1].sum())
    neg_w = float(w_sorted[y_sorted == 0].sum())
    if pos_w <= 0.0 or neg_w <= 0.0:
        return 0.0
    cum_neg = np.cumsum(w_sorted * (y_sorted == 0))
    auc = float(np.sum(w_sorted * (y_sorted == 1) * cum_neg) / (pos_w * neg_w))
    return auc


def _fit_weighted_logistic(X: np.ndarray, y: np.ndarray, sample_weight: np.ndarray, l2: float) -> np.ndarray:
    n_samples, n_features = X.shape
    beta = np.zeros(n_features, dtype=float)
    reg = np.eye(n_features, dtype=float)
    reg[0, 0] = 0.0
    tol = 1e-8
    max_iter = 100

    for _ in range(max_iter):
        z = X @ beta
        p = _sigmoid(z)
        w = sample_weight * p * (1.0 - p)
        grad = X.T @ (sample_weight * (p - y)) + (l2 * reg @ beta)
        hess = X.T @ (X * w[:, None]) + (l2 * reg)
        hess = hess + np.eye(n_features) * 1e-9
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(hess, grad, rcond=None)[0]
        beta_next = beta - step
        if float(np.max(np.abs(beta_next - beta))) < tol:
            beta = beta_next
            break
        beta = beta_next
    return beta


def _build_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    work = prepare_trainable_label_table(df)
    work = one_hot_session_columns(work)
    cols = [col for col in feature_columns() if col in work.columns]
    session_cols = [col for col in work.columns if col.startswith("session__")]
    cols.extend([col for col in session_cols if col not in cols])
    matrix = work.loc[:, cols].copy() if cols else pd.DataFrame(index=work.index)
    for col in cols:
        matrix[col] = pd.to_numeric(matrix[col], errors="coerce")
    return matrix, cols


def _split_metrics(df: pd.DataFrame, probs: np.ndarray, sample_weight: np.ndarray) -> dict[str, dict[str, float]]:
    work = df.copy()
    work["prob_rv"] = probs
    work["pred_label"] = np.where(work["prob_rv"] >= 0.5, "rv", "tr")
    work["y"] = (work["label_rvtr_v1"] == "rv").astype(int)

    metrics: dict[str, dict[str, float]] = {}
    for split_name in ["train", "valid", "holdout"]:
        mask = work["split"] == split_name
        part = work.loc[mask].copy()
        if part.empty:
            metrics[split_name] = {
                "row_count": 0,
                "rv_rate": 0.0,
                "accuracy": 0.0,
                "balanced_accuracy": 0.0,
                "log_loss": 0.0,
                "brier": 0.0,
                "roc_auc": 0.0,
            }
            continue
        y = part["y"].to_numpy(dtype=float)
        p = part["prob_rv"].to_numpy(dtype=float)
        w = sample_weight[mask.to_numpy()]
        pred = (p >= 0.5).astype(int)
        metrics[split_name] = {
            "row_count": int(len(part)),
            "rv_rate": float(y.mean()),
            "accuracy": float((pred == y).mean()),
            "balanced_accuracy": _balanced_accuracy(y, pred),
            "log_loss": _weighted_log_loss(y, p, w),
            "brier": _brier_score(y, p, w),
            "roc_auc": _roc_auc(y, p, w),
        }
    return metrics


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    label_table = _safe_read_csv(Path(args.label_table).resolve())
    if label_table.empty:
        raise ValueError("Label table is empty.")
    label_table = prepare_trainable_label_table(label_table)
    label_table = label_table[label_table["label_rvtr_v1"].isin(["rv", "tr"])].copy()
    label_table = label_table[label_table["group_status"].eq("complete_unique_pair")].copy()
    label_table = label_table[label_table["hard_gate_passed"].astype(bool)].copy()
    label_table = label_table[label_table["split"].isin(["train", "valid", "holdout"])].copy()
    if label_table.empty:
        raise ValueError("No trainable rows available after filtering.")

    X_df, cols = _build_matrix(label_table)
    if not cols:
        raise ValueError("No usable feature columns found for logistic training.")

    X = X_df.to_numpy(dtype=float)
    y = (label_table["label_rvtr_v1"] == "rv").astype(int).to_numpy(dtype=float)

    train_mask = label_table["split"] == "train"
    if not bool(train_mask.any()):
        raise ValueError("Training split is empty; cannot fit time-series model.")

    train_X = X[train_mask.to_numpy()]
    train_y = y[train_mask.to_numpy()]
    train_count = len(train_y)
    pos_count = float((train_y == 1).sum())
    neg_count = float((train_y == 0).sum())
    if pos_count <= 0.0 or neg_count <= 0.0:
        raise ValueError("Training split must contain both rv and tr labels.")
    w_pos = train_count / (2.0 * pos_count)
    w_neg = train_count / (2.0 * neg_count)
    sample_weight = np.where(y == 1, w_pos, w_neg).astype(float)

    feature_mean = train_X.mean(axis=0)
    feature_std = train_X.std(axis=0, ddof=0)
    feature_std = np.where(feature_std <= 1e-9, 1.0, feature_std)

    X_scaled = (X - feature_mean) / feature_std
    X_design = np.column_stack([np.ones(len(X_scaled)), X_scaled])
    beta_scaled = _fit_weighted_logistic(X_design[train_mask.to_numpy()], train_y, sample_weight[train_mask.to_numpy()], float(args.l2))

    coef_scaled = beta_scaled[1:]
    intercept_scaled = float(beta_scaled[0])
    coef_original = coef_scaled / feature_std
    intercept_original = intercept_scaled - float(np.sum(coef_scaled * feature_mean / feature_std))

    logits = intercept_scaled + (X_scaled @ coef_scaled)
    probs = _sigmoid(logits)

    metrics = _split_metrics(label_table, probs, sample_weight)
    metrics["overall"] = {
        "row_count": int(len(label_table)),
        "rv_rate": float(y.mean()),
        "accuracy": float(((probs >= 0.5).astype(int) == y).mean()),
        "balanced_accuracy": _balanced_accuracy(y, (probs >= 0.5).astype(int)),
        "log_loss": _weighted_log_loss(y, probs, sample_weight),
        "brier": _brier_score(y, probs, sample_weight),
        "roc_auc": _roc_auc(y, probs, sample_weight),
    }

    coef_rows = [
        {
            "feature": "intercept",
            "coef_original": intercept_original,
            "coef_scaled": intercept_scaled,
            "abs_coef_original": abs(intercept_original),
            "feature_mean": 0.0,
            "feature_std": 1.0,
            "preferred_label": "rv" if intercept_original >= 0.0 else "tr",
        }
    ]
    for idx, feature in enumerate(cols):
        coef = float(coef_original[idx])
        coef_rows.append(
            {
                "feature": feature,
                "coef_original": coef,
                "coef_scaled": float(coef_scaled[idx]),
                "abs_coef_original": abs(coef),
                "feature_mean": float(feature_mean[idx]),
                "feature_std": float(feature_std[idx]),
                "preferred_label": "rv" if coef >= 0.0 else "tr",
            }
        )

    coef_df = pd.DataFrame(coef_rows).sort_values("abs_coef_original", ascending=False, kind="mergesort")
    coef_df.to_csv(output_dir / "rvtr_logit_v1_coef.csv", index=False)

    pred_df = label_table.copy()
    pred_df["prob_rv"] = probs
    pred_df["prob_tr"] = 1.0 - probs
    pred_df["pred_label"] = np.where(pred_df["prob_rv"] >= 0.5, "rv", "tr")
    pred_df["pred_margin"] = pred_df["prob_rv"] - 0.5
    pred_df["is_correct"] = pred_df["pred_label"].eq(pred_df["label_rvtr_v1"])
    pred_df["sample_weight"] = sample_weight
    pred_df.to_csv(output_dir / "rvtr_logit_v1_predictions.csv.gz", index=False, compression="gzip")

    metrics_path = output_dir / "rvtr_logit_v1_metrics.json"
    metrics_payload = {
        "l2": float(args.l2),
        "train_row_count": int(train_mask.sum()),
        "feature_count": int(len(cols)),
        "class_weights": {"rv": float(w_pos), "tr": float(w_neg)},
        "splits": metrics,
        "feature_columns": cols,
        "feature_standardization": {
            "feature": cols,
            "mean": [float(x) for x in feature_mean],
            "std": [float(x) for x in feature_std],
        },
    }
    metrics_path.write_text(json.dumps(metrics_payload, indent=2, sort_keys=True), encoding="utf-8")

    print(
        "RV/TR logistic training completed:",
        f"rows={len(label_table)}",
        f"features={len(cols)}",
        f"out={output_dir}",
    )


if __name__ == "__main__":
    main()
