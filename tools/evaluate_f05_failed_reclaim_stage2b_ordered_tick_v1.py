#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]
YEAR_PATTERNS = {
    2023: re.compile(r"usdjpy-2023-\d{2}-raw-ticks-v1\.tar\.gz$"),
    2024: re.compile(r"usdjpy-2024-\d{2}-raw-ticks-v1\.tar\.gz$"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--raw-tick-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    prereg_path = Path(args.prereg)
    raw_dir = Path(args.raw_tick_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    prereg = json.loads(prereg_path.read_text())
    assert prereg["analysis_boundary"]["included_periods"] == FOLDS
    assert prereg["analysis_boundary"]["excluded_periods"] == ["2025H1", "2025H2"]
    assert prereg["analysis_boundary"]["selection_must_not_access_excluded_periods"] is True
    assert prereg["analysis_boundary"]["all_included_periods_require_ordered_bid_ask_ticks"] is True
    assert prereg["production_authorization"] is False

    archives = sorted(p for p in raw_dir.rglob("*.tar.gz") if p.is_file())
    by_year = {
        year: [p for p in archives if YEAR_PATTERNS[year].search(p.name)]
        for year in (2023, 2024)
    }
    missing_years = [year for year, files in by_year.items() if not files]

    axes = prereg["ordered_tick_axes"]
    grid_count = (
        len(prereg["structural_candidates"])
        * len(axes["profit_disarm_threshold_executable_pips"])
        * len(axes["profit_persistence"])
        * len(axes["failure_confirmation"])
        * len(axes["exit_delay_seconds"])
    )

    status = "READY_STAGE2B_ORDERED_TICK_GRID" if not missing_years else "BLOCKED_STAGE2B_MISSING_ORDERED_TICK_AUTHORITY"
    result = {
        "schema_version": "1.0",
        "status": status,
        "analysis_periods": FOLDS,
        "excluded_periods_not_accessed": ["2025H1", "2025H2"],
        "ordered_tick_archives": {
            str(year): [p.name for p in files] for year, files in by_year.items()
        },
        "missing_ordered_tick_years": missing_years,
        "grid_candidate_count": grid_count,
        "selection_executed": False,
        "proxy_substitution_used": False,
        "production_authorization": False,
        "next_action": (
            "run full Stage 2B grid" if not missing_years
            else "finish and publish missing ordered Bid/Ask Tick authority, then rerun without changing preregistration"
        ),
    }
    (out / "preflight_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": "1.0",
        "evaluator_sha256": sha256(Path(__file__)),
        "prereg_sha256": sha256(prereg_path),
        "raw_tick_files": {
            p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in archives
        },
        "result_sha256": sha256(out / "preflight_result.json"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
