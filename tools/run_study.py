#!/usr/bin/env python3
"""Config-driven study runner for orchestrating run/analyze/compare flows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.orchestration import run_study


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run study-level orchestration across multiple experiment runs.")
    parser.add_argument("--config", required=True, help="Path to YAML study config.")
    parser.add_argument(
        "--dataset-id",
        default=None,
        help="Optional dataset_id override applied to all runs (for cloud dispatch overrides).",
    )
    parser.add_argument(
        "--output-tag",
        default=None,
        help="Optional output tag; when set, writes under <output_root>/<sanitized_tag>/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = run_study(args.config, dataset_id_override=args.dataset_id, output_tag=args.output_tag)
    print(
        "Study run completed:",
        f"study={metadata['study_name']}",
        f"runs={len(metadata['runs'])}",
        f"errors={len(metadata['errors'])}",
        f"warnings={len(metadata['warnings'])}",
        f"compare_generated={metadata['compare']['generated']}",
        f"out={metadata['output_root']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
