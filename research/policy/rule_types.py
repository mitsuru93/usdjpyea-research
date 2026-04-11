"""Typed structures for research-side policy screening rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_ACTIONS = {"allow", "deny"}
SUPPORTED_OPERATORS = {">", ">=", "<", "<=", "==", "!=", "between", "in", "not_in"}
SUPPORTED_SELECTORS = {"candidate_family", "direction", "session", "touch_side"}


@dataclass(frozen=True)
class PolicyCondition:
    """Single condition over a candidate or feature column."""

    feature: str
    op: str
    value: Any


@dataclass(frozen=True)
class PolicyRule:
    """Single ordered rule in screening policy."""

    action: str
    name: str | None
    selectors: dict[str, list[Any]]
    conditions: list[PolicyCondition]


@dataclass(frozen=True)
class PolicyConfig:
    """Top-level policy configuration payload."""

    enabled: bool
    name: str
    semantics: str
    rules: list[PolicyRule]
