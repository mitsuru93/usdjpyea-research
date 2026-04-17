#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.policy.decision_policy import (
    DecisionPrepBundle,
    apply_decision_policy_to_candidates,
    apply_prepared_decision_policy,
    parse_decision_policy_config,
)
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
    result = apply_decision_policy_to_candidates(cand_df, policy)
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

    rvtr_policy = parse_decision_policy_config(
        {
            "family": "total_score_rvtr_v1",
            "rv_score_weights": {"rv_momo_score": 0.7},
            "tr_score_weights": {"tr_momo_score": 0.9},
        },
        "ts_ctx_full_v1",
    )
    rvtr_result = apply_decision_policy_to_candidates(cand_df, rvtr_policy)
    rvtr_audit = rvtr_result["audit_df"]
    for col in [
        "rv_band_score",
        "tr_band_score",
        "rv_timing_score",
        "tr_timing_score",
        "rv_momo_score",
        "tr_momo_score",
        "rv_stretch_score",
        "tr_stretch_score",
        "rv_regime_score",
        "tr_regime_score",
        "rv_exit_proxy_score",
        "tr_exit_proxy_score",
        "hard_gate_passed",
        "hard_gate_reject_reason",
        "score_gap_abs",
        "score_gap_signed",
        "score_winner",
        "tie_break_reason",
    ]:
        assert col in rvtr_audit.columns, f"missing column: {col}"
    assert set(rvtr_audit["final_decision"].astype(str).unique()).issubset({"rv", "tr", "no_entry"})

    tie_df = rvtr_audit.head(2).copy()
    tie_df.loc[:, "rv_band_score"] = 0.0
    tie_df.loc[:, "tr_band_score"] = 0.0
    tie_df.loc[:, "rv_timing_score"] = 0.0
    tie_df.loc[:, "tr_timing_score"] = 0.0
    tie_df.loc[:, "rv_momo_score"] = 0.0
    tie_df.loc[:, "tr_momo_score"] = 0.0
    tie_df.loc[:, "rv_stretch_score"] = 0.0
    tie_df.loc[:, "tr_stretch_score"] = 0.0
    tie_df.loc[:, "rv_regime_score"] = 0.0
    tie_df.loc[:, "tr_regime_score"] = 0.0
    tie_df.loc[:, "rv_exit_proxy_score"] = 0.0
    tie_df.loc[:, "tr_exit_proxy_score"] = 0.0
    tie_df.loc[:, "hard_gate_passed"] = True
    tie_df.loc[:, "hard_gate_reject_reason"] = ""
    tie_df.loc[:, "candidate_family"] = ["rev", "trend"]
    tie_df.loc[:, "direction"] = ["sell", "buy"]
    tie_df.loc[:, "decision_group_id"] = "tie_group"
    tie_df.loc[:, "decision_group_rank"] = [1, 2]
    tie_res = apply_prepared_decision_policy(
        DecisionPrepBundle(score_bundle=rvtr_policy.score_bundle, decision_policy_version=rvtr_policy.version, prep_df=tie_df),
        rvtr_policy,
    )
    tie_audit = tie_res["audit_df"]
    assert "tie_family_alignment_rev" in set(tie_audit["tie_break_reason"].astype(str).tolist())
    print("total score policy smoke test passed")


if __name__ == "__main__":
    main()
