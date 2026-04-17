#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.policy.decision_policy import apply_prepared_decision_policy, parse_decision_policy_config, prepare_decision_policy_inputs
from tools.run_experiment import _build_precompute_inputs, _compute_preprocessed_frames


def main() -> None:
    cfg = {
        "input_csv": "research/data_sample/usdjpy_m1_tiny_sample.csv",
        "input_timezone_mode": "UTC",
        "max_holding_bars": 20,
        "symbol": "USDJPY",
        "timeframe": "M1",
        "timing_mode": "baseline_touch",
        "band_model": "fixed_pips",
        "band_pips": 10,
    }
    params, _ = _build_precompute_inputs(cfg)
    pre = _compute_preprocessed_frames(cfg, params)
    cand_df = pre["candidate_feature_df"]

    policy = parse_decision_policy_config(
        {
            "family": "total_score_rvtrno_v1",
            "entry_threshold": 0.75,
            "margin_threshold": 0.10,
            "rv_score_weights": {"rv_score": 1.0},
            "tr_score_weights": {"tr_score": 1.0},
        },
        "sf_ctx_base_v1",
    )
    bundle = prepare_decision_policy_inputs(cand_df, policy.score_bundle)
    result = apply_prepared_decision_policy(bundle, policy)
    audit_df = result["audit_df"]
    required_cols = [
        "rv_total_score",
        "tr_total_score",
        "final_decision",
        "reject_reason",
        "entry_strength_score",
        "decision_margin_score",
    ]
    for col in required_cols:
        assert col in audit_df.columns, f"missing column: {col}"
    assert set(audit_df["final_decision"].astype(str).unique()).issubset({"rv", "tr", "no_entry"})
    print("total score policy smoke test passed")


if __name__ == "__main__":
    main()
