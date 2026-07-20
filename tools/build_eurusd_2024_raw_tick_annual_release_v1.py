#!/usr/bin/env python3
"""Validate twelve recovered EURUSD 2024 monthly packages and build release inventory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--source-run-id", required=True, type=int)
    parser.add_argument("--source-run-attempt", required=True, type=int)
    parser.add_argument("--source-head-sha", required=True)
    parser.add_argument("--package-run-id", required=True, type=int)
    parser.add_argument("--package-run-attempt", required=True, type=int)
    args = parser.parse_args()

    root = args.release_dir
    packages = sorted(root.glob("eurusd-2024-??-raw-ticks-v1.tar.gz"))
    manifests = sorted(root.glob("eurusd-2024-??-raw-ticks-v1.manifest.json"))
    receipts = sorted(root.glob("eurusd-2024-??-source-artifacts.json"))
    if len(packages) != 12 or len(manifests) != 12 or len(receipts) != 12:
        raise SystemExit(
            f"expected 12 packages/manifests/receipts, got {len(packages)}/{len(manifests)}/{len(receipts)}"
        )

    monthly: list[dict[str, Any]] = []
    expected_days = expected_hours = resolved_hours = tick_rows = 0
    recovered_dates: list[str] = []
    seen_months: set[str] = set()
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("symbol") != "EURUSD" or not manifest.get("accepted"):
            raise SystemExit(f"unaccepted monthly manifest: {manifest_path.name}")
        month = str(manifest.get("month"))
        if month in seen_months:
            raise SystemExit(f"duplicate month: {month}")
        seen_months.add(month)
        package = root / f"eurusd-{month}-raw-ticks-v1.tar.gz"
        receipt = root / f"eurusd-{month}-source-artifacts.json"
        if not package.is_file() or not receipt.is_file():
            raise SystemExit(f"missing package or receipt for {month}")
        totals = manifest["totals"]
        if int(totals.get("error_hours", -1)) != 0 or int(totals.get("negative_spread_rows", -1)) != 0:
            raise SystemExit(f"invalid month totals for {month}: {totals}")
        expected_days += int(totals["expected_days"])
        expected_hours += int(totals["expected_hours"])
        resolved_hours += int(totals["resolved_hours"])
        tick_rows += int(totals["tick_rows"])
        recovered_dates.extend(str(value) for value in manifest.get("recovered_dates", []))
        monthly.append({
            "month": month,
            "package": package.name,
            "package_sha256": sha256_file(package),
            "package_bytes": package.stat().st_size,
            "manifest": manifest_path.name,
            "manifest_sha256": sha256_file(manifest_path),
            "source_artifact_receipt": receipt.name,
            "source_artifact_receipt_sha256": sha256_file(receipt),
            "recovered_dates": manifest.get("recovered_dates", []),
            "totals": totals,
        })

    accepted = expected_days == 366 and expected_hours == 8784 and resolved_hours == 8784
    annual = {
        "schema_version": "eurusd_2024_raw_tick_annual_recovered_v1",
        "symbol": "EURUSD",
        "start_utc": "2024-01-01T00:00:00Z",
        "end_utc": "2025-01-01T00:00:00Z",
        "source": "Dukascopy BI5 public Bid/Ask ticks",
        "source_workflow_run_id": args.source_run_id,
        "source_workflow_run_attempt": args.source_run_attempt,
        "source_head_sha": args.source_head_sha,
        "package_workflow_run_id": args.package_run_id,
        "package_workflow_run_attempt": args.package_run_attempt,
        "expected_days": expected_days,
        "expected_hours": expected_hours,
        "resolved_hours": resolved_hours,
        "tick_rows": tick_rows,
        "recovered_day_count": len(sorted(set(recovered_dates))),
        "recovered_dates": sorted(set(recovered_dates)),
        "accepted": accepted,
        "months": monthly,
        "mt4_boundary": (
            "Raw BI5 and deterministic decoded Bid/Ask Tick CSV.GZ files are preserved. "
            "FXT/HST or the selected importer conversion is still required before MT4 Strategy Tester use."
        ),
    }
    if not accepted:
        raise SystemExit(
            f"annual validation failed days={expected_days} expected_hours={expected_hours} resolved={resolved_hours}"
        )
    annual_path = root / "eurusd-2024-raw-ticks-v1.annual-manifest.json"
    annual_path.write_text(json.dumps(annual, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    notes = root / "RELEASE_NOTES.md"
    notes.write_text(
        "# EURUSD 2024 Raw Dukascopy Bid/Ask Ticks v1\n\n"
        "- Period: 2024-01-01 through 2025-01-01 UTC\n"
        f"- Source workflow run: {args.source_run_id}, attempt {args.source_run_attempt}\n"
        f"- Recovery/package workflow run: {args.package_run_id}, attempt {args.package_run_attempt}\n"
        f"- Recovered days: {len(sorted(set(recovered_dates)))}\n"
        "- Preserves exact hourly Dukascopy BI5 payloads and deterministic decoded Bid/Ask Tick CSV.GZ files.\n"
        "- This is a public Dukascopy proxy, not Rakuten quotes.\n"
        "- MT4 Strategy Tester use requires FXT/HST generation or the selected importer conversion.\n",
        encoding="utf-8",
    )

    checksum_path = root / "SHA256SUMS"
    with checksum_path.open("w", encoding="utf-8", newline="\n") as fh:
        for path in sorted(root.iterdir()):
            if path.is_file() and path.name != "SHA256SUMS":
                fh.write(f"{sha256_file(path)}  {path.name}\n")
    print(json.dumps({
        "accepted": True,
        "expected_days": expected_days,
        "expected_hours": expected_hours,
        "resolved_hours": resolved_hours,
        "tick_rows": tick_rows,
        "recovered_day_count": len(sorted(set(recovered_dates))),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
