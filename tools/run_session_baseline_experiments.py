#!/usr/bin/env python3
"""Run session-filtered baseline experiments on FX bid/ask bar artifacts.

This is not an optimizer. It is a first-pass market-structure probe that asks
whether simple breakout/continuation signals retain any expectancy after
session splits, project-wide no-trade windows, and cost stress.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

PIP_SIZE = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "AUDUSD": 0.0001,
    "USDCAD": 0.0001,
    "USDCHF": 0.0001,
    "USDJPY": 0.01,
}

DEFAULT_SESSIONS = {
    "primary_utc_13_16_jst_22_01": {13, 14, 15, 16},
    "secondary_utc_7_9_jst_16_18": {7, 8, 9},
    "excluded_utc_21_23_jst_06_08": {21, 22, 23},
    "all_non_excluded": set(range(24)) - {21, 22, 23},
    "all_hours": set(range(24)),
}

COST_SPREAD_MODES = {"fixed_base", "max_base_public"}


@dataclass(frozen=True)
class Scenario:
    spread_mult: float
    slippage_pips: float

    @property
    def label(self) -> str:
        return f"spread_x{self.spread_mult:g}_slip_{self.slippage_pips:g}"


def parse_float_list(raw: str) -> list[float]:
    return [float(x) for x in raw.replace(",", " ").split() if x.strip()]


def parse_int_list(raw: str) -> list[int]:
    return [int(x) for x in raw.replace(",", " ").split() if x.strip()]


def parse_hhmm(raw: str) -> time:
    hour_s, minute_s = raw.split(":", 1)
    return time(hour=int(hour_s), minute=int(minute_s))


def load_session_config(path: str | None) -> dict[str, object] | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def symbol_applies(window: dict[str, object], symbol: str) -> bool:
    applies = window.get("applies_to", ["*"])
    if not isinstance(applies, list):
        raise ValueError(f"applies_to must be a list in no-trade window: {window}")
    normalized = {str(item).upper() for item in applies}
    return "*" in normalized or symbol.upper() in normalized


def local_time_in_window(local_times: pd.Series, start_t: time, end_t: time) -> pd.Series:
    if start_t <= end_t:
        return (local_times >= start_t) & (local_times < end_t)
    return (local_times >= start_t) | (local_times < end_t)


def hard_exclusion_mask(trades: pd.DataFrame, symbol: str, session_config: dict[str, object] | None) -> tuple[pd.Series, pd.Series]:
    mask = pd.Series(False, index=trades.index)
    reasons = pd.Series("", index=trades.index, dtype="object")
    if not session_config:
        return mask, reasons
    windows = session_config.get("hard_no_trade_windows", [])
    if not isinstance(windows, list):
        raise ValueError("hard_no_trade_windows must be a list")
    for window in windows:
        if not isinstance(window, dict):
            raise ValueError(f"no-trade window must be an object: {window}")
        if not symbol_applies(window, symbol):
            continue
        tz = ZoneInfo(str(window["timezone"]))
        start_t = parse_hhmm(str(window["start_local"]))
        end_t = parse_hhmm(str(window["end_local"]))
        local_times = trades["entry_ts"].dt.tz_convert(tz).dt.time
        window_mask = local_time_in_window(local_times, start_t, end_t)
        reason = str(window.get("id", "hard_no_trade_window"))
        mask = mask | window_mask
        reasons = reasons.mask(window_mask & reasons.eq(""), reason)
        reasons = reasons.mask(window_mask & ~reasons.eq("") & ~reasons.str.contains(reason, regex=False), reasons + ";" + reason)
    return mask, reasons


def load_bars(paths: list[str], symbol: str, timeframes: set[str]) -> pd.DataFrame:
    frames = []
    for raw in paths:
        path = Path(raw)
        frame = pd.read_csv(path)
        frame["_input_path"] = str(path)
        frames.append(frame)
    if not frames:
        raise ValueError("at least one --input is required")
    df = pd.concat(frames, ignore_index=True)
    required = {
        "timestamp_utc",
        "symbol",
        "mid_open",
        "mid_high",
        "mid_low",
        "mid_close",
        "spread_mean_pips",
        "source_build_id",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"bar files missing required columns: {sorted(missing)}")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.upper()
    df = df[df["symbol"] == symbol.upper()].copy()
    if df.empty:
        raise ValueError(f"no bars found for symbol={symbol}")
    for col in ["mid_open", "mid_high", "mid_low", "mid_close", "spread_mean_pips"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["timestamp_utc", "mid_open", "mid_high", "mid_low", "mid_close", "spread_mean_pips"])
    df["timeframe"] = df["source_build_id"].astype(str).str.extract(r"_([A-Z0-9]+)_spread_v\d+$", expand=False)
    unknown_tf = df["timeframe"].isna()
    if unknown_tf.any():
        df.loc[unknown_tf, "timeframe"] = df.loc[unknown_tf, "_input_path"].str.extract(r"/(M1|M5|M15|H1)/", expand=False)
    df = df[df["timeframe"].isin(timeframes)].copy()
    if df.empty:
        raise ValueError(f"no bars found for requested timeframes={sorted(timeframes)}")
    df = df.drop_duplicates(subset=["timeframe", "timestamp_utc"], keep="last")
    return df.sort_values(["timeframe", "timestamp_utc"]).reset_index(drop=True)


def build_trade_rows(
    df: pd.DataFrame,
    *,
    symbol: str,
    family: str,
    params: dict[str, int | float],
    signal_side: pd.Series,
    hold_bars: int,
    pip: float,
) -> pd.DataFrame:
    work = df.copy()
    work["side"] = signal_side
    work["entry_ts"] = work["timestamp_utc"].shift(-1)
    work["entry_mid"] = work["mid_open"].shift(-1)
    work["entry_public_spread_pips"] = work["spread_mean_pips"].shift(-1)
    work["exit_ts"] = work["timestamp_utc"].shift(-hold_bars)
    work["exit_mid"] = work["mid_close"].shift(-hold_bars)
    mask = (
        work["side"].isin([1, -1])
        & work["entry_mid"].notna()
        & work["exit_mid"].notna()
        & work["entry_public_spread_pips"].notna()
    )
    trades = work.loc[
        mask,
        ["timestamp_utc", "entry_ts", "exit_ts", "entry_mid", "exit_mid", "entry_public_spread_pips", "side"],
    ].copy()
    if trades.empty:
        return trades
    trades["symbol"] = symbol
    trades["timeframe"] = str(df["timeframe"].iloc[0])
    trades["family"] = family
    trades["params_json"] = json.dumps(params, sort_keys=True)
    trades["hold_bars"] = hold_bars
    trades["entry_hour_utc"] = trades["entry_ts"].dt.hour.astype(int)
    trades["entry_hour_jst"] = ((trades["entry_hour_utc"] + 9) % 24).astype(int)
    trades["gross_pips"] = trades["side"] * (trades["exit_mid"] - trades["entry_mid"]) / pip
    return trades.reset_index(drop=True)


def breakout_trades(df: pd.DataFrame, *, symbol: str, lookbacks: list[int], holds: list[int], pip: float) -> list[pd.DataFrame]:
    out = []
    for lookback in lookbacks:
        prev_high = df["mid_high"].shift(1).rolling(lookback, min_periods=lookback).max()
        prev_low = df["mid_low"].shift(1).rolling(lookback, min_periods=lookback).min()
        side = pd.Series(0, index=df.index)
        side = side.mask(df["mid_close"] > prev_high, 1)
        side = side.mask(df["mid_close"] < prev_low, -1)
        for hold in holds:
            out.append(
                build_trade_rows(
                    df,
                    symbol=symbol,
                    family="breakout_close_followthrough",
                    params={"lookback_bars": lookback},
                    signal_side=side,
                    hold_bars=hold,
                    pip=pip,
                )
            )
    return out


def pullback_trades(
    df: pd.DataFrame,
    *,
    symbol: str,
    trend_lookbacks: list[int],
    trend_min_pips: list[float],
    pullback_min_pips: list[float],
    holds: list[int],
    pip: float,
) -> list[pd.DataFrame]:
    out = []
    close = df["mid_close"]
    one_bar_change = (close - close.shift(1)) / pip
    for lookback in trend_lookbacks:
        prior_trend = (close.shift(1) - close.shift(lookback + 1)) / pip
        for trend_min in trend_min_pips:
            for pullback_min in pullback_min_pips:
                side = pd.Series(0, index=df.index)
                side = side.mask((prior_trend >= trend_min) & (one_bar_change <= -pullback_min), 1)
                side = side.mask((prior_trend <= -trend_min) & (one_bar_change >= pullback_min), -1)
                for hold in holds:
                    out.append(
                        build_trade_rows(
                            df,
                            symbol=symbol,
                            family="pullback_continuation",
                            params={
                                "trend_lookback_bars": lookback,
                                "trend_min_pips": trend_min,
                                "pullback_min_pips": pullback_min,
                            },
                            signal_side=side,
                            hold_bars=hold,
                            pip=pip,
                        )
                    )
    return out


def apply_hard_exclusions(
    trades: pd.DataFrame,
    *,
    symbol: str,
    session_config: dict[str, object] | None,
    enforce: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if trades.empty or not session_config or not enforce:
        return trades.copy(), trades.iloc[0:0].copy()
    mask, reasons = hard_exclusion_mask(trades, symbol, session_config)
    excluded = trades.loc[mask].copy()
    if not excluded.empty:
        excluded["hard_exclude_reason"] = reasons.loc[mask]
    kept = trades.loc[~mask].copy()
    return kept.reset_index(drop=True), excluded.reset_index(drop=True)


def assign_sessions(trades: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for name, hours in DEFAULT_SESSIONS.items():
        part = trades[trades["entry_hour_utc"].isin(hours)].copy()
        if part.empty:
            continue
        part["session"] = name
        frames.append(part)
    if not frames:
        return trades.iloc[0:0].copy()
    return pd.concat(frames, ignore_index=True)


def profit_factor(values: pd.Series) -> float:
    gains = values[values > 0].sum()
    losses = -values[values < 0].sum()
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return float(gains / losses)


def summarize(stressed: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "symbol",
        "timeframe",
        "session",
        "family",
        "params_json",
        "hold_bars",
        "scenario",
        "spread_mult",
        "slippage_pips",
    ]
    rows = []
    for key, group in stressed.groupby(keys, dropna=False, sort=True):
        net = group["net_pips"]
        gross = group["gross_pips"]
        row = dict(zip(keys, key))
        row.update(
            trades=int(len(group)),
            win_rate=float((net > 0).mean()) if len(group) else 0.0,
            avg_gross_pips=float(gross.mean()) if len(group) else 0.0,
            avg_cost_pips=float(group["cost_pips"].mean()) if len(group) else 0.0,
            avg_entry_public_spread_pips=float(group["entry_public_spread_pips"].mean()) if len(group) else 0.0,
            avg_net_pips=float(net.mean()) if len(group) else 0.0,
            median_net_pips=float(net.median()) if len(group) else 0.0,
            total_net_pips=float(net.sum()) if len(group) else 0.0,
            p10_net_pips=float(net.quantile(0.10)) if len(group) else 0.0,
            p90_net_pips=float(net.quantile(0.90)) if len(group) else 0.0,
            profit_factor=profit_factor(net),
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["scenario", "timeframe", "session", "avg_net_pips", "trades"],
        ascending=[True, True, True, False, False],
    )


def make_readme(output_dir: Path, summary: pd.DataFrame, config: dict[str, object]) -> None:
    default_scenario = "spread_x1_slip_0"
    filtered = summary[(summary["scenario"] == default_scenario) & (summary["trades"] >= int(config["min_trades_for_top_table"]))]
    top = filtered.sort_values(["avg_net_pips", "trades"], ascending=[False, False]).head(20)
    lines = [
        "# USDJPY Session Baseline Results",
        "",
        "This artifact is a first-pass market-structure probe, not a deployable EA backtest.",
        "Signals use mid-price bar logic, then subtract spread and slippage stress.",
        "When `cost_spread_mode=max_base_public`, spread cost is based on max(Rakuten base spread, public bar spread).",
        "Project-wide hard no-trade windows are applied before session summaries when configured.",
        "",
        "## Configuration",
        "",
        "```json",
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Top default-cost rows with minimum trade count",
        "",
    ]
    if top.empty:
        lines.append("No rows met the minimum trade-count filter for the default-cost scenario.")
    else:
        display_cols = [
            "timeframe",
            "session",
            "family",
            "params_json",
            "hold_bars",
            "trades",
            "win_rate",
            "avg_cost_pips",
            "avg_net_pips",
            "total_net_pips",
            "profit_factor",
        ]
        lines.append(top[display_cols].to_markdown(index=False))
    lines += [
        "",
        "## Files",
        "",
        "- `trades.csv`: signal-level gross outcomes before stress expansion and after hard no-trade filtering.",
        "- `excluded_trades.csv`: signal-level trades removed by project-wide hard no-trade windows.",
        "- `summary.csv`: grouped gross/net metrics by timeframe, session, strategy family, parameters, and stress scenario.",
        "- `top_default_cost.csv`: default-cost rows sorted by average net pips after a minimum trade-count filter.",
        "- `config.json`: run configuration.",
        "",
    ]
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def spread_basis_for_cost(part: pd.DataFrame, base_spread_pips: float, cost_spread_mode: str) -> pd.Series:
    if cost_spread_mode == "fixed_base":
        return pd.Series(base_spread_pips, index=part.index, dtype="float64")
    if cost_spread_mode == "max_base_public":
        return part["entry_public_spread_pips"].clip(lower=base_spread_pips)
    raise ValueError(f"unsupported cost spread mode: {cost_spread_mode}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run session-filtered baseline experiments on FX bars.")
    parser.add_argument("--input", action="append", required=True, help="Bar CSV or CSV.GZ path. Repeatable.")
    parser.add_argument("--output-dir", required=True, help="Directory for experiment outputs.")
    parser.add_argument("--symbol", default="USDJPY", help="Symbol to analyze.")
    parser.add_argument("--timeframes", nargs="+", default=["M5", "M15"], help="Timeframes to include.")
    parser.add_argument("--base-spread-pips", type=float, default=0.5, help="Base round-trip spread cost in pips.")
    parser.add_argument(
        "--cost-spread-mode",
        choices=sorted(COST_SPREAD_MODES),
        default="max_base_public",
        help="Spread basis for cost. fixed_base ignores bar spread; max_base_public uses max(base spread, public spread).",
    )
    parser.add_argument("--spread-mults", default="1.0 1.5 2.0 3.0", help="Spread multipliers to stress.")
    parser.add_argument("--slippage-pips", default="0.0 0.1 0.3 0.5", help="Slippage pips per side to stress.")
    parser.add_argument("--breakout-lookbacks", default="3 6 12", help="Breakout lookback bars.")
    parser.add_argument("--trend-lookbacks", default="6 12 24", help="Pullback continuation trend lookback bars.")
    parser.add_argument("--trend-min-pips", default="3 6 10", help="Pullback continuation minimum trend pips.")
    parser.add_argument("--pullback-min-pips", default="1 2", help="Minimum one-bar pullback pips.")
    parser.add_argument("--hold-bars", default="1 3 6", help="Fixed holding periods in bars.")
    parser.add_argument("--min-trades-for-top-table", type=int, default=30, help="Top table minimum trade count.")
    parser.add_argument("--session-config", default=None, help="Project-wide market session/no-trade JSON config.")
    parser.add_argument(
        "--disable-hard-no-trade-windows",
        action="store_true",
        help="Do not remove trades that fall inside hard no-trade windows from the session config.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()
    pip = PIP_SIZE.get(symbol)
    if pip is None:
        raise ValueError(f"unsupported symbol: {symbol}")
    session_config = load_session_config(args.session_config)
    timeframes = {tf.upper() for tf in args.timeframes}
    bars = load_bars(args.input, symbol=symbol, timeframes=timeframes)

    hold_bars = parse_int_list(args.hold_bars)
    trade_frames = []
    for _timeframe, group in bars.groupby("timeframe", sort=True):
        group = group.sort_values("timestamp_utc").reset_index(drop=True)
        trade_frames.extend(
            breakout_trades(
                group,
                symbol=symbol,
                lookbacks=parse_int_list(args.breakout_lookbacks),
                holds=hold_bars,
                pip=pip,
            )
        )
        trade_frames.extend(
            pullback_trades(
                group,
                symbol=symbol,
                trend_lookbacks=parse_int_list(args.trend_lookbacks),
                trend_min_pips=parse_float_list(args.trend_min_pips),
                pullback_min_pips=parse_float_list(args.pullback_min_pips),
                holds=hold_bars,
                pip=pip,
            )
        )
    trades_raw = pd.concat([f for f in trade_frames if not f.empty], ignore_index=True) if trade_frames else pd.DataFrame()
    if trades_raw.empty:
        raise ValueError("no trades generated by baseline signal definitions")
    trades, excluded_trades = apply_hard_exclusions(
        trades_raw,
        symbol=symbol,
        session_config=session_config,
        enforce=not args.disable_hard_no_trade_windows,
    )
    if trades.empty:
        raise ValueError("all trades were removed by hard no-trade windows")
    session_trades = assign_sessions(trades)
    if session_trades.empty:
        raise ValueError("no trades remained after session assignment")

    scenarios = [Scenario(m, s) for m in parse_float_list(args.spread_mults) for s in parse_float_list(args.slippage_pips)]
    stressed_frames = []
    for scenario in scenarios:
        part = session_trades.copy()
        part["spread_mult"] = scenario.spread_mult
        part["slippage_pips"] = scenario.slippage_pips
        part["scenario"] = scenario.label
        spread_basis = spread_basis_for_cost(part, args.base_spread_pips, args.cost_spread_mode)
        part["spread_basis_pips"] = spread_basis
        part["cost_pips"] = (spread_basis * scenario.spread_mult) + (2.0 * scenario.slippage_pips)
        part["net_pips"] = part["gross_pips"] - part["cost_pips"]
        stressed_frames.append(part)
    stressed = pd.concat(stressed_frames, ignore_index=True)
    summary = summarize(stressed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "symbol": symbol,
        "timeframes": sorted(timeframes),
        "base_spread_pips": args.base_spread_pips,
        "cost_spread_mode": args.cost_spread_mode,
        "spread_multipliers": parse_float_list(args.spread_mults),
        "slippage_pips_per_side": parse_float_list(args.slippage_pips),
        "sessions": {k: sorted(v) for k, v in DEFAULT_SESSIONS.items()},
        "session_config": args.session_config,
        "hard_no_trade_windows_enabled": not args.disable_hard_no_trade_windows,
        "raw_signal_trades_before_hard_exclusion": int(len(trades_raw)),
        "hard_excluded_trades": int(len(excluded_trades)),
        "breakout_lookbacks": parse_int_list(args.breakout_lookbacks),
        "trend_lookbacks": parse_int_list(args.trend_lookbacks),
        "trend_min_pips": parse_float_list(args.trend_min_pips),
        "pullback_min_pips": parse_float_list(args.pullback_min_pips),
        "hold_bars": hold_bars,
        "input_files": args.input,
        "min_trades_for_top_table": args.min_trades_for_top_table,
    }
    trades.to_csv(output_dir / "trades.csv", index=False)
    excluded_trades.to_csv(output_dir / "excluded_trades.csv", index=False)
    summary.to_csv(output_dir / "summary.csv", index=False)
    default_top = summary[(summary["scenario"] == "spread_x1_slip_0") & (summary["trades"] >= args.min_trades_for_top_table)].sort_values(
        ["avg_net_pips", "trades"], ascending=[False, False]
    )
    default_top.to_csv(output_dir / "top_default_cost.csv", index=False)
    (output_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    make_readme(output_dir, summary, config)
    print(json.dumps({
        "output_dir": str(output_dir),
        "bars": int(len(bars)),
        "raw_signal_trades": int(len(trades_raw)),
        "hard_excluded_trades": int(len(excluded_trades)),
        "trades": int(len(trades)),
        "session_trade_rows": int(len(session_trades)),
        "summary_rows": int(len(summary)),
        "cost_spread_mode": args.cost_spread_mode,
        "session_config": args.session_config,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
