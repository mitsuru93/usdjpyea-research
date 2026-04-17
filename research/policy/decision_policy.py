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
    entry_threshold: float = 0.75
    rv_score_weights: dict[str, float] | None = None
    tr_score_weights: dict[str, float] | None = None
    version: str = DECISION_POLICY_VERSION


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
    """Apply a deterministic RV/TR/no-entry decision policy to paired candidates."""
    audit_df = candidates_df.copy()
    audit_df["decision_policy_family"] = policy.family
    audit_df["score_bundle"] = policy.score_bundle
    audit_df["decision_policy_version"] = policy.version
    audit_df["rvtr_score"] = pd.Series(dtype="float64")
    audit_df["rvtr_score_margin"] = pd.Series(dtype="float64")
    audit_df["selected_by_decision_policy"] = False
    audit_df["decision_policy_outcome"] = "exclude"
    audit_df["decision_group_id"] = ""
    audit_df["final_decision"] = "no_entry"
    audit_df["reject_reason"] = "excluded_by_policy"
    audit_df["rv_total_score"] = pd.Series(0.0, index=audit_df.index, dtype="float64")
    audit_df["tr_total_score"] = pd.Series(0.0, index=audit_df.index, dtype="float64")
    audit_df["entry_strength_score"] = pd.Series(0.0, index=audit_df.index, dtype="float64")
    audit_df["decision_margin_score"] = pd.Series(0.0, index=audit_df.index, dtype="float64")

    if audit_df.empty:
        return _build_result(audit_df, policy, no_entry_group_count=0)

    audit_df = _attach_scores(audit_df, policy.score_bundle)
    if policy.family == "total_score_rvtrno_v1":
        audit_df = _attach_total_scores(audit_df, policy)
    if policy.family == "bin_env_v1":
        audit_df["selected_by_decision_policy"] = True
        audit_df["decision_policy_outcome"] = "include"
        audit_df["final_decision"] = audit_df["candidate_family"].map({"rev": "rv", "trend": "tr"}).fillna("no_entry")
        audit_df["reject_reason"] = ""
        audit_df["entry_strength_score"] = audit_df[["rv_total_score", "tr_total_score"]].max(axis=1)
        audit_df["decision_margin_score"] = (audit_df["rv_total_score"] - audit_df["tr_total_score"]).abs()
        audit_df["rvtr_score_margin"] = 0.0
        return _build_result(audit_df, policy, no_entry_group_count=0)

    no_entry_group_count = 0
    group_cols = ["timestamp", "touch_side"]
    for group_key, part in audit_df.groupby(group_cols, sort=False, dropna=False):
        group_id = "|".join(str(item) for item in (group_key if isinstance(group_key, tuple) else (group_key,)))
        audit_df.loc[part.index, "decision_group_id"] = group_id

        ranked = part.sort_values(["rvtr_score", "candidate_family"], ascending=[False, True])
        best_idx = ranked.index[0]
        best_score = float(ranked.iloc[0]["rvtr_score"])
        second_score = float(ranked.iloc[1]["rvtr_score"]) if len(ranked) > 1 else 0.0
        margin = best_score - second_score
        audit_df.loc[part.index, "rvtr_score_margin"] = margin

        if policy.family == "total_score_rvtrno_v1":
            part_df = audit_df.loc[part.index].copy()
            part_df["entry_strength_score"] = part_df[["rv_total_score", "tr_total_score"]].max(axis=1)
            part_df["decision_margin_score"] = (part_df["rv_total_score"] - part_df["tr_total_score"]).abs()

            rv_wins = (part_df["rv_total_score"] >= policy.entry_threshold) & (
                (part_df["rv_total_score"] - part_df["tr_total_score"]) >= policy.margin_threshold
            )
            tr_wins = (part_df["tr_total_score"] >= policy.entry_threshold) & (
                (part_df["tr_total_score"] - part_df["rv_total_score"]) >= policy.margin_threshold
            )
            part_df.loc[rv_wins, "final_decision"] = "rv"
            part_df.loc[tr_wins, "final_decision"] = "tr"

            family_match_mask = (
                ((part_df["final_decision"] == "rv") & part_df["candidate_family"].eq("rev"))
                | ((part_df["final_decision"] == "tr") & part_df["candidate_family"].eq("trend"))
            )
            if bool(family_match_mask.any()):
                best_match_idx = (
                    part_df.loc[family_match_mask]
                    .sort_values(
                        ["entry_strength_score", "decision_margin_score", "candidate_family"],
                        ascending=[False, False, True],
                        kind="mergesort",
                    )
                    .index[0]
                )
                part_df["reject_reason"] = "no_entry_threshold"
                part_df.loc[part_df["final_decision"] != "no_entry", "reject_reason"] = "decision_family_mismatch"
                part_df.loc[family_match_mask, "reject_reason"] = "not_top_decision_score"
                part_df.loc[best_match_idx, "selected_by_decision_policy"] = True
                part_df.loc[best_match_idx, "decision_policy_outcome"] = "include"
                part_df.loc[best_match_idx, "reject_reason"] = ""
            else:
                no_entry_group_count += 1
                part_df["reject_reason"] = "no_entry_threshold"
                part_df.loc[part_df["final_decision"] != "no_entry", "reject_reason"] = "decision_family_mismatch"

            audit_df.loc[part.index, "selected_by_decision_policy"] = part_df["selected_by_decision_policy"]
            audit_df.loc[part.index, "decision_policy_outcome"] = part_df["decision_policy_outcome"]
            audit_df.loc[part.index, "final_decision"] = part_df["final_decision"]
            audit_df.loc[part.index, "reject_reason"] = part_df["reject_reason"]
            audit_df.loc[part.index, "entry_strength_score"] = part_df["entry_strength_score"]
            audit_df.loc[part.index, "decision_margin_score"] = part_df["decision_margin_score"]
            continue

        if policy.family == "two_stage_margin_v1" and margin < policy.margin_threshold:
            no_entry_group_count += 1
            audit_df.loc[part.index, "decision_policy_outcome"] = "no_entry_margin"
            audit_df.loc[part.index, "reject_reason"] = "no_entry_margin"
            audit_df.loc[part.index, "entry_strength_score"] = best_score
            audit_df.loc[part.index, "decision_margin_score"] = margin
            continue

        if policy.family == "tri_score_rvtrno_v1":
            no_entry_score = policy.no_entry_threshold + max(0.0, policy.margin_threshold - margin)
            audit_df.loc[part.index, "no_entry_score"] = no_entry_score
            if no_entry_score >= best_score:
                no_entry_group_count += 1
                audit_df.loc[part.index, "decision_policy_outcome"] = "no_entry_score"
                audit_df.loc[part.index, "reject_reason"] = "no_entry_score"
                audit_df.loc[part.index, "entry_strength_score"] = best_score
                audit_df.loc[part.index, "decision_margin_score"] = margin
                continue

        audit_df.loc[best_idx, "selected_by_decision_policy"] = True
        audit_df.loc[best_idx, "decision_policy_outcome"] = "include"
        selected_family = str(audit_df.loc[best_idx, "candidate_family"]).strip().lower()
        selected_decision = "rv" if selected_family == "rev" else "tr" if selected_family == "trend" else "no_entry"
        audit_df.loc[best_idx, "final_decision"] = selected_decision
        audit_df.loc[best_idx, "reject_reason"] = ""
        audit_df.loc[part.index, "entry_strength_score"] = best_score
        audit_df.loc[part.index, "decision_margin_score"] = margin

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
    result["directional_momo"] = directional_momo
    result["extended_from_ema"] = extended_from_ema
    result["rsi_extreme"] = rsi_extreme
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
