#!/usr/bin/env python3
"""Read-only adapter from archived B02/F05 path ledgers to canonical events.

The archived ledger is intentionally treated as evidence, not rewritten. Column aliases
are resolved explicitly, unknown columns are preserved in payload, and missing required
fields fail closed. The adapter does not fetch Tick data or change historical labels.
"""
from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from tools.research_platform.event_model_v1 import TradeEvent, TradeIdentity, validate_event_stream

SCHEMA_VERSION = "usdjpy_b02_f05_path_ledger_adapter_v1"

ALIASES = {
    "trade_id": ("trade_id", "id", "signal_id", "position_id"),
    "strategy": ("strategy", "family", "ea_family"),
    "side": ("side", "direction", "trade_side"),
    "period": ("period", "fold", "sample_period"),
    "entry_time_utc": ("entry_time_utc", "entry_utc", "entry_time", "open_time_utc"),
    "entry_price": ("entry_price", "open_price", "entry_px"),
    "path_class": ("path_class", "m1_path_class", "exact_tick_path_class", "common_path_class"),
    "mfe_pips": ("mfe_pips", "max_favourable_pips", "max_favorable_pips"),
    "mae_pips": ("mae_pips", "max_adverse_pips"),
    "exit_time_utc": ("exit_time_utc", "exit_utc", "close_time_utc", "exit_time"),
}


@dataclass(frozen=True, slots=True)
class AdaptedTrade:
    identity: TradeIdentity
    events: tuple[TradeEvent, ...]
    source_row: Mapping[str, str]


def _open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def _resolve(row: Mapping[str, str], canonical: str, required: bool = True) -> str | None:
    for name in ALIASES[canonical]:
        value = row.get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    if required:
        raise ValueError(f"missing required ledger field {canonical}; accepted aliases={ALIASES[canonical]}")
    return None


def _float(value: str | None, default: float = 0.0) -> float:
    return default if value is None or value == "" else float(value)


def adapt_row(row: Mapping[str, str]) -> AdaptedTrade:
    trade_id = _resolve(row, "trade_id")
    identity = TradeIdentity(
        trade_id=trade_id,
        strategy=_resolve(row, "strategy").upper(),
        side=_resolve(row, "side").upper(),
        period=_resolve(row, "period"),
        entry_time_utc=_resolve(row, "entry_time_utc"),
        entry_price=_float(_resolve(row, "entry_price")),
    )
    path_class = _resolve(row, "path_class")
    mfe = _float(_resolve(row, "mfe_pips", required=False))
    mae = _float(_resolve(row, "mae_pips", required=False))
    payload: dict[str, Any] = {"path_class": path_class, "source_schema": SCHEMA_VERSION, "source_row": dict(row)}
    events = [TradeEvent(trade_id, 0, "ENTRY", identity.entry_time_utc, 0, 0.0, 0.0, 0.0, {})]
    events.append(TradeEvent(trade_id, 1, "PATH_CLASSIFIED", identity.entry_time_utc, 0, 0.0, mfe, mae, payload))
    exit_time = _resolve(row, "exit_time_utc", required=False)
    if exit_time:
        events.append(TradeEvent(trade_id, 2, "BASELINE_EXIT", exit_time, 0, 0.0, mfe, mae, {"source_row": dict(row)}))
    validated = tuple(validate_event_stream(identity, events))
    return AdaptedTrade(identity, validated, dict(row))


def load_path_ledger(path: Path, limit: int | None = None) -> list[AdaptedTrade]:
    output: list[AdaptedTrade] = []
    with _open_text(path) as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("ledger has no header")
        for row_number, row in enumerate(reader, start=2):
            try:
                output.append(adapt_row(row))
            except Exception as exc:
                raise ValueError(f"failed to adapt ledger row {row_number}: {exc}") from exc
            if limit is not None and len(output) >= limit:
                break
    return output
