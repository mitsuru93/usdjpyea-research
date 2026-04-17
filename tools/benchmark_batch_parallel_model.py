#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _expand(spec_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "expand_batch.py"), "--batch-spec", str(spec_path)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    line = proc.stdout.strip().splitlines()[-1]
    m_runtime = re.search(r"runtime_dir=(.+)$", line)
    if not m_runtime:
        raise RuntimeError(f"runtime_dir parse failed: {line}")
    runtime_dir = Path(m_runtime.group(1).strip())
    manifest = yaml.safe_load((runtime_dir / "batch_manifest.yaml").read_text(encoding="utf-8")) or {}
    shards = manifest.get("shards", [])
    runs_per_shard = [len(shard.get("runs", [])) for shard in shards]
    return {
        "line": line,
        "runtime_dir": str(runtime_dir),
        "shard_count": len(shards),
        "runs_per_shard": runs_per_shard,
        "total_runs": sum(runs_per_shard),
    }


def _schedule_duration(shard_durations: list[float], workers: int) -> tuple[float, float]:
    lanes = [0.0 for _ in range(workers)]
    if not shard_durations:
        return 0.0, 0.0
    first_wave = max(shard_durations[:workers])
    for dur in sorted(shard_durations, reverse=True):
        lane_idx = min(range(workers), key=lambda i: lanes[i])
        lanes[lane_idx] += dur
    return first_wave, max(lanes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--miss-sec", type=float, required=True)
    parser.add_argument("--hit-sec", type=float, required=True)
    parser.add_argument("--output-dir", default="docs/benchmarks/batch_parallel_model")
    args = parser.parse_args()

    output_dir = (REPO_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    specs = {
        "lite_sh2_v1": REPO_ROOT / "configs/batches/batch_rvtr_policy_threshold_sweep_lite_sh2_v1.yaml",
        "lite_sh1_v1": REPO_ROOT / "configs/batches/batch_rvtr_policy_threshold_sweep_lite_sh1_v1.yaml",
    }

    result = {
        "assumptions": {
            "workers": args.workers,
            "miss_sec": args.miss_sec,
            "hit_sec": args.hit_sec,
            "shard_duration_model": "duration = miss + hit * (runs_in_shard - 1)",
        },
        "specs": {},
    }

    for key, spec_path in specs.items():
        expanded = _expand(spec_path)
        durations = [args.miss_sec + (runs - 1) * args.hit_sec for runs in expanded["runs_per_shard"]]
        first_wave, total = _schedule_duration(durations, args.workers)
        variance = 0.0
        if durations:
            mean = sum(durations) / len(durations)
            variance = sum((d - mean) ** 2 for d in durations) / len(durations)
        cache_hit_rate = 0.0
        if expanded["total_runs"] > 0:
            cache_hit_rate = max(0.0, (expanded["total_runs"] - expanded["shard_count"]) / expanded["total_runs"])

        result["specs"][key] = {
            **expanded,
            "modeled_shard_durations_sec": durations,
            "modeled_first_wave_completion_sec": first_wave,
            "modeled_total_completion_sec": total,
            "modeled_shard_duration_variance": variance,
            "modeled_cache_hit_rate": cache_hit_rate,
        }

    (output_dir / "batch_parallel_model.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# Batch parallel model benchmark",
        "",
        "This is a model-based benchmark using measured miss/hit single-run times.",
        "",
        f"- workers (max-parallel): {args.workers}",
        f"- per-run miss sec: {args.miss_sec:.6f}",
        f"- per-run hit sec: {args.hit_sec:.6f}",
        "",
    ]
    for key, payload in result["specs"].items():
        md_lines.extend(
            [
                f"## {key}",
                f"- shard_count: {payload['shard_count']}",
                f"- total_runs: {payload['total_runs']}",
                f"- modeled first wave sec: {payload['modeled_first_wave_completion_sec']:.6f}",
                f"- modeled total completion sec: {payload['modeled_total_completion_sec']:.6f}",
                f"- modeled shard duration variance: {payload['modeled_shard_duration_variance']:.6f}",
                f"- modeled cache hit rate: {payload['modeled_cache_hit_rate']:.6f}",
                "",
            ]
        )
    (output_dir / "batch_parallel_model.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(f"wrote {output_dir / 'batch_parallel_model.json'}")
    print(f"wrote {output_dir / 'batch_parallel_model.md'}")


if __name__ == "__main__":
    main()
