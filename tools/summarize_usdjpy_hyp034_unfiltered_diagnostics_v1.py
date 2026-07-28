#!/usr/bin/env python3
"""Complete preregistered diagnostics after the binding mechanism stop.

This script does not select, filter, freeze, rescue, or authorize a candidate.
It evaluates only the unchanged completed-M15-reclaim population already used by
the binding USDJPY-HYP-034 decision. 2020-2022 and 2025 are forbidden.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from evaluate_usdjpy_previous_day_extreme_sweep_v1 import load_baseline, portfolio_attribution
from usdjpy_hyp034_metrics_v1 import (
    bootstrap_metrics,
    concentration_metrics,
    cost_stress,
    deterministic_csv,
    package_manifest,
    trade_metrics,
    write_json,
)
from usdjpy_hyp034_study_v1 import full_equity_replay

DIAGNOSTIC_ID = "UNFILTERED_COMPLETED_M15_RECLAIM_DIAGNOSTIC_ONLY"


def finite(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(item) for item in value]
    if isinstance(value, float):
        if np.isnan(value):
            return None
        if np.isinf(value):
            return "INF" if value > 0 else "-INF"
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path-metrics", type=Path, required=True)
    parser.add_argument("--final-result", type=Path, required=True)
    parser.add_argument("--baseline-trades", type=Path, required=True)
    parser.add_argument("--raw-2023", type=Path, required=True)
    parser.add_argument("--raw-2024", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    scientific = json.loads(args.final_result.read_text(encoding="utf-8"))
    assert scientific["hypothesis_id"] == "USDJPY-HYP-034"
    assert scientific["decision"] == "NO_PORTABLE_REJECTION_MECHANISM"
    assert scientific["selected_candidate"] is None
    assert scientific["historical_validation_authorized"] is False
    assert scientific["protected_2020_2022_accessed"] is False
    assert scientific["protected_2025_accessed"] is False

    trades = pd.read_csv(args.path_metrics)
    for column in ("entry_decision_utc", "entry_utc", "exit_utc"):
        trades[column] = pd.to_datetime(trades[column], utc=True)
    if len(trades) != scientific["unfiltered_candidate_metrics"]["event_count"]:
        raise ValueError("path ledger count differs from binding final result")
    if not trades.entry_utc.dt.year.isin([2023, 2024]).all() or not trades.exit_utc.dt.year.isin([2023, 2024]).all():
        raise ValueError("protected or non-development date in diagnostic trade ledger")

    baseline = load_baseline(args.baseline_trades)
    full_equity, full_equity_daily = full_equity_replay(
        [args.raw_2023, args.raw_2024],
        baseline,
        {DIAGNOSTIC_ID: trades},
    )
    portfolio = portfolio_attribution(baseline, DIAGNOSTIC_ID, trades, full_equity)
    costs = cost_stress(trades)
    concentration = concentration_metrics(trades)
    bootstrap = bootstrap_metrics(trades)
    metrics = trade_metrics(trades)
    monthly = trades.groupby("month", sort=True).pl_jpy.sum()
    fold = trades.groupby("fold", sort=True).pl_jpy.sum()

    diagnostic_gates = [
        {"gate": "candidate_net_positive", "value": metrics["net_jpy"], "threshold": ">0", "pass": metrics["net_jpy"] > 0},
        {"gate": "profit_factor_min_1_10", "value": metrics["profit_factor"], "threshold": ">=1.10", "pass": metrics["profit_factor"] >= 1.10},
        {"gate": "positive_folds_min_3", "value": int((fold > 0).sum()), "threshold": ">=3/4", "pass": int((fold > 0).sum()) >= 3},
        {"gate": "positive_months_min_16", "value": int((monthly > 0).sum()), "threshold": ">=16/24", "pass": int((monthly > 0).sum()) >= 16},
        {"gate": "best_event_removed_net_positive", "value": concentration["best_event_removed_net_jpy"], "threshold": ">0", "pass": concentration["best_event_removed_net_jpy"] > 0},
        {"gate": "top3_removed_net_positive", "value": concentration["top3_removed_net_jpy"], "threshold": ">0", "pass": concentration["top3_removed_net_jpy"] > 0},
        {"gate": "top5_removed_net_positive", "value": concentration["top5_removed_net_jpy"], "threshold": ">0", "pass": concentration["top5_removed_net_jpy"] > 0},
        {"gate": "event_bootstrap_lower95_positive", "value": bootstrap["event"]["lower95_jpy"], "threshold": ">0", "pass": bootstrap["event"]["lower95_jpy"] > 0},
        {"gate": "date_session_bootstrap_lower95_positive", "value": bootstrap["date_session"]["lower95_jpy"], "threshold": ">0", "pass": bootstrap["date_session"]["lower95_jpy"] > 0},
        {"gate": "probability_nonpositive_max_5pct", "value": bootstrap["event"]["probability_nonpositive"], "threshold": "<=0.05", "pass": bootstrap["event"]["probability_nonpositive"] <= 0.05},
        {"gate": "spread_plus_0_5_positive", "value": float(costs.loc[costs.stress.eq("SPREAD_PLUS_0_5_PIP"), "net_jpy"].iloc[0]), "threshold": ">0", "pass": float(costs.loc[costs.stress.eq("SPREAD_PLUS_0_5_PIP"), "net_jpy"].iloc[0]) > 0},
        {"gate": "spread_plus_1_0_positive", "value": float(costs.loc[costs.stress.eq("SPREAD_PLUS_1_0_PIP"), "net_jpy"].iloc[0]), "threshold": ">0", "pass": float(costs.loc[costs.stress.eq("SPREAD_PLUS_1_0_PIP"), "net_jpy"].iloc[0]) > 0},
        {"gate": "entry_delay_5s_positive", "value": float(costs.loc[costs.stress.eq("ENTRY_DELAY_5S"), "net_jpy"].iloc[0]), "threshold": ">0", "pass": float(costs.loc[costs.stress.eq("ENTRY_DELAY_5S"), "net_jpy"].iloc[0]) > 0},
        {"gate": "negative_day_contribution_positive", "value": portfolio["B02_F05_negative_day_contribution_jpy"], "threshold": ">0", "pass": portfolio["B02_F05_negative_day_contribution_jpy"] > 0},
        {"gate": "combined_net_above_baseline", "value": portfolio["combined_net_jpy"] - portfolio["baseline_net_jpy"], "threshold": ">0", "pass": portfolio["combined_net_jpy"] > portfolio["baseline_net_jpy"]},
        {"gate": "combined_realized_dd_nonworse", "value": portfolio["combined_realized_mdd_jpy"] - portfolio["baseline_realized_mdd_jpy"], "threshold": "<=0", "pass": portfolio["combined_realized_mdd_jpy"] <= portfolio["baseline_realized_mdd_jpy"] + 1e-6},
        {"gate": "combined_full_equity_dd_nonworse", "value": portfolio["combined_full_equity_mdd_jpy"] - portfolio["baseline_full_equity_mdd_jpy"], "threshold": "<=0", "pass": portfolio["combined_full_equity_mdd_jpy"] <= portfolio["baseline_full_equity_mdd_jpy"] + 1e-6},
        {"gate": "minimum_equity_nonworse", "value": portfolio["combined_full_equity_minimum_jpy"] - portfolio["baseline_full_equity_minimum_jpy"], "threshold": ">=0", "pass": portfolio["combined_full_equity_minimum_jpy"] >= portfolio["baseline_full_equity_minimum_jpy"] - 1e-6},
    ]

    summary = {
        "schema_version": "usdjpy_hyp034_unfiltered_diagnostics_v1",
        "hypothesis_id": "USDJPY-HYP-034",
        "family_id": "S_PREVIOUS_DAY_EXTREME_SWEEP_REJECTION",
        "diagnostic_population_id": DIAGNOSTIC_ID,
        "scientific_decision_preserved": "NO_PORTABLE_REJECTION_MECHANISM",
        "candidate_created": False,
        "candidate_freeze_authorized": False,
        "historical_validation_authorized": False,
        "core_mt4_authorized": False,
        "external_2025_authorized": False,
        "production_authorized": False,
        "live_authorized": False,
        "protected_2020_2022_accessed": False,
        "protected_2025_accessed": False,
        "trade_metrics": metrics,
        "positive_folds": int((fold > 0).sum()),
        "fold_net_jpy": fold.to_dict(),
        "positive_months": int((monthly > 0).sum()),
        "negative_months": int((monthly < 0).sum()),
        "concentration": concentration,
        "bootstrap": bootstrap,
        "cost_stress": costs.to_dict(orient="records"),
        "portfolio": portfolio,
        "binding_failure_count_in_diagnostic_matrix": int(sum(not bool(row["pass"]) for row in diagnostic_gates)),
        "exact_next_action": "Close HYP-034 without candidate freeze, historical validation, Core/MT4, or 2025 access."
    }

    deterministic_csv(costs, args.output / "cost_stress_unfiltered.csv")
    deterministic_csv(pd.DataFrame([{"method": method, **values} for method, values in bootstrap.items()]), args.output / "bootstrap_unfiltered.csv")
    deterministic_csv(pd.DataFrame([concentration]), args.output / "concentration_unfiltered.csv")
    deterministic_csv(pd.DataFrame([portfolio]), args.output / "portfolio_attribution_unfiltered.csv")
    deterministic_csv(pd.DataFrame(diagnostic_gates), args.output / "diagnostic_gate_matrix.csv")
    deterministic_csv(full_equity_daily, args.output / "full_equity_daily_unfiltered.csv.gz", gzip=True)
    write_json(finite(full_equity), args.output / "full_equity_unfiltered.json")
    write_json(finite(summary), args.output / "unfiltered_diagnostics.json")
    manifest = package_manifest(args.output, {"PACKAGE_MANIFEST.json", "PACKAGE_SHA256SUMS"})
    write_json(manifest, args.output / "PACKAGE_MANIFEST.json")
    (args.output / "PACKAGE_SHA256SUMS").write_text(
        "\n".join(f"{row['sha256']}  {row['path']}" for row in manifest["files"]) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(finite(summary), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
