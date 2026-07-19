#!/usr/bin/env python3
"""Trade construction and evaluation for EURUSD H1/H2 screen v1."""
from __future__ import annotations

from typing import Any

import pandas as pd

from eurusd_h1_h2_data_v1 import *


def build_trades(
    bars: pd.DataFrame,
    spec: dict[str, Any],
    session_config: dict[str, Any],
    costs: dict[str, Any],
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> pd.DataFrame:
    side = signal_for_candidate(bars, spec)
    hold = int(spec["hold_bars"])
    candidates: list[dict[str, Any]] = []
    last_exit_idx = -1
    excluded_mask = hard_exclusion_mask(bars["timestamp_utc"].shift(-1), session_config)
    for signal_idx in side[side.isin([1, -1])].index:
        entry_idx = int(signal_idx) + 1
        exit_idx = int(signal_idx) + hold
        if exit_idx >= len(bars) or entry_idx >= len(bars):
            continue
        if entry_idx <= last_exit_idx:
            continue
        entry_ts = bars.at[entry_idx, "timestamp_utc"]
        exit_bar_ts = bars.at[exit_idx, "timestamp_utc"]
        exit_time = exit_bar_ts + ONE_HOUR
        if entry_ts < period_start or exit_time > period_end:
            continue
        if bool(excluded_mask.iloc[signal_idx]):
            continue
        direction = int(side.iloc[signal_idx])
        entry_mid = float(bars.at[entry_idx, "mid_open"])
        exit_mid = float(bars.at[exit_idx, "mid_close"])
        spread_basis = max(float(costs["base_spread_pips"]), float(bars.at[entry_idx, "spread_mean_pips"]))
        gross = direction * (exit_mid - entry_mid) / PIP
        row = {
            "candidate_id": spec["id"], "family_id": spec["family_id"], "family": spec["family"],
            "signal_ts": bars.at[signal_idx, "timestamp_utc"], "entry_ts": entry_ts,
            "exit_bar_ts": exit_bar_ts, "exit_time_utc": exit_time, "side": direction,
            "hold_bars": hold, "entry_mid": entry_mid, "exit_mid": exit_mid,
            "entry_public_spread_mean_pips": float(bars.at[entry_idx, "spread_mean_pips"]),
            "spread_basis_pips": spread_basis, "gross_pips": gross,
            "entry_date_utc": entry_ts.strftime("%Y-%m-%d"), "entry_month": entry_ts.strftime("%Y-%m"),
        }
        for mult in costs["spread_multipliers"]:
            for slip in costs["slippage_pips_per_side"]:
                tag = f"m{str(mult).replace('.', 'p')}_s{str(slip).replace('.', 'p')}"
                total_cost = spread_basis * float(mult) + 2.0 * float(slip)
                row[f"cost_{tag}_pips"] = total_cost
                row[f"net_{tag}_pips"] = gross - total_cost
        candidates.append(row)
        last_exit_idx = exit_idx
    return pd.DataFrame(candidates)


def metric_summary(trades: pd.DataFrame, net_col: str) -> dict[str, Any]:
    if trades.empty:
        return {"trades": 0, "wins": 0, "win_rate": 0.0, "avg_net_pips": 0.0, "total_net_pips": 0.0, "profit_factor": 0.0, "max_drawdown_pips": 0.0}
    net = pd.to_numeric(trades[net_col], errors="coerce").fillna(0.0)
    equity = net.cumsum()
    drawdown = equity - equity.cummax()
    return {
        "trades": int(len(trades)), "wins": int((net > 0).sum()), "win_rate": float((net > 0).mean()),
        "avg_net_pips": float(net.mean()), "total_net_pips": float(net.sum()),
        "profit_factor": finite(profit_factor(net)), "max_drawdown_pips": float(drawdown.min()) if len(drawdown) else 0.0,
    }


def summarize_candidate(trades: pd.DataFrame, candidate: dict[str, Any], period: str, protocol: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    default_col = protocol["cost_cases"]["default"]["net_column"]
    severe_col = protocol["cost_cases"]["severe"]["net_column"]
    base = metric_summary(trades, default_col)
    severe = metric_summary(trades, severe_col)
    monthly_rows = []
    for month in protocol["period_months"][period]:
        group = trades[trades["entry_month"] == month] if not trades.empty else trades
        row = {"candidate_id": candidate["id"], "family_id": candidate["family_id"], "family": candidate["family"], "period": period, "month": month}
        row.update(metric_summary(group, default_col))
        monthly_rows.append(row)
    monthly = pd.DataFrame(monthly_rows)
    daily = trades.groupby("entry_date_utc")[default_col].sum().sort_values(ascending=False) if not trades.empty else pd.Series(dtype=float)
    cost_rows = []
    for mult in protocol["cost_grid"]["spread_multipliers"]:
        for slip in protocol["cost_grid"]["slippage_pips_per_side"]:
            tag = f"m{str(mult).replace('.', 'p')}_s{str(slip).replace('.', 'p')}"
            m = metric_summary(trades, f"net_{tag}_pips")
            cost_rows.append({"candidate_id": candidate["id"], "family_id": candidate["family_id"], "family": candidate["family"], "period": period, "spread_multiplier": mult, "slippage_pips_per_side": slip, **m})
    row = {
        "candidate_id": candidate["id"], "family_id": candidate["family_id"], "family": candidate["family"],
        "robustness_group": candidate["robustness_group"], "period": period, **base,
        "positive_months": int((monthly["avg_net_pips"] > 0).sum()),
        "minimum_monthly_trades": int(monthly["trades"].min()) if not monthly.empty else 0,
        "total_excluding_best_two_days": float(base["total_net_pips"] - daily.head(2).sum()) if len(daily) else float(base["total_net_pips"]),
        "best_day": str(daily.index[0]) if len(daily) else "", "best_day_net_pips": float(daily.iloc[0]) if len(daily) else 0.0,
        "severe_avg_net_pips": severe["avg_net_pips"], "severe_profit_factor": severe["profit_factor"],
    }
    return row, monthly, pd.DataFrame(cost_rows)


def candidate_development_pass(row: pd.Series, protocol: dict[str, Any]) -> tuple[bool, str]:
    g = protocol["development_candidate_gate"]
    checks = {
        "avg_net": float(row["avg_net_pips"]) > float(g["avg_net_pips_gt"]),
        "profit_factor": float(row["profit_factor"]) >= float(g["profit_factor_gte"]),
        "positive_months": int(row["positive_months"]) >= int(g["positive_months_gte"]),
        "trades": int(row["trades"]) >= int(g["trades_gte"]),
        "ex_best_two": float(row["total_excluding_best_two_days"]) > float(g["total_excluding_best_two_days_gt"]),
        "severe_pf": float(row["severe_profit_factor"]) >= float(g["severe_profit_factor_gte"]),
    }
    return all(checks.values()), ",".join(k for k, v in checks.items() if not v)


def candidate_validation_pass(row: pd.Series, protocol: dict[str, Any]) -> tuple[bool, str]:
    g = protocol["validation_candidate_gate"]
    checks = {
        "avg_net": float(row["avg_net_pips"]) > float(g["avg_net_pips_gt"]),
        "profit_factor": float(row["profit_factor"]) >= float(g["profit_factor_gte"]),
        "positive_months": int(row["positive_months"]) >= int(g["positive_months_gte"]),
        "trades": int(row["trades"]) >= int(g["trades_gte"]),
    }
    return all(checks.values()), ",".join(k for k, v in checks.items() if not v)


def run_period(bars: pd.DataFrame, specs: list[dict[str, Any]], registry: dict[str, Any], session_config: dict[str, Any], protocol: dict[str, Any], period: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    start = pd.Timestamp(protocol["periods"][period]["start_utc"])
    end = pd.Timestamp(protocol["periods"][period]["end_utc_exclusive"])
    all_trades, summaries, monthly_frames, cost_frames = [], [], [], []
    for spec in specs:
        trades = build_trades(bars, spec, session_config, registry["execution_conventions"]["costs"], start, end)
        row, monthly, costs = summarize_candidate(trades, spec, period, protocol)
        summaries.append(row)
        monthly_frames.append(monthly)
        cost_frames.append(costs)
        if not trades.empty:
            trades = trades.copy()
            trades["period"] = period
            all_trades.append(trades)
    return (
        pd.DataFrame(summaries),
        pd.concat(monthly_frames, ignore_index=True) if monthly_frames else pd.DataFrame(),
        pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame(),
        pd.concat(cost_frames, ignore_index=True) if cost_frames else pd.DataFrame(),
    )
