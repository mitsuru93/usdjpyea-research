#!/usr/bin/env python3
"""Expand batch research spec into deterministic shard study configs."""

from __future__ import annotations

import argparse
import json
import itertools
import math
import os
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.orchestration.path_utils import ensure_directory, sanitize_label

SPREAD_MODES = {"ignore", "audit_only", "column_proxy"}
DEFAULT_BAND_MODEL_WEIGHTS = {
    "percent": 1.0,
    "fixed_pips": 1.0,
    "max_percent_fixed_floor": 1.2,
    "atr": 1.8,
    "min_atr_fixed_cap": 2.0,
    "max_atr_fixed_floor": 2.0,
    "range_mean": 1.6,
    "range_median": 1.9,
    "range_percentile": 3.0,
    "stddev": 2.4,
    "realized_vol_cc": 3.2,
    "parkinson": 3.2,
    "garman_klass": 3.4,
    "rogers_satchell": 3.4,
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping-style YAML config at {path}")
    return data


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def _repo_relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand batch spec into shard study configs for matrix execution.")
    parser.add_argument("--batch-spec", required=True, help="Path to batch spec YAML")
    parser.add_argument("--dataset-id", default=None, help="Optional dataset_id override")
    parser.add_argument("--output-tag", default=None, help="Optional output tag override")
    parser.add_argument("--runtime-dir", default="research/reports/batches/runtime", help="Batch runtime output root")
    parser.add_argument(
        "--write-github-output",
        action="store_true",
        help="When set, write core paths + matrix JSON to GITHUB_OUTPUT",
    )
    return parser.parse_args()


def _validate_batch_spec(spec: dict[str, Any]) -> None:
    required = [
        "batch_id",
        "dataset_registry",
        "dataset_id",
        "output_root",
        "shard_size",
        "blackout_windows_jst",
        "spread_mode",
        "band_model_sweep",
        "timing_modes",
        "compare_sections",
        "ranking_profile",
        "review_sink",
        "notes",
    ]
    missing = [k for k in required if k not in spec]
    if missing:
        raise ValueError(f"Batch spec missing required fields: {missing}")

    shard_size = int(spec["shard_size"])
    if shard_size <= 0:
        raise ValueError("shard_size must be > 0")

    spread_mode = str(spec.get("spread_mode", "")).strip()
    if spread_mode not in SPREAD_MODES:
        raise ValueError(f"spread_mode must be one of {sorted(SPREAD_MODES)}")

    blackout_windows = spec.get("blackout_windows_jst", [])
    if not isinstance(blackout_windows, list):
        raise ValueError("blackout_windows_jst must be a list")
    for idx, window in enumerate(blackout_windows):
        if not isinstance(window, dict):
            raise ValueError(f"blackout_windows_jst[{idx}] must be a mapping")
        if str(window.get("start_hhmmss", "")).strip() == "" or str(window.get("end_hhmmss", "")).strip() == "":
            raise ValueError(
                f"blackout_windows_jst[{idx}] must define daily recurring 'start_hhmmss' and 'end_hhmmss'"
            )

    analyze_after_run = spec.get("analyze_after_run", True)
    if not isinstance(analyze_after_run, bool):
        raise ValueError("analyze_after_run must be a boolean when provided")

    weighted_cfg = spec.get("weighted_sharding")
    if weighted_cfg is None:
        return
    if not isinstance(weighted_cfg, dict):
        raise ValueError("weighted_sharding must be a mapping when provided")
    enabled = weighted_cfg.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("weighted_sharding.enabled must be a boolean")
    model_weights = weighted_cfg.get("model_weights")
    if model_weights is not None:
        if not isinstance(model_weights, dict):
            raise ValueError("weighted_sharding.model_weights must be a mapping")
        for key, value in model_weights.items():
            model_name = str(key).strip().lower()
            if not model_name:
                raise ValueError("weighted_sharding.model_weights keys must be non-empty")
            try:
                weight = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"weighted_sharding.model_weights[{key!r}] must be numeric") from exc
            if weight <= 0:
                raise ValueError(f"weighted_sharding.model_weights[{key!r}] must be > 0")


def _band_variants(spec: dict[str, Any]) -> list[dict[str, Any]]:
    sweep = spec.get("band_model_sweep", {}) or {}
    if sweep.get("families"):
        variants: list[dict[str, Any]] = []
        families = sweep.get("families", {}) or {}
        for family_name, family_cfg_raw in families.items():
            family_cfg = family_cfg_raw or {}
            models = [str(x).strip().lower() for x in family_cfg.get("models", []) if str(x).strip()]
            if not models:
                models = [str(family_name).strip().lower()]
            grid_cfg = family_cfg.get("grid", {}) or {}
            ordered_keys = [str(k) for k in grid_cfg.keys()]
            value_lists: list[list[Any]] = []
            for key in ordered_keys:
                raw_values = grid_cfg.get(key, [])
                values = list(raw_values) if isinstance(raw_values, list) else [raw_values]
                value_lists.append(values)
            if not value_lists:
                value_lists = [[]]
            for model in models:
                for combo in itertools.product(*value_lists) if ordered_keys else [tuple()]:
                    cfg = {"band_model": model}
                    combo_tokens: list[str] = []
                    band_value = ""
                    for idx, key in enumerate(ordered_keys):
                        value = combo[idx]
                        cfg[key] = value
                        if key in {"band_percent", "band_pips", "band_atr_k", "band_std_k", "band_vol_k"} and band_value == "":
                            band_value = value
                        token_val = sanitize_label(str(value)).upper()[:8]
                        combo_tokens.append(f"{sanitize_label(key).upper()[:4]}{token_val}")
                    token_base = sanitize_label(family_name).upper()[:5] or "BAND"
                    token = f"{token_base}{len(variants):03d}" if not combo_tokens else f"{token_base}_{'_'.join(combo_tokens)}"
                    variants.append(
                        {
                            "band_model_family": str(family_name).strip().lower(),
                            "band_model": model,
                            "band_value": band_value,
                            "band_token": token[:40],
                            "cfg": cfg,
                        }
                    )
        if not variants:
            raise ValueError("band_model_sweep.families produced zero variants")
        return variants

    if sweep.get("variants"):
        variants: list[dict[str, Any]] = []
        for idx, raw in enumerate(sweep.get("variants", [])):
            item = dict(raw or {})
            band_model = str(item.get("band_model", "")).strip().lower()
            if not band_model:
                raise ValueError(f"band_model_sweep.variants[{idx}] missing band_model")
            family = str(item.get("band_model_family", band_model)).strip().lower()
            token = str(item.get("band_token", "")).strip() or f"V{idx:03d}"
            band_cfg = {"band_model": band_model}
            for key, value in item.items():
                if key.startswith("band_") and key not in {"band_model_family", "band_token"}:
                    band_cfg[key] = value
            variants.append(
                {
                    "band_model_family": family,
                    "band_model": band_model,
                    "band_value": item.get("band_value", ""),
                    "band_token": token,
                    "cfg": band_cfg,
                }
            )
        if not variants:
            raise ValueError("band_model_sweep.variants produced zero variants")
        return variants

    pct_values = [float(v) for v in sweep.get("percent_envelope", [])]
    pip_values = [float(v) for v in sweep.get("fixed_pip_envelope", [])]
    atr_values = [float(v) for v in sweep.get("atr_k_envelope", [])]

    variants: list[dict[str, Any]] = []
    for value in pct_values:
        token = f"PCT{int(round(value * 1000)):03d}"
        variants.append(
            {
                "band_model_family": "percent",
                "band_model": "percent",
                "band_value": value,
                "band_token": token,
                "cfg": {"band_model": "percent", "band_percent": value},
            }
        )
    for value in pip_values:
        token = f"PIP{int(round(value)):02d}"
        variants.append(
            {
                "band_model_family": "fixed_pips",
                "band_model": "fixed_pips",
                "band_value": value,
                "band_token": token,
                "cfg": {"band_model": "fixed_pips", "band_pips": value},
            }
        )
    for value in atr_values:
        token = f"ATR{int(round(value * 10)):02d}"
        variants.append(
            {
                "band_model_family": "atr",
                "band_model": "atr",
                "band_value": value,
                "band_token": token,
                "cfg": {"band_model": "atr", "band_atr_k": value},
            }
        )
    if not variants:
        raise ValueError("band_model_sweep produced zero variants")
    return variants


def _build_variant_label(*, family_token: str, band_token: str, timing_mode: str) -> str:
    timing_token = {
        "baseline_touch": "TRGBASE",
        "rv_close_confirm": "TRGRV",
        "all_close": "TRGALL",
    }.get(timing_mode, f"TRG{sanitize_label(timing_mode).upper()}")
    return f"FAM{family_token}__BAND{band_token}__{timing_token}__HG30__DECBASE__EXNONE__V1"


def _decision_policy_variants(spec: dict[str, Any]) -> list[dict[str, Any]]:
    sweep = spec.get("decision_policy_sweep")
    if not sweep:
        return [{"decision_policy": "", "score_bundle": "", "decision_token": "DECBASE", "score_token": "SFBASE"}]

    policies = [str(x).strip() for x in (sweep.get("families", []) or []) if str(x).strip()]
    bundles = [str(x).strip() for x in (sweep.get("score_bundles", []) or []) if str(x).strip()]
    if not policies:
        raise ValueError("decision_policy_sweep.families must define at least one policy")
    if not bundles:
        raise ValueError("decision_policy_sweep.score_bundles must define at least one score bundle")

    policy_tokens = {
        "bin_env_v1": "DENV",
        "bin_forceflip_v1": "DFF",
        "two_stage_margin_v1": "D2M",
        "tri_score_rvtrno_v1": "D3S",
    }
    score_tokens = {
        "sf_ctx_base_v1": "SBAS",
        "sf_ctx_momo_v1": "SMOM",
        "sf_timing_micro_v1": "STIM",
        "sf_zone_risk_v1": "SZON",
    }
    margin_threshold_values = sweep.get("margin_threshold_values")
    no_entry_threshold_values = sweep.get("no_entry_threshold_values")
    legacy_policy_bundle_only = margin_threshold_values is None and no_entry_threshold_values is None

    if legacy_policy_bundle_only:
        variants: list[dict[str, Any]] = []
        for policy in policies:
            for bundle in bundles:
                policy_key = policy.lower()
                bundle_key = bundle.lower()
                variants.append(
                    {
                        "decision_policy": policy,
                        "score_bundle": bundle,
                        "decision_token": policy_tokens.get(policy_key, f"D{sanitize_label(policy).upper()}"),
                        "score_token": score_tokens.get(bundle_key, f"S{sanitize_label(bundle).upper()}"),
                    }
                )
        return variants

    margin_values = [float(x) for x in (margin_threshold_values or [0.75])]
    no_entry_values = [float(x) for x in (no_entry_threshold_values or [0.25])]
    if not margin_values:
        raise ValueError("decision_policy_sweep.margin_threshold_values must define at least one numeric value")
    if not no_entry_values:
        raise ValueError("decision_policy_sweep.no_entry_threshold_values must define at least one numeric value")

    variants: list[dict[str, Any]] = []

    def _threshold_token(margin: float, no_entry: float, *, include_no_entry: bool) -> str:
        margin_token = int(round(margin * 100))
        no_entry_token = int(round(no_entry * 100))
        if include_no_entry:
            return f"M{margin_token:03d}N{no_entry_token:03d}"
        return f"M{margin_token:03d}"

    for policy in policies:
        for bundle in bundles:
            policy_key = policy.lower()
            bundle_key = bundle.lower()
            base_decision_token = policy_tokens.get(policy_key, f"D{sanitize_label(policy).upper()}")
            score_token = score_tokens.get(bundle_key, f"S{sanitize_label(bundle).upper()}")

            if policy_key == "two_stage_margin_v1":
                for margin_threshold in margin_values:
                    no_entry_threshold = 0.25
                    variants.append(
                        {
                            "decision_policy_family": policy,
                            "decision_policy": {
                                "family": policy,
                                "margin_threshold": margin_threshold,
                                "no_entry_threshold": no_entry_threshold,
                            },
                            "score_bundle": bundle,
                            "margin_threshold": margin_threshold,
                            "no_entry_threshold": no_entry_threshold,
                            "decision_token": f"{base_decision_token}{_threshold_token(margin_threshold, no_entry_threshold, include_no_entry=False)}",
                            "score_token": score_token,
                        }
                    )
                continue

            if policy_key == "tri_score_rvtrno_v1":
                for margin_threshold, no_entry_threshold in itertools.product(margin_values, no_entry_values):
                    variants.append(
                        {
                            "decision_policy_family": policy,
                            "decision_policy": {
                                "family": policy,
                                "margin_threshold": margin_threshold,
                                "no_entry_threshold": no_entry_threshold,
                            },
                            "score_bundle": bundle,
                            "margin_threshold": margin_threshold,
                            "no_entry_threshold": no_entry_threshold,
                            "decision_token": f"{base_decision_token}{_threshold_token(margin_threshold, no_entry_threshold, include_no_entry=True)}",
                            "score_token": score_token,
                        }
                    )
                continue

            default_margin_threshold = 0.75
            default_no_entry_threshold = 0.25
            variants.append(
                {
                    "decision_policy_family": policy,
                    "decision_policy": {
                        "family": policy,
                        "margin_threshold": default_margin_threshold,
                        "no_entry_threshold": default_no_entry_threshold,
                    },
                    "score_bundle": bundle,
                    "margin_threshold": default_margin_threshold,
                    "no_entry_threshold": default_no_entry_threshold,
                    "decision_token": base_decision_token,
                    "score_token": score_token,
                }
            )

    return variants


def _build_policy_variant_label(
    *, family_token: str, band_token: str, timing_mode: str, decision_token: str, score_token: str
) -> str:
    timing_token = {
        "baseline_touch": "TRGBASE",
        "rv_close_confirm": "TRGRV",
        "all_close": "TRGALL",
    }.get(timing_mode, f"TRG{sanitize_label(timing_mode).upper()}")
    return f"FAM{family_token}__BAND{band_token}__{timing_token}__HG30__{decision_token}__{score_token}__V1"


def _variant_weight(variant: dict[str, Any], model_weights: dict[str, float]) -> float:
    band_model = str(variant.get("band_model", "")).strip().lower()
    return float(model_weights.get(band_model, 1.0))


def _contiguous_assignments(*, variants: list[dict[str, Any]], shard_size: int) -> list[list[dict[str, Any]]]:
    shard_count = math.ceil(len(variants) / shard_size)
    return [
        variants[shard_index * shard_size : min((shard_index + 1) * shard_size, len(variants))]
        for shard_index in range(shard_count)
    ]


def _weighted_assignments(
    *,
    variants: list[dict[str, Any]],
    shard_size: int,
    model_weights: dict[str, float],
) -> tuple[list[list[dict[str, Any]]], list[float]]:
    shard_count = math.ceil(len(variants) / shard_size)
    shards: list[list[dict[str, Any]]] = [[] for _ in range(shard_count)]
    shard_totals: list[float] = [0.0 for _ in range(shard_count)]
    ranked_variants = sorted(
        variants,
        key=lambda item: (-_variant_weight(item, model_weights), str(item.get("label", ""))),
    )
    for variant in ranked_variants:
        candidates = [idx for idx in range(shard_count) if len(shards[idx]) < shard_size]
        if not candidates:
            raise RuntimeError("Weighted sharding failed: no shard has remaining capacity")
        target_idx = min(candidates, key=lambda idx: (shard_totals[idx], idx))
        shards[target_idx].append(variant)
        shard_totals[target_idx] += _variant_weight(variant, model_weights)
    return shards, shard_totals


def main() -> None:
    args = parse_args()
    batch_spec_path = Path(args.batch_spec).resolve()
    spec = _load_yaml(batch_spec_path)
    _validate_batch_spec(spec)

    dataset_id = str(args.dataset_id).strip() if args.dataset_id else str(spec["dataset_id"]).strip()
    output_tag = str(args.output_tag).strip() if args.output_tag else str(spec.get("output_tag_default", "")).strip()

    batch_id = str(spec["batch_id"]).strip()
    runtime_root = ensure_directory(Path(args.runtime_dir).resolve())
    runtime_dir = ensure_directory(runtime_root / sanitize_label(batch_id))

    output_root = Path(str(spec["output_root"]))
    if not output_root.is_absolute():
        output_root = (REPO_ROOT / output_root).resolve()
    if output_tag:
        output_root = output_root / sanitize_label(output_tag)
    output_root = output_root.resolve()

    variants: list[dict[str, Any]] = []
    for timing_mode in [str(x).strip() for x in spec.get("timing_modes", []) if str(x).strip()]:
        for band_variant in _band_variants(spec):
            for decision_variant in _decision_policy_variants(spec):
                family_token = sanitize_label(str(band_variant.get("band_model_family", "base")).upper())[:12] or "BASE"
                if decision_variant["decision_policy"]:
                    label = _build_policy_variant_label(
                        family_token=family_token,
                        band_token=band_variant["band_token"],
                        timing_mode=timing_mode,
                        decision_token=decision_variant["decision_token"],
                        score_token=decision_variant["score_token"],
                    )
                else:
                    label = _build_variant_label(
                        family_token=family_token, band_token=band_variant["band_token"], timing_mode=timing_mode
                    )
                variants.append(
                    {
                        "label": label,
                        "timing_mode": timing_mode,
                        "band_model_family": band_variant.get("band_model_family", band_variant["band_model"]),
                        "band_model": band_variant["band_model"],
                        "band_value": band_variant["band_value"],
                        **band_variant["cfg"],
                        **{
                            key: value
                            for key, value in decision_variant.items()
                            if key in {"decision_policy", "score_bundle"}
                        },
                    }
                )

    if not variants:
        raise ValueError("No variants produced from timing_modes x band_model_sweep")

    shard_size = int(spec["shard_size"])
    analyze_after_run = bool(spec.get("analyze_after_run", True))
    weighted_cfg = spec.get("weighted_sharding", {}) or {}
    weighted_enabled = bool(weighted_cfg.get("enabled", False))
    configured_weights = weighted_cfg.get("model_weights", {}) or {}
    band_model_weights = dict(DEFAULT_BAND_MODEL_WEIGHTS)
    band_model_weights.update({str(k).strip().lower(): float(v) for k, v in configured_weights.items()})
    if weighted_enabled:
        shard_variants_list, shard_weight_totals = _weighted_assignments(
            variants=variants,
            shard_size=shard_size,
            model_weights=band_model_weights,
        )
        sharding_strategy = "weighted_greedy"
    else:
        shard_variants_list = _contiguous_assignments(variants=variants, shard_size=shard_size)
        shard_weight_totals = [
            sum(_variant_weight(item, band_model_weights) for item in shard_variants) for shard_variants in shard_variants_list
        ]
        sharding_strategy = "contiguous"
    shard_count = len(shard_variants_list)
    shards_dir = ensure_directory(runtime_dir / "shards")

    shard_records: list[dict[str, Any]] = []
    for shard_index, shard_variants in enumerate(shard_variants_list):
        shard_id = f"shard_{shard_index:03d}"
        shard_dir = ensure_directory(shards_dir / shard_id)
        shard_runtime_relpath = f"shards/{shard_id}/study"
        study_config_relpath = f"shards/{shard_id}/study_config.yaml"
        shard_artifact_name = f"batch-shard-{sanitize_label(batch_id)}-{shard_id}"
        study_output = (output_root / "shards" / shard_id / "study").resolve()
        study_cfg_path = (shard_dir / "study_config.yaml").resolve()

        runs = []
        for variant in shard_variants:
            run_item = {
                "label": variant["label"],
                "dataset_id": dataset_id,
                "timing_mode": variant["timing_mode"],
                "band_model": variant["band_model"],
                "decision_policy": variant.get("decision_policy"),
                "score_bundle": variant.get("score_bundle"),
                "notes": (
                    f"batch_variant family={variant.get('band_model_family')} "
                    f"model={variant['band_model']} "
                    f"decision_policy={variant.get('decision_policy_family') or variant.get('decision_policy') or 'bin_env_v1'} "
                    f"score_bundle={variant.get('score_bundle') or 'sf_ctx_base_v1'}"
                ),
            }
            for key, value in variant.items():
                if key.startswith("band_") and key not in {"band_model_family", "band_token"}:
                    run_item[key] = value
            runs.append(
                run_item
            )

        study_cfg = {
            "study_name": f"{batch_id}__{shard_id}",
            "output_root": str(study_output),
            "dataset_registry": spec["dataset_registry"],
            "shared_defaults": {
                "input_timezone_mode": "UTC",
                "max_holding_bars": 30,
                "symbol": "USDJPY",
                "timeframe": "M1",
                "analyze_after_run": analyze_after_run,
            },
            "runs": runs,
            "compare": {
                "enabled": True,
                "compare_sections": list(spec.get("compare_sections", [])),
                "selected_bucket_features": [],
                "notes": f"batch shard compare for {batch_id} {shard_id}",
            },
            "notes": f"Batch-generated shard config ({batch_id}/{shard_id}); pre-MT4 research-only.",
        }
        _write_yaml(study_cfg_path, study_cfg)

        shard_records.append(
            {
                "shard_id": shard_id,
                "shard_index": shard_index,
                "study_config": str(study_cfg_path),
                "study_config_relpath": study_config_relpath,
                "study_output": str(study_output),
                "study_output_relpath": shard_runtime_relpath,
                "shard_runtime_relpath": shard_runtime_relpath,
                "shard_output_relpath": shard_runtime_relpath,
                "shard_artifact_name": shard_artifact_name,
                "run_count": len(shard_variants),
                "estimated_weight_total": float(shard_weight_totals[shard_index]),
                "runs": shard_variants,
            }
        )

    manifest = {
        "batch_id": batch_id,
        "batch_spec": str(batch_spec_path),
        "dataset_registry": str(spec["dataset_registry"]),
        "dataset_id": dataset_id,
        "output_tag": output_tag,
        "output_root": str(output_root),
        "spread_mode": str(spec["spread_mode"]),
        "blackout_windows_jst": list(spec.get("blackout_windows_jst", [])),
        "ranking_profile": dict(spec.get("ranking_profile", {})),
        "review_sink": dict(spec.get("review_sink", {})),
        "analyze_after_run": analyze_after_run,
        "sharding_strategy": sharding_strategy,
        "weighted_sharding": {
            "enabled": weighted_enabled,
            "weight_proxy": "band_model_compute_class",
            "model_weights": band_model_weights,
        },
        "compare_sections": list(spec.get("compare_sections", [])),
        "shard_size": shard_size,
        "shard_count": shard_count,
        "variant_count": len(variants),
        "runtime_bundle_relroot": _repo_relpath(runtime_dir),
        "batch_manifest_relpath": f"{_repo_relpath(runtime_dir)}/batch_manifest.yaml",
        "shards": shard_records,
        "notes": str(spec.get("notes", "")),
    }

    manifest_path = (runtime_dir / "batch_manifest.yaml").resolve()
    _write_yaml(manifest_path, manifest)

    matrix_rows = [
        {
            "shard_id": rec["shard_id"],
            "study_config": rec["study_config"],
            "study_config_relpath": rec["study_config_relpath"],
            "study_output": rec["study_output"],
            "study_output_relpath": rec["study_output_relpath"],
            "shard_runtime_relpath": rec["shard_runtime_relpath"],
            "shard_artifact_name": rec["shard_artifact_name"],
        }
        for rec in shard_records
    ]
    matrix_payload = {"include": matrix_rows}
    matrix_json = json.dumps(matrix_payload)

    print(
        "Batch expansion completed:",
        f"batch_id={batch_id}",
        f"dataset_id={dataset_id}",
        f"variants={len(variants)}",
        f"shards={shard_count}",
        f"runtime_dir={runtime_dir}",
    )

    if args.write_github_output:
        github_output_raw = os.environ.get("GITHUB_OUTPUT", "").strip()
        if not github_output_raw:
            raise RuntimeError("--write-github-output was provided but GITHUB_OUTPUT is not set")
        github_output = Path(github_output_raw)
        with github_output.open("a", encoding="utf-8") as out:
            out.write(f"batch_runtime_dir={runtime_dir.as_posix()}\n")
            out.write(f"runtime_bundle_relroot={_repo_relpath(runtime_dir)}\n")
            out.write(f"batch_manifest={manifest_path.as_posix()}\n")
            out.write(f"batch_manifest_relpath={_repo_relpath(manifest_path)}\n")
            out.write(f"batch_output_root={output_root.as_posix()}\n")
            out.write(f"batch_id={batch_id}\n")
            out.write(f"dataset_id={dataset_id}\n")
            out.write(f"output_tag={output_tag}\n")
            out.write(f"matrix={matrix_json}\n")


if __name__ == "__main__":
    main()
