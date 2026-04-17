"""Research-side RV/TR/no-entry decision policy experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

DECISION_POLICY_VERSION = "decision_policy_v1"
SUPPORTED_DECISION_FAMILIES = {
    "bin_env_v1",
    "bin_forceflip_v1",
    "two_stage_margin_v1",
    "tri_score_rvtrno_v1",
    "total_score_rvtrno_v1",
    "total_score_rvtr_v1",
}
SUPPORTED_SCORE_BUNDLES = {
    "sf_ctx_base_v1",
    "sf_ctx_momo_v1",
    "sf_timing_micro_v1",
    "sf_zone_risk_v1",
    "ts_ctx_min_v1",
    "ts_ctx_band_timing_v1",
    "ts_ctx_full_v1",
}
DEFAULT_DECISION_FAMILY = "bin_env_v1"
DEFAULT_SCORE_BUNDLE = "sf_ctx_base_v1"
TOTAL_SCORE_RVTR_V1_BUNDLE_PRESETS: dict[str, dict[str, dict[str, float]]] = {
    "ts_ctx_min_v1": {
        "rv": {
            "rv_momo_score": 0.75,
            "rv_stretch_score": 0.70,
        },
        "tr": {
            "tr_momo_score": 0.85,
            "tr_stretch_score": 0.35,
        },
    },
    "ts_ctx_band_timing_v1": {
        "rv": {
            "rv_band_score": 0.45,
            "rv_timing_score": 0.35,
            "rv_momo_score": 0.70,
            "rv_stretch_score": 0.65,
        },
        "tr": {
            "tr_band_score": 0.35,
            "tr_timing_score": 0.45,
            "tr_momo_score": 0.90,
            "tr_stretch_score": 0.30,
        },
    },
    "ts_ctx_full_v1": {
        "rv": {
            "rv_band_score": 0.40,
            "rv_timing_score": 0.35,
            "rv_momo_score": 0.65,
            "rv_stretch_score": 0.60,
            "rv_regime_score": 0.45,
            "rv_exit_proxy_score": 0.30,
        },
        "tr": {
            "tr_band_score": 0.35,
            "tr_timing_score": 0.50,
            "tr_momo_score": 0.85,
            "tr_stretch_score": 0.25,
            "tr_regime_score": 0.50,
            "tr_exit_proxy_score": 0.35,
        },
    },
}


@dataclass(frozen=True)
class DecisionPolicyConfig:
    family: str
    score_bundle: str
    margin_threshold: float
    no_entry_threshold: float
    entry_threshold: float = 0.75
    rv_score_weights: dict[str, float] | None = None
    tr_score_weights: dict[str, float] | None = None
    version: str = DECISION_POLICY_VERSION


@dataclass(frozen=True)
class DecisionPrepBundle:
    score_bundle: str
    decision_policy_version: str
    prep_df: pd.DataFrame


def parse_decision_policy_config(
    raw_policy: str | dict[str, Any] | None,
    raw_score_bundle: str | dict[str, Any] | None = None,
) -> DecisionPolicyConfig:
    """Normalize decision policy fields from experiment YAML."""
    family = DEFAULT_DECISION_FAMILY
    margin_threshold = 0.75
    no_entry_threshold = 0.25
    entry_threshold = 0.75
    rv_score_weights: dict[str, float] | None = None
    tr_score_weights: dict[str, float] | None = None

    if isinstance(raw_policy, dict):
        family = str(raw_policy.get("family", raw_policy.get("name", family))).strip()
        margin_threshold = float(raw_policy.get("margin_threshold", margin_threshold))
        no_entry_threshold = float(raw_policy.get("no_entry_threshold", no_entry_threshold))
        entry_threshold = float(raw_policy.get("entry_threshold", entry_threshold))
        rv_weights_raw = raw_policy.get("rv_score_weights")
        tr_weights_raw = raw_policy.get("tr_score_weights")
        if isinstance(rv_weights_raw, dict):
            rv_score_weights = {str(k): float(v) for k, v in rv_weights_raw.items()}
        if isinstance(tr_weights_raw, dict):
            tr_score_weights = {str(k): float(v) for k, v in tr_weights_raw.items()}
    elif raw_policy is not None and str(raw_policy).strip() != "":
        family = str(raw_policy).strip()

    score_bundle = DEFAULT_SCORE_BUNDLE
    if isinstance(raw_score_bundle, dict):
        score_bundle = str(raw_score_bundle.get("name", raw_score_bundle.get("bundle", score_bundle))).strip()
    elif raw_score_bundle is not None and str(raw_score_bundle).strip() != "":
        score_bundle = str(raw_score_bundle).strip()
    elif isinstance(raw_policy, dict) and raw_policy.get("score_bundle") is not None:
        score_bundle = str(raw_policy["score_bundle"]).strip()

    family = family.lower()
    score_bundle = score_bundle.lower()
    if family not in SUPPORTED_DECISION_FAMILIES:
        raise ValueError(f"Unsupported decision_policy family '{family}'. Allowed: {sorted(SUPPORTED_DECISION_FAMILIES)}")
    if score_bundle not in SUPPORTED_SCORE_BUNDLES:
        raise ValueError(f"Unsupported score_bundle '{score_bundle}'. Allowed: {sorted(SUPPORTED_SCORE_BUNDLES)}")

    return DecisionPolicyConfig(
        family=family,
        score_bundle=score_bundle,
        margin_threshold=margin_threshold,
        no_entry_threshold=no_entry_threshold,
        entry_threshold=entry_threshold,
        rv_score_weights=rv_score_weights,
        tr_score_weights=tr_score_weights,
    )


def apply_decision_policy_to_candidates(
    candidates_df: pd.DataFrame,
    policy: DecisionPolicyConfig,
) -> dict[str, Any]:
    prep_bundle = prepare_decision_policy_inputs(candidates_df, policy.score_bundle)
    return apply_prepared_decision_policy(prep_bundle, policy)


def prepare_decision_policy_inputs(
    candidates_df: pd.DataFrame,
    score_bundle: str,
) -> DecisionPrepBundle:
    """Build threshold-independent score preparation bundle."""
    audit_df = candidates_df.copy()
    audit_df["score_bundle"] = score_bundle
    audit_df["decision_policy_version"] = DECISION_POLICY_VERSION
    audit_df["rvtr_score"] = pd.Series(dtype="float64")
    audit_df["rvtr_score_margin"] = pd.Series(dtype="float64")
    audit_df["decision_group_id"] = ""
    audit_df["decision_group_rank"] = pd.Series(dtype="int64")
    audit_df["decision_best_score"] = pd.Series(dtype="float64")
    audit_df["decision_second_score"] = pd.Series(dtype="float64")
    audit_df["decision_group_count"] = pd.Series(dtype="int64")
    audit_df["hard_gate_passed"] = True
    audit_df["hard_gate_reject_reason"] = ""
    audit_df["score_gap_abs"] = pd.Series(dtype="float64")
    audit_df["score_gap_signed"] = pd.Series(dtype="float64")
    audit_df["score_winner"] = ""
    audit_df["tie_break_reason"] = ""

    if audit_df.empty:
        return DecisionPrepBundle(
            score_bundle=score_bundle,
            decision_policy_version=DECISION_POLICY_VERSION,
            prep_df=audit_df,
        )

    audit_df = _attach_scores(audit_df, score_bundle)

    decision_group_id = (
        audit_df["timestamp"].astype(str).fillna("")
        + "|"
        + audit_df["touch_side"].astype(str).fillna("")
    )
    audit_df["decision_group_id"] = decision_group_id

    ranked = audit_df.sort_values(
        ["decision_group_id", "rvtr_score", "candidate_family"],
        ascending=[True, False, True],
        kind="mergesort",
    ).copy()

    grouped = ranked.groupby("decision_group_id", sort=False, dropna=False)
    ranked["decision_group_rank"] = grouped.cumcount().add(1).astype("int64")
    ranked["decision_best_score"] = grouped["rvtr_score"].transform("first").astype("float64")
    ranked["decision_group_count"] = grouped["rvtr_score"].transform("size").astype("int64")

    second_score_map = ranked.loc[ranked["decision_group_rank"] == 2, ["decision_group_id", "rvtr_score"]].drop_duplicates(
        "decision_group_id", keep="first"
    )
    second_score_series = second_score_map.set_index("decision_group_id")["rvtr_score"] if not second_score_map.empty else pd.Series(dtype="float64")
    ranked["decision_second_score"] = ranked["decision_group_id"].map(second_score_series).fillna(0.0).astype("float64")
    ranked["rvtr_score_margin"] = ranked["decision_best_score"] - ranked["decision_second_score"]

    audit_df = ranked.sort_index()

    return DecisionPrepBundle(
        score_bundle=score_bundle,
        decision_policy_version=DECISION_POLICY_VERSION,
        prep_df=audit_df,
    )


def apply_prepared_decision_policy(
    prep_bundle: DecisionPrepBundle,
    policy: DecisionPolicyConfig,
) -> dict[str, Any]:
    """Apply threshold-dependent decision policy on prepared score bundle."""
    audit_df = prep_bundle.prep_df.copy()
    audit_df["decision_policy_family"] = policy.family
    audit_df["score_bundle"] = policy.score_bundle
    audit_df["decision_policy_version"] = policy.version
    audit_df["selected_by_decision_policy"] = False
    audit_df["decision_policy_outcome"] = "exclude"
    audit_df["final_decision"] = "no_entry"
    audit_df["reject_reason"] = "excluded_by_policy"
    audit_df["rv_total_score"] = pd.to_numeric(audit_df.get("rv_score", 0.0), errors="coerce").fillna(0.0).astype("float64")
    audit_df["tr_total_score"] = pd.to_numeric(audit_df.get("tr_score", 0.0), errors="coerce").fillna(0.0).astype("float64")
    audit_df["entry_strength_score"] = 0.0
    audit_df["decision_margin_score"] = 0.0

    if audit_df.empty:
        return _build_result(audit_df, policy, no_entry_group_count=0)

    if policy.family == "bin_env_v1":
        audit_df["selected_by_decision_policy"] = True
        audit_df["decision_policy_outcome"] = "include"
        audit_df["final_decision"] = audit_df["candidate_family"].map({"rev": "rv", "trend": "tr"}).fillna("no_entry")
        audit_df["reject_reason"] = ""
        audit_df["entry_strength_score"] = audit_df[["rv_total_score", "tr_total_score"]].max(axis=1)
        audit_df["decision_margin_score"] = (audit_df["rv_total_score"] - audit_df["tr_total_score"]).abs()
        audit_df["rvtr_score_margin"] = 0.0
        return _build_result(audit_df, policy, no_entry_group_count=0)

    if policy.family == "total_score_rvtrno_v1":
        audit_df = _attach_total_scores(audit_df, policy)
        rv_wins = (audit_df["rv_total_score"] >= policy.entry_threshold) & (
            (audit_df["rv_total_score"] - audit_df["tr_total_score"]) >= policy.margin_threshold
        )
        tr_wins = (audit_df["tr_total_score"] >= policy.entry_threshold) & (
            (audit_df["tr_total_score"] - audit_df["rv_total_score"]) >= policy.margin_threshold
        )
        audit_df.loc[rv_wins, "final_decision"] = "rv"
        audit_df.loc[tr_wins, "final_decision"] = "tr"
        audit_df["entry_strength_score"] = audit_df[["rv_total_score", "tr_total_score"]].max(axis=1)
        audit_df["decision_margin_score"] = (audit_df["rv_total_score"] - audit_df["tr_total_score"]).abs()

        family_match_mask = (
            ((audit_df["final_decision"] == "rv") & audit_df["candidate_family"].eq("rev"))
            | ((audit_df["final_decision"] == "tr") & audit_df["candidate_family"].eq("trend"))
        )
        audit_df["reject_reason"] = "no_entry_threshold"
        audit_df.loc[audit_df["final_decision"] != "no_entry", "reject_reason"] = "decision_family_mismatch"
        ranked_match = (
            audit_df.loc[family_match_mask]
            .sort_values(
                ["decision_group_id", "entry_strength_score", "decision_margin_score", "candidate_family"],
                ascending=[True, False, False, True],
                kind="mergesort",
            )
            .groupby("decision_group_id", sort=False, dropna=False)
            .cumcount()
        )
        top_selected_idx = ranked_match[ranked_match.eq(0)].index
        audit_df.loc[top_selected_idx, "selected_by_decision_policy"] = True
        audit_df.loc[top_selected_idx, "decision_policy_outcome"] = "include"
        audit_df.loc[top_selected_idx, "reject_reason"] = ""
        overflow_mask = family_match_mask & ~audit_df.index.isin(top_selected_idx)
        audit_df.loc[overflow_mask, "reject_reason"] = "not_top_decision_score"

        selected_groups = set(audit_df.loc[top_selected_idx, "decision_group_id"].astype(str))
        no_entry_group_mask = ~audit_df["decision_group_id"].astype(str).isin(selected_groups)
        no_entry_group_count = int(audit_df.loc[no_entry_group_mask, "decision_group_id"].nunique())
        return _build_result(audit_df, policy, no_entry_group_count=no_entry_group_count)

    if policy.family == "total_score_rvtr_v1":
        audit_df = _attach_total_scores_rvtr_v1(audit_df, policy)
        audit_df["score_gap_signed"] = (audit_df["rv_total_score"] - audit_df["tr_total_score"]).astype("float64")
        audit_df["score_gap_abs"] = audit_df["score_gap_signed"].abs().astype("float64")
        audit_df["score_winner"] = "tie"
        audit_df.loc[audit_df["score_gap_signed"] > 0.0, "score_winner"] = "rv"
        audit_df.loc[audit_df["score_gap_signed"] < 0.0, "score_winner"] = "tr"
        audit_df["tie_break_reason"] = ""

        tie_mask = audit_df["score_winner"].eq("tie")
        rv_tie = tie_mask & audit_df["candidate_family"].eq("rev")
        tr_tie = tie_mask & audit_df["candidate_family"].eq("trend")
        audit_df.loc[rv_tie, "score_winner"] = "rv"
        audit_df.loc[rv_tie, "tie_break_reason"] = "tie_family_alignment_rev"
        audit_df.loc[tr_tie, "score_winner"] = "tr"
        audit_df.loc[tr_tie, "tie_break_reason"] = "tie_family_alignment_trend"
        unresolved_tie = tie_mask & ~rv_tie & ~tr_tie
        audit_df.loc[unresolved_tie, "score_winner"] = "rv"
        audit_df.loc[unresolved_tie, "tie_break_reason"] = "tie_fixed_order_rv_first"

        audit_df["final_decision"] = audit_df["score_winner"]
        family_match_mask = (
            ((audit_df["final_decision"] == "rv") & audit_df["candidate_family"].eq("rev"))
            | ((audit_df["final_decision"] == "tr") & audit_df["candidate_family"].eq("trend"))
        )
        audit_df["entry_strength_score"] = audit_df[["rv_total_score", "tr_total_score"]].max(axis=1)
        audit_df["decision_margin_score"] = audit_df["score_gap_abs"].astype("float64")
        audit_df["reject_reason"] = "decision_family_mismatch"
        audit_df.loc[audit_df["hard_gate_passed"] == False, "reject_reason"] = audit_df["hard_gate_reject_reason"]

        ranked_match = (
            audit_df.loc[family_match_mask & audit_df["hard_gate_passed"]]
            .sort_values(
                ["decision_group_id", "entry_strength_score", "decision_margin_score", "candidate_family"],
                ascending=[True, False, False, True],
                kind="mergesort",
            )
            .groupby("decision_group_id", sort=False, dropna=False)
            .cumcount()
        )
        top_selected_idx = ranked_match[ranked_match.eq(0)].index
        audit_df.loc[top_selected_idx, "selected_by_decision_policy"] = True
        audit_df.loc[top_selected_idx, "decision_policy_outcome"] = "include"
        audit_df.loc[top_selected_idx, "reject_reason"] = ""
        overflow_mask = (family_match_mask & audit_df["hard_gate_passed"]) & ~audit_df.index.isin(top_selected_idx)
        audit_df.loc[overflow_mask, "reject_reason"] = "not_top_decision_score"

        return _build_result(audit_df, policy, no_entry_group_count=0)

    best_row_mask = audit_df["decision_group_rank"].eq(1)

    no_entry_group_mask = pd.Series(False, index=audit_df.index)
    if policy.family == "two_stage_margin_v1":
        no_entry_group_mask = audit_df["rvtr_score_margin"] < policy.margin_threshold
        audit_df.loc[no_entry_group_mask, "decision_policy_outcome"] = "no_entry_margin"
    elif policy.family == "tri_score_rvtrno_v1":
        no_entry_score = policy.no_entry_threshold + (policy.margin_threshold - audit_df["rvtr_score_margin"]).clip(lower=0.0)
        audit_df["no_entry_score"] = no_entry_score
        no_entry_group_mask = no_entry_score >= audit_df["decision_best_score"]
        audit_df.loc[no_entry_group_mask, "decision_policy_outcome"] = "no_entry_score"

    include_mask = best_row_mask & ~no_entry_group_mask
    audit_df.loc[include_mask, "selected_by_decision_policy"] = True
    audit_df.loc[include_mask, "decision_policy_outcome"] = "include"
    audit_df.loc[include_mask, "final_decision"] = audit_df.loc[include_mask, "candidate_family"].map({"rev": "rv", "trend": "tr"}).fillna(
        "no_entry"
    )
    audit_df.loc[include_mask, "reject_reason"] = ""
    audit_df.loc[audit_df["decision_policy_outcome"] == "no_entry_margin", "reject_reason"] = "no_entry_margin"
    audit_df.loc[audit_df["decision_policy_outcome"] == "no_entry_score", "reject_reason"] = "no_entry_score"
    audit_df["entry_strength_score"] = audit_df["decision_best_score"].astype("float64")
    audit_df["decision_margin_score"] = audit_df["rvtr_score_margin"].astype("float64")
    no_entry_group_count = int(audit_df.loc[no_entry_group_mask, "decision_group_id"].nunique())

    return _build_result(audit_df, policy, no_entry_group_count=no_entry_group_count)


def _attach_scores(df: pd.DataFrame, score_bundle: str) -> pd.DataFrame:
    result = df.copy()
    def _num(col: str, default: float = 0.0) -> pd.Series:
        return pd.to_numeric(result.get(col, pd.Series(default, index=result.index)), errors="coerce").fillna(default)

    dist = _num("dist_from_ema_pips", 0.0)
    atr14 = _num("atr14_pips", 0.0)
    band_width_pips = _num("band_width_pips", 0.0)
    pre10 = _num("pre10_change_pips", 0.0)
    pre30 = _num("pre30_change_pips", 0.0)
    pre60 = _num("pre60_change_pips", 0.0)
    net10 = _num("net10_change_pips", 0.0)
    atr_ratio = _num("atr_ratio_5_14", 1.0)
    rsi14 = _num("rsi14", 50.0)
    macd_hist = _num("macd_hist", 0.0)
    bb_width_ratio = _num("bb_width_ratio_to_close", 0.0)
    m5_slope = _num("m5_slope", 0.0)
    m30_slope = _num("m30_slope", 0.0)
    h1_slope = _num("h1_slope", 0.0)

    direction_sign = result["direction"].map({"buy": 1.0, "sell": -1.0}).fillna(0.0)
    directional_momo = direction_sign * (pre10 + (0.5 * net10))
    extended_from_ema = dist.abs()
    rsi_extreme = (rsi14 - 50.0).abs() / 10.0
    dist_from_ema_norm_by_atr = extended_from_ema / atr14.replace(0.0, pd.NA)
    dist_from_ema_norm_by_atr = dist_from_ema_norm_by_atr.fillna(0.0)
    dist_from_ema_norm_by_band = extended_from_ema / band_width_pips.replace(0.0, pd.NA)
    dist_from_ema_norm_by_band = dist_from_ema_norm_by_band.fillna(0.0)
    band_width_norm_vs_atr = band_width_pips / atr14.replace(0.0, pd.NA)
    band_width_norm_vs_atr = band_width_norm_vs_atr.fillna(0.0)
    result["dist_from_ema_norm_by_band"] = dist_from_ema_norm_by_band.astype("float64")
    result["dist_from_ema_norm_by_atr"] = dist_from_ema_norm_by_atr.astype("float64")
    result["band_width_norm_vs_atr"] = band_width_norm_vs_atr.astype("float64")
    band_period = _num("band_atr_period", 0.0)
    band_period = band_period.where(band_period > 0.0, _num("band_vol_period", 0.0))
    band_period = band_period.where(
        band_period > 0.0,
        _num("band_range_period", 0.0),
    )
    result["band_period"] = band_period.astype("float64")
    result["band_value"] = _num("band_value", 0.0).astype("float64")
    result["timing_mode"] = result.get("timing_mode", "baseline_touch").astype(str)
    result["ambiguous_dual_touch_same_bar"] = (
        result.get("timing_close_reject_reason", "").astype(str).eq("ambiguous_dual_touch_same_bar").astype(float)
    )
    close_rejected = _num("timing_close_rejected", 0.0)
    result["close_inside_band_distance"] = (
        1.0 - result.get("timing_still_touch_at_close", False).astype(float)
    ).where(close_rejected.astype(bool), 0.0)
    result["touch_to_close_reversion"] = result["close_inside_band_distance"]
    result["rsi_extreme"] = rsi_extreme
    result["extended_from_ema"] = extended_from_ema
    result["directional_momo"] = directional_momo

    # Hard-gate layer (separate from score layer).
    fatal_data_issue = result.get("timestamp").isna() if "timestamp" in result.columns else pd.Series(True, index=result.index)
    impossible_execution_state = (
        _num("entry_price", 0.0) <= 0.0
    ) | (
        _num("tp_pips", 0.0) <= 0.0
    ) | (
        _num("sl_pips", 0.0) <= 0.0
    ) | result.get("direction", "").astype(str).isin({"", "nan"})
    spread_abnormal = _num("spread_abnormal", 0.0) > 0.0
    explicit_shock_lock = _num("shock_lock", 0.0) > 0.0
    blackout_or_missing_inputs = result[
        [c for c in ["dist_from_ema_pips", "pre10_change_pips", "rsi14", "atr14_pips"] if c in result.columns]
    ].isna().any(axis=1) if any(c in result.columns for c in ["dist_from_ema_pips", "pre10_change_pips", "rsi14", "atr14_pips"]) else pd.Series(False, index=result.index)
    result["hard_gate_reject_reason"] = ""
    result.loc[fatal_data_issue, "hard_gate_reject_reason"] = "fatal_data_issue"
    result.loc[~fatal_data_issue & impossible_execution_state, "hard_gate_reject_reason"] = "impossible_execution_state"
    result.loc[~fatal_data_issue & ~impossible_execution_state & spread_abnormal, "hard_gate_reject_reason"] = "spread_abnormal"
    result.loc[~fatal_data_issue & ~impossible_execution_state & ~spread_abnormal & explicit_shock_lock, "hard_gate_reject_reason"] = "explicit_shock_lock"
    result.loc[
        ~fatal_data_issue & ~impossible_execution_state & ~spread_abnormal & ~explicit_shock_lock & blackout_or_missing_inputs,
        "hard_gate_reject_reason",
    ] = "blackout_or_missing_essential_inputs"
    result["hard_gate_passed"] = result["hard_gate_reject_reason"].eq("")

    rev_score = (0.20 * extended_from_ema) + (0.20 * rsi_extreme) - (0.12 * directional_momo)
    trend_score = (0.28 * directional_momo) + (0.04 * extended_from_ema)

    if score_bundle == "sf_ctx_momo_v1":
        directional_momo30 = direction_sign * pre30
        rev_score = rev_score - (0.08 * directional_momo30)
        trend_score = trend_score + (0.18 * directional_momo30)
    elif score_bundle == "sf_timing_micro_v1":
        asia_penalty = result.get("session", "").astype(str).str.lower().eq("asia").astype(float)
        rev_score = rev_score - (0.35 * asia_penalty)
        trend_score = trend_score + (0.10 * asia_penalty)
    elif score_bundle == "sf_zone_risk_v1":
        atr_penalty = (atr_ratio - 1.0).abs()
        rev_score = rev_score - (0.25 * atr_penalty)
        trend_score = trend_score - (0.10 * atr_penalty)

    result["rv_score"] = rev_score
    result["tr_score"] = trend_score
    result["directional_momo"] = directional_momo
    result["extended_from_ema"] = extended_from_ema
    result["rsi_extreme"] = rsi_extreme

    # Taxonomy-aware block scores (kept as audit columns).
    result["rv_band_score"] = (0.45 * dist_from_ema_norm_by_band) + (0.20 * dist_from_ema_norm_by_atr) - (0.10 * band_width_norm_vs_atr)
    result["tr_band_score"] = (0.30 * dist_from_ema_norm_by_atr) + (0.15 * band_width_norm_vs_atr)
    timing_still_touch = pd.to_numeric(result.get("timing_still_touch_at_close", 0.0), errors="coerce").fillna(0.0)
    timing_close_confirmed = pd.to_numeric(result.get("timing_close_confirmed", 0.0), errors="coerce").fillna(0.0)
    timing_close_rejected = pd.to_numeric(result.get("timing_close_rejected", 0.0), errors="coerce").fillna(0.0)
    result["rv_timing_score"] = (0.20 * result["touch_to_close_reversion"]) - (0.30 * timing_still_touch) + (0.15 * timing_close_rejected)
    result["tr_timing_score"] = (0.25 * timing_still_touch) + (0.20 * timing_close_confirmed) - (0.15 * timing_close_rejected)
    momo_blend = directional_momo + (0.40 * direction_sign * pre30) + (0.20 * direction_sign * pre60) + (0.30 * m5_slope) + (0.20 * m30_slope) + (0.10 * h1_slope)
    result["rv_momo_score"] = -0.18 * momo_blend
    result["tr_momo_score"] = 0.22 * momo_blend
    result["rv_stretch_score"] = (0.16 * rsi_extreme) + (0.10 * extended_from_ema) - (0.05 * macd_hist.abs()) + (0.05 * bb_width_ratio)
    result["tr_stretch_score"] = (0.08 * macd_hist) - (0.06 * rsi_extreme) + (0.03 * bb_width_ratio)
    session = result.get("session", "").astype(str).str.lower()
    session_london_ny = session.isin(["london", "newyork", "new_york"]).astype(float)
    vol_regime = (atr_ratio - 1.0).abs()
    family_is_rev = result.get("candidate_family", "").astype(str).eq("rev").astype(float)
    family_is_tr = result.get("candidate_family", "").astype(str).eq("trend").astype(float)
    result["rv_regime_score"] = (0.12 * (1.0 - vol_regime.clip(upper=2.0))) + (0.05 * (1.0 - session_london_ny)) + (0.06 * family_is_rev)
    result["tr_regime_score"] = (0.12 * vol_regime.clip(upper=2.0)) + (0.08 * session_london_ny) + (0.06 * family_is_tr)
    tp_pips = _num("tp_pips", 0.0)
    sl_pips = _num("sl_pips", 1.0)
    tp_sl_ratio = tp_pips / sl_pips.replace(0.0, pd.NA)
    tp_sl_ratio = tp_sl_ratio.fillna(0.0)
    vol_tp_size = tp_pips / atr14.replace(0.0, pd.NA)
    vol_sl_size = sl_pips / atr14.replace(0.0, pd.NA)
    result["tp_sl_ratio"] = tp_sl_ratio.astype("float64")
    result["rv_exit_proxy_score"] = (0.10 * tp_sl_ratio) - (0.04 * vol_tp_size.fillna(0.0))
    result["tr_exit_proxy_score"] = (0.14 * tp_sl_ratio) + (0.04 * vol_sl_size.fillna(0.0))

    result["rvtr_score"] = trend_score.where(result["candidate_family"] == "trend", rev_score).fillna(0.0)
    result["no_entry_score"] = 0.0
    return result


def _attach_total_scores(df: pd.DataFrame, policy: DecisionPolicyConfig) -> pd.DataFrame:
    result = df.copy()
    rv_weights = {
        "rv_score": 1.0,
        "tr_score": 0.0,
        "directional_momo": -0.08,
        "extended_from_ema": 0.05,
        "rsi_extreme": 0.04,
    }
    tr_weights = {
        "rv_score": 0.0,
        "tr_score": 1.0,
        "directional_momo": 0.08,
        "extended_from_ema": 0.02,
        "rsi_extreme": 0.0,
    }
    if policy.rv_score_weights:
        rv_weights.update(policy.rv_score_weights)
    if policy.tr_score_weights:
        tr_weights.update(policy.tr_score_weights)

    feature_map: dict[str, pd.Series] = {
        "rv_score": pd.to_numeric(result.get("rv_score", 0.0), errors="coerce").fillna(0.0),
        "tr_score": pd.to_numeric(result.get("tr_score", 0.0), errors="coerce").fillna(0.0),
        "directional_momo": pd.to_numeric(result.get("directional_momo", 0.0), errors="coerce").fillna(0.0),
        "extended_from_ema": pd.to_numeric(result.get("extended_from_ema", 0.0), errors="coerce").fillna(0.0),
        "rsi_extreme": pd.to_numeric(result.get("rsi_extreme", 0.0), errors="coerce").fillna(0.0),
    }

    rv_total = pd.Series(0.0, index=result.index, dtype="float64")
    tr_total = pd.Series(0.0, index=result.index, dtype="float64")
    for feature_name, weight in rv_weights.items():
        rv_total = rv_total + (float(weight) * feature_map.get(feature_name, pd.Series(0.0, index=result.index)))
    for feature_name, weight in tr_weights.items():
        tr_total = tr_total + (float(weight) * feature_map.get(feature_name, pd.Series(0.0, index=result.index)))
    result["rv_total_score"] = rv_total.astype("float64")
    result["tr_total_score"] = tr_total.astype("float64")
    return result


def _attach_total_scores_rvtr_v1(df: pd.DataFrame, policy: DecisionPolicyConfig) -> pd.DataFrame:
    result = df.copy()
    preset = TOTAL_SCORE_RVTR_V1_BUNDLE_PRESETS.get(
        policy.score_bundle,
        TOTAL_SCORE_RVTR_V1_BUNDLE_PRESETS["ts_ctx_full_v1"],
    )
    rv_weights = dict(preset["rv"])
    tr_weights = dict(preset["tr"])
    if policy.rv_score_weights:
        rv_weights.update(policy.rv_score_weights)
    if policy.tr_score_weights:
        tr_weights.update(policy.tr_score_weights)

    rv_total = pd.Series(0.0, index=result.index, dtype="float64")
    tr_total = pd.Series(0.0, index=result.index, dtype="float64")
    for feature_name, weight in rv_weights.items():
        feature = pd.to_numeric(result.get(feature_name, 0.0), errors="coerce").fillna(0.0)
        rv_total = rv_total + (float(weight) * feature)
    for feature_name, weight in tr_weights.items():
        feature = pd.to_numeric(result.get(feature_name, 0.0), errors="coerce").fillna(0.0)
        tr_total = tr_total + (float(weight) * feature)

    result["rv_total_score"] = rv_total.astype("float64")
    result["tr_total_score"] = tr_total.astype("float64")
    return result


def _build_result(audit_df: pd.DataFrame, policy: DecisionPolicyConfig, *, no_entry_group_count: int) -> dict[str, Any]:
    selected = audit_df[audit_df["selected_by_decision_policy"]].copy()
    rv_selected = int((selected.get("candidate_family", pd.Series(dtype=object)) == "rev").sum())
    tr_selected = int((selected.get("candidate_family", pd.Series(dtype=object)) == "trend").sum())
    return {
        "included_df": selected,
        "audit_df": audit_df,
        "summary": {
            "decision_policy_family": policy.family,
            "score_bundle": policy.score_bundle,
            "decision_policy_version": policy.version,
            "base_candidate_count": int(len(audit_df)),
            "selected_candidate_count": int(len(selected)),
            "rv_selected_count": rv_selected,
            "tr_selected_count": tr_selected,
            "no_entry_group_count": int(no_entry_group_count),
        },
    }
