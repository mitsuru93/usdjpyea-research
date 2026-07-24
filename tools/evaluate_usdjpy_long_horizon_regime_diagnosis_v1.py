#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from usdjpy_fixed5_portability_lib_v1 import IDS, build_signals, build_trades, load23, load24

PERIODS = {
    "2023H1": (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2023-07-01", tz="UTC")),
    "2023H2": (pd.Timestamp("2023-07-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC")),
    "2024H1": (pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2024-07-01", tz="UTC")),
    "2024H2": (pd.Timestamp("2024-07-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
}
DIMENSIONS = [
    "direction_agreement",
    "persistent_signal_relation",
    "path_efficiency_5d_bin",
    "path_efficiency_20d_bin",
    "volatility_ratio_bin",
    "range_position_20d_bin",
]

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def profit_factor(values: pd.Series) -> float:
    gain = float(values[values > 0].sum())
    loss = float(-values[values < 0].sum())
    if loss == 0:
        return math.inf if gain > 0 else 0.0
    return gain / loss

def parse_fixed(root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    registry = json.loads((root / "workr1/r1_registry_snapshot.json").read_text())
    candidates: dict[str, dict[str, Any]] = {}
    for family in registry["families"]:
        for row in family["candidates"]:
            if row["id"] in IDS:
                candidates[row["id"]] = row
    frozen = pd.read_csv(root / "workr6/frozen_complete_strategies.csv")
    specs = []
    for row in frozen.itertuples(index=False):
        if row.candidate_id in IDS:
            specs.append({
                "freeze_rank": int(row.freeze_rank),
                "strategy_id": row.strategy_id,
                "candidate_id": row.candidate_id,
                "family": row.family,
                "entry_definition_sha256": row.definition_sha256,
                "time_cap_bars": int(row.time_cap_bars),
            })
    assert set(candidates) == set(IDS)
    assert {x["candidate_id"] for x in specs} == set(IDS)
    return candidates, specs

def market_features(bars: pd.DataFrame) -> pd.DataFrame:
    close = bars["mid_close"].astype(float)
    ret = close.pct_change()
    abs_change = close.diff().abs()
    f = pd.DataFrame({"signal_dt": bars["timestamp_utc"]})
    f["return_5d"] = close / close.shift(480) - 1.0
    f["return_20d"] = close / close.shift(1920) - 1.0
    f["path_efficiency_5d"] = (close - close.shift(480)).abs() / abs_change.rolling(480, min_periods=480).sum().replace(0.0, np.nan)
    f["path_efficiency_20d"] = (close - close.shift(1920)).abs() / abs_change.rolling(1920, min_periods=1920).sum().replace(0.0, np.nan)
    vol5 = np.sqrt(ret.pow(2).rolling(480, min_periods=480).mean())
    vol20 = np.sqrt(ret.pow(2).rolling(1920, min_periods=1920).mean())
    f["volatility_ratio_5d_20d"] = vol5 / vol20.replace(0.0, np.nan)
    hi = bars["mid_high"].rolling(1920, min_periods=1920).max()
    lo = bars["mid_low"].rolling(1920, min_periods=1920).min()
    f["range_position_20d"] = (close - lo) / (hi - lo).replace(0.0, np.nan)
    up5, up20 = f["return_5d"] > 0, f["return_20d"] > 0
    dn5, dn20 = f["return_5d"] < 0, f["return_20d"] < 0
    f["direction_agreement"] = np.select([up5 & up20, dn5 & dn20], ["BOTH_UP", "BOTH_DOWN"], default="DISAGREE_OR_ZERO")
    f["path_efficiency_5d_bin"] = np.where(f["path_efficiency_5d"] >= 0.25, "GE_0_25", "LT_0_25")
    f["path_efficiency_20d_bin"] = np.where(f["path_efficiency_20d"] >= 0.25, "GE_0_25", "LT_0_25")
    f["volatility_ratio_bin"] = np.where(f["volatility_ratio_5d_20d"] > 1.0, "GT_1", "LE_1")
    f["range_position_20d_bin"] = np.select(
        [f["range_position_20d"] <= 1/3, f["range_position_20d"] >= 2/3],
        ["LOWER_THIRD", "UPPER_THIRD"], default="MIDDLE_THIRD")
    return f

def generate_all(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates, specs = parse_fixed(root)
    b23 = load23(root / "work23/normalized/usdjpy_2023_m15_bid_utc_rakuten_mt4_v1.csv.gz")
    b24 = load24(root / "workr0/canonical/bars/M15/USDJPY_M15.csv.gz")
    bars = pd.concat([b23, b24], ignore_index=True).sort_values("timestamp_utc").drop_duplicates("timestamp_utc").reset_index(drop=True)
    features = market_features(bars)
    trade_frames = []
    for label, (start, end) in PERIODS.items():
        period_bars = b23 if label.startswith("2023") else b24
        signals = pd.concat([build_signals(period_bars, candidates[cid], start, end) for cid in IDS], ignore_index=True)
        trades = build_trades(period_bars, signals, specs, start, end)
        trades["period"] = label
        trade_frames.append(trades)
    trades = pd.concat(trade_frames, ignore_index=True)
    trades["signal_dt"] = pd.to_datetime(trades["signal_ts"], utc=True)
    joined = trades.merge(features, on="signal_dt", how="left", validate="many_to_one")
    feature_cols = ["return_5d", "return_20d", "path_efficiency_5d", "path_efficiency_20d", "volatility_ratio_5d_20d", "range_position_20d"]
    joined["feature_complete"] = joined[feature_cols].notna().all(axis=1)
    joined = joined[joined["feature_complete"]].copy()
    persistent = joined["direction_agreement"].isin(["BOTH_UP", "BOTH_DOWN"])
    market_side = np.where(joined["direction_agreement"] == "BOTH_UP", 1, np.where(joined["direction_agreement"] == "BOTH_DOWN", -1, 0))
    joined["persistent_signal_relation"] = np.select(
        [persistent & (joined["side"].to_numpy(int) == market_side), persistent & (joined["side"].to_numpy(int) == -market_side)],
        ["PERSISTENT_ALIGNED", "PERSISTENT_COUNTER"], default="NONPERSISTENT")
    joined["continuation_default"] = joined["default_net_pips"]
    joined["continuation_severe"] = joined["severe_net_pips"]
    joined["reversal_default"] = -joined["gross_pips"] - joined["default_cost_pips"]
    joined["reversal_severe"] = -joined["gross_pips"] - joined["severe_cost_pips"]
    joined["action_advantage"] = 2.0 * joined["gross_pips"]
    return bars, joined

def metrics(group: pd.DataFrame, action: str) -> dict[str, Any]:
    default_col = f"{action}_default"
    severe_col = f"{action}_severe"
    default = group[default_col].astype(float)
    severe = group[severe_col].astype(float)
    monthly = group.groupby("entry_month", sort=True)[default_col].sum()
    daily = group.groupby("entry_date_utc", sort=True)[default_col].sum()
    positives = daily[daily > 0].sort_values(ascending=False)
    positive_sum = float(positives.sum())
    return {
        "trades": int(len(group)),
        "default_net_pips": float(default.sum()),
        "default_pf": float(profit_factor(default)),
        "severe_net_pips": float(severe.sum()),
        "severe_pf": float(profit_factor(severe)),
        "positive_months": int((monthly > 0).sum()),
        "negative_months": int((monthly < 0).sum()),
        "ex_best_two_dates_default": float(default.sum() - daily.sort_values(ascending=False).head(2).sum()),
        "top_two_positive_date_share": 0.0 if positive_sum == 0 else float(positives.head(2).sum() / positive_sum),
    }

def aggregate_states(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pooled_rows, strategy_rows, side_rows = [], [], []
    for dimension in DIMENSIONS:
        for state, state_group in trades.groupby(dimension, sort=True):
            for period, period_group in state_group.groupby("period", sort=True):
                base = {"dimension": dimension, "state": state, "period": period, "action_advantage_pips": float(period_group["action_advantage"].sum())}
                for action in ["continuation", "reversal"]:
                    row = dict(base); row["action"] = action; row.update(metrics(period_group, action)); pooled_rows.append(row)
                for cid, subgroup in period_group.groupby("candidate_id", sort=True):
                    for action in ["continuation", "reversal"]:
                        row = dict(base); row.update({"candidate_id": cid, "action": action}); row.update(metrics(subgroup, action)); strategy_rows.append(row)
                for side, subgroup in period_group.groupby("side", sort=True):
                    for action in ["continuation", "reversal"]:
                        row = dict(base); row.update({"side": int(side), "action": action}); row.update(metrics(subgroup, action)); side_rows.append(row)
    return pd.DataFrame(pooled_rows), pd.DataFrame(strategy_rows), pd.DataFrame(side_rows)

def evaluate_consistency(pooled: pd.DataFrame, strategy: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (dimension, state), group in pooled.groupby(["dimension", "state"], sort=True):
        period_actions = {}
        for period in PERIODS:
            pg = group[group["period"] == period]
            if len(pg) != 2:
                period_actions[period] = None; continue
            cont = pg[pg["action"] == "continuation"].iloc[0]
            rev = pg[pg["action"] == "reversal"].iloc[0]
            if int(cont["trades"]) < 30:
                period_actions[period] = None; continue
            period_actions[period] = "continuation" if float(cont["default_net_pips"]) >= float(rev["default_net_pips"]) else "reversal"
        actions = [period_actions[p] for p in PERIODS]
        same = None not in actions and len(set(actions)) == 1
        preferred = actions[0] if same else None
        gates = {"same_preferred_action": same}
        breadth = []
        if same:
            selected = group[group["action"] == preferred].set_index("period")
            gates.update({
                "default_positive_all": bool((selected["default_net_pips"] > 0).all()),
                "severe_positive_all": bool((selected["severe_net_pips"] > 0).all()),
                "advantage_positive_all": bool((selected["action_advantage_pips"] > 0).all()) if preferred == "continuation" else bool((selected["action_advantage_pips"] < 0).all()),
                "monthly_breadth_all": bool(((selected["positive_months"] >= 4) & (selected["negative_months"] <= 2)).all()),
                "ex_best_two_positive_all": bool((selected["ex_best_two_dates_default"] > 0).all()),
            })
            for period in PERIODS:
                sg = strategy[(strategy["dimension"] == dimension) & (strategy["state"] == state) & (strategy["period"] == period)]
                supported = sg[sg["trades"] >= 5]
                pivot = supported.pivot_table(index="candidate_id", columns="action", values="default_net_pips", aggfunc="first")
                if {"continuation", "reversal"}.issubset(pivot.columns):
                    favorable = (pivot[preferred] > pivot["reversal" if preferred == "continuation" else "continuation"]).sum()
                    breadth.append(int(favorable))
                else:
                    breadth.append(0)
            gates["strategy_breadth_all"] = bool(all(x >= 3 for x in breadth))
        else:
            gates.update({"default_positive_all": False, "severe_positive_all": False, "advantage_positive_all": False, "monthly_breadth_all": False, "ex_best_two_positive_all": False, "strategy_breadth_all": False})
        passed = all(gates.values())
        rows.append({"dimension": dimension, "state": state, "preferred_action": preferred or "INCONSISTENT", "period_actions": json.dumps(period_actions, sort_keys=True), "min_supported_strategies": min(breadth) if breadth else 0, **gates, "passed": passed})
    return pd.DataFrame(rows).sort_values(["passed", "dimension", "state"], ascending=[False, True, True]).reset_index(drop=True)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    bars, trades = generate_all(args.input_root)
    pooled, strategy, side = aggregate_states(trades)
    consistency = evaluate_consistency(pooled, strategy)
    passing = consistency[consistency["passed"]]
    trades.to_csv(args.output / "usdjpy_long_horizon_regime_trade_features_v1.csv", index=False)
    pooled.to_csv(args.output / "usdjpy_long_horizon_regime_pooled_metrics_v1.csv", index=False)
    strategy.to_csv(args.output / "usdjpy_long_horizon_regime_strategy_metrics_v1.csv", index=False)
    side.to_csv(args.output / "usdjpy_long_horizon_regime_side_metrics_v1.csv", index=False)
    consistency.to_csv(args.output / "usdjpy_long_horizon_regime_consistency_v1.csv", index=False)
    result = {
        "schema_version": "usdjpy_long_horizon_regime_diagnosis_result_v1",
        "status": "SUCCESSOR_STATE_FOUND" if len(passing) else "CLOSED_NO_FOURFOLD_CONSISTENT_STATE",
        "decision": "AUTHORIZE_SEPARATE_FINITE_SUCCESSOR_PREREGISTRATION" if len(passing) else "CLOSE_RQ_020B_NO_ROUTER_FROM_TESTED_STATES",
        "population": {"feature_complete_trades": int(len(trades)), "period_counts": trades.groupby("period").size().astype(int).to_dict()},
        "dimensions": DIMENSIONS,
        "tested_state_count": int(len(consistency)),
        "passing_state_count": int(len(passing)),
        "passing_states": passing.to_dict("records"),
        "consistency_rows": consistency.to_dict("records"),
        "boundaries": {"interactions_tested": False, "thresholds_optimized": False, "2024_source_mutated": False, "2025_accessed": False, "MT4_accessed": False, "router_created": False, "live_orders": False},
    }
    result["output_sha256"] = {p.name: file_sha(p) for p in args.output.iterdir() if p.is_file()}
    (args.output / "usdjpy_long_horizon_regime_diagnosis_result_v1.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
