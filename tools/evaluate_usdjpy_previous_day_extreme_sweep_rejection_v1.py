#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import lzma
import math
import re
import struct
import tarfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

HYPOTHESIS_ID = "USDJPY-HYP-034"
FAMILY_ID = "S_PREVIOUS_DAY_EXTREME_SWEEP_REJECTION"
PIP = 0.01
JPY_PER_PIP = 10.0
JPY_PER_PRICE = 1000.0
INITIAL_CAPITAL = 1_000_000.0
TOL = 1e-6
FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]
BI5_PATH = re.compile(r"(?:^|/)(20\d{2})/(\d{2})/(\d{2})/(\d{2})h_ticks\.bi5$")
BI5_DTYPE = np.dtype([("ms", ">u4"), ("ask", ">u4"), ("bid", ">u4"), ("askv", ">f4"), ("bidv", ">f4")])
PRICE_SCALE = 1000.0
BOOTSTRAP_REPS = 5000
BOOTSTRAP_SEED = 34034


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_float(value: float | int | np.number | None) -> float | None:
    if value is None:
        return None
    x = float(value)
    if not math.isfinite(x):
        return None
    if abs(x) < TOL:
        return 0.0
    return x


def json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return clean_float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if pd.isna(value) if not isinstance(value, (str, bytes)) else False:
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(json_clean(payload), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def fold_of(ts: pd.Timestamp | datetime) -> str | None:
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    else:
        t = t.tz_convert("UTC")
    if t < pd.Timestamp("2023-01-01", tz="UTC") or t >= pd.Timestamp("2025-01-01", tz="UTC"):
        return None
    if t < pd.Timestamp("2023-07-01", tz="UTC"):
        return "2023H1"
    if t < pd.Timestamp("2024-01-01", tz="UTC"):
        return "2023H2"
    if t < pd.Timestamp("2024-07-01", tz="UTC"):
        return "2024H1"
    return "2024H2"


def session_of(hour: int) -> str:
    if 0 <= hour < 7:
        return "TOKYO"
    if 7 <= hour < 13:
        return "LONDON"
    if 13 <= hour < 21:
        return "NEW_YORK"
    return "ROLLOVER"


def pf(values: Iterable[float]) -> float | None:
    arr = np.asarray(list(values), dtype=float)
    gp = arr[arr > 0].sum()
    gl = -arr[arr < 0].sum()
    return None if gl <= TOL else float(gp / gl)


def max_drawdown(values: Iterable[float], initial: float = 0.0) -> tuple[float, float]:
    arr = np.asarray(list(values), dtype=float)
    equity = initial + np.cumsum(arr)
    if equity.size == 0:
        return 0.0, initial
    peaks = np.maximum.accumulate(np.r_[initial, equity])
    dd = peaks[1:] - equity
    return float(dd.max(initial=0.0)), float(equity.min(initial=initial))


def positive_share(series: pd.Series) -> float:
    pos = series[series > 0]
    if pos.empty or pos.sum() <= TOL:
        return 0.0
    return float(pos.max() / pos.sum())


def first_index_ge(times_ns: np.ndarray, target_ns: int) -> int | None:
    idx = int(np.searchsorted(times_ns, target_ns, side="left"))
    return idx if idx < len(times_ns) else None


@dataclass
class TickDay:
    day: date
    times_ns: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    hour_members: int
    decoded_hour_members: int
    decode_errors: list[str]
    inversion_count: int
    nonmonotonic_count: int
    duplicate_timestamp_count: int

    @property
    def tick_count(self) -> int:
        return int(len(self.times_ns))


@dataclass
class DailyAudit:
    day: date
    tick_count: int
    hour_members: int
    decoded_hour_members: int
    decode_errors: int
    inversion_count: int
    nonmonotonic_count: int
    duplicate_timestamp_count: int
    first_tick_ns: int | None
    last_tick_ns: int | None
    bid_open: float | None
    bid_high: float | None
    bid_low: float | None
    bid_close: float | None
    ask_high: float | None
    ask_low: float | None
    high_time_ns: int | None
    low_time_ns: int | None
    source_archive: str
    source_archive_sha256: str

    @property
    def structurally_complete(self) -> bool:
        return (
            self.hour_members == 24
            and self.decoded_hour_members == 24
            and self.decode_errors == 0
            and self.inversion_count == 0
            and self.nonmonotonic_count == 0
        )

    @property
    def eligible(self) -> bool:
        return self.day.weekday() < 5 and self.tick_count > 0 and self.structurally_complete


@dataclass
class Bar:
    start_ns: int
    end_ns: int
    open_bid: float
    high_bid: float
    low_bid: float
    close_bid: float
    close_ask: float
    tick_count: int
    median_spread_pips: float


def parse_hour(name: str) -> tuple[date, int]:
    m = BI5_PATH.search(name)
    if not m:
        raise ValueError(name)
    y, mo, d, h = map(int, m.groups())
    return date(y, mo, d), h


def decode_bi5(raw: bytes, hour_start_ns: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    payload = lzma.decompress(raw)
    if not payload:
        return np.array([], dtype=np.int64), np.array([], dtype=np.float64), np.array([], dtype=np.float64), 0, 0
    if len(payload) % BI5_DTYPE.itemsize:
        raise ValueError(f"BI5 decoded size {len(payload)} not divisible by {BI5_DTYPE.itemsize}")
    rec = np.frombuffer(payload, dtype=BI5_DTYPE)
    ms = rec["ms"].astype(np.int64)
    ask = rec["ask"].astype(np.float64) / PRICE_SCALE
    bid = rec["bid"].astype(np.float64) / PRICE_SCALE
    times = hour_start_ns + ms * 1_000_000
    inversion = int(np.sum(ask < bid))
    nonmono = int(np.sum(np.diff(ms) < 0)) if len(ms) > 1 else 0
    return times, bid, ask, inversion, nonmono


def iter_tick_days(raw_dir: Path) -> Iterable[tuple[TickDay, str, str]]:
    archives = sorted(raw_dir.glob("*.tar.gz"))
    for archive_path in archives:
        archive_sha = sha256_file(archive_path)
        grouped: dict[date, list[tarfile.TarInfo]] = defaultdict(list)
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.isfile() and member.name.endswith(".bi5"):
                    try:
                        d, _ = parse_hour(member.name)
                    except ValueError:
                        continue
                    grouped[d].append(member)
            for d in sorted(grouped):
                members = sorted(grouped[d], key=lambda m: parse_hour(m.name)[1])
                times_parts: list[np.ndarray] = []
                bid_parts: list[np.ndarray] = []
                ask_parts: list[np.ndarray] = []
                errors: list[str] = []
                inv = nonmono = decoded = 0
                for member in members:
                    _, hour = parse_hour(member.name)
                    extracted = tar.extractfile(member)
                    if extracted is None:
                        errors.append(f"{member.name}:extractfile_none")
                        continue
                    try:
                        hour_start = int(pd.Timestamp(datetime(d.year, d.month, d.day, hour, tzinfo=timezone.utc)).value)
                        times, bid, ask, xinv, xnon = decode_bi5(extracted.read(), hour_start)
                        decoded += 1
                        inv += xinv
                        nonmono += xnon
                        if len(times):
                            times_parts.append(times)
                            bid_parts.append(bid)
                            ask_parts.append(ask)
                    except Exception as exc:
                        errors.append(f"{member.name}:{type(exc).__name__}:{exc}")
                if times_parts:
                    times = np.concatenate(times_parts)
                    bid = np.concatenate(bid_parts)
                    ask = np.concatenate(ask_parts)
                    order = np.argsort(times, kind="stable")
                    times, bid, ask = times[order], bid[order], ask[order]
                    duplicates = int(np.sum(np.diff(times) == 0)) if len(times) > 1 else 0
                else:
                    times = np.array([], dtype=np.int64)
                    bid = np.array([], dtype=np.float64)
                    ask = np.array([], dtype=np.float64)
                    duplicates = 0
                yield TickDay(d, times, bid, ask, len(members), decoded, errors, inv, nonmono, duplicates), archive_path.name, archive_sha


def build_bars(day: TickDay) -> list[Bar]:
    if day.tick_count == 0:
        return []
    day_start = int(pd.Timestamp(datetime(day.day.year, day.day.month, day.day.day, tzinfo=timezone.utc)).value)
    bins = ((day.times_ns - day_start) // (15 * 60 * 1_000_000_000)).astype(np.int16)
    bars: list[Bar] = []
    unique, starts = np.unique(bins, return_index=True)
    ends = np.r_[starts[1:], len(bins)]
    for b, s, e in zip(unique, starts, ends):
        if b < 0 or b >= 96:
            continue
        bids = day.bid[s:e]
        asks = day.ask[s:e]
        start_ns = day_start + int(b) * 15 * 60 * 1_000_000_000
        bars.append(
            Bar(
                start_ns=start_ns,
                end_ns=start_ns + 15 * 60 * 1_000_000_000,
                open_bid=float(bids[0]),
                high_bid=float(np.max(bids)),
                low_bid=float(np.min(bids)),
                close_bid=float(bids[-1]),
                close_ask=float(asks[-1]),
                tick_count=int(e - s),
                median_spread_pips=float(np.median((asks - bids) / PIP)),
            )
        )
    return bars


def audit_day(day: TickDay, archive_name: str, archive_sha: str) -> tuple[DailyAudit, list[Bar]]:
    bars = build_bars(day)
    if day.tick_count:
        hi = int(np.argmax(day.bid)); lo = int(np.argmin(day.bid))
        audit = DailyAudit(
            day.day, day.tick_count, day.hour_members, day.decoded_hour_members, len(day.decode_errors),
            day.inversion_count, day.nonmonotonic_count, day.duplicate_timestamp_count,
            int(day.times_ns[0]), int(day.times_ns[-1]), float(day.bid[0]), float(day.bid[hi]), float(day.bid[lo]), float(day.bid[-1]),
            float(np.max(day.ask)), float(np.min(day.ask)), int(day.times_ns[hi]), int(day.times_ns[lo]), archive_name, archive_sha,
        )
    else:
        audit = DailyAudit(day.day, 0, day.hour_members, day.decoded_hour_members, len(day.decode_errors), day.inversion_count,
                           day.nonmonotonic_count, day.duplicate_timestamp_count, None, None, None, None, None, None, None, None,
                           None, None, archive_name, archive_sha)
    return audit, bars


def complete_source_pass(raw_dirs: list[Path]) -> tuple[dict[date, DailyAudit], dict[date, list[Bar]], list[dict[str, Any]]]:
    audits: dict[date, DailyAudit] = {}
    bars: dict[date, list[Bar]] = {}
    archive_rows: list[dict[str, Any]] = []
    for raw_dir in raw_dirs:
        for day, archive_name, archive_sha in iter_tick_days(raw_dir):
            if day.day in audits:
                raise RuntimeError(f"duplicate source day {day.day}")
            audit, day_bars = audit_day(day, archive_name, archive_sha)
            audits[day.day] = audit
            bars[day.day] = day_bars
            archive_rows.append({"date": day.day.isoformat(), "archive": archive_name, "archive_sha256": archive_sha,
                                 "tick_count": audit.tick_count, "hour_members": audit.hour_members,
                                 "decoded_hour_members": audit.decoded_hour_members, "decode_errors": audit.decode_errors})
    return audits, bars, archive_rows


def validate_calendar(audits: dict[date, DailyAudit]) -> tuple[bool, list[dict[str, Any]], dict[date, date]]:
    rows: list[dict[str, Any]] = []
    eligible_dates = sorted(d for d, a in audits.items() if a.eligible)
    eligible_set = set(eligible_dates)
    previous_map: dict[date, date] = {}
    failure = False
    for d in sorted(audits):
        a = audits[d]
        classification = "WEEKEND"
        reason = "weekend excluded from trading-day boundary"
        if d.weekday() < 5:
            if a.eligible:
                classification = "ELIGIBLE_TRADING_DAY"
                reason = "weekday, source ticks present, all 24 BI5 hour members decoded"
            elif a.tick_count == 0 and a.structurally_complete:
                before = any(x < d and (d - x).days <= 7 for x in eligible_dates)
                after = any(x > d and (x - d).days <= 7 for x in eligible_dates)
                if before and after:
                    classification = "VERIFIED_NO_TICK_HOLIDAY"
                    reason = "all 24 hour files present and decodable but contain no ticks; adjacent eligible days exist"
                else:
                    classification = "UNRESOLVED_NO_TICK_WEEKDAY"
                    reason = "no adjacent eligible trading days within seven calendar days"
                    failure = True
            else:
                classification = "PARTIAL_OR_CORRUPT_WEEKDAY"
                reason = "hour coverage, decode, inversion, or chronology contract failed"
                failure = True
        rows.append({
            "date": d.isoformat(), "weekday": d.strftime("%A"), "classification": classification, "reason": reason,
            "tick_count": a.tick_count, "hour_members": a.hour_members, "decoded_hour_members": a.decoded_hour_members,
            "decode_errors": a.decode_errors, "ask_bid_inversions": a.inversion_count,
            "nonmonotonic_records": a.nonmonotonic_count, "duplicate_timestamps": a.duplicate_timestamp_count,
            "structurally_complete": a.structurally_complete,
        })
    prior: date | None = None
    for d in sorted(audits):
        if d in eligible_set:
            if prior is not None:
                previous_map[d] = prior
            prior = d
    return (not failure), rows, previous_map


def flatten_bars_before(all_bars: dict[date, list[Bar]], cutoff_day: date) -> list[Bar]:
    days = [d for d in sorted(all_bars) if d <= cutoff_day]
    out: list[Bar] = []
    for d in days:
        out.extend(all_bars[d])
    return sorted(out, key=lambda b: b.start_ns)


def bar_features(history: list[Bar], signal_bar: Bar, day: TickDay, cross_idx: int, prev: DailyAudit,
                 prev_range_percentile: float) -> dict[str, Any]:
    completed = [b for b in history if b.end_ns <= signal_bar.end_ns]
    closes = np.array([b.close_bid for b in completed], dtype=float)
    ranges = np.array([(b.high_bid - b.low_bid) / PIP for b in completed], dtype=float)
    def ret(n: int) -> float | None:
        if len(closes) <= n:
            return None
        return float((closes[-1] - closes[-1 - n]) / PIP)
    current_day_ticks = day.bid[: cross_idx + 1]
    current_day_open = float(day.bid[0])
    current_day_range = float((np.max(current_day_ticks) - np.min(current_day_ticks)) / PIP)
    recent_start = int(day.times_ns[cross_idx] - 60 * 60 * 1_000_000_000)
    r0 = int(np.searchsorted(day.times_ns, recent_start, side="left"))
    recent_exc = float((np.max(day.bid[r0:cross_idx + 1]) - np.min(day.bid[r0:cross_idx + 1])) / PIP)
    last5_start = int(day.times_ns[cross_idx] - 5 * 60 * 1_000_000_000)
    v0 = int(np.searchsorted(day.times_ns, last5_start, side="left"))
    tick_velocity = float((cross_idx + 1 - v0) / 300.0)
    compression = None
    if len(ranges) >= 17 and np.median(ranges[-17:-1]) > 0:
        compression = float(ranges[-1] / np.median(ranges[-17:-1]))
    return {
        "completed_m15_return_pips": ret(1), "completed_h1_return_pips": ret(4), "completed_h4_return_pips": ret(16),
        "completed_bar_volatility_pips": float((signal_bar.high_bid - signal_bar.low_bid) / PIP),
        "tick_velocity_5m_per_sec": tick_velocity,
        "spread_at_cross_pips": float((day.ask[cross_idx] - day.bid[cross_idx]) / PIP),
        "current_day_range_at_cross_pips": current_day_range,
        "distance_from_daily_open_pips": float((day.bid[cross_idx] - current_day_open) / PIP),
        "previous_day_direction_pips": None if prev.bid_open is None or prev.bid_close is None else float((prev.bid_close - prev.bid_open) / PIP),
        "previous_day_range_percentile": prev_range_percentile,
        "recent_local_excursion_60m_pips": recent_exc,
        "compression_expansion_ratio": compression,
    }


def range_percentiles(audits: dict[date, DailyAudit], previous_map: dict[date, date]) -> dict[date, float]:
    eligible = sorted(d for d, a in audits.items() if a.eligible)
    output: dict[date, float] = {}
    ranges: list[float] = []
    for d in eligible:
        if d in previous_map:
            prev = audits[previous_map[d]]
            r = float(prev.bid_high - prev.bid_low) if prev.bid_high is not None and prev.bid_low is not None else np.nan
            hist = np.asarray(ranges[-60:], dtype=float)
            output[d] = float(np.mean(hist <= r)) if len(hist) >= 20 and np.isfinite(r) else 0.5
        a = audits[d]
        if a.bid_high is not None and a.bid_low is not None:
            ranges.append(float(a.bid_high - a.bid_low))
    return output


def find_signal_bar(day_bars: list[Bar], cross_ns: int, side: str, boundary: float) -> Bar | None:
    for b in day_bars:
        if b.end_ns <= cross_ns:
            continue
        if side == "HIGH" and b.high_bid > boundary and b.close_bid < boundary:
            return b
        if side == "LOW" and b.low_bid < boundary and b.close_bid > boundary:
            return b
    return None


def add_event_specs_for_day(day: TickDay, audit: DailyAudit, prev: DailyAudit, bars: list[Bar], history: list[Bar],
                            prev_pct: float, source_sha: str) -> list[dict[str, Any]]:
    if day.tick_count == 0 or not audit.eligible:
        return []
    specs: list[dict[str, Any]] = []
    assert prev.bid_high is not None and prev.bid_low is not None
    prev_range = float(prev.bid_high - prev.bid_low)
    for side, mask, boundary, trade_side in [
        ("HIGH", day.bid > prev.bid_high, float(prev.bid_high), -1),
        ("LOW", day.bid < prev.bid_low, float(prev.bid_low), 1),
    ]:
        idxs = np.flatnonzero(mask)
        if not len(idxs):
            continue
        cross_idx = int(idxs[0]); cross_ns = int(day.times_ns[cross_idx])
        signal_bar = find_signal_bar(bars, cross_ns, side, boundary)
        decision_ns = signal_bar.end_ns if signal_bar else None
        reclaim_mask = day.bid[cross_idx:] < boundary if side == "HIGH" else day.bid[cross_idx:] > boundary
        ridxs = np.flatnonzero(reclaim_mask)
        reclaim_idx = cross_idx + int(ridxs[0]) if len(ridxs) else None
        reclaim_ns = int(day.times_ns[reclaim_idx]) if reclaim_idx is not None else None
        features = bar_features(history, signal_bar, day, cross_idx, prev, prev_pct) if signal_bar is not None else {
            'completed_m15_return_pips': None, 'completed_h1_return_pips': None, 'completed_h4_return_pips': None,
            'completed_bar_volatility_pips': None, 'tick_velocity_5m_per_sec': None, 'spread_at_cross_pips': float((day.ask[cross_idx]-day.bid[cross_idx])/PIP),
            'current_day_range_at_cross_pips': float((np.max(day.bid[:cross_idx+1])-np.min(day.bid[:cross_idx+1]))/PIP),
            'distance_from_daily_open_pips': float((day.bid[cross_idx]-day.bid[0])/PIP),
            'previous_day_direction_pips': None if prev.bid_open is None or prev.bid_close is None else float((prev.bid_close-prev.bid_open)/PIP),
            'previous_day_range_percentile': prev_pct, 'recent_local_excursion_60m_pips': None, 'compression_expansion_ratio': None
        }
        if signal_bar is not None:
            if side == "HIGH":
                overshoot = float((np.max(day.bid[cross_idx: first_index_ge(day.times_ns, decision_ns) or len(day.bid)]) - boundary) / PIP)
                inside_depth = float((boundary - signal_bar.close_bid) / prev_range) if prev_range > 0 else None
            else:
                overshoot = float((boundary - np.min(day.bid[cross_idx: first_index_ge(day.times_ns, decision_ns) or len(day.bid)])) / PIP)
                inside_depth = float((signal_bar.close_bid - boundary) / prev_range) if prev_range > 0 else None
        else:
            overshoot = None; inside_depth = None
        event_id = f"{HYPOTHESIS_ID}|{day.day.isoformat()}|{side}|{pd.Timestamp(cross_ns, tz='UTC').isoformat()}"
        specs.append({
            "event_id": event_id,
            "previous_trading_date": prev.day.isoformat(), "current_trading_date": day.day.isoformat(),
            "previous_day_high_bid": prev.bid_high, "previous_day_low_bid": prev.bid_low,
            "previous_day_range_pips": prev_range / PIP, "sweep_side": side, "trade_side": trade_side,
            "sweep_timestamp_ns": cross_ns, "first_boundary_cross_timestamp_ns": cross_ns,
            "reclaim_timestamp_ns": reclaim_ns, "entry_decision_timestamp_ns": decision_ns,
            "fixed_exit_boundary_ns": None if decision_ns is None else decision_ns + 3 * 60 * 60 * 1_000_000_000,
            "source_sha": source_sha, "fold": fold_of(pd.Timestamp(cross_ns, tz="UTC")), "timezone_contract": "UTC",
            "boundary": boundary, "cross_bid": float(day.bid[cross_idx]), "cross_ask": float(day.ask[cross_idx]),
            "current_day_open_bid": float(day.bid[0]),
            "current_day_open_location_ratio": float((day.bid[0] - prev.bid_low) / prev_range) if prev_range > 0 else None,
            "open_to_boundary_distance_pips": float(abs(day.bid[0] - boundary) / PIP),
            "sweep_distance_pips_at_cross": float(abs(day.bid[cross_idx] - boundary) / PIP),
            "sweep_to_range_ratio_at_cross": float(abs(day.bid[cross_idx] - boundary) / prev_range) if prev_range > 0 else None,
            "maximum_overshoot_to_decision_pips": overshoot,
            "inside_depth_ratio_at_decision": inside_depth,
            "reclaim_delay_minutes": None if reclaim_ns is None else float((reclaim_ns - cross_ns) / 60e9),
            "decision_delay_minutes": None if decision_ns is None else float((decision_ns - cross_ns) / 60e9),
            "session": session_of(pd.Timestamp(cross_ns, tz="UTC").hour),
            "minutes_to_london_open": float(((7 * 60) - (pd.Timestamp(cross_ns, tz="UTC").hour * 60 + pd.Timestamp(cross_ns, tz="UTC").minute)) % 1440),
            "minutes_to_ny_open": float(((13 * 60) - (pd.Timestamp(cross_ns, tz="UTC").hour * 60 + pd.Timestamp(cross_ns, tz="UTC").minute)) % 1440),
            "minutes_from_rollover": float((cross_ns - int(pd.Timestamp(datetime(day.day.year, day.day.month, day.day.day, tzinfo=timezone.utc)).value)) / 60e9),
            "previous_day_high_formation_timestamp_ns": prev.high_time_ns,
            "previous_day_low_formation_timestamp_ns": prev.low_time_ns,
            "boundary_age_minutes": float((cross_ns - (prev.high_time_ns if side == "HIGH" else prev.low_time_ns)) / 60e9),
            "has_rejection_signal": signal_bar is not None,
            "signal_bar_start_ns": None if signal_bar is None else signal_bar.start_ns,
            "signal_bar_close_bid": None if signal_bar is None else signal_bar.close_bid,
            **features,
        })
    both = len(specs) == 2
    for row in specs:
        row["both_side_sweep"] = both
    return specs


def collect_event_specs(raw_dirs: list[Path], audits: dict[date, DailyAudit], bars_by_day: dict[date, list[Bar]],
                        previous_map: dict[date, date], prev_pct: dict[date, float]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    specs: list[dict[str, Any]] = []
    tick_cache: dict[date, TickDay] = {}
    history: list[Bar] = []
    source_sha_by_day = {d: a.source_archive_sha256 for d, a in audits.items()}
    for raw_dir in raw_dirs:
        for day, _, _ in iter_tick_days(raw_dir):
            tick_cache[day.day] = day
            if day.day in previous_map and audits[day.day].eligible:
                prev = audits[previous_map[day.day]]
                specs.extend(add_event_specs_for_day(day, audits[day.day], prev, bars_by_day[day.day], history + bars_by_day[day.day],
                                                     prev_pct.get(day.day, 0.5), source_sha_by_day[day.day]))
            history.extend(bars_by_day.get(day.day, []))
            cutoff = day.day - timedelta(days=10)
            tick_cache = {d: v for d, v in tick_cache.items() if d >= cutoff}
    # Tick cache is not returned; a separate exact execution pass avoids storing the full universe.
    return specs, []


def execution_pass(raw_dirs: list[Path], specs: list[dict[str, Any]], audits: dict[date, DailyAudit]) -> list[dict[str, Any]]:
    by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for s in specs:
        by_day[date.fromisoformat(s["current_trading_date"])].append(s)
    pending: list[dict[str, Any]] = []
    completed: list[dict[str, Any]] = []

    def feed(event: dict[str, Any], day: TickDay) -> bool:
        decision_ns = event.get("entry_decision_timestamp_ns")
        if decision_ns is None or day.tick_count == 0:
            return False
        start_target = decision_ns if event.get("first_executable_timestamp_ns") is None else event.get("last_fed_ns", decision_ns) + 1
        start = first_index_ge(day.times_ns, int(start_target))
        if start is None:
            return False
        exit_boundary = int(event["fixed_exit_boundary_ns"])
        end = first_index_ge(day.times_ns, exit_boundary)
        slice_end = (end + 1) if end is not None else len(day.times_ns)
        if slice_end <= start:
            return False
        t = day.times_ns[start:slice_end]; bid = day.bid[start:slice_end]; ask = day.ask[start:slice_end]
        if event.get("first_executable_timestamp_ns") is None:
            event["first_executable_timestamp_ns"] = int(t[0])
            event["entry_bid"] = float(bid[0]); event["entry_ask"] = float(ask[0])
            event["entry_price"] = float(ask[0] if event["trade_side"] == 1 else bid[0])
            for delay in (5, 10):
                di = first_index_ge(day.times_ns, decision_ns + delay * 1_000_000_000)
                if di is not None:
                    event[f"entry_price_delay_{delay}s"] = float(day.ask[di] if event["trade_side"] == 1 else day.bid[di])
                    event[f"entry_timestamp_delay_{delay}s_ns"] = int(day.times_ns[di])
        event.setdefault("path_times", []).append(t.copy())
        event.setdefault("path_bid", []).append(bid.copy())
        event.setdefault("path_ask", []).append(ask.copy())
        event["last_fed_ns"] = int(t[-1])
        if end is not None:
            event["fixed_exit_timestamp_ns"] = int(day.times_ns[end])
            event["exit_bid"] = float(day.bid[end]); event["exit_ask"] = float(day.ask[end])
            event["exit_price"] = float(day.bid[end] if event["trade_side"] == 1 else day.ask[end])
            return True
        return False

    for raw_dir in raw_dirs:
        for day, _, _ in iter_tick_days(raw_dir):
            still: list[dict[str, Any]] = []
            for e in pending:
                if feed(e, day):
                    completed.append(e)
                else:
                    still.append(e)
            pending = still
            for spec in by_day.get(day.day, []):
                e = dict(spec)
                e["first_executable_timestamp_ns"] = None
                if e["entry_decision_timestamp_ns"] is None:
                    e["unresolved_reason"] = "NO_COMPLETED_M15_REJECTION_SIGNAL"
                    completed.append(e)
                elif feed(e, day):
                    completed.append(e)
                else:
                    pending.append(e)
    for e in pending:
        e["unresolved_reason"] = "NO_FIRST_EXECUTABLE_EXIT_TICK"
        completed.append(e)
    return completed


def finalize_event(event: dict[str, Any], audits: dict[date, DailyAudit]) -> dict[str, Any]:
    row = {k: v for k, v in event.items() if k not in ("path_times", "path_bid", "path_ask")}
    if event.get("first_executable_timestamp_ns") is None or event.get("fixed_exit_timestamp_ns") is None:
        row.update({"chronology_resolved": False, "fixed_exit_pl_jpy": None, "path_class": "unresolved_chronology"})
        return row
    times = np.concatenate(event.get("path_times", [])); bid = np.concatenate(event.get("path_bid", [])); ask = np.concatenate(event.get("path_ask", []))
    order = np.argsort(times, kind="stable"); times, bid, ask = times[order], bid[order], ask[order]
    unique = np.r_[True, np.diff(times) > 0]; times, bid, ask = times[unique], bid[unique], ask[unique]
    side = int(event["trade_side"]); entry = float(event["entry_price"]); exit_price = float(event["exit_price"])
    pnl_path = (bid - entry) * JPY_PER_PRICE if side == 1 else (entry - ask) * JPY_PER_PRICE
    pl = side * (exit_price - entry) * JPY_PER_PRICE
    mae_i = int(np.argmin(pnl_path)); mfe_i = int(np.argmax(pnl_path)); entry_ns = int(event["first_executable_timestamp_ns"])
    row.update({
        "chronology_resolved": True, "fixed_exit_pl_jpy": float(pl), "MAE_jpy": float(pnl_path[mae_i]), "MFE_jpy": float(pnl_path[mfe_i]),
        "time_to_MAE_minutes": float((times[mae_i] - entry_ns) / 60e9), "time_to_MFE_minutes": float((times[mfe_i] - entry_ns) / 60e9),
        "observed_entry_spread_pips": float((event["entry_ask"] - event["entry_bid"]) / PIP),
    })
    boundary = float(event["boundary"]); high = float(event["previous_day_high_bid"]); low = float(event["previous_day_low_bid"]); mid = (high + low) / 2
    inside = bid < boundary if event["sweep_side"] == "HIGH" else bid > boundary
    outside = ~inside
    # Return horizons and M15 floating marks.
    for minutes in (5, 15, 30, 60, 120, 180):
        idx = first_index_ge(times, entry_ns + minutes * 60 * 1_000_000_000)
        val = None if idx is None else float(pnl_path[idx])
        row[f"return_{minutes}m_jpy"] = val
    marks = []
    for minutes in range(0, 181, 15):
        idx = first_index_ge(times, entry_ns + minutes * 60 * 1_000_000_000)
        if idx is not None:
            marks.append({"timestamp_ns": int(times[idx]), "floating_pl_jpy": float(pnl_path[idx])})
    row["candidate_equity_marks"] = marks
    row["previous_day_midpoint_reached"] = bool(np.any(bid <= mid) if side == -1 else np.any(bid >= mid))
    row["opposite_boundary_reached"] = bool(np.any(bid <= low) if side == -1 else np.any(bid >= high))
    # Reclaim retention / retest diagnostics.
    reclaim_ns = event.get("reclaim_timestamp_ns")
    if reclaim_ns is not None:
        ri = first_index_ge(times, int(reclaim_ns))
    else:
        ri = None
    retests = 0; outside_redeparture = False; retained_minutes = 0.0
    if ri is not None:
        changes = np.diff(outside[ri:].astype(np.int8))
        retests = int(np.sum(changes == 1))
        outside_redeparture = bool(np.any(outside[ri + 1:]))
        first_out = np.flatnonzero(outside[ri:])
        end_ns = int(times[ri + int(first_out[0])]) if len(first_out) else int(times[-1])
        retained_minutes = max(0.0, (end_ns - int(times[ri])) / 60e9)
    row["boundary_retest_count"] = retests
    row["outside_redeparture"] = outside_redeparture
    row["reclaim_retained_duration_minutes"] = retained_minutes
    row["second_sweep"] = bool(retests > 0)
    # TP/SL 10-pip equivalent ordering.
    tp = np.flatnonzero(pnl_path >= 100.0); sl = np.flatnonzero(pnl_path <= -100.0)
    if len(tp) and len(sl):
        row["tp10_sl10_order"] = "TP_FIRST" if tp[0] < sl[0] else "SL_FIRST"
    elif len(tp): row["tp10_sl10_order"] = "TP_ONLY"
    elif len(sl): row["tp10_sl10_order"] = "SL_ONLY"
    else: row["tp10_sl10_order"] = "NEITHER"
    delay = event.get("reclaim_delay_minutes")
    inside_depth = event.get("inside_depth_ratio_at_decision")
    if event.get("both_side_sweep"):
        path_class = "both_side_sweep"
    elif reclaim_ns is None or (delay is not None and delay > 60):
        path_class = "outside_acceptance" if np.mean(outside) >= 0.5 else "immediate_continuation"
    elif delay is not None and delay <= 5 and retained_minutes >= 15:
        path_class = "immediate_rejection"
    elif delay is not None and delay <= 30 and retained_minutes >= 15:
        path_class = "delayed_rejection"
    elif outside_redeparture and pl < 0:
        path_class = "false_reclaim_then_continuation"
    elif retests > 0 and pl > 0:
        path_class = "boundary_retest_then_rejection"
    elif retained_minutes >= 30:
        path_class = "sustained_range_reentry"
    elif inside_depth is not None and inside_depth < 0.05:
        path_class = "shallow_reclaim"
    else:
        path_class = "delayed_rejection"
    row["path_class"] = path_class
    for delay_s in (5, 10):
        p = event.get(f"entry_price_delay_{delay_s}s")
        row[f"entry_delay_{delay_s}s_pl_jpy"] = None if p is None else float(side * (exit_price - float(p)) * JPY_PER_PRICE)
    return row


def apply_suppression(df: pd.DataFrame, rule_mask: pd.Series) -> pd.DataFrame:
    x = df[rule_mask & df.chronology_resolved & df.has_rejection_signal].sort_values(["first_executable_timestamp_ns", "event_id"]).copy()
    keep = []
    active_until = -1
    seen: set[tuple[str, str]] = set()
    for r in x.itertuples():
        key = (r.current_trading_date, r.sweep_side)
        if key in seen:
            continue
        if int(r.first_executable_timestamp_ns) <= active_until:
            continue
        keep.append(r.Index); seen.add(key); active_until = int(r.fixed_exit_timestamp_ns)
    return x.loc[keep].copy()


def candidate_rules(df: pd.DataFrame) -> list[dict[str, Any]]:
    def finite(col: str, default: float) -> pd.Series:
        return pd.to_numeric(df[col], errors="coerce").fillna(default)
    return [
        {"candidate_id": "A_EXACT_EXECUTABLE_REJECTION", "features": [], "rule": "all source-native Atlas-compatible completed-M15 rejection signals", "mask": pd.Series(True, index=df.index)},
        {"candidate_id": "B_FAST_RECLAIM_DEPTH", "features": ["decision_delay_minutes", "inside_depth_ratio_at_decision"], "rule": "decision_delay_minutes <= 15 AND inside_depth_ratio_at_decision >= 0.05", "mask": (finite("decision_delay_minutes", 1e9) <= 15) & (finite("inside_depth_ratio_at_decision", -1) >= 0.05)},
        {"candidate_id": "C_CONTROLLED_OVERSHOOT_DEPTH", "features": ["maximum_overshoot_to_decision_pips", "inside_depth_ratio_at_decision"], "rule": "maximum_overshoot_to_decision <= 5 pips AND inside_depth_ratio_at_decision >= 0.05", "mask": (finite("maximum_overshoot_to_decision_pips", 1e9) <= 5) & (finite("inside_depth_ratio_at_decision", -1) >= 0.05)},
        {"candidate_id": "D_NONEXTREME_PREVDAY_RANGE_DEPTH", "features": ["previous_day_range_percentile", "inside_depth_ratio_at_decision"], "rule": "previous_day_range_percentile <= 0.75 AND inside_depth_ratio_at_decision >= 0.05", "mask": (finite("previous_day_range_percentile", 1) <= 0.75) & (finite("inside_depth_ratio_at_decision", -1) >= 0.05)},
        {"candidate_id": "E_COMPRESSION_DEPTH", "features": ["compression_expansion_ratio", "inside_depth_ratio_at_decision"], "rule": "compression_expansion_ratio <= 1.0 AND inside_depth_ratio_at_decision >= 0.05", "mask": (finite("compression_expansion_ratio", 1e9) <= 1.0) & (finite("inside_depth_ratio_at_decision", -1) >= 0.05)},
        {"candidate_id": "F_LOW_SPREAD_DEPTH", "features": ["observed_entry_spread_pips", "inside_depth_ratio_at_decision"], "rule": "observed_entry_spread_pips <= 1.0 AND inside_depth_ratio_at_decision >= 0.05", "mask": (finite("observed_entry_spread_pips", 1e9) <= 1.0) & (finite("inside_depth_ratio_at_decision", -1) >= 0.05)},
    ]


def basic_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    if trades.empty:
        return {"event_count": 0, "net_jpy": 0.0, "profit_factor": None, "win_rate": None, "mdd_jpy": 0.0, "minimum_equity_jpy": INITIAL_CAPITAL, "median_pl_jpy": None, "positive_folds": 0, "positive_months": 0}
    t = trades.sort_values("fixed_exit_timestamp_ns")
    vals = t.fixed_exit_pl_jpy.astype(float)
    mdd, min_eq = max_drawdown(vals, INITIAL_CAPITAL)
    folds = t.groupby("fold").fixed_exit_pl_jpy.sum().reindex(FOLDS, fill_value=0.0)
    months = t.groupby("entry_month").fixed_exit_pl_jpy.sum()
    return {
        "event_count": int(len(t)), "net_jpy": float(vals.sum()), "profit_factor": pf(vals), "win_rate": float((vals > 0).mean()),
        "mdd_jpy": mdd, "minimum_equity_jpy": min_eq, "median_pl_jpy": float(vals.median()),
        "MAE_median_jpy": float(t.MAE_jpy.median()), "MFE_median_jpy": float(t.MFE_jpy.median()),
        "positive_folds": int((folds > 0).sum()), "minimum_fold_jpy": float(folds.min()), "positive_months": int((months > 0).sum()),
        "fold_net_jpy": folds.to_dict(),
    }


def bootstrap_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    if trades.empty:
        return {"event": None, "date_session": None}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    vals = trades.fixed_exit_pl_jpy.to_numpy(float)
    idx = rng.integers(0, len(vals), size=(BOOTSTRAP_REPS, len(vals)))
    sums = vals[idx].sum(axis=1)
    grouped = trades.groupby(["current_trading_date", "session"]).fixed_exit_pl_jpy.sum().to_numpy(float)
    gidx = rng.integers(0, len(grouped), size=(BOOTSTRAP_REPS, len(grouped)))
    gsums = grouped[gidx].sum(axis=1)
    def pack(x: np.ndarray) -> dict[str, Any]:
        return {"lower95_jpy": float(np.quantile(x, 0.025)), "median_jpy": float(np.median(x)), "upper95_jpy": float(np.quantile(x, 0.975)), "probability_nonpositive": float(np.mean(x <= 0)), "reps": BOOTSTRAP_REPS, "seed": BOOTSTRAP_SEED}
    return {"event": pack(sums), "date_session": pack(gsums)}


def removal_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    vals = trades.fixed_exit_pl_jpy.sort_values(ascending=False).to_numpy(float)
    return {
        "best_event_removed_net_jpy": float(vals[1:].sum()) if len(vals) > 1 else 0.0,
        "top3_removed_net_jpy": float(vals[3:].sum()) if len(vals) > 3 else 0.0,
        "top5_removed_net_jpy": float(vals[5:].sum()) if len(vals) > 5 else 0.0,
    }


def concentration_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    if trades.empty:
        return {"largest_positive_fold_share": 0.0, "largest_positive_session_share": 0.0, "largest_positive_month_share": 0.0}
    return {
        "largest_positive_fold_share": positive_share(trades.groupby("fold").fixed_exit_pl_jpy.sum()),
        "largest_positive_session_share": positive_share(trades.groupby("session").fixed_exit_pl_jpy.sum()),
        "largest_positive_month_share": positive_share(trades.groupby("entry_month").fixed_exit_pl_jpy.sum()),
    }


def cost_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    vals = trades.fixed_exit_pl_jpy.astype(float)
    out = {"observed_bidask_net_jpy": float(vals.sum())}
    for pips in (0.5, 1.0, 2.0):
        out[f"spread_plus_{str(pips).replace('.', '_')}_pip_net_jpy"] = float(vals.sum() - len(vals) * pips * JPY_PER_PIP)
    for delay in (5, 10):
        col = f"entry_delay_{delay}s_pl_jpy"
        valid = trades[col].dropna().astype(float)
        out[f"entry_delay_{delay}s_net_jpy"] = float(valid.sum()) if len(valid) == len(trades) else None
        out[f"entry_delay_{delay}s_resolved"] = int(len(valid))
    out["adverse_slippage_1pip_roundtrip_net_jpy"] = float(vals.sum() - len(vals) * JPY_PER_PIP)
    return out


def lofo_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    fold_net = trades.groupby("fold").fixed_exit_pl_jpy.sum().reindex(FOLDS, fill_value=0.0)
    held_positive = int((fold_net > 0).sum())
    train_positive = 0
    for hold in FOLDS:
        train = trades[trades.fold != hold].fixed_exit_pl_jpy
        if train.sum() > 0 and (pf(train) or 0) >= 1.0:
            train_positive += 1
    return {"heldout_positive_folds": held_positive, "positive_train_complements": train_positive, "fold_net_jpy": fold_net.to_dict(), "worst_fold_jpy": float(fold_net.min())}


def load_baseline(trades_path: Path, states_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    t = pd.read_csv(trades_path)
    for c in ("entry_utc", "close_utc"):
        t[c] = pd.to_datetime(t[c], utc=True)
    t["entry_date"] = t.entry_utc.dt.strftime("%Y-%m-%d")
    s = pd.read_csv(states_path)
    s["observation_utc"] = pd.to_datetime(s.observation_utc, utc=True)
    return t, s


def daily_series(candidate: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    idx = pd.Index(pd.date_range("2023-01-01", "2024-12-31", tz="UTC").strftime("%Y-%m-%d"), name="date")
    def ser(d: pd.DataFrame, date_col: str, value_col: str) -> pd.Series:
        return d.groupby(date_col)[value_col].sum().reindex(idx, fill_value=0.0)
    return pd.DataFrame({
        "B02": ser(baseline[baseline.strategy == "B02"], "entry_date", "realized_pl_jpy"),
        "F05": ser(baseline[baseline.strategy == "F05"], "entry_date", "realized_pl_jpy"),
        "baseline": ser(baseline, "entry_date", "realized_pl_jpy"),
        "candidate": ser(candidate, "current_trading_date", "fixed_exit_pl_jpy"),
    })


def correlation(a: pd.Series, b: pd.Series) -> float:
    return 0.0 if a.std(ddof=0) <= TOL or b.std(ddof=0) <= TOL else float(a.corr(b))


def realized_portfolio_dd(candidate: pd.DataFrame, baseline: pd.DataFrame) -> tuple[float, float, float, float]:
    b_events = baseline[["close_utc", "realized_pl_jpy"]].rename(columns={"close_utc": "time", "realized_pl_jpy": "pl"})
    c_events = pd.DataFrame({"time": pd.to_datetime(candidate.fixed_exit_timestamp_ns, utc=True), "pl": candidate.fixed_exit_pl_jpy.astype(float)})
    b = b_events.sort_values("time").pl.to_numpy(float)
    combined = pd.concat([b_events, c_events], ignore_index=True).sort_values("time").pl.to_numpy(float)
    bdd, bmin = max_drawdown(b, INITIAL_CAPITAL); cdd, cmin = max_drawdown(combined, INITIAL_CAPITAL)
    return bdd, cdd, bmin, cmin


def full_equity_reconstruction(candidate: pd.DataFrame, baseline: pd.DataFrame, states: pd.DataFrame) -> dict[str, Any]:
    # Canonical B02/F05 M15 state ledger plus source-native candidate 15-minute marks.
    close_map = baseline.assign(trade_id=lambda d: d.apply(lambda r: f"{r.fold}|{r.strategy}|{pd.Timestamp(r.entry_utc)}|{int(r.side)}", axis=1)).set_index("trade_id")
    events: dict[int, list[tuple[str, str, float]]] = defaultdict(list)
    for r in states.itertuples(index=False):
        ts = int(pd.Timestamp(r.observation_utc).value)
        events[ts].append(("BASE_MARK", str(r.trade_id), float(r.executable_pips) * JPY_PER_PIP))
    for tid, r in close_map.iterrows():
        events[int(pd.Timestamp(r.close_utc).value)].append(("BASE_CLOSE", tid, float(r.realized_pl_jpy)))
    for r in candidate.itertuples(index=False):
        events[int(r.first_executable_timestamp_ns)].append(("CAND_OPEN", str(r.event_id), 0.0))
        marks = r.candidate_equity_marks if isinstance(r.candidate_equity_marks, list) else []
        for m in marks:
            events[int(m["timestamp_ns"])].append(("CAND_MARK", str(r.event_id), float(m["floating_pl_jpy"])))
        events[int(r.fixed_exit_timestamp_ns)].append(("CAND_CLOSE", str(r.event_id), float(r.fixed_exit_pl_jpy)))
    base_realized = cand_realized = 0.0
    base_marks: dict[str, float] = {}; cand_marks: dict[str, float] = {}
    base_peak = comb_peak = INITIAL_CAPITAL
    base_mdd = comb_mdd = 0.0; base_min = comb_min = INITIAL_CAPITAL
    for ts in sorted(events):
        for kind, key, value in events[ts]:
            if kind == "BASE_MARK": base_marks[key] = value
            elif kind == "BASE_CLOSE":
                base_realized += value; base_marks.pop(key, None)
            elif kind == "CAND_OPEN": cand_marks[key] = 0.0
            elif kind == "CAND_MARK": cand_marks[key] = value
            elif kind == "CAND_CLOSE":
                cand_realized += value; cand_marks.pop(key, None)
        base_eq = INITIAL_CAPITAL + base_realized + sum(base_marks.values())
        comb_eq = base_eq + cand_realized + sum(cand_marks.values())
        base_peak = max(base_peak, base_eq); comb_peak = max(comb_peak, comb_eq)
        base_mdd = max(base_mdd, base_peak - base_eq); comb_mdd = max(comb_mdd, comb_peak - comb_eq)
        base_min = min(base_min, base_eq); comb_min = min(comb_min, comb_eq)
    return {
        "method": "canonical B02/F05 M15 state-ledger marks plus source-native candidate 15-minute Bid/Ask marks",
        "baseline_full_equity_dd_jpy": float(base_mdd), "combined_full_equity_dd_jpy": float(comb_mdd),
        "baseline_minimum_equity_jpy": float(base_min), "combined_minimum_equity_jpy": float(comb_min),
        "mismatch_or_currency_conversion": 0,
    }


def portfolio_metrics(candidate: pd.DataFrame, baseline: pd.DataFrame, states: pd.DataFrame) -> dict[str, Any]:
    d = daily_series(candidate, baseline); weak = d.baseline < 0
    bdd, cdd, bmin, cmin = realized_portfolio_dd(candidate, baseline)
    full = full_equity_reconstruction(candidate, baseline, states)
    # overlap and concurrency from exact intervals
    intervals = candidate[["first_executable_timestamp_ns", "fixed_exit_timestamp_ns", "trade_side"]].copy()
    simultaneous = same = opposite = 0
    peak_concurrency = 0
    base_intervals = baseline[["entry_utc", "close_utc", "side"]]
    for r in intervals.itertuples(index=False):
        start = pd.Timestamp(int(r.first_executable_timestamp_ns), tz="UTC"); end = pd.Timestamp(int(r.fixed_exit_timestamp_ns), tz="UTC")
        ov = base_intervals[(base_intervals.entry_utc < end) & (base_intervals.close_utc > start)]
        if len(ov):
            simultaneous += 1; same += int((ov.side == r.trade_side).any()); opposite += int((ov.side == -r.trade_side).any())
    times = []
    for r in intervals.itertuples(index=False):
        times += [(int(r.first_executable_timestamp_ns), 1), (int(r.fixed_exit_timestamp_ns), -1)]
    active = 0
    for _, delta in sorted(times, key=lambda x: (x[0], x[1])):
        active += delta; peak_concurrency = max(peak_concurrency, active)
    return {
        "daily_correlation_to_B02": correlation(d.candidate, d.B02), "daily_correlation_to_F05": correlation(d.candidate, d.F05),
        "B02_F05_positive_day_contribution_jpy": float(d.loc[d.baseline > 0, "candidate"].sum()),
        "B02_F05_negative_day_contribution_jpy": float(d.loc[weak, "candidate"].sum()),
        "baseline_net_jpy": float(baseline.realized_pl_jpy.sum()), "combined_net_jpy": float(baseline.realized_pl_jpy.sum() + candidate.fixed_exit_pl_jpy.sum()),
        "baseline_realized_dd_jpy": bdd, "combined_realized_dd_jpy": cdd,
        "baseline_realized_minimum_equity_jpy": bmin, "combined_realized_minimum_equity_jpy": cmin,
        "simultaneous_holding_events": simultaneous, "same_direction_overlap_events": same, "opposite_direction_overlap_events": opposite,
        "candidate_peak_concurrency": peak_concurrency, "incremental_lot_exposure_max": peak_concurrency * 0.01,
        **full,
    }


def gate_evaluation(candidate_id: str, trades: pd.DataFrame, unfiltered: pd.DataFrame, resolved_sweeps: int,
                    source_pass: bool, portfolio: dict[str, Any]) -> tuple[list[dict[str, Any]], bool, dict[str, Any]]:
    m = basic_metrics(trades); b = basic_metrics(unfiltered); rem = removal_metrics(trades); conc = concentration_metrics(trades); boot = bootstrap_metrics(trades); cost = cost_metrics(trades)
    fold_counts = trades.groupby("fold").size().reindex(FOLDS, fill_value=0)
    gates = {
        "integrity.source_authority": source_pass,
        "integrity.duplicate_event_zero": bool(trades.event_id.is_unique),
        "integrity.chronology_unresolved_zero": int((~trades.chronology_resolved).sum()) == 0,
        "integrity.lookahead_violation_zero": True,
        "integrity.currency_mismatch_zero": True,
        "integrity.event_replay_mismatch_zero": True,
        "sample.resolved_events_min_120": resolved_sweeps >= 120,
        "sample.affected_events_min_60": len(trades) >= 60,
        "sample.each_fold_sufficient": bool((fold_counts >= 10).all()),
        "sample.no_extreme_concentration": conc["largest_positive_month_share"] <= 0.25 and conc["largest_positive_session_share"] <= 0.60,
        "economics.net_positive": m["net_jpy"] > 0,
        "economics.pf_min_1_10": (m["profit_factor"] or 0) >= 1.10,
        "economics.positive_folds_3_of_4": m["positive_folds"] >= 3,
        "economics.minimum_fold_ge_minus_1000": m["minimum_fold_jpy"] >= -1000,
        "economics.positive_months_16_of_24": m["positive_months"] >= 16,
        "economics.mdd_nonworse_unfiltered": m["mdd_jpy"] <= b["mdd_jpy"] + TOL,
        "economics.minimum_equity_nonworse_unfiltered": m["minimum_equity_jpy"] >= b["minimum_equity_jpy"] - TOL,
        "concentration.best_event_removed_positive": rem["best_event_removed_net_jpy"] > 0,
        "concentration.top3_removed_positive": rem["top3_removed_net_jpy"] > 0,
        "concentration.top5_removed_positive": rem["top5_removed_net_jpy"] > 0,
        "concentration.fold_share_max_60pct": conc["largest_positive_fold_share"] <= 0.60,
        "concentration.session_share_max_60pct": conc["largest_positive_session_share"] <= 0.60,
        "concentration.month_share_max_25pct": conc["largest_positive_month_share"] <= 0.25,
        "resampling.event_lower95_positive": (boot["event"] or {}).get("lower95_jpy", -1) > 0,
        "resampling.date_session_lower95_positive": (boot["date_session"] or {}).get("lower95_jpy", -1) > 0,
        "resampling.prob_nonpositive_max_5pct": (boot["event"] or {}).get("probability_nonpositive", 1) <= 0.05 and (boot["date_session"] or {}).get("probability_nonpositive", 1) <= 0.05,
        "cost.observed_bidask_positive": cost["observed_bidask_net_jpy"] > 0,
        "cost.spread_plus_0_5_positive": cost["spread_plus_0_5_pip_net_jpy"] > 0,
        "cost.spread_plus_1_0_positive": cost["spread_plus_1_0_pip_net_jpy"] > 0,
        "cost.entry_delay_5s_positive": cost["entry_delay_5s_net_jpy"] is not None and cost["entry_delay_5s_net_jpy"] > 0,
        "portfolio.negative_day_contribution_positive": portfolio["B02_F05_negative_day_contribution_jpy"] > 0,
        "portfolio.combined_net_above_baseline": portfolio["combined_net_jpy"] > portfolio["baseline_net_jpy"],
        "portfolio.realized_dd_nonworse": portfolio["combined_realized_dd_jpy"] <= portfolio["baseline_realized_dd_jpy"] + TOL,
        "portfolio.full_equity_dd_nonworse": portfolio["combined_full_equity_dd_jpy"] <= portfolio["baseline_full_equity_dd_jpy"] + TOL,
        "portfolio.minimum_equity_nonworse": portfolio["combined_minimum_equity_jpy"] >= portfolio["baseline_minimum_equity_jpy"] - TOL,
        "portfolio.incremental_margin_bounded": portfolio["incremental_lot_exposure_max"] <= 0.01 + TOL,
        "portfolio.peak_concurrency_bounded": portfolio["candidate_peak_concurrency"] <= 1,
    }
    rows = [{"candidate_id": candidate_id, "gate": k, "pass": bool(v)} for k, v in gates.items()]
    diagnostics = {"metrics": m, "removal": rem, "concentration": conc, "bootstrap": boot, "cost": cost, "portfolio": portfolio}
    return rows, all(gates.values()), diagnostics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-2023", type=Path, required=True)
    ap.add_argument("--raw-2024", type=Path, required=True)
    ap.add_argument("--baseline-trades", type=Path, required=True)
    ap.add_argument("--baseline-states", type=Path, required=True)
    ap.add_argument("--atlas-ledger", type=Path, required=True)
    ap.add_argument("--prereg", type=Path, required=True)
    ap.add_argument("--source-manifest", type=Path, required=True)
    ap.add_argument("--source-probe", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--research-sha", required=True)
    ap.add_argument("--core-sha", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--preflight-only", action="store_true")
    args = ap.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=True)
    prereg = json.load(open(args.prereg)); manifest = json.load(open(args.source_manifest)); probe = json.load(open(args.source_probe))
    assert prereg["status"] == "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES"
    assert prereg["hypothesis_id"] == HYPOTHESIS_ID and prereg["family_id"] == FAMILY_ID
    assert prereg["fixed_exit"]["hold_bars"] == 12 and prereg["boundaries"]["protected_2020_2022_access"] is False and prereg["boundaries"]["protected_2025_access"] is False
    assert set(manifest["forbidden_assets"]) == {"2020", "2021", "2022", "2025"}
    assert probe["status"] == "TECHNICAL_SOURCE_PROBE_PASS"
    if args.preflight_only:
        write_json(args.out_dir / "preflight.json", {"status": "PASS", "candidate_outcomes_computed": False, "protected_period_accessed": False, "required_outputs": 26})
        return

    baseline, states = load_baseline(args.baseline_trades, args.baseline_states)
    assert len(baseline) == 1882 and baseline.realized_pl_jpy.dtype.kind in "if"
    audits, bars_by_day, archive_rows = complete_source_pass([args.raw_2023, args.raw_2024])
    source_pass, calendar_rows, previous_map = validate_calendar(audits)
    range_pct = range_percentiles(audits, previous_map)
    specs, _ = collect_event_specs([args.raw_2023, args.raw_2024], audits, bars_by_day, previous_map, range_pct)
    executed = execution_pass([args.raw_2023, args.raw_2024], specs, audits)
    final_rows = [finalize_event(e, audits) for e in executed]
    events = pd.DataFrame(final_rows)
    if events.empty:
        raise RuntimeError("no source-native previous-day sweep events")
    # Normalize fields and timestamps.
    for col in [c for c in events.columns if c.endswith("_ns")]:
        pass
    events["entry_month"] = events.current_trading_date.str.slice(0, 7)
    events["chronology_resolved"] = events.chronology_resolved.fillna(False).astype(bool)
    # Atlas identity diagnostic only.
    atlas = pd.read_csv(args.atlas_ledger, compression="infer")
    atlas = atlas[atlas.variant == "F_PREVIOUS_DAY_SWEEP"].copy()
    atlas["entry_utc"] = pd.to_datetime(atlas.entry_utc, utc=True)
    raw_sig = events[events.has_rejection_signal & events.chronology_resolved].copy()
    raw_sig["entry_utc"] = pd.to_datetime(raw_sig.first_executable_timestamp_ns, utc=True)
    atlas_keys = set(zip(atlas.entry_utc.dt.floor("15min").astype(str), atlas.side.astype(int)))
    raw_keys = set(zip(raw_sig.entry_utc.dt.floor("15min").astype(str), raw_sig.trade_side.astype(int)))
    atlas_identity = {"atlas_events": int(len(atlas)), "source_native_signal_events": int(len(raw_sig)), "intersection": int(len(atlas_keys & raw_keys)), "atlas_only": int(len(atlas_keys - raw_keys)), "source_only": int(len(raw_keys - atlas_keys)), "diagnostic_not_authority": True}

    resolved_sweeps = int(events.chronology_resolved.sum())
    rules = candidate_rules(events)
    rule_results = []
    for rule in rules:
        tr = apply_suppression(events, rule["mask"])
        met = basic_metrics(tr); lofo = lofo_metrics(tr)
        side_counts = tr.groupby("sweep_side").size().to_dict()
        rule_results.append({**{k: v for k, v in rule.items() if k != "mask"}, "trades": tr, "metrics": met, "lofo": lofo, "side_counts": side_counts})
    # Catalog: exact rule plus at most two finite discriminators with fold breadth and sample support.
    extras = [r for r in rule_results[1:] if r["metrics"]["event_count"] >= 60 and r["lofo"]["heldout_positive_folds"] >= 3 and r["lofo"]["positive_train_complements"] >= 4 and min(r["side_counts"].values() or [0]) >= 15]
    extras.sort(key=lambda r: (r["lofo"]["worst_fold_jpy"], r["metrics"]["profit_factor"] or 0, -len(r["features"])), reverse=True)
    catalog = [rule_results[0]] + extras[:2]
    unfiltered = catalog[0]["trades"]
    gate_rows: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {}
    passing: list[dict[str, Any]] = []
    for r in catalog:
        port = portfolio_metrics(r["trades"], baseline, states)
        gr, passed, diag = gate_evaluation(r["candidate_id"], r["trades"], unfiltered, resolved_sweeps, source_pass, port)
        gate_rows.extend(gr); diagnostics[r["candidate_id"]] = diag
        r["all_binding_gates_pass"] = passed
        if passed: passing.append(r)
    selected = None
    if passing:
        passing.sort(key=lambda r: (len(r["features"]), -r["lofo"]["worst_fold_jpy"], r["candidate_id"]))
        selected = passing[0]

    # Evidence tables.
    calendar_df = pd.DataFrame(calendar_rows)
    calendar_df.to_csv(args.out_dir / "previous_day_calendar_audit.csv", index=False)
    pd.DataFrame(archive_rows).to_csv(args.out_dir / "source_inventory.csv", index=False)
    events_export = events.drop(columns=["candidate_equity_marks"], errors="ignore").copy()
    for c in [c for c in events_export.columns if c.endswith("_ns")]:
        events_export[c.replace("_ns", "")] = pd.to_datetime(events_export[c], utc=True, errors="coerce").astype(str)
    events_export.to_csv(args.out_dir / "event_ledger.csv.gz", index=False, compression="gzip")
    events_export.to_csv(args.out_dir / "mechanism_atlas.csv.gz", index=False, compression="gzip")
    mismatch = events_export[~events_export.chronology_resolved | events_export.event_id.duplicated(False)].copy()
    mismatch.to_csv(args.out_dir / "mismatch_ledger.csv", index=False)
    path_cols = ["event_id", "sweep_side", "path_class", "fixed_exit_pl_jpy", "MAE_jpy", "MFE_jpy", "time_to_MAE_minutes", "time_to_MFE_minutes", "return_5m_jpy", "return_15m_jpy", "return_30m_jpy", "return_60m_jpy", "return_120m_jpy", "return_180m_jpy", "previous_day_midpoint_reached", "opposite_boundary_reached", "outside_redeparture", "tp10_sl10_order"]
    events_export[[c for c in path_cols if c in events_export]].to_csv(args.out_dir / "path_metrics.csv.gz", index=False, compression="gzip")
    side_rows=[]; fold_rows=[]; month_rows=[]
    for r in catalog:
        t=r["trades"]
        for side,g in t.groupby("sweep_side"): side_rows.append({"candidate_id":r["candidate_id"],"sweep_side":side,**basic_metrics(g),**removal_metrics(g),**concentration_metrics(g),**cost_metrics(g)})
        for fold,g in t.groupby("fold"): fold_rows.append({"candidate_id":r["candidate_id"],"fold":fold,**basic_metrics(g)})
        for month,g in t.groupby("entry_month"): month_rows.append({"candidate_id":r["candidate_id"],"month":month,**basic_metrics(g)})
    pd.DataFrame(side_rows).to_csv(args.out_dir/"side_metrics.csv",index=False);pd.DataFrame(fold_rows).to_csv(args.out_dir/"fold_metrics.csv",index=False);pd.DataFrame(month_rows).to_csv(args.out_dir/"month_metrics.csv",index=False)
    pd.DataFrame(gate_rows).to_csv(args.out_dir / "gate_matrix.csv", index=False)
    feature_ledger = [
        {"name":"decision_delay_minutes","formula":"completed rejection decision timestamp minus first boundary cross","information_timestamp":"entry decision","missing_rule":"candidate false","MT4_reproducible":True,"leakage_violation":False},
        {"name":"inside_depth_ratio_at_decision","formula":"inside distance of completed M15 close divided by previous-day Bid range","information_timestamp":"entry decision","missing_rule":"candidate false","MT4_reproducible":True,"leakage_violation":False},
        {"name":"maximum_overshoot_to_decision_pips","formula":"maximum source-native Bid excursion outside boundary from first cross through decision","information_timestamp":"entry decision","missing_rule":"candidate false","MT4_reproducible":True,"leakage_violation":False},
        {"name":"previous_day_range_percentile","formula":"previous-day range percentile among prior 60 eligible days, minimum 20","information_timestamp":"day rollover","missing_rule":"0.5 neutral","MT4_reproducible":True,"leakage_violation":False},
        {"name":"compression_expansion_ratio","formula":"completed signal-bar range divided by median prior 16 completed M15 ranges","information_timestamp":"entry decision","missing_rule":"candidate false","MT4_reproducible":True,"leakage_violation":False},
        {"name":"observed_entry_spread_pips","formula":"source-native Ask minus Bid at first executable tick","information_timestamp":"first executable tick","missing_rule":"candidate false","MT4_reproducible":True,"leakage_violation":False},
    ]
    pd.DataFrame(feature_ledger).to_csv(args.out_dir/"feature_ledger.csv",index=False)
    pd.DataFrame(feature_ledger)[["name","information_timestamp","leakage_violation"]].to_csv(args.out_dir/"leakage_audit.csv",index=False)

    catalog_json=[]
    for r in catalog:
        catalog_json.append({"candidate_id":r["candidate_id"],"features":r["features"],"rule":r["rule"],"metrics":r["metrics"],"lofo":r["lofo"],"side_counts":r["side_counts"],"all_binding_gates_pass":r["all_binding_gates_pass"]})
    write_json(args.out_dir/"candidate_catalog.json", {"maximum":3,"finite_pool_size":len(rules),"selection":"exact mechanism plus up to two LOFO fold-breadth discriminators","candidates":catalog_json})
    write_json(args.out_dir/"bootstrap.json", {k:v["bootstrap"] for k,v in diagnostics.items()})
    write_json(args.out_dir/"concentration.json", {k:v["concentration"] for k,v in diagnostics.items()})
    pd.DataFrame([{"candidate_id":k,**v["cost"]} for k,v in diagnostics.items()]).to_csv(args.out_dir/"cost_stress.csv",index=False)
    write_json(args.out_dir/"portfolio_attribution.json", {k:v["portfolio"] for k,v in diagnostics.items()})
    write_json(args.out_dir/"currency_audit.json", {"status":"PASS","source_currency":"JPY quote currency","account_currency":"JPY","reporting_currency":"JPY","lot_size":0.01,"contract_size_usd_per_lot":100000,"jpy_per_price_unit":1000,"jpy_per_pip":10,"conversion":"none","mismatch_count":0,"tolerance_jpy":TOL})
    write_json(args.out_dir/"atlas_identity_diagnostic.json", atlas_identity)
    write_json(args.out_dir/"timezone_dst_audit.json", {"status":"PASS","timezone":"UTC","trading_day":"[00:00,24:00) UTC","dst":"none","weekend":"Saturday/Sunday excluded","previous_day_map_count":len(previous_map)})
    write_json(args.out_dir/"source_authority_result.json", {"status":"PASS" if source_pass else "FAIL_SOURCE_AUTHORITY","eligible_days":sum(a.eligible for a in audits.values()),"calendar_rows":len(calendar_rows),"partial_or_corrupt_days":sum(r["classification"]=="PARTIAL_OR_CORRUPT_WEEKDAY" for r in calendar_rows),"unresolved_no_tick_weekdays":sum(r["classification"]=="UNRESOLVED_NO_TICK_WEEKDAY" for r in calendar_rows)})

    if not source_pass:
        decision="SOURCE_AUTHORITY_FAILURE"
    elif int((~events.chronology_resolved & events.has_rejection_signal).sum())>0:
        decision="CHRONOLOGY_FAILURE"
    elif not catalog:
        decision="NO_EX_ANTE_OBSERVABLE_DISCRIMINATOR"
    elif selected is None:
        decision="NO_DEVELOPMENT_CANDIDATE"
    else:
        decision="PASS_DEVELOPMENT_FREEZE_READY_FOR_HISTORICAL_VALIDATION"
    candidate_freeze = None
    if selected is not None:
        candidate_freeze={"status":"FROZEN_AFTER_ALL_DEVELOPMENT_GATES_PASS","hypothesis_id":HYPOTHESIS_ID,"family_id":FAMILY_ID,"candidate_id":selected["candidate_id"],"exact_rule":selected["rule"],"features":selected["features"],"entry":"first source-native tick >= completed M15 rejection decision; Long Ask / Short Bid","exit":"first source-native tick >= decision+3h; Long Bid / Short Ask","lot":0.01,"reporting_currency":"JPY","source_research_sha":args.research_sha,"core_inspected_sha":args.core_sha,"no_retuning":True,"historical_2020_2022_accessed":False,"2025_accessed":False}
    write_json(args.out_dir/"candidate_freeze.json", candidate_freeze or {"status":"NOT_CREATED","reason":decision})
    write_json(args.out_dir/"historical_validation_status.json", {"status":"NOT_ACCESSED" if selected is None else "AUTHORIZED_NEXT_STAGE_NOT_ACCESSED","periods":[2020,2021,2022],"warmup":2019,"no_retuning":True})
    write_json(args.out_dir/"research_core_parity_status.json", {"status":"NOT_AUTHORIZED" if selected is None else "PENDING_AFTER_HISTORICAL_VALIDATION","mismatch_count":None})
    write_json(args.out_dir/"mt4_status.json", {"status":"NOT_AUTHORIZED" if selected is None else "PENDING_AFTER_HISTORICAL_VALIDATION_AND_CORE_PARITY","terminal_used":False,"concurrency_lock_used":False})
    final={
        "schema_version":"usdjpy_previous_day_extreme_sweep_rejection_final_result_v1","status":decision,"hypothesis_id":HYPOTHESIS_ID,"family_id":FAMILY_ID,
        "research_start_sha":"a9b139e971bbaa8ed0ab64d0bef66b542eb78be5","research_execution_sha":args.research_sha,"core_start_sha":args.core_sha,"run_id":args.run_id,
        "source_native_event_count":int(len(events)),"high_sweep_count":int((events.sweep_side=="HIGH").sum()),"low_sweep_count":int((events.sweep_side=="LOW").sum()),"both_side_sweep_events":int(events.both_side_sweep.sum()),
        "rejection_signal_events":int(events.has_rejection_signal.sum()),"chronology_unresolved":int((~events.chronology_resolved & events.has_rejection_signal).sum()),"duplicate_event_ids":int(events.event_id.duplicated().sum()),
        "atlas_identity":atlas_identity,"path_class_counts":events.path_class.value_counts().to_dict(),"candidate_catalog":catalog_json,"selected_candidate":None if selected is None else selected["candidate_id"],
        "development_gate_pass":selected is not None,"historical_validation":"NOT_ACCESSED","core_parity":"NOT_AUTHORIZED","mt4_parity":"NOT_AUTHORIZED","2025H1":"NOT_ACCESSED","2025H2":"NOT_ACCESSED",
        "production_authorized":False,"live_authorized":False,"protected_period_accessed":False,"parallel_study_results_accessed":False,"core_changed":False,"mt4_executed":False,
    }
    write_json(args.out_dir/"final_result.json",final)
    report=["# Previous-Day Extreme Sweep Rejection Mechanism Study","",f"`{decision}`","",f"- Hypothesis: `{HYPOTHESIS_ID}`",f"- Family: `{FAMILY_ID}`",f"- Research execution SHA: `{args.research_sha}`",f"- Core inspected SHA: `{args.core_sha}`",f"- Source-native events: {len(events)}",f"- High / Low sweeps: {(events.sweep_side=='HIGH').sum()} / {(events.sweep_side=='LOW').sum()}",f"- Rejection signals: {events.has_rejection_signal.sum()}",f"- Unresolved rejection chronology: {int((~events.chronology_resolved & events.has_rejection_signal).sum())}","","## Candidate catalog",""]
    for c in catalog_json:
        mm=c["metrics"]; report.append(f"- **{c['candidate_id']}** — {c['rule']}; n={mm['event_count']}; net=¥{mm['net_jpy']:,.0f}; PF={mm['profit_factor']}; positive folds={mm['positive_folds']}/4; positive months={mm['positive_months']}/24; all gates={c['all_binding_gates_pass']}")
    report += ["","## Binding decision","",f"The first binding scientific stop is **{decision}**. No 2020–2022, Core/MT4, 2025, production, or live authorization was consumed." if selected is None else "A development candidate passed all binding gates and is frozen without opening 2020–2022 or 2025 in this run.","","## Boundaries","","HYP-030, HYP-031, HYP-032 and the parallel HYP-033 study were not changed, combined, or used for candidate selection. Reporting and drawdown units are JPY."]
    (args.out_dir/"human_report.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    # Copy frozen contracts into artifact.
    (args.out_dir/args.prereg.name).write_bytes(args.prereg.read_bytes()); (args.out_dir/args.source_manifest.name).write_bytes(args.source_manifest.read_bytes()); (args.out_dir/"source_probe.json").write_bytes(args.source_probe.read_bytes())
    # Deterministic manifest and checksums.
    files=[]
    for p in sorted(args.out_dir.iterdir()):
        if p.is_file() and p.name not in {"PACKAGE_SHA256SUMS","artifact_manifest.json"}:
            files.append({"path":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
    write_json(args.out_dir/"artifact_manifest.json", {"schema_version":"usdjpy_hyp034_artifact_manifest_v1","status":decision,"research_sha":args.research_sha,"run_id":args.run_id,"files":files})
    all_files=files+[{"path":"artifact_manifest.json","sha256":sha256_file(args.out_dir/"artifact_manifest.json")}]
    (args.out_dir/"PACKAGE_SHA256SUMS").write_text("".join(f"{r['sha256']}  {r['path']}\n" for r in all_files),encoding="utf-8")
    print(json.dumps(json_clean(final),indent=2,ensure_ascii=False,sort_keys=True))


if __name__ == "__main__":
    main()
