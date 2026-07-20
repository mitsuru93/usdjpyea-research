#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def load_base(path: Path):
    spec = importlib.util.spec_from_file_location("eurusd_v2_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(json_safe(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses > 0:
        return gains / losses
    return math.inf if gains > 0 else 0.0


def stress_metrics(trades: pd.DataFrame, multiplier: float, slippage: float, months: list[str]) -> dict[str, Any]:
    if trades.empty:
        return {
            "trades": 0,
            "avg_net_pips": 0.0,
            "total_net_pips": 0.0,
            "profit_factor": 0.0,
            "positive_months": 0,
            "total_excluding_best_two_days": 0.0,
            "max_drawdown_pips": 0.0,
        }
    net = trades.gross_pips - trades.spread_basis_pips * multiplier - 2.0 * slippage
    working = trades[["entry_ts", "entry_date_utc", "entry_month"]].copy()
    working["net"] = net.to_numpy()
    monthly = working.groupby("entry_month").net.sum().reindex(months, fill_value=0.0)
    daily = working.groupby("entry_date_utc").net.sum().sort_values(ascending=False)
    equity = working.sort_values("entry_ts").net.cumsum()
    drawdown = equity - equity.cummax()
    return {
        "trades": int(len(working)),
        "avg_net_pips": float(working.net.mean()),
        "total_net_pips": float(working.net.sum()),
        "profit_factor": profit_factor(working.net),
        "positive_months": int((monthly > 0).sum()),
        "total_excluding_best_two_days": float(working.net.sum() - daily.head(2).sum()),
        "max_drawdown_pips": float(drawdown.min()),
    }


def scenario_key(multiplier: float, slippage: float) -> tuple[float, float]:
    return round(float(multiplier), 10), round(float(slippage), 10)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", required=True, type=Path)
    parser.add_argument("--candidate-protocol", required=True, type=Path)
    parser.add_argument("--stress-protocol", required=True, type=Path)
    parser.add_argument("--base-runner", default=Path("tools/run_eurusd_h1_h2_v2_validation.py"), type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    stress = json.loads(args.stress_protocol.read_text(encoding="utf-8"))
    candidate_protocol = json.loads(args.candidate_protocol.read_text(encoding="utf-8"))
    if stress["status"] != "preregistered_before_stress_execution":
        raise RuntimeError("stress protocol is not preregistered")
    base = load_base(args.base_runner)
    bars = base.load_bars(args.bars)
    if len(bars) != 6112:
        raise RuntimeError(f"unexpected annual H1 rows: {len(bars)}")
    definitions = {
        item["id"]: item
        for item in candidate_protocol["diagnostic_baselines"] + candidate_protocol["v2_candidates"]
    }
    candidate_roles = {item["id"]: item["role"] for item in stress["candidates"]}
    if set(candidate_roles) - set(definitions):
        raise RuntimeError("stress candidate is absent from the authoritative candidate protocol")

    h1_start = pd.Timestamp(stress["periods"]["development_H1"][0])
    h1_end = pd.Timestamp(stress["periods"]["development_H1"][1])
    h2_start = pd.Timestamp(stress["periods"]["fixed_validation_H2"][0])
    h2_end = pd.Timestamp(stress["periods"]["fixed_validation_H2"][1])
    h1_months = [f"2024-{month:02d}" for month in range(1, 7)]
    h2_months = [f"2024-{month:02d}" for month in range(7, 13)]
    full_months = [f"2024-{month:02d}" for month in range(1, 13)]

    period_trades: dict[tuple[str, str], pd.DataFrame] = {}
    for candidate_id in candidate_roles:
        definition = definitions[candidate_id]
        h1 = base.trades(bars, definition, candidate_protocol, h1_start, h1_end)
        h2 = base.trades(bars, definition, candidate_protocol, h2_start, h2_end)
        full = pd.concat([h1, h2], ignore_index=True)
        if h1.empty or h2.empty:
            raise RuntimeError(f"candidate lacks trades in a registered period: {candidate_id}")
        period_trades[(candidate_id, "H1")] = h1
        period_trades[(candidate_id, "H2")] = h2
        period_trades[(candidate_id, "FULL_2024")] = full

    rows: list[dict[str, Any]] = []
    grid = stress["cost_grid"]
    for candidate_id, role in candidate_roles.items():
        for period_name, months in [("H1", h1_months), ("H2", h2_months), ("FULL_2024", full_months)]:
            trades = period_trades[(candidate_id, period_name)]
            for multiplier in grid["spread_multipliers"]:
                for slippage in grid["slippage_pips_per_side"]:
                    metrics = stress_metrics(trades, float(multiplier), float(slippage), months)
                    rows.append(
                        {
                            "candidate_id": candidate_id,
                            "role": role,
                            "period": period_name,
                            "spread_multiplier": float(multiplier),
                            "slippage_pips_per_side": float(slippage),
                            **metrics,
                        }
                    )
    grid_frame = pd.DataFrame(rows)

    scenario_rows: list[dict[str, Any]] = []
    for scenario_name, setting in stress["registered_scenarios"].items():
        key = scenario_key(setting["spread_multiplier"], setting["slippage_pips_per_side"])
        subset = grid_frame.loc[
            (grid_frame.spread_multiplier.round(10) == key[0])
            & (grid_frame.slippage_pips_per_side.round(10) == key[1])
        ].copy()
        subset.insert(0, "scenario", scenario_name)
        scenario_rows.extend(subset.to_dict("records"))
    scenarios = pd.DataFrame(scenario_rows)

    primary_id = next(candidate_id for candidate_id, role in candidate_roles.items() if role == "production_primary")
    lookup = {
        (row.candidate_id, row.period, row.scenario): row
        for row in scenarios.itertuples(index=False)
    }
    default_h2 = lookup[(primary_id, "H2", "default")]
    moderate_h2 = lookup[(primary_id, "H2", "moderate")]
    severe_full = lookup[(primary_id, "FULL_2024", "severe")]
    gate = stress["production_primary_acceptance"]
    checks = {
        "fixed_H2_default_total_net_pips": float(default_h2.total_net_pips) > float(gate["fixed_H2_default_total_net_pips_gt"]),
        "fixed_H2_default_profit_factor": float(default_h2.profit_factor) >= float(gate["fixed_H2_default_profit_factor_gte"]),
        "fixed_H2_moderate_total_net_pips": float(moderate_h2.total_net_pips) > float(gate["fixed_H2_moderate_total_net_pips_gt"]),
        "fixed_H2_moderate_profit_factor": float(moderate_h2.profit_factor) >= float(gate["fixed_H2_moderate_profit_factor_gte"]),
        "full_2024_severe_total_net_pips": float(severe_full.total_net_pips) > float(gate["full_2024_severe_total_net_pips_gt"]),
        "full_2024_severe_profit_factor": float(severe_full.profit_factor) >= float(gate["full_2024_severe_profit_factor_gte"]),
    }
    primary_pass = all(checks.values())

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    grid_frame.to_csv(out / "stress_grid.csv", index=False)
    scenarios.to_csv(out / "registered_scenarios.csv", index=False)
    result = {
        "schema_version": "eurusd_fv2_cost_execution_stress_result_v1",
        "production_primary_candidate_id": primary_id,
        "production_primary_pass": primary_pass,
        "acceptance_checks": checks,
        "default_H2": default_h2._asdict(),
        "moderate_H2": moderate_h2._asdict(),
        "severe_FULL_2024": severe_full._asdict(),
        "candidate_rules_changed": False,
        "new_filter_selected": False,
        "operational_tests_deferred_to_core": stress["operational_tests_deferred_to_core"],
        "optional_final_2025_policy": stress["optional_final_2025_policy"],
    }
    write_json(out / "stress_result.json", result)
    source_receipt = {
        "schema_version": "eurusd_fv2_cost_execution_stress_source_receipt_v1",
        "bars_file": str(args.bars),
        "bars_file_sha256": f"sha256:{sha256_file(args.bars)}",
        "bars_frame_content_sha256": f"sha256:{base.frame_hash(bars)}",
        "bars_rows": int(len(bars)),
        "candidate_protocol_sha256": f"sha256:{sha256_file(args.candidate_protocol)}",
        "stress_protocol_sha256": f"sha256:{sha256_file(args.stress_protocol)}",
        "authoritative_candidate_lock_sha256": stress["authoritative_candidate_lock_sha256"],
    }
    write_json(out / "source_receipt.json", source_receipt)

    selected = scenarios.loc[
        (scenarios.candidate_id == primary_id)
        & scenarios.scenario.isin(["default", "moderate", "severe"])
        & scenarios.period.isin(["H2", "FULL_2024"])
    ]
    lines = [
        "# EURUSD F v2 cost and execution stress v1",
        "",
        f"Production primary: `{primary_id}`",
        f"Registered acceptance: **{primary_pass}**",
        "",
        selected.to_markdown(index=False),
        "",
        "No signal, exit, entry filter or candidate role was changed from this stress result.",
        "Operational fault-injection and simulated state reinitialization are deferred to the Core production-EA implementation. The Rakuten account is not disconnected for a restart test.",
    ]
    (out / "analysis_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    required = stress["required_outputs"]
    missing = [name for name in required if not (out / name).exists() and name != "SHA256SUMS"]
    if missing:
        raise RuntimeError(f"missing required outputs: {missing}")
    checksum_lines = []
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            checksum_lines.append(f"{sha256_file(path)}  {path.name}")
    (out / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps(json_safe(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
