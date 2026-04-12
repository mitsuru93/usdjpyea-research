"""Helpers for deterministic multi-run comparison outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_METRIC_COLUMNS = [
    "trade_count",
    "win_rate",
    "avg_pnl_pips",
    "total_pnl_pips",
]

FULL_METRIC_COLUMNS = [
    "trade_count",
    "win_count",
    "loss_count",
    "timeout_count",
    "win_rate",
    "avg_pnl_pips",
    "total_pnl_pips",
]


def load_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def ensure_columns(df: pd.DataFrame, required_cols: list[str], defaults: float = 0.0) -> pd.DataFrame:
    out = df.copy()
    for col in required_cols:
        if col not in out.columns:
            out[col] = defaults
    return out


def safe_label(label: str) -> str:
    return label.strip().replace(" ", "_").replace("/", "_")


def sort_key_frame(df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df

    work = df.copy()
    for col in key_cols:
        if col in work.columns:
            work[col] = work[col].fillna("<NA>").astype(str)

    existing = [c for c in key_cols if c in work.columns]
    if existing:
        work = work.sort_values(existing).reset_index(drop=True)
    return work


def compute_direction_summary(candidates_df: pd.DataFrame) -> pd.DataFrame:
    if candidates_df.empty or "direction" not in candidates_df.columns:
        return pd.DataFrame(columns=["direction"] + FULL_METRIC_COLUMNS)

    required = {"direction", "outcome_status", "pnl_pips"}
    if not required.issubset(set(candidates_df.columns)):
        return pd.DataFrame(columns=["direction"] + FULL_METRIC_COLUMNS)

    rows: list[dict] = []
    for direction, part in candidates_df.groupby("direction", dropna=False):
        trade_count = int(len(part))
        win_count = int((part["outcome_status"] == "win").sum())
        loss_count = int((part["outcome_status"] == "loss").sum())
        timeout_count = int((part["outcome_status"] == "timeout").sum())

        rows.append(
            {
                "direction": direction,
                "trade_count": trade_count,
                "win_count": win_count,
                "loss_count": loss_count,
                "timeout_count": timeout_count,
                "win_rate": (win_count / trade_count) if trade_count else 0.0,
                "avg_pnl_pips": float(part["pnl_pips"].mean()) if trade_count else 0.0,
                "total_pnl_pips": float(part["pnl_pips"].sum()) if trade_count else 0.0,
            }
        )

    return sort_key_frame(pd.DataFrame(rows), ["direction"])


def merge_section_frames(
    run_frames: list[tuple[str, pd.DataFrame]],
    key_cols: list[str],
    baseline_label: str,
) -> pd.DataFrame:
    merged: pd.DataFrame | None = None
    baseline_token = safe_label(baseline_label)
    variant_tokens: list[str] = []
    metric_cols_union: list[str] = []
    has_standard_metrics = False

    for label, frame in run_frames:
        token = safe_label(label)
        if token != baseline_token and token not in variant_tokens:
            variant_tokens.append(token)

        work = ensure_columns(frame, FULL_METRIC_COLUMNS)
        has_current_standard_metrics = any(col in frame.columns for col in FULL_METRIC_COLUMNS)
        has_standard_metrics = has_standard_metrics or has_current_standard_metrics
        dynamic_metrics = [
            col for col in frame.columns if col not in key_cols and pd.api.types.is_numeric_dtype(frame[col])
        ]
        for metric in dynamic_metrics:
            if metric not in metric_cols_union:
                metric_cols_union.append(metric)

        metric_cols = FULL_METRIC_COLUMNS if has_standard_metrics else dynamic_metrics
        keep_cols = key_cols + metric_cols
        work = work[[c for c in keep_cols if c in work.columns]].copy()
        work = work.rename(columns={metric: f"{token}_{metric}" for metric in metric_cols if metric in work.columns})

        if merged is None:
            merged = work
        elif key_cols:
            merged = merged.merge(work, on=key_cols, how="outer")
        else:
            merged = pd.concat([merged.reset_index(drop=True), work.reset_index(drop=True)], axis=1)

    if merged is None:
        return pd.DataFrame(columns=key_cols)

    metric_cols_for_delta = REQUIRED_METRIC_COLUMNS if has_standard_metrics else metric_cols_union
    primary_variant = variant_tokens[0] if variant_tokens else None
    for metric in metric_cols_for_delta:
        baseline_col = f"{baseline_token}_{metric}"
        if baseline_col not in merged.columns:
            merged[baseline_col] = 0.0

        for token in variant_tokens:
            run_col = f"{token}_{metric}"
            if run_col in merged.columns:
                delta_col = f"delta_{token}_{metric}_vs_baseline"
                merged[delta_col] = merged[run_col].fillna(0.0) - merged[baseline_col].fillna(0.0)
                if token == primary_variant:
                    merged[f"delta_{metric}_vs_baseline"] = merged[delta_col]

    return sort_key_frame(merged, key_cols)


def merge_bucket_frames(
    run_frames: list[tuple[str, pd.DataFrame]],
    key_cols: list[str],
    baseline_label: str,
) -> pd.DataFrame:
    merged: pd.DataFrame | None = None
    baseline_token = safe_label(baseline_label)
    variant_tokens: list[str] = []

    for label, frame in run_frames:
        token = safe_label(label)
        if token != baseline_token and token not in variant_tokens:
            variant_tokens.append(token)

        work = ensure_columns(frame, ["trade_count", "avg_pnl_pips"])
        keep = key_cols + ["trade_count", "avg_pnl_pips"]
        work = work[[c for c in keep if c in work.columns]].copy()
        work = work.rename(
            columns={
                "trade_count": f"{token}_trade_count",
                "avg_pnl_pips": f"{token}_avg_pnl_pips",
            }
        )
        merged = work if merged is None else merged.merge(work, on=key_cols, how="outer")

    if merged is None:
        return pd.DataFrame(columns=key_cols)

    primary_variant = variant_tokens[0] if variant_tokens else None
    for metric in ["trade_count", "avg_pnl_pips"]:
        baseline_col = f"{baseline_token}_{metric}"
        if baseline_col not in merged.columns:
            merged[baseline_col] = 0.0

        for token in variant_tokens:
            run_col = f"{token}_{metric}"
            if run_col in merged.columns:
                delta_col = f"delta_{token}_{metric}_vs_baseline"
                merged[delta_col] = merged[run_col].fillna(0.0) - merged[baseline_col].fillna(0.0)
                if token == primary_variant:
                    merged[f"delta_{metric}_vs_baseline"] = merged[delta_col]

    return sort_key_frame(merged, key_cols)


def build_missing_message(section: str, label: str, path: Path) -> str:
    return f"[{section}] missing artifact for run '{label}': {path}"
