"""Study-level orchestrator for multi-run experiment/analysis/compare workflows."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from research.io.dataset_resolver import resolve_dataset_to_local_csv
from research.orchestration.path_utils import ensure_directory, resolve_local_path, sanitize_label

RUN_REQUIRED_KEYS = ["input_csv", "input_timezone_mode", "max_holding_bars", "symbol", "timeframe"]
ANALYSIS_OPTIONAL_KEYS = [
    "quantile_bucket_count",
    "selected_features",
    "selected_feature_pairs",
    "slice_modes",
    "bucket_mode",
    "fixed_bins_by_feature",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping-style YAML config at {path}")
    return data


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def _load_dataset_registry(path: Path) -> dict[str, Any]:
    data = _load_yaml(path)
    datasets = data.get("datasets", {})
    if not isinstance(datasets, dict):
        raise ValueError(f"Dataset registry must define mapping-style 'datasets' at {path}")
    return data


def _run_cli(cli_path: Path, config_path: Path, repo_root: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(cli_path), "--config", str(config_path)]
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) if not existing else f"{repo_root}:{existing}"
    return subprocess.run(cmd, text=True, capture_output=True, check=False, cwd=repo_root, env=env)


def _validate_study_config(cfg: dict[str, Any]) -> None:
    required = ["study_name", "output_root", "shared_defaults", "runs"]
    missing = [key for key in required if key not in cfg]
    if missing:
        raise ValueError(f"Study config missing required fields: {missing}")

    runs = cfg.get("runs", [])
    if not isinstance(runs, list) or not runs:
        raise ValueError("Study config requires a non-empty 'runs' list")

    shared_defaults = cfg.get("shared_defaults", {}) if isinstance(cfg.get("shared_defaults", {}), dict) else {}
    shared_has_input_csv = str(shared_defaults.get("input_csv", "")).strip() != ""
    shared_has_dataset_id = str(shared_defaults.get("dataset_id", "")).strip() != ""

    for idx, run in enumerate(runs):
        if not isinstance(run, dict):
            raise ValueError(f"runs[{idx}] must be a mapping")
        if "label" not in run:
            raise ValueError(f"runs[{idx}] must include at least 'label'")
        has_input_csv = str(run.get("input_csv", "")).strip() != ""
        has_dataset_id = str(run.get("dataset_id", "")).strip() != ""
        if not (has_input_csv or has_dataset_id or shared_has_input_csv or shared_has_dataset_id):
            raise ValueError(f"runs[{idx}] must include 'input_csv' or 'dataset_id'")


def _resolve_dataset_input_csv(
    *,
    merged: dict[str, Any],
    dataset_registry: dict[str, Any],
    dataset_registry_path: Path | None,
    study_label: str,
    repo_root: Path,
    dataset_cache_dir: Path,
) -> str:
    input_csv = str(merged.get("input_csv", "")).strip()
    if input_csv:
        return str(resolve_local_path(input_csv, base_dir=repo_root))

    dataset_id = str(merged.get("dataset_id", "")).strip()
    if not dataset_id:
        raise ValueError(f"run '{study_label}' must define 'input_csv' or 'dataset_id'")

    datasets = dataset_registry.get("datasets", {})
    dataset_entry = datasets.get(dataset_id)
    if not isinstance(dataset_entry, dict):
        registry_display = str(dataset_registry_path) if dataset_registry_path else "<none>"
        raise KeyError(f"run '{study_label}' dataset_id '{dataset_id}' not found in registry: {registry_display}")

    resolved = resolve_dataset_to_local_csv(
        dataset_id=dataset_id,
        entry=dataset_entry,
        repo_root=repo_root,
        cache_dir=dataset_cache_dir,
    )
    return str(resolved)


def _build_run_experiment_config(
    *,
    shared_defaults: dict[str, Any],
    run_cfg: dict[str, Any],
    run_output_dir: Path,
    repo_root: Path,
    study_config_dir: Path,
    dataset_registry: dict[str, Any],
    dataset_registry_path: Path | None,
    dataset_cache_dir: Path,
) -> dict[str, Any]:
    merged = dict(shared_defaults)
    merged.update(run_cfg)
    _normalize_policy_override_fields(merged=merged, run_cfg=run_cfg)

    merged["output_dir"] = str(run_output_dir)
    merged["input_csv"] = _resolve_dataset_input_csv(
        merged=merged,
        dataset_registry=dataset_registry,
        dataset_registry_path=dataset_registry_path,
        study_label=str(run_cfg.get("label", "")),
        repo_root=repo_root,
        dataset_cache_dir=dataset_cache_dir,
    )
    _normalize_policy_file_path(merged=merged, study_config_dir=study_config_dir, repo_root=repo_root)

    missing = [key for key in RUN_REQUIRED_KEYS if key not in merged]
    if missing:
        raise ValueError(f"run '{run_cfg.get('label', '')}' missing required run fields after merge: {missing}")

    passthrough_keys = [
        *RUN_REQUIRED_KEYS,
        "input_csv",
        "output_dir",
        "notes",
        "policy",
        "policy_file",
        "timing_mode",
        "band_model",
        "band_percent",
        "band_pips",
        "band_atr_k",
        "band_atr_period",
        "pip_size",
        "ema_period",
    ]
    return {key: merged[key] for key in passthrough_keys if key in merged}


def _normalize_policy_override_fields(*, merged: dict[str, Any], run_cfg: dict[str, Any]) -> None:
    """Normalize run-level policy overrides against shared defaults.

    Rules:
    - run-level `policy` override removes inherited `policy_file` unless run explicitly also defines `policy_file`.
    - run-level `policy_file` override removes inherited `policy` unless run explicitly also defines `policy`.
    - explicit null/empty values clear that field deterministically.
    - if run explicitly provides both as non-empty, keep both so downstream validation can fail clearly.
    """

    run_sets_policy = "policy" in run_cfg
    run_sets_policy_file = "policy_file" in run_cfg

    if run_sets_policy:
        if run_cfg.get("policy") in (None, {}):
            merged.pop("policy", None)
        if not run_sets_policy_file:
            merged.pop("policy_file", None)

    if run_sets_policy_file:
        raw_policy_file = run_cfg.get("policy_file")
        policy_file_is_empty = raw_policy_file is None or str(raw_policy_file).strip() == ""
        if policy_file_is_empty:
            merged.pop("policy_file", None)
        if not run_sets_policy:
            merged.pop("policy", None)


def _normalize_policy_file_path(*, merged: dict[str, Any], study_config_dir: Path, repo_root: Path) -> None:
    raw_policy_file = merged.get("policy_file")
    if raw_policy_file is None:
        return

    policy_file = Path(str(raw_policy_file))
    if policy_file.is_absolute():
        merged["policy_file"] = str(policy_file.resolve())
        return

    candidate_from_study_dir = (study_config_dir / policy_file).resolve()
    if candidate_from_study_dir.exists():
        merged["policy_file"] = str(candidate_from_study_dir)
        return

    candidate_from_repo_root = (repo_root / policy_file).resolve()
    if candidate_from_repo_root.exists():
        merged["policy_file"] = str(candidate_from_repo_root)
        return

    raise FileNotFoundError(
        "Policy preset file not found for study run. Tried study-config-relative and repo-root-relative paths: "
        f"'{candidate_from_study_dir}' and '{candidate_from_repo_root}'."
    )


def _build_analysis_config(
    *,
    shared_defaults: dict[str, Any],
    run_cfg: dict[str, Any],
    run_output_dir: Path,
    analysis_output_dir: Path,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_dir": str(run_output_dir),
        "output_dir": str(analysis_output_dir),
    }
    for key in ANALYSIS_OPTIONAL_KEYS:
        if key in shared_defaults:
            payload[key] = shared_defaults[key]
        if key in run_cfg:
            payload[key] = run_cfg[key]
    if "notes" in run_cfg:
        payload["notes"] = run_cfg["notes"]
    return payload


def _build_compare_config(
    *,
    cfg: dict[str, Any],
    run_records: list[dict[str, Any]],
    compare_output_dir: Path,
) -> dict[str, Any]:
    compare_cfg = cfg.get("compare", {}) or {}
    payload: dict[str, Any] = {
        "output_dir": str(compare_output_dir),
        "runs": [
            {
                "label": record["label"],
                "run_dir": record["run_dir"],
                "analysis_dir": record.get("analysis_dir"),
            }
            for record in run_records
            if record["status"] == "completed"
        ],
        "notes": str(compare_cfg.get("notes", "")),
    }
    if "compare_sections" in compare_cfg:
        payload["compare_sections"] = list(compare_cfg["compare_sections"])
    if "selected_bucket_features" in compare_cfg:
        payload["selected_bucket_features"] = list(compare_cfg["selected_bucket_features"])
    return payload


def run_study(
    config_path: str | Path,
    *,
    dataset_id_override: str | None = None,
    output_tag: str | None = None,
) -> dict[str, Any]:
    config_path = Path(config_path)
    cfg = _load_yaml(config_path)
    _validate_study_config(cfg)

    repo_root = Path(__file__).resolve().parents[2]
    dataset_registry_cfg = cfg.get("dataset_registry")
    dataset_registry_path: Path | None = None
    dataset_registry: dict[str, Any] = {"datasets": {}}
    if dataset_registry_cfg is not None and str(dataset_registry_cfg).strip() != "":
        raw_registry_path = Path(str(dataset_registry_cfg))
        if raw_registry_path.is_absolute():
            dataset_registry_path = raw_registry_path.resolve()
        else:
            from_study_dir = (config_path.parent / raw_registry_path).resolve()
            dataset_registry_path = from_study_dir if from_study_dir.exists() else (repo_root / raw_registry_path).resolve()
        dataset_registry = _load_dataset_registry(dataset_registry_path)

    for run in cfg.get("runs", []):
        if isinstance(run, dict) and dataset_id_override:
            run["dataset_id"] = dataset_id_override

    base_output_root = resolve_local_path(str(cfg["output_root"]), base_dir=repo_root)
    if output_tag and str(output_tag).strip():
        tag = sanitize_label(str(output_tag).strip())
        output_root = ensure_directory(base_output_root / tag)
    else:
        output_root = ensure_directory(base_output_root)
    runtime_config_dir = ensure_directory(output_root / "runtime_configs")
    dataset_cache_dir = ensure_directory(output_root / "dataset_cache")

    run_tool_path = repo_root / "tools" / "run_experiment.py"
    analyze_tool_path = repo_root / "tools" / "analyze_run.py"
    compare_tool_path = repo_root / "tools" / "compare_runs.py"

    shared_defaults = dict(cfg.get("shared_defaults", {}))
    run_records: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    baseline_label = str(cfg["runs"][0]["label"])

    seen_safe_labels: dict[str, str] = {}
    for run in cfg["runs"]:
        raw_label = str(run["label"])
        safe_label = sanitize_label(raw_label)
        existing = seen_safe_labels.get(safe_label)
        if existing is not None and existing != raw_label:
            raise ValueError(
                "Run label collision after sanitization: "
                f"'{existing}' and '{raw_label}' both map to '{safe_label}'. "
                "Use unique labels that remain unique after sanitization."
            )
        seen_safe_labels[safe_label] = raw_label

    for run in cfg["runs"]:
        label = str(run["label"])
        safe_label = sanitize_label(label)
        run_output_dir = ensure_directory(output_root / "runs" / safe_label)
        analysis_output_dir = ensure_directory(output_root / "analysis" / safe_label)

        record: dict[str, Any] = {
            "label": label,
            "run_dir": str(run_output_dir),
            "analysis_dir": None,
            "status": "pending",
            "analyze_after_run": bool(run.get("analyze_after_run", shared_defaults.get("analyze_after_run", False))),
            "warnings": [],
            "errors": [],
        }

        try:
            run_payload = _build_run_experiment_config(
                shared_defaults=shared_defaults,
                run_cfg=run,
                run_output_dir=run_output_dir,
                repo_root=repo_root,
                study_config_dir=config_path.parent.resolve(),
                dataset_registry=dataset_registry,
                dataset_registry_path=dataset_registry_path,
                dataset_cache_dir=dataset_cache_dir,
            )
            run_cfg_path = runtime_config_dir / f"run_{safe_label}.yaml"
            _write_yaml(run_cfg_path, run_payload)

            run_proc = _run_cli(run_tool_path, run_cfg_path, repo_root)
            if run_proc.returncode != 0:
                record["status"] = "run_failed"
                err = (run_proc.stderr or run_proc.stdout or "").strip()
                message = f"run '{label}' failed during run_experiment: {err}"
                record["errors"].append(message)
                errors.append(message)
                run_records.append(record)
                continue

            record["status"] = "completed"

            if record["analyze_after_run"]:
                analysis_payload = _build_analysis_config(
                    shared_defaults=shared_defaults,
                    run_cfg=run,
                    run_output_dir=run_output_dir,
                    analysis_output_dir=analysis_output_dir,
                )
                analysis_cfg_path = runtime_config_dir / f"analysis_{safe_label}.yaml"
                _write_yaml(analysis_cfg_path, analysis_payload)

                analysis_proc = _run_cli(analyze_tool_path, analysis_cfg_path, repo_root)
                if analysis_proc.returncode != 0:
                    record["status"] = "analysis_failed"
                    err = (analysis_proc.stderr or analysis_proc.stdout or "").strip()
                    message = f"run '{label}' failed during analyze_run: {err}"
                    record["errors"].append(message)
                    errors.append(message)
                else:
                    record["analysis_dir"] = str(analysis_output_dir)
        except Exception as exc:  # noqa: BLE001
            record["status"] = "config_error"
            message = f"run '{label}' config/setup error: {exc}"
            record["errors"].append(message)
            errors.append(message)

        run_records.append(record)

    compare_generated = False
    compare_dir: str | None = None
    compare_cfg = cfg.get("compare", {}) or {}
    compare_enabled = bool(compare_cfg.get("enabled", False))

    completed_runs = [record for record in run_records if record["status"] == "completed"]
    baseline_completed = any(record["label"] == baseline_label and record["status"] == "completed" for record in run_records)
    compare_skipped_reason: str | None = None

    if compare_enabled:
        if len(completed_runs) < 2:
            compare_skipped_reason = "fewer_than_two_completed_runs"
            warnings.append("Compare was enabled but skipped because fewer than two completed runs were available.")
        elif not baseline_completed:
            compare_skipped_reason = "configured_baseline_not_completed"
            warnings.append(
                "Compare was enabled but skipped because the configured baseline run "
                f"'{baseline_label}' did not complete successfully."
            )
        else:
            compare_output_dir = ensure_directory(output_root / "compare")
            compare_payload = _build_compare_config(cfg=cfg, run_records=run_records, compare_output_dir=compare_output_dir)
            compare_cfg_path = runtime_config_dir / "compare.yaml"
            _write_yaml(compare_cfg_path, compare_payload)

            compare_proc = _run_cli(compare_tool_path, compare_cfg_path, repo_root)
            if compare_proc.returncode != 0:
                err = (compare_proc.stderr or compare_proc.stdout or "").strip()
                errors.append(f"compare step failed: {err}")
            else:
                compare_generated = True
                compare_dir = str(compare_output_dir)

    metadata = {
        "study_name": str(cfg["study_name"]),
        "study_config": str(config_path.resolve()),
        "dataset_registry": str(dataset_registry_path) if dataset_registry_path else None,
        "dataset_id_override": str(dataset_id_override) if dataset_id_override else None,
        "output_root": str(output_root.resolve()),
        "baseline_run_label": baseline_label,
        "run_labels": [str(run.get("label", "")) for run in cfg.get("runs", [])],
        "runs": run_records,
        "compare": {
            "enabled": compare_enabled,
            "generated": compare_generated,
            "output_dir": compare_dir,
            "baseline_completed": baseline_completed,
            "skipped_reason": compare_skipped_reason,
            "selected_bucket_features": list(compare_cfg.get("selected_bucket_features", [])),
        },
        "warnings": warnings,
        "errors": errors,
        "notes": str(cfg.get("notes", "")),
    }

    metadata_path = output_root / "study_metadata.yaml"
    _write_yaml(metadata_path, metadata)

    summary_lines = [
        "# Study Summary",
        "",
        f"- study_name: {metadata['study_name']}",
        f"- baseline_run_label: {metadata['baseline_run_label']}",
        f"- output_root: {metadata['output_root']}",
        "",
        "## Runs",
        "",
    ]
    for record in run_records:
        summary_lines.append(f"- label: {record['label']}")
        summary_lines.append(f"  - status: {record['status']}")
        summary_lines.append(f"  - run_dir: {record['run_dir']}")
        summary_lines.append(f"  - analysis_dir: {record.get('analysis_dir')}")
        if record["errors"]:
            summary_lines.append("  - errors:")
            summary_lines.extend([f"    - {line}" for line in record["errors"]])

    summary_lines.extend(["", "## Compare", ""])
    summary_lines.append(f"- enabled: {compare_enabled}")
    summary_lines.append(f"- generated: {compare_generated}")
    summary_lines.append(f"- output_dir: {compare_dir}")
    summary_lines.append(f"- baseline_completed: {baseline_completed}")
    summary_lines.append(f"- skipped_reason: {compare_skipped_reason}")

    summary_lines.extend(["", "## Warnings", ""])
    if warnings:
        summary_lines.extend([f"- {line}" for line in warnings])
    else:
        summary_lines.append("- None")

    summary_lines.extend(["", "## Errors", ""])
    if errors:
        summary_lines.extend([f"- {line}" for line in errors])
    else:
        summary_lines.append("- None")

    (output_root / "study_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    return metadata
