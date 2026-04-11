#!/usr/bin/env python3
"""Lightweight smoke test for config-driven candidate experiment pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "experiments" / "smoke_test_candidate_run.yaml"
OUTPUT_DIR = REPO_ROOT / "research" / "reports" / "smoke_test_candidate_run"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "run_experiment.py"),
        "--config",
        str(CONFIG_PATH),
    ]
    subprocess.run(cmd, check=True)

    required = [
        "candidates.csv",
        "summary_overall.csv",
        "summary_by_month.csv",
        "summary_by_session.csv",
        "summary_by_family.csv",
        "run_metadata.yaml",
    ]
    missing = [name for name in required if not (OUTPUT_DIR / name).exists()]
    if missing:
        raise RuntimeError(f"Smoke test failed, missing outputs: {missing}")

    print("Smoke test passed. Outputs written to", OUTPUT_DIR)


if __name__ == "__main__":
    main()
