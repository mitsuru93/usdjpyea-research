from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd

from usdjpy_full_architecture_census_data_v1 import FOLDS, HORIZONS


def evaluate_cells(metrics: pd.DataFrame, candidates: list[dict[str, Any]], signal_hashes: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    grid = pd.MultiIndex.from_product(
        [[row["candidate_id"] for row in candidates], HORIZONS], names=["candidate_id", "horizon_bars"]
    ).to_frame(index=False)
    metadata = pd.DataFrame(candidates)[["candidate_id", "family", "definition_sha256"]]
    grid = grid.merge(metadata, on="candidate_id", how="left")

    cell_rows: list[dict[str, Any]] = []
    for row in grid.itertuples(index=False):
        current = metrics[(metrics["candidate_id"] == row.candidate_id) & (metrics["horizon_bars"] == row.horizon_bars)].set_index("fold")
        all_folds = set(current.index) == set(FOLDS)
        support = all_folds and bool((current["trades"] >= 20).all())
        core = support and bool((current["default_net_pips"] > 0).all()) and bool((current["default_pf"] >= 1).all()) and bool((current["severe_net_pips"] > 0).all()) and bool((current["severe_pf"] >= 1).all())
        full = core and bool((current["positive_months"] >= 4).all()) and bool((current["negative_months"] <= 2).all()) and bool((current["ex_best_two_dates_default_pips"] > 0).all())
        cell_rows.append(
            {
                "candidate_id": row.candidate_id,
                "family": row.family,
                "definition_sha256": row.definition_sha256,
                "signal_ledger_sha256": signal_hashes[row.candidate_id],
                "horizon_bars": int(row.horizon_bars),
                "all_four_folds": all_folds,
                "support_gate": support,
                "core_gate": core,
                "full_gate": full,
                "minimum_fold_trades": int(current["trades"].min()) if all_folds else 0,
                "minimum_fold_default_net_pips": float(current["default_net_pips"].min()) if all_folds else 0.0,
                "minimum_fold_severe_net_pips": float(current["severe_net_pips"].min()) if all_folds else 0.0,
                "fourfold_default_net_pips": float(current["default_net_pips"].sum()) if all_folds else 0.0,
                "fourfold_severe_net_pips": float(current["severe_net_pips"].sum()) if all_folds else 0.0,
                "full_gate_folds": int(((current["positive_months"] >= 4) & (current["negative_months"] <= 2) & (current["ex_best_two_dates_default_pips"] > 0)).sum()) if all_folds else 0,
            }
        )
    cells = pd.DataFrame(cell_rows)

    entry_rows: list[dict[str, Any]] = []
    for candidate_id, current in cells.groupby("candidate_id", sort=True):
        current = current.set_index("horizon_bars").reindex(HORIZONS)
        core_flags = current["core_gate"].fillna(False).astype(bool).tolist()
        runs: list[list[int]] = []
        run: list[int] = []
        for horizon, flag in zip(HORIZONS, core_flags):
            if flag:
                run.append(horizon)
            else:
                if run:
                    runs.append(run)
                run = []
        if run:
            runs.append(run)
        eligible_runs = [r for r in runs if len(r) >= 3 and any(bool(current.loc[h, "full_gate"]) for h in r)]
        first = current.iloc[0]
        entry_rows.append(
            {
                "candidate_id": candidate_id,
                "family": first["family"],
                "definition_sha256": first["definition_sha256"],
                "signal_ledger_sha256": first["signal_ledger_sha256"],
                "core_gate_cells": int(current["core_gate"].sum()),
                "full_gate_cells": int(current["full_gate"].sum()),
                "longest_contiguous_core_run": max((len(r) for r in runs), default=0),
                "eligible_contiguous_runs": "|".join(",".join(map(str, r)) for r in eligible_runs),
                "entry_neighbourhood_gate": bool(eligible_runs),
            }
        )
    entries = pd.DataFrame(entry_rows)

    family_rows: list[dict[str, Any]] = []
    core_cells = cells[cells["core_gate"]].copy()
    for family, current_entries in entries.groupby("family", sort=True):
        passing_entries = current_entries[current_entries["entry_neighbourhood_gate"]]
        family_core = core_cells[core_cells["family"] == family]
        distinct_definitions = int(passing_entries["definition_sha256"].nunique())
        distinct_signal_ledgers = int(passing_entries["signal_ledger_sha256"].nunique())
        median_min_severe = float(family_core["minimum_fold_severe_net_pips"].median()) if len(family_core) else 0.0
        gate = len(passing_entries) >= 2 and distinct_definitions >= 2 and distinct_signal_ledgers >= 2 and median_min_severe > 0
        family_rows.append(
            {
                "family": family,
                "entry_definitions": int(len(current_entries)),
                "passing_entry_definitions": int(len(passing_entries)),
                "distinct_passing_definition_sha256": distinct_definitions,
                "distinct_passing_signal_ledgers": distinct_signal_ledgers,
                "core_gate_cells": int(len(family_core)),
                "full_gate_cells": int(family_core["full_gate"].sum()) if len(family_core) else 0,
                "median_minimum_fold_severe_net_pips": median_min_severe,
                "median_fourfold_severe_net_pips": float(family_core["fourfold_severe_net_pips"].median()) if len(family_core) else 0.0,
                "family_region_gate": bool(gate),
            }
        )
    families = pd.DataFrame(family_rows)
    return cells, entries, families


def signal_hashes(signals: pd.DataFrame, candidates: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in candidates:
        current = signals[signals["candidate_id"] == row["candidate_id"]][["fold", "signal_ts", "entry_ts", "side"]].copy()
        payload = current.sort_values(["fold", "signal_ts", "side"]).to_csv(index=False, lineterminator="\n").encode()
        result[row["candidate_id"]] = hashlib.sha256(payload).hexdigest()
    return result


def write_csv(frame: pd.DataFrame, path: Any) -> None:
    frame.to_csv(path, index=False, float_format="%.12f", lineterminator="\n")


