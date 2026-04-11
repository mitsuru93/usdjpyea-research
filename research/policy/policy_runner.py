"""Policy runner that applies ordered screening rules to candidate rows."""

from __future__ import annotations

from typing import Any

import pandas as pd

from research.policy.rule_engine import compile_rules, evaluate_rule_mask
from research.policy.rule_types import PolicyConfig

POLICY_SEMANTICS = "last_match_wins"


def parse_policy_config(policy_cfg: dict[str, Any] | None) -> PolicyConfig:
    """Normalize YAML policy config into typed config."""
    cfg = policy_cfg or {}
    enabled = bool(cfg.get("enabled", False))
    name = str(cfg.get("name", "unnamed_policy"))
    semantics = str(cfg.get("semantics", POLICY_SEMANTICS)).strip().lower()

    if semantics != POLICY_SEMANTICS:
        raise ValueError(
            f"Unsupported policy semantics '{semantics}'. Only '{POLICY_SEMANTICS}' is supported."
        )

    rules = compile_rules(cfg.get("rules", []))
    return PolicyConfig(enabled=enabled, name=name, semantics=semantics, rules=rules)


def apply_policy_to_candidates(candidates_df: pd.DataFrame, policy: PolicyConfig) -> dict[str, Any]:
    """Apply policy and return included set + full audit set + metadata."""
    audit_df = candidates_df.copy()
    audit_df["policy_enabled"] = bool(policy.enabled)
    audit_df["policy_name"] = policy.name if policy.enabled else ""
    audit_df["policy_semantics"] = policy.semantics if policy.enabled else ""
    audit_df["policy_decision"] = "include"
    audit_df["matched_rule_index"] = pd.Series([pd.NA] * len(audit_df), dtype="Int64")
    audit_df["matched_rule_name"] = pd.Series([None] * len(audit_df), dtype="object")
    audit_df["excluded_by_policy"] = False

    if not policy.enabled or audit_df.empty:
        return {
            "included_df": audit_df[audit_df["excluded_by_policy"] == False].copy(),  # noqa: E712
            "audit_df": audit_df,
            "matched_rule_events": 0,
        }

    matched_rule_events = 0  # Counts rule-row match events across ordered rules (not unique candidates).
    for idx, rule in enumerate(policy.rules):
        rule_mask = evaluate_rule_mask(audit_df, rule, idx)
        if not rule_mask.any():
            continue

        matched_rule_events += int(rule_mask.sum())
        audit_df.loc[rule_mask, "matched_rule_index"] = idx
        audit_df.loc[rule_mask, "matched_rule_name"] = rule.name

        if rule.action == "allow":
            audit_df.loc[rule_mask, "policy_decision"] = "include"
            audit_df.loc[rule_mask, "excluded_by_policy"] = False
        else:  # deny
            audit_df.loc[rule_mask, "policy_decision"] = "exclude"
            audit_df.loc[rule_mask, "excluded_by_policy"] = True

    included_df = audit_df[~audit_df["excluded_by_policy"]].copy()
    return {
        "included_df": included_df,
        "audit_df": audit_df,
        "matched_rule_events": matched_rule_events,
    }
