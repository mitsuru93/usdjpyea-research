#!/usr/bin/env python3
"""Validate repaired USDJPY 2024 day packets and build one monthly manifest."""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


COUNT_FIELDS = (
    "resolved_hours",
    "downloaded_hours",
    "missing_404_hours",
    "no_tick_hours",
    "error_hours",
    "tick_rows",
    "negative_spread_rows",
    "source_bi5_bytes",
    "decoded_csv_bytes",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_final_records(path: Path) -> dict[str, dict[str, Any]]:
    final: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            final[str(row["hour_start_utc"])] = row
    return final


def validate_day(root: Path, day: str) -> tuple[dict[str, int], dict[str, Any], list[str]]:
    failures: list[str] = []
    manifest_path = root / "download_manifest.jsonl"
    summary_path = root / "day_summary.json"
    checksums_path = root / "SHA256SUMS"
    if not manifest_path.exists() or not summary_path.exists() or not checksums_path.exists():
        return {}, {}, [f"missing day packet files: {day}"]

    recorded_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    final = load_final_records(manifest_path)
    if len(final) != 24:
        failures.append(f"{day}: final hour records={len(final)} expected=24")

    computed = {
        "resolved_hours": 0,
        "downloaded_hours": 0,
        "missing_404_hours": 0,
        "no_tick_hours": 0,
        "error_hours": 0,
        "tick_rows": 0,
        "negative_spread_rows": 0,
        "source_bi5_bytes": 0,
        "decoded_csv_bytes": 0,
    }

    for hour, row in sorted(final.items()):
        status = str(row.get("status"))
        if status == "error":
            computed["error_hours"] += 1
            failures.append(f"{day}: terminal error {hour} {row.get('error_type')}: {row.get('error')}")
            continue
        if status == "downloaded":
            computed["downloaded_hours"] += 1
            source_rel = row.get("source_bi5_path")
            decoded_rel = row.get("decoded_csv_path")
            if not source_rel or not decoded_rel:
                failures.append(f"{day}: downloaded row missing paths {hour}")
                continue
            source = root / str(source_rel)
            decoded = root / str(decoded_rel)
            if not source.exists():
                failures.append(f"{day}: missing source BI5 {hour}")
            elif sha256_file(source) != row.get("source_bi5_sha256"):
                failures.append(f"{day}: source BI5 hash mismatch {hour}")
            if not decoded.exists():
                failures.append(f"{day}: missing decoded CSV {hour}")
            elif sha256_file(decoded) != row.get("decoded_csv_sha256"):
                failures.append(f"{day}: decoded CSV hash mismatch {hour}")
            computed["tick_rows"] += int(row.get("rows", 0))
            computed["negative_spread_rows"] += int(row.get("negative_spread_rows", 0))
            computed["source_bi5_bytes"] += int(row.get("source_bi5_bytes", 0))
            computed["decoded_csv_bytes"] += int(row.get("decoded_csv_bytes", 0))
        elif status == "missing_404":
            computed["missing_404_hours"] += 1
        elif status == "no_ticks":
            computed["no_tick_hours"] += 1
        else:
            failures.append(f"{day}: unknown status {status!r} at {hour}")

    computed["resolved_hours"] = len(final) - computed["error_hours"]

    for key in COUNT_FIELDS:
        if int(recorded_summary.get(key, -1)) != computed[key]:
            failures.append(
                f"{day}: summary mismatch {key} recorded={recorded_summary.get(key)} computed={computed[key]}"
            )
    if int(recorded_summary.get("expected_hours", -1)) != 24:
        failures.append(f"{day}: expected_hours is not 24")
    if computed["negative_spread_rows"] != 0:
        failures.append(f"{day}: negative spread rows={computed['negative_spread_rows']}")

    return computed, recorded_summary, failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", required=True)
    parser.add_argument("--month", required=True, type=int)
    parser.add_argument("--out", required=True)
    parser.add_argument("--source-run-id", required=True, type=int)
    parser.add_argument("--repair-run-id", required=True, type=int)
    parser.add_argument("--repair-run-attempt", required=True, type=int)
    args = parser.parse_args()

    staging = Path(args.staging)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    expected_days = calendar.monthrange(2024, args.month)[1]
    expected_dates = [date(2024, args.month, day).isoformat() for day in range(1, expected_days + 1)]
    totals = {
        "expected_days": expected_days,
        "present_days": 0,
        "expected_hours": expected_days * 24,
        **{key: 0 for key in COUNT_FIELDS},
    }
    failures: list[str] = []
    day_summaries: list[dict[str, Any]] = []

    for day in expected_dates:
        root = staging / day
        if not root.is_dir():
            failures.append(f"missing day directory: {day}")
            continue
        totals["present_days"] += 1
        computed, summary, day_failures = validate_day(root, day)
        failures.extend(day_failures)
        if summary:
            day_summaries.append(summary)
        for key in COUNT_FIELDS:
            totals[key] += int(computed.get(key, 0))

    accepted = (
        not failures
        and totals["present_days"] == totals["expected_days"]
        and totals["resolved_hours"] == totals["expected_hours"]
        and totals["error_hours"] == 0
        and totals["negative_spread_rows"] == 0
    )

    manifest = {
        "schema_version": "usdjpy_2024_raw_tick_month_repaired_v1",
        "symbol": "USDJPY",
        "month": f"2024-{args.month:02d}",
        "source": "Dukascopy BI5 public Bid/Ask ticks",
        "source_workflow_run_id": args.source_run_id,
        "repair_workflow_run_id": args.repair_run_id,
        "repair_workflow_run_attempt": args.repair_run_attempt,
        "totals": totals,
        "failures": failures,
        "day_summaries": day_summaries,
        "accepted": accepted,
    }
    manifest_path = out_dir / f"usdjpy-2024-{args.month:02d}-raw-ticks-v1.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"month": manifest["month"], "accepted": accepted, **totals}, sort_keys=True))
    if not accepted:
        raise SystemExit("month validation failed: " + "; ".join(failures[:30]))


if __name__ == "__main__":
    main()
