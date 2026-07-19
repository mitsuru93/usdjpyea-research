#!/usr/bin/env python3
"""Download one or more UTC hours of Dukascopy BI5 ticks and preserve both source BI5 and decoded CSV.GZ.

This tool is designed for durable research archives. It does not claim Rakuten quote equivalence.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import lzma
import random
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://datafeed.dukascopy.com/datafeed/{symbol}/{year}/{month0:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
RECORD = struct.Struct(">IIIff")
RETRYABLE = {408, 425, 429, 500, 502, 503, 504}
SCALES = {"USDJPY": 1000.0}


def parse_hour(value: str) -> dt.datetime:
    raw = value.strip().replace("Z", "")
    if "T" not in raw:
        raw += "T00:00:00"
    elif len(raw) == 13:
        raw += ":00:00"
    parsed = dt.datetime.fromisoformat(raw)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed.replace(minute=0, second=0, microsecond=0)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, retries: int, timeout: float, base_sleep: float) -> bytes | None:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "usdjpyea-research/raw-bi5-archive-v1",
                    "Accept": "application/octet-stream,*/*;q=0.8",
                    "Connection": "close",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            last_error = exc
            if exc.code not in RETRYABLE:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            delay = max(float(retry_after), base_sleep) if retry_after else base_sleep * (2**attempt)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            delay = base_sleep * (2**attempt)
        if attempt < retries:
            time.sleep(delay + random.uniform(0.0, max(0.1, base_sleep * 0.25)))
    if last_error is not None:
        raise last_error
    return None


def decode(payload: bytes, symbol: str, hour: dt.datetime) -> tuple[list[tuple[str, str, str, str, str, str]], int]:
    raw = lzma.decompress(payload, format=lzma.FORMAT_AUTO)
    if len(raw) % RECORD.size != 0:
        raise ValueError(f"decoded BI5 size is not record aligned: {len(raw)}")
    scale = SCALES[symbol]
    base = hour.replace(tzinfo=dt.timezone.utc)
    rows: list[tuple[str, str, str, str, str, str]] = []
    negative_spreads = 0
    for offset in range(0, len(raw), RECORD.size):
        ms, ask_raw, bid_raw, ask_vol, bid_vol = RECORD.unpack_from(raw, offset)
        ts = base + dt.timedelta(milliseconds=int(ms))
        ask = ask_raw / scale
        bid = bid_raw / scale
        if ask < bid:
            negative_spreads += 1
        rows.append(
            (
                ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                symbol,
                f"{bid:.8f}",
                f"{ask:.8f}",
                f"{bid_vol:.8f}",
                f"{ask_vol:.8f}",
            )
        )
    return rows, negative_spreads


def write_csv_gz(path: Path, rows: list[tuple[str, str, str, str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw_fh:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_fh, mtime=0) as gz_fh:
            with io.TextIOWrapper(gz_fh, encoding="utf-8", newline="") as text_fh:
                writer = csv.writer(text_fh, lineterminator="\n")
                writer.writerow(["timestamp_utc", "symbol", "bid", "ask", "bid_volume", "ask_volume", "source"])
                for row in rows:
                    writer.writerow([*row, "dukascopy_bi5"])


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="USDJPY", choices=sorted(SCALES))
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--manifest-out", required=True)
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--retry-passes", type=int, default=3)
    parser.add_argument("--request-timeout", type=float, default=45.0)
    parser.add_argument("--request-interval", type=float, default=0.05)
    parser.add_argument("--max-errors", type=int, default=0)
    args = parser.parse_args()

    start = parse_hour(args.start)
    end = parse_hour(args.end)
    if end <= start:
        raise ValueError("--end must be later than --start")

    root = Path(args.output_root)
    manifest_path = Path(args.manifest_out)
    summary_path = Path(args.summary_out)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    hours: list[dt.datetime] = []
    current = start
    while current < end:
        hours.append(current)
        current += dt.timedelta(hours=1)

    final: dict[str, dict[str, object]] = {}
    attempts: list[dict[str, object]] = []

    for pass_index in range(args.retry_passes + 1):
        pending = hours if pass_index == 0 else [h for h in hours if final[h.strftime("%Y-%m-%dT%H:%M:%SZ")]["status"] == "error"]
        if not pending:
            break
        for hour in pending:
            key = hour.strftime("%Y-%m-%dT%H:%M:%SZ")
            url = BASE_URL.format(
                symbol=args.symbol,
                year=hour.year,
                month0=hour.month - 1,
                day=hour.day,
                hour=hour.hour,
            )
            source = root / "source_bi5" / args.symbol / f"{hour:%Y/%m/%d/%H}h_ticks.bi5"
            decoded = root / "decoded_csv" / args.symbol / f"{hour:%Y/%m/%d/%H}.csv.gz"
            record: dict[str, object] = {
                "symbol": args.symbol,
                "hour_start_utc": key,
                "url": url,
                "attempt_pass": pass_index,
            }
            try:
                payload = fetch(url, retries=args.retries, timeout=args.request_timeout, base_sleep=1.0)
                if payload is None:
                    record.update(status="missing_404", rows=0, source_bi5_path=None, decoded_csv_path=None)
                elif payload == b"":
                    record.update(status="no_ticks", rows=0, source_bi5_path=None, decoded_csv_path=None)
                else:
                    source.parent.mkdir(parents=True, exist_ok=True)
                    source.write_bytes(payload)
                    rows, negative_spreads = decode(payload, args.symbol, hour)
                    write_csv_gz(decoded, rows)
                    record.update(
                        status="downloaded",
                        rows=len(rows),
                        negative_spread_rows=negative_spreads,
                        source_bi5_path=rel(source, root),
                        source_bi5_sha256=sha256_bytes(payload),
                        source_bi5_bytes=len(payload),
                        decoded_csv_path=rel(decoded, root),
                        decoded_csv_sha256=sha256_file(decoded),
                        decoded_csv_bytes=decoded.stat().st_size,
                    )
            except Exception as exc:
                record.update(status="error", rows=0, error_type=type(exc).__name__, error=str(exc))
            final[key] = record
            attempts.append(dict(record))
            if args.request_interval > 0:
                time.sleep(args.request_interval)

    with manifest_path.open("w", encoding="utf-8", newline="\n") as fh:
        for record in attempts:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    errors = [r for r in final.values() if r["status"] == "error"]
    downloaded = [r for r in final.values() if r["status"] == "downloaded"]
    summary = {
        "schema_version": "dukascopy_raw_tick_day_v1",
        "symbol": args.symbol,
        "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_hours": len(hours),
        "resolved_hours": len(final) - len(errors),
        "downloaded_hours": len(downloaded),
        "missing_404_hours": sum(1 for r in final.values() if r["status"] == "missing_404"),
        "no_tick_hours": sum(1 for r in final.values() if r["status"] == "no_ticks"),
        "error_hours": len(errors),
        "tick_rows": sum(int(r.get("rows", 0)) for r in downloaded),
        "negative_spread_rows": sum(int(r.get("negative_spread_rows", 0)) for r in downloaded),
        "source_bi5_bytes": sum(int(r.get("source_bi5_bytes", 0)) for r in downloaded),
        "decoded_csv_bytes": sum(int(r.get("decoded_csv_bytes", 0)) for r in downloaded),
        "manifest_sha256": sha256_file(manifest_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    if len(errors) > args.max_errors:
        raise RuntimeError(f"terminal download errors={len(errors)} allowed={args.max_errors}")
    if summary["negative_spread_rows"] != 0:
        raise RuntimeError(f"negative spread rows={summary['negative_spread_rows']}")


if __name__ == "__main__":
    main()
