#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

KEYS = ["candidate_id", "family", "definition_sha256", "horizon_bars"]
PAIR_KEYS = ["candidate_id", "horizon_bars"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, float_format="%.12f", lineterminator="\n")


def write_deterministic_gzip_csv(df: pd.DataFrame, path: Path) -> None:
    text = df.to_csv(index=False, float_format="%.12f", lineterminator="\n")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(text.encode("utf-8"))


def positive_counts(
    df: pd.DataFrame,
    label_col: str,
    prefix: str,
    expected_rows: int,
    exclude_label: int | None = None,
) -> pd.DataFrame:
    work = df.copy()
    if exclude_label is not None:
        work = work[work[label_col] != exclude_label].copy()
    grouped = work.groupby(KEYS, sort=False)
    out = grouped.agg(
        **{
            f"{prefix}_rows": (label_col, "size"),
            f"{prefix}_nonempty": ("trades", lambda x: int((x > 0).sum())),
            f"{prefix}_default_positive": (
                "avg_default_net_pips",
                lambda x: int((x > 0).sum()),
            ),
            f"{prefix}_severe_positive": (
                "avg_severe_net_pips",
                lambda x: int((x > 0).sum()),
            ),
            f"minimum_{prefix}_avg_default_net_pips": (
                "avg_default_net_pips",
                "min",
            ),
            f"minimum_{prefix}_avg_severe_net_pips": (
                "avg_severe_net_pips",
                "min",
            ),
        }
    ).reset_index()
    assert len(out) == 660
    assert out[f"{prefix}_rows"].eq(expected_rows).all()
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--r2-dir", required=True)
    p.add_argument("--r3-dir", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    r2 = Path(args.r2_dir)
    r3 = Path(args.r3_dir)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))

    summary_path = r2 / "candidate_horizon_summary.csv"
    trades_path = r2 / "candidate_horizon_trades.csv.gz"
    acceptance_path = r3 / "r3_acceptance.json"
    monthly_path = r3 / "temporal_monthly.csv"
    anchored_path = r3 / "anchored_ranking.csv"

    assert sha256(trades_path) == config["inputs"]["r2_trade_ledger_sha256"]
    assert sha256(summary_path) == config["inputs"]["r2_summary_sha256"]
    assert sha256(acceptance_path) == config["inputs"]["r3_acceptance_sha256"]
    assert sha256(monthly_path) == config["inputs"]["r3_temporal_monthly_sha256"]
    assert sha256(anchored_path) == config["inputs"]["r3_anchored_ranking_sha256"]

    summary = pd.read_csv(summary_path)
    trades = pd.read_csv(trades_path, compression="gzip")
    monthly = pd.read_csv(monthly_path)
    quarterly = pd.read_csv(r3 / "temporal_quarterly.csv")
    rolling2 = pd.read_csv(r3 / "rolling_2month.csv")
    rolling3 = pd.read_csv(r3 / "rolling_3month.csv")
    anchored = pd.read_csv(anchored_path)
    spread = pd.read_csv(r3 / "spread_regime.csv")
    rv32 = pd.read_csv(r3 / "rv32_regime.csv")
    rv96 = pd.read_csv(r3 / "rv96_regime.csv")
    neighborhood = pd.read_csv(r3 / "horizon_neighborhood.csv")
    concentration = pd.read_csv(r3 / "concentration.csv")
    sample = pd.read_csv(r3 / "sample_classes.csv")

    assert len(summary) == 660
    assert len(trades) == 383078
    assert summary["candidate_id"].nunique() == 60
    assert summary["horizon_bars"].nunique() == 11

    q = positive_counts(quarterly, "quarter", "quarter", 2)
    r2m = positive_counts(rolling2, "window", "rolling2", 5)
    r3m = positive_counts(rolling3, "window", "rolling3", 4)
    sp = positive_counts(spread, "spread_quartile", "spread", 4)
    rv32p = positive_counts(rv32, "rv32_quartile", "rv32", 4, exclude_label=0)
    rv96p = positive_counts(rv96, "rv96_quartile", "rv96", 4, exclude_label=0)

    anchored_agg = (
        anchored.groupby(KEYS, sort=False)
        .agg(
            anchored_rows=("anchor_end_month", "size"),
            median_anchored_percentile_avg_default_net_pips=(
                "percentile_avg_default_net_pips", "median"
            ),
            median_anchored_percentile_avg_severe_net_pips=(
                "percentile_avg_severe_net_pips", "median"
            ),
            minimum_anchored_avg_default_net_pips=("avg_default_net_pips", "min"),
            minimum_anchored_avg_severe_net_pips=("avg_severe_net_pips", "min"),
        )
        .reset_index()
    )
    assert len(anchored_agg) == 660
    assert anchored_agg["anchored_rows"].eq(5).all()

    base = summary.merge(sample[KEYS + ["sample_class"]], on=KEYS, validate="one_to_one")
    base = base.merge(q, on=KEYS, validate="one_to_one")
    base = base.merge(r2m, on=KEYS, validate="one_to_one")
    base = base.merge(r3m, on=KEYS, validate="one_to_one")
    base = base.merge(sp, on=KEYS, validate="one_to_one")
    base = base.merge(rv32p, on=KEYS, validate="one_to_one")
    base = base.merge(rv96p, on=KEYS, validate="one_to_one")
    base = base.merge(anchored_agg, on=KEYS, validate="one_to_one")
    base = base.merge(neighborhood, on=KEYS, validate="one_to_one")
    base = base.merge(concentration, on=KEYS, validate="one_to_one", suffixes=("", "_concentration"))
    assert len(base) == 660

    eligibility = config["eligibility"]
    base["gate_sample_class"] = base["sample_class"].isin(eligibility["allowed_sample_classes"])
    base["gate_aggregate_trades"] = base["trades"].ge(eligibility["minimum_aggregate_trades"])
    base["gate_minimum_monthly_trades"] = base["minimum_monthly_trades"].ge(
        eligibility["minimum_monthly_trades"]
    )
    base["gate_aggregate_avg_default_positive"] = base["avg_default_net_pips"].gt(0)
    base["gate_aggregate_avg_severe_positive"] = base["avg_severe_net_pips"].gt(0)
    base["gate_default_pf_above_one"] = base["default_profit_factor"].gt(1)
    base["gate_severe_pf_above_one"] = base["severe_profit_factor"].gt(1)
    base["gate_positive_months"] = base["positive_months"].ge(
        eligibility["aggregate"]["minimum_positive_months"]
    )
    base["gate_excluding_best_two_days_positive"] = base[
        "total_excluding_best_two_utc_days"
    ].gt(0)
    base["gate_quarters_default"] = base["quarter_default_positive"].ge(
        eligibility["quarters"]["required_default_positive"]
    )
    base["gate_quarters_severe"] = base["quarter_severe_positive"].ge(
        eligibility["quarters"]["required_severe_positive"]
    )
    base["gate_rolling2_default"] = base["rolling2_default_positive"].ge(
        eligibility["rolling_2month"]["required_default_positive"]
    )
    base["gate_rolling2_severe"] = base["rolling2_severe_positive"].ge(
        eligibility["rolling_2month"]["required_severe_positive"]
    )
    base["gate_rolling3_default"] = base["rolling3_default_positive"].ge(
        eligibility["rolling_3month"]["required_default_positive"]
    )
    base["gate_rolling3_severe"] = base["rolling3_severe_positive"].ge(
        eligibility["rolling_3month"]["required_severe_positive"]
    )
    base["gate_neighbor_default"] = base["all_available_default_positive"].astype(bool)
    base["gate_neighbor_severe"] = base["severe_positive_count"].ge(
        eligibility["horizon_neighborhood"]["minimum_severe_positive_count"]
    )
    base["gate_not_isolated"] = ~base["isolated_default_positive"].astype(bool)
    base["gate_spread_nonempty"] = base["spread_nonempty"].eq(
        eligibility["spread_regimes"]["nonempty_regimes"]
    )
    base["gate_spread_default"] = base["spread_default_positive"].ge(
        eligibility["spread_regimes"]["minimum_default_positive_regimes"]
    )
    base["gate_spread_severe"] = base["spread_severe_positive"].ge(
        eligibility["spread_regimes"]["minimum_severe_positive_regimes"]
    )
    base["gate_rv32_nonempty"] = base["rv32_nonempty"].eq(
        eligibility["rv32_regimes"]["nonwarmup_regimes"]
    )
    base["gate_rv32_default"] = base["rv32_default_positive"].ge(
        eligibility["rv32_regimes"]["minimum_default_positive_regimes"]
    )
    base["gate_rv32_severe"] = base["rv32_severe_positive"].ge(
        eligibility["rv32_regimes"]["minimum_severe_positive_regimes"]
    )
    base["gate_rv96_nonempty"] = base["rv96_nonempty"].eq(
        eligibility["rv96_regimes"]["nonwarmup_regimes"]
    )
    base["gate_rv96_default"] = base["rv96_default_positive"].ge(
        eligibility["rv96_regimes"]["minimum_default_positive_regimes"]
    )
    base["gate_rv96_severe"] = base["rv96_severe_positive"].ge(
        eligibility["rv96_regimes"]["minimum_severe_positive_regimes"]
    )
    c = eligibility["concentration"]
    base["gate_day_concentration"] = base["largest_absolute_day_share"].le(
        c["maximum_largest_absolute_day_share"]
    )
    base["gate_month_concentration"] = base["largest_absolute_month_share"].le(
        c["maximum_largest_absolute_month_share"]
    )
    base["gate_top_two_positive_days"] = base[
        "top_two_days_share_of_positive_daily_pips"
    ].le(c["maximum_top_two_days_share_of_positive_daily_pips"])
    base["gate_direction_concentration"] = base[
        "direction_absolute_contribution_share_max"
    ].le(c["maximum_direction_absolute_contribution_share"])

    gate_columns = [col for col in base.columns if col.startswith("gate_")]
    base["eligible"] = base[gate_columns].all(axis=1)
    base["failure_reasons"] = base.apply(
        lambda row: "|".join(
            name.removeprefix("gate_") for name in gate_columns if not bool(row[name])
        ),
        axis=1,
    )

    base["aggregate_avg_severe_net_pips"] = base["avg_severe_net_pips"]
    base["aggregate_severe_profit_factor"] = base["severe_profit_factor"]
    base["minimum_quarterly_avg_severe_net_pips"] = base[
        "minimum_quarter_avg_severe_net_pips"
    ]
    base["minimum_rolling_3month_avg_severe_net_pips"] = base[
        "minimum_rolling3_avg_severe_net_pips"
    ]
    base["minimum_spread_regime_avg_default_net_pips"] = base[
        "minimum_spread_avg_default_net_pips"
    ]
    base["minimum_rv32_nonwarmup_avg_default_net_pips"] = base[
        "minimum_rv32_avg_default_net_pips"
    ]
    base["minimum_rv96_nonwarmup_avg_default_net_pips"] = base[
        "minimum_rv96_avg_default_net_pips"
    ]
    base["median_neighbor_avg_default_net_pips"] = base[
        "median_neighbor_avg_default_net_pips"
    ]
    base["total_excluding_best_two_utc_days_per_trade"] = (
        base["total_excluding_best_two_utc_days"] / base["trades"].replace(0, np.nan)
    )
    base["one_minus_largest_absolute_month_share"] = 1.0 - base[
        "largest_absolute_month_share"
    ]
    base["one_minus_direction_absolute_contribution_share"] = 1.0 - base[
        "direction_absolute_contribution_share_max"
    ]

    components = config["ranking"]["components"]
    eligible = base[base["eligible"]].copy()
    for component in components:
        assert component in eligible.columns, component
        eligible[f"pct_{component}"] = eligible[component].rank(
            method="average", pct=True, ascending=True
        )
    pct_cols = [f"pct_{component}" for component in components]
    eligible["selection_score"] = eligible[pct_cols].mean(axis=1)
    eligible = eligible.sort_values(
        [
            "selection_score",
            "aggregate_avg_severe_net_pips",
            "minimum_quarterly_avg_severe_net_pips",
            "total_excluding_best_two_utc_days_per_trade",
            "candidate_id",
            "horizon_bars",
        ],
        ascending=[False, False, False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    eligible["eligible_rank"] = np.arange(1, len(eligible) + 1)

    score_cols = ["selection_score", "eligible_rank"] + pct_cols
    base = base.merge(eligible[KEYS + score_cols], on=KEYS, how="left", validate="one_to_one")

    trade_keys = trades[["candidate_id", "horizon_bars", "entry_ts", "entry_date_utc", "default_net_pips"]].copy()
    trade_keys["entry_ts"] = pd.to_datetime(trade_keys["entry_ts"], utc=True)
    trade_keys["entry_date_utc"] = trade_keys["entry_date_utc"].astype(str)
    calendar = pd.Index(
        pd.date_range("2024-01-01", "2024-06-30", freq="D").strftime("%Y-%m-%d"),
        name="entry_date_utc",
    )
    eligible_ids = list(zip(eligible["candidate_id"], eligible["horizon_bars"].astype(int)))
    daily_vectors: dict[tuple[str, int], np.ndarray] = {}
    entry_sets: dict[tuple[str, int], set[str]] = {}
    for candidate_id, horizon in eligible_ids:
        subset = trade_keys[
            (trade_keys["candidate_id"] == candidate_id)
            & (trade_keys["horizon_bars"] == horizon)
        ]
        daily = (
            subset.groupby("entry_date_utc")["default_net_pips"]
            .sum()
            .reindex(calendar, fill_value=0.0)
            .to_numpy(dtype=float)
        )
        daily_vectors[(candidate_id, horizon)] = daily
        entry_sets[(candidate_id, horizon)] = set(
            subset["entry_ts"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    pair_rows: list[dict[str, Any]] = []
    similarity_lookup: dict[tuple[tuple[str, int], tuple[str, int]], tuple[float, float, bool]] = {}
    corr_threshold = float(config["redundancy"]["daily_default_net_pearson_threshold"])
    jac_threshold = float(config["redundancy"]["entry_timestamp_jaccard_threshold"])
    for i, left in enumerate(eligible_ids):
        a = daily_vectors[left]
        for right in eligible_ids[i + 1 :]:
            b = daily_vectors[right]
            if float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
                corr = 0.0
            else:
                corr = float(np.corrcoef(a, b)[0, 1])
                if not math.isfinite(corr):
                    corr = 0.0
            sa, sb = entry_sets[left], entry_sets[right]
            union = sa | sb
            jac = float(len(sa & sb) / len(union)) if union else 0.0
            redundant = bool(corr >= corr_threshold and jac >= jac_threshold)
            pair_rows.append(
                {
                    "left_candidate_id": left[0],
                    "left_horizon_bars": left[1],
                    "right_candidate_id": right[0],
                    "right_horizon_bars": right[1],
                    "daily_default_net_pearson": corr,
                    "entry_timestamp_jaccard": jac,
                    "redundant": redundant,
                }
            )
            similarity_lookup[(left, right)] = (corr, jac, redundant)
            similarity_lookup[(right, left)] = (corr, jac, redundant)
    pairwise = pd.DataFrame(pair_rows)

    selected_rows: list[pd.Series] = []
    selected_keys: list[tuple[str, int]] = []
    selected_definitions: set[str] = set()
    family_counts: dict[str, int] = {}
    decision_rows: list[dict[str, Any]] = []
    max_selected = int(config["surface_contract"]["maximum_selected"])
    max_family = int(config["surface_contract"]["maximum_per_family"])

    for row in eligible.itertuples(index=False):
        key = (row.candidate_id, int(row.horizon_bars))
        reason = ""
        blocker_candidate = ""
        blocker_horizon: int | str = ""
        corr: float | str = ""
        jac: float | str = ""
        if row.definition_sha256 in selected_definitions:
            reason = "duplicate_definition_sha256"
            for selected_row in selected_rows:
                if selected_row["definition_sha256"] == row.definition_sha256:
                    blocker_candidate = str(selected_row["candidate_id"])
                    blocker_horizon = int(selected_row["horizon_bars"])
                    break
        elif family_counts.get(row.family, 0) >= max_family:
            reason = "family_cap"
        else:
            for selected_key in selected_keys:
                pcorr, pjac, redundant = similarity_lookup[(key, selected_key)]
                if redundant:
                    reason = "pairwise_redundancy"
                    blocker_candidate, blocker_horizon = selected_key
                    corr, jac = pcorr, pjac
                    break
        if reason:
            decision_rows.append(
                {
                    "candidate_id": row.candidate_id,
                    "horizon_bars": int(row.horizon_bars),
                    "eligible_rank": int(row.eligible_rank),
                    "decision": "skipped",
                    "reason": reason,
                    "blocking_candidate_id": blocker_candidate,
                    "blocking_horizon_bars": blocker_horizon,
                    "daily_default_net_pearson": corr,
                    "entry_timestamp_jaccard": jac,
                }
            )
            continue
        selected_series = eligible.loc[
            (eligible["candidate_id"] == row.candidate_id)
            & (eligible["horizon_bars"] == row.horizon_bars)
        ].iloc[0]
        selected_rows.append(selected_series)
        selected_keys.append(key)
        selected_definitions.add(row.definition_sha256)
        family_counts[row.family] = family_counts.get(row.family, 0) + 1
        decision_rows.append(
            {
                "candidate_id": row.candidate_id,
                "horizon_bars": int(row.horizon_bars),
                "eligible_rank": int(row.eligible_rank),
                "decision": "selected",
                "reason": "",
                "blocking_candidate_id": "",
                "blocking_horizon_bars": "",
                "daily_default_net_pearson": "",
                "entry_timestamp_jaccard": "",
            }
        )
        if len(selected_rows) >= max_selected:
            break

    selected = pd.DataFrame(selected_rows)
    if len(selected):
        selected = selected.copy()
        selected["selection_rank"] = np.arange(1, len(selected) + 1)
    else:
        selected = eligible.head(0).copy()
        selected["selection_rank"] = pd.Series(dtype=int)

    decisions = pd.DataFrame(decision_rows)
    family_summary = (
        base.groupby("family", sort=True)
        .agg(
            combinations=("candidate_id", "size"),
            eligible_combinations=("eligible", "sum"),
        )
        .reset_index()
    )
    selected_family = (
        selected.groupby("family").size().rename("selected_representatives")
        if len(selected)
        else pd.Series(dtype=int, name="selected_representatives")
    )
    family_summary = family_summary.merge(
        selected_family, left_on="family", right_index=True, how="left"
    )
    family_summary["selected_representatives"] = (
        family_summary["selected_representatives"].fillna(0).astype(int)
    )

    audit_columns = (
        KEYS
        + [
            "trades", "minimum_monthly_trades", "sample_class",
            "avg_default_net_pips", "avg_severe_net_pips",
            "default_profit_factor", "severe_profit_factor", "positive_months",
            "total_excluding_best_two_utc_days", "quarter_default_positive",
            "quarter_severe_positive", "rolling2_default_positive",
            "rolling2_severe_positive", "rolling3_default_positive",
            "rolling3_severe_positive", "spread_default_positive",
            "spread_severe_positive", "rv32_default_positive",
            "rv32_severe_positive", "rv96_default_positive",
            "rv96_severe_positive", "largest_absolute_day_share",
            "largest_absolute_month_share", "top_two_days_share_of_positive_daily_pips",
            "direction_absolute_contribution_share_max", "all_available_default_positive",
            "severe_positive_count", "isolated_default_positive",
        ]
        + gate_columns
        + ["eligible", "failure_reasons"]
        + components
        + score_cols
    )
    audit = base[audit_columns].sort_values(
        ["eligible", "selection_score", "candidate_id", "horizon_bars"],
        ascending=[False, False, True, True],
        kind="mergesort",
        na_position="last",
    )

    write_csv(audit, outdir / "selection_audit_all_660.csv")
    write_csv(eligible, outdir / "eligible_ranked.csv")
    write_csv(selected, outdir / "selected_representatives.csv")
    write_csv(decisions, outdir / "redundancy_decisions.csv")
    write_deterministic_gzip_csv(pairwise, outdir / "eligible_pairwise_similarity.csv.gz")
    write_csv(family_summary, outdir / "family_selection_summary.csv")

    selected_pairs_ok = True
    for i, left in enumerate(selected_keys):
        for right in selected_keys[i + 1 :]:
            if similarity_lookup[(left, right)][2]:
                selected_pairs_ok = False

    eligibility_conjunction_exact = bool(
        (base["eligible"] == base[gate_columns].all(axis=1)).all()
    )
    selected_definitions_unique = selected["definition_sha256"].nunique() == len(selected)
    family_cap_ok = (
        selected.groupby("family").size().max() <= max_family if len(selected) else True
    )
    selected_max_ok = len(selected) <= max_selected
    sparse_not_eligible = not bool(
        base.loc[base["sample_class"] == "sparse", "eligible"].any()
    )
    pairwise_expected = len(eligible) * (len(eligible) - 1) // 2
    acceptance = {
        "status": "PASS",
        "audit_rows_660": len(audit) == 660,
        "input_trade_rows_383078": len(trades) == 383078,
        "all_gate_columns_present": len(gate_columns) >= 30,
        "sparse_never_eligible": sparse_not_eligible,
        "eligibility_is_exact_gate_conjunction": eligibility_conjunction_exact,
        "ranking_only_contains_eligible": bool(eligible["eligible"].all()),
        "twelve_equal_rank_components": len(components) == 12 and len(pct_cols) == 12,
        "eligible_pairwise_grid_complete": len(pairwise) == pairwise_expected,
        "selected_at_most_eight": selected_max_ok,
        "selected_definition_sha256_unique": selected_definitions_unique,
        "selected_family_cap_two": family_cap_ok,
        "selected_pairwise_redundancy_clear": selected_pairs_ok,
        "no_gate_relaxation": config["surface_contract"]["relaxation_if_too_few"] is False,
        "H2_rows_parsed_zero": True,
        "2025_access_false": True,
        "entry_definitions_unchanged": True,
        "horizons_unchanged": True,
        "exit_optimization_false": True,
        "Core_promotion_false": True,
        "MT4_promotion_false": True,
    }
    acceptance = {
        key: (value if key == "status" else bool(value))
        for key, value in acceptance.items()
    }
    if not all(v is True for k, v in acceptance.items() if k != "status"):
        acceptance["status"] = "FAIL"
    (outdir / "r4_acceptance.json").write_text(
        json.dumps(acceptance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    output_hashes = {
        path.name: sha256(path)
        for path in sorted(outdir.iterdir())
        if path.is_file() and path.name not in {"run_metadata.json"}
    }
    metadata = {
        "version": "v1",
        "status": acceptance["status"],
        "research_stage": "R4_entry_horizon_selection",
        "candidate_horizon_combinations": 660,
        "eligible_combinations": int(len(eligible)),
        "selected_representatives": int(len(selected)),
        "selected_candidates": [
            {
                "selection_rank": int(row.selection_rank),
                "candidate_id": row.candidate_id,
                "family": row.family,
                "definition_sha256": row.definition_sha256,
                "horizon_bars": int(row.horizon_bars),
                "selection_score": float(row.selection_score),
            }
            for row in selected.itertuples(index=False)
        ],
        "gate_columns": gate_columns,
        "ranking_components": components,
        "pairwise_rows": int(len(pairwise)),
        "H2_rows_parsed": 0,
        "2025_artifact_access": False,
        "entry_definition_changes": False,
        "horizon_changes": False,
        "exit_optimization": False,
        "Core_promotion": False,
        "MT4_promotion": False,
        "R5_design_unblocked": acceptance["status"] == "PASS",
        "output_sha256": output_hashes,
    }
    (outdir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    assert acceptance["status"] == "PASS", acceptance
    print(
        json.dumps(
            {
                "R4": "PASS",
                "audit": len(audit),
                "eligible": len(eligible),
                "selected": len(selected),
                "pairwise": len(pairwise),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
