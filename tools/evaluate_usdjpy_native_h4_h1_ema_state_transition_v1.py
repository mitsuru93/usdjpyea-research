#!/usr/bin/env python3
"""Evaluate the frozen native H4/H1 EMA state-transition family.

Use --preflight-only before the preregistration merge. In that mode the tool
validates data construction, finite-grid identity, indicator initialization and
execution-map coverage, but it does not generate transitions, positions or P/L.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PIP = 0.01
FOLDS = {
    "2023H1": (pd.Timestamp("2023-01-01T00:00:00Z"), pd.Timestamp("2023-07-01T00:00:00Z")),
    "2023H2": (pd.Timestamp("2023-07-01T00:00:00Z"), pd.Timestamp("2024-01-01T00:00:00Z")),
    "2024H1": (pd.Timestamp("2024-01-01T00:00:00Z"), pd.Timestamp("2024-07-01T00:00:00Z")),
    "2024H2": (pd.Timestamp("2024-07-01T00:00:00Z"), pd.Timestamp("2025-01-01T00:00:00Z")),
}
EXPECTED_CELLS = [
    ("N_H4F3S12_H1F4S16", 3, 12, 4, 16, 0, 0),
    ("N_H4F3S12_H1F8S32", 3, 12, 8, 32, 0, 1),
    ("N_H4F6S24_H1F4S16", 6, 24, 4, 16, 1, 0),
    ("N_H4F6S24_H1F8S32", 6, 24, 8, 32, 1, 1),
    ("N_H4F12S48_H1F4S16", 12, 48, 4, 16, 2, 0),
    ("N_H4F12S48_H1F8S32", 12, 48, 8, 32, 2, 1),
]


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nth_sunday(year: int, month: int, nth: int, hour: int) -> pd.Timestamp:
    first = datetime(year, month, 1, hour, tzinfo=timezone.utc)
    return pd.Timestamp(first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (nth - 1)))


def is_us_dst(ts: pd.Timestamp) -> bool:
    return nth_sunday(ts.year, 3, 2, 7) <= ts < nth_sunday(ts.year, 11, 1, 6)


def server_to_utc(server: pd.Timestamp) -> pd.Timestamp:
    winter = server - pd.Timedelta(hours=2)
    return server - pd.Timedelta(hours=3) if is_us_dst(winter) else winter


def utc_to_server(utc: pd.Timestamp) -> pd.Timestamp:
    return utc + pd.Timedelta(hours=3 if is_us_dst(utc) else 2)


def hard_excluded(logical_utc: pd.Timestamp) -> bool:
    hour = logical_utc.hour
    return (20 <= hour < 23) if is_us_dst(logical_utc) else (21 <= hour < 24)


def load_m15_2023(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    server_first = pd.to_datetime(raw["first_timestamp_mt4_server"], utc=True, errors="raise")
    logical_server = server_first.dt.floor("15min")
    accepted_utc = pd.DatetimeIndex([server_to_utc(value) for value in server_first])
    logical_utc = pd.DatetimeIndex([server_to_utc(value) for value in logical_server])
    frame = pd.DataFrame({
        "logical_utc": logical_utc,
        "logical_server": logical_server,
        "accepted_ts": accepted_utc,
        "open": pd.to_numeric(raw["open"], errors="raise"),
        "high": pd.to_numeric(raw["high"], errors="raise"),
        "low": pd.to_numeric(raw["low"], errors="raise"),
        "close": pd.to_numeric(raw["close"], errors="raise"),
        "default_cost_pips": 0.5,
        "year": 2023,
    }).sort_values("logical_utc").reset_index(drop=True)
    assert len(frame) == 24825
    assert not frame["logical_utc"].duplicated().any()
    return frame


def load_m15_2024(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, compression="gzip")
    logical_utc = pd.to_datetime(raw["timestamp_utc"], utc=True, errors="raise")
    logical_server = pd.DatetimeIndex([utc_to_server(value) for value in logical_utc])
    spread = pd.to_numeric(raw["spread_mean_pips"], errors="raise")
    frame = pd.DataFrame({
        "logical_utc": logical_utc,
        "logical_server": logical_server,
        "accepted_ts": logical_utc,
        "open": pd.to_numeric(raw["mid_open"], errors="raise"),
        "high": pd.to_numeric(raw["mid_high"], errors="raise"),
        "low": pd.to_numeric(raw["mid_low"], errors="raise"),
        "close": pd.to_numeric(raw["mid_close"], errors="raise"),
        "default_cost_pips": np.maximum(0.5, spread),
        "year": 2024,
    }).sort_values("logical_utc").reset_index(drop=True)
    assert len(frame) == 24439
    assert not frame["logical_utc"].duplicated().any()
    return frame


def aggregate_exact(m15: pd.DataFrame, frequency: str, slots: int) -> pd.DataFrame:
    bucket = m15["logical_server"].dt.floor(frequency)
    work = m15.assign(bucket_server=bucket)
    grouped = work.groupby("bucket_server", sort=True).agg(
        constituent=("logical_server", "size"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    )
    exact = []
    for start in grouped.index:
        actual = set(work.loc[work["bucket_server"] == start, "logical_server"])
        expected = set(pd.date_range(start, periods=slots, freq="15min"))
        exact.append(actual == expected)
    grouped["exact"] = exact
    grouped = grouped[grouped["exact"]].copy()
    grouped["information_utc"] = [server_to_utc(start + pd.tseries.frequencies.to_offset(frequency)) for start in grouped.index]
    return grouped.reset_index().sort_values("information_utc").reset_index(drop=True)


def add_state(frame: pd.DataFrame, fast: int, slow: int, prefix: str) -> pd.DataFrame:
    work = frame.copy()
    fast_ema = work["close"].ewm(span=fast, adjust=False, min_periods=slow).mean()
    slow_ema = work["close"].ewm(span=slow, adjust=False, min_periods=slow).mean()
    state = pd.Series(0, index=work.index, dtype="int8")
    state.loc[fast_ema > slow_ema] = 1
    state.loc[fast_ema < slow_ema] = -1
    work[f"{prefix}_fast"] = fast_ema
    work[f"{prefix}_slow"] = slow_ema
    work[f"{prefix}_state"] = state
    previous = state.shift(1).fillna(0).astype("int8")
    transition = pd.Series(0, index=work.index, dtype="int8")
    transition.loc[(previous == -1) & (state == 1)] = 1
    transition.loc[(previous == 1) & (state == -1)] = -1
    work[f"{prefix}_transition"] = transition
    return work


def execution_index(m15_times: np.ndarray, information_time: pd.Timestamp) -> int | None:
    index = int(np.searchsorted(m15_times, np.datetime64(information_time.to_datetime64()), side="left"))
    return index if index < len(m15_times) else None


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


@dataclass
class Pending:
    side: int
    h4_info: pd.Timestamp
    remaining_future_h1: int = 4


@dataclass
class Position:
    side: int
    entry_index: int
    entry_info: pd.Timestamp
    entry_reason: str


def simulate_fold(candidate_id: str, h4: pd.DataFrame, h1: pd.DataFrame, m15: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    h4_events = h4[(h4["information_utc"] >= start) & (h4["information_utc"] < end)][["information_utc", "h4_state", "h4_transition"]].copy()
    h4_events["kind"] = "H4"
    h1_events = h1[(h1["information_utc"] >= start) & (h1["information_utc"] < end)][["information_utc", "h1_state"]].copy()
    h1_events["kind"] = "H1"
    events = pd.concat([h4_events, h1_events], ignore_index=True, sort=False)
    events["order"] = events["kind"].map({"H4": 0, "H1": 1})
    events = events.sort_values(["information_utc", "order"]).reset_index(drop=True)
    fold_m15 = m15[(m154T4 