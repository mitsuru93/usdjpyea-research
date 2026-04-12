#!/usr/bin/env python3
"""Single-dispatch batch runner wrapper (cloud workflow uses expand + matrix + review steps)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Expand and execute all batch shards sequentially, then build review artifacts.")
    p.add_argument("--batch-spec", required=True)
    p.add_argument("--dataset-id", default=None)
    p.add_argument("--output-tag", default=None)
    p.add_argument("--review-issue-number", default=None)
    return p.parse_args()


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    import yaml

    spec = yaml.safe_load(Path(args.batch_spec).read_text(encoding="utf-8")) or {}
    batch_id = str(spec.get("batch_id", "")).strip()
    if not batch_id:
        raise ValueError("batch_spec must include batch_id")

    _run(
        [
            sys.executable,
            "tools/expand_batch.py",
            "--batch-spec",
            args.batch_spec,
            *( ["--dataset-id", args.dataset_id] if args.dataset_id else [] ),
            *( ["--output-tag", args.output_tag] if args.output_tag else [] ),
        ],
        cwd=repo_root,
    )

    # deterministic runtime location mirrors expand_batch default.
    runtime_manifest = repo_root / "research" / "reports" / "batches" / "runtime" / batch_id / "batch_manifest.yaml"

    manifest = yaml.safe_load(runtime_manifest.read_text(encoding="utf-8")) or {}
    for shard in manifest.get("shards", []):
        _run([sys.executable, "tools/run_study.py", "--config", str(shard["study_config"])], cwd=repo_root)

    _run(
        [
            sys.executable,
            "tools/review_batch.py",
            "--batch-manifest",
            str(runtime_manifest),
            *( ["--review-issue-number", args.review_issue_number] if args.review_issue_number else [] ),
        ],
        cwd=repo_root,
    )


if __name__ == "__main__":
    main()
