#!/usr/bin/env python3
"""Lightweight local environment + config checks for research CLIs."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.io.dataset_resolver import validate_dataset_entry

TIMING_MODE_VALUES = {"baseline_touch", "rv_close_confirm", "all_close"}


class CheckRunner:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passes: list[str] = []

    def check(self, condition: bool, ok: str, fail: str) -> None:
        if condition:
            self.passes.append(ok)
            print(f"[PASS] {ok}")
        else:
            self.failures.append(fail)
            print(f"[FAIL] {fail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lightweight environment + config checks for local research runs.")
    parser.add_argument("--study-config", help="Optional study config YAML path.")
    parser.add_argument("--experiment-config", help="Optional experiment config YAML path.")
    parser.add_argument("--analysis-config", help="Optional analysis config YAML path.")
    parser.add_argument("--compare-config", help="Optional compare config YAML path.")
    return parser.parse_args()


def _resolve(path_text: str | Path) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _load_yaml(path_text: str | Path) -> dict[str, Any]:
    path = _resolve(path_text)
    yaml = importlib.import_module("yaml")
    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping-style YAML at {path}")
    return payload


def _load_dataset_registry(cfg: dict[str, Any], cfg_dir: Path) -> tuple[dict[str, Any], Path | None]:
    raw_path = cfg.get("dataset_registry")
    if raw_path is None or str(raw_path).strip() == "":
        return {"datasets": {}}, None

    path = Path(str(raw_path))
    if not path.is_absolute():
        cfg_relative = (cfg_dir / path).resolve()
        if cfg_relative.exists():
            path = cfg_relative
        else:
            path = (REPO_ROOT / path).resolve()
    else:
        path = path.resolve()

    payload = _load_yaml(path)
    datasets = payload.get("datasets", {})
    if not isinstance(datasets, dict):
        raise ValueError(f"Dataset registry must define mapping-style 'datasets': {path}")
    return payload, path


def _resolve_policy_preset_path(raw_path: str | Path, *, config_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()

    config_relative = (config_dir / path).resolve()
    if config_relative.exists():
        return config_relative

    return (REPO_ROOT / path).resolve()


def _check_policy_reference(
    runner: CheckRunner,
    *,
    policy: Any,
    policy_file: Any,
    context_label: str,
    config_dir: Path,
) -> None:
    has_inline = policy not in (None, {})
    has_file = policy_file is not None and str(policy_file).strip() != ""

    runner.check(
        not (has_inline and has_file),
        f"{context_label} policy reference uses either inline policy or policy_file (not both)",
        f"{context_label} policy reference cannot define both 'policy' and 'policy_file'",
    )

    if not has_file:
        return

    resolved = _resolve_policy_preset_path(str(policy_file), config_dir=config_dir)
    runner.check(
        resolved.exists(),
        f"{context_label} policy_file exists: {resolved}",
        f"{context_label} policy_file missing: {resolved}",
    )
    if not resolved.exists():
        return

    try:
        payload = _load_yaml(resolved)
        is_mapping = isinstance(payload, dict)
        runner.check(
            is_mapping,
            f"{context_label} policy_file loads as mapping YAML: {resolved}",
            f"{context_label} policy_file must be mapping-style YAML: {resolved}",
        )
    except Exception as exc:  # noqa: BLE001
        runner.check(False, "", f"{context_label} policy_file could not be loaded: {resolved} ({exc})")


def _normalize_merged_policy_fields(*, merged: dict[str, Any], run_cfg: dict[str, Any]) -> None:
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


def _check_imports(runner: CheckRunner) -> None:
    for mod in ["pandas", "yaml"]:
        try:
            importlib.import_module(mod)
            runner.check(True, f"Python package import available: {mod}", "")
        except Exception as exc:  # noqa: BLE001
            runner.check(False, "", f"Python package import failed: {mod} ({exc})")

    try:
        importlib.import_module("research")
        importlib.import_module("research.orchestration.study_runner")
        importlib.import_module("research.analysis")
        importlib.import_module("research.comparison")
        runner.check(True, "Repo-root imports are available (research package)", "")
    except Exception as exc:  # noqa: BLE001
        runner.check(False, "", f"Repo-root imports failed: {exc}")


def _check_output_parent(runner: CheckRunner, output_dir: str, label: str) -> None:
    out = _resolve(output_dir)
    parent_ready = out.parent.exists() or out.parent.parent.exists()
    runner.check(
        parent_ready,
        f"{label} output parent path is creatable from repo context: {out.parent}",
        f"{label} output parent path missing (non-creatable): {out.parent}",
    )


def _check_experiment_config(runner: CheckRunner, path_text: str) -> None:
    cfg_path = _resolve(path_text)
    runner.check(cfg_path.exists(), f"Experiment config exists: {cfg_path}", f"Experiment config missing: {cfg_path}")
    if not cfg_path.exists():
        return

    try:
        cfg = _load_yaml(cfg_path)
    except Exception as exc:  # noqa: BLE001
        runner.check(False, "", f"Experiment config could not be loaded: {cfg_path} ({exc})")
        return
    required = ["input_csv", "output_dir", "input_timezone_mode", "max_holding_bars", "symbol", "timeframe"]
    missing = [key for key in required if key not in cfg]
    runner.check(not missing, "Experiment config required top-level fields present", f"Experiment config missing fields: {missing}")

    if "input_csv" in cfg:
        input_csv = _resolve(str(cfg["input_csv"]))
        runner.check(input_csv.exists(), f"Experiment input CSV found: {input_csv}", f"Experiment input CSV missing: {input_csv}")
    if "output_dir" in cfg:
        _check_output_parent(runner, str(cfg["output_dir"]), "Experiment")
    _check_policy_reference(
        runner,
        policy=cfg.get("policy"),
        policy_file=cfg.get("policy_file"),
        context_label="Experiment config",
        config_dir=cfg_path.parent,
    )
    if "timing_mode" in cfg:
        timing_mode = str(cfg.get("timing_mode", "")).strip().lower()
        runner.check(
            timing_mode in TIMING_MODE_VALUES,
            f"Experiment timing_mode is supported: {timing_mode}",
            f"Experiment timing_mode unsupported: {timing_mode}; allowed={sorted(TIMING_MODE_VALUES)}",
        )


def _check_analysis_config(runner: CheckRunner, path_text: str) -> None:
    cfg_path = _resolve(path_text)
    runner.check(cfg_path.exists(), f"Analysis config exists: {cfg_path}", f"Analysis config missing: {cfg_path}")
    if not cfg_path.exists():
        return

    try:
        cfg = _load_yaml(cfg_path)
    except Exception as exc:  # noqa: BLE001
        runner.check(False, "", f"Analysis config could not be loaded: {cfg_path} ({exc})")
        return
    required = ["run_dir", "output_dir"]
    missing = [key for key in required if key not in cfg]
    runner.check(not missing, "Analysis config required top-level fields present", f"Analysis config missing fields: {missing}")

    if "run_dir" in cfg:
        run_dir = _resolve(str(cfg["run_dir"]))
        runner.check(run_dir.exists(), f"Analysis run_dir exists: {run_dir}", f"Analysis run_dir missing: {run_dir}")
    if "output_dir" in cfg:
        _check_output_parent(runner, str(cfg["output_dir"]), "Analysis")


def _check_compare_config(runner: CheckRunner, path_text: str) -> None:
    cfg_path = _resolve(path_text)
    runner.check(cfg_path.exists(), f"Compare config exists: {cfg_path}", f"Compare config missing: {cfg_path}")
    if not cfg_path.exists():
        return

    try:
        cfg = _load_yaml(cfg_path)
    except Exception as exc:  # noqa: BLE001
        runner.check(False, "", f"Compare config could not be loaded: {cfg_path} ({exc})")
        return
    required = ["output_dir", "runs"]
    missing = [key for key in required if key not in cfg]
    runner.check(not missing, "Compare config required top-level fields present", f"Compare config missing fields: {missing}")

    runs = list(cfg.get("runs", []))
    runner.check(bool(runs), "Compare config has at least one run", "Compare config requires at least one run entry")
    for idx, run in enumerate(runs):
        ok = isinstance(run, dict) and "label" in run and "run_dir" in run
        runner.check(ok, f"Compare runs[{idx}] has label + run_dir", f"Compare runs[{idx}] must include label + run_dir")
        if not ok:
            continue
        run_dir = _resolve(str(run["run_dir"]))
        runner.check(run_dir.exists(), f"Compare run_dir exists for '{run['label']}': {run_dir}", f"Compare run_dir missing for '{run['label']}': {run_dir}")
        if run.get("analysis_dir"):
            analysis_dir = _resolve(str(run["analysis_dir"]))
            runner.check(
                analysis_dir.exists(),
                f"Compare analysis_dir exists for '{run['label']}': {analysis_dir}",
                f"Compare analysis_dir missing for '{run['label']}': {analysis_dir}",
            )

    if "output_dir" in cfg:
        _check_output_parent(runner, str(cfg["output_dir"]), "Compare")


def _check_study_config(runner: CheckRunner, path_text: str) -> None:
    cfg_path = _resolve(path_text)
    runner.check(cfg_path.exists(), f"Study config exists: {cfg_path}", f"Study config missing: {cfg_path}")
    if not cfg_path.exists():
        return

    try:
        cfg = _load_yaml(cfg_path)
    except Exception as exc:  # noqa: BLE001
        runner.check(False, "", f"Study config could not be loaded: {cfg_path} ({exc})")
        return

    dataset_registry: dict[str, Any] = {"datasets": {}}
    try:
        dataset_registry, dataset_registry_path = _load_dataset_registry(cfg, cfg_path.parent)
        if dataset_registry_path is not None:
            runner.check(
                dataset_registry_path.exists(),
                f"Study dataset registry exists: {dataset_registry_path}",
                f"Study dataset registry missing: {dataset_registry_path}",
            )
    except Exception as exc:  # noqa: BLE001
        runner.check(False, "", f"Study dataset registry invalid: {exc}")
        dataset_registry = {"datasets": {}}
    required = ["study_name", "output_root", "shared_defaults", "runs"]
    missing = [key for key in required if key not in cfg]
    runner.check(not missing, "Study config required top-level fields present", f"Study config missing fields: {missing}")

    if "output_root" in cfg:
        output_root = _resolve(str(cfg["output_root"]))
        output_parent_ready = output_root.parent.exists() or output_root.parent.parent.exists()
        runner.check(
            output_parent_ready,
            f"Study output_root parent path is creatable: {output_root.parent}",
            f"Study output_root parent missing (non-creatable): {output_root.parent}",
        )

    runs = cfg.get("runs", [])
    runner.check(isinstance(runs, list) and bool(runs), "Study config has non-empty runs list", "Study config requires non-empty runs list")
    shared_defaults = cfg.get("shared_defaults", {})
    shared_has_input_csv = isinstance(shared_defaults, dict) and str(shared_defaults.get("input_csv", "")).strip() != ""
    shared_has_dataset_id = isinstance(shared_defaults, dict) and str(shared_defaults.get("dataset_id", "")).strip() != ""
    if isinstance(runs, list):
        for idx, run in enumerate(runs):
            is_map = isinstance(run, dict)
            runner.check(is_map, f"Study runs[{idx}] is a mapping", f"Study runs[{idx}] must be a mapping")
            if not is_map:
                continue
            has_label = "label" in run
            has_input_csv = str(run.get("input_csv", "")).strip() != ""
            has_dataset_id = str(run.get("dataset_id", "")).strip() != ""
            runner.check(has_label, f"Study runs[{idx}] has label", f"Study runs[{idx}] missing label")
            runner.check(
                has_input_csv or has_dataset_id or shared_has_input_csv or shared_has_dataset_id,
                f"Study runs[{idx}] has input_csv or dataset_id",
                f"Study runs[{idx}] missing both input_csv and dataset_id",
            )
            if has_input_csv:
                input_csv = _resolve(str(run["input_csv"]))
                runner.check(
                    input_csv.exists(),
                    f"Study runs[{idx}] input CSV found: {input_csv}",
                    f"Study runs[{idx}] input CSV missing: {input_csv}",
                )
            if has_dataset_id:
                dataset_id = str(run["dataset_id"]).strip()
                dataset_map = dataset_registry.get("datasets", {})
                dataset_entry = dataset_map.get(dataset_id) if isinstance(dataset_map, dict) else None
                runner.check(
                    isinstance(dataset_entry, dict),
                    f"Study runs[{idx}] dataset_id found in registry: {dataset_id}",
                    f"Study runs[{idx}] dataset_id missing in registry: {dataset_id}",
                )
                if isinstance(dataset_entry, dict):
                    _check_dataset_entry(
                        runner,
                        dataset_id=dataset_id,
                        dataset_entry=dataset_entry,
                        context_label=f"Study runs[{idx}]",
                    )
            elif not has_input_csv and shared_has_dataset_id:
                dataset_id = str(shared_defaults.get("dataset_id", "")).strip()
                dataset_map = dataset_registry.get("datasets", {})
                dataset_entry = dataset_map.get(dataset_id) if isinstance(dataset_map, dict) else None
                runner.check(
                    isinstance(dataset_entry, dict),
                    f"Study runs[{idx}] shared dataset_id found in registry: {dataset_id}",
                    f"Study runs[{idx}] shared dataset_id missing in registry: {dataset_id}",
                )
                if isinstance(dataset_entry, dict):
                    _check_dataset_entry(
                        runner,
                        dataset_id=dataset_id,
                        dataset_entry=dataset_entry,
                        context_label=f"Study runs[{idx}]",
                    )
            _check_policy_reference(
                runner,
                policy=run.get("policy"),
                policy_file=run.get("policy_file"),
                context_label=f"Study runs[{idx}]",
                config_dir=cfg_path.parent,
            )

    if isinstance(shared_defaults, dict):
        _check_policy_reference(
            runner,
            policy=shared_defaults.get("policy"),
            policy_file=shared_defaults.get("policy_file"),
            context_label="Study shared_defaults",
            config_dir=cfg_path.parent,
        )

        if isinstance(runs, list):
            for idx, run in enumerate(runs):
                if not isinstance(run, dict):
                    continue
                merged = dict(shared_defaults)
                merged.update(run)
                _normalize_merged_policy_fields(merged=merged, run_cfg=run)
                _check_policy_reference(
                    runner,
                    policy=merged.get("policy"),
                    policy_file=merged.get("policy_file"),
                    context_label=f"Study merged runs[{idx}]",
                    config_dir=cfg_path.parent,
                )


def _check_dataset_entry(runner: CheckRunner, *, dataset_id: str, dataset_entry: dict[str, Any], context_label: str) -> None:
    errors = validate_dataset_entry(dataset_id, dataset_entry)
    runner.check(
        not errors,
        f"{context_label} dataset entry for '{dataset_id}' passes provider validation",
        f"{context_label} dataset entry invalid for '{dataset_id}': {'; '.join(errors)}",
    )
    if errors:
        return

    provider = str(dataset_entry.get("provider", "repo_path")).strip() or "repo_path"
    if provider == "repo_path":
        dataset_path = _resolve(str(dataset_entry["path"]))
        runner.check(
            dataset_path.exists(),
            f"{context_label} repo_path dataset file found: {dataset_path}",
            f"{context_label} repo_path dataset file missing: {dataset_path}",
        )


def main() -> None:
    args = parse_args()
    runner = CheckRunner()

    print(f"[INFO] Repo root: {REPO_ROOT}")
    _check_imports(runner)

    try:
        if args.study_config:
            _check_study_config(runner, args.study_config)
        if args.experiment_config:
            _check_experiment_config(runner, args.experiment_config)
        if args.analysis_config:
            _check_analysis_config(runner, args.analysis_config)
        if args.compare_config:
            _check_compare_config(runner, args.compare_config)
    except Exception as exc:  # noqa: BLE001
        runner.failures.append(str(exc))
        print(f"[FAIL] Exception during checks: {exc}")

    print("\nSummary:")
    print(f"  PASS: {len(runner.passes)}")
    print(f"  FAIL: {len(runner.failures)}")

    if runner.failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
