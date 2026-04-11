"""Study-level orchestrator for multi-run experiment/analysis/compare workflows."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

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

    for idx, run in enumerate(runs):
        if not isinstance(run, dict):
            raise ValueError(f"runs[{idx}] must be a mapping")
        if "label" not in run or "input_csv" not in run:
            raise ValueError(f"runs[{idx}] must include at least 'label' and 'input_csv'")


def _build_run_experiment_config(
    *,
    shared_defaults: dict[str, Any],
    run_cfg: dict[str, Any],
    run_output_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    merged = dict(shared_defaults)
    merged.update(run_cfg)

    merged["output_dir"] = str(run_output_dir)
    merged["input_csv"] = str(resolve_local_path(str(merged["input_csv"]), base_dir=repo_root))

    missing = [key for key in RUN_REQUIRED_KEYS if key not in merged]
    if missing:
        raise ValueError(f"run '{run_cfg.get('label', '')}' missing required run fields after merge: {missing}")

    return {key: merged[key] for key in [*RUN_REQUIRED_KEYS, "input_csv", "output_dir", "notes"] if key in merged}


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


def run_study(config_path: str | Path) -> dict[str, Any]:
    config_path = Path(config_path)
    cfg = _load_yaml(config_path)
    _validate_study_config(cfg)

    repo_root = Path(__file__).resolve().parents[2]

    output_root = ensure_directory(resolve_local_path(str(cfg["output_root"]), base_dir=repo_root))
    runtime_config_dir = ensure_directory(output_root / "runtime_configs")

    run_tool_path = repo_root / "tools" / "run_experiment.py"
    analyze_tool_path = repo_root / "tools" / "analyze_run.py"
    compare_tool_path = repo_root / "tools" / "compare_runs.py"

    shared_defaults = dict(cfg.get("shared_defaults", {}))
    run_records: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

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

    if compare_enabled:
        if len(completed_runs) < 2:
            warnings.append("Compare was enabled but skipped because fewer than two completed runs were available.")
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
        "output_root": str(output_root.resolve()),
        "baseline_run_label": str(cfg["runs"][0]["label"]),
        "run_labels": [str(run.get("label", "")) for run in cfg.get("runs", [])],
        "runs": run_records,
        "compare": {
            "enabled": compare_enabled,
            "generated": compare_generated,
            "output_dir": compare_dir,
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
