#!/usr/bin/env python3
"""Aggregate shard outputs into deterministic batch-level review artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.io.dataset_resolver import resolve_dataset_to_local_csv
from research.orchestration.path_utils import sanitize_label


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping YAML at {path}")
    return data


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate completed batch shard outputs into review artifacts.")
    p.add_argument("--batch-manifest", required=True, help="Path to batch manifest YAML from expand_batch.py")
    p.add_argument("--review-issue-number", default=None, help="Optional override issue number")
    p.add_argument(
        "--artifact-staging-root",
        default=None,
        help="Optional artifact staging root used in cloud aggregate jobs to resolve shard outputs.",
    )
    return p.parse_args()


def _safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _pnl_stats(summary_df: pd.DataFrame, prefix: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        f"profitable_{prefix}_count": 0,
        f"losing_{prefix}_count": 0,
        f"worst_{prefix}_pnl_pips": 0.0,
        f"best_{prefix}_pnl_pips": 0.0,
    }
    if summary_df.empty or "total_pnl_pips" not in summary_df.columns:
        return result

    pnl = pd.to_numeric(summary_df["total_pnl_pips"], errors="coerce").dropna()
    if pnl.empty:
        return result

    result[f"profitable_{prefix}_count"] = int((pnl > 0.0).sum())
    result[f"losing_{prefix}_count"] = int((pnl < 0.0).sum())
    result[f"worst_{prefix}_pnl_pips"] = float(pnl.min())
    result[f"best_{prefix}_pnl_pips"] = float(pnl.max())
    return result


def _top_session_share(summary_df: pd.DataFrame) -> float:
    if summary_df.empty or "trade_count" not in summary_df.columns:
        return 0.0
    trade_counts = pd.to_numeric(summary_df["trade_count"], errors="coerce").fillna(0.0)
    total = float(trade_counts.sum())
    if total <= 0.0:
        return 0.0
    return float(trade_counts.max() / total)


def _load_dataset_path(manifest: dict[str, Any], manifest_path: Path) -> Path | None:
    registry_path = Path(str(manifest.get("dataset_registry", "")))
    if not registry_path.is_absolute():
        registry_path = (REPO_ROOT / registry_path).resolve()
    if not registry_path.exists():
        return None

    reg = _load_yaml(registry_path)
    datasets = reg.get("datasets", {}) if isinstance(reg, dict) else {}
    entry = datasets.get(str(manifest.get("dataset_id", ""))) if isinstance(datasets, dict) else None
    if not isinstance(entry, dict):
        return None

    dataset_id = str(manifest.get("dataset_id", "")).strip()
    if not dataset_id:
        return None
    cache_dir = Path(str(manifest.get("output_root", REPO_ROOT / "research/reports/tmp"))).resolve() / "dataset_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return resolve_dataset_to_local_csv(
        dataset_id=dataset_id,
        entry=entry,
        repo_root=REPO_ROOT,
        cache_dir=cache_dir,
    )


def _spread_audit(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    dataset_path = _load_dataset_path(manifest, manifest_path)
    result: dict[str, Any] = {
        "spread_mode": manifest.get("spread_mode"),
        "dataset_path": str(dataset_path) if dataset_path else None,
        "spread_column_present": False,
        "headers": [],
        "stats": {},
    }
    if dataset_path is None or not dataset_path.exists():
        result["warning"] = "dataset_path_unresolved_or_missing"
        return result

    sample = pd.read_csv(dataset_path, nrows=5000)
    result["headers"] = [str(c) for c in sample.columns]
    spread_col = None
    for col in sample.columns:
        if str(col).strip().lower() == "spread":
            spread_col = col
            break
    if spread_col is None:
        return result

    result["spread_column_present"] = True
    spread_series = pd.to_numeric(sample[spread_col], errors="coerce")
    non_null = spread_series.dropna()
    if non_null.empty:
        result["stats"] = {"non_null_count": 0}
        return result

    result["stats"] = {
        "non_null_count": int(non_null.shape[0]),
        "zero_count": int((non_null == 0).sum()),
        "min": float(non_null.min()),
        "p50": float(non_null.quantile(0.50)),
        "p90": float(non_null.quantile(0.90)),
        "max": float(non_null.max()),
    }
    return result


def _parse_hms_to_seconds(value: str) -> int | None:
    text = str(value).strip()
    parts = text.split(":")
    if len(parts) != 3:
        return None
    try:
        hh, mm, ss = [int(p) for p in parts]
    except ValueError:
        return None
    if hh < 0 or hh > 23 or mm < 0 or mm > 59 or ss < 0 or ss > 59:
        return None
    return hh * 3600 + mm * 60 + ss


def _in_blackout_jst(timestamp: pd.Series, windows: list[dict[str, Any]]) -> pd.Series:
    if timestamp.empty:
        return pd.Series(False, index=timestamp.index)

    ts = pd.to_datetime(timestamp, errors="coerce", utc=True)
    ts_jst = ts.dt.tz_convert("Asia/Tokyo")
    mask = pd.Series(False, index=timestamp.index)
    seconds_of_day = ts_jst.dt.hour * 3600 + ts_jst.dt.minute * 60 + ts_jst.dt.second
    for window in windows:
        start_sec = _parse_hms_to_seconds(str(window.get("start_hhmmss", "")))
        end_sec = _parse_hms_to_seconds(str(window.get("end_hhmmss", "")))
        if start_sec is None or end_sec is None:
            continue
        if start_sec == end_sec:
            window_mask = pd.Series(True, index=timestamp.index)
        elif start_sec < end_sec:
            window_mask = (seconds_of_day >= start_sec) & (seconds_of_day < end_sec)
        else:
            # midnight crossing window, e.g. 23:55:00 -> 00:10:00
            window_mask = (seconds_of_day >= start_sec) | (seconds_of_day < end_sec)
        mask = mask | window_mask
    return mask.fillna(False)


def _resolve_study_output(shard: dict[str, Any], artifact_staging_root: Path | None) -> Path:
    abs_output = Path(str(shard.get("study_output", ""))).resolve()
    if abs_output.exists():
        return abs_output
    if artifact_staging_root is None:
        return abs_output
    runtime_rel = str(shard.get("shard_runtime_relpath", "")).strip()
    if runtime_rel:
        staged = (artifact_staging_root / runtime_rel).resolve()
        if staged.exists():
            return staged
    output_rel = str(shard.get("shard_output_relpath", "")).strip()
    if output_rel:
        staged = (artifact_staging_root / output_rel).resolve()
        if staged.exists():
            return staged
    return abs_output


def _resolve_run_output_dir(*, study_output: Path, run_record: dict[str, Any]) -> Path | None:
    label = str(run_record.get("label", ""))
    safe_label = sanitize_label(label)
    staged_run_dir = (study_output / "runs" / safe_label).resolve()
    if staged_run_dir.exists():
        return staged_run_dir

    legacy_run_dir_raw = str(run_record.get("run_dir", "")).strip()
    if not legacy_run_dir_raw:
        return None
    legacy_run_dir = Path(legacy_run_dir_raw).resolve()
    if legacy_run_dir.exists():
        return legacy_run_dir
    return None


def _find_variant_by_band(
    candidates: list[dict[str, Any]],
    *,
    band_model: str,
    band_value: float,
    tolerance: float = 1e-9,
) -> dict[str, Any] | None:
    for item in candidates:
        if str(item.get("band_model", "")).strip().lower() != band_model:
            continue
        raw = item.get("band_value")
        if raw is None:
            continue
        if abs(float(raw) - band_value) <= tolerance:
            return item
    return None


def _build_variant_compare_rows(variant_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(variant_rows) < 2:
        return []
    preferred_pairs = [
        (("percent", 0.05), ("fixed_pips", 11.0)),
        (("percent", 0.05), ("atr", 1.2)),
    ]
    selected: tuple[dict[str, Any], dict[str, Any]] | None = None
    for (model_a, value_a), (model_b, value_b) in preferred_pairs:
        a = _find_variant_by_band(variant_rows, band_model=model_a, band_value=value_a)
        b = _find_variant_by_band(variant_rows, band_model=model_b, band_value=value_b)
        if a is not None and b is not None:
            selected = (a, b)
            break
    if selected is None:
        sorted_rows = sorted(variant_rows, key=lambda x: str(x.get("variant_label", "")))
        for idx, a in enumerate(sorted_rows):
            band_a = (str(a.get("band_model", "")), a.get("band_value"))
            for b in sorted_rows[idx + 1 :]:
                band_b = (str(b.get("band_model", "")), b.get("band_value"))
                if band_a != band_b:
                    selected = (a, b)
                    break
            if selected is not None:
                break
        if selected is None:
            selected = (sorted_rows[0], sorted_rows[1])

    a, b = selected
    ts_a = set(a.get("candidate_timestamps", set()))
    ts_b = set(b.get("candidate_timestamps", set()))
    overlap = len(ts_a & ts_b)
    return [
        {
            "variant_a": a.get("variant_label", ""),
            "variant_b": b.get("variant_label", ""),
            "candidate_count_a": int(a.get("candidate_count", 0)),
            "candidate_count_b": int(b.get("candidate_count", 0)),
            "candidate_timestamp_overlap_count": overlap,
            "candidate_timestamp_only_a": len(ts_a - ts_b),
            "candidate_timestamp_only_b": len(ts_b - ts_a),
        }
    ]


def _build_policy_compare_rows(variant_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    policy_rows = [row for row in variant_rows if str(row.get("decision_policy", "")).strip()]
    if len(policy_rows) < 2:
        return []

    selected: tuple[dict[str, Any], dict[str, Any]] | None = None
    by_anchor: dict[tuple[str, Any, str], list[dict[str, Any]]] = {}
    for row in policy_rows:
        key = (str(row.get("band_model", "")), row.get("band_value"), str(row.get("score_bundle", "")))
        by_anchor.setdefault(key, []).append(row)
    for rows in by_anchor.values():
        families = {str(row.get("decision_policy", "")) for row in rows}
        if len(rows) >= 2 and len(families) >= 2:
            sorted_rows = sorted(rows, key=lambda x: str(x.get("decision_policy", "")))
            selected = (sorted_rows[0], sorted_rows[1])
            break
    if selected is None:
        sorted_rows = sorted(policy_rows, key=lambda x: str(x.get("variant_label", "")))
        selected = (sorted_rows[0], sorted_rows[1])

    a, b = selected
    ts_a = set(a.get("candidate_timestamps", set()))
    ts_b = set(b.get("candidate_timestamps", set()))
    return [
        {
            "variant_a": a.get("variant_label", ""),
            "variant_b": b.get("variant_label", ""),
            "decision_policy_a": a.get("decision_policy", ""),
            "decision_policy_b": b.get("decision_policy", ""),
            "score_bundle_a": a.get("score_bundle", ""),
            "score_bundle_b": b.get("score_bundle", ""),
            "candidate_count_a": int(a.get("candidate_count", 0)),
            "candidate_count_b": int(b.get("candidate_count", 0)),
            "rv_selected_count_a": int(a.get("rv_selected_count", 0)),
            "rv_selected_count_b": int(b.get("rv_selected_count", 0)),
            "tr_selected_count_a": int(a.get("tr_selected_count", 0)),
            "tr_selected_count_b": int(b.get("tr_selected_count", 0)),
            "no_entry_group_count_a": int(a.get("no_entry_group_count", 0)),
            "no_entry_group_count_b": int(b.get("no_entry_group_count", 0)),
            "candidate_timestamp_overlap_count": len(ts_a & ts_b),
            "candidate_timestamp_only_a": len(ts_a - ts_b),
            "candidate_timestamp_only_b": len(ts_b - ts_a),
        }
    ]


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.batch_manifest).resolve()
    manifest = _load_yaml(manifest_path)
    artifact_staging_root = Path(args.artifact_staging_root).resolve() if args.artifact_staging_root else None
    output_root = Path(str(manifest["output_root"])).resolve()
    batch_output = output_root
    batch_output.mkdir(parents=True, exist_ok=True)

    ranking_rows: list[dict[str, Any]] = []
    variant_diag_rows: list[dict[str, Any]] = []
    policy_diag_rows: list[dict[str, Any]] = []
    robustness_rows: list[dict[str, Any]] = []
    shard_status_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    blackout_windows = list(manifest.get("blackout_windows_jst", []))

    run_meta_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for shard in manifest.get("shards", []):
        shard_id = str(shard.get("shard_id", ""))
        for run_meta in shard.get("runs", []):
            if isinstance(run_meta, dict):
                run_meta_lookup[(shard_id, str(run_meta.get("label", "")))] = run_meta

    for shard in manifest.get("shards", []):
        shard_id = str(shard.get("shard_id", ""))
        study_output = _resolve_study_output(shard, artifact_staging_root=artifact_staging_root)
        study_metadata_path = study_output / "study_metadata.yaml"
        if not study_metadata_path.exists():
            shard_status_rows.append({"shard_id": shard_id, "status": "missing_study_metadata", "completed_runs": 0})
            warnings.append(f"{shard_id}: study_metadata.yaml missing")
            continue

        study_metadata = _load_yaml(study_metadata_path)
        runs = study_metadata.get("runs", []) if isinstance(study_metadata, dict) else []
        completed = [r for r in runs if str(r.get("status", "")) == "completed"]
        shard_status_rows.append({"shard_id": shard_id, "status": "ok", "completed_runs": len(completed)})

        for run in completed:
            label = str(run.get("label", ""))
            run_dir = _resolve_run_output_dir(study_output=study_output, run_record=run)
            if run_dir is None:
                warnings.append(f"{shard_id}/{label}: run_dir unresolved in aggregate staging")
                continue
            overall = _safe_read_csv(run_dir / "summary_overall.csv")
            candidates = _safe_read_csv(run_dir / "candidates.csv")
            candidate_summary = _safe_read_csv(run_dir / "candidate_summary.csv")
            policy_summary = _safe_read_csv(run_dir / "policy_candidate_summary.csv")
            month_summary = _safe_read_csv(run_dir / "summary_by_month.csv")
            session_summary = _safe_read_csv(run_dir / "summary_by_session.csv")
            if overall.empty:
                warnings.append(f"{shard_id}/{label}: summary_overall.csv missing or empty")
                continue

            row = overall.iloc[0].to_dict()
            trade_count = int(row.get("trade_count", 0) or 0)
            total_pnl = float(row.get("total_pnl_pips", 0.0) or 0.0)
            avg_pnl = float(row.get("avg_pnl_pips", 0.0) or 0.0)
            win_rate = float(row.get("win_rate", 0.0) or 0.0)
            meta = run_meta_lookup.get((shard_id, label), {})

            blackout_excluded = 0
            kept_trade_count = trade_count
            kept_total_pnl = total_pnl
            kept_avg_pnl = avg_pnl
            if not candidates.empty and "timestamp" in candidates.columns and blackout_windows:
                blackout_mask = _in_blackout_jst(candidates["timestamp"], blackout_windows)
                blackout_excluded = int(blackout_mask.sum())
                kept = candidates.loc[~blackout_mask].copy()
                kept_trade_count = int(len(kept))
                kept_total_pnl = float(pd.to_numeric(kept.get("pnl_pips", pd.Series([], dtype=float)), errors="coerce").fillna(0.0).sum())
                kept_avg_pnl = (kept_total_pnl / kept_trade_count) if kept_trade_count else 0.0

            candidate_count = int(len(candidates))
            if not candidate_summary.empty and "candidate_count" in candidate_summary.columns:
                candidate_count = int(candidate_summary.iloc[0].get("candidate_count", candidate_count) or candidate_count)
            candidate_timestamps: set[str] = set()
            if not candidates.empty and "timestamp" in candidates.columns:
                ts = pd.to_datetime(candidates["timestamp"], errors="coerce", utc=True).dropna()
                candidate_timestamps = set(ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ").tolist())
            decision_policy = str(meta.get("decision_policy", "") or "")
            score_bundle = str(meta.get("score_bundle", "") or "")
            rv_selected_count = 0
            tr_selected_count = 0
            no_entry_group_count = 0
            if not policy_summary.empty:
                policy_row = policy_summary.iloc[0].to_dict()
                decision_policy = str(policy_row.get("decision_policy_family", decision_policy) or decision_policy)
                score_bundle = str(policy_row.get("score_bundle", score_bundle) or score_bundle)
                rv_selected_count = int(policy_row.get("rv_selected_count", 0) or 0)
                tr_selected_count = int(policy_row.get("tr_selected_count", 0) or 0)
                no_entry_group_count = int(policy_row.get("no_entry_group_count", 0) or 0)
                base_candidate_count = int(policy_row.get("base_candidate_count", candidate_count) or candidate_count)
                candidate_count = int(policy_row.get("selected_candidate_count", candidate_count) or candidate_count)
            else:
                base_candidate_count = candidate_count

            robustness = {
                **_pnl_stats(month_summary, "month"),
                **_pnl_stats(session_summary, "session"),
                "top_session_share": _top_session_share(session_summary),
            }
            ranking_rows.append(
                {
                    "batch_id": manifest.get("batch_id"),
                    "dataset_id": manifest.get("dataset_id"),
                    "shard_id": shard_id,
                    "variant_label": label,
                    "timing_mode": str(meta.get("timing_mode", "")),
                    "band_model": str(meta.get("band_model", "")),
                    "band_value": meta.get("band_value"),
                    "decision_policy": decision_policy,
                    "score_bundle": score_bundle,
                    "trade_count": trade_count,
                    "total_pnl_pips": total_pnl,
                    "avg_pnl_pips": avg_pnl,
                    "win_rate": win_rate,
                    "blackout_excluded_count": blackout_excluded,
                    "kept_trade_count": kept_trade_count,
                    "kept_total_pnl_pips": kept_total_pnl,
                    "kept_avg_pnl_pips": kept_avg_pnl,
                    "candidate_count": candidate_count,
                    "base_candidate_count": base_candidate_count,
                    "rv_selected_count": rv_selected_count,
                    "tr_selected_count": tr_selected_count,
                    "no_entry_group_count": no_entry_group_count,
                    **robustness,
                }
            )
            robustness_rows.append(
                {
                    "batch_id": manifest.get("batch_id"),
                    "dataset_id": manifest.get("dataset_id"),
                    "shard_id": shard_id,
                    "variant_label": label,
                    "timing_mode": str(meta.get("timing_mode", "")),
                    "band_model": str(meta.get("band_model", "")),
                    "band_value": meta.get("band_value"),
                    "decision_policy": decision_policy,
                    "score_bundle": score_bundle,
                    "kept_trade_count": kept_trade_count,
                    "kept_total_pnl_pips": kept_total_pnl,
                    "kept_avg_pnl_pips": kept_avg_pnl,
                    "candidate_count": candidate_count,
                    "base_candidate_count": base_candidate_count,
                    "rv_selected_count": rv_selected_count,
                    "tr_selected_count": tr_selected_count,
                    "no_entry_group_count": no_entry_group_count,
                    **robustness,
                }
            )
            variant_diag_rows.append(
                {
                    "variant_label": label,
                    "band_model": str(meta.get("band_model", "")),
                    "band_value": meta.get("band_value"),
                    "candidate_count": candidate_count,
                    "candidate_timestamps": candidate_timestamps,
                }
            )
            policy_diag_rows.append(
                {
                    "variant_label": label,
                    "band_model": str(meta.get("band_model", "")),
                    "band_value": meta.get("band_value"),
                    "decision_policy": decision_policy,
                    "score_bundle": score_bundle,
                    "candidate_count": candidate_count,
                    "rv_selected_count": rv_selected_count,
                    "tr_selected_count": tr_selected_count,
                    "no_entry_group_count": no_entry_group_count,
                    "candidate_timestamps": candidate_timestamps,
                }
            )

    ranking_df = pd.DataFrame(ranking_rows)
    if not ranking_df.empty:
        ranking_df = ranking_df.sort_values(["kept_total_pnl_pips", "kept_avg_pnl_pips", "kept_trade_count"], ascending=[False, False, False])
    shortlist_n = int((manifest.get("ranking_profile", {}) or {}).get("shortlist_top_n", 8) or 8)
    shortlist_df = ranking_df.head(shortlist_n).copy() if not ranking_df.empty else ranking_df.copy()
    robustness_df = pd.DataFrame(robustness_rows)
    if not robustness_df.empty:
        robustness_df = robustness_df.sort_values(
            [
                "worst_month_pnl_pips",
                "profitable_month_count",
                "worst_session_pnl_pips",
                "kept_total_pnl_pips",
            ],
            ascending=[False, False, False, False],
        )
    shortlist_robustness_df = robustness_df.head(shortlist_n).copy() if not robustness_df.empty else robustness_df.copy()
    variant_compare_df = pd.DataFrame(_build_variant_compare_rows(variant_diag_rows))
    policy_compare_df = pd.DataFrame(_build_policy_compare_rows(policy_diag_rows))

    spread_audit = _spread_audit(manifest, manifest_path)
    spread_required = bool((manifest.get("ranking_profile", {}) or {}).get("require_spread_column", False))
    if spread_required and not spread_audit.get("spread_column_present", False):
        warnings.append("Spread column required by profile but not available in dataset header")

    batch_metadata = {
        "batch_id": manifest.get("batch_id"),
        "dataset_id": manifest.get("dataset_id"),
        "output_tag": manifest.get("output_tag"),
        "variant_count": int(len(ranking_df)),
        "shard_count": int(manifest.get("shard_count", 0)),
        "blackout_windows_jst": blackout_windows,
        "spread_audit": spread_audit,
        "warnings": warnings,
    }
    batch_manifest = {
        "batch_id": manifest.get("batch_id"),
        "batch_spec": manifest.get("batch_spec"),
        "review_sink": manifest.get("review_sink"),
        "shard_status": shard_status_rows,
        "artifacts": {
            "batch_metadata": "batch_metadata.yaml",
            "batch_manifest": "batch_manifest.yaml",
            "batch_ranking": "batch_ranking.csv",
            "batch_shortlist": "batch_shortlist.csv",
            "batch_review": "batch_review.md",
            "batch_review_machine": "batch_review_machine.yaml",
            "band_variant_compare": "band_variant_compare.csv",
            "policy_variant_compare": "policy_variant_compare.csv",
            "policy_variant_robustness": "policy_variant_robustness.csv",
            "shortlist_robustness": "shortlist_robustness.csv",
        },
    }

    ranking_df.to_csv(batch_output / "batch_ranking.csv", index=False)
    shortlist_df.to_csv(batch_output / "batch_shortlist.csv", index=False)
    robustness_df.to_csv(batch_output / "policy_variant_robustness.csv", index=False)
    shortlist_robustness_df.to_csv(batch_output / "shortlist_robustness.csv", index=False)
    variant_compare_df.to_csv(batch_output / "band_variant_compare.csv", index=False)
    policy_compare_df.to_csv(batch_output / "policy_variant_compare.csv", index=False)
    _write_yaml(batch_output / "batch_metadata.yaml", batch_metadata)
    _write_yaml(batch_output / "batch_manifest.yaml", batch_manifest)

    issue_number = args.review_issue_number or str((manifest.get("review_sink", {}) or {}).get("issue_number", ""))
    comment_marker = str((manifest.get("review_sink", {}) or {}).get("comment_marker", "BATCH_REVIEW"))

    lines = [
        f"<!-- {comment_marker} -->",
        f"# Batch Review: {manifest.get('batch_id')}",
        "",
        f"- dataset_id: `{manifest.get('dataset_id')}`",
        f"- output_tag: `{manifest.get('output_tag') or '<none>'}`",
        f"- shard_count: `{manifest.get('shard_count')}`",
        f"- variant_count: `{len(ranking_df)}`",
        "",
        "## Shard status",
    ]
    for row in shard_status_rows:
        lines.append(f"- {row['shard_id']}: {row['status']} (completed_runs={row['completed_runs']})")
    lines.extend(["", "## Spread audit", f"- spread_mode: `{spread_audit.get('spread_mode')}`", f"- spread_column_present: `{spread_audit.get('spread_column_present')}`"])
    stats = spread_audit.get("stats", {}) or {}
    if stats:
        lines.append(
            "- stats: "
            f"non_null={stats.get('non_null_count')}, zero={stats.get('zero_count')}, "
            f"min={stats.get('min')}, p50={stats.get('p50')}, p90={stats.get('p90')}, max={stats.get('max')}"
        )
    lines.extend(["", "## Blackout windows (JST)"])
    if blackout_windows:
        for w in blackout_windows:
            lines.append(
                f"- {w.get('start_hhmmss')} -> {w.get('end_hhmmss')} ({w.get('label', 'window')}, recurring daily JST)"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Top ranked variants by kept_total_pnl_pips"])
    if shortlist_df.empty:
        lines.append("- none")
    else:
        for _, row in shortlist_df.iterrows():
            lines.append(
                f"- {row['variant_label']} ({row.get('timing_mode')}/{row.get('band_model')}={row.get('band_value')}, "
                f"policy={row.get('decision_policy') or '<default>'}, score={row.get('score_bundle') or '<default>'}): "
                f"kept_total_pnl_pips={row['kept_total_pnl_pips']:.3f}, "
                f"kept_avg_pnl_pips={row['kept_avg_pnl_pips']:.3f}, kept_trade_count={int(row['kept_trade_count'])}, "
                f"blackout_excluded={int(row['blackout_excluded_count'])}"
            )
    lines.extend(["", "## Top robust variants"])
    if shortlist_robustness_df.empty:
        lines.append("- none")
    else:
        for _, row in shortlist_robustness_df.iterrows():
            lines.append(
                f"- {row['variant_label']} ({row.get('timing_mode')}/{row.get('band_model')}={row.get('band_value')}, "
                f"policy={row.get('decision_policy') or '<default>'}, score={row.get('score_bundle') or '<default>'}): "
                f"worst_month_pnl_pips={row['worst_month_pnl_pips']:.3f}, "
                f"profitable_month_count={int(row['profitable_month_count'])}, "
                f"losing_month_count={int(row['losing_month_count'])}, "
                f"worst_session_pnl_pips={row['worst_session_pnl_pips']:.3f}, "
                f"top_session_share={row['top_session_share']:.3f}, "
                f"kept_total_pnl_pips={row['kept_total_pnl_pips']:.3f}"
            )
    lines.extend(["", "## Band variant compare"])
    if variant_compare_df.empty:
        lines.append("- no comparable variant pair found")
    else:
        c = variant_compare_df.iloc[0]
        lines.append(
            f"- {c['variant_a']} vs {c['variant_b']}: "
            f"candidate_count=({int(c['candidate_count_a'])}, {int(c['candidate_count_b'])}), "
            f"overlap={int(c['candidate_timestamp_overlap_count'])}, "
            f"only_a={int(c['candidate_timestamp_only_a'])}, only_b={int(c['candidate_timestamp_only_b'])}"
        )
    lines.extend(["", "## Policy variant compare"])
    if policy_compare_df.empty:
        lines.append("- no comparable policy variant pair found")
    else:
        c = policy_compare_df.iloc[0]
        lines.append(
            f"- {c['variant_a']} ({c['decision_policy_a']}/{c['score_bundle_a']}) vs "
            f"{c['variant_b']} ({c['decision_policy_b']}/{c['score_bundle_b']}): "
            f"candidate_count=({int(c['candidate_count_a'])}, {int(c['candidate_count_b'])}), "
            f"rv=({int(c['rv_selected_count_a'])}, {int(c['rv_selected_count_b'])}), "
            f"tr=({int(c['tr_selected_count_a'])}, {int(c['tr_selected_count_b'])}), "
            f"no_entry=({int(c['no_entry_group_count_a'])}, {int(c['no_entry_group_count_b'])}), "
            f"overlap={int(c['candidate_timestamp_overlap_count'])}"
        )
    lines.extend(["", "## No-entry-heavy variants"])
    if ranking_df.empty or "no_entry_group_count" not in ranking_df.columns:
        lines.append("- none")
    else:
        no_entry_df = ranking_df.sort_values(
            ["no_entry_group_count", "base_candidate_count", "kept_total_pnl_pips"],
            ascending=[False, False, False],
        ).head(shortlist_n)
        if no_entry_df.empty or int(no_entry_df["no_entry_group_count"].max()) <= 0:
            lines.append("- none")
        else:
            for _, row in no_entry_df.iterrows():
                base_count = int(row.get("base_candidate_count", 0) or 0)
                no_entry_count = int(row.get("no_entry_group_count", 0) or 0)
                no_entry_share = (no_entry_count / base_count) if base_count else 0.0
                lines.append(
                    f"- {row['variant_label']} (policy={row.get('decision_policy') or '<default>'}, "
                    f"score={row.get('score_bundle') or '<default>'}): "
                    f"no_entry_group_count={no_entry_count}, base_candidate_count={base_count}, "
                    f"no_entry_share={no_entry_share:.3f}, "
                    f"rv={int(row.get('rv_selected_count', 0) or 0)}, "
                    f"tr={int(row.get('tr_selected_count', 0) or 0)}, "
                    f"kept_total_pnl_pips={row['kept_total_pnl_pips']:.3f}"
                )

    lines.extend(
        [
            "",
            "## Shortlist artifacts",
            "- `batch_shortlist.csv`",
            "- `shortlist_robustness.csv`",
            "",
            "## Warnings",
        ]
    )
    if warnings:
        lines.extend([f"- {w}" for w in warnings])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Key artifacts",
            "- `batch_metadata.yaml`",
            "- `batch_manifest.yaml`",
            "- `batch_ranking.csv`",
            "- `batch_shortlist.csv`",
            "- `batch_review.md`",
            "- `batch_review_machine.yaml`",
            "- `band_variant_compare.csv`",
            "- `policy_variant_compare.csv`",
            "- `policy_variant_robustness.csv`",
            "- `shortlist_robustness.csv`",
        ]
    )
    review_md = "\n".join(lines) + "\n"
    (batch_output / "batch_review.md").write_text(review_md, encoding="utf-8")

    review_machine = {
        "issue_number": issue_number,
        "comment_marker": comment_marker,
        "batch_id": manifest.get("batch_id"),
        "dataset_id": manifest.get("dataset_id"),
        "output_tag": manifest.get("output_tag"),
        "warnings": warnings,
        "spread_audit": spread_audit,
        "shortlist_count": int(len(shortlist_df)),
        "review_markdown_path": str((batch_output / "batch_review.md").resolve()),
    }
    _write_yaml(batch_output / "batch_review_machine.yaml", review_machine)

    print(
        "Batch review completed:",
        f"batch_id={manifest.get('batch_id')}",
        f"variants={len(ranking_df)}",
        f"shortlist={len(shortlist_df)}",
        f"out={batch_output}",
    )


if __name__ == "__main__":
    main()
