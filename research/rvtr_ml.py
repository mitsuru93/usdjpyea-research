"""Shared helpers for the RV/TR ML research pipeline.

Research-only helpers for label sourcing, feature construction, and time-based
splits. The code intentionally stays on the research side and does not touch
Core / MT4 production paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from research.io.csv_loader import load_ohlc_csv
from research.orchestration.path_utils import sanitize_label

PIP_SIZE = 0.01
LABEL_GAP_THRESHOLD_PIPS = 2.0
TRAIN_START = pd.Timestamp("2024-01-01")
TRAIN_END = pd.Timestamp("2024-12-31 23:59:59")
VALID_START = pd.Timestamp("2025-01-01")
VALID_END = pd.Timestamp("2025-10-31 23:59:59")
HOLDOUT_START = pd.Timestamp("2025-11-01")
HOLDOUT_END = pd.Timestamp("2026-02-18 23:59:59")

SHORTLIST_BANDS = {
    "ATR04_P07",
    "ATR04_P14",
    "ATR04_P28",
    "ATR05_P07",
    "ATR05_P14",
}
COMPARISON_BANDS = {
    "PARK08_P10",
    "PARK08_P20",
}
CONTROL_BANDS = {"bin_env_v1"}

PRIMARY_AUDIT_NAMES = ("rvtr_label_source_rows.csv.gz", "candidates_decision_policy_audit.csv", "candidates_policy_audit.csv")
PRIMARY_OUTCOME_NAMES = ("candidates_aggregate.csv.gz", "candidates.csv")
AUDIT_READ_COLUMNS = (
    "timestamp",
    "touch_side",
    "candidate_family",
    "direction",
    "candidate_id",
    "pnl_pips",
    "session",
    "month",
    "pre10_change_pips",
    "pre30_change_pips",
    "pre60_change_pips",
    "net10_change_pips",
    "dist_from_ema_pips",
    "atr14_pips",
    "atr5_pips",
    "rsi14",
    "macd_hist",
    "bb_width_ratio_to_close",
    "atr_ratio_5_14",
    "envelope_upper",
    "upper_env",
    "envelope_lower",
    "lower_env",
    "hard_gate_passed",
    "band_token",
    "band_label",
    "band_name",
)
OUTCOME_READ_COLUMNS = (
    "candidate_id",
    "timestamp",
    "touch_side",
    "candidate_family",
    "direction",
    "pnl_pips",
)
LABEL_BUILD_REQUIRED_COLUMNS = ("timestamp", "touch_side", "candidate_family", "pnl_pips")


@dataclass(frozen=True)
class RunArtifact:
    run_dir: Path
    source_path: Path
    metadata_path: Path | None
    band_config_path: Path | None
    rows: pd.DataFrame
    metadata: dict[str, Any]
    band_config: dict[str, Any]


def _load_yaml(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping YAML at {path}")
    return payload


def _resolve_metadata_path(run_dir: Path) -> Path | None:
    """Resolve metadata from run_metadata.yaml first, then ancestor study_metadata.yaml."""
    run_metadata = run_dir / "run_metadata.yaml"
    if run_metadata.exists():
        return run_metadata
    for parent in [run_dir] + list(run_dir.parents):
        study_metadata = parent / "study_metadata.yaml"
        if study_metadata.exists():
            return study_metadata
    return None


@lru_cache(maxsize=8)
def _load_ohlc_cached(csv_path: str) -> pd.DataFrame:
    return load_ohlc_csv(csv_path)


def load_ohlc_for_run(metadata: dict[str, Any], repo_root: Path) -> pd.DataFrame | None:
    raw_path = str(metadata.get("input_csv", "")).strip()
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    if not path.exists():
        return None
    return _load_ohlc_cached(str(path))


def _iter_run_dirs(source_root: Path) -> list[Path]:
    if not source_root.exists():
        return []
    if source_root.is_file():
        return [source_root.parent]
    run_dirs: set[Path] = set()
    for name in PRIMARY_AUDIT_NAMES + PRIMARY_OUTCOME_NAMES:
        for candidate_path in source_root.rglob(name):
            run_dirs.add(candidate_path.parent)
    return sorted(run_dirs)


def _first_existing(run_dir: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = run_dir / name
        if path.exists():
            return path
    return None


def _first_existing_name(run_dir: Path, names: tuple[str, ...], missing: str = "missing") -> str:
    path = _first_existing(run_dir, names)
    return path.name if path is not None else missing


def _value_counts_str(series: pd.Series, limit: int = 20) -> str:
    if series.empty:
        return ""
    counts = series.value_counts(dropna=False).head(limit)
    parts: list[str] = []
    for key, value in counts.items():
        text = str(key)
        if text in {"nan", "None", "NaT"}:
            text = "<missing>"
        parts.append(f"{text}:{int(value)}")
    return "|".join(parts)


def _merge_outcome_table(audit_df: pd.DataFrame, outcome_df: pd.DataFrame) -> pd.DataFrame:
    if audit_df.empty or outcome_df.empty:
        return audit_df.copy()
    if "pnl_pips" in audit_df.columns and audit_df["pnl_pips"].notna().any():
        return audit_df.copy()
    if "pnl_pips" not in outcome_df.columns:
        return audit_df.copy()

    join_candidates = [
        ["candidate_id"],
        ["timestamp", "touch_side", "candidate_family", "direction"],
        ["timestamp", "candidate_family", "direction"],
    ]
    for keys in join_candidates:
        if all(key in audit_df.columns and key in outcome_df.columns for key in keys):
            keep_cols = list(dict.fromkeys(keys + ["pnl_pips"]))
            merged = audit_df.merge(
                outcome_df.loc[:, keep_cols].drop_duplicates(keys, keep="last"),
                on=keys,
                how="left",
                suffixes=("", "_outcome"),
            )
            if merged["pnl_pips"].notna().any():
                return merged

    if len(audit_df) == len(outcome_df):
        merged = audit_df.copy().reset_index(drop=True)
        merged["pnl_pips"] = pd.to_numeric(outcome_df["pnl_pips"], errors="coerce").reset_index(drop=True)
        return merged

    return audit_df.copy()


def _read_csv_columns(path: Path, requested_cols: tuple[str, ...]) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0, low_memory=False)
    existing_cols = [col for col in requested_cols if col in header.columns]
    if not existing_cols:
        return pd.DataFrame()
    return pd.read_csv(path, usecols=existing_cols, low_memory=False)


def load_run_rows(run_dir: str | Path) -> pd.DataFrame:
    """Load one run directory and merge audit/outcome artifacts when both exist."""
    run_dir = Path(run_dir)
    audit_path = _first_existing(run_dir, PRIMARY_AUDIT_NAMES)
    outcome_path = _first_existing(run_dir, PRIMARY_OUTCOME_NAMES)
    if audit_path is None and outcome_path is None:
        return pd.DataFrame()
    if audit_path is None:
        return _read_csv_columns(outcome_path, OUTCOME_READ_COLUMNS)
    requested_cols = AUDIT_READ_COLUMNS
    if audit_path.name == "rvtr_label_source_rows.csv.gz":
        requested_cols = tuple(dict.fromkeys(AUDIT_READ_COLUMNS + OUTCOME_READ_COLUMNS))
    audit_df = _read_csv_columns(audit_path, requested_cols)
    if outcome_path is None:
        return audit_df
    outcome_df = _read_csv_columns(outcome_path, OUTCOME_READ_COLUMNS)
    return _merge_outcome_table(audit_df, outcome_df)


def _load_run_artifact(run_dir: Path, band_config: dict[str, Any] | None = None) -> RunArtifact | None:
    rows = load_run_rows(run_dir)
    if rows.empty:
        return None
    metadata_path = _resolve_metadata_path(run_dir)
    band_config_path = run_dir / "effective_band_config.yaml"
    metadata = _load_yaml(metadata_path)
    effective_band_config = band_config if band_config is not None else _load_yaml(band_config_path)
    source_path = _first_existing(run_dir, PRIMARY_AUDIT_NAMES + PRIMARY_OUTCOME_NAMES)
    if source_path is None:
        return None
    return RunArtifact(
        run_dir=run_dir,
        source_path=source_path,
        metadata_path=metadata_path,
        band_config_path=band_config_path if band_config_path.exists() else None,
        rows=rows,
        metadata=metadata,
        band_config=effective_band_config,
    )


def load_run_artifacts(source_root: str | Path) -> list[RunArtifact]:
    root = Path(source_root).resolve()
    artifacts: list[RunArtifact] = []
    for run_dir in _iter_run_dirs(root):
        artifact = _load_run_artifact(run_dir)
        if artifact is not None:
            artifacts.append(artifact)
    return artifacts


def _band_token_from_band_config(band_config: dict[str, Any]) -> str:
    band_model = str(band_config.get("band_model", "")).strip().lower()
    if not band_model:
        return ""
    if band_model == "atr":
        k = float(band_config.get("band_atr_k", band_config.get("band_value", 0.0)) or 0.0)
        period = int(float(band_config.get("band_atr_period", 0) or 0))
        return f"ATR{int(round(k * 10)):02d}_P{period:02d}"
    if band_model == "parkinson":
        k = float(band_config.get("band_vol_k", band_config.get("band_value", 0.0)) or 0.0)
        period = int(float(band_config.get("band_vol_period", 0) or 0))
        return f"PARK{int(round(k * 10)):02d}_P{period:02d}"
    if band_model == "fixed_pips":
        pips = float(band_config.get("band_pips", band_config.get("band_value", 0.0)) or 0.0)
        return f"PIP{int(round(pips)):02d}"
    if band_model == "percent":
        pct = float(band_config.get("band_percent", band_config.get("band_value", 0.0)) or 0.0)
        return f"PCT{int(round(pct * 1000)):03d}"
    return sanitize_label(band_model).upper()


def _normalize_band_token(token: str) -> str:
    return str(token).strip().upper()


def _scalar_float(value: Any, default: float = 0.0) -> float:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return float(default)
    return float(numeric)


def _session_core(session: str) -> float:
    text = str(session).strip().lower()
    if text == "asia":
        return -1.0
    if text == "tokyo":
        return -0.5
    if text == "london":
        return 1.0
    if text in {"ny", "newyork", "new_york"}:
        return 0.75
    return 0.0


def _safe_ts(value: Any) -> pd.Timestamp:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid timestamp value: {value!r}")
    return pd.Timestamp(ts)


def _series_or_default(df: pd.DataFrame, col: str, default: float | str | None = np.nan) -> pd.Series:
    if col in df.columns:
        return df[col]
    if isinstance(default, str):
        return pd.Series(default, index=df.index, dtype="object")
    return pd.Series(default, index=df.index, dtype="float64")


def _lookup_close_frame(ohlc_df: pd.DataFrame | None) -> pd.DataFrame | None:
    if ohlc_df is None or ohlc_df.empty:
        return None
    frame = ohlc_df.loc[:, ["datetime", "close"]].copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    for window in (5, 30, 60):
        frame[f"close_lag_{window}"] = frame["close"].shift(window)
    return frame


def _build_family_block_scores(base: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=base.index)
    out["rv_band_score"] = base["dist_from_ema_norm_by_band"]
    out["tr_band_score"] = base["dist_from_ema_norm_by_band"]
    out["rv_timing_score"] = -base["session_core"]
    out["tr_timing_score"] = base["session_core"]
    out["rv_momo_score"] = -base["directional_momo_core"]
    out["tr_momo_score"] = base["directional_momo_core"]
    out["rv_stretch_score"] = base["dist_from_ema_norm_by_atr"]
    out["tr_stretch_score"] = base["dist_from_ema_norm_by_atr"]
    out["rv_regime_score"] = -base["regime_core"]
    out["tr_regime_score"] = base["regime_core"]
    out["rv_exit_proxy_score"] = -base["exit_proxy_core"]
    out["tr_exit_proxy_score"] = base["exit_proxy_core"]
    return out


def _build_feature_frame(candidate_rows: pd.DataFrame, close_frame: pd.DataFrame | None) -> pd.DataFrame:
    work = candidate_rows.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce")
    work["session"] = _series_or_default(work, "session", "").astype(str).str.strip()
    work["candidate_family"] = _series_or_default(work, "candidate_family", "").astype(str).str.lower()
    work["direction"] = _series_or_default(work, "direction", "").astype(str).str.lower()
    work["pre10_change_pips"] = pd.to_numeric(_series_or_default(work, "pre10_change_pips"), errors="coerce")
    work["pre30_change_pips"] = pd.to_numeric(_series_or_default(work, "pre30_change_pips"), errors="coerce")
    work["pre60_change_pips"] = pd.to_numeric(_series_or_default(work, "pre60_change_pips"), errors="coerce")
    work["net10_change_pips"] = pd.to_numeric(_series_or_default(work, "net10_change_pips"), errors="coerce")
    work["dist_from_ema_pips"] = pd.to_numeric(_series_or_default(work, "dist_from_ema_pips"), errors="coerce")
    work["atr14_pips"] = pd.to_numeric(_series_or_default(work, "atr14_pips"), errors="coerce")
    work["atr5_pips"] = pd.to_numeric(_series_or_default(work, "atr5_pips"), errors="coerce")
    work["rsi14"] = pd.to_numeric(_series_or_default(work, "rsi14", 50.0), errors="coerce").fillna(50.0)
    work["macd_hist"] = pd.to_numeric(_series_or_default(work, "macd_hist"), errors="coerce")
    work["bb_width_ratio_to_close"] = pd.to_numeric(_series_or_default(work, "bb_width_ratio_to_close"), errors="coerce")
    work["atr_ratio_5_14"] = pd.to_numeric(_series_or_default(work, "atr_ratio_5_14", 1.0), errors="coerce").fillna(1.0)
    work["envelope_upper"] = pd.to_numeric(
        _series_or_default(work, "envelope_upper").combine_first(_series_or_default(work, "upper_env")),
        errors="coerce",
    )
    work["envelope_lower"] = pd.to_numeric(
        _series_or_default(work, "envelope_lower").combine_first(_series_or_default(work, "lower_env")),
        errors="coerce",
    )
    work["month"] = _series_or_default(work, "month", "").astype(str)
    work.loc[work["month"].isin(["", "nan", "NaT", "None"]), "month"] = work["timestamp"].dt.strftime("%Y-%m")
    work.loc[work["month"].isin(["", "nan", "NaT", "None"]), "month"] = ""

    work["direction_sign"] = np.select(
        [work["direction"].eq("buy"), work["direction"].eq("sell")],
        [1.0, -1.0],
        default=0.0,
    )
    work["session_core"] = work["session"].map(_session_core).astype(float)
    work["atr14_safe"] = work["atr14_pips"].where(work["atr14_pips"].abs() > 1e-9, 1.0)
    band_width_pips = ((work["envelope_upper"] - work["envelope_lower"]) / PIP_SIZE).fillna(0.0)
    band_half_width_pips = (band_width_pips / 2.0).where(band_width_pips.abs() > 1e-9, 1.0)

    work["dist_from_ema_norm_by_band"] = work["dist_from_ema_pips"] / band_half_width_pips
    work["dist_from_ema_norm_by_atr"] = work["dist_from_ema_pips"] / work["atr14_safe"]
    work["band_width_norm_vs_atr"] = band_width_pips / work["atr14_safe"]
    work["directional_momo_core"] = (
        work["direction_sign"] * (0.6 * work["pre10_change_pips"] + 0.3 * work["pre30_change_pips"] + 0.1 * work["net10_change_pips"]) / 10.0
    )
    work["regime_core"] = ((work["atr_ratio_5_14"] - 1.0) * 0.75) + (0.25 * work["bb_width_ratio_to_close"].fillna(0.0) * 100.0)

    if close_frame is not None and not close_frame.empty:
        merged = work.merge(close_frame, left_on="timestamp", right_on="datetime", how="left")
        for window in (5, 30, 60):
            merged[f"m{window if window != 60 else '1'}_slope"] = (
                (merged["close"] - merged[f"close_lag_{window}"]) / float(window) / PIP_SIZE
            )
        merged["m5_slope"] = merged["m5_slope"].fillna(0.0)
        merged["m30_slope"] = merged["m30_slope"].fillna(0.0)
        merged["h1_slope"] = merged["m1_slope"].fillna(0.0)
        work = merged.drop(columns=[c for c in ["datetime", "close", "close_lag_5", "close_lag_30", "close_lag_60", "m1_slope"] if c in merged.columns])
    else:
        work["m5_slope"] = 0.0
        work["m30_slope"] = 0.0
        work["h1_slope"] = 0.0

    work["exit_proxy_core"] = (0.5 * work["m5_slope"]) + (0.3 * work["m30_slope"]) + (0.2 * work["h1_slope"]) + (0.1 * work["macd_hist"].fillna(0.0) * 100.0)

    work = pd.concat([work, _build_family_block_scores(work)], axis=1)
    return work


def _band_token_for_artifact(artifact: RunArtifact, first_row: pd.Series | None) -> str:
    for col in ("band_token", "band_label", "band_name"):
        if first_row is not None and col in first_row.index:
            token = str(first_row.get(col, "")).strip()
            if token:
                return _normalize_band_token(token)
    if artifact.band_config:
        return _normalize_band_token(_band_token_from_band_config(artifact.band_config))
    return ""


def _required_columns_present(base_rows: pd.DataFrame) -> pd.Series:
    required_cols = [
        "dist_from_ema_pips",
        "atr14_pips",
        "envelope_upper",
        "envelope_lower",
        "session",
        "month",
    ]
    present = pd.Series(True, index=base_rows.index)
    for col in required_cols:
        if col not in base_rows.columns:
            present &= False
        else:
            present &= base_rows[col].notna()
    return present


def build_label_table_with_diagnostics(source_root: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build RV/TR labels and return per-run diagnostics for root-cause analysis."""
    run_dirs = _iter_run_dirs(Path(source_root).resolve())
    shortlist_band_tokens = {_normalize_band_token(x) for x in SHORTLIST_BANDS}
    repo_root = Path(__file__).resolve().parents[1]
    grouped_frames: list[pd.DataFrame] = []
    run_summaries: list[dict[str, Any]] = []

    for run_dir in run_dirs:
        band_config_path = run_dir / "effective_band_config.yaml"
        has_band_config = band_config_path.exists()
        band_config = _load_yaml(band_config_path)
        band_token = _normalize_band_token(_band_token_from_band_config(band_config))
        audit_source_name = _first_existing_name(run_dir, PRIMARY_AUDIT_NAMES)
        outcome_source_name = _first_existing_name(run_dir, PRIMARY_OUTCOME_NAMES)
        summary_row: dict[str, Any] = {
            "run_dir": str(run_dir),
            "source_run_dir": str(run_dir),
            "band_token": band_token,
            "is_shortlist_band": False,
            "audit_source_name": audit_source_name,
            "outcome_source_name": outcome_source_name,
            "rows_loaded": 0,
            "has_required_columns": False,
            "missing_required_columns": "",
            "candidate_family_values": "",
            "touch_side_values": "",
            "rows_after_family_filter": 0,
            "rows_after_required_key_filter": 0,
            "group_count": 0,
            "complete_pair_group_count": 0,
            "emitted_label_rows": 0,
            "exclude_reason": "",
        }
        reasons: list[str] = []
        if not has_band_config:
            reasons.append("missing_band_config")
        if band_token not in shortlist_band_tokens:
            reasons.append("not_shortlist_band")
        summary_row["is_shortlist_band"] = band_token in shortlist_band_tokens
        if reasons:
            summary_row["exclude_reason"] = ";".join(reasons)
            run_summaries.append(summary_row)
            continue

        rows = load_run_rows(run_dir)
        summary_row["rows_loaded"] = int(len(rows))
        if rows.empty:
            summary_row["exclude_reason"] = "zero_rows_loaded"
            run_summaries.append(summary_row)
            continue

        missing_required_cols = sorted(col for col in LABEL_BUILD_REQUIRED_COLUMNS if col not in rows.columns)
        summary_row["missing_required_columns"] = "|".join(missing_required_cols)
        summary_row["has_required_columns"] = len(missing_required_cols) == 0
        if not summary_row["has_required_columns"]:
            summary_row["exclude_reason"] = "missing_required_columns"
            run_summaries.append(summary_row)
            continue

        artifact = _load_run_artifact(run_dir, band_config=band_config)
        if artifact is None:
            summary_row["exclude_reason"] = "missing_audit_source"
            run_summaries.append(summary_row)
            continue

        work = artifact.rows.copy()
        work["candidate_family"] = work["candidate_family"].astype(str).str.lower()
        summary_row["candidate_family_values"] = _value_counts_str(work["candidate_family"])
        work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce")
        work["touch_side"] = work.get("touch_side", "").astype(str).str.lower()
        summary_row["touch_side_values"] = _value_counts_str(work["touch_side"])

        work = work.loc[work["candidate_family"].isin(["rev", "trend"])].copy()
        summary_row["rows_after_family_filter"] = int(len(work))
        if work.empty:
            summary_row["exclude_reason"] = "zero_rows_after_family_filter"
            run_summaries.append(summary_row)
            continue

        work = work.loc[work["timestamp"].notna() & work["touch_side"].ne("")].copy()
        summary_row["rows_after_required_key_filter"] = int(len(work))
        if work.empty:
            summary_row["exclude_reason"] = "zero_rows_after_required_key_filter"
            run_summaries.append(summary_row)
            continue

        work["source_run_dir"] = str(artifact.run_dir)
        work["source_artifact_path"] = str(artifact.source_path)
        work["band_token"] = band_token

        if "candidate_id" in work.columns:
            work["candidate_id"] = work["candidate_id"].astype(str)
        family_rank = np.where(work["candidate_family"].eq("rev"), 0, 1)
        work = work.assign(family_rank=family_rank)

        group_cols = ["source_run_dir", "band_token", "timestamp", "touch_side"]
        sort_cols = group_cols + ["family_rank"] + (["candidate_id"] if "candidate_id" in work.columns else [])
        work = work.sort_values(sort_cols, kind="mergesort")

        family_rows = work.drop_duplicates(group_cols + ["candidate_family"], keep="first").copy()
        base_rows = work.drop_duplicates(group_cols, keep="first").copy()
        summary_row["group_count"] = int(len(base_rows))
        if summary_row["group_count"] == 0:
            summary_row["exclude_reason"] = "zero_groups"
            run_summaries.append(summary_row)
            continue

        pair = (
            family_rows.pivot_table(index=group_cols, columns="candidate_family", values="pnl_pips", aggfunc="first")
            .rename(columns={"rev": "pnl_rv_pips", "trend": "pnl_tr_pips"})
            .reset_index()
        )
        counts = (
            work.groupby(group_cols, dropna=False)
            .agg(raw_row_count=("candidate_family", "size"), unique_family_count=("candidate_family", "nunique"))
            .reset_index()
        )
        summary_row["complete_pair_group_count"] = int(
            (counts["raw_row_count"].eq(2) & counts["unique_family_count"].eq(2)).sum()
        )
        if summary_row["complete_pair_group_count"] == 0:
            summary_row["exclude_reason"] = "zero_complete_pairs"
            run_summaries.append(summary_row)
            continue

        if "month" not in base_rows.columns:
            base_rows["month"] = base_rows["timestamp"].dt.strftime("%Y-%m")
        else:
            base_rows["month"] = base_rows["month"].astype(str)
            base_rows.loc[base_rows["month"].isin(["", "nan", "NaT", "None"]), "month"] = base_rows["timestamp"].dt.strftime("%Y-%m")
        if "session" not in base_rows.columns:
            base_rows["session"] = ""

        hard_gate = None
        if "hard_gate_passed" not in base_rows.columns:
            if "hard_gate_passed" in work.columns:
                hard_gate = (
                    work.assign(hard_gate_passed=work["hard_gate_passed"].fillna(False).astype(bool))
                    .groupby(group_cols, dropna=False)["hard_gate_passed"]
                    .max()
                    .reset_index()
                )
            else:
                hard_gate = base_rows.loc[:, group_cols].copy()
                hard_gate["hard_gate_passed"] = _required_columns_present(base_rows).to_numpy()

        features = _build_feature_frame(base_rows, _lookup_close_frame(load_ohlc_for_run(artifact.metadata, repo_root)))
        feature_extras = features.drop(columns=[col for col in features.columns if col in base_rows.columns and col not in group_cols], errors="ignore")

        out = (
            base_rows.merge(pair, on=group_cols, how="left")
            .merge(counts, on=group_cols, how="left")
            .merge(feature_extras, on=group_cols, how="left")
        )
        if hard_gate is not None:
            out = out.merge(hard_gate, on=group_cols, how="left")

        out["decision_group_id_v1"] = (
            sanitize_label(artifact.run_dir.name)
            + "||"
            + out["band_token"].astype(str)
            + "||"
            + out["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
            + "||"
            + out["touch_side"].astype(str)
        )
        out["group_status"] = np.select(
            [
                out["raw_row_count"].eq(2) & out["unique_family_count"].eq(2),
                out["unique_family_count"].eq(2) & ~out["raw_row_count"].eq(2),
                out["unique_family_count"].eq(1),
            ],
            ["complete_unique_pair", "duplicate_or_ambiguous_pair", "incomplete_pair"],
            default="incomplete_pair",
        )

        out["pnl_rv_pips"] = pd.to_numeric(out["pnl_rv_pips"], errors="coerce")
        out["pnl_tr_pips"] = pd.to_numeric(out["pnl_tr_pips"], errors="coerce")
        out["label_gap_rv_minus_tr_pips"] = out["pnl_rv_pips"] - out["pnl_tr_pips"]
        out["label_rvtr_v1"] = np.select(
            [
                out["label_gap_rv_minus_tr_pips"] >= LABEL_GAP_THRESHOLD_PIPS,
                out["label_gap_rv_minus_tr_pips"] <= -LABEL_GAP_THRESHOLD_PIPS,
            ],
            ["rv", "tr"],
            default="ambiguous",
        )
        out["band_model"] = str(artifact.band_config.get("band_model", "")).strip().lower()
        out["band_model_family"] = str(artifact.band_config.get("band_model_family", artifact.band_config.get("band_model", ""))).strip().lower()
        grouped_frames.append(out)
        summary_row["emitted_label_rows"] = int(len(out))
        summary_row["exclude_reason"] = "ok"
        run_summaries.append(summary_row)

    label_table = pd.DataFrame()
    if grouped_frames:
        label_table = pd.concat(grouped_frames, ignore_index=True)
        label_table = label_table.sort_values(["band_token", "timestamp", "touch_side"], kind="mergesort").reset_index(drop=True)
    run_summary_df = pd.DataFrame(run_summaries)
    if run_summary_df.empty:
        run_summary_df = pd.DataFrame(
            columns=[
                "run_dir",
                "source_run_dir",
                "band_token",
                "is_shortlist_band",
                "audit_source_name",
                "outcome_source_name",
                "rows_loaded",
                "has_required_columns",
                "missing_required_columns",
                "candidate_family_values",
                "touch_side_values",
                "rows_after_family_filter",
                "rows_after_required_key_filter",
                "group_count",
                "complete_pair_group_count",
                "emitted_label_rows",
                "exclude_reason",
            ]
        )
    exclude_counts = run_summary_df["exclude_reason"].fillna("unknown").astype(str).value_counts().to_dict()
    diagnostics = {
        "discovered_run_count": int(len(run_dirs)),
        "shortlist_matched_run_count": int(run_summary_df["is_shortlist_band"].fillna(False).sum()) if not run_summary_df.empty else 0,
        "skipped_not_shortlist_count": int(run_summary_df["exclude_reason"].astype(str).str.contains(r"(^|;)not_shortlist_band($|;)").sum()) if not run_summary_df.empty else 0,
        "loaded_run_count": int((run_summary_df["rows_loaded"] > 0).sum()) if not run_summary_df.empty else 0,
        "runs_with_rows_count": int((run_summary_df["rows_after_required_key_filter"] > 0).sum()) if not run_summary_df.empty else 0,
        "runs_with_complete_pairs_count": int((run_summary_df["complete_pair_group_count"] > 0).sum()) if not run_summary_df.empty else 0,
        "total_rows_loaded": int(run_summary_df["rows_loaded"].sum()) if not run_summary_df.empty else 0,
        "total_groups": int(run_summary_df["group_count"].sum()) if not run_summary_df.empty else 0,
        "total_complete_pair_groups": int(run_summary_df["complete_pair_group_count"].sum()) if not run_summary_df.empty else 0,
        "total_emitted_label_rows": int(run_summary_df["emitted_label_rows"].sum()) if not run_summary_df.empty else 0,
        "exclude_reason_counts": {str(k): int(v) for k, v in exclude_counts.items()},
        "audit_source_counts": run_summary_df["audit_source_name"].astype(str).value_counts().to_dict() if not run_summary_df.empty else {},
        "band_token_counts": run_summary_df["band_token"].astype(str).value_counts().to_dict() if not run_summary_df.empty else {},
        "shortlist_bands": sorted(SHORTLIST_BANDS),
    }
    return label_table, run_summary_df, diagnostics


def build_label_table(source_root: str | Path) -> pd.DataFrame:
    """Build one-row-per-decision-group RV/TR labels for shortlisted bands."""
    label_table, _, _ = build_label_table_with_diagnostics(source_root)
    return label_table


def _split_name(ts: pd.Timestamp) -> str:
    if TRAIN_START <= ts <= TRAIN_END:
        return "train"
    if VALID_START <= ts <= VALID_END:
        return "valid"
    if HOLDOUT_START <= ts <= HOLDOUT_END:
        return "holdout"
    return "other"


def add_split_column(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if work.empty:
        work["split"] = pd.Series(dtype="object")
        return work
    work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce")
    work["split"] = work["timestamp"].map(lambda v: _split_name(v) if pd.notna(v) else "other")
    return work


def build_distribution_table(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        cols = group_cols + ["row_count", "rv_count", "tr_count", "ambiguous_count", "rv_share", "tr_share"]
        return pd.DataFrame(columns=cols)
    if not group_cols:
        row = {
            "row_count": int(len(df)),
            "rv_count": int((df["label_rvtr_v1"] == "rv").sum()),
            "tr_count": int((df["label_rvtr_v1"] == "tr").sum()),
            "ambiguous_count": int((df["label_rvtr_v1"] == "ambiguous").sum()),
        }
        row["rv_share"] = row["rv_count"] / row["row_count"] if row["row_count"] else 0.0
        row["tr_share"] = row["tr_count"] / row["row_count"] if row["row_count"] else 0.0
        return pd.DataFrame([row])

    grouped = df.groupby(group_cols, dropna=False)
    out = grouped.agg(
        row_count=("label_rvtr_v1", "size"),
        rv_count=("label_rvtr_v1", lambda s: int((s == "rv").sum())),
        tr_count=("label_rvtr_v1", lambda s: int((s == "tr").sum())),
        ambiguous_count=("label_rvtr_v1", lambda s: int((s == "ambiguous").sum())),
    ).reset_index()
    out["rv_share"] = np.where(out["row_count"] > 0, out["rv_count"] / out["row_count"], 0.0)
    out["tr_share"] = np.where(out["row_count"] > 0, out["tr_count"] / out["row_count"], 0.0)
    return out


def prepare_trainable_label_table(df: pd.DataFrame) -> pd.DataFrame:
    work = add_split_column(df)
    if work.empty:
        return work
    required_cols = [
        "decision_group_id_v1",
        "band_token",
        "timestamp",
        "touch_side",
        "session",
        "month",
        "group_status",
        "hard_gate_passed",
        "label_rvtr_v1",
        "pnl_rv_pips",
        "pnl_tr_pips",
        "label_gap_rv_minus_tr_pips",
    ] + feature_columns()
    numeric_cols = [
        "pnl_rv_pips",
        "pnl_tr_pips",
        "label_gap_rv_minus_tr_pips",
        "dist_from_ema_norm_by_band",
        "dist_from_ema_norm_by_atr",
        "band_width_norm_vs_atr",
        "pre10_change_pips",
        "pre30_change_pips",
        "pre60_change_pips",
        "net10_change_pips",
        "m5_slope",
        "m30_slope",
        "h1_slope",
        "rsi14",
        "macd_hist",
        "bb_width_ratio_to_close",
        "atr_ratio_5_14",
        "rv_band_score",
        "tr_band_score",
        "rv_timing_score",
        "tr_timing_score",
        "rv_momo_score",
        "tr_momo_score",
        "rv_stretch_score",
        "tr_stretch_score",
        "rv_regime_score",
        "tr_regime_score",
        "rv_exit_proxy_score",
        "tr_exit_proxy_score",
    ]
    for col in numeric_cols:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    if "session" in work.columns:
        work["session"] = work["session"].astype(str)
    for col in required_cols:
        if col not in work.columns:
            work[col] = pd.NA
    work = work.dropna(subset=required_cols).copy()
    return work


def feature_columns() -> list[str]:
    return [
        "rv_band_score",
        "tr_band_score",
        "rv_timing_score",
        "tr_timing_score",
        "rv_momo_score",
        "tr_momo_score",
        "rv_stretch_score",
        "tr_stretch_score",
        "rv_regime_score",
        "tr_regime_score",
        "rv_exit_proxy_score",
        "tr_exit_proxy_score",
        "dist_from_ema_norm_by_band",
        "dist_from_ema_norm_by_atr",
        "band_width_norm_vs_atr",
        "pre10_change_pips",
        "pre30_change_pips",
        "pre60_change_pips",
        "net10_change_pips",
        "m5_slope",
        "m30_slope",
        "h1_slope",
        "rsi14",
        "macd_hist",
        "bb_width_ratio_to_close",
        "atr_ratio_5_14",
    ]


def one_hot_session_columns(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "session" not in work.columns:
        return work
    session = work["session"].astype(str).str.lower()
    for value in sorted(session.dropna().unique()):
        safe = sanitize_label(value).lower()
        work[f"session__{safe}"] = (session == value).astype(float)
    return work


__all__ = [
    "CONTROL_BANDS",
    "COMPARISON_BANDS",
    "HOLDOUT_END",
    "HOLDOUT_START",
    "LABEL_GAP_THRESHOLD_PIPS",
    "PRIMARY_AUDIT_NAMES",
    "PRIMARY_OUTCOME_NAMES",
    "PIP_SIZE",
    "SHORTLIST_BANDS",
    "TRAIN_END",
    "TRAIN_START",
    "VALID_END",
    "VALID_START",
    "RunArtifact",
    "add_split_column",
    "build_distribution_table",
    "build_label_table",
    "build_label_table_with_diagnostics",
    "feature_columns",
    "load_ohlc_for_run",
    "load_run_artifacts",
    "load_run_rows",
    "one_hot_session_columns",
    "prepare_trainable_label_table",
    "sanitize_label",
]
