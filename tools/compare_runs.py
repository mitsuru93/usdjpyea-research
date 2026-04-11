#!/usr/bin/env python3
"""Config-driven multi-run comparison across completed run artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.comparison import DEFAULT_COMPARE_SECTIONS, compare_runs_from_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare completed run artifacts side by side.")
    parser.add_argument("--config", required=True, help="Path to YAML compare config.")
    return parser.parse_args()


def _load_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    required = ["output_dir", "runs"]
    missing = [key for key in required if key not in cfg]
    if missing:
        raise ValueError(f"Compare config missing required fields: {missing}")

    runs = list(cfg.get("runs", []))
    if not runs:
        raise ValueError("Compare config requires at least one run entry.")

    for idx, run in enumerate(runs):
        if "label" not in run or "run_dir" not in run:
            raise ValueError(f"runs[{idx}] must include label and run_dir")

    cfg["compare_sections"] = list(cfg.get("compare_sections", DEFAULT_COMPARE_SECTIONS))
    cfg["selected_bucket_features"] = list(cfg.get("selected_bucket_features", []))
    cfg["notes"] = str(cfg.get("notes", ""))
    return cfg


def main() -> None:
    args = parse_args()
    cfg = _load_config(args.config)
    result = compare_runs_from_config(cfg)

    print(
        "Run comparison completed:",
        f"baseline={result['baseline_label']}",
        f"files={len(result['generated_files'])}",
        f"warnings={len(result['warnings'])}",
        f"out={result['output_dir']}",
    )


if __name__ == "__main__":
    main()
