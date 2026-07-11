#!/usr/bin/env python3
"""Summarize Dukascopy download manifest coverage for workflow gating.

This tool is intentionally small and source-agnostic over the manifest schema emitted
by tools/download_dukascopy_bi5_ticks.py. It does not promote a dataset; it only
reports whether the collection run is complete enough for the current workflow stage.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SUCCESS_STATUSES = {"downloaded", "exists"}
SOFT_MISSING_STATUSES = {"missing_404", "no_ticks", "market_closed"}
ERROR_STATUSES = {"error"}


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


def expected_hours(start: dt.datetime, end: dt.datetime, symbols: list[str]) -> int:
    if end <= start:
        raise ValueError("end must be after start")
    hours = int((end - start).total_seconds() // 3600)
    return hours * len(symbols)


def load_manifest(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
    return records


def deduplicate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the final record for each symbol/hour.

    The downloader may append retry-pass records after an initial error. For coverage
    gating, only the latest terminal state for a symbol/hour should count.
    """
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        symbol = str(record.get("symbol", "UNKNOWN"))
        hour = str(record.get("hour_start_utc", ""))
        latest[(symbol, hour)] = record
    return list(latest.values())


def summarize(records: list[dict[str, Any]], expected: int, raw_records: int) -> dict[str, Any]:
    status_counts = Counter(str(r.get("status", "")) for r in records)
    by_symbol: dict[str, Counter[str]] = defaultdict(Counter)
    error_examples: list[dict[str, Any]] = []
    for r in records:
        symbol = str(r.get("symbol", "UNKNOWN"))
        status = str(r.get("status", ""))
        by_symbol[symbol][status] += 1
        if status in ERROR_STATUSES and len(error_examples) < 20:
            error_examples.append(
                {
                    "symbol": symbol,
                    "hour_start_utc": r.get("hour_start_utc"),
                    "url": r.get("url"),
                    "error_type": r.get("error_type"),
                    "error": r.get("error"),
                    "attempt_pass": r.get("attempt_pass"),
                }
            )
    successful = sum(status_counts[s] for s in SUCCESS_STATUSES)
    hard_errors = sum(status_counts[s] for s in ERROR_STATUSES)
    soft_missing = sum(status_counts[s] for s in SOFT_MISSING_STATUSES)
    observed = len(records)
    effective_expected = max(expected - soft_missing, 0)
    calendar_coverage = successful / expected if expected else 0.0
    effective_coverage = successful / effective_expected if effective_expected else 0.0
    return {
        "expected_records": expected,
        "raw_manifest_records": raw_records,
        "observed_records": observed,
        "successful_records": successful,
        "soft_missing_records": soft_missing,
        "hard_error_records": hard_errors,
        "calendar_coverage": calendar_coverage,
        "effective_expected_records": effective_expected,
        "effective_coverage": effective_coverage,
        "status_counts": dict(sorted(status_counts.items())),
        "by_symbol": {k: dict(sorted(v.items())) for k, v in sorted(by_symbol.items())},
        "error_examples": error_examples,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize download manifest coverage.")
    parser.add_argument("--manifest", required=True, help="Download manifest JSONL path.")
    parser.add_argument("--symbols", nargs="+", required=True, help="Expected symbols.")
    parser.add_argument("--start", required=True, help="UTC start hour/date, inclusive.")
    parser.add_argument("--end", required=True, help="UTC end hour/date, exclusive.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument("--min-coverage", type=float, default=1.0, help="Minimum successful/effective-expected coverage after excluding no-tick or explicit missing hours.")
    parser.add_argument("--max-hard-errors", type=int, default=0, help="Maximum terminal error records allowed.")
    parser.add_argument(
        "--expected-records-mode",
        choices=["calendar", "observed"],
        default="calendar",
        help="Use calendar hours from start/end, or use observed manifest records. Use observed for discontinuous trading-day chunk aggregates.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbols = [s.upper() for s in args.symbols]
    raw_records = load_manifest(Path(args.manifest))
    records = deduplicate_records(raw_records)
    if args.expected_records_mode == "observed":
        expected = len(records)
    else:
        expected = expected_hours(parse_utc_hour(args.start), parse_utc_hour(args.end), symbols)
    summary = summarize(records, expected, raw_records=len(raw_records))
    summary["expected_records_mode"] = args.expected_records_mode
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    failures: list[str] = []
    if summary["effective_coverage"] < args.min_coverage:
        failures.append(f"effective coverage {summary['effective_coverage']:.6f} < min {args.min_coverage:.6f}")
    if summary["hard_error_records"] > args.max_hard_errors:
        failures.append(f"hard errors {summary['hard_error_records']} > max {args.max_hard_errors}")
    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
