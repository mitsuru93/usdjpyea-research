#!/usr/bin/env python3
"""Corrected entry-horizon diagnostic using one contiguous H1 development block.

Run 29582417411 reset signal history at every month boundary. The canonical H1
screen concatenates January-June bars before generating signals, so this v2
runner does the same. It remains development-only and never reads H2 results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import run_usdjpy_h1_entry_horizon_diagnostic_v1 as v1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", action="append", required=True, type=v1.base.parse_labeled_path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--horizon-config", required=True, type=Path)
    parser.add_argument("--session-config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    horizon_config = json.loads(args.horizon_config.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))
    horizons = [int(value) for value in horizon_config["horizon_bars"]]
    if horizons != sorted(set(horizons)) or 6 not in horizons:
        raise ValueError("horizon_bars must be unique, sorted and include 6")
    path_window = int(horizon_config["path_window_bars"])
    if path_window < max(horizons):
        raise ValueError("path_window_bars must be >= maximum horizon")
    if horizon_config.get("development_block_policy") != "concatenate_all_months_before_signal_generation":
        raise ValueError("development_block_policy must preserve canonical contiguous H1 semantics")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bar_frames: list[pd.DataFrame] = []
    coverage_rows: list[dict[str, object]] = []
    for month, root in sorted(dict(args.bars).items()):
        bars, coverage = v1.corrected.load_bars(month, root)
        bar_frames.append(bars)
        coverage_rows.append(coverage)
    bars = pd.concat(bar_frames, ignore_index=True).sort_values("timestamp_utc").reset_index(drop=True)

    horizon_frames: list[pd.DataFrame] = []
    path_frames: list[pd.DataFrame] = []
    definition_rows: list[dict[str, object]] = []
    for family_block in registry["families"]:
        family = str(family_block["family"])
        generator = v1.signal_function(family)
        for raw_candidate in family_block["candidates"]:
            candidate = dict(raw_candidate)
            candidate["base_spread_pips"] = float(registry["costs"]["base_spread_pips"])
            definition_id = v1.entry_definition_id(family, candidate)
            definition_rows.append(
                {
                    "candidate_id": candidate["id"],
                    "entry_definition_id": definition_id,
                    "family": family,
                    "registered_hold_bars": int(candidate["hold_bars"]),
                    "entry_parameters_json": json.dumps(
                        {
                            key: value
                            for key, value in candidate.items()
                            if key not in {"id", "hold_bars", "base_spread_pips"}
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                }
            )
            side = generator(bars, candidate)
            eligible = v1.eligible_signal_mask(bars, side, session_config)
            horizon_rows = v1.build_horizon_rows(
                bars, side, eligible, family, candidate, definition_id, horizons
            )
            if not horizon_rows.empty:
                horizon_frames.append(horizon_rows)
            path_rows = v1.build_path_rows(
                bars, side, eligible, family, candidate, definition_id, path_window
            )
            if not path_rows.empty:
                path_frames.append(path_rows)

    if not horizon_frames:
        raise RuntimeError("no horizon trades generated")
    if not path_frames:
        raise RuntimeError("no path trades generated")

    horizon_trades = pd.concat(horizon_frames, ignore_index=True)
    path_trades = pd.concat(path_frames, ignore_index=True)
    horizon_summary, horizon_monthly, stability = v1.build_horizon_summaries(
        horizon_trades, horizons
    )
    path_summary = v1.build_path_summary(path_trades)
    definition_map = pd.DataFrame(definition_rows).sort_values(
        ["family", "entry_definition_id", "candidate_id"]
    )

    horizon_trades.to_csv(output_dir / "horizon_trades.csv", index=False)
    horizon_summary.to_csv(output_dir / "horizon_summary.csv", index=False)
    horizon_monthly.to_csv(output_dir / "horizon_monthly.csv", index=False)
    path_trades.to_csv(output_dir / "entry_path_trades.csv", index=False)
    path_summary.to_csv(output_dir / "entry_path_summary.csv", index=False)
    stability.to_csv(output_dir / "horizon_stability.csv", index=False)
    definition_map.to_csv(output_dir / "entry_definition_map.csv", index=False)
    pd.DataFrame(coverage_rows).to_csv(output_dir / "source_bar_coverage.csv", index=False)

    metadata = {
        "version": "v2",
        "status": "development_diagnostic_only",
        "invalid_predecessor_run_id": 29582417411,
        "registry": str(args.registry),
        "horizon_config": str(args.horizon_config),
        "session_config": str(args.session_config),
        "months": sorted(dict(args.bars)),
        "horizons": horizons,
        "path_window_bars": path_window,
        "development_block_policy": "concatenate_all_months_before_signal_generation",
        "candidate_count": int(definition_map["candidate_id"].nunique()),
        "unique_entry_definition_count": int(definition_map["entry_definition_id"].nunique()),
        "h2_data_read": False,
        "promotion_decision": False,
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
