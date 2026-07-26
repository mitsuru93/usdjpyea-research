#!/usr/bin/env python3
"""Canonical trade/event records for USDJPY B02/F05 research.

This module is deliberately dependency-free so every evaluator and GitHub Actions
job can import the same definitions. It does not fetch or regenerate market data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "usdjpy_b02_f05_event_model_v1"
ALLOWED_STRATEGIES = {"B02", "F05"}
ALLOWED_SIDES = {"BUY", "SELL"}
ALLOWED_PERIODS = {"2023H1", "2023H2", "2024H1", "2024H2"}


@dataclass(frozen=True, slots=True)
class TradeIdentity:
    trade_id: str
    strategy: str
    side: str
    period: str
    entry_time_utc: str
    entry_price: float

    def validate(self) -> None:
        if not self.trade_id.strip():
            raise ValueError("trade_id is required")
        if self.strategy not in ALLOWED_STRATEGIES:
            raise ValueError(f"unsupported strategy: {self.strategy}")
        if self.side not in ALLOWED_SIDES:
            raise ValueError(f"unsupported side: {self.side}")
        if self.period not in ALLOWED_PERIODS:
            raise ValueError(f"unsupported period: {self.period}")
        _parse_utc(self.entry_time_utc)
        if self.entry_price <= 0:
            raise ValueError("entry_price must be positive")


@dataclass(frozen=True, slots=True)
class TradeEvent:
    trade_id: str
    event_index: int
    event_type: str
    event_time_utc: str
    elapsed_ms: int
    signed_pips: float
    mfe_pips: float
    mae_pips: float
    payload: Mapping[str, Any]

    def validate(self) -> None:
        if not self.trade_id.strip():
            raise ValueError("trade_id is required")
        if self.event_index < 0:
            raise ValueError("event_index must be non-negative")
        if not self.event_type.strip():
            raise ValueError("event_type is required")
        _parse_utc(self.event_time_utc)
        if self.elapsed_ms < 0:
            raise ValueError("elapsed_ms must be non-negative")
        if self.mfe_pips < 0 or self.mae_pips < 0:
            raise ValueError("MFE/MAE must be non-negative magnitudes")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"timestamp is not explicit UTC: {value}")
    return parsed


def validate_event_stream(identity: TradeIdentity, events: Iterable[TradeEvent]) -> list[TradeEvent]:
    identity.validate()
    ordered = list(events)
    previous_time = _parse_utc(identity.entry_time_utc)
    previous_elapsed = -1
    previous_index = -1
    for event in ordered:
        event.validate()
        if event.trade_id != identity.trade_id:
            raise ValueError(f"foreign event {event.trade_id} in {identity.trade_id}")
        event_time = _parse_utc(event.event_time_utc)
        if event.event_index != previous_index + 1:
            raise ValueError("event_index must be contiguous from zero")
        if event_time < previous_time or event.elapsed_ms < previous_elapsed:
            raise ValueError("event stream is not monotonic")
        previous_time = event_time
        previous_elapsed = event.elapsed_ms
        previous_index = event.event_index
    return ordered


def deterministic_record_sha256(identity: TradeIdentity, events: Iterable[TradeEvent]) -> str:
    validated = validate_event_stream(identity, events)
    document = {
        "schema_version": SCHEMA_VERSION,
        "trade": asdict(identity),
        "events": [asdict(event) for event in validated],
    }
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()
