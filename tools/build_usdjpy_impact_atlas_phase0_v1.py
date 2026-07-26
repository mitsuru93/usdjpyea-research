#!/usr/bin/env python3
"""Build the Phase 0 source/lineage audit for USDJPY Impact Atlas v1.

This command performs no candidate selection and never reads 2025 market outcomes.
It inventories repository-resident contracts/results and reports missing authorities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


REQUIRED_REPOSITORY_PATHS = (
    "docs/research/USDJPY_CURRENT_RESEARCH_STATE.md",
    "docs/research/USDJPY_IMPACT_ATLAS_PROGRAM_V1.md",
    "configs/research/usdjpy_impact_atlas_v1_prereg.json",
    "configs/research/usdjpy_b02_f05_experiment_registry_v1.json",
)

HISTORICAL_FOLDS = ("2023H1", "2023H2", "2024H1", "2024H2")
EXCLUDED_SELECTION_PERIODS = ("2025H1", "2025H2")


@dataclass(frozen=True)
class FileIdentity:
    path: str
    exists: bool
    size_bytes: int | None
    sha256: str | None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identify(root: Path, relative_paths: Iterable[str]) -> list[FileIdentity]:
    rows: list[FileIdentity] = []
    for relative in relative_paths:
        path = root / relative
        if path.is_file():
            rows.append(FileIdentity(relative, True, path.stat().st_size, sha256_file(path)))
        else:
            rows.append(FileIdentity(relative, False, None, None))
    return rows


def discover_evidence(root: Path) -> list[FileIdentity]:
    patterns = (
        "docs/research/*factor*",
        "docs/research/*lifecycle*",
        "docs/research/*structural*",
        "docs/research/*failed_reclaim*",
        "configs/research/*factor*",
        "configs/research/*lifecycle*",
        "configs/research/*structural*",
        "configs/research/*failed_reclaim*",
    )
    paths: set[str] = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file():
                paths.add(path.relative_to(root).as_posix())
    return identify(root, sorted(paths))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    required = identify(root, REQUIRED_REPOSITORY_PATHS)
    evidence = discover_evidence(root)
    missing = [row.path for row in required if not row.exists]

    payload = {
        "schema_version": "usdjpy_impact_atlas_phase0_source_audit_v1",
        "study_id": "USDJPY_IMPACT_ATLAS_V1",
        "status": "PASS_REPOSITORY_CONTRACT_AUDIT" if not missing else "BLOCKED_MISSING_REPOSITORY_CONTRACTS",
        "historical_folds": list(HISTORICAL_FOLDS),
        "excluded_selection_periods": list(EXCLUDED_SELECTION_PERIODS),
        "selection_executed": False,
        "2025_market_outcomes_accessed": False,
        "required_contracts": [asdict(row) for row in required],
        "discovered_evidence": [asdict(row) for row in evidence],
        "missing_required_paths": missing,
        "next_gate": "resolve accepted Release and dataset authorities before Phase 1" if not missing else "restore missing repository contracts",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "evidence_files": len(evidence), "missing": missing}))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
