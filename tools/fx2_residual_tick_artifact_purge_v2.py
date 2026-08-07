#!/usr/bin/env python3
"""Run residual Tick purge with the observed USDJPY 2024 Release naming contract."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import fx2_residual_tick_artifact_purge_v1 as v1


def validate_usdjpy_2024(api: v1.base.GitHubApi) -> dict[str, Any]:
    receipt = v1.json.loads(v1.USDJPY_2024_RECEIPT.read_text(encoding="utf-8"))
    durable = receipt.get("durable_release") or {}
    validation = receipt.get("annual_validation") or {}
    if receipt.get("archive_status") != "durably_archived_in_github_release_and_receipt_committed":
        raise v1.Error("USDJPY 2024 archive status mismatch")
    if durable.get("tag") != v1.USDJPY_2024_TAG or durable.get("asset_count") != 64:
        raise v1.Error("USDJPY 2024 receipt Release identity mismatch")
    if durable.get("actions_artifact_expiry_independent") is not True:
        raise v1.Error("USDJPY 2024 Release is not Actions-expiry independent")
    if validation.get("accepted") is not True or validation.get("present_days") != 366 or validation.get("resolved_hours") != 8784:
        raise v1.Error("USDJPY 2024 annual validation mismatch")
    if validation.get("missing_404_hours") != 0 or validation.get("error_hours") != 0:
        raise v1.Error("USDJPY 2024 annual validation has unresolved errors")

    identity, assets = v1.stable_release(api, v1.USDJPY_2024_TAG)
    expected = {
        f"usdjpy-2024-{month:02d}-raw-ticks-v1.{suffix}"
        for month in range(1, 13)
        for suffix in ("tar.gz", "manifest.json", "SHA256SUMS")
    }
    expected |= {
        f"usdjpy-2024-{month:02d}-{suffix}.json"
        for month in range(1, 13)
        for suffix in ("source-artifacts", "repair-artifacts")
    }
    expected |= {
        "usdjpy-2024-raw-ticks-v1.annual-manifest.json",
        "usdjpy-2024-raw-tick-repair-lock-v1.json",
        "RELEASE_NOTES.md",
        "SHA256SUMS",
    }
    if set(assets) != expected or identity["asset_count"] != 64:
        raise v1.Error(
            f"USDJPY 2024 Release inventory mismatch missing={sorted(expected-set(assets))} "
            f"extra={sorted(set(assets)-expected)}"
        )
    for row in assets.values():
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", row["digest"], flags=re.I):
            raise v1.Error(f"USDJPY 2024 Release asset lacks SHA-256: {row['name']}")
    return {
        "authority_type": "complete_year_raw_release",
        "year": 2024,
        "receipt_sha256": v1.file_sha(v1.USDJPY_2024_RECEIPT),
        **identity,
    }


def main() -> None:
    v1.validate_usdjpy_2024 = validate_usdjpy_2024
    v1.main()


if __name__ == "__main__":
    main()
