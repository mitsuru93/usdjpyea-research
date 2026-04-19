"""Shared helpers for the RV/TR ML research pipeline.

This module stays research-side only. It provides deterministic data loading,
label-table construction, feature derivation, and small utility helpers that
the CLI tools reuse.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

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
CONTROL_BANDS = {
    "bin_env_v1",
}


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
    for candidate_path in source_root.rglob("candidates_decision_policy_audit.csv"):
        run_dirs.add(candidate_path.parent)
    for candidate_path in source_root.rglob("candidates_aggregate.csv.gz"):
        run_dirs.add(candidate_path.parent)
    for candidate_path in source_root.rglob("candidates_policy_audit.csv"):
        run_dirs.add(candidate_path.parent)
    for candidate_path in source_root.rglob("candidates.csv"):
        run_dirs.add(candidate_path.parent)
    return sorted(run_dirs)


def _load_run_artifact(run_dir: Path) -> RunArtifact | None:
    audit_path = _first_existing(run_dir, ["candidates_decision_policy_audit.csv", "candidates_policy_audit.csv"])
    pnl_path = _first_existing(run_dir, ["candidates_aggregate.csv.gz", "candidates.csv"])
    source_path = audit_path or pnl_path
    if source_path is None:
        return None

    rows = load_run_rows(run_dir)
    metadata_path = _resolve_metadata_path(run_dir)
    band_config_path = run_dir / "effective_band_config.yaml"
    metadata = _load_yaml(metadata_path)
    band_config = _load_yaml(band_config_path)
    return RunArtifact(
        run_dir=run_dir,
        source_path=source_path,
        metadata_path=metadata_path if metadata_path is not None else None,
        band_config_path=band_config_path if band_config_path.exists() else None,
        rows=rows,
        metadata=metadata,
        band_config=band_config,
    )


def _first_existing(run_dir: Path, names: list[str]) -> Path | None:
    for name in names:
        path = run_dir / name
        if path.exists():
            return path
    return None


def _merge_outcome_table(audit_df: pd.DataFrame, outcome_df: pd.DataFrame) -> pd.DataFrame:
    if audit_df.empty or outcome_df.empty:
        return audit_df.copy()
    if "pnl_pips" in audit_df.columns and audit_df["pnl_pips"].notna().any():
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
            return merged

    if len(audit_df) == len(outcome_df) and "pnl_pips" in outcome_df.columns:
        merged = audit_df.copy().reset_index(drop=True)
        merged["pnl_pips"] = pd.to_numeric(outcome_df["pnl_pips"], errors="coerce").reset_index(drop=True)
        return merged

    return audit_df.copy()


def load_run_rows(run_dir: str | Path) -> pd.DataFrame:
    run_dir = Path(run_dir)
    audit_path = _first_existing(run_dir, ["candidates_decision_policy_audit.csv", "candidates_policy_audit.csv"])
    pnl_path = _first_existing(run_dir, ["candidates_aggregate.csv.gz", "candidates.csv"])
    if audit_path is not None and pnl_path is not None:
        audit_df = pd.read_csv(audit_path)
        outcome_df = pd.read_csv(pnl_path)
        return _merge_outcome_table(audit_df, outcome_df)
    if audit_path is not None:
        return pd.read_csv(audit_path)
    if pnl_path is not None:
        return pd.read_csv(pnl_path)
    return pd.DataFrame()


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


def _extract_band_token(row: pd.Series, band_config: dict[str, Any]) -> str:
    for col in ["band_token", "band_label", "band_name"]:
        if col in row.index and str(row.get(col, "")).strip():
            return _normalize_band_token(row.get(col, ""))
    if band_config:
        return _normalize_band_token(_band_token_from_band_config(band_config))
    return ""


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


def _lookup_close_series(ohlc_df: pd.DataFrame) -> pd.Series:
    close = pd.to_numeric(ohlc_df["close"], errors="coerce")
    close.index = pd.to_datetime(ohlc_df["datetime"], errors="coerce")
    return close.sort_index()


def _slope_from_close_series(close_series: pd.Series, ts: pd.Timestamp, window: int) -> float:
    if window <= 0:
        return 0.0
    try:
        loc = close_series.index.get_loc(ts)
    except KeyError:
        return 0.0
    if isinstance(loc, slice):
        loc = loc.stop - 1
    if loc < window:
        return 0.0
    current = float(close_series.iloc[loc])
    past = float(close_series.iloc[loc - window])
    return (current - past) / float(window) / PIP_SIZE


def _build_family_block_scores(base: dict[str, float]) -> dict[str, float]:
    band = base["dist_from_ema_norm_by_band"]
    timing = base["session_core"]
    momo = base["directional_momo_core"]
    stretch = base["dist_from_ema_norm_by_atr"]
    regime = base["regime_core"]
    exit_proxy = base["exit_proxy_core"]

    return {
        "rv_band_score": band,
        "tr_band_score": band,
        "rv_timing_score": -timing,
        "tr_timing_score": timing,
        "rv_momo_score": -momo,
        "tr_momo_score": momo,
        "rv_stretch_score": stretch,
        "tr_stretch_score": stretch,
        "rv_regime_score": -regime,
        "tr_regime_score": regime,
        "rv_exit_proxy_score": -exit_proxy,
        "tr_exit_proxy_score": exit_proxy,
    }


def _feature_row_from_candidate(row: pd.Series, close_series: pd.Series) -> dict[str, Any]:
    ts = _safe_ts(row.get("timestamp"))
    dist_from_ema_pips = _scalar_float(row.get("dist_from_ema_pips"))
    atr14_pips = _scalar_float(row.get("atr14_pips"))
    atr14_safe = atr14_pips if abs(atr14_pips) > 1e-9 else 1.0
    envelope_upper = row.get("envelope_upper", row.get("upper_env", 0.0))
    envelope_lower = row.get("envelope_lower", row.get("lower_env", 0.0))
    band_width_pips = float((float(envelope_upper) - float(envelope_lower)) / PIP_SIZE)
    band_half_width_pips = band_width_pips / 2.0 if abs(band_width_pips) > 1e-9 else 1.0
    pre10 = _scalar_float(row.get("pre10_change_pips"))
    pre30 = _scalar_float(row.get("pre30_change_pips"))
    pre60 = _scalar_float(row.get("pre60_change_pips"))
    net10 = _scalar_float(row.get("net10_change_pips"))
    rsi14 = _scalar_float(row.get("rsi14"), 50.0)
    macd_hist = _scalar_float(row.get("macd_hist"))
    bb_width_ratio_to_close = _scalar_float(row.get("bb_width_ratio_to_close"))
    atr_ratio_5_14 = _scalar_float(row.get("atr_ratio_5_14"), 1.0)
    session = str(row.get("session", "")).strip()
    direction = str(row.get("direction", "")).strip().lower()
    direction_sign = 1.0 if direction == "buy" else -1.0 if direction == "sell" else 0.0

    m5_slope = _slope_from_close_series(close_series, ts, 5)
    m30_slope = _slope_from_close_series(close_series, ts, 30)
    h1_slope = _slope_from_close_series(close_series, ts, 60)

    dist_from_ema_norm_by_band = dist_from_ema_pips / band_half_width_pips
    dist_from_ema_norm_by_atr = dist_from_ema_pips / atr14_safe
    band_width_norm_vs_atr = band_width_pips / atr14_safe
    directional_momo_core = direction_sign * (0.6 * pre10 + 0.3 * pre30 + 0.1 * net10) / 10.0
    regime_core = ((atr_ratio_5_14 - 1.0) * 0.75) + (0.25 * bb_width_ratio_to_close * 100.0)
    exit_proxy_core = (0.5 * m5_slope) + (0.3 * m30_slope) + (0.2 * h1_slope) + (0.1 * macd_hist * 100.0)

    base = {
        "dist_from_ema_norm_by_band": dist_from_ema_norm_by_band,
        "dist_from_ema_norm_by_atr": dist_from_ema_norm_by_atr,
        "band_width_norm_vs_atr": band_width_norm_vs_atr,
        "pre10_change_pips": pre10,
        "pre30_change_pips": pre30,
        "pre60_change_pips": pre60,
        "net10_change_pips": net10,
        "m5_slope": m5_slope,
        "m30_slope": m30_slope,
        "h1_slope": h1_slope,
        "rsi14": rsi14,
        "macd_hist": macd_hist,
        "bb_width_ratio_to_close": bb_width_ratio_to_close,
        "atr_ratio_5_14": atr_ratio_5_14,
        "session": session,
        "session_core": _session_core(session),
        "directional_momo_core": directional_momo_core,
        "regime_core": regime_core,
        "exit_proxy_core": exit_proxy_core,
    }
    base.update(_build_family_block_scores(base))
    return base


def load_run_artifacts(source_root: str | Path) -> list[RunArtifact]:
    root = Path(source_root).resolve()
    artifacts: list[RunArtifact] = []
    for run_dir in _iter_run_dirs(root):
        artifact = _load_run_artifact(run_dir)
        if artifact is not None:
            artifacts.append(artifact)
    return artifacts


def _band_is_shortlisted(band_token: str, shortlist_bands: set[str]) -> bool:
    return _normalize_band_token(band_token) in {_normalize_band_token(x) for x in shortlist_bands}


def build_label_table(source_root: str | Path) -> pd.DataFrame:
    artifacts = load_run_artifacts(source_root)
    if not artifacts:
        return pd.DataFrame()

    grouped_rows: list[dict[str, Any]] = []
    shortlist_band_tokens = {_normalize_band_token(x) for x in SHORTLIST_BANDS}
    repo_root = Path(__file__).resolve().parents[1]

    for artifact in artifacts:
        band_token = _extract_band_token(artifact.rows.iloc[0] if not artifact.rows.empty else pd.Series(dtype=object), artifact.band_config)
        if band_token not in shortlist_band_tokens:
            continue

        ohlc_df = load_ohlc_for_run(artifact.metadata, repo_root)
        close_series = _lookup_close_series(ohlc_df) if ohlc_df is not None else None
        work = artifact.rows.copy()

        if "candidate_family" not in work.columns:
            continue
        if "timestamp" not in work.columns:
            continue

        for _, group in work.groupby(["timestamp", "touch_side"], dropna=False):
            family_map: dict[str, pd.Series] = {}
            for _, row in group.iterrows():
                family = str(row.get("candidate_family", "")).strip().lower()
                if family in {"rev", "trend"} and family not in family_map:
                    family_map[family] = row
            if not family_map:
                continue

            base_row = next(iter(family_map.values()))
            timestamp = _safe_ts(base_row.get("timestamp"))
            touch_side = str(base_row.get("touch_side", "")).strip().lower()
            decision_group_id_v1 = "||".join([sanitize_label(artifact.run_dir.name), band_token, timestamp.isoformat(), touch_side])

            pnl_rv = pd.to_numeric(family_map["rev"].get("pnl_pips"), errors="coerce") if "rev" in family_map else pd.NA
            pnl_tr = pd.to_numeric(family_map["trend"].get("pnl_pips"), errors="coerce") if "trend" in family_map else pd.NA
            if pd.isna(pnl_rv) or pd.isna(pnl_tr):
                continue
            pnl_rv = float(pnl_rv)
            pnl_tr = float(pnl_tr)

            label_gap = float(pnl_rv - pnl_tr)
            if label_gap >= LABEL_GAP_THRESHOLD_PIPS:
                label = "rv"
            elif label_gap <= -LABEL_GAP_THRESHOLD_PIPS:
                label = "tr"
            else:
                label = "ambiguous"

            required_cols = [
                "dist_from_ema_pips",
                "atr14_pips",
                "envelope_upper",
                "envelope_lower",
                "session",
                "month",
            ]
            missing_required = [col for col in required_cols if col not in base_row.index or pd.isna(base_row.get(col))]
            if "hard_gate_passed" in base_row.index and not pd.isna(base_row.get("hard_gate_passed")):
                hard_gate_passed = bool(base_row.get("hard_gate_passed"))
            else:
                hard_gate_passed = len(missing_required) == 0
            group_status = "complete_unique_pair" if set(family_map.keys()) == {"rev", "trend"} else "incomplete_pair"
            if len(group) != len(family_map):
                group_status = "duplicate_or_ambiguous_pair" if group_status == "complete_unique_pair" else group_status

            feature_base = _feature_row_from_candidate(base_row, close_series) if close_series is not None else {
                "dist_from_ema_norm_by_band": 0.0,
                "dist_from_ema_norm_by_atr": 0.0,
                "band_width_norm_vs_atr": 0.0,
                "pre10_change_pips": _scalar_float(base_row.get("pre10_change_pips")),
                "pre30_change_pips": _scalar_float(base_row.get("pre30_change_pips")),
                "pre60_change_pips": _scalar_float(base_row.get("pre60_change_pips")),
                "net10_change_pips": _scalar_float(base_row.get("net10_change_pips")),
                "m5_slope": 0.0,
                "m30_slope": 0.0,
                "h1_slope": 0.0,
                "rsi14": _scalar_float(base_row.get("rsi14"), 50.0),
                "macd_hist": _scalar_float(base_row.get("macd_hist")),
                "bb_width_ratio_to_close": _scalar_float(base_row.get("bb_width_ratio_to_close")),
                "atr_ratio_5_14": _scalar_float(base_row.get("atr_ratio_5_14"), 1.0),
                "session": str(base_row.get("session", "")),
                "session_core": _session_core(str(base_row.get("session", ""))),
                "directional_momo_core": 0.0,
                "regime_core": 0.0,
                "exit_proxy_core": 0.0,
                "rv_band_score": 0.0,
                "tr_band_score": 0.0,
                "rv_timing_score": 0.0,
                "tr_timing_score": 0.0,
                "rv_momo_score": 0.0,
                "tr_momo_score": 0.0,
                "rv_stretch_score": 0.0,
                "tr_stretch_score": 0.0,
                "rv_regime_score": 0.0,
                "tr_regime_score": 0.0,
                "rv_exit_proxy_score": 0.0,
                "tr_exit_proxy_score": 0.0,
            }

            shared = {
                "decision_group_id_v1": decision_group_id_v1,
                "band_token": band_token,
                "band_model": str(artifact.band_config.get("band_model", "")).strip().lower(),
                "band_model_family": str(artifact.band_config.get("band_model_family", artifact.band_config.get("band_model", ""))).strip().lower(),
                "source_run_dir": str(artifact.run_dir),
                "source_artifact_path": str(artifact.source_path),
                "timestamp": timestamp.isoformat(),
                "touch_side": touch_side,
                "session": str(base_row.get("session", "")),
                "month": str(base_row.get("month", "")),
                "hard_gate_passed": bool(hard_gate_passed),
                "group_status": group_status,
                "label_gap_rv_minus_tr_pips": label_gap,
                "label_rvtr_v1": label,
                "pnl_rv_pips": pnl_rv,
                "pnl_tr_pips": pnl_tr,
            }

            row_payload = dict(shared)
            row_payload.update(feature_base)
            grouped_rows.append(row_payload)

    label_table = pd.DataFrame(grouped_rows)
    if label_table.empty:
        return label_table

    label_table = label_table.sort_values(["band_token", "timestamp", "touch_side"], kind="mergesort").reset_index(drop=True)
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
        return pd.DataFrame(columns=group_cols + ["row_count", "rv_count", "tr_count", "ambiguous_count"])
    grouped = df.groupby(group_cols, dropna=False) if group_cols else [("overall", df)]
    rows: list[dict[str, Any]] = []
    for key, part in grouped:
        row: dict[str, Any] = {}
        if group_cols:
            if len(group_cols) == 1:
                row[group_cols[0]] = key
            else:
                row.update(dict(zip(group_cols, key)))
        row["row_count"] = int(len(part))
        row["rv_count"] = int((part["label_rvtr_v1"] == "rv").sum())
        row["tr_count"] = int((part["label_rvtr_v1"] == "tr").sum())
        row["ambiguous_count"] = int((part["label_rvtr_v1"] == "ambiguous").sum())
        row["rv_share"] = (row["rv_count"] / row["row_count"]) if row["row_count"] else 0.0
        row["tr_share"] = (row["tr_count"] / row["row_count"]) if row["row_count"] else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


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
