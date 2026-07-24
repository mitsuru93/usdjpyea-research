from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from usdjpy_full_architecture_census_data_v1 import (
    EXPECTED, FOLDS, HORIZONS, aggregate_cell_fold, build_all_signals,
    build_trades, file_sha256, load_candidates, regress_h1_signals,
)
from usdjpy_full_architecture_census_gates_v1 import (
    evaluate_cells, signal_hashes, write_csv,
)
from usdjpy_fixed5_portability_lib_v1 import load23, load24


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.input_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol.get("status") != "FROZEN_BEFORE_CENSUS_OUTCOMES":
        raise RuntimeError("protocol is not frozen")

    paths = {
        "m15_2023": root / "work23/normalized/usdjpy_2023_m15_bid_utc_rakuten_mt4_v1.csv.gz",
        "m15_2024": root / "workr0/canonical/bars/M15/USDJPY_M15.csv.gz",
        "r1_signals": root / "workr1/candidate_signals.csv.gz",
        "r1_registry": root / "workr1/r1_registry_snapshot.json",
        "r2_summary": root / "workr2/candidate_horizon_summary.csv",
    }
    identities = {name: file_sha256(path) for name, path in paths.items()}
    if identities != EXPECTED:
        raise RuntimeError((identities, EXPECTED))

    candidates = load_candidates(paths["r1_registry"])
    bars23 = load23(paths["m15_2023"])
    bars24 = load24(paths["m15_2024"])

    signals_by_fold: dict[str, pd.DataFrame] = {}
    trades_by_fold: dict[str, pd.DataFrame] = {}
    for fold, (start, end) in FOLDS.items():
        bars = bars23 if fold.startswith("2023") else bars24
        signals = build_all_signals(bars, candidates, start, end, fold)
        signals_by_fold[fold] = signals
        trades_by_fold[fold] = build_trades(bars, signals, fold, start, end)

    h1_regression = regress_h1_signals(signals_by_fold["2024H1"], paths["r1_signals"])
    if not h1_regression["exact"]:
        raise RuntimeError(f"2024H1 signal regression failed: {h1_regression}")

    all_signals = pd.concat(signals_by_fold.values(), ignore_index=True)
    all_trades = pd.concat(trades_by_fold.values(), ignore_index=True)
    metrics = aggregate_cell_fold(all_trades)
    hashes = signal_hashes(all_signals, candidates)
    cells, entries, families = evaluate_cells(metrics, candidates, hashes)

    passing_families = families[families["family_region_gate"]].copy()
    if len(passing_families):
        passing_families = passing_families.sort_values(
            ["passing_entry_definitions", "full_gate_cells", "median_minimum_fold_severe_net_pips", "median_fourfold_severe_net_pips", "family"],
            ascending=[False, False, False, False, True],
        )
    retained = passing_families.head(1)["family"].tolist()

    write_csv(metrics, output / "usdjpy_full_architecture_census_cell_fold_metrics_v1.csv")
    write_csv(cells, output / "usdjpy_full_architecture_census_cell_gates_v1.csv")
    write_csv(entries, output / "usdjpy_full_architecture_census_entry_neighbourhoods_v1.csv")
    write_csv(families, output / "usdjpy_full_architecture_census_family_regions_v1.csv")

    result = {
        "schema_version": "usdjpy_full_frozen_architecture_census_result_v1",
        "status": "FAMILY_REGION_RETAINED_FOR_SEPARATE_PREREGISTRATION_REVIEW" if retained else "CLOSED_NO_FAMILY_REGION",
        "decision": "RETAIN_AT_MOST_ONE_FAMILY_REGION; NO_CELL_OR_CANDIDATE_SELECTED" if retained else "CLOSE_RQ_020E_NO_FAMILY_REGION",
        "research_question": "USDJPY-RQ-020E",
        "lineage": "USDJPY_HISTORICAL_2024_LEGACY_CONTRACT_APPLIED_TO_2023_V1",
        "input_sha256": identities,
        "2024H1_signal_regression": h1_regression,
        "population": {
            "candidates": 60,
            "horizons": HORIZONS,
            "cells": 660,
            "cell_fold_rows": int(len(metrics)),
            "signal_rows_by_fold": {fold: int(len(frame)) for fold, frame in signals_by_fold.items()},
            "trade_rows_by_fold": {fold: int(len(frame)) for fold, frame in trades_by_fold.items()},
        },
        "gate_counts": {
            "support_cells": int(cells["support_gate"].sum()),
            "core_cells": int(cells["core_gate"].sum()),
            "full_cells": int(cells["full_gate"].sum()),
            "entry_neighbourhoods": int(entries["entry_neighbourhood_gate"].sum()),
            "family_regions": int(families["family_region_gate"].sum()),
        },
        "retained_family_regions": retained,
        "passing_family_regions": passing_families.to_dict("records"),
        "boundaries": {
            "single_combination_selected": False,
            "candidate_generated": False,
            "entry_or_horizon_changed": False,
            "parameter_or_weight_optimized": False,
            "MT4_accessed": False,
            "2025_accessed": False,
            "live_orders": False,
        },
    }
    result["scientific_output_sha256"] = {
        path.name: file_sha256(path)
        for path in sorted(output.glob("*.csv"))
    }
    result_path = output / "usdjpy_full_frozen_architecture_census_result_v1.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
