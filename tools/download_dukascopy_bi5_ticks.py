#!/usr/bin/env python3
"""Download and decode Dukascopy hourly BI5 tick files.

This is a source-specific downloader for public-data research outside MT4.
It writes gzip CSV tick files with UTC timestamps and bid/ask prices.

Important boundaries:
- This is not Rakuten MT4 data.
- This downloader uses Dukascopy as a public market proxy.
- Raw output should be stored as workflow artifacts or release assets, not committed to git.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import lzma
import random
import struct
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DUKASCOPY_SYMBOLS = {
    "EURUSD": "EURUSD",
    "USDJPY": "USDJPY",
    "GBPUSD": "GBPUSD",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "USDCHF": "USDCHF",
}

PIP_SCALE = {
    "EURUSD": 100000.0,
    "GBPUSD": 100000.0,
    "AUDUSD": 100000.0,
    "USDCAD": 100000.0,
    "USDCHF": 100000.0,
    "USDJPY": 1000.0,
}

BASE_URL = "https://datafeed.dukascopy.com/datafeed/{symbol}/{year}/{month_zero_based:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
RECORD_STRUCT = struct.Struct(">IIIff")
RETRYABLE_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}


@dataclass(frozen=True)
class HourSpec:
    symbol: str
    hour_start: dt.datetime

    @property
    def url(self) -> str:
        return BASE_URL.format(
            symbol=DUKASCOPY_SYMBOLS[self.symbol],
            year=self.hour_start.year,
            month_zero_based=self.hour_start.month - 1,
            day=self.hour_start.day,
            hour=self.hour_start.hour,
        )

    @property
    def output_relpath(self) -> Path:
        return Path(self.symbol) / f"{self.hour_start:%Y/%m/%d/%H}.csv.gz"


def iter_hours(start: dt.datetime, end: dt.datetime, symbols: list[str]) -> Iterable[HourSpec]:
    current = start
    while current < end:
        for symbol in symbols:
            yield HourSpec(symbol=symbol, hour_start=current)
        current += dt.timedelta(hours=1)


def parse_utc_hour(value: str) -> dt.datetime:
    raw = value.strip().replace("Z", "")
    if "T" not in raw:
        raw = raw + "T00:00:00"
    elif len(raw) == 13:
        raw = raw + ":00:00"
    parsed = dt.datetime.fromisoformat(raw)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed.replace(minute=0, second=0, microsecond=0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def retry_delay(attempt: int, base_seconds: float, retry_after: str | None = None) -> float:
    if retry_after:
        try:
            return max(float(retry_after), base_seconds)
        except ValueError:
            pass
    exponential = base_seconds * (2**attempt)
    jitter = random.uniform(0.0, max(0.1, base_seconds * 0.25))
    return exponential + jitter


def fetch_bytes(url: str, retries: int, sleep_seconds: float) -> bytes | None:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "usdjpyea-research/dukascopy-downloader",
                    "Accept": "application/octet-stream,*/*;q=0.8",
                    "Connection": "close",
                },
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = response.read()
                if not payload:
                    raise RuntimeError(f"empty response payload: {url}")
                return payload
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            last_error = exc
            if exc.code not in RETRYABLE_HTTP_CODES:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            delay = retry_delay(attempt, sleep_seconds, retry_after)
            print(
                f"retryable HTTP error code={exc.code} attempt={attempt + 1}/{retries + 1} "
                f"sleep={delay:.2f}s url={url}",
                file=sys.stderr,
            )
        except (urllib.error.URLError, TimeoutError, ConnectionError, RuntimeError) as exc:
            last_error = exc
            delay = retry_delay(attempt, sleep_seconds)
            print(
                f"retryable network error type={type(exc).__name__} attempt={attempt + 1}/{retries + 1} "
                f"sleep={delay:.2f}s url={url} detail={exc}",
                file=sys.stderr,
            )
        if attempt < retries:
            time.sleep(delay)
    if last_error is not None:
        raise last_error
    return None


def decode_bi5(payload: bytes, symbol: str, hour_start: dt.datetime) -> list[tuple[str, float, float, float, float]]:
    if not payload:
        return []
    decompressed = lzma.decompress(payload, format=lzma.FORMAT_AUTO)
    if len(decompressed) % RECORD_STRUCT.size != 0:
        raise ValueError(f"decoded BI5 payload size is not record-aligned: bytes={len(decompressed)}")
    scale = PIP_SCALE[symbol]
    rows: list[tuple[str, float, float, float, float]] = []
    base = hour_start.replace(tzinfo=dt.timezone.utc)
    for offset in range(0, len(decompressed), RECORD_STRUCT.size):
        ms_from_hour, ask_raw, bid_raw, ask_volume, bid_volume = RECORD_STRUCT.unpack_from(decompressed, offset)
        ts = base + dt.timedelta(milliseconds=int(ms_from_hour))
        ask = ask_raw / scale
        bid = bid_raw / scale
        rows.append((ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), bid, ask, bid_volume, ask_volume))
    return rows


def write_ticks(path: Path, rows: list[tuple[str, float, float, float, float]], symbol: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp_utc", "symbol", "bid", "ask", "bid_volume", "ask_volume", "source"])
        for ts, bid, ask, bid_volume, ask_volume in rows:
            writer.writerow([ts, symbol, f"{bid:.8f}", f"{ask:.8f}", f"{bid_volume:.8f}", f"{ask_volume:.8f}", "dukascopy_bi5"])


def download_hour(spec: HourSpec, output_root: Path, overwrite: bool, retries: int, sleep_seconds: float) -> dict[str, object]:
    output_path = output_root / spec.output_relpath
    if output_path.exists() and not overwrite:
        return {
            "symbol": spec.symbol,
            "hour_start_utc": spec.hour_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": spec.url,
            "path": str(output_path),
            "status": "exists",
            "rows": None,
            "sha256": sha256_file(output_path),
            "bytes": output_path.stat().st_size,
        }
    payload = fetch_bytes(spec.url, retries=retries, sleep_seconds=sleep_seconds)
    if payload is None:
        return {
            "symbol": spec.symbol,
            "hour_start_utc": spec.hour_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": spec.url,
            "path": str(output_path),
            "status": "missing_404",
            "rows": 0,
            "sha256": None,
            "bytes": 0,
        }
    rows = decode_bi5(payload, symbol=spec.symbol, hour_start=spec.hour_start)
    write_ticks(output_path, rows, symbol=spec.symbol)
    return {
        "symbol": spec.symbol,
        "hour_start_utc": spec.hour_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url": spec.url,
        "path": str(output_path),
        "status": "downloaded",
        "rows": len(rows),
        "sha256": sha256_file(output_path),
        "bytes": output_path.stat().st_size,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Dukascopy BI5 hourly tick files for selected FX symbols.")
    parser.add_argument("--symbols", nargs="+", required=True, choices=sorted(DUKASCOPY_SYMBOLS), help="Symbols to download.")
    parser.add_argument("--start", required=True, help="UTC start hour/date, inclusive. Example: 2024-01-01 or 2024-01-01T00")
    parser.add_argument("--end", required=True, help="UTC end hour/date, exclusive. Example: 2024-02-01 or 2024-02-01T00")
    parser.add_argument("--output-root", required=True, help="Root directory for raw tick CSV.GZ outputs.")
    parser.add_argument("--manifest-out", default=None, help="JSONL manifest output path. Default: <output-root>/dukascopy_download_manifest.jsonl")
    parser.add_argument("--overwrite", action="store_true", help="Re-download existing hourly files.")
    parser.add_argument("--retries", type=int, default=6, help="Retries for transient network/HTTP failures.")
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Base delay for exponential retry backoff.")
    parser.add_argument("--request-interval", type=float, default=0.25, help="Minimum pause between hourly requests.")
    parser.add_argument("--max-errors", type=int, default=0, help="Maximum terminal request/decode errors allowed before failing after manifest write.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = parse_utc_hour(args.start)
    end = parse_utc_hour(args.end)
    if end <= start:
        raise ValueError("--end must be after --start")
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_out = Path(args.manifest_out) if args.manifest_out else output_root / "dukascopy_download_manifest.jsonl"
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    errors = 0
    attempted = 0
    with manifest_out.open("w", encoding="utf-8") as manifest_fh:
        for spec in iter_hours(start, end, [s.upper() for s in args.symbols]):
            attempted += 1
            try:
                record = download_hour(
                    spec,
                    output_root,
                    overwrite=args.overwrite,
                    retries=args.retries,
                    sleep_seconds=args.sleep_seconds,
                )
            except Exception as exc:  # continue so the manifest preserves the exact failure location
                errors += 1
                record = {
                    "symbol": spec.symbol,
                    "hour_start_utc": spec.hour_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "url": spec.url,
                    "path": str(output_root / spec.output_relpath),
                    "status": "error",
                    "rows": 0,
                    "sha256": None,
                    "bytes": 0,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
            print(line)
            manifest_fh.write(line + "\n")
            manifest_fh.flush()
            if args.request_interval > 0:
                time.sleep(args.request_interval)
    print(f"wrote manifest: {manifest_out} attempted={attempted} errors={errors}")
    if errors > args.max_errors:
        raise RuntimeError(f"download completed with terminal errors={errors}, allowed={args.max_errors}; inspect {manifest_out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
