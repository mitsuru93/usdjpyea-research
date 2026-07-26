#!/usr/bin/env python3
"""Build factor-analysis observations from canonical trade/event records."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from tools.research_platform.event_model_v1 import TradeEvent, TradeIdentity, validate_event_stream
from tools.research_platform.factor_analysis_v1 import TradeObservation

SCHEMA_VERSION = "usdjpy_b02_f05_observation_builder_v1"


@dataclass(frozen=True, slots=True)
class CanonicalTradeRecord:
    identity: TradeIdentity
    events: Sequence[TradeEvent]


def _event_by_type(events: Sequence[TradeEvent]) -> dict[str, TradeEvent]:
    result: dict[str, TradeEvent] = {}
    for event in events:
        result.setdefault(event.event_type, event)
    return result


def build_observation(
    record: CanonicalTradeRecord,
    *,
    outcome_event_types: Sequence[str] = ("BASELINE_EXIT", "CANDIDATE_EXIT"),
    factor_event_types: Sequence[str] | None = None,
    extra_factors: Mapping[str, float | int | bool | str | None] | None = None,
) -> TradeObservation:
    events = validate_event_stream(record.identity, record.events)
    by_type = _event_by_type(events)
    outcome = None
    terminal_state = events[-1].event_type if events else "NO_EVENTS"
    for event_type in outcome_event_types:
        if event_type in by_type:
            outcome = by_type[event_type].signed_pips
            terminal_state = event_type
            break
    if outcome is None:
        if not events:
            raise ValueError(f"trade {record.identity.trade_id} has no events")
        outcome = events[-1].signed_pips

    factors: dict[str, float | int | bool | str | None] = {
        "event_count": len(events),
        "terminal_elapsed_ms": events[-1].elapsed_ms,
        "terminal_mfe_pips": events[-1].mfe_pips,
        "terminal_mae_pips": events[-1].mae_pips,
    }
    selected = factor_event_types or tuple(by_type)
    for event_type in selected:
        event = by_type.get(event_type)
        if event is None:
            factors[f"has_{event_type.lower()}"] = False
            continue
        prefix = event_type.lower()
        factors[f"has_{prefix}"] = True
        factors[f"{prefix}_elapsed_ms"] = event.elapsed_ms
        factors[f"{prefix}_signed_pips"] = event.signed_pips
        factors[f"{prefix}_mfe_pips"] = event.mfe_pips
        factors[f"{prefix}_mae_pips"] = event.mae_pips
        for key, value in event.payload.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                factors[f"{prefix}_{key}"] = value
    if extra_factors:
        factors.update(extra_factors)

    observation = TradeObservation(
        trade_id=record.identity.trade_id,
        period=record.identity.period,
        strategy=record.identity.strategy,
        side=record.identity.side,
        state=terminal_state,
        outcome_pips=float(outcome),
        factors=factors,
    )
    observation.validate()
    return observation


def build_observations(records: Iterable[CanonicalTradeRecord], **kwargs) -> list[TradeObservation]:
    observations = [build_observation(record, **kwargs) for record in records]
    if len({row.trade_id for row in observations}) != len(observations):
        raise ValueError("duplicate trade_id in observation population")
    return observations
