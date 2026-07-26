#!/usr/bin/env python3
"""State-transition rules for reusable B02/F05 event-path analysis.

The first profile implements the frozen F05 failed-reclaim chronology without
changing its thresholds or scientific decision rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from tools.research_platform.event_model_v1 import TradeEvent

F05_FAILED_RECLAIM_PROFILE = "f05_failed_reclaim_validation_protocol_v1"


@dataclass(frozen=True, slots=True)
class TransitionAssessment:
    profile: str
    terminal_state: str
    valid: bool
    reason: str


_REQUIRED_ORDER = (
    "ENTRY",
    "INITIAL_FAILURE_ARMED",
    "INITIAL_REENTRY",
    "FIRST_RECLAIM",
    "RECLAIM_FAILURE",
    "CANDIDATE_EXIT",
)


def assess_f05_failed_reclaim(events: Iterable[TradeEvent]) -> TransitionAssessment:
    """Validate the binding chronology from the frozen failed-reclaim protocol.

    PROFIT_DISARM may occur after ENTRY and before RECLAIM_FAILURE. When present it
    permanently terminates the candidate path and the baseline exit must remain.
    """
    ordered = list(events)
    types = [event.event_type for event in ordered]
    if not types or types[0] != "ENTRY":
        return TransitionAssessment(F05_FAILED_RECLAIM_PROFILE, "INVALID", False, "ENTRY must be first")

    if "PROFIT_DISARM" in types:
        disarm_index = types.index("PROFIT_DISARM")
        if "RECLAIM_FAILURE" in types and disarm_index > types.index("RECLAIM_FAILURE"):
            return TransitionAssessment(F05_FAILED_RECLAIM_PROFILE, "INVALID", False, "profit disarm occurred after failure confirmation")
        if "CANDIDATE_EXIT" in types:
            return TransitionAssessment(F05_FAILED_RECLAIM_PROFILE, "INVALID", False, "candidate exit is forbidden after profit disarm")
        return TransitionAssessment(F05_FAILED_RECLAIM_PROFILE, "PROFIT_DISARMED", True, "baseline exit retained")

    positions: list[int] = []
    for event_type in _REQUIRED_ORDER:
        if types.count(event_type) != 1:
            return TransitionAssessment(F05_FAILED_RECLAIM_PROFILE, "INCOMPLETE", False, f"expected exactly one {event_type}")
        positions.append(types.index(event_type))
    if positions != sorted(positions):
        return TransitionAssessment(F05_FAILED_RECLAIM_PROFILE, "INVALID", False, "failed-reclaim events are out of order")

    reclaim = ordered[types.index("FIRST_RECLAIM")]
    failure = ordered[types.index("RECLAIM_FAILURE")]
    exit_event = ordered[types.index("CANDIDATE_EXIT")]
    if failure.event_time_utc <= reclaim.event_time_utc:
        return TransitionAssessment(F05_FAILED_RECLAIM_PROFILE, "INVALID", False, "failure M5 completion must be strictly after reclaim M1 close")
    if exit_event.event_time_utc <= failure.event_time_utc:
        return TransitionAssessment(F05_FAILED_RECLAIM_PROFILE, "INVALID", False, "candidate exit must be after failure confirmation")

    return TransitionAssessment(F05_FAILED_RECLAIM_PROFILE, "CANDIDATE_EXIT", True, "binding chronology satisfied")
