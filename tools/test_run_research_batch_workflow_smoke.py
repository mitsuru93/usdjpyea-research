from __future__ import annotations

from pathlib import Path


def test_run_research_batch_workflow_keeps_shard_artifacts_on_failure() -> None:
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "run_research_batch.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "- name: Upload shard artifacts\n        if: always()" in workflow_text
    assert "- name: Upload shard artifacts bundle\n        if: always()" in workflow_text

    assert "study_metadata.yaml" in workflow_text
    assert "study_summary.md" in workflow_text
    assert "runtime_configs" in workflow_text
    assert "run_metadata.yaml" in workflow_text
    assert "-name \"*.log\"" in workflow_text
