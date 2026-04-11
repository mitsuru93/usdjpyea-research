"""Deterministic pandas-only policy rule engine for candidate screening."""

from __future__ import annotations

from typing import Any

import pandas as pd

from research.policy.rule_types import (
    SUPPORTED_ACTIONS,
    SUPPORTED_OPERATORS,
    SUPPORTED_SELECTORS,
    PolicyCondition,
    PolicyRule,
)


def compile_rules(raw_rules: list[dict[str, Any]] | None) -> list[PolicyRule]:
    """Validate and normalize YAML rule mappings into typed rule definitions."""
    if not raw_rules:
        return []

    rules: list[PolicyRule] = []
    for idx, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            raise ValueError(f"policy.rules[{idx}] must be a mapping")

        action = str(raw_rule.get("type", "")).strip().lower()
        if action not in SUPPORTED_ACTIONS:
            raise ValueError(
                f"policy.rules[{idx}].type must be one of {sorted(SUPPORTED_ACTIONS)}, got '{action}'"
            )

        name = raw_rule.get("name")
        if name is not None:
            name = str(name)

        selectors: dict[str, list[Any]] = {}
        for key in SUPPORTED_SELECTORS:
            if key not in raw_rule:
                continue
            raw_value = raw_rule[key]
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            selectors[key] = [v for v in values]

        raw_conditions = raw_rule.get("conditions", [])
        if raw_conditions is None:
            raw_conditions = []
        if not isinstance(raw_conditions, list):
            raise ValueError(f"policy.rules[{idx}].conditions must be a list")

        conditions: list[PolicyCondition] = []
        for cond_idx, raw_cond in enumerate(raw_conditions):
            if not isinstance(raw_cond, dict):
                raise ValueError(f"policy.rules[{idx}].conditions[{cond_idx}] must be a mapping")

            feature = raw_cond.get("feature", raw_cond.get("column"))
            if feature is None:
                raise ValueError(f"policy.rules[{idx}].conditions[{cond_idx}] missing 'feature'")
            feature = str(feature)

            op = str(raw_cond.get("op", "")).strip()
            if op not in SUPPORTED_OPERATORS:
                raise ValueError(
                    f"policy.rules[{idx}].conditions[{cond_idx}].op must be one of "
                    f"{sorted(SUPPORTED_OPERATORS)}, got '{op}'"
                )

            if "value" not in raw_cond:
                raise ValueError(f"policy.rules[{idx}].conditions[{cond_idx}] missing 'value'")
            value = raw_cond["value"]

            conditions.append(PolicyCondition(feature=feature, op=op, value=value))

        rules.append(
            PolicyRule(
                action=action,
                name=name,
                selectors=selectors,
                conditions=conditions,
            )
        )

    return rules


def evaluate_rule_mask(df: pd.DataFrame, rule: PolicyRule, rule_index: int) -> pd.Series:
    """Return matching mask for a single rule over dataframe rows."""
    mask = pd.Series(True, index=df.index)

    for selector, selector_values in rule.selectors.items():
        if selector not in df.columns:
            raise ValueError(
                f"policy.rules[{rule_index}] selector '{selector}' not found in candidate columns. "
                f"Available columns include: {list(df.columns)}"
            )
        mask &= _build_in_mask(df[selector], selector_values)

    for cond in rule.conditions:
        if cond.feature not in df.columns:
            raise ValueError(
                f"policy.rules[{rule_index}] references missing feature/column '{cond.feature}'. "
                f"Available columns include: {list(df.columns)}"
            )
        mask &= _evaluate_condition(df[cond.feature], cond)

    return mask


def _build_in_mask(series: pd.Series, values: list[Any]) -> pd.Series:
    if series.dtype == "object" or pd.api.types.is_string_dtype(series):
        lowered = {str(v).lower() for v in values}
        return series.astype(str).str.lower().isin(lowered)
    return series.isin(values)


def _evaluate_condition(series: pd.Series, cond: PolicyCondition) -> pd.Series:
    op = cond.op
    value = cond.value

    if op == ">":
        return series > value
    if op == ">=":
        return series >= value
    if op == "<":
        return series < value
    if op == "<=":
        return series <= value
    if op == "==":
        return _evaluate_equality(series, value)
    if op == "!=":
        return ~_evaluate_equality(series, value)
    if op == "between":
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError("'between' requires two-element list/tuple value [lower, upper]")
        lower, upper = value
        return (series >= lower) & (series <= upper)
    if op == "in":
        values = value if isinstance(value, list) else [value]
        return _build_in_mask(series, values)
    if op == "not_in":
        values = value if isinstance(value, list) else [value]
        return ~_build_in_mask(series, values)

    raise ValueError(f"Unsupported operator: {op}")


def _evaluate_equality(series: pd.Series, value: Any) -> pd.Series:
    """Case-insensitive equality for object/string-like columns, exact for numeric columns."""
    if series.dtype == "object" or pd.api.types.is_string_dtype(series):
        lhs = series.astype(str).str.lower()
        rhs = str(value).lower()
        return lhs == rhs
    return series == value
