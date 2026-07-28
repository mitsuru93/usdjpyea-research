#!/usr/bin/env python3
"""Source-native Dukascopy BI5 utilities for USDJPY-HYP-034.

This module is scientific-source plumbing only. It decodes immutable BI5 members,
constructs UTC tick days and M15 Bid/Ask bars, and exposes deterministic streaming
for path and full-equity replay. It contains no candidate selection or outcome gate.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import re
import struct
import tarfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

BI5_DTYPE = np.dtype([
    ("ms", ">u4"),
    ("ask_i", ">u4"),
    ("bid_i", ">u4"),
    ("ask_volume", ">f4"),
    ("bid_volume", ">f4"),
])
BI5_RECORD_BYTES = struct.calcsize(">3I2f")
PRICE_SCALE = 1000.0
M15_NS = 15 * 60 * 1_000_000_000
BI5_PATH = re.compile(r"(?:^|/)(20\d{2})/(\d{2})/(\d{2})/(\d{2})h_ticks\.bi5$")
DAY_PREFIX = re.compile(r"^(20\d{2}-\d{2}-\d{2})/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_ns(year: int, month: int, day: int, hour: int) -> int:
    return int(datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp() * 1_000_000_000)


def member_identity(name: str) -> tuple[str, int]:
    match = BI5_PATH.search(name)
    if not match:
        raise ValueError(f"invalid BI5 member path: {name}")
    year, month, day, hour = (int(value) for value in match.groups())
    return f"{year:04d}-{month:02d}-{day:02d}", utc_ns(year, month, day, hour)


def decode_bi5(payload: bytes, hour_ns: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    decoded = lzma.decompress(payload)
    if len(decoded) % BI5_RECORD_BYTES:
        raise ValueError(f"decoded BI5 size {len(decoded)} not divisible by {BI5_RECORD_BYTES}")
    if not decoded:
        empty_i = np.array([], dtype=np.int64)
        empty_f = np.array([], dtype=np.float64)
        return empty_i, empty_f, empty_f.copy(), empty_f.copy(), empty_f.copy()
    records = np.frombuffer(decoded, dtype=BI5_DTYPE)
    timestamps = hour_ns + records["ms"].astype(np.int64) * 1_000_000
    ask = records["ask_i"].astype(np.float64) / PRICE_SCALE
    bid = records["bid_i"].astype(np.float64) / PRICE_SCALE
    ask_volume = records["ask_volume"].astype(np.float64)
    bid_volume = records["bid_volume"].astype(np.float64)
    return timestamps, bid, ask, bid_volume, ask_volume


@dataclass
class TickDay:
    date_utc: str
    timestamp_ns: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    bid_volume: np.ndarray
    ask_volume: np.ndarray
    member_count: int
    nonempty_member_count: int
    source_archive: str
    source_archive_sha256: str
    day_summary: dict[str, Any] | None
    download_manifest_rows: int

    @property
    def empty(self) -> bool:
        return len(self.timestamp_ns) == 0

    @property
    def first_timestamp(self) -> pd.Timestamp | None:
        return None if self.empty else pd.Timestamp(int(self.timestamp_ns[0]), tz="UTC")

    @property
    def last_timestamp(self) -> pd.Timestamp | None:
        return None if self.empty else pd.Timestamp(int(self.timestamp_ns[-1]), tz="UTC")


class MonthlyArchive:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.sha256 = sha256_file(self.path)

    def iter_days(self) -> Iterator[TickDay]:
        with tarfile.open(self.path, "r:gz") as archive:
            members = [member for member in archive.getmembers() if member.isfile()]
            by_day: dict[str, list[tarfile.TarInfo]] = {}
            summaries: dict[str, dict[str, Any]] = {}
            manifest_rows: dict[str, int] = {}
            for member in members:
                prefix = DAY_PREFIX.match(member.name)
                if not prefix:
                    continue
                day = prefix.group(1)
                if member.name.endswith("day_summary.json"):
                    extracted = archive.extractfile(member)
                    if extracted is not None:
                        try:
                            summaries[day] = json.loads(extracted.read().decode("utf-8"))
                        except Exception as exc:
                            summaries[day] = {"parse_error": f"{type(exc).__name__}: {exc}"}
                elif member.name.endswith("download_manifest.jsonl"):
                    extracted = archive.extractfile(member)
                    if extracted is not None:
                        manifest_rows[day] = sum(1 for line in extracted.read().splitlines() if line.strip())
                elif member.name.lower().endswith(".bi5") and BI5_PATH.search(member.name):
                    by_day.setdefault(day, []).append(member)
            all_days = sorted(set(by_day) | set(summaries) | set(manifest_rows))
            for day in all_days:
                time_parts: list[np.ndarray] = []
                bid_parts: list[np.ndarray] = []
                ask_parts: list[np.ndarray] = []
                bid_volume_parts: list[np.ndarray] = []
                ask_volume_parts: list[np.ndarray] = []
                nonempty = 0
                day_members = sorted(by_day.get(day, []), key=lambda member: member.name)
                for member in day_members:
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise RuntimeError(f"cannot extract {member.name}")
                    _, hour_ns = member_identity(member.name)
                    timestamps, bid, ask, bid_volume, ask_volume = decode_bi5(extracted.read(), hour_ns)
                    if len(timestamps):
                        nonempty += 1
                        time_parts.append(timestamps)
                        bid_parts.append(bid)
                        ask_parts.append(ask)
                        bid_volume_parts.append(bid_volume)
                        ask_volume_parts.append(ask_volume)
                if time_parts:
                    timestamps = np.concatenate(time_parts)
                    bid = np.concatenate(bid_parts)
                    ask = np.concatenate(ask_parts)
                    bid_volume = np.concatenate(bid_volume_parts)
                    ask_volume = np.concatenate(ask_volume_parts)
                    order = np.argsort(timestamps, kind="stable")
                    timestamps, bid, ask = timestamps[order], bid[order], ask[order]
                    bid_volume, ask_volume = bid_volume[order], ask_volume[order]
                else:
                    timestamps = np.array([], dtype=np.int64)
                    bid = np.array([], dtype=np.float64)
                    ask = np.array([], dtype=np.float64)
                    bid_volume = np.array([], dtype=np.float64)
                    ask_volume = np.array([], dtype=np.float64)
                yield TickDay(
                    date_utc=day,
                    timestamp_ns=timestamps,
                    bid=bid,
                    ask=ask,
                    bid_volume=bid_volume,
                    ask_volume=ask_volume,
                    member_count=len(day_members),
                    nonempty_member_count=nonempty,
                    source_archive=self.path.name,
                    source_archive_sha256=self.sha256,
                    day_summary=summaries.get(day),
                    download_manifest_rows=manifest_rows.get(day, 0),
                )


def iter_tick_days(raw_dirs: list[Path]) -> Iterator[TickDay]:
    archives: list[Path] = []
    for raw_dir in raw_dirs:
        archives.extend(sorted(Path(raw_dir).glob("*.tar.gz")))
    if not archives:
        raise FileNotFoundError("no raw BI5 tar.gz archives")
    previous = ""
    for archive_path in sorted(archives):
        for tick_day in MonthlyArchive(archive_path).iter_days():
            if tick_day.date_utc < previous:
                raise ValueError("tick-day chronology is not monotonic")
            previous = tick_day.date_utc
            yield tick_day


def tick_day_audit(day: TickDay) -> dict[str, Any]:
    if day.empty:
        return {
            "date_utc": day.date_utc,
            "tick_count": 0,
            "first_tick_utc": None,
            "last_tick_utc": None,
            "bid_high": None,
            "bid_low": None,
            "bid_open": None,
            "bid_close": None,
            "ask_high": None,
            "ask_low": None,
            "ask_open": None,
            "ask_close": None,
            "ask_bid_inversion_count": 0,
            "duplicate_timestamp_count": 0,
            "nonmonotonic_timestamp_count": 0,
            "max_intertick_gap_seconds": None,
            "member_count": day.member_count,
            "nonempty_member_count": day.nonempty_member_count,
            "download_manifest_rows": day.download_manifest_rows,
            "source_archive": day.source_archive,
            "source_archive_sha256": day.source_archive_sha256,
            "day_summary_json": json.dumps(day.day_summary, sort_keys=True) if day.day_summary is not None else None,
        }
    delta = np.diff(day.timestamp_ns)
    return {
        "date_utc": day.date_utc,
        "tick_count": int(len(day.timestamp_ns)),
        "first_tick_utc": pd.Timestamp(int(day.timestamp_ns[0]), tz="UTC").isoformat(),
        "last_tick_utc": pd.Timestamp(int(day.timestamp_ns[-1]), tz="UTC").isoformat(),
        "bid_high": float(np.max(day.bid)),
        "bid_low": float(np.min(day.bid)),
        "bid_open": float(day.bid[0]),
        "bid_close": float(day.bid[-1]),
        "ask_high": float(np.max(day.ask)),
        "ask_low": float(np.min(day.ask)),
        "ask_open": float(day.ask[0]),
        "ask_close": float(day.ask[-1]),
        "ask_bid_inversion_count": int(np.sum(day.ask < day.bid)),
        "duplicate_timestamp_count": int(np.sum(delta == 0)),
        "nonmonotonic_timestamp_count": int(np.sum(delta < 0)),
        "max_intertick_gap_seconds": float(np.max(delta) / 1_000_000_000) if len(delta) else 0.0,
        "member_count": day.member_count,
        "nonempty_member_count": day.nonempty_member_count,
        "download_manifest_rows": day.download_manifest_rows,
        "source_archive": day.source_archive,
        "source_archive_sha256": day.source_archive_sha256,
        "day_summary_json": json.dumps(day.day_summary, sort_keys=True) if day.day_summary is not None else None,
    }


def m15_bars(day: TickDay) -> pd.DataFrame:
    columns = [
        "bar_start_utc", "first_tick_utc", "last_tick_utc", "bid_open", "bid_high", "bid_low", "bid_close",
        "ask_open", "ask_high", "ask_low", "ask_close", "spread_open_pips", "spread_close_pips",
        "spread_mean_pips", "spread_max_pips", "tick_count",
    ]
    if day.empty:
        return pd.DataFrame(columns=columns)
    bar_ids = day.timestamp_ns // M15_NS
    starts = np.flatnonzero(np.r_[True, bar_ids[1:] != bar_ids[:-1]])
    ends = np.r_[starts[1:], len(bar_ids)]
    rows: list[dict[str, Any]] = []
    for start, end in zip(starts, ends):
        spread = (day.ask[start:end] - day.bid[start:end]) / 0.01
        rows.append({
            "bar_start_utc": pd.Timestamp(int(bar_ids[start] * M15_NS), tz="UTC"),
            "first_tick_utc": pd.Timestamp(int(day.timestamp_ns[start]), tz="UTC"),
            "last_tick_utc": pd.Timestamp(int(day.timestamp_ns[end - 1]), tz="UTC"),
            "bid_open": float(day.bid[start]),
            "bid_high": float(np.max(day.bid[start:end])),
            "bid_low": float(np.min(day.bid[start:end])),
            "bid_close": float(day.bid[end - 1]),
            "ask_open": float(day.ask[start]),
            "ask_high": float(np.max(day.ask[start:end])),
            "ask_low": float(np.min(day.ask[start:end])),
            "ask_close": float(day.ask[end - 1]),
            "spread_open_pips": float(spread[0]),
            "spread_close_pips": float(spread[-1]),
            "spread_mean_pips": float(np.mean(spread)),
            "spread_max_pips": float(np.max(spread)),
            "tick_count": int(end - start),
        })
    return pd.DataFrame(rows, columns=columns)


def source_inventory(raw_dirs: list[Path]) -> dict[str, Any]:
    archives: list[dict[str, Any]] = []
    for raw_dir in raw_dirs:
        for path in sorted(Path(raw_dir).glob("*.tar.gz")):
            archives.append({"path": str(path), "name": path.name, "byte_size": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "schema_version": "usdjpy_hyp034_source_inventory_v1",
        "source": "Dukascopy BI5 Bid/Ask Tick",
        "format": "LZMA-compressed >3I2f records",
        "price_scale": PRICE_SCALE,
        "timezone": "UTC from terminal BI5 member suffix",
        "archives": archives,
        "archive_count": len(archives),
    }
