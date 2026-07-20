#!/usr/bin/env python3
"""Validate twelve repaired monthly packages and build the annual release files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

TOTAL_FIELDS = (
    "expected_days",
    "present_days",
    "expected_hours",
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
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--source-run-id", required=True, type=int)
    parser.add_argument("--source-run-attempt", required=True, type=int)
    parser.add_argument("--source-head-sha", required=True)
    parser.add_argument("--repair-run-id", required=True, type=int)
    parser.add_argument("--repair-run-attempt", required=True, type=int)
    parser.add_argument("--package-run-id", required=True, type=int)
    parser.add_argument("--package-run-attempt", required=True, type=int)
    args = parser.parse_args()

    root = args.release_dir
    root.mkdir(parents=True, exist_ok=True)
    manifests = sorted(root.glob("usdjpy-2024-??-raw-ticks-v1.manifest.json"))
    archives = sorted(root.glob("usdjpy-2024-??-raw-ticks-v1.tar.gz"))
    if len(manifests) != 12 or len(archives) != 12:
        raise SystemExit(
            f"expected 12 manifests and 12 archives, got {len(manifests)} and {len(archives)}"
        )

    annual_totals = {field: 0 for field in TOTAL_FIELDS}
    month_rows: list[dict[str, Any]] = []
    for manifest_path in manifests:
        row = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not bool(row.get("accepted")):
            raise SystemExit(f"unaccepted month: {row.get('month')}")
        month = str(row["month"])
        archive_path = root / f"usdjpy-{month}-raw-ticks-v1.tar.gz"
        checksum_path = root / f"usdjpy-{month}-raw-ticks-v1.SHA256SUMS"
        if not archive_path.is_file() or not checksum_path.is_file():
            raise SystemExit(f"monthly package files missing for {month}")
        for field in TOTAL_FIELDS:
            annual_totals[field] += int(row["totals"][field])
        month_rows.append(
            {
                "month": month,
                "manifest": manifest_path.name,
                "manifest_sha256": sha256_file(manifest_path),
                "archive": archive_path.name,
                "archive_sha256": sha256_file(archive_path),
                "checksums": checksum_path.name,
                "checksums_sha256": sha256_file(checksum_path),
                "totals": row["totals"],
            }
        )

    required_totals = {
        "expected_days": 366,
        "present_days": 366,
        "expected_hours": 8784,
        "resolved_hours": 8784,
        "error_hours": 0,
        "negative_spread_rows": 0,
    }
    for field, expected in required_totals.items():
        actual = annual_totals[field]
        if actual != expected:
            raise SystemExit(f"{field}={actual}, expected {expected}")

    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    lock_target = root / "usdjpy-2024-raw-tick-repair-lock-v1.json"
    lock_target.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    annual = {
        "schema_version": "usdjpy_2024_raw_tick_annual_repaired_v1",
        "symbol": "USDJPY",
        "period_start_utc": "2024-01-01T00:00:00Z",
        "period_end_utc_exclusive": "2025-01-01T00:00:00Z",
        "source": "Dukascopy BI5 public Bid/Ask ticks",
        "source_workflow_run_id": args.source_run_id,
        "source_workflow_run_attempt": args.source_run_attempt,
        "source_workflow_head_sha": args.source_head_sha,
        "repair_data_workflow_run_id": args.repair_run_id,
        "repair_data_workflow_run_attempt": args.repair_run_attempt,
        "package_workflow_run_id": args.package_run_id,
        "package_workflow_run_attempt": args.package_run_attempt,
        "repair_scope": lock["repair_scope"],
        "annual_totals": annual_totals,
        "months": month_rows,
        "accepted": True,
        "boundaries": {
            "original_hourly_bi5_preserved": True,
            "decoded_bid_ask_csv_preserved": True,
            "rakuten_quote_equivalence": False,
            "standard_mt4_real_tick_input_ready": False,
            "requires_fxt_hst_or_tick_import_conversion": True,
        },
    }
    annual_path = root / "usdjpy-2024-raw-ticks-v1.annual-manifest.json"
    annual_path.write_text(json.dumps(annual, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    notes = f"""# USDJPY 2024 Raw Dukascopy Bid/Ask Ticks v1

This release preserves the original hourly Dukascopy BI5 payloads and deterministic decoded Bid/Ask CSV.GZ files for all 8,784 UTC hours of 2024.

Source run {args.source_run_id} resolved 8,741 hours. Repair run {args.repair_run_id} recollected the 28 affected UTC days at maximum two-day parallelism and replaced the 43 terminal-error hours. Package recovery run {args.package_run_id} then enumerated every source and repair artifact through paginated GitHub REST calls before rebuilding and revalidating all twelve monthly packages.

This dataset is a public Dukascopy proxy and is not equivalent to Rakuten Securities quotes. FXT/HST generation or a compatible tick-import conversion is still required before MT4 Strategy Tester use.
"""
    (root / "RELEASE_NOTES.md").write_text(notes, encoding="utf-8")

    checksum_lines = []
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            checksum_lines.append(f"{sha256_file(path)}  {path.name}")
    (root / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps({"accepted": True, **annual_totals}, sort_keys=True))


if __name__ == "__main__":
    main()
