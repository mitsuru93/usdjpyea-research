#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "run_research_batch.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    run_shards = workflow["jobs"]["run-shards"]
    assert run_shards["runs-on"] == ["self-hosted", "linux", "x64"]
    assert int(run_shards["strategy"]["max-parallel"]) == 4

    steps = run_shards["steps"]
    step_names = [s.get("name", "") for s in steps]
    assert "Run shard study" in step_names
    assert "Review shard timing study" in step_names

    run_step = next(s for s in steps if s.get("name") == "Run shard study")
    review_step = next(s for s in steps if s.get("name") == "Review shard timing study")

    run_cmd = str(run_step.get("run", ""))
    review_cmd = str(review_step.get("run", ""))
    assert "python -u tools/run_study.py" in run_cmd
    assert "/usr/bin/time -v" in run_cmd
    assert "start_utc=" in run_cmd and "end_utc=" in run_cmd

    assert "python -u tools/review_timing_study.py" in review_cmd
    assert "/usr/bin/time -v" in review_cmd
    assert "start_utc=" in review_cmd and "end_utc=" in review_cmd

    for spec_name in [
        "batch_rvtr_policy_threshold_sweep_lite_v1.yaml",
        "batch_rvtr_policy_threshold_sweep_lite_sh2_v1.yaml",
        "batch_rvtr_policy_threshold_sweep_lite_sh1_v1.yaml",
        "batch_rvtr_policy_total_score_narrow_v1.yaml",
        "batch_rvtr_policy_total_score_narrow_sh1_v1.yaml",
    ]:
        spec_path = REPO_ROOT / "configs" / "batches" / spec_name
        payload = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict) and "shard_size" in payload

    sh1 = yaml.safe_load((REPO_ROOT / "configs" / "batches" / "batch_rvtr_policy_threshold_sweep_lite_sh1_v1.yaml").read_text())
    sh2 = yaml.safe_load((REPO_ROOT / "configs" / "batches" / "batch_rvtr_policy_threshold_sweep_lite_sh2_v1.yaml").read_text())
    total_score = yaml.safe_load((REPO_ROOT / "configs" / "batches" / "batch_rvtr_policy_total_score_narrow_v1.yaml").read_text())
    total_score_sh1 = yaml.safe_load((REPO_ROOT / "configs" / "batches" / "batch_rvtr_policy_total_score_narrow_sh1_v1.yaml").read_text())
    assert int(sh1["shard_size"]) == 1
    assert int(sh2["shard_size"]) == 2
    assert int(total_score["shard_size"]) == 2
    assert int(total_score_sh1["shard_size"]) == 1

    print("batch workflow smoke test passed")


if __name__ == "__main__":
    main()
