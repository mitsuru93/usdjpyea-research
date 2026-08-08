#!/usr/bin/env python3
"""Common USDJPY portfolio accounting and integration primitives.

This module is infrastructure, not a candidate selector. It preserves strategy-local
trade rules and accepts only completed, hash-pinned ledgers. Missing evidence remains
None and blocks the relevant integrity gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import math
import re

import numpy as np
import pandas as pd

WORK_ID = "USDJPY-EA-INTEGRATION-001"
SYMBOL = "USDJPY"
COMMON_INITIAL_CAPITAL_JPY = 100_000.0
PIP = 0.01
POINT = 0.001
JPY_PER_PIP_001_LOT = 10.0
DEFAULT_LOT = 0.01
DEFAULT_SPREAD_POINTS = 5
DEFAULT_LEVERAGE = 25.0
CONTRACT_UNITS_001_LOT = 1_000.0
TOL = 1e-9

COMMON_TRADE_FIELDS = [
    "study_id", "hypothesis_id", "candidate_id", "candidate_version",
    "strategy_id", "source", "broker", "symbol", "lot", "side",
    "signal_utc", "decision_utc", "entry_utc", "entry_bid", "entry_ask",
    "entry_price", "exit_utc", "exit_bid", "exit_ask", "exit_price",
    "realized_pl_jpy", "spread_points", "commission", "swap", "exit_reason",
    "position_id", "source_trade_id", "candidate_visibility",
    "validation_run_id", "research_sha", "core_sha", "artifact_digest",
]

CHRONOLOGY = [
    "EXECUTABLE_MARKET_TICK",
    "STRATEGY_LOCAL_EXIT_CONDITION_FINALIZED",
    "CLOSE_EXECUTION",
    "REALIZED_PL_APPLIED",
    "STATE_AND_LOSS_COUNTER_UPDATED",
    "ENTRY_PERMISSION",
    "ENTRY_EXECUTION",
    "MARGIN_UPDATED",
    "EQUITY_SNAPSHOT",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            return None
        return 0.0 if abs(float(value)) < TOL else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat().replace("+00:00", "Z")
    return value


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(obj), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_utc(series: pd.Series, mt4: bool = False) -> pd.Series:
    if mt4:
        return pd.to_datetime(series, format="%Y.%m.%d %H:%M:%S", utc=True, errors="coerce")
    return pd.to_datetime(series, utc=True, format="mixed", errors="coerce")


def profit_factor(values: Iterable[float]) -> float | None:
    x = np.asarray(list(values), dtype=float)
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    return None if gl <= TOL else gp / gl


def drawdown_details(equity: Iterable[float], timestamps: Iterable[Any] | None = None) -> dict[str, Any]:
    x = np.asarray(list(equity), dtype=float)
    if len(x) == 0:
        return {
            "maximum_drawdown_jpy": 0.0,
            "minimum_equity_jpy": None,
            "drawdown_start_utc": None,
            "drawdown_bottom_utc": None,
            "drawdown_recovery_utc": None,
            "recovery_duration_seconds": None,
            "recovery_grid_points": 0,
            "recovered": True,
        }
    ts = pd.to_datetime(list(timestamps), utc=True, format="mixed") if timestamps is not None else pd.RangeIndex(len(x))
    peak = np.maximum.accumulate(x)
    dd = peak - x
    bottom = int(np.argmax(dd))
    peak_idx = int(np.where(x[: bottom + 1] >= peak[bottom] - TOL)[0][-1])
    future = np.flatnonzero(x[bottom:] >= peak[bottom] - TOL)
    recovered = len(future) > 0
    recovery_idx = bottom + int(future[0]) if recovered else len(x) - 1
    if isinstance(ts, pd.DatetimeIndex):
        duration = float((ts[recovery_idx] - ts[peak_idx]).total_seconds())
        start_ts = ts[peak_idx]
        bottom_ts = ts[bottom]
        recovery_ts = ts[recovery_idx] if recovered else None
    else:
        duration = None
        start_ts = bottom_ts = recovery_ts = None
    return {
        "maximum_drawdown_jpy": float(dd.max()),
        "minimum_equity_jpy": float(x.min()),
        "drawdown_start_utc": start_ts,
        "drawdown_bottom_utc": bottom_ts,
        "drawdown_recovery_utc": recovery_ts,
        "recovery_duration_seconds": duration,
        "recovery_grid_points": int(recovery_idx - peak_idx),
        "recovered": bool(recovered),
    }


def realized_equity(trades: pd.DataFrame, initial_capital: float = COMMON_INITIAL_CAPITAL_JPY) -> pd.DataFrame:
    closes = trades[["exit_utc", "realized_pl_jpy"]].copy().sort_values("exit_utc", kind="mergesort")
    rows = pd.DataFrame({
        "timestamp_utc": pd.concat([
            pd.Series([closes.exit_utc.min() - pd.Timedelta(nanoseconds=1)]),
            closes.exit_utc.reset_index(drop=True),
        ], ignore_index=True),
        "realized_equity_jpy": np.r_[initial_capital, initial_capital + closes.realized_pl_jpy.cumsum().to_numpy(float)],
    })
    return rows


def business_window_min(daily: pd.Series, n: int) -> float:
    if daily.empty:
        return 0.0
    start = pd.Timestamp(daily.index.min(), tz="UTC")
    end = pd.Timestamp(daily.index.max(), tz="UTC")
    idx = pd.date_range(start, end, freq="B", tz="UTC").strftime("%Y-%m-%d")
    values = daily.reindex(idx, fill_value=0.0)
    roll = values.rolling(n, min_periods=n).sum()
    return float(roll.min()) if roll.notna().any() else float(values.sum())


def commonize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field, None) for field in COMMON_TRADE_FIELDS}
