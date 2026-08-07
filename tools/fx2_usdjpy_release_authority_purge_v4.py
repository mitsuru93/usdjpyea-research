#!/usr/bin/env python3
"""Run the repaired USDJPY authority controller with exact yearly inventories.

The 2023 and 2025 Releases each contain:
- 12 monthly tar.gz packages;
- 12 monthly manifests;
- 12 monthly SHA256SUMS files;
- one aggregate SHA256SUMS;
- one annual manifest.
All 38 asset identities are sealed into the candidate digest.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.fx2_usdjpy_release_authority_purge_v3 import load_fixed


def exact_year_release(module: Any, api: Any, year: int, tag: str) -> dict[str, Any]:
    identity, assets = module.stable_assets(api, tag)
    expected = {"SHA256SUMS", f"usdjpy-{year}-raw-ticks-v1.annual-manifest.json"}
    expected |= {
        f"usdjpy-{year}-{month:02d}-raw-ticks-v1.{suffix}"
        for month in range(1, 13)
        for suffix in ("tar.gz", "manifest.json", "SHA256SUMS")
    }
    observed = set(assets)
    if observed != expected:
        raise module.Error(
            f"year Release inventory mismatch {tag}: "
            f"missing={sorted(expected-observed)} extra={sorted(observed-expected)}"
        )
    if identity["asset_count"] != 38:
        raise module.Error(
            f"year Release asset count mismatch {tag}: {identity['asset_count']} != 38"
        )
    annual = assets[f"usdjpy-{year}-raw-ticks-v1.annual-manifest.json"]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", annual["digest"], flags=re.I):
        raise module.Error(f"annual manifest lacks SHA-256: {tag}")
    return {
        "authority_type": "complete_year_raw_release",
        "year": year,
        "annual_manifest_asset_id": annual["id"],
        "annual_manifest_digest": annual["digest"],
        **identity,
    }


def main() -> None:
    module = load_fixed()
    module.validate_year_release = lambda api, year, tag: exact_year_release(
        module, api, year, tag
    )
    module.main()


if __name__ == "__main__":
    main()
