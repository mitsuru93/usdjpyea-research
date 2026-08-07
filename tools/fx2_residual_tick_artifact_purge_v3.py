#!/usr/bin/env python3
"""Run residual Tick purge with exact current USDJPY/EURUSD Release contracts."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import fx2_residual_tick_artifact_purge_v1 as v1
from tools.fx2_residual_tick_artifact_purge_v2 import validate_usdjpy_2024


def validate_eurusd_year(api: v1.base.GitHubApi, year: int) -> dict[str, Any]:
    tag = f"eurusd-{year}-raw-bidask-ticks-v1"
    identity, assets = v1.stable_release(api, tag)
    expected = {
        f"eurusd-{year}-{month:02d}-raw-ticks-v1.{suffix}"
        for month in range(1, 13)
        for suffix in ("tar.gz", "manifest.json", "SHA256SUMS")
    }
    expected |= {
        f"eurusd-{year}-raw-ticks-v1.annual-manifest.json",
        "RELEASE_NOTES.md",
        "SHA256SUMS",
    }
    if set(assets) != expected:
        raise v1.Error(
            f"EURUSD Release inventory mismatch {tag}: "
            f"missing={sorted(expected-set(assets))} extra={sorted(set(assets)-expected)}"
        )
    for row in assets.values():
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", row["digest"], flags=re.I):
            raise v1.Error(f"EURUSD Release asset lacks SHA-256: {tag}/{row['name']}")
    return {"authority_type": "complete_year_raw_release", "year": year, **identity}


def validate_authorities(api: v1.base.GitHubApi) -> dict[str, dict[str, Any]]:
    fixed = v1.load_fixed()
    fixed.validate_year_release = lambda api_obj, year, tag: v1.exact_year_release(fixed, api_obj, year, tag)
    authorities: dict[str, dict[str, Any]] = {}

    source_native = fixed.validate_source_native(api, ROOT)
    authorities["USDJPY:2019Q4-2022"] = {
        "authority_type": "source_native_tick_authority",
        **source_native,
    }
    for year, tag in (
        (2023, "usdjpy-2023-raw-bidask-ticks-v1"),
        (2025, "usdjpy-2025-raw-bidask-ticks-v1"),
    ):
        authorities[f"USDJPY:{year}"] = fixed.validate_year_release(api, year, tag)
    authorities["USDJPY:2024"] = validate_usdjpy_2024(api)

    for year in (2020, 2021, 2022, 2023):
        authorities[f"EURUSD:{year}"] = validate_eurusd_year(api, year)
    authorities["EURUSD:2024"] = v1.eur_2024.release_identity(api)

    for key, row in authorities.items():
        row["authority_key"] = key
        row["authority_evidence_sha256"] = v1.sha(row)
    return dict(sorted(authorities.items()))


def main() -> None:
    v1.validate_usdjpy_2024 = validate_usdjpy_2024
    v1.validate_authorities = validate_authorities
    v1.main()


if __name__ == "__main__":
    main()
