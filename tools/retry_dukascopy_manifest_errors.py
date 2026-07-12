#!/usr/bin/env python3
"""Retry final error hours from a Dukascopy BI5 download manifest.

This tool is intended for aggregate repair after daily chunk artifacts have been
collected. It reads a combined manifest, keeps the latest record per symbol/hour,
then retries only hours whose final status is `error`.

It writes a retry-only manifest. Concatenate the original combined manifest first
and this retry manifest second before coverage gating so downstream summarization
keeps the repaired terminal state.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# The script is executed from the repository root as `python tools/...`; Python
# places the tools directory on sys.path, so this import resolves to the sibling
# downloader module.
from download_dukascopy_bi5_ticks import HourSpec, parse_utc_hour, try_spec, write_record


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
    return records


def latest_by_hour(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        symbol = str(record.get("symbol", "")).upper()
        hour = str(record.get("hour_start_utc", ""))
        if not symbol or not hour:
            continue
        latest[(symbol, hour)] = record
    return latest


def spec_from_record(record: dict[str, Any]) -> HourSpec:
    symbol = str(record.get("symbol", "")).upper()
    hour_raw = str(record.get("hour_start_utc", ""))
    if not symbol or not hour_raw:
        raise ValueError(f"record does not contain symbol/hour_start_utc: {record}")
    return HourSpec(symbol=symbol, hour_start=parse_utc_hour(hour_raw))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retry final error hours from a Dukascopy manifest.")
    parser.add_argument("--manifest", required=True, help="Combined manifest JSONL to inspect.")
    parser.add_argument("--output-root", required=True, help="Root directory for repaired tick CSV.GZ outputs.")
    parser.add_argument("--manifest-out", required=True, help="Retry-only manifest JSONL output.")
    parser.add_argument("--passes", type=int, default=3, help="Number of retry passes over still-error hours.")
    parser.add_argument("--retries", type=int, default=4, help="Per-hour retries inside each repair pass.")
    parser.add_argument("--sleep-seconds", type=float, default=2.0, help="Base exponential backoff delay for retries.")
    parser.add_argument("--request-timeout", type=float, default=60.0, help="Per-request HTTP timeout in seconds.")
    parser.add_argument("--request-interval", type=float, default=1.0, help="Pause after each repaired hour request.")
    parser.add_argument("--pass-sleep-seconds", type=float, default=20.0, help="Pause before each repair pass.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_manifest = Path(args.manifest)
    output_root = Path(args.output_root)
    manifest_out = Path(args.manifest_out)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_out.parent.mkdir(parents=True, exist_ok=True)

    source_records = load_records(source_manifest)
    final_records = latest_by_hour(source_records)
    error_records = [record for record in final_records.values() if str(record.get("status")) == "error"]
    print(f"source_records={len(source_records)} final_hours={len(final_records)} initial_error_hours={len(error_records)}")

    with manifest_out.open("w", encoding="utf-8") as manifest_fh:
        for pass_no in range(1, args.passes + 1):
            retry_records = [record for record in final_records.values() if str(record.get("status")) == "error"]
            if not retry_records:
                print(f"no error hours remain before repair pass {pass_no}")
                break
            print(f"repair pass {pass_no}: retrying {len(retry_records)} error hours", file=sys.stderr)
            if args.pass_sleep_seconds > 0:
                time.sleep(args.pass_sleep_seconds)
            for record in sorted(retry_records, key=lambda r: (str(r.get("symbol", "")), str(r.get("hour_start_utc", "")))):
                spec = spec_from_record(record)
                repaired = try_spec(
                    spec,
                    output_root,
                    overwrite=True,
                    retries=args.retries,
                    sleep_seconds=args.sleep_seconds,
                    request_timeout=args.request_timeout,
                    pass_name=f"aggregate_repair_{pass_no}",
                )
                final_records[spec.key] = repaired
                write_record(manifest_fh, repaired)
                if args.request_interval > 0:
                    time.sleep(args.request_interval)

    final_errors = sum(1 for record in final_records.values() if str(record.get("status")) == "error")
    print(f"wrote repair manifest: {manifest_out} final_errors={final_errors}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
