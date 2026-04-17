#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = {
    "input_csv": "research/data_sample/usdjpy_m1_tiny_sample.csv",
    "input_timezone_mode": "UTC",
    "max_holding_bars": 20,
    "symbol": "USDJPY",
    "timeframe": "M1",
    "timing_mode": "baseline_touch",
    "band_model": "fixed_pips",
    "band_pips": 10,
    "decision_policy": {
        "family": "two_stage_margin_v1",
        "margin_threshold": 0.75,
        "no_entry_threshold": 0.25,
    },
    "score_bundle": "sf_ctx_base_v1",
    "policy": {},
}


def _run(cfg_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "run_experiment.py"), "--config", str(cfg_path)],
        check=True,
        cwd=REPO_ROOT,
    )


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _summary_snapshot(run_dir: Path) -> dict[str, object]:
    policy_summary = pd.read_csv(run_dir / "policy_candidate_summary.csv").iloc[0].to_dict()
    candidates = pd.read_csv(run_dir / "candidates.csv")
    status_counts = candidates["outcome_status"].value_counts().to_dict() if not candidates.empty else {}
    overall = pd.read_csv(run_dir / "summary_overall.csv")
    by_month = pd.read_csv(run_dir / "summary_by_month.csv")
    by_session = pd.read_csv(run_dir / "summary_by_session.csv")
    return {
        "policy_summary": policy_summary,
        "status_counts": status_counts,
        "overall": overall.to_dict(orient="records"),
        "by_month": by_month.to_dict(orient="records"),
        "by_session": by_session.to_dict(orient="records"),
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        cache_dir = temp_root / "cache"
        out1 = temp_root / "run1"
        out2 = temp_root / "run2"

        cfg1 = dict(BASE_CONFIG)
        cfg1.update(
            {
                "output_dir": str(out1),
                "shared_precompute_cache_dir": str(cache_dir),
                "shared_precompute_cache_key": "threshold-reuse-regression-v1",
            }
        )
        cfg2 = dict(cfg1)
        cfg2["output_dir"] = str(out2)

        cfg1_path = temp_root / "run1.yaml"
        cfg2_path = temp_root / "run2.yaml"
        cfg1_path.write_text(yaml.safe_dump(cfg1, sort_keys=False), encoding="utf-8")
        cfg2_path.write_text(yaml.safe_dump(cfg2, sort_keys=False), encoding="utf-8")

        _run(cfg1_path)
        _run(cfg2_path)

        md1 = _read_yaml(out1 / "run_metadata.yaml")
        md2 = _read_yaml(out2 / "run_metadata.yaml")

        assert bool(md1.get("cache", {}).get("decision_score_prep", {}).get("cache_hit", False)) is False
        assert bool(md1.get("cache", {}).get("outcome_table", {}).get("cache_hit", False)) is False
        assert bool(md2.get("cache", {}).get("decision_score_prep", {}).get("cache_hit", False)) is True
        assert bool(md2.get("cache", {}).get("outcome_table", {}).get("cache_hit", False)) is True

        s1 = _summary_snapshot(out1)
        s2 = _summary_snapshot(out2)
        assert s1 == s2, "cache miss/hit results diverged"

        required_policy_metrics = [
            "selected_candidate_count",
            "rv_selected_count",
            "tr_selected_count",
            "no_entry_group_count",
        ]
        for metric in required_policy_metrics:
            assert metric in s1["policy_summary"], f"missing metric: {metric}"

        print("threshold reuse regression test passed")


if __name__ == "__main__":
    main()
