#!/usr/bin/env python3
"""Lightweight smoke test for simulator v1 pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = REPO_ROOT / "research" / "data_sample" / "usdjpy_m1_tiny_sample.csv"
OUTPUT_DIR = REPO_ROOT / "research" / "reports" / "smoke_test_v1"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "run_candidate_sim.py"),
        "--input-csv",
        str(SAMPLE_CSV),
        "--output-dir",
        str(OUTPUT_DIR),
        "--max-holding-bars",
        "20",
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
