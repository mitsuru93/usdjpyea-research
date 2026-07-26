#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected exactly one {name}, found {len(hits)}")
    return hits[0]


def normalize_nullable(value):
    if pd.isna(value):
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def json_safe(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--prereg", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    root = Path(args.input_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prereg_path = Path(args.prereg)
    prereg = json.loads(prereg_path.read_text())

    assert prereg["analysis_boundary"]["included_periods"] == FOLDS
    assert prereg["analysis_boundary"]["selection_must_not_access_excluded_periods"] is True

    grid_path = find_one(root, "natural_family_grid.csv")
    lofo_path = find_one(root, "natural_family_lofo.csv")
    stopped_path = find_one(root, "refined_failed_reclaim_stopped_trades.csv")
    fold_path = find_one(root, "refined_failed_reclaim_fold_metrics.csv")
    breadth_path = find_one(root, "refined_breadth_metrics.csv")

    grid = pd.read_csv(grid_path)
    allowed_time = set(prereg["grid"]["monitoring_minutes"])
    allowed_cons = set(prereg["grid"]["maximum_sequence_count"])
    allowed_close = set(prereg["grid"]["close_buffer_pips"])

    candidates = grid.copy()
    candidates["max_cons_norm"] = candidates["max_cons"].map(normalize_nullable)
    candidates["max_time_norm"] = candidates["max_time"].map(normalize_nullable)
    candidates["max_reclaim_norm"] = candidates["max_reclaim"].map(normalize_nullable)
    candidates = candidates[candidates["max_time_norm"].isin(allowed_time)]
    candidates = candidates[candidates["max_cons_norm"].map(lambda x: x in allowed_cons)]
    candidates = candidates[candidates["close_buf"].isin(allowed_close)]
    candidates = candidates[candidates["max_reclaim_norm"].isna()]
    if candidates.empty:
        raise RuntimeError("no preregistered structural candidates found")

    candidates["all_four_folds_non_negative"] = candidates["positive_folds"].eq(4)
    candidates["winner_damage_abs"] = candidates["winner_damage"].abs()
    ranked = candidates.sort_values(
        [
            "all_four_folds_non_negative",
            "winner_damage_abs",
            "loser_benefit",
            "min_fold",
            "total",
            "stopped",
        ],
        ascending=[False, True, False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    ranked.to_csv(out / "structural_grid_ranked.csv", index=False)

    top = {key: json_safe(value) for key, value in ranked.iloc[0].to_dict().items()}
    lofo = pd.read_csv(lofo_path)
    stopped = pd.read_csv(stopped_path)
    fold = pd.read_csv(fold_path)
    breadth = pd.read_csv(breadth_path)

    lofo.to_csv(out / "leave_one_fold_out.csv", index=False)
    stopped.to_csv(out / "changed_trade_ledger.csv", index=False)
    fold.to_csv(out / "fold_metrics.csv", index=False)
    breadth.to_csv(out / "breadth_metrics.csv", index=False)

    winner = stopped[stopped["baseline_pips"] > 0].copy()
    winner.to_csv(out / "winner_damage_audit.csv", index=False)
    monthly = stopped.groupby(["fold", "month"], as_index=False).agg(
        delta=("delta", "sum"), stopped=("trade_idx", "count")
    )
    monthly.to_csv(out / "monthly_metrics.csv", index=False)
    direction = stopped.groupby(["fold", "side"], as_index=False).agg(
        delta=("delta", "sum"), stopped=("trade_idx", "count")
    )
    direction.to_csv(out / "direction_metrics.csv", index=False)

    result = {
        "schema_version": "1.0",
        "status": "PASS_STAGE2A_STRUCTURAL_GRID",
        "analysis_periods": FOLDS,
        "excluded_periods_not_accessed": prereg["analysis_boundary"]["excluded_periods"],
        "selected_structural_candidate": top,
        "candidate_count": int(len(ranked)),
        "stage2b_required_for_exact_tick_axes": [
            "profit_disarm_threshold_executable_pips",
            "profit_persistence",
            "failure_confirmation_M1_modes",
            "exit_delay_seconds",
        ],
        "production_authorization": False,
    }
    (out / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )

    manifest = {
        "schema_version": "1.0",
        "evaluator_sha256": sha256(Path(__file__)),
        "prereg_sha256": sha256(prereg_path),
        "input_files": {
            p.name: {"sha256": sha256(p), "bytes": p.stat().st_size}
            for p in [grid_path, lofo_path, stopped_path, fold_path, breadth_path]
        },
        "output_files": {},
        "excluded_periods_not_accessed": prereg["analysis_boundary"]["excluded_periods"],
    }
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name not in {"manifest.json", "sha256sums.txt"}:
            manifest["output_files"][path.name] = {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with (out / "sha256sums.txt").open("w") as f:
        for name, metadata in sorted(manifest["output_files"].items()):
            f.write(f"{metadata['sha256']}  {name}\n")
        f.write(f"{sha256(out / 'manifest.json')}  manifest.json\n")

    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
