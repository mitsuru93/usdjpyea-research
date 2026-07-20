#!/usr/bin/env python3
"""Verify the USDJPY 2025 replication preregistration before any 2025 access."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

LOCKED_BLOBS = {
    "configs/research/usdjpy_2025_full_year_replication_v1.json": "3c883bf3bb808388664de5f54e1bcc056cb9e913",
    "docs/research_reboot/usdjpy_2025_full_year_replication_prereg_v1.md": "dbd8009bba6185c22c25575a8e536ccb95525e3e",
    "docs/research_reboot/usdjpy_research_roadmap_2024_primary_2025_replication_v4.md": "1a569bf09283270944571eea8262846222ae8c3d",
    "docs/research_reboot/usdjpy_v1_candidate_specific_h2_validation_result_v1.md": "7888e1659639c4abf5ad36659feed44f76277fcb",
}


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    lock_path = root / "configs/research/usdjpy_2025_full_year_replication_prereg_lock_v1.json"
    config_path = root / "configs/research/usdjpy_2025_full_year_replication_v1.json"
    if not lock_path.is_file() or not config_path.is_file():
        raise RuntimeError("2025 replication preregistration files are missing")

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    results: dict[str, dict[str, object]] = {}
    for relative, expected in LOCKED_BLOBS.items():
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"locked file is missing: {relative}")
        payload = path.read_bytes()
        actual = git_blob_sha1(payload)
        if actual != expected:
            raise RuntimeError(f"locked file changed: {relative} {actual} != {expected}")
        declared = lock["locked_files"][relative]["git_blob_sha1"]
        if declared != expected:
            raise RuntimeError(f"lock declaration changed: {relative} {declared} != {expected}")
        results[relative] = {
            "git_blob_sha1": actual,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "pass": True,
        }

    assert config["period"] == {
        "start_utc": "2025-01-01T00:00:00Z",
        "end_utc_exclusive": "2026-01-01T00:00:00Z",
        "continuous_block": True,
        "mandatory_half_year_subgates": False,
    }
    expected_survivors = [
        "R1B02_legacy_asia_00_07_breakout__T0_fixed_time_cap",
        "R1F05_donchian_96__T0_fixed_time_cap",
    ]
    assert config["input_contract"]["survivor_strategy_ids"] == expected_survivors
    assert config["input_contract"]["strategy_count"] == 2
    assert config["input_contract"]["strategy_parameters_unchanged"] is True
    assert config["input_contract"]["ranking_prohibited"] is True
    assert config["input_contract"]["parameter_optimization_prohibited"] is True
    assert config["input_contract"]["failed_strategy_rescue_prohibited"] is True
    assert config["individual_gates"] == {
        "minimum_trades": 120,
        "average_default_net_pips_strictly_positive": True,
        "average_severe_net_pips_strictly_positive": True,
        "default_profit_factor_strictly_above": 1.0,
        "severe_profit_factor_strictly_above": 1.0,
        "minimum_default_positive_months_of_12": 8,
        "minimum_severe_positive_months_of_12": 6,
        "minimum_default_positive_quarters_of_4": 3,
        "minimum_severe_positive_quarters_of_4": 2,
        "total_default_net_pips_excluding_best_two_utc_entry_dates_strictly_positive": True,
        "maximum_largest_absolute_month_contribution_share": 0.60,
        "maximum_top_two_utc_entry_dates_share_of_positive_daily_pips": 0.50,
        "maximum_absolute_long_short_contribution_share": 0.95,
    }
    assert config["authorization_boundary"] == {
        "this_preregistration_opens_2025_results": False,
        "raw_tick_collection_may_begin_after_lock": True,
        "replication_run_may_begin_only_after_canonical_2025_bundle_is_locked": True,
        "Core_or_MT4_parameter_change_authorized": False,
        "live_capital_authorized": False,
    }
    firewall = lock["firewall_at_lock_creation"]
    if any(bool(value) for value in firewall.values()):
        raise RuntimeError(f"preregistration firewall contains an authorized/open state: {firewall}")

    output = {
        "schema_version": "usdjpy_2025_replication_prereg_lock_verification_v1",
        "status": "PASS",
        "lock_sha256": sha256_file(lock_path),
        "config_sha256": sha256_file(config_path),
        "locked_files": results,
        "survivor_strategy_ids": expected_survivors,
        "2025_strategy_results_opened": False,
        "raw_tick_collection_authorized": True,
        "replication_evaluation_authorized": False,
        "live_capital_authorized": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
