#!/usr/bin/env python3
"""Pre-registered USDJPY M15 breakout + prior-24h alignment screen.

This is a fixed-candidate research screen, not an optimizer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

PIP = 0.01
SYMBOL = "USDJPY"
SERVER_TIMEZONE = "Europe/Helsinki"
PRIMARY_HOURS_UTC = {13, 14, 15, 16}
BREAKOUT_LOOKBACK = 3
ALIGNMENT_BARS = 96
HOLD_BARS = 6
BASE_SPREAD_PIPS = 0.5
DEFAULT_COST_PIPS = 0.5
SEVERE_COST_PIPS = 2.5
OFFICIAL_INTERVENTION_DATES = {"2024-07-11", "2024-07-12"}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def parse_hhmm(raw: str) -> time:
    h, m = raw.split(":", 1)
    return time(int(h), int(m))


def load_m1(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"DT", "Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    dt = pd.to_datetime(df["DT"], errors="coerce")
    if dt.isna().any():
        raise ValueError("DT contains unparsable rows")
    utc = pd.DatetimeIndex(dt).tz_localize(
        SERVER_TIMEZONE, ambiguous="infer", nonexistent="shift_forward"
    ).tz_convert("UTC")
    out = df.assign(timestamp_utc=utc).set_index("timestamp_utc").sort_index()
    for col in ["Open", "High", "Low", "Close"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.dropna(subset=["Open", "High", "Low", "Close"])


def resample_m15(m1: pd.DataFrame) -> pd.DataFrame:
    bars = m1[["Open", "High", "Low", "Close"]].resample(
        "15min", label="left", closed="left"
    ).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"})
    return bars.dropna().rename(
        columns={"Open": "mid_open", "High": "mid_high", "Low": "mid_low", "Close": "mid_close"}
    )


def build_candidate(bars: pd.DataFrame) -> pd.DataFrame:
    prev_high = bars["mid_high"].shift(1).rolling(BREAKOUT_LOOKBACK, min_periods=BREAKOUT_LOOKBACK).max()
    prev_low = bars["mid_low"].shift(1).rolling(BREAKOUT_LOOKBACK, min_periods=BREAKOUT_LOOKBACK).min()
    prior_24h_return_pips = (bars["mid_close"] - bars["mid_open"].shift(ALIGNMENT_BARS - 1)) / PIP

    side = pd.Series(0, index=bars.index, dtype="int64")
    side = side.mask((bars["mid_close"] > prev_high) & (prior_24h_return_pips > 0), 1)
    side = side.mask((bars["mid_close"] < prev_low) & (prior_24h_return_pips < 0), -1)

    work = bars.copy()
    work["side"] = side
    work["prior_24h_return_pips"] = prior_24h_return_pips
    work["entry_ts"] = pd.Series(work.index, index=work.index).shift(-1)
    work["entry_mid"] = work["mid_open"].shift(-1)
    work["exit_ts"] = pd.Series(work.index, index=work.index).shift(-HOLD_BARS)
    work["exit_mid"] = work["mid_close"].shift(-HOLD_BARS)

    trades = work[
        work["side"].isin([1, -1])
        & work["entry_ts"].notna()
        & work["exit_ts"].notna()
        & work["entry_mid"].notna()
        & work["exit_mid"].notna()
    ][["side", "prior_24h_return_pips", "entry_ts", "entry_mid", "exit_ts", "exit_mid"]].copy()

    trades["entry_hour_utc"] = trades["entry_ts"].dt.hour.astype(int)
    trades = trades[trades["entry_hour_utc"].isin(PRIMARY_HOURS_UTC)].copy()
    trades["date_utc"] = trades["entry_ts"].dt.date.astype(str)
    trades["month"] = trades["entry_ts"].dt.strftime("%Y-%m")
    trades["gross_pips"] = trades["side"] * (trades["exit_mid"] - trades["entry_mid"]) / PIP
    trades["default_cost_pips"] = DEFAULT_COST_PIPS
    trades["severe_cost_pips"] = SEVERE_COST_PIPS
    trades["default_net_pips"] = trades["gross_pips"] - trades["default_cost_pips"]
    trades["severe_net_pips"] = trades["gross_pips"] - trades["severe_cost_pips"]
    return trades.reset_index(drop=True)


def apply_hard_exclusions(trades: pd.DataFrame, config_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    mask = pd.Series(False, index=trades.index)
    reasons = pd.Series("", index=trades.index, dtype="object")
    for window in config.get("hard_no_trade_windows", []):
        applies = {str(v).upper() for v in window.get("applies_to", ["*"])}
        if "*" not in applies and SYMBOL not in applies:
            continue
        tz = ZoneInfo(str(window["timezone"]))
        start_t = parse_hhmm(str(window["start_local"]))
        end_t = parse_hhmm(str(window["end_local"]))
        local = trades["entry_ts"].dt.tz_convert(tz).dt.time
        this = ((local >= start_t) & (local < end_t)) if start_t <= end_t else ((local >= start_t) | (local < end_t))
        mask |= this
        reasons = reasons.mask(this, str(window.get("id", "hard_no_trade_window")))
    excluded = trades.loc[mask].copy()
    if not excluded.empty:
        excluded["hard_exclude_reason"] = reasons.loc[mask]
    return trades.loc[~mask].reset_index(drop=True), excluded.reset_index(drop=True)


def summarize(group: pd.DataFrame, net_col: str) -> dict[str, float | int]:
    net = group[net_col]
    return {
        "trades": int(len(group)),
        "win_rate": float((net > 0).mean()) if len(group) else 0.0,
        "avg_gross_pips": float(group["gross_pips"].mean()) if len(group) else 0.0,
        "avg_net_pips": float(net.mean()) if len(group) else 0.0,
        "total_net_pips": float(net.sum()) if len(group) else 0.0,
        "profit_factor": profit_factor(net),
    }


def grouped(trades: pd.DataFrame, keys: list[str], net_col: str, scenario: str) -> pd.DataFrame:
    rows = []
    for key, group in trades.groupby(keys, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(keys, key))
        row.update(summarize(group, net_col))
        row["scenario"] = scenario
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_gate(trades: pd.DataFrame, monthly_default: pd.DataFrame) -> dict[str, object]:
    all_default = summarize(trades, "default_net_pips")
    all_severe = summarize(trades, "severe_net_pips")
    no_intervention = trades[~trades["date_utc"].isin(OFFICIAL_INTERVENTION_DATES)]
    no_event_default = summarize(no_intervention, "default_net_pips")
    daily = trades.groupby("date_utc")["default_net_pips"].sum().sort_values(ascending=False)
    ex_best_two_total = float(daily.iloc[2:].sum()) if len(daily) > 2 else float("-inf")
    expected_months = [f"2024-{m:02d}" for m in range(7, 13)]
    month_map = monthly_default.set_index("month") if not monthly_default.empty else pd.DataFrame()
    positive_months = int((monthly_default["avg_net_pips"] > 0).sum())
    per_month_counts = {m: int(month_map.loc[m, "trades"]) if m in month_map.index else 0 for m in expected_months}
    checks = {
        "positive_months_at_least_4": positive_months >= 4,
        "aggregate_default_avg_positive": all_default["avg_net_pips"] > 0,
        "aggregate_default_pf_at_least_1_10": all_default["profit_factor"] >= 1.10,
        "excluding_official_dates_avg_positive": no_event_default["avg_net_pips"] > 0,
        "excluding_official_dates_pf_at_least_1_05": no_event_default["profit_factor"] >= 1.05,
        "excluding_best_two_days_total_positive": ex_best_two_total > 0,
        "aggregate_trades_at_least_180": len(trades) >= 180,
        "each_month_trades_at_least_15": all(v >= 15 for v in per_month_counts.values()),
        "severe_avg_no_worse_than_minus_0_5": all_severe["avg_net_pips"] >= -0.5,
        "severe_pf_at_least_0_90": all_severe["profit_factor"] >= 0.90,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "positive_months": positive_months,
        "per_month_counts": per_month_counts,
        "aggregate_default": all_default,
        "aggregate_severe": all_severe,
        "excluding_official_intervention_dates": no_event_default,
        "official_intervention_dates": sorted(OFFICIAL_INTERVENTION_DATES),
        "best_two_days": daily.head(2).to_dict(),
        "total_net_excluding_best_two_days": ex_best_two_total,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--session-config", required=True, type=Path)
    ap.add_argument("--start", default="2024-07-01T00:00:00Z")
    ap.add_argument("--end", default="2025-01-01T00:00:00Z")
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--fail-on-gate", action="store_true")
    args = ap.parse_args()

    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
    end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")
    if start >= end:
        raise ValueError("start must be before end")

    m1 = load_m1(args.input)
    bars = resample_m15(m1)
    trades = build_candidate(bars)
    trades = trades[(trades["entry_ts"] >= start) & (trades["entry_ts"] < end)].copy()
    trades, excluded = apply_hard_exclusions(trades, args.session_config)
    if trades.empty:
        raise ValueError("no retained trades")

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    monthly_default = grouped(trades, ["month"], "default_net_pips", "default")
    monthly_severe = grouped(trades, ["month"], "severe_net_pips", "severe")
    daily_default = grouped(trades, ["month", "date_utc"], "default_net_pips", "default")
    side_default = grouped(trades, ["month", "side"], "default_net_pips", "default")
    event_rows = []
    for label, excluded_dates in [("all_dates", set()), ("exclude_official_intervention_dates", OFFICIAL_INTERVENTION_DATES)]:
        kept = trades[~trades["date_utc"].isin(excluded_dates)]
        row = {"sensitivity": label, "excluded_dates": ",".join(sorted(excluded_dates))}
        row.update(summarize(kept, "default_net_pips"))
        event_rows.append(row)
    gate = evaluate_gate(trades, monthly_default)

    trades.to_csv(out / "trades.csv", index=False)
    excluded.to_csv(out / "excluded_trades.csv", index=False)
    monthly_default.to_csv(out / "monthly_default.csv", index=False)
    monthly_severe.to_csv(out / "monthly_severe.csv", index=False)
    daily_default.to_csv(out / "daily_default.csv", index=False)
    side_default.to_csv(out / "side_default.csv", index=False)
    pd.DataFrame(event_rows).to_csv(out / "event_sensitivity.csv", index=False)
    (out / "gate.json").write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    config = {
        "purpose": "pre-registered H2 fixed-candidate screen; no optimization",
        "symbol": SYMBOL,
        "server_timezone": SERVER_TIMEZONE,
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "candidate": {
            "timeframe": "M15",
            "breakout_lookback": BREAKOUT_LOOKBACK,
            "prior_24h_alignment_bars": ALIGNMENT_BARS,
            "hold_bars": HOLD_BARS,
            "entry_hours_utc": sorted(PRIMARY_HOURS_UTC),
            "entry": "next M15 bar open",
            "exit": "close of sixth held M15 bar",
        },
        "costs": {
            "base_spread_pips": BASE_SPREAD_PIPS,
            "default_total_cost_pips": DEFAULT_COST_PIPS,
            "severe_total_cost_pips": SEVERE_COST_PIPS,
        },
        "input": str(args.input),
        "input_sha256": file_sha256(args.input),
        "session_config": str(args.session_config),
        "hard_excluded_trades": int(len(excluded)),
    }
    (out / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(monthly_default.to_string(index=False))
    print(json.dumps(gate, indent=2, sort_keys=True))
    return 3 if args.fail_on_gate and not gate["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
