#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.policy.decision_policy import DecisionPolicyConfig, apply_prepared_decision_policy, prepare_decision_policy_inputs
from research.simulator.outcome_engine import evaluate_candidates
from tools.profile_hotpaths import _legacy_apply, _legacy_evaluate, _legacy_prepare
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
    env_df = pre["env_df"]
    cand_df = pre["candidate_feature_df"]

    policy = DecisionPolicyConfig(
        family="tri_score_rvtrno_v1",
        score_bundle="sf_ctx_base_v1",
        margin_threshold=0.75,
        no_entry_threshold=0.25,
    )

    prep_new = prepare_decision_policy_inputs(cand_df, policy.score_bundle).prep_df.sort_index()
    prep_old = _legacy_prepare(cand_df, policy.score_bundle).sort_index()
    compare_cols = ["decision_group_id", "decision_group_rank", "decision_best_score", "decision_second_score", "rvtr_score_margin"]
    pd.testing.assert_frame_equal(prep_new[compare_cols], prep_old[compare_cols], check_dtype=False)

    apply_new = apply_prepared_decision_policy(prepare_decision_policy_inputs(cand_df, policy.score_bundle), policy)
    apply_old_df = _legacy_apply(prep_old, policy)
    apply_new_df = apply_new["audit_df"].sort_values(["timestamp", "touch_side", "candidate_family", "direction"]).reset_index(drop=True)
    apply_old_df = apply_old_df.sort_values(["timestamp", "touch_side", "candidate_family", "direction"]).reset_index(drop=True)
    pd.testing.assert_series_equal(
        apply_new_df["selected_by_decision_policy"],
        apply_old_df["selected_by_decision_policy"],
        check_names=False,
    )
    pd.testing.assert_series_equal(
        apply_new_df["decision_policy_outcome"].astype(str),
        apply_old_df["decision_policy_outcome"].astype(str),
        check_names=False,
    )

    selected_new = apply_new["included_df"].copy()
    selected_old = apply_old_df[apply_old_df["selected_by_decision_policy"]].copy()
    out_new = evaluate_candidates(env_df, selected_new, max_holding_bars=20)
    out_old = _legacy_evaluate(env_df, selected_old, max_holding_bars=20)
    key_cols = ["candidate_id", "outcome_status", "bars_held", "pnl_pips"]
    out_new = out_new.sort_values("candidate_id").reset_index(drop=True)
    out_old = out_old.sort_values("candidate_id").reset_index(drop=True)
    pd.testing.assert_frame_equal(out_new[key_cols], out_old[key_cols], check_dtype=False)

    print("semantic regression legacy parity passed")


if __name__ == "__main__":
    main()
