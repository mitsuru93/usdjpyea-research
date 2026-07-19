#!/usr/bin/env python3
"""Download Dukascopy hourly BI5 files while preserving both raw BI5 and decoded tick CSV.GZ.

This tool is intentionally separate from the older research downloader because the
2024 MT4-data collection contract requires immutable raw source payloads.
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
from pathlib import Path

BASE_URL = (
    "https://datafeed.dukascopy.com/datafeed/"
    "{symbol}/{year}/{month_zero_based:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
)
RECORD_STRUCT = struct.Struct(">IIIff")
RETRYABLE_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}
PIP_SCALE = {"USDJPY": 1000.0}


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_bytes(url: str, retries: int, timeout: float, base_sleep: float) -> bytes | None:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "usdjpyea-research/raw-bi5-v1",
                    "Accept": "application/octet-stream,*/*;q=0.8",
                    "Connection": "close",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            last_error = exc
            if exc.code not in RETRYABLE_HTTP_CODES:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = max(float(retry_after), base_sleep) if retry_after else base_sleep * (2**attempt)
            except ValueError:
                delay = base_sleep * (2**attempt)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            delay = base_sleep * (2**attempt)

        if attempt < retries:
            delay += random.uniform(0.0, max(0.1, base_sleep * 0.25))
            print(
                f"retry attempt={attempt + 1}/{retries + 1} sleep={delay:.2f}s url={url}",
                file=sys.stderr,
            )
            time.sleep(delay)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"failed without an exception: {url}")


def decode_rows(payload: bytes, symbol: str, hour_start: dt.datetime):
    decompressed = lzma.decompress(payload, format=lzma.FORMAT_AUTO)
    if len(decompressed) % RECORD_STRUCT.size:
        raise ValueError(
            f"decoded payload is not record aligned: bytes={len(decompressed)} "
            f"record_size={RECORD_STRUCT.size}"
        )

    scale = PIP_SCALE[symbol]
    base = hour_start.replace(tzinfo=dt.timezone.utc)
    for offset in range(0, len(decompressed), RECORD_STRUCT.size):
        ms_from_hour, ask_raw, bid_raw, ask_volume, bid_volume = RECORD_STRUCT.unpack_from(
            decompressed, offset
        )
        timestamp = base + dt.timedelta(milliseconds=int(ms_from_hour))
        yield (
            timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            bid_raw / scale,
            ask_raw / scale,
            float(bid_volume),
            float(ask_volume),
        )


def write_csv_gz(path: Path, rows, symbol: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with gzip.open(path, "wt", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(
            ["timestamp_utc", "symbol", "bid", "ask", "bid_volume", "ask_volume", "source"]
        )
        for timestamp, bid, ask, bid_volume, ask_volume in rows:
            writer.writerow(
                [
                    timestamp,
                    symbol,
                    f"{bid:.8f}",
                    f"{ask:.8f}",
                    f"{bid_volume:.8f}",
                    f"{ask_volume:.8f}",
                    "dukascopy_bi5",
                ]
            )
            count += 1
    return count


def download_hour(
    *,
    symbol: str,
    hour_start: dt.datetime,
    output_root: Path,
    retries: int,
    timeout: float,
    base_sleep: float,
) -> dict[str, object]:
    rel_dir = Path(symbol) / f"{hour_start:%Y/%m/%d}"
    raw_path = output_root / "raw_bi5" / rel_dir / f"{hour_start:%H}h_ticks.bi5"
    csv_path = output_root / "csv_ticks" / rel_dir / f"{hour_start:%H}.csv.gz"
    url = BASE_URL.format(
        symbol=symbol,
        year=hour_start.year,
        month_zero_based=hour_start.month - 1,
        day=hour_start.day,
        hour=hour_start.hour,
    )

    record: dict[str, object] = {
        "symbol": symbol,
        "hour_start_utc": hour_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url": url,
        "raw_bi5_path": str(raw_path.relative_to(output_root)),
        "csv_ticks_path": str(csv_path.relative_to(output_root)),
    }

    try:
        payload = fetch_bytes(url, retries=retries, timeout=timeout, base_sleep=base_sleep)
        if payload is None:
            return {
                **record,
                "status": "missing_404",
                "rows": 0,
                "raw_bi5_bytes": 0,
                "raw_bi5_sha256": None,
                "csv_ticks_bytes": 0,
                "csv_ticks_sha256": None,
            }
        if payload == b"":
            return {
                **record,
                "status": "empty_response",
                "rows": 0,
                "raw_bi5_bytes": 0,
                "raw_bi5_sha256": None,
                "csv_ticks_bytes": 0,
                "csv_ticks_sha256": None,
            }

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(payload)
        rows = write_csv_gz(csv_path, decode_rows(payload, symbol, hour_start), symbol)
        if rows <= 0:
            raw_path.unlink(missing_ok=True)
            csv_path.unlink(missing_ok=True)
            return {
                **record,
                "status": "decoded_no_ticks",
                "rows": 0,
                "raw_bi5_bytes": 0,
                "raw_bi5_sha256": None,
                "csv_ticks_bytes": 0,
                "csv_ticks_sha256": None,
            }

        return {
            **record,
            "status": "downloaded",
            "rows": rows,
            "raw_bi5_bytes": raw_path.stat().st_size,
            "raw_bi5_sha256": sha256_file(raw_path),
            "csv_ticks_bytes": csv_path.stat().st_size,
            "csv_ticks_sha256": sha256_file(csv_path),
        }
    except Exception as exc:
        raw_path.unlink(missing_ok=True)
        csv_path.unlink(missing_ok=True)
        return {
            **record,
            "status": "error",
            "rows": 0,
            "raw_bi5_bytes": 0,
            "raw_bi5_sha256": None,
            "csv_ticks_bytes": 0,
            "csv_ticks_sha256": None,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="USDJPY", choices=sorted(PIP_SCALE))
    parser.add_argument("--start", required=True, help="UTC inclusive hour/date")
    parser.add_argument("--end", required=True, help="UTC exclusive hour/date")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--manifest-out", required=True)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--request-timeout", type=float, default=45.0)
    parser.add_argument("--retry-sleep-seconds", type=float, default=1.0)
    parser.add_argument("--request-interval", type=float, default=0.05)
    parser.add_argument("--retry-error-passes", type=int, default=2)
    parser.add_argument("--max-errors", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()
    start = parse_hour(args.start)
    end = parse_hour(args.end)
    if end <= start:
        raise ValueError("--end must be after --start")

    output_root = Path(args.output_root)
    manifest_path = Path(args.manifest_out)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    hours = []
    current = start
    while current < end:
        hours.append(current)
        current += dt.timedelta(hours=1)

    final: dict[str, dict[str, object]] = {}
    for pass_index in range(args.retry_error_passes + 1):
        pending = hours if pass_index == 0 else [
            hour
            for hour in hours
            if final[hour.strftime("%Y-%m-%dT%H:%M:%SZ")]["status"] == "error"
        ]
        if not pending:
            break

        for hour in pending:
            key = hour.strftime("%Y-%m-%dT%H:%M:%SZ")
            result = download_hour(
                symbol=symbol,
                hour_start=hour,
                output_root=output_root,
                retries=args.retries,
                timeout=args.request_timeout,
                base_sleep=args.retry_sleep_seconds,
            )
            result["attempt_pass"] = pass_index
            final[key] = result
            print(json.dumps(result, sort_keys=True), flush=True)
            if args.request_interval > 0:
                time.sleep(args.request_interval)

    ordered = [final[hour.strftime("%Y-%m-%dT%H:%M:%SZ")] for hour in hours]
    with manifest_path.open("w", encoding="utf-8", newline="\n") as fh:
        for record in ordered:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    errors = [row for row in ordered if row["status"] == "error"]
    summary = {
        "symbol": symbol,
        "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_hours": len(hours),
        "downloaded_hours": sum(row["status"] == "downloaded" for row in ordered),
        "terminal_errors": len(errors),
        "rows": sum(int(row["rows"]) for row in ordered),
        "raw_bi5_bytes": sum(int(row["raw_bi5_bytes"]) for row in ordered),
        "csv_ticks_bytes": sum(int(row["csv_ticks_bytes"]) for row in ordered),
    }
    summary_path = output_root / "day_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))

    if len(errors) > args.max_errors:
        raise RuntimeError(
            f"terminal errors={len(errors)} exceeds max_errors={args.max_errors}; "
            f"see {manifest_path}"
        )


if __name__ == "__main__":
    main()
