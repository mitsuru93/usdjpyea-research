#!/usr/bin/env python3
"""Run the fixed USDJPY H1 multi-family development screen on Dukascopy M15 bars.

The candidate registry is authoritative. This tool does not optimize thresholds or
combine families. It evaluates the listed candidates and applies the listed H1
retention screen.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

PIP = 0.01
SYMBOL = "USDJPY"


def parse_labeled_path(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("expected MONTH=PATH")
    label, value = raw.split("=", 1)
    path = Path(value).expanduser().resolve()
    if not label.strip() or not path.exists():
        raise argparse.ArgumentTypeError(f"invalid input: {raw}")
    return label.strip(), path


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def parse_hhmm(raw: str) -> time:
    hour, minute = raw.split(":", 1)
    return time(int(hour), int(minute))


def load_bars(month: str, root: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    paths = sorted(root.rglob("M15/USDJPY_M15.csv.gz"))
    if not paths:
        raise FileNotFoundError(f"no M15/USDJPY_M15.csv.gz under {root}")
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        required = {
            "timestamp_utc", "mid_open", "mid_high", "mid_low", "mid_close",
            "spread_open_pips"
        }
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{path} missing columns: {sorted(missing)}")
        frame = frame[list(required)].copy()
        frame["_path"] = str(path)
        frame["_priority"] = 1 if "baseline_aggregate_repair" in str(path) else 0
        frames.append(frame)
    bars = pd.concat(frames, ignore_index=True)
    bars["timestamp_utc"] = pd.to_datetime(bars["timestamp_utc"], utc=True)
    for col in ["mid_open", "mid_high", "mid_low", "mid_close", "spread_open_pips"]:
        bars[col] = pd.to_numeric(bars[col], errors="coerce")
    bars = bars.dropna(subset=["timestamp_utc", "mid_open", "mid_high", "mid_low", "mid_close"])
    before = len(bars)
    bars = bars.sort_values(["timestamp_utc", "_priority", "_path"])
    bars = bars.drop_duplicates("timestamp_utc", keep="last")
    bars = bars.sort_values("timestamp_utc").reset_index(drop=True)
    bars["month"] = month
    bars["date_utc"] = bars["timestamp_utc"].dt.strftime("%Y-%m-%d")
    bars["hour_utc"] = bars["timestamp_utc"].dt.hour.astype(int)
    bars["bar_range_pips"] = (bars["mid_high"] - bars["mid_low"]) / PIP
    coverage = {
        "month": month,
        "files": len(paths),
        "rows_before_dedup": int(before),
        "rows_after_dedup": int(len(bars)),
        "duplicate_rows_removed": int(before - len(bars)),
        "start": bars["timestamp_utc"].min().isoformat(),
        "end": bars["timestamp_utc"].max().isoformat(),
    }
    return bars, coverage


def hard_exclusion_mask(entry_ts: pd.Series, config: dict, symbol: str) -> pd.Series:
    mask = pd.Series(False, index=entry_ts.index)
    for window in config.get("hard_no_trade_windows", []):
        applies = {str(v).upper() for v in window.get("applies_to", ["*"])}
        if "*" not in applies and symbol.upper() not in applies:
            continue
        local = entry_ts.dt.tz_convert(ZoneInfo(str(window["timezone"]))).dt.time
        start_t = parse_hhmm(str(window["start_local"]))
        end_t = parse_hhmm(str(window["end_local"]))
        if start_t <= end_t:
            current = (local >= start_t) & (local < end_t)
        else:
            current = (local >= start_t) | (local < end_t)
        mask |= current
    return mask


def finalize_signals(
    bars: pd.DataFrame,
    side: pd.Series,
    candidate: dict,
    family: str,
    session_config: dict,
) -> pd.DataFrame:
    hold = int(candidate["hold_bars"])
    work = bars.copy()
    work["side"] = side.fillna(0).astype(int)
    work["entry_ts"] = work["timestamp_utc"].shift(-1)
    work["entry_mid"] = work["mid_open"].shift(-1)
    work["entry_spread_pips"] = work["spread_open_pips"].shift(-1)
    work["exit_ts"] = work["timestamp_utc"].shift(-hold)
    work["exit_mid"] = work["mid_close"].shift(-hold)
    trades = work[
        work["side"].isin([1, -1])
        & work["entry_ts"].notna()
        & work["exit_ts"].notna()
        & work["entry_mid"].notna()
        & work["exit_mid"].notna()
    ].copy()
    if trades.empty:
        return trades
    trades = trades[~hard_exclusion_mask(trades["entry_ts"], session_config, SYMBOL)].copy()
    trades["candidate_id"] = candidate["id"]
    trades["family"] = family
    trades["hold_bars"] = hold
    trades["entry_date_utc"] = trades["entry_ts"].dt.strftime("%Y-%m-%d")
    trades["entry_month"] = trades["entry_ts"].dt.strftime("%Y-%m")
    trades["gross_pips"] = trades["side"] * (trades["exit_mid"] - trades["entry_mid"]) / PIP
    base = float(candidate.get("base_spread_pips", 0.5))
    spread = trades["entry_spread_pips"].fillna(base).clip(lower=base)
    trades["default_cost_pips"] = spread
    trades["severe_cost_pips"] = spread * 3.0 + 1.0
    trades["default_net_pips"] = trades["gross_pips"] - trades["default_cost_pips"]
    trades["severe_net_pips"] = trades["gross_pips"] - trades["severe_cost_pips"]
    return trades


def first_per_direction_day(side: pd.Series, bars: pd.DataFrame) -> pd.Series:
    keep = pd.Series(0, index=side.index, dtype=int)
    selected = pd.DataFrame({"side": side, "date": bars["date_utc"], "ts": bars["timestamp_utc"]})
    selected = selected[selected["side"].isin([1, -1])]
    if selected.empty:
        return keep
    first_idx = selected.sort_values("ts").groupby(["date", "side"], sort=False).head(1).index
    keep.loc[first_idx] = side.loc[first_idx].astype(int)
    return keep


def session_reference(bars: pd.DataFrame, start_hour: int, end_hour: int) -> pd.DataFrame:
    ref = bars[(bars["hour_utc"] >= start_hour) & (bars["hour_utc"] < end_hour)]
    daily = ref.groupby("date_utc").agg(ref_high=("mid_high", "max"), ref_low=("mid_low", "min"))
    return bars[["date_utc"]].join(daily, on="date_utc")


def prior_day_reference(bars: pd.DataFrame) -> pd.DataFrame:
    daily = bars.groupby("date_utc").agg(ref_high=("mid_high", "max"), ref_low=("mid_low", "min"))
    daily = daily.shift(1)
    return bars[["date_utc"]].join(daily, on="date_utc")


def impulse_breakout(bars: pd.DataFrame, candidate: dict) -> pd.Series:
    lb = int(candidate["lookback_bars"])
    prev_high = bars["mid_high"].shift(1).rolling(lb, min_periods=lb).max()
    prev_low = bars["mid_low"].shift(1).rolling(lb, min_periods=lb).min()
    expanded = bars["bar_range_pips"] > bars["bar_range_pips"].shift(1)
    allowed = bars["hour_utc"].isin(candidate["entry_hours_utc"])
    side = pd.Series(0, index=bars.index, dtype=int)
    side.loc[allowed & expanded & (bars["mid_close"] > prev_high)] = 1
    side.loc[allowed & expanded & (bars["mid_close"] < prev_low)] = -1
    return side


def session_breakout(bars: pd.DataFrame, candidate: dict) -> pd.Series:
    if candidate["reference"] == "prior_utc_day_range":
        ref = prior_day_reference(bars)
    else:
        ref = session_reference(
            bars, int(candidate["reference_start_hour"]), int(candidate["reference_end_hour_exclusive"])
        )
    allowed = (
        (bars["hour_utc"] >= int(candidate["entry_start_hour"]))
        & (bars["hour_utc"] <= int(candidate["entry_end_hour_inclusive"]))
    )
    side = pd.Series(0, index=bars.index, dtype=int)
    side.loc[allowed & (bars["mid_close"] > ref["ref_high"])] = 1
    side.loc[allowed & (bars["mid_close"] < ref["ref_low"])] = -1
    return first_per_direction_day(side, bars)


def failed_excursion(bars: pd.DataFrame, candidate: dict) -> pd.Series:
    if candidate["reference"] == "rolling_completed_bars":
        lb = int(candidate["lookback_bars"])
        ref_high = bars["mid_high"].shift(1).rolling(lb, min_periods=lb).max()
        ref_low = bars["mid_low"].shift(1).rolling(lb, min_periods=lb).min()
        allowed = bars["hour_utc"].isin(candidate["entry_hours_utc"])
    else:
        ref = session_reference(
            bars, int(candidate["reference_start_hour"]), int(candidate["reference_end_hour_exclusive"])
        )
        ref_high, ref_low = ref["ref_high"], ref["ref_low"]
        allowed = (
            (bars["hour_utc"] >= int(candidate["entry_start_hour"]))
            & (bars["hour_utc"] <= int(candidate["entry_end_hour_inclusive"]))
        )
    failed_high = (bars["mid_high"] > ref_high) & (bars["mid_close"] <= ref_high) & (bars["mid_close"] >= ref_low)
    failed_low = (bars["mid_low"] < ref_low) & (bars["mid_close"] >= ref_low) & (bars["mid_close"] <= ref_high)
    side = pd.Series(0, index=bars.index, dtype=int)
    side.loc[allowed & failed_high & ~failed_low] = -1
    side.loc[allowed & failed_low & ~failed_high] = 1
    return side


def compression_expansion(bars: pd.DataFrame, candidate: dict) -> pd.Series:
    n = int(candidate["compression_bars"])
    m = int(candidate["comparison_bars"])
    comp_high = bars["mid_high"].shift(1).rolling(n, min_periods=n).max()
    comp_low = bars["mid_low"].shift(1).rolling(n, min_periods=n).min()
    comp_range = comp_high - comp_low
    earlier_high = bars["mid_high"].shift(n + 1).rolling(m, min_periods=m).max()
    earlier_low = bars["mid_low"].shift(n + 1).rolling(m, min_periods=m).min()
    compressed = comp_range < (earlier_high - earlier_low)
    expanded = bars["bar_range_pips"] > bars["bar_range_pips"].shift(1)
    allowed = bars["hour_utc"].isin(candidate["entry_hours_utc"])
    side = pd.Series(0, index=bars.index, dtype=int)
    side.loc[allowed & compressed & expanded & (bars["mid_close"] > comp_high)] = 1
    side.loc[allowed & compressed & expanded & (bars["mid_close"] < comp_low)] = -1
    return side


def trend_continuation(bars: pd.DataFrame, candidate: dict) -> pd.Series:
    n = int(candidate["trend_bars"])
    trend_return = bars["mid_close"].shift(1) - bars["mid_open"].shift(n)
    prev_bearish = bars["mid_close"].shift(1) < bars["mid_open"].shift(1)
    prev_bullish = bars["mid_close"].shift(1) > bars["mid_open"].shift(1)
    allowed = bars["hour_utc"].isin(candidate["entry_hours_utc"])
    side = pd.Series(0, index=bars.index, dtype=int)
    side.loc[allowed & (trend_return > 0) & prev_bearish & (bars["mid_close"] > bars["mid_high"].shift(1))] = 1
    side.loc[allowed & (trend_return < 0) & prev_bullish & (bars["mid_close"] < bars["mid_low"].shift(1))] = -1
    return side


def summarize(group: pd.DataFrame, net_col: str = "default_net_pips") -> dict[str, float | int]:
    net = group[net_col]
    return {
        "trades": int(len(group)),
        "win_rate": float((net > 0).mean()) if len(group) else 0.0,
        "avg_net_pips": float(net.mean()) if len(group) else 0.0,
        "total_net_pips": float(net.sum()) if len(group) else 0.0,
        "profit_factor": profit_factor(net),
    }


def evaluate_candidate(trades: pd.DataFrame, candidate_id: str, family: str, events: set[str], screen: dict) -> tuple[dict, pd.DataFrame]:
    monthly_rows = []
    for month, group in trades.groupby("entry_month", sort=True):
        row = {"candidate_id": candidate_id, "family": family, "month": month}
        row.update(summarize(group))
        monthly_rows.append(row)
    monthly = pd.DataFrame(monthly_rows)
    default = summarize(trades)
    severe = summarize(trades, "severe_net_pips")
    q1 = trades[trades["entry_month"].isin(["2024-01", "2024-02", "2024-03"])]
    q2 = trades[trades["entry_month"].isin(["2024-04", "2024-05", "2024-06"])]
    event_excluded = trades[~trades["entry_date_utc"].isin(events)]
    daily = trades.groupby("entry_date_utc")["default_net_pips"].sum().sort_values(ascending=False)
    positive_months = int((monthly["avg_net_pips"] > 0).sum()) if not monthly.empty else 0
    min_monthly = int(monthly["trades"].min()) if not monthly.empty else 0
    total_ex_best_two = float(default["total_net_pips"] - daily.head(2).sum())
    row = {
        "candidate_id": candidate_id,
        "family": family,
        **default,
        "positive_months": positive_months,
        "minimum_monthly_trades": min_monthly,
        "q1_avg_net_pips": float(q1["default_net_pips"].mean()) if len(q1) else 0.0,
        "q2_avg_net_pips": float(q2["default_net_pips"].mean()) if len(q2) else 0.0,
        "severe_avg_net_pips": severe["avg_net_pips"],
        "severe_profit_factor": severe["profit_factor"],
        "event_excluded_avg_net_pips": float(event_excluded["default_net_pips"].mean()) if len(event_excluded) else 0.0,
        "event_excluded_profit_factor": profit_factor(event_excluded["default_net_pips"]),
        "total_excluding_best_two_days": total_ex_best_two,
        "best_day": daily.index[0] if len(daily) else "",
        "best_day_net_pips": float(daily.iloc[0]) if len(daily) else 0.0,
    }
    checks = {
        "aggregate_avg": row["avg_net_pips"] > float(screen["aggregate_avg_net_pips_gt"]),
        "aggregate_pf": row["profit_factor"] >= float(screen["aggregate_profit_factor_gte"]),
        "q1_avg": row["q1_avg_net_pips"] > float(screen["q1_avg_net_pips_gt"]),
        "q2_avg": row["q2_avg_net_pips"] > float(screen["q2_avg_net_pips_gt"]),
        "positive_months": row["positive_months"] >= int(screen["positive_months_gte"]),
        "ex_best_two": row["total_excluding_best_two_days"] > float(screen["total_excluding_best_two_days_gt"]),
        "event_excluded": row["event_excluded_avg_net_pips"] > float(screen["event_excluded_avg_net_pips_gt"]),
        "severe_pf": row["severe_profit_factor"] >= float(screen["severe_profit_factor_gte"]),
        "trades": row["trades"] >= int(screen["aggregate_trades_gte"]),
        "monthly_trades": row["minimum_monthly_trades"] >= int(screen["minimum_monthly_trades_gte"]),
    }
    row["retention_pass"] = all(checks.values())
    row["failed_checks"] = ",".join(key for key, passed in checks.items() if not passed)
    return row, monthly


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", action="append", required=True, type=parse_labeled_path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--session-config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))
    events = set(registry["event_dates_utc"])
    screen = registry["h1_retention_screen"]

    bar_frames = []
    coverage_rows = []
    for month, path in sorted(dict(args.bars).items()):
        bars, coverage = load_bars(month, path)
        bar_frames.append(bars)
        coverage_rows.append(coverage)
    bars = pd.concat(bar_frames, ignore_index=True).sort_values("timestamp_utc").reset_index(drop=True)

    all_trades = []
    summary_rows = []
    monthly_frames = []
    candidate_specs = {}
    for family_spec in registry["families"]:
        family = family_spec["family"]
        for candidate in family_spec["candidates"]:
            candidate = dict(candidate)
            candidate["base_spread_pips"] = registry["costs"]["base_spread_pips"]
            candidate_specs[candidate["id"]] = candidate
            if family == "m15_impulse_breakout":
                side = impulse_breakout(bars, candidate)
            elif family == "session_range_breakout":
                side = session_breakout(bars, candidate)
            elif family == "mean_reversion_failed_excursion":
                side = failed_excursion(bars, candidate)
            elif family == "compression_expansion":
                side = compression_expansion(bars, candidate)
            elif family == "higher_timeframe_trend_continuation":
                side = trend_continuation(bars, candidate)
            else:
                raise ValueError(f"unsupported family: {family}")
            trades = finalize_signals(bars, side, candidate, family, session_config)
            if trades.empty:
                row = {"candidate_id": candidate["id"], "family": family, "trades": 0, "retention_pass": False, "failed_checks": "no_trades"}
                summary_rows.append(row)
                continue
            result, monthly = evaluate_candidate(trades, candidate["id"], family, events, screen)
            summary_rows.append(result)
            monthly_frames.append(monthly)
            all_trades.append(trades)

    summary = pd.DataFrame(summary_rows)
    monthly = pd.concat(monthly_frames, ignore_index=True) if monthly_frames else pd.DataFrame()
    trades_out = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()

    ranking = summary.copy()
    ranking = ranking.sort_values(
        ["family", "retention_pass", "positive_months", "event_excluded_profit_factor", "severe_profit_factor", "total_excluding_best_two_days"],
        ascending=[True, False, False, False, False, False],
    )
    ranking["family_rank"] = ranking.groupby("family").cumcount() + 1
    max_rep = int(screen["max_representatives_per_family"])
    retained = ranking[(ranking["retention_pass"]) & (ranking["family_rank"] <= max_rep)]

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(coverage_rows).to_csv(out / "source_bar_coverage.csv", index=False)
    summary.to_csv(out / "candidate_summary.csv", index=False)
    monthly.to_csv(out / "candidate_monthly.csv", index=False)
    ranking.to_csv(out / "family_ranking.csv", index=False)
    trades_out.to_csv(out / "candidate_trades.csv", index=False)
    retained_payload = {
        "registry": str(args.registry),
        "retained_candidates": [
            {
                "candidate_id": row["candidate_id"],
                "family": row["family"],
                "family_rank": int(row["family_rank"]),
                "spec": candidate_specs[row["candidate_id"]],
            }
            for _, row in retained.iterrows()
        ],
    }
    (out / "retained_candidates.json").write_text(json.dumps(retained_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(ranking.to_string(index=False))
    print(json.dumps(retained_payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
