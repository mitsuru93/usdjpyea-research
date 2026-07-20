#!/usr/bin/env python3
"""Evaluate the two frozen EURUSD F v2 candidates on untouched 2025 H1 bars.

The protocol is committed before 2025 source access. This evaluator may accept
or reject the frozen candidates; it must not nominate, rank, or tune new rules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PIP = 0.0001
ONE_HOUR = pd.Timedelta(hours=1)
EXPECTED_IDS = [
    "F_v2_z72_1p5_mean_target_0p5_max12",
    "F_v2_z72_1p5_mean_target_0p25_max12",
]
REQUIRED_COLUMNS = {
    "timestamp_utc",
    "symbol",
    "mid_open",
    "mid_high",
    "mid_low",
    "mid_close",
    "spread_mean_pips",
    "tick_count",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_bars(path: Path, label: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")
    frame = frame[
        [
            "timestamp_utc",
            "symbol",
            "mid_open",
            "mid_high",
            "mid_low",
            "mid_close",
            "spread_mean_pips",
            "tick_count",
        ]
    ].copy()
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True, errors="raise")
    for column in [
        "mid_open",
        "mid_high",
        "mid_low",
        "mid_close",
        "spread_mean_pips",
        "tick_count",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    frame = frame.sort_values("timestamp_utc").reset_index(drop=True)
    if frame.empty:
        raise ValueError(f"{label} contains no bars")
    if frame["timestamp_utc"].duplicated().any():
        raise ValueError(f"{label} contains duplicate timestamps")
    if set(frame["symbol"].astype(str).str.upper()) != {"EURUSD"}:
        raise ValueError(f"{label} contains an unexpected symbol")
    if (frame["mid_high"] < frame[["mid_open", "mid_close", "mid_low"]].max(axis=1)).any():
        raise ValueError(f"{label} contains invalid highs")
    if (frame["mid_low"] > frame[["mid_open", "mid_close", "mid_high"]].min(axis=1)).any():
        raise ValueError(f"{label} contains invalid lows")
    return frame


def frame_content_sha256(frame: pd.DataFrame) -> str:
    work = frame[
        [
            "timestamp_utc",
            "symbol",
            "mid_open",
            "mid_high",
            "mid_low",
            "mid_close",
            "spread_mean_pips",
            "tick_count",
        ]
    ].copy()
    work["timestamp_utc"] = work["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = work.to_csv(index=False, float_format="%.15g", lineterminator="\n").encode()
    return hashlib.sha256(payload).hexdigest()


def add_indicators(frame: pd.DataFrame, z_lookback: int, er_lookback: int) -> pd.DataFrame:
    result = frame.copy()
    close = result["mid_close"]
    mean = close.rolling(z_lookback, min_periods=z_lookback).mean()
    deviation = close.rolling(z_lookback, min_periods=z_lookback).std(ddof=0).replace(0, np.nan)
    result["zscore"] = (close - mean) / deviation
    direction = (close - close.shift(er_lookback)).abs()
    volatility = close.diff().abs().rolling(er_lookback, min_periods=er_lookback).sum().replace(0, np.nan)
    result["efficiency_ratio"] = direction / volatility
    result["entry_date_utc"] = result["timestamp_utc"].dt.strftime("%Y-%m-%d")
    result["entry_month"] = result["timestamp_utc"].dt.strftime("%Y-%m")
    return result


def hard_excluded(entry_utc: pd.Timestamp) -> bool:
    local = entry_utc.tz_convert(ZoneInfo("America/New_York"))
    return 16 <= local.hour < 19


def build_trades(
    frame: pd.DataFrame,
    candidate: dict[str, object],
    start: pd.Timestamp,
    end: pd.Timestamp,
    execution: dict[str, object],
) -> pd.DataFrame:
    threshold = float(candidate["entry_abs_z"])
    er_max = float(candidate["efficiency_ratio_maximum"])
    target = float(candidate["exit_target_abs_z"])
    max_hold = int(candidate["maximum_hold_bars"])

    side = pd.Series(0, index=frame.index, dtype=int)
    regime = frame["efficiency_ratio"] <= er_max
    side.loc[regime & (frame["zscore"] <= -threshold)] = 1
    side.loc[regime & (frame["zscore"] >= threshold)] = -1

    rows: list[dict[str, object]] = []
    last_exit_index = -1
    for signal_index in side[side.isin([1, -1])].index:
        signal_index = int(signal_index)
        entry_index = signal_index + 1
        if entry_index >= len(frame) or entry_index <= last_exit_index:
            continue
        entry_utc = frame.at[entry_index, "timestamp_utc"]
        if not (start <= entry_utc < end):
            continue
        if hard_excluded(entry_utc):
            continue

        direction = int(side.at[signal_index])
        entry_mid = float(frame.at[entry_index, "mid_open"])
        exit_index: int | None = None
        exit_reason = "max_hold"
        for hold in range(1, max_hold + 1):
            current = signal_index + hold
            if current >= len(frame):
                break
            z_value = frame.at[current, "zscore"]
            if pd.isna(z_value):
                continue
            reached = (direction == 1 and float(z_value) >= -target) or (
                direction == -1 and float(z_value) <= target
            )
            if reached:
                exit_index = current
                exit_reason = f"z_target_{target}"
                break
        if exit_index is None:
            exit_index = signal_index + max_hold
        if exit_index >= len(frame):
            continue

        exit_utc = frame.at[exit_index, "timestamp_utc"] + ONE_HOUR
        if exit_utc > end:
            continue
        exit_mid = float(frame.at[exit_index, "mid_close"])
        gross_pips = direction * (exit_mid - entry_mid) / PIP
        spread_basis = max(
            float(execution["base_spread_pips"]),
            float(frame.at[entry_index, "spread_mean_pips"]),
        )
        default = execution["default_cost"]
        severe = execution["severe_cost"]
        default_cost = spread_basis * float(default["spread_multiplier"]) + 2.0 * float(
            default["slippage_pips_per_side"]
        )
        severe_cost = spread_basis * float(severe["spread_multiplier"]) + 2.0 * float(
            severe["slippage_pips_per_side"]
        )
        rows.append(
            {
                "candidate_id": candidate["id"],
                "signal_ts": frame.at[signal_index, "timestamp_utc"],
                "entry_ts": entry_utc,
                "exit_time_utc": exit_utc,
                "side": direction,
                "hold_bars": exit_index - signal_index,
                "exit_reason": exit_reason,
                "signal_zscore": float(frame.at[signal_index, "zscore"]),
                "signal_efficiency_ratio": float(frame.at[signal_index, "efficiency_ratio"]),
                "entry_mid": entry_mid,
                "exit_mid": exit_mid,
                "gross_pips": gross_pips,
                "spread_basis_pips": spread_basis,
                "default_cost_pips": default_cost,
                "net_pips": gross_pips - default_cost,
                "severe_cost_pips": severe_cost,
                "severe_net_pips": gross_pips - severe_cost,
                "entry_date_utc": entry_utc.strftime("%Y-%m-%d"),
                "entry_month": entry_utc.strftime("%Y-%m"),
            }
        )
        last_exit_index = exit_index
    return pd.DataFrame(rows)


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses > 0:
        return gains / losses
    return math.inf if gains > 0 else 0.0


def summarize(trades: pd.DataFrame, months: list[str]) -> dict[str, object]:
    if trades.empty:
        return {
            "trades": 0,
            "avg_net_pips": 0.0,
            "total_net_pips": 0.0,
            "profit_factor": 0.0,
            "positive_months": 0,
            "total_excluding_best_two_days": 0.0,
            "severe_profit_factor": 0.0,
            "max_drawdown_pips": 0.0,
        }
    monthly = trades.groupby("entry_month")["net_pips"].sum().reindex(months, fill_value=0.0)
    daily = trades.groupby("entry_date_utc")["net_pips"].sum().sort_values(ascending=False)
    equity = trades.sort_values("entry_ts")["net_pips"].cumsum()
    equity_with_origin = pd.concat([pd.Series([0.0]), equity.reset_index(drop=True)], ignore_index=True)
    drawdown = equity_with_origin - equity_with_origin.cummax()
    return {
        "trades": int(len(trades)),
        "avg_net_pips": float(trades["net_pips"].mean()),
        "total_net_pips": float(trades["net_pips"].sum()),
        "profit_factor": float(profit_factor(trades["net_pips"])),
        "positive_months": int((monthly > 0).sum()),
        "total_excluding_best_two_days": float(trades["net_pips"].sum() - daily.head(2).sum()),
        "severe_profit_factor": float(profit_factor(trades["severe_net_pips"])),
        "max_drawdown_pips": float(drawdown.min()),
    }


def gate_pass(metrics: dict[str, object], gate: dict[str, object]) -> bool:
    return bool(
        float(metrics["profit_factor"]) >= float(gate["profit_factor_gte"])
        and int(metrics["positive_months"]) >= int(gate["positive_months_gte"])
        and int(metrics["trades"]) >= int(gate["trades_gte"])
        and float(metrics["total_excluding_best_two_days"])
        > float(gate["total_excluding_best_two_days_gt"])
        and float(metrics["severe_profit_factor"])
        >= float(gate["severe_profit_factor_gte"])
    )


def monthly_rows(trades: pd.DataFrame, candidate_id: str, months: list[str]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for month in months:
        subset = trades.loc[trades["entry_month"] == month]
        result.append(
            {
                "candidate_id": candidate_id,
                "month": month,
                "trades": int(len(subset)),
                "gross_total_pips": float(subset["gross_pips"].sum()) if not subset.empty else 0.0,
                "net_total_pips": float(subset["net_pips"].sum()) if not subset.empty else 0.0,
                "net_avg_pips": float(subset["net_pips"].mean()) if not subset.empty else 0.0,
                "profit_factor": float(profit_factor(subset["net_pips"])) if not subset.empty else 0.0,
                "severe_profit_factor": float(profit_factor(subset["severe_net_pips"]))
                if not subset.empty
                else 0.0,
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warmup-bars", required=True, type=Path)
    parser.add_argument("--replication-bars", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol["status"] != "preregistered_before_2025_source_access":
        raise RuntimeError("replication protocol is not preregistered")
    candidate_ids = [row["id"] for row in protocol["candidate_definitions"]]
    if candidate_ids != EXPECTED_IDS:
        raise RuntimeError(f"unexpected frozen candidate cohort: {candidate_ids}")
    if not protocol["anti_leakage"]["candidate_rules_immutable_before_2025_access"]:
        raise RuntimeError("anti-leakage lock is not active")

    start = pd.Timestamp(protocol["period"]["replication_start_utc"])
    end = pd.Timestamp(protocol["period"]["replication_end_utc_exclusive"])
    warmup = load_bars(args.warmup_bars, "warmup")
    replication = load_bars(args.replication_bars, "replication")
    if warmup["timestamp_utc"].max() >= start:
        raise RuntimeError("warmup source contains 2025 or later bars")
    if replication["timestamp_utc"].min() < start or replication["timestamp_utc"].max() >= end:
        raise RuntimeError("replication source is outside the preregistered 2025 period")

    combined = pd.concat([warmup, replication], ignore_index=True).sort_values("timestamp_utc").reset_index(drop=True)
    if combined["timestamp_utc"].duplicated().any():
        raise RuntimeError("combined source contains duplicate timestamps")
    first = protocol["candidate_definitions"][0]
    combined = add_indicators(
        combined,
        int(first["zscore_lookback_bars"]),
        int(first["efficiency_ratio_lookback_bars"]),
    )

    months = [f"2025-{month:02d}" for month in range(1, 13)]
    summary_rows: list[dict[str, object]] = []
    trade_frames: list[pd.DataFrame] = []
    all_monthly_rows: list[dict[str, object]] = []
    for candidate in protocol["candidate_definitions"]:
        trades = build_trades(combined, candidate, start, end, protocol["execution"])
        metrics = summarize(trades, months)
        passed = gate_pass(metrics, protocol["replication_gate"])
        summary_rows.append(
            {
                "candidate_id": candidate["id"],
                "implementation_priority": candidate["implementation_priority"],
                **metrics,
                "replication_pass": passed,
            }
        )
        if not trades.empty:
            trade_frames.append(trades)
        all_monthly_rows.extend(monthly_rows(trades, str(candidate["id"]), months))

    summary = pd.DataFrame(summary_rows)
    trades_all = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    monthly = pd.DataFrame(all_monthly_rows)
    passing = summary.loc[summary["replication_pass"], "candidate_id"].tolist()
    family_pass = len(passing) >= 1
    if len(passing) == 2:
        decision = protocol["family_decision"]["if_both_pass"]
    elif len(passing) == 1:
        decision = f"retain sole passing frozen candidate: {passing[0]}"
    else:
        decision = protocol["family_decision"]["if_neither_passes"]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_dir / "replication_summary.csv", index=False)
    trades_all.to_csv(args.output_dir / "replication_trades.csv", index=False)
    monthly.to_csv(args.output_dir / "monthly_metrics.csv", index=False)

    source_receipt = {
        "schema_version": "eurusd_fv2_2025_replication_source_receipt_v1",
        "warmup_file": str(args.warmup_bars),
        "warmup_file_sha256": f"sha256:{sha256_file(args.warmup_bars)}",
        "warmup_frame_sha256": f"sha256:{frame_content_sha256(warmup)}",
        "warmup_first_utc": warmup["timestamp_utc"].iloc[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "warmup_last_utc": warmup["timestamp_utc"].iloc[-1].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "replication_file": str(args.replication_bars),
        "replication_file_sha256": f"sha256:{sha256_file(args.replication_bars)}",
        "replication_frame_sha256": f"sha256:{frame_content_sha256(replication)}",
        "replication_first_utc": replication["timestamp_utc"].iloc[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "replication_last_utc": replication["timestamp_utc"].iloc[-1].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol_file": str(args.protocol),
        "protocol_sha256": f"sha256:{sha256_file(args.protocol)}",
        "candidate_lock_sha256": protocol["authoritative_predecessors"]["candidate_lock_sha256"],
    }
    write_json(args.output_dir / "source_receipt.json", source_receipt)
    result = {
        "schema_version": "eurusd_fv2_2025_replication_result_v1",
        "period": protocol["period"],
        "candidate_ids": candidate_ids,
        "passing_candidate_ids": passing,
        "family_pass": family_pass,
        "decision": decision,
        "new_rule_or_parameter_selected_from_2025": False,
        "summary": summary_rows,
    }
    write_json(args.output_dir / "replication_result.json", result)

    lines = [
        "# EURUSD F v2 untouched 2025 full-year replication",
        "",
        f"Family pass: **{family_pass}**",
        f"Passing frozen candidates: {', '.join(passing) if passing else 'none'}",
        f"Pre-registered decision: {decision}",
        "",
        summary.to_markdown(index=False),
        "",
        "No rule, parameter, filter, or exit threshold was created or tuned from 2025 results.",
    ]
    (args.output_dir / "analysis_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    checksum_lines = []
    for path in sorted(args.output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            checksum_lines.append(f"{sha256_file(path)}  {path.name}")
    (args.output_dir / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
