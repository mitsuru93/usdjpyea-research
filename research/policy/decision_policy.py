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
}
SUPPORTED_SCORE_BUNDLES = {
    "sf_ctx_base_v1",
    "sf_ctx_momo_v1",
    "sf_timing_micro_v1",
    "sf_zone_risk_v1",
}
DEFAULT_DECISION_FAMILY = "bin_env_v1"
DEFAULT_SCORE_BUNDLE = "sf_ctx_base_v1"


@dataclass(frozen=True)
class DecisionPolicyConfig:
    family: str
    score_bundle: str
    margin_threshold: float
    no_entry_threshold: float
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

    if isinstance(raw_policy, dict):
        family = str(raw_policy.get("family", raw_policy.get("name", family))).strip()
        margin_threshold = float(raw_policy.get("margin_threshold", margin_threshold))
        no_entry_threshold = float(raw_policy.get("no_entry_threshold", no_entry_threshold))
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

    if audit_df.empty:
        return DecisionPrepBundle(
            score_bundle=score_bundle,
            decision_policy_version=DECISION_POLICY_VERSION,
            prep_df=audit_df,
        )

    audit_df = _attach_scores(audit_df, score_bundle)

    group_cols = ["timestamp", "touch_side"]
    for group_key, part in audit_df.groupby(group_cols, sort=False, dropna=False):
        group_id = "|".join(str(item) for item in (group_key if isinstance(group_key, tuple) else (group_key,)))
        audit_df.loc[part.index, "decision_group_id"] = group_id

        ranked = part.sort_values(["rvtr_score", "candidate_family"], ascending=[False, True])
        best_score = float(ranked.iloc[0]["rvtr_score"])
        second_score = float(ranked.iloc[1]["rvtr_score"]) if len(ranked) > 1 else 0.0
        margin = best_score - second_score
        audit_df.loc[part.index, "rvtr_score_margin"] = margin
        audit_df.loc[part.index, "decision_best_score"] = best_score
        audit_df.loc[part.index, "decision_second_score"] = second_score
        audit_df.loc[part.index, "decision_group_count"] = int(len(ranked))

        group_rank = pd.Series(range(1, len(ranked) + 1), index=ranked.index, dtype="int64")
        audit_df.loc[group_rank.index, "decision_group_rank"] = group_rank

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

    if audit_df.empty:
        return _build_result(audit_df, policy, no_entry_group_count=0)

    if policy.family == "bin_env_v1":
        audit_df["selected_by_decision_policy"] = True
        audit_df["decision_policy_outcome"] = "include"
        audit_df["rvtr_score_margin"] = 0.0
        return _build_result(audit_df, policy, no_entry_group_count=0)

    no_entry_group_count = 0
    for _, part in audit_df.groupby("decision_group_id", sort=False, dropna=False):
        group_best = part[part["decision_group_rank"] == 1]
        if group_best.empty:
            continue
        best_idx = group_best.index[0]
        margin = float(part["rvtr_score_margin"].iloc[0])
        best_score = float(part["decision_best_score"].iloc[0])

        if policy.family == "two_stage_margin_v1" and margin < policy.margin_threshold:
            no_entry_group_count += 1
            audit_df.loc[part.index, "decision_policy_outcome"] = "no_entry_margin"
            continue

        if policy.family == "tri_score_rvtrno_v1":
            no_entry_score = policy.no_entry_threshold + max(0.0, policy.margin_threshold - margin)
            audit_df.loc[part.index, "no_entry_score"] = no_entry_score
            if no_entry_score >= best_score:
                no_entry_group_count += 1
                audit_df.loc[part.index, "decision_policy_outcome"] = "no_entry_score"
                continue

        audit_df.loc[best_idx, "selected_by_decision_policy"] = True
        audit_df.loc[best_idx, "decision_policy_outcome"] = "include"

    return _build_result(audit_df, policy, no_entry_group_count=no_entry_group_count)


def _attach_scores(df: pd.DataFrame, score_bundle: str) -> pd.DataFrame:
    result = df.copy()
    dist = pd.to_numeric(result.get("dist_from_ema_pips", 0.0), errors="coerce").fillna(0.0)
    pre10 = pd.to_numeric(result.get("pre10_change_pips", 0.0), errors="coerce").fillna(0.0)
    pre30 = pd.to_numeric(result.get("pre30_change_pips", 0.0), errors="coerce").fillna(0.0)
    net10 = pd.to_numeric(result.get("net10_change_pips", 0.0), errors="coerce").fillna(0.0)
    atr_ratio = pd.to_numeric(result.get("atr_ratio_5_14", 1.0), errors="coerce").fillna(1.0)
    rsi14 = pd.to_numeric(result.get("rsi14", 50.0), errors="coerce").fillna(50.0)

    direction_sign = result["direction"].map({"buy": 1.0, "sell": -1.0}).fillna(0.0)
    directional_momo = direction_sign * (pre10 + (0.5 * net10))
    extended_from_ema = dist.abs()
    rsi_extreme = (rsi14 - 50.0).abs() / 10.0

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
    result["rvtr_score"] = trend_score.where(result["candidate_family"] == "trend", rev_score).fillna(0.0)
    result["no_entry_score"] = 0.0
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
