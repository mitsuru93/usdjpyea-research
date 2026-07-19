#!/usr/bin/env python3
"""Download and preserve Dukascopy hourly BI5 payloads and normalized bid/ask ticks.

This archive downloader is intentionally separate from the bar-collection workflow.
For each UTC hour it stores:
- the exact vendor BI5 payload;
- a deterministic gzip CSV containing timestamp_utc, bid, ask and volumes;
- a manifest with hashes for both representations.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import sys
import time
from pathlib import Path

from download_dukascopy_bi5_ticks import (
    DUKASCOPY_SYMBOLS,
    HourSpec,
    decode_bi5,
    fetch_bytes,
    iter_hours,
    parse_utc_hour,
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_tick_csv_bytes(
    rows: list[tuple[str, float, float, float, float]], symbol: str
) -> bytes:
    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(["timestamp_utc", "symbol", "bid", "ask", "bid_volume", "ask_volume", "source"])
    for ts, bid, ask, bid_volume, ask_volume in rows:
        writer.writerow(
            [
                ts,
                symbol,
                f"{bid:.8f}",
                f"{ask:.8f}",
                f"{bid_volume:.8f}",
                f"{ask_volume:.8f}",
                "dukascopy_bi5",
            ]
        )
    return text.getvalue().encode("utf-8")


def deterministic_gzip(payload: bytes) -> bytes:
    target = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=target, compresslevel=9, mtime=0) as fh:
        fh.write(payload)
    return target.getvalue()


def bi5_relpath(spec: HourSpec) -> Path:
    return Path(spec.symbol) / f"{spec.hour_start:%Y/%m/%d/%H}h_ticks.bi5"


def tick_relpath(spec: HourSpec) -> Path:
    return Path(spec.symbol) / f"{spec.hour_start:%Y/%m/%d/%H}.csv.gz"


def download_one(
    spec: HourSpec,
    *,
    bi5_root: Path,
    tick_root: Path,
    retries: int,
    sleep_seconds: float,
    request_timeout: float,
    pass_name: str,
) -> dict[str, object]:
    base = {
        "symbol": spec.symbol,
        "hour_start_utc": spec.hour_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url": spec.url,
        "attempt_pass": pass_name,
    }
    try:
        payload = fetch_bytes(
            spec.url,
            retries=retries,
            sleep_seconds=sleep_seconds,
            request_timeout=request_timeout,
        )
        if payload is None:
            return {**base, "status": "missing_404", "rows": 0}
        if payload == b"":
            return {**base, "status": "no_ticks", "rows": 0}

        rows = decode_bi5(payload, symbol=spec.symbol, hour_start=spec.hour_start)
        vendor_path = bi5_root / bi5_relpath(spec)
        tick_path = tick_root / tick_relpath(spec)
        vendor_path.parent.mkdir(parents=True, exist_ok=True)
        tick_path.parent.mkdir(parents=True, exist_ok=True)
        vendor_path.write_bytes(payload)
        csv_payload = normalized_tick_csv_bytes(rows, spec.symbol)
        gzip_payload = deterministic_gzip(csv_payload)
        tick_path.write_bytes(gzip_payload)
        return {
            **base,
            "status": "downloaded",
            "rows": len(rows),
            "bi5_path": str(vendor_path),
            "bi5_bytes": len(payload),
            "bi5_sha256": sha256_bytes(payload),
            "tick_path": str(tick_path),
            "tick_gzip_bytes": len(gzip_payload),
            "tick_gzip_sha256": sha256_bytes(gzip_payload),
            "tick_content_bytes": len(csv_payload),
            "tick_content_sha256": sha256_bytes(csv_payload),
            "tick_gzip_mtime": 0,
        }
    except Exception as exc:
        return {
            **base,
            "status": "error",
            "rows": 0,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def write_record(fh, record: dict[str, object]) -> None:
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    print(line)
    fh.write(line + "\n")
    fh.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive Dukascopy BI5 and normalized tick data.")
    parser.add_argument("--symbols", nargs="+", required=True, choices=sorted(DUKASCOPY_SYMBOLS))
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--bi5-output-root", required=True)
    parser.add_argument("--tick-output-root", required=True)
    parser.add_argument("--manifest-out", required=True)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--request-interval", type=float, default=0.10)
    parser.add_argument("--request-timeout", type=float, default=35.0)
    parser.add_argument("--max-errors", type=int, default=0)
    parser.add_argument("--error-retry-passes", type=int, default=6)
    parser.add_argument("--error-retry-sleep-seconds", type=float, default=8.0)
    parser.add_argument("--error-retry-request-timeout", type=float, default=60.0)
    parser.add_argument("--error-retry-retries", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = parse_utc_hour(args.start)
    end = parse_utc_hour(args.end)
    if end <= start:
        raise ValueError("--end must be after --start")
    symbols = [s.upper() for s in args.symbols]
    specs = list(iter_hours(start, end, symbols))
    bi5_root = Path(args.bi5_output_root)
    tick_root = Path(args.tick_output_root)
    manifest = Path(args.manifest_out)
    bi5_root.mkdir(parents=True, exist_ok=True)
    tick_root.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    final_by_key: dict[tuple[str, str], dict[str, object]] = {}
    attempted = 0
    with manifest.open("w", encoding="utf-8") as fh:
        for spec in specs:
            attempted += 1
            record = download_one(
                spec,
                bi5_root=bi5_root,
                tick_root=tick_root,
                retries=args.retries,
                sleep_seconds=args.sleep_seconds,
                request_timeout=args.request_timeout,
                pass_name="initial",
            )
            final_by_key[spec.key] = record
            write_record(fh, record)
            if args.request_interval > 0:
                time.sleep(args.request_interval)

        for retry_pass in range(1, args.error_retry_passes + 1):
            retry_specs = [
                spec for spec in specs if str(final_by_key.get(spec.key, {}).get("status")) == "error"
            ]
            if not retry_specs:
                break
            print(f"retrying terminal errors pass={retry_pass} count={len(retry_specs)}", file=sys.stderr)
            if args.error_retry_sleep_seconds > 0:
                time.sleep(args.error_retry_sleep_seconds)
            for spec in retry_specs:
                attempted += 1
                record = download_one(
                    spec,
                    bi5_root=bi5_root,
                    tick_root=tick_root,
                    retries=args.error_retry_retries,
                    sleep_seconds=args.sleep_seconds,
                    request_timeout=args.error_retry_request_timeout,
                    pass_name=f"error_retry_{retry_pass}",
                )
                final_by_key[spec.key] = record
                write_record(fh, record)
                if args.request_interval > 0:
                    time.sleep(args.request_interval)

    final_errors = sum(1 for row in final_by_key.values() if row.get("status") == "error")
    print(
        json.dumps(
            {
                "expected_hours": len(specs),
                "attempted_requests": attempted,
                "terminal_errors": final_errors,
                "manifest": str(manifest),
            },
            sort_keys=True,
        )
    )
    if final_errors > args.max_errors:
        raise RuntimeError(
            f"download completed with terminal errors={final_errors}, allowed={args.max_errors}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
