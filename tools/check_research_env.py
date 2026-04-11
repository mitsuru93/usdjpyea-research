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
    runner.check(out.parent.exists(), f"{label} output parent exists: {out.parent}", f"{label} output parent missing: {out.parent}")


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
    required = ["study_name", "output_root", "shared_defaults", "runs"]
    missing = [key for key in required if key not in cfg]
    runner.check(not missing, "Study config required top-level fields present", f"Study config missing fields: {missing}")

    if "output_root" in cfg:
        output_root = _resolve(str(cfg["output_root"]))
        runner.check(
            output_root.parent.exists(),
            f"Study output_root parent exists: {output_root.parent}",
            f"Study output_root parent missing: {output_root.parent}",
        )

    runs = cfg.get("runs", [])
    runner.check(isinstance(runs, list) and bool(runs), "Study config has non-empty runs list", "Study config requires non-empty runs list")
    if isinstance(runs, list):
        for idx, run in enumerate(runs):
            is_map = isinstance(run, dict)
            runner.check(is_map, f"Study runs[{idx}] is a mapping", f"Study runs[{idx}] must be a mapping")
            if not is_map:
                continue
            has_fields = "label" in run and "input_csv" in run
            runner.check(has_fields, f"Study runs[{idx}] has label + input_csv", f"Study runs[{idx}] missing label/input_csv")
            if "input_csv" in run:
                input_csv = _resolve(str(run["input_csv"]))
                runner.check(
                    input_csv.exists(),
                    f"Study runs[{idx}] input CSV found: {input_csv}",
                    f"Study runs[{idx}] input CSV missing: {input_csv}",
                )
            _check_policy_reference(
                runner,
                policy=run.get("policy"),
                policy_file=run.get("policy_file"),
                context_label=f"Study runs[{idx}]",
                config_dir=cfg_path.parent,
            )

    shared_defaults = cfg.get("shared_defaults", {})
    if isinstance(shared_defaults, dict):
        _check_policy_reference(
            runner,
            policy=shared_defaults.get("policy"),
            policy_file=shared_defaults.get("policy_file"),
            context_label="Study shared_defaults",
            config_dir=cfg_path.parent,
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
