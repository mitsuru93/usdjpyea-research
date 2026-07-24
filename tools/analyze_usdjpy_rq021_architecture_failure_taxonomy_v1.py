#!/usr/bin/env python3
"""Describe failure modes in the already-opened RQ-020E four-fold census.

This evaluator opens no new market outcomes and does not generate or rank a
candidate. It attributes the frozen 660-cell result by family, horizon,
direction and weakest fold, then records one architecture-information gap for
ledger duplicate review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PERIODS = ["2023H1", "2023H2", "2024H1", "2024H2"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_json(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {key: clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    return value


def build_cell_taxonomy(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (candidate_id, family, horizon), group in metrics.groupby(
        ["candidate_id", "family", "horizon_bars"], sort=True
    ):
        fold = group.set_index("period").reindex(PERIODS)
        if fold.isna().any().any():
            raise AssertionError((candidate_id, horizon, "incomplete fold grid"))
        default_ok = (fold["default_net_pips"] > 0) & (fold["default_pf"] >= 1)
        severe_ok = (fold["severe_net_pips"] > 0) & (fold["severe_pf"] >= 1)
        breadth_ok = (
            (fold["positive_months"] >= 4)
            & (fold["negative_months"] <= 2)
            & (fold["ex_best_two_dates"] > 0)
        )
        severe_values = fold["severe_net_pips"].to_numpy(float)
        default_values = fold["default_net_pips"].to_numpy(float)
        rows.append(
            {
                "candidate_id": candidate_id,
                "family": family,
                "horizon_bars": int(horizon),
                "default_pass_folds": int(default_ok.sum()),
                "severe_pass_folds": int(severe_ok.sum()),
                "breadth_pass_folds": int(breadth_ok.sum()),
                "weakest_severe_fold": str(fold["severe_net_pips"].idxmin()),
                "minimum_fold_default_net": float(default_values.min()),
                "minimum_fold_severe_net": float(severe_values.min()),
                "fourfold_default_net": float(default_values.sum()),
                "fourfold_severe_net": float(severe_values.sum()),
                "severe_range": float(severe_values.max() - severe_values.min()),
                "default_sign_changes": int(
                    np.sum(np.sign(default_values[:-1]) != np.sign(default_values[1:]))
                ),
                "severe_sign_changes": int(
                    np.sum(np.sign(severe_values[:-1]) != np.sign(severe_values[1:]))
                ),
            }
        )
    result = pd.DataFrame(rows)
    if len(result) != 660:
        raise AssertionError(("cell count", len(result)))
    return result


def build_family_taxonomy(cell: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for family, group in cell.groupby("family", sort=True):
        weakest = group["weakest_severe_fold"].value_counts().reindex(PERIODS, fill_value=0)
        fold_metrics = metrics[metrics["family"] == family]
        row: dict[str, Any] = {
            "family": family,
            "entries": int(group["candidate_id"].nunique()),
            "cells": int(len(group)),
            "default_4fold_cells": int((group["default_pass_folds"] == 4).sum()),
            "severe_4fold_cells": int((group["severe_pass_folds"] == 4).sum()),
            "median_default_pass_folds": float(group["default_pass_folds"].median()),
            "median_severe_pass_folds": float(group["severe_pass_folds"].median()),
            "median_minimum_fold_default_net": float(group["minimum_fold_default_net"].median()),
            "median_minimum_fold_severe_net": float(group["minimum_fold_severe_net"].median()),
            "median_fourfold_default_net": float(group["fourfold_default_net"].median()),
            "median_fourfold_severe_net": float(group["fourfold_severe_net"].median()),
            "median_severe_range": float(group["severe_range"].median()),
        }
        for period in PERIODS:
            row[f"weakest_{period}"] = int(weakest[period])
            period_rows = fold_metrics[fold_metrics["period"] == period]
            row[f"median_default_net_{period}"] = float(period_rows["default_net_pips"].median())
            row[f"median_severe_net_{period}"] = float(period_rows["severe_net_pips"].median())
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["severe_4fold_cells", "default_4fold_cells", "median_minimum_fold_severe_net"],
        ascending=[False, False, False],
    )


def build_horizon_taxonomy(cell: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for horizon, group in cell.groupby("horizon_bars", sort=True):
        weakest = group["weakest_severe_fold"].value_counts().reindex(PERIODS, fill_value=0)
        fold_metrics = metrics[metrics["horizon_bars"] == horizon]
        row: dict[str, Any] = {
            "horizon_bars": int(horizon),
            "cells": int(len(group)),
            "default_4fold_cells": int((group["default_pass_folds"] == 4).sum()),
            "severe_4fold_cells": int((group["severe_pass_folds"] == 4).sum()),
            "median_default_pass_folds": float(group["default_pass_folds"].median()),
            "median_severe_pass_folds": float(group["severe_pass_folds"].median()),
            "median_minimum_fold_default_net": float(group["minimum_fold_default_net"].median()),
            "median_minimum_fold_severe_net": float(group["minimum_fold_severe_net"].median()),
            "median_fourfold_default_net": float(group["fourfold_default_net"].median()),
            "median_fourfold_severe_net": float(group["fourfold_severe_net"].median()),
            "median_severe_range": float(group["severe_range"].median()),
            "median_trade_count": float(fold_metrics["trades"].median()),
        }
        for period in PERIODS:
            row[f"weakest_{period}"] = int(weakest[period])
        rows.append(row)
    return pd.DataFrame(rows).sort_values("horizon_bars")


def build_direction_taxonomy(direction: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pivot = direction.pivot_table(
        index=["candidate_id", "family", "horizon_bars", "period"],
        columns="side",
        values=["default_net_pips", "severe_net_pips", "trades"],
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    pivot.columns = [
        "candidate_id",
        "family",
        "horizon_bars",
        "period",
    ] + [f"{metric}_{'short' if side == -1 else 'long'}" for metric, side in pivot.columns[4:]]
    for column in [
        "default_net_pips_short", "default_net_pips_long",
        "severe_net_pips_short", "severe_net_pips_long",
        "trades_short", "trades_long",
    ]:
        if column not in pivot:
            pivot[column] = 0.0
    pivot["dominant_severe_side"] = np.where(
        pivot["severe_net_pips_long"] > pivot["severe_net_pips_short"],
        "long",
        np.where(
            pivot["severe_net_pips_short"] > pivot["severe_net_pips_long"],
            "short",
            "tie",
        ),
    )
    pivot["long_severe_positive"] = pivot["severe_net_pips_long"] > 0
    pivot["short_severe_positive"] = pivot["severe_net_pips_short"] > 0
    pivot["both_severe_positive"] = (
        pivot["long_severe_positive"] & pivot["short_severe_positive"]
    )

    rows: list[dict[str, Any]] = []
    for (candidate_id, family, horizon), group in pivot.groupby(
        ["candidate_id", "family", "horizon_bars"], sort=True
    ):
        fold = group.set_index("period").reindex(PERIODS)
        dominant = fold["dominant_severe_side"].tolist()
        rows.append(
            {
                "candidate_id": candidate_id,
                "family": family,
                "horizon_bars": int(horizon),
                "long_positive_folds": int(fold["long_severe_positive"].sum()),
                "short_positive_folds": int(fold["short_severe_positive"].sum()),
                "both_positive_folds": int(fold["both_severe_positive"].sum()),
                "same_dominant_side_all_folds": len(set(dominant)) == 1,
                "dominant_side_sequence": "|".join(dominant),
                "dominant_side_switches": int(
                    sum(left != right for left, right in zip(dominant, dominant[1:]))
                ),
                "long_fourfold_severe_net": float(fold["severe_net_pips_long"].sum()),
                "short_fourfold_severe_net": float(fold["severe_net_pips_short"].sum()),
            }
        )
    return pivot, pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell-fold-metrics", required=True, type=Path)
    parser.add_argument("--direction-metrics", required=True, type=Path)
    parser.add_argument("--census-result", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    census = json.loads(args.census_result.read_text(encoding="utf-8"))
    if census.get("status") != "CLOSED_NO_FAMILY_REGION":
        raise AssertionError("RQ-020E census is not closed")
    metrics = pd.read_csv(args.cell_fold_metrics)
    direction = pd.read_csv(args.direction_metrics)
    if len(metrics) != 2640 or len(direction) != 5280:
        raise AssertionError((len(metrics), len(direction)))

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    cell = build_cell_taxonomy(metrics)
    family = build_family_taxonomy(cell, metrics)
    horizon = build_horizon_taxonomy(cell, metrics)
    direction_fold, direction_cell = build_direction_taxonomy(direction)

    paths = {
        "cell": output / "usdjpy_rq021_cell_failure_taxonomy_v1.csv",
        "family": output / "usdjpy_rq021_family_failure_taxonomy_v1.csv",
        "horizon": output / "usdjpy_rq021_horizon_failure_taxonomy_v1.csv",
        "direction_fold": output / "usdjpy_rq021_direction_fold_taxonomy_v1.csv",
        "direction_stability": output / "usdjpy_rq021_direction_stability_v1.csv",
    }
    cell.to_csv(paths["cell"], index=False, lineterminator="\n")
    family.to_csv(paths["family"], index=False, lineterminator="\n")
    horizon.to_csv(paths["horizon"], index=False, lineterminator="\n")
    direction_fold.to_csv(paths["direction_fold"], index=False, lineterminator="\n")
    direction_cell.to_csv(paths["direction_stability"], index=False, lineterminator="\n")

    result = {
        "schema_version": "usdjpy_rq021_architecture_failure_taxonomy_result_v1",
        "status": "DESCRIPTIVE_TAXONOMY_COMPLETE_ONE_DISTINCT_QUESTION_IDENTIFIED",
        "research_question": "USDJPY-RQ-021",
        "source_scope": "already opened RQ-020E outputs only",
        "source_sha256": {
            "census_result": sha256_file(args.census_result),
            "cell_fold_metrics": sha256_file(args.cell_fold_metrics),
            "direction_metrics": sha256_file(args.direction_metrics),
        },
        "population": {
            "cells": int(len(cell)),
            "families": int(cell["family"].nunique()),
            "horizons": int(cell["horizon_bars"].nunique()),
            "cell_fold_rows": int(len(metrics)),
            "direction_rows": int(len(direction)),
        },
        "fold_pass_distribution": {
            "default": {str(key): int(value) for key, value in cell["default_pass_folds"].value_counts().sort_index().items()},
            "severe": {str(key): int(value) for key, value in cell["severe_pass_folds"].value_counts().sort_index().items()},
            "breadth": {str(key): int(value) for key, value in cell["breadth_pass_folds"].value_counts().sort_index().items()},
        },
        "weakest_severe_fold_counts": {
            key: int(value) for key, value in cell["weakest_severe_fold"].value_counts().items()
        },
        "direction_taxonomy": {
            "same_dominant_side_all_four_folds_cells": int(direction_cell["same_dominant_side_all_folds"].sum()),
            "dominant_side_switch_at_least_once_cells": int((direction_cell["dominant_side_switches"] >= 1).sum()),
            "dominant_side_switch_two_or_more_cells": int((direction_cell["dominant_side_switches"] >= 2).sum()),
            "long_severe_positive_all_four_cells": int((direction_cell["long_positive_folds"] == 4).sum()),
            "short_severe_positive_all_four_cells": int((direction_cell["short_positive_folds"] == 4).sum()),
            "both_directions_severe_positive_all_four_cells": int((direction_cell["both_positive_folds"] == 4).sum()),
        },
        "retained_findings": [
            "Cost fragility is architecture-wide: 14 cells pass all folds at default cost but only one at severe cost.",
            "The weakest fold is distributed across all four periods, with 2024H2 most frequent but not dominant enough to explain closure alone.",
            "Dominant direction changes in 562 of 660 cells, so static M15 direction rules are strongly regime dependent.",
            "No fixed horizon forms a robust family neighbourhood; longer holds improve isolated continuation cells but worsen the median minimum-fold severe result.",
            "Session-handoff is the least-failed family, but it has only one isolated core cell and no full or neighbourhood pass.",
        ],
        "information_gap": {
            "identified_dimension": "native higher-timeframe state-transition architecture with state-conditional event termination",
            "why_absent_from_R1_R2": "R1 entries are generated from M15-local patterns or session references and R2 exits are unconditional fixed M15 horizons. A longer M15 lookback or 24/48-bar hold is not a completed H1/H4 state transition or an event-defined termination.",
            "duplicate_audit": {
                "Families_A_I": "tested shock/admission, overlap, event confirmation and checkpoint/state-adaptive repairs applied to existing B02/F05 or M15 signals",
                "RQ_020B": "tested static 5-day/20-day state partitions and action routing, not native higher-timeframe signal construction",
                "RQ_020E": "exhausted all frozen M15 Entry x fixed-time horizon cells",
                "distinct_information": "the primary signal and its termination are both defined by completed native higher-timeframe structure rather than used as an overlay on an M15 entry",
            },
            "successor_question_id": "USDJPY-RQ-022",
            "successor_question": "Can a native H1/H4 state-transition architecture, with entry and termination events defined on completed higher-timeframe structure rather than an M15 pattern plus fixed horizon, produce a broad family region across all four development folds?",
            "candidate_generated": False,
            "family_preregistered": False,
        },
        "output_sha256": {key: sha256_file(path) for key, path in paths.items()},
        "boundaries": {
            "new_market_outcomes_accessed": False,
            "cell_retuned": False,
            "horizon_added": False,
            "candidate_generated": False,
            "family_preregistered": False,
            "MT4_accessed": False,
            "2025_accessed": False,
            "live_orders": False,
        },
    }
    result = clean_json(result)
    result_path = output / "usdjpy_rq021_architecture_failure_taxonomy_result_v1.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
