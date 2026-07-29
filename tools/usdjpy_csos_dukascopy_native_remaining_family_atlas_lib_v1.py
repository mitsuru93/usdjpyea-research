from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

import hyp035 as h35

PROGRAM = "USDJPY-CSOS-DUKASCOPY-NATIVE-REMAINING-FAMILY-ATLAS-V1"
PIP = 0.01
JPY_PER_PIP = 10.0
INITIAL_CAPITAL = 1_000_000.0
POSITION_UNITS = 1_000
TOL = 1e-6
FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]
MONTHS = list(pd.period_range("2023-01", "2024-12", freq="M").astype(str))
TARGET_VARIANTS = [
    "A_FALSE_BREAKOUT_REVERSAL",
    "B_BALANCE_MEAN_REVERSION",
    "C_SHOCK_CONTINUATION",
    "E_TOKYO_LONDON",
    "E_LONDON_NY",
    "E_NY_TOKYO",
    "G_TREND_EXHAUSTION",
    "H_COMPRESSION_BREAKOUT",
    "I_FAILED_TREND_CONTINUATION",
    "K_LONDON_OPENING_RANGE_BREAKOUT",
    "K_ROUND_NUMBER_REJECTION",
    "K_DAILY_TIME_SERIES_MOMENTUM",
]
VARIANT_TO_FAMILY = {
    "A_FALSE_BREAKOUT_REVERSAL": "A",
    "B_BALANCE_MEAN_REVERSION": "B",
    "C_SHOCK_CONTINUATION": "C",
    "E_TOKYO_LONDON": "E",
    "E_LONDON_NY": "E",
    "E_NY_TOKYO": "E",
    "G_TREND_EXHAUSTION": "G",
    "H_COMPRESSION_BREAKOUT": "H",
    "I_FAILED_TREND_CONTINUATION": "I",
    "K_LONDON_OPENING_RANGE_BREAKOUT": "K",
    "K_ROUND_NUMBER_REJECTION": "K",
    "K_DAILY_TIME_SERIES_MOMENTUM": "K",
}
FAMILY_NAMES = {
    "A": "False Breakout Reversal",
    "B": "Balance Mean Reversion",
    "C": "Shock Continuation",
    "E": "Session Transition",
    "G": "Trend Exhaustion",
    "H": "Volatility Compression Breakout",
    "I": "Failed Trend Continuation",
    "K": "Other Literature- and Practice-Led Families",
}
HOLD = {
    "A_FALSE_BREAKOUT_REVERSAL": 16,
    "B_BALANCE_MEAN_REVERSION": 16,
    "C_SHOCK_CONTINUATION": 8,
    "E_TOKYO_LONDON": 8,
    "E_LONDON_NY": 8,
    "E_NY_TOKYO": 8,
    "G_TREND_EXHAUSTION": 12,
    "H_COMPRESSION_BREAKOUT": 16,
    "I_FAILED_TREND_CONTINUATION": 12,
    "K_LONDON_OPENING_RANGE_BREAKOUT": 8,
    "K_ROUND_NUMBER_REJECTION": 12,
    "K_DAILY_TIME_SERIES_MOMENTUM": 32,
}
DAILY_SIDE_SUPPRESSION = {"K_LONDON_OPENING_RANGE_BREAKOUT"}
MECHANISM_HYPOTHESES = {
    "A_FALSE_BREAKOUT_REVERSAL": "Test whether sweep depth and close-back-inside acceptance identify genuine rejection at entry time.",
    "B_BALANCE_MEAN_REVERSION": "Test whether balance persistence and standardized excursion magnitude identify reversion capacity at entry time.",
    "C_SHOCK_CONTINUATION": "Test whether shock body dominance, close extremity and immediate liquidity continuity identify continuation at entry time.",
    "E_TOKYO_LONDON": "Test whether Tokyo displacement efficiency and transition liquidity continuity identify portable continuation at 07:00 UTC.",
    "E_LONDON_NY": "Test whether London displacement efficiency and transition liquidity continuity identify portable continuation at 13:00 UTC.",
    "E_NY_TOKYO": "Test whether New York displacement efficiency and rollover acceptance identify portable continuation at 21:00 UTC.",
    "G_TREND_EXHAUSTION": "Test whether trend age, expansion intensity and opposite close acceptance distinguish genuine exhaustion from temporary retracement.",
    "H_COMPRESSION_BREAKOUT": "Test whether compression duration and breakout acceptance distinguish expansion from false release at entry time.",
    "I_FAILED_TREND_CONTINUATION": "Test whether failed-extreme depth and EMA20 recross acceptance identify a causal continuation failure at entry time.",
    "K_LONDON_OPENING_RANGE_BREAKOUT": "Test whether opening-range displacement and post-break acceptance identify durable London expansion at entry time.",
    "K_ROUND_NUMBER_REJECTION": "Test whether penetration depth, wick dominance and close recovery identify causal half-yen rejection at entry time.",
    "K_DAILY_TIME_SERIES_MOMENTUM": "Test whether four-day displacement persistence relative to ATR96 identifies daily momentum continuation at entry time.",
}


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            return None
        return 0.0 if abs(float(value)) < TOL else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(clean(value), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def deterministic_gzip_csv(path: Path, frame: pd.DataFrame) -> None:
    raw = frame.to_csv(index=False, lineterminator="\n", na_rep="", float_format="%.10f").encode()
    with path.open("wb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, compresslevel=9, mtime=0) as archive:
            archive.write(raw)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profit_factor(values: Iterable[float]) -> float | None:
    values = np.asarray(list(values), dtype=float)
    gross_profit = float(values[values > 0].sum())
    gross_loss = float(-values[values < 0].sum())
    return None if gross_loss <= TOL else gross_profit / gross_loss


def realized_drawdown(values: Iterable[float], initial: float = INITIAL_CAPITAL) -> tuple[float, float]:
    values = np.asarray(list(values), dtype=float)
    if len(values) == 0:
        return 0.0, initial
    equity = initial + np.cumsum(values)
    peaks = np.maximum.accumulate(np.r_[initial, equity])[1:]
    return float(np.max(peaks - equity, initial=0.0)), float(np.min(np.r_[initial, equity]))


def fold_of(timestamp: Any) -> str | None:
    t = pd.Timestamp(timestamp)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    else:
        t = t.tz_convert("UTC")
    if t < pd.Timestamp("2023-01-01", tz="UTC") or t >= pd.Timestamp("2025-01-01", tz="UTC"):
        return None
    if t < pd.Timestamp("2023-07-01", tz="UTC"):
        return "2023H1"
    if t < pd.Timestamp("2024-01-01", tz="UTC"):
        return "2023H2"
    if t < pd.Timestamp("2024-07-01", tz="UTC"):
        return "2024H1"
    return "2024H2"


def session_of(hour: int) -> str:
    if hour < 7:
        return "TOKYO"
    if hour < 12:
        return "LONDON"
    if hour < 16:
        return "LONDON_NY_OVERLAP"
    if hour < 21:
        return "NEW_YORK"
    return "TRANSITION"


def reconstruct_source(raw_dirs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    bars, audit, source = h35.source(raw_dirs)
    bars = bars.copy()
    bars["bar_start_utc"] = pd.to_datetime(bars.bar_start_utc, utc=True)
    return bars, audit, source


def feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    x = bars.rename(columns={
        "bar_start_utc": "time",
        "bid_open": "open",
        "bid_high": "high",
        "bid_low": "low",
        "bid_close": "close",
    }).copy()
    x = x.sort_values("time", kind="mergesort").reset_index(drop=True)
    x["fold"] = x.time.map(fold_of)
    x["date"] = x.time.dt.strftime("%Y-%m-%d")
    x["hour"] = x.time.dt.hour.astype(int)
    x["minute"] = x.time.dt.minute.astype(int)
    previous_close = x.close.shift()
    true_range = pd.concat([
        x.high - x.low,
        (x.high - previous_close).abs(),
        (x.low - previous_close).abs(),
    ], axis=1).max(axis=1)
    x["tr"] = true_range / PIP
    x["body"] = (x.close - x.open).abs() / PIP
    x["direction"] = np.sign(x.close - x.open)
    x["atr16"] = x.tr.rolling(16).mean()
    x["atr20"] = x.tr.rolling(20).mean()
    x["atr96"] = x.tr.rolling(96).mean()
    x["median_tr96"] = x.tr.rolling(96).median()
    x["ema20"] = x.close.ewm(span=20, adjust=False).mean()
    x["ema96"] = x.close.ewm(span=96, adjust=False).mean()
    x["trend_strength"] = (x.ema20 - x.ema96) / (x.atr20 * PIP)
    x["mean32"] = x.close.rolling(32).mean()
    sd32 = x.close.rolling(32).std(ddof=0)
    x["z32"] = (x.close - x.mean32) / sd32.replace(0, np.nan)
    x["prior_high16"] = x.high.shift().rolling(16).max()
    x["prior_low16"] = x.low.shift().rolling(16).min()
    x["prior_high32"] = x.high.shift().rolling(32).max()
    x["prior_low32"] = x.low.shift().rolling(32).min()
    path = x.close.diff().abs().rolling(32).sum() / PIP
    x["efficiency32"] = ((x.close - x.close.shift(32)).abs() / PIP) / path.replace(0, np.nan)
    x["vol_ratio"] = x.atr20 / x.atr96
    x["compression_ratio"] = x.atr16 / x.atr96
    close_position = (x.close - x.low) / (x.high - x.low).replace(0, np.nan)
    x["shock"] = (x.tr >= 2.5 * x.median_tr96) & (x.body >= 0.65 * x.tr)
    x["up_shock"] = x.shock & (x.direction > 0) & (close_position >= 0.8)
    x["down_shock"] = x.shock & (x.direction < 0) & (close_position <= 0.2)
    x["range_price"] = x.high - x.low
    x["body_ratio"] = (x.close - x.open).abs() / x.range_price.replace(0, np.nan)
    x["close_position"] = close_position
    x["market_state"] = np.select(
        [x.trend_strength >= 1, x.trend_strength <= -1, x.efficiency32 <= 0.35],
        ["UP_TREND", "DOWN_TREND", "BALANCE"],
        default="TRANSITION",
    )
    x["volatility_state"] = np.select(
        [x.vol_ratio < 0.75, x.vol_ratio > 1.25],
        ["LOW", "HIGH"],
        default="NORMAL",
    )
    opening = x[x.hour == 7].groupby("date").agg(opening_high=("high", "max"), opening_low=("low", "min"))
    x = x.join(opening, on="date")
    return x


def raw_signal_frame(x: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    def add(mask: Any, variant: str, side: int, reason: str, strength: pd.Series | None = None) -> None:
        index = x.index[pd.Series(mask, index=x.index).fillna(False).astype(bool)]
        if not len(index):
            return
        frame = pd.DataFrame({"signal_index": index, "variant_id": variant, "side": side, "reason": reason})
        frame["signal_strength"] = np.nan if strength is None else strength.reindex(index).to_numpy()
        frames.append(frame)

    add((x.high > x.prior_high32) & (x.close < x.prior_high32) & (x.close < x.open), "A_FALSE_BREAKOUT_REVERSAL", -1, "upper_range_sweep", (x.high - x.prior_high32) / PIP)
    add((x.low < x.prior_low32) & (x.close > x.prior_low32) & (x.close > x.open), "A_FALSE_BREAKOUT_REVERSAL", 1, "lower_range_sweep", (x.prior_low32 - x.low) / PIP)
    balance = (x.trend_strength.abs() <= 0.35) & (x.efficiency32 <= 0.35)
    add(balance & (x.z32 >= 2), "B_BALANCE_MEAN_REVERSION", -1, "upper_two_sigma", x.z32.abs())
    add(balance & (x.z32 <= -2), "B_BALANCE_MEAN_REVERSION", 1, "lower_two_sigma", x.z32.abs())
    add(x.up_shock, "C_SHOCK_CONTINUATION", 1, "up_shock", x.body / x.median_tr96)
    add(x.down_shock, "C_SHOCK_CONTINUATION", -1, "down_shock", x.body / x.median_tr96)
    for start_hour, end_hour, variant in [(0, 7, "E_TOKYO_LONDON"), (7, 13, "E_LONDON_NY"), (13, 21, "E_NY_TOKYO")]:
        grouped = x[(x.hour >= start_hour) & (x.hour < end_hour)].groupby("date").agg(
            session_open=("open", "first"), session_close=("close", "last"), session_high=("high", "max"),
            session_low=("low", "min"), observed_bars=("time", "size"),
        )
        grouped["session_range"] = grouped.session_high - grouped.session_low
        grouped["session_efficiency"] = (grouped.session_close - grouped.session_open).abs() / grouped.session_range.replace(0, np.nan)
        grouped["session_close_position"] = (grouped.session_close - grouped.session_low) / grouped.session_range.replace(0, np.nan)
        transition = x[(x.hour == end_hour) & (x.minute == 0)][["date"]].join(grouped, on="date")
        minimum = max(8, (end_hour - start_hour) * 3)
        eligible = transition.observed_bars >= minimum
        long_mask = pd.Series(False, index=x.index)
        short_mask = pd.Series(False, index=x.index)
        long_mask.loc[transition.index] = eligible & (transition.session_efficiency >= 0.6) & (transition.session_close_position >= 0.8)
        short_mask.loc[transition.index] = eligible & (transition.session_efficiency >= 0.6) & (transition.session_close_position <= 0.2)
        strength = pd.Series(np.nan, index=x.index)
        strength.loc[transition.index] = transition.session_efficiency
        add(long_mask, variant, 1, "prior_session_close_high", strength)
        add(short_mask, variant, -1, "prior_session_close_low", strength)
    add((x.trend_strength.shift() >= 1.5) & (x.tr >= 1.25 * x.median_tr96) & (x.close < x.low.shift()) & (x.close < x.open), "G_TREND_EXHAUSTION", -1, "uptrend_exhaustion", x.trend_strength.shift().abs())
    add((x.trend_strength.shift() <= -1.5) & (x.tr >= 1.25 * x.median_tr96) & (x.close > x.high.shift()) & (x.close > x.open), "G_TREND_EXHAUSTION", 1, "downtrend_exhaustion", x.trend_strength.shift().abs())
    add((x.compression_ratio.shift() <= 0.6) & (x.close > x.prior_high16) & (x.close > x.open) & (x.body_ratio >= 0.5), "H_COMPRESSION_BREAKOUT", 1, "upper_compression_break", 1 / x.compression_ratio.shift())
    add((x.compression_ratio.shift() <= 0.6) & (x.close < x.prior_low16) & (x.close < x.open) & (x.body_ratio >= 0.5), "H_COMPRESSION_BREAKOUT", -1, "lower_compression_break", 1 / x.compression_ratio.shift())
    add((x.trend_strength.shift() >= 1) & (x.high > x.prior_high16) & (x.close < x.ema20) & (x.close < x.open), "I_FAILED_TREND_CONTINUATION", -1, "uptrend_failed", x.trend_strength.shift().abs())
    add((x.trend_strength.shift() <= -1) & (x.low < x.prior_low16) & (x.close > x.ema20) & (x.close > x.open), "I_FAILED_TREND_CONTINUATION", 1, "downtrend_failed", x.trend_strength.shift().abs())
    london_window = (x.hour >= 8) & (x.hour <= 12)
    add(london_window & x.opening_high.notna() & (x.close > x.opening_high) & (x.close > x.open), "K_LONDON_OPENING_RANGE_BREAKOUT", 1, "london_or_up", (x.close - x.opening_high) / PIP)
    add(london_window & x.opening_low.notna() & (x.close < x.opening_low) & (x.close < x.open), "K_LONDON_OPENING_RANGE_BREAKOUT", -1, "london_or_down", (x.opening_low - x.close) / PIP)
    upper = np.ceil(x.close.shift() * 2) / 2
    lower = np.floor(x.close.shift() * 2) / 2
    upper_wick = x.high - pd.concat([x.open, x.close], axis=1).max(axis=1)
    lower_wick = pd.concat([x.open, x.close], axis=1).min(axis=1) - x.low
    add((x.high >= upper) & (x.close < upper) & (upper_wick / x.range_price.replace(0, np.nan) >= 0.4), "K_ROUND_NUMBER_REJECTION", -1, "upper_half_yen", upper_wick / x.range_price.replace(0, np.nan))
    add((x.low <= lower) & (x.close > lower) & (lower_wick / x.range_price.replace(0, np.nan) >= 0.4), "K_ROUND_NUMBER_REJECTION", 1, "lower_half_yen", lower_wick / x.range_price.replace(0, np.nan))
    momentum = (x.close - x.close.shift(96)) / PIP
    daily_gate = (x.hour == 0) & (x.minute == 0) & x.atr96.notna()
    add(daily_gate & (momentum >= x.atr96), "K_DAILY_TIME_SERIES_MOMENTUM", 1, "four_day_up", momentum.abs() / x.atr96)
    add(daily_gate & (momentum <= -x.atr96), "K_DAILY_TIME_SERIES_MOMENTUM", -1, "four_day_down", momentum.abs() / x.atr96)
    if not frames:
        return pd.DataFrame(columns=["signal_index", "variant_id", "side", "reason", "signal_strength"])
    raw = pd.concat(frames, ignore_index=True).sort_values(["signal_index", "variant_id", "side"], kind="mergesort")
    return raw.drop_duplicates(["signal_index", "variant_id", "side"], keep="first").reset_index(drop=True)


def suppress_and_translate(raw: pd.DataFrame, x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    active_until: dict[str, int] = {}
    seen_daily: set[tuple[str, str, int]] = set()
    accepted: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for row in raw.itertuples(index=False):
        i = int(row.signal_index)
        variant = str(row.variant_id)
        side = int(row.side)
        hold = HOLD[variant]
        reason: str | None = None
        if i < 100:
            reason = "WARMUP"
        elif i + 1 + hold >= len(x):
            reason = "TAIL"
        elif x.fold.iat[i] != x.fold.iat[i + 1 + hold]:
            reason = "FOLD_CROSSING"
        elif i <= active_until.get(variant, -1):
            reason = "ACTIVE_VARIANT"
        else:
            daily_key = (variant, str(x.date.iat[i]), side)
            if variant in DAILY_SIDE_SUPPRESSION and daily_key in seen_daily:
                reason = "SAME_DAY_SAME_SIDE"
        signal_time = x.time.iat[i]
        audit = {
            "variant_id": variant,
            "family_id": VARIANT_TO_FAMILY[variant],
            "signal_index": i,
            "signal_utc": signal_time,
            "side": side,
            "reason": row.reason,
            "signal_strength": row.signal_strength,
            "accepted": reason is None,
            "suppression_reason": reason,
        }
        audit_rows.append(audit)
        if reason is not None:
            continue
        active_until[variant] = i + hold + 1
        seen_daily.add((variant, str(x.date.iat[i]), side))
        entry = x.iloc[i + 1]
        exit_bar = x.iloc[i + 1 + hold]
        accepted.append({
            "raw_event_id": f"{x.fold.iat[i]}|{variant}|{entry.time.isoformat()}|{side}",
            "family_id": VARIANT_TO_FAMILY[variant],
            "family": FAMILY_NAMES[VARIANT_TO_FAMILY[variant]],
            "variant_id": variant,
            "signal_index": i,
            "fold": x.fold.iat[i],
            "reason": row.reason,
            "signal_strength": row.signal_strength,
            "signal_utc": signal_time,
            "decision_utc": signal_time + pd.Timedelta(minutes=15),
            "entry_boundary_utc": entry.time,
            "exit_boundary_utc": exit_bar.time,
            "side": side,
            "side_label": "LONG" if side > 0 else "SHORT",
            "hold_bars": hold,
            "session": session_of(int(entry.hour)),
            "market_state": entry.market_state,
            "volatility_state": entry.volatility_state,
            "atr20_pips": entry.atr20,
            "vol_ratio": entry.vol_ratio,
            "entry_date": entry.time.strftime("%Y-%m-%d"),
            "entry_month": entry.time.strftime("%Y-%m"),
        })
    audit_frame = pd.DataFrame(audit_rows)
    events = pd.DataFrame(accepted)
    if len(events):
        events = events.sort_values(["entry_boundary_utc", "variant_id", "side"], kind="mergesort").reset_index(drop=True)
    suppression = audit_frame.groupby(["variant_id", "accepted", "suppression_reason"], dropna=False).size().rename("count").reset_index()
    return events, audit_frame, suppression


def execute_events(raw_dirs: list[Path], events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    trades = h35.execute(raw_dirs, events)
    trades["variant_id"] = trades.variant_id.astype(str)
    trades["family_id"] = trades.family_id.astype(str)
    trades["entry_tick_utc"] = pd.to_datetime(trades.entry_tick_utc, utc=True)
    trades["exit_tick_utc"] = pd.to_datetime(trades.exit_tick_utc, utc=True)
    trades["signal_utc"] = pd.to_datetime(trades.signal_utc, utc=True)
    trades["entry_month"] = trades.entry_tick_utc.dt.strftime("%Y-%m")
    trades["entry_year"] = trades.entry_tick_utc.dt.year.astype(int)
    trades["entry_date"] = trades.entry_tick_utc.dt.strftime("%Y-%m-%d")
    return trades.sort_values(["exit_tick_utc", "variant_id", "raw_event_id"], kind="mergesort").reset_index(drop=True)


def family_nonoverlap(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, group in trades.groupby("family_id", sort=False):
        until = pd.Timestamp.min.tz_localize("UTC")
        for row in group.sort_values(["entry_tick_utc", "variant_id"], kind="mergesort").itertuples(index=False):
            if row.entry_tick_utc < until:
                continue
            rows.append(row._asdict())
            until = row.exit_tick_utc
    return pd.DataFrame(rows)


def load_old_atlas(path: Path) -> pd.DataFrame:
    old = pd.read_csv(path)
    old = old[old.variant.astype(str).isin(TARGET_VARIANTS)].copy()
    for column in ["signal_utc", "entry_utc", "exit_utc"]:
        old[column] = pd.to_datetime(old[column], utc=True)
    old["side"] = pd.to_numeric(old.side, errors="raise").astype(int)
    return old.sort_values(["variant", "signal_utc", "side"], kind="mergesort").reset_index(drop=True)


def identity_audit(old: pd.DataFrame, new_events: pd.DataFrame, trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    trade_map = trades.set_index("raw_event_id", drop=False) if len(trades) else pd.DataFrame()
    for variant in TARGET_VARIANTS:
        a = old[old.variant.eq(variant)].copy()
        n = new_events[new_events.variant_id.eq(variant)].copy()
        a["signal_key"] = a.signal_utc.astype(str) + "|" + a.side.astype(str)
        n["signal_key"] = n.signal_utc.astype(str) + "|" + n.side.astype(str)
        a["exact_key"] = a.signal_key + "|" + a.entry_utc.astype(str) + "|" + a.exit_utc.astype(str)
        n["exact_key"] = n.signal_key + "|" + n.entry_boundary_utc.astype(str) + "|" + n.exit_boundary_utc.astype(str)
        old_signal = set(a.signal_key)
        new_signal = set(n.signal_key)
        old_exact = set(a.exact_key)
        new_exact = set(n.exact_key)
        a_by = a.set_index("signal_key", drop=False)
        n_by = n.set_index("signal_key", drop=False)
        boundary_mismatch = 0
        pl_mismatch = 0
        side_mismatch_keys: set[str] = set()
        for key in sorted(old_signal - new_signal):
            row = a_by.loc[key]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            same_time = n[n.signal_utc.eq(row.signal_utc)]
            classification = "SIDE_MISMATCH" if len(same_time) else "OLD_ATLAS_ONLY"
            if len(same_time):
                side_mismatch_keys.add(str(row.signal_utc))
            detail.append({"variant_id": variant, "classification": classification, "year": int(row.signal_utc.year), "signal_utc": row.signal_utc, "side": int(row.side), "old_entry_utc": row.entry_utc, "new_entry_utc": None, "old_exit_utc": row.exit_utc, "new_exit_utc": None, "old_pl_jpy": row.get("normalized_pl_jpy"), "new_pl_jpy": None, "attribution": "CROSS_SOURCE_SIGNAL_OR_SIDE_QUALIFICATION"})
        for key in sorted(new_signal - old_signal):
            row = n_by.loc[key]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            same_time = a[a.signal_utc.eq(row.signal_utc)]
            classification = "SIDE_MISMATCH_NATIVE" if len(same_time) else "DUKASCOPY_ONLY"
            if len(same_time):
                side_mismatch_keys.add(str(row.signal_utc))
            detail.append({"variant_id": variant, "classification": classification, "year": int(row.signal_utc.year), "signal_utc": row.signal_utc, "side": int(row.side), "old_entry_utc": None, "new_entry_utc": row.entry_boundary_utc, "old_exit_utc": None, "new_exit_utc": row.exit_boundary_utc, "old_pl_jpy": None, "new_pl_jpy": None, "attribution": "CROSS_SOURCE_SIGNAL_OR_SIDE_QUALIFICATION"})
        for key in sorted(old_signal & new_signal):
            ao = a_by.loc[key]
            nn = n_by.loc[key]
            if isinstance(ao, pd.DataFrame):
                ao = ao.iloc[0]
            if isinstance(nn, pd.DataFrame):
                nn = nn.iloc[0]
            entry_mismatch = pd.Timestamp(ao.entry_utc) != pd.Timestamp(nn.entry_boundary_utc)
            exit_mismatch = pd.Timestamp(ao.exit_utc) != pd.Timestamp(nn.exit_boundary_utc)
            if entry_mismatch or exit_mismatch:
                boundary_mismatch += 1
                detail.append({"variant_id": variant, "classification": "ENTRY_EXIT_BOUNDARY_MISMATCH", "year": int(ao.signal_utc.year), "signal_utc": ao.signal_utc, "side": int(ao.side), "old_entry_utc": ao.entry_utc, "new_entry_utc": nn.entry_boundary_utc, "old_exit_utc": ao.exit_utc, "new_exit_utc": nn.exit_boundary_utc, "old_pl_jpy": ao.get("normalized_pl_jpy"), "new_pl_jpy": None, "attribution": "OBSERVED_BAR_BOUNDARY_OR_ACTIVE_SUPPRESSION_CHRONOLOGY"})
            if len(trades):
                event_id = nn.raw_event_id
                if event_id in trade_map.index:
                    tr = trade_map.loc[event_id]
                    if isinstance(tr, pd.DataFrame):
                        tr = tr.iloc[0]
                    old_pl = float(ao.get("normalized_pl_jpy", np.nan))
                    if np.isfinite(old_pl) and abs(old_pl - float(tr.realized_pl_jpy)) > TOL:
                        pl_mismatch += 1
                        detail.append({"variant_id": variant, "classification": "P_L_MISMATCH", "year": int(ao.signal_utc.year), "signal_utc": ao.signal_utc, "side": int(ao.side), "old_entry_utc": ao.entry_utc, "new_entry_utc": nn.entry_boundary_utc, "old_exit_utc": ao.exit_utc, "new_exit_utc": nn.exit_boundary_utc, "old_pl_jpy": old_pl, "new_pl_jpy": float(tr.realized_pl_jpy), "attribution": "SOURCE_PRICE_AND_EXECUTABLE_BID_ASK_DIFFERENCE"})
        summary.append({
            "variant_id": variant,
            "family_id": VARIANT_TO_FAMILY[variant],
            "old_atlas_events": len(a),
            "dukascopy_native_events": len(n),
            "common_signal_side_events": len(old_signal & new_signal),
            "exact_common_events": len(old_exact & new_exact),
            "old_atlas_only": len(old_signal - new_signal),
            "dukascopy_only": len(new_signal - old_signal),
            "side_mismatch_timestamps": len(side_mismatch_keys),
            "entry_exit_boundary_mismatch": boundary_mismatch,
            "pl_mismatch": pl_mismatch,
            "signal_side_match_rate_vs_old": len(old_signal & new_signal) / len(old_signal) if old_signal else None,
            "exact_match_rate_vs_old": len(old_exact & new_exact) / len(old_exact) if old_exact else None,
            "old_2023_events": int((a.signal_utc.dt.year == 2023).sum()),
            "new_2023_events": int((n.signal_utc.dt.year == 2023).sum()),
            "old_2024_events": int((a.signal_utc.dt.year == 2024).sum()),
            "new_2024_events": int((n.signal_utc.dt.year == 2024).sum()),
            "identity_is_selection_gate": False,
        })
    return pd.DataFrame(summary), pd.DataFrame(detail)


def bucket_metrics(trades: pd.DataFrame, key: str, expected: list[str] | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    groups = {str(k): g for k, g in trades.groupby(key, dropna=False)}
    keys = expected if expected is not None else sorted(groups)
    for value in keys:
        group = groups.get(str(value), trades.iloc[:0])
        ordered = group.sort_values("exit_tick_utc", kind="mergesort") if len(group) else group
        dd, minimum = realized_drawdown(ordered.realized_pl_jpy if len(group) else [])
        rows.append({
            key: value,
            "trades": len(group),
            "net_jpy": float(group.realized_pl_jpy.sum()) if len(group) else 0.0,
            "gross_profit_jpy": float(group.loc[group.realized_pl_jpy > 0, "realized_pl_jpy"].sum()) if len(group) else 0.0,
            "gross_loss_jpy": float(-group.loc[group.realized_pl_jpy < 0, "realized_pl_jpy"].sum()) if len(group) else 0.0,
            "profit_factor": profit_factor(group.realized_pl_jpy) if len(group) else None,
            "win_rate": float((group.realized_pl_jpy > 0).mean()) if len(group) else None,
            "mean_pl_jpy": float(group.realized_pl_jpy.mean()) if len(group) else None,
            "median_pl_jpy": float(group.realized_pl_jpy.median()) if len(group) else None,
            "realized_mdd_jpy": dd,
            "minimum_realized_equity_jpy": minimum,
            "mean_mae_pips": float(group.mae_pips.mean()) if len(group) else None,
            "mean_mfe_pips": float(group.mfe_pips.mean()) if len(group) else None,
        })
    return pd.DataFrame(rows)


def standalone_metrics(trades: pd.DataFrame, raw_count: int, suppression_count: int) -> dict[str, Any]:
    ordered = trades.sort_values("exit_tick_utc", kind="mergesort")
    dd, minimum = realized_drawdown(ordered.realized_pl_jpy)
    fold = bucket_metrics(trades, "fold", FOLDS)
    month = bucket_metrics(trades, "entry_month", MONTHS)
    side = bucket_metrics(trades, "side_label", ["LONG", "SHORT"])
    session = bucket_metrics(trades, "session")
    year = bucket_metrics(trades, "entry_year", ["2023", "2024"])
    positive_year_net = year.loc[year.net_jpy > 0, "net_jpy"]
    positive_fold_net = fold.loc[fold.net_jpy > 0, "net_jpy"]
    positive_month_net = month.loc[month.net_jpy > 0, "net_jpy"]
    positive_session_net = session.loc[session.net_jpy > 0, "net_jpy"]
    concentration = lambda values: (float(values.max() / values.sum()) if len(values) and values.sum() > TOL else None)
    return {
        "raw_signals": raw_count,
        "suppressed_signals": suppression_count,
        "executable_trades": len(trades),
        "long_trades": int((trades.side > 0).sum()),
        "short_trades": int((trades.side < 0).sum()),
        "net_jpy": float(trades.realized_pl_jpy.sum()),
        "gross_profit_jpy": float(trades.loc[trades.realized_pl_jpy > 0, "realized_pl_jpy"].sum()),
        "gross_loss_jpy": float(-trades.loc[trades.realized_pl_jpy < 0, "realized_pl_jpy"].sum()),
        "profit_factor": profit_factor(trades.realized_pl_jpy),
        "win_rate": float((trades.realized_pl_jpy > 0).mean()),
        "mean_pl_jpy": float(trades.realized_pl_jpy.mean()),
        "median_pl_jpy": float(trades.realized_pl_jpy.median()),
        "realized_mdd_jpy": dd,
        "minimum_realized_equity_jpy": minimum,
        "mean_mae_pips": float(trades.mae_pips.mean()),
        "mean_mfe_pips": float(trades.mfe_pips.mean()),
        "mean_time_to_mae_seconds": float(trades.time_to_mae_seconds.mean()),
        "mean_time_to_mfe_seconds": float(trades.time_to_mfe_seconds.mean()),
        "positive_folds": int((fold.net_jpy > 0).sum()),
        "minimum_fold_jpy": float(fold.net_jpy.min()),
        "positive_months": int((month.net_jpy > 0).sum()),
        "minimum_month_jpy": float(month.net_jpy.min()),
        "positive_sessions": int((session.net_jpy > 0).sum()),
        "year_concentration": concentration(positive_year_net),
        "fold_concentration": concentration(positive_fold_net),
        "month_concentration": concentration(positive_month_net),
        "session_concentration": concentration(positive_session_net),
        "fold_trades": {str(r.fold): int(r.trades) for r in fold.itertuples()},
        "month_trades": {str(r.entry_month): int(r.trades) for r in month.itertuples()},
        "session_trades": {str(r.session): int(r.trades) for r in session.itertuples()},
        "fold_net_jpy": {str(r.fold): float(r.net_jpy) for r in fold.itertuples()},
        "month_net_jpy": {str(r.entry_month): float(r.net_jpy) for r in month.itertuples()},
        "side_net_jpy": {str(r.side_label): float(r.net_jpy) for r in side.itertuples()},
        "session_net_jpy": {str(r.session): float(r.net_jpy) for r in session.itertuples()},
        "year_net_jpy": {str(r.entry_year): float(r.net_jpy) for r in year.itertuples()},
    }


def concentration_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    ordered = trades.realized_pl_jpy.sort_values(ascending=False)
    winners = ordered[ordered > 0]
    top_decile_count = int(math.ceil(len(winners) * 0.10))
    net = float(ordered.sum())
    return {
        "best_event_removed_net_jpy": net - float(ordered.head(1).sum()),
        "top3_winners_removed_net_jpy": net - float(ordered.head(3).sum()),
        "top5_winners_removed_net_jpy": net - float(ordered.head(5).sum()),
        "top10_winners_removed_net_jpy": net - float(ordered.head(10).sum()),
        "top_decile_winner_count": top_decile_count,
        "top_decile_winners_removed_net_jpy": net - float(winners.head(top_decile_count).sum()),
    }


def bootstrap_metrics(trades: pd.DataFrame, reps: int = 5000, seed: int = 41041) -> dict[str, Any]:
    rng = np.random.default_rng(seed)

    def resample(values: np.ndarray) -> dict[str, Any]:
        values = np.asarray(values, dtype=float)
        if len(values) == 0:
            return {"lower_95_jpy": None, "median_jpy": None, "upper_95_jpy": None, "p_non_positive": None}
        sums: list[np.ndarray] = []
        remaining = reps
        while remaining:
            n = min(250, remaining)
            sums.append(rng.choice(values, size=(n, len(values)), replace=True).sum(axis=1))
            remaining -= n
        sample = np.concatenate(sums)
        return {
            "lower_95_jpy": float(np.quantile(sample, 0.025)),
            "median_jpy": float(np.median(sample)),
            "upper_95_jpy": float(np.quantile(sample, 0.975)),
            "p_non_positive": float((sample <= 0).mean()),
        }

    event = trades.realized_pl_jpy.to_numpy()
    date = trades.groupby("entry_date").realized_pl_jpy.sum().to_numpy()
    session_block = trades.groupby(["entry_date", "session"]).realized_pl_jpy.sum().to_numpy()
    return {"reps": reps, "seed": seed, "event": resample(event), "date": resample(date), "session_block": resample(session_block)}


def robustness_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    return {
        "observed_bid_ask_net_jpy": float(trades.realized_pl_jpy.sum()),
        "spread_plus_0_5_pip_net_jpy": float(trades.spread_plus_0_5_pl_jpy.sum()),
        "spread_plus_1_0_pip_net_jpy": float(trades.spread_plus_1_0_pl_jpy.sum()),
        "spread_plus_2_0_pip_net_jpy": float(trades.spread_plus_2_0_pl_jpy.sum()),
        "entry_delay_5s_net_jpy": float(trades.entry_delay_5s_pl_jpy.sum()),
        "entry_delay_15s_net_jpy": float(trades.entry_delay_15s_pl_jpy.sum()),
        "adverse_slippage_0_5_pip_each_execution_net_jpy": float(trades.slippage_0_5_each_pl_jpy.sum()),
        "mean_observed_spread_pips": float(trades.spread_pips.mean()),
        "maximum_entry_execution_delay_seconds": float(trades.entry_exec_delay_seconds.max()),
        "maximum_exit_execution_delay_seconds": float(trades.exit_exec_delay_seconds.max()),
    }


def load_baseline(path: Path) -> pd.DataFrame:
    baseline = pd.read_csv(path)
    baseline.entry_utc = pd.to_datetime(baseline.entry_utc, utc=True)
    baseline.close_utc = pd.to_datetime(baseline.close_utc, utc=True)
    baseline = baseline[baseline.fold.isin(FOLDS)].copy()
    baseline["entry_date"] = baseline.entry_utc.dt.strftime("%Y-%m-%d")
    baseline["entry_month"] = baseline.entry_utc.dt.strftime("%Y-%m")
    if len(baseline) != 1882:
        raise ValueError(f"canonical baseline trade count mismatch: {len(baseline)}")
    return baseline.sort_values(["close_utc", "strategy", "entry_utc"], kind="mergesort").reset_index(drop=True)


def correlation(a: pd.Series, b: pd.Series) -> float:
    if a.std(ddof=0) <= TOL or b.std(ddof=0) <= TOL:
        return 0.0
    value = a.corr(b)
    return 0.0 if not np.isfinite(value) else float(value)


def rolling_window_minimum(series: pd.Series, window: int, business_days: pd.Index) -> tuple[float, str | None, str | None]:
    aligned = series.reindex(business_days, fill_value=0.0)
    rolling = aligned.rolling(window, min_periods=window).sum()
    if rolling.dropna().empty:
        return 0.0, None, None
    end = rolling.idxmin()
    end_position = aligned.index.get_loc(end)
    start = aligned.index[end_position - window + 1]
    return float(rolling.loc[end]), str(start), str(end)


def peak_concurrency(intervals: list[tuple[pd.Timestamp, pd.Timestamp]]) -> int:
    points: list[tuple[pd.Timestamp, int, int]] = []
    for start, end in intervals:
        points.append((start, 1, 1))
        points.append((end, 0, -1))
    current = 0
    peak = 0
    for _, _, delta in sorted(points, key=lambda item: (item[0], item[1])):
        current += delta
        peak = max(peak, current)
    return peak


def portfolio_metrics(baseline: pd.DataFrame, trades: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    index = pd.Index(pd.date_range("2023-01-01", "2024-12-31", tz="UTC").strftime("%Y-%m-%d"))
    aggregate = lambda frame, column, value: frame.groupby(pd.to_datetime(frame[column], utc=True).dt.strftime("%Y-%m-%d"))[value].sum().reindex(index, fill_value=0.0)
    base = aggregate(baseline, "entry_utc", "realized_pl_jpy")
    candidate = aggregate(trades, "entry_tick_utc", "realized_pl_jpy")
    b02 = aggregate(baseline[baseline.strategy.eq("B02")], "entry_utc", "realized_pl_jpy")
    f05 = aggregate(baseline[baseline.strategy.eq("F05")], "entry_utc", "realized_pl_jpy")
    combined_daily = base + candidate
    baseline_events = [(r.close_utc, 0, str(r.strategy), float(r.realized_pl_jpy)) for r in baseline.itertuples()]
    candidate_events = [(r.exit_tick_utc, 1, str(r.raw_event_id), float(r.realized_pl_jpy)) for r in trades.itertuples()]
    baseline_dd, baseline_minimum = realized_drawdown([event[3] for event in sorted(baseline_events)])
    combined_dd, combined_minimum = realized_drawdown([event[3] for event in sorted(baseline_events + candidate_events)])
    business_days = pd.Index(pd.date_range("2023-01-02", "2024-12-31", freq="B", tz="UTC").strftime("%Y-%m-%d"))
    clusters: list[dict[str, Any]] = []
    values: dict[str, tuple[float, str | None, str | None]] = {}
    for label, series in [("baseline", base), ("candidate", candidate), ("combined", combined_daily)]:
        for window in [1, 5, 20]:
            value, start, end = rolling_window_minimum(series, window, business_days)
            values[f"{label}_{window}"] = (value, start, end)
            clusters.append({"series": label, "window_business_days": window, "minimum_jpy": value, "start_date": start, "end_date": end})
    baseline_month = base.groupby(base.index.str[:7]).sum()
    combined_month = combined_daily.groupby(combined_daily.index.str[:7]).sum()
    overlap_rows: list[dict[str, Any]] = []
    same_count = 0
    opposite_count = 0
    simultaneous_count = 0
    for trade in trades.itertuples(index=False):
        overlapping = baseline[(baseline.entry_utc < trade.exit_tick_utc) & (baseline.close_utc > trade.entry_tick_utc)]
        simultaneous = len(overlapping) > 0
        same = bool((overlapping.side.astype(int) == int(trade.side)).any()) if simultaneous else False
        opposite = bool((overlapping.side.astype(int) != int(trade.side)).any()) if simultaneous else False
        same_count += int(same)
        opposite_count += int(opposite)
        simultaneous_count += int(simultaneous)
        overlap_rows.append({"raw_event_id": trade.raw_event_id, "variant_id": trade.variant_id, "entry_tick_utc": trade.entry_tick_utc, "exit_tick_utc": trade.exit_tick_utc, "candidate_side": int(trade.side), "overlapping_baseline_trades": len(overlapping), "same_direction_overlap": same, "opposite_direction_overlap": opposite, "simultaneous_holding": simultaneous})
    baseline_intervals = [(r.entry_utc, r.close_utc) for r in baseline.itertuples()]
    candidate_intervals = [(r.entry_tick_utc, r.exit_tick_utc) for r in trades.itertuples()]
    baseline_peak = peak_concurrency(baseline_intervals)
    candidate_peak = peak_concurrency(candidate_intervals)
    combined_peak = peak_concurrency(baseline_intervals + candidate_intervals)
    result = {
        "baseline_net_jpy": float(baseline.realized_pl_jpy.sum()),
        "candidate_additive_net_jpy": float(trades.realized_pl_jpy.sum()),
        "combined_net_jpy": float(baseline.realized_pl_jpy.sum() + trades.realized_pl_jpy.sum()),
        "daily_correlation_to_B02": correlation(candidate, b02),
        "daily_correlation_to_F05": correlation(candidate, f05),
        "positive_baseline_day_contribution_jpy": float(candidate[base > 0].sum()),
        "negative_baseline_day_contribution_jpy": float(candidate[base < 0].sum()),
        "zero_baseline_day_contribution_jpy": float(candidate[base == 0].sum()),
        "baseline_realized_dd_jpy": baseline_dd,
        "combined_realized_dd_jpy": combined_dd,
        "realized_dd_improvement_jpy": baseline_dd - combined_dd,
        "baseline_minimum_realized_equity_jpy": baseline_minimum,
        "combined_minimum_realized_equity_jpy": combined_minimum,
        "minimum_realized_equity_improvement_jpy": combined_minimum - baseline_minimum,
        "baseline_worst_1_business_day_jpy": values["baseline_1"][0],
        "combined_worst_1_business_day_jpy": values["combined_1"][0],
        "baseline_worst_5_business_day_jpy": values["baseline_5"][0],
        "combined_worst_5_business_day_jpy": values["combined_5"][0],
        "baseline_worst_20_business_day_jpy": values["baseline_20"][0],
        "combined_worst_20_business_day_jpy": values["combined_20"][0],
        "baseline_worst_calendar_month_jpy": float(baseline_month.min()),
        "combined_worst_calendar_month_jpy": float(combined_month.min()),
        "same_direction_overlap_rate": same_count / len(trades) if len(trades) else 0.0,
        "opposite_direction_overlap_rate": opposite_count / len(trades) if len(trades) else 0.0,
        "simultaneous_holding_rate": simultaneous_count / len(trades) if len(trades) else 0.0,
        "baseline_peak_concurrency": baseline_peak,
        "candidate_peak_concurrency": candidate_peak,
        "combined_peak_concurrency": combined_peak,
        "incremental_peak_concurrency": combined_peak - baseline_peak,
        "incremental_margin_proxy_position_units": candidate_peak * POSITION_UNITS,
        "full_equity_status": "NOT_AVAILABLE",
        "full_equity_reason": "Canonical B02/F05 state ledger is M15 Bid-open path evidence from mixed historical lineages and does not provide common-source intrabar executable Bid/Ask equity at every Dukascopy Tick timestamp; combining it with Tick-level candidate floating P/L would not be exact.",
        "combined_full_equity_dd_jpy": None,
        "minimum_full_equity_jpy": None,
        "floating_loss_overlap": None,
        "baseline_trade_outcome_changed": False,
    }
    return result, pd.DataFrame(clusters + overlap_rows)


def post_event_separation(trades: pd.DataFrame) -> dict[str, Any]:
    winners = trades[trades.realized_pl_jpy > 0]
    losers = trades[trades.realized_pl_jpy <= 0]
    result: dict[str, Any] = {}
    for horizon in [15, 30, 60, 120, 240]:
        column = f"return_{horizon}m_pips"
        winner_median = float(winners[column].median()) if len(winners) else None
        loser_median = float(losers[column].median()) if len(losers) else None
        result[f"winner_median_{horizon}m_pips"] = winner_median
        result[f"loser_median_{horizon}m_pips"] = loser_median
        result[f"winner_minus_loser_{horizon}m_pips"] = None if winner_median is None or loser_median is None else winner_median - loser_median
    result["entry_signal_strength_winner_median"] = float(winners.signal_strength.median()) if len(winners) else None
    result["entry_signal_strength_loser_median"] = float(losers.signal_strength.median()) if len(losers) else None
    return result


def build_gate_rows(variant: str, standalone: dict[str, Any], concentration: dict[str, Any], bootstrap: dict[str, Any], robustness: dict[str, Any], portfolio: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    pf = standalone["profit_factor"] or 0.0
    track_a = {
        "executable_trades_ge_120": standalone["executable_trades"] >= 120,
        "net_positive": standalone["net_jpy"] > 0,
        "pf_ge_1_10": pf >= 1.10,
        "positive_folds_ge_3": standalone["positive_folds"] >= 3,
        "minimum_fold_ge_minus_1000": standalone["minimum_fold_jpy"] >= -1000 - TOL,
        "positive_months_ge_16": standalone["positive_months"] >= 16,
        "best_event_removed_positive": concentration["best_event_removed_net_jpy"] > 0,
        "top5_winners_removed_positive": concentration["top5_winners_removed_net_jpy"] > 0,
        "event_bootstrap_p_nonpositive_le_10pct": (bootstrap["event"]["p_non_positive"] or 1.0) <= 0.10,
        "spread_plus_1pip_positive": robustness["spread_plus_1_0_pip_net_jpy"] > 0,
        "entry_delay_5s_positive": robustness["entry_delay_5s_net_jpy"] > 0,
        "additive_portfolio_net_improves": portfolio["combined_net_jpy"] > portfolio["baseline_net_jpy"],
        "combined_realized_dd_non_worse": portfolio["combined_realized_dd_jpy"] <= portfolio["baseline_realized_dd_jpy"] + TOL,
        "worst_20_business_day_non_worse": portfolio["combined_worst_20_business_day_jpy"] >= portfolio["baseline_worst_20_business_day_jpy"] - TOL,
    }
    track_b = {
        "standalone_net_positive": standalone["net_jpy"] > 0,
        "pf_ge_1_00": pf >= 1.00,
        "positive_folds_ge_3": standalone["positive_folds"] >= 3,
        "negative_baseline_day_contribution_positive": portfolio["negative_baseline_day_contribution_jpy"] > 0,
        "additive_net_improves": portfolio["combined_net_jpy"] > portfolio["baseline_net_jpy"],
        "combined_realized_dd_improves": portfolio["combined_realized_dd_jpy"] < portfolio["baseline_realized_dd_jpy"] - TOL,
        "minimum_equity_improves": portfolio["combined_minimum_realized_equity_jpy"] > portfolio["baseline_minimum_realized_equity_jpy"] + TOL,
        "worst_5_business_day_non_worse": portfolio["combined_worst_5_business_day_jpy"] >= portfolio["baseline_worst_5_business_day_jpy"] - TOL,
        "worst_20_business_day_non_worse": portfolio["combined_worst_20_business_day_jpy"] >= portfolio["baseline_worst_20_business_day_jpy"] - TOL,
        "top5_winners_removed_positive": concentration["top5_winners_removed_net_jpy"] > 0,
        "spread_plus_1pip_positive": robustness["spread_plus_1_0_pip_net_jpy"] > 0,
    }
    rows = [{"variant_id": variant, "family_id": VARIANT_TO_FAMILY[variant], "track": track, "gate": gate, "pass": passed} for track, gates in [("A_INDEPENDENT_ALPHA", track_a), ("B_COMPLEMENTARITY", track_b)] for gate, passed in gates.items()]
    return rows, track_a, track_b


def rank_and_shortlist(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    frame = pd.DataFrame(records)
    a = frame.sort_values(["track_a_eligible", "track_a_pass_count", "net_jpy", "profit_factor", "positive_months", "event_bootstrap_p_non_positive"], ascending=[False, False, False, False, False, True], kind="mergesort").reset_index(drop=True)
    a.insert(0, "track_a_rank", range(1, len(a) + 1))
    b = frame.sort_values(["track_b_eligible", "track_b_pass_count", "realized_dd_improvement_jpy", "negative_baseline_day_contribution_jpy", "net_jpy"], ascending=[False, False, False, False, False], kind="mergesort").reset_index(drop=True)
    b.insert(0, "track_b_rank", range(1, len(b) + 1))
    a_choice = a[a.track_a_eligible].head(1)
    b_choice = b[b.track_b_eligible].head(1)
    track_a = None if a_choice.empty else clean(a_choice.iloc[0].to_dict())
    track_b = None if b_choice.empty else clean(b_choice.iloc[0].to_dict())
    shortlisted_variants = {choice["variant_id"] for choice in [track_a, track_b] if choice is not None}
    mechanism_candidates = frame[~frame.variant_id.isin(shortlisted_variants)].copy()
    mechanism_candidates = mechanism_candidates[
        (mechanism_candidates.post_event_15m_separation_pips >= 1.0)
        & (mechanism_candidates.post_event_60m_separation_pips >= 2.0)
        & (mechanism_candidates.negative_baseline_day_contribution_jpy > 0)
        & (mechanism_candidates.max_abs_baseline_correlation <= 0.20)
        & (~mechanism_candidates.track_a_eligible)
        & (~mechanism_candidates.track_b_eligible)
    ]
    mechanism_candidates = mechanism_candidates.sort_values(["negative_baseline_day_contribution_jpy", "post_event_60m_separation_pips", "max_abs_baseline_correlation"], ascending=[False, False, True])
    mechanism = None
    if len(mechanism_candidates):
        row = mechanism_candidates.iloc[0]
        mechanism = clean({
            "family_id": row.family_id,
            "variant_id": row.variant_id,
            "designation": "MECHANISM_RESEARCH_ONLY",
            "post_event_15m_separation_pips": row.post_event_15m_separation_pips,
            "post_event_60m_separation_pips": row.post_event_60m_separation_pips,
            "negative_baseline_day_contribution_jpy": row.negative_baseline_day_contribution_jpy,
            "daily_correlation_to_B02": row.daily_correlation_to_B02,
            "daily_correlation_to_F05": row.daily_correlation_to_F05,
            "direct_candidate_failure": "Failed at least one fixed shortlist gate; no current variant adoption is authorized.",
            "entry_time_distinct_hypothesis": MECHANISM_HYPOTHESES[str(row.variant_id)],
            "overlap_with_hyp028_033_034": False,
        })
    if track_a and track_b:
        decision = "ATLAS_COMPLETE_DUAL_SHORTLIST"
    elif track_a:
        decision = "ATLAS_COMPLETE_INDEPENDENT_ALPHA_SHORTLIST"
    elif track_b:
        decision = "ATLAS_COMPLETE_COMPLEMENTARITY_SHORTLIST"
    elif mechanism:
        decision = "ATLAS_COMPLETE_MECHANISM_RESEARCH_ONLY"
    else:
        decision = "ATLAS_COMPLETE_NO_FAMILY_WORTH_FOLLOWUP"
    shortlist = {
        "decision": decision,
        "track_a": track_a,
        "track_b": track_b,
        "unique_shortlisted_variants": sorted(shortlisted_variants),
        "mechanism_research_only": mechanism,
        "shortlist_count": len(shortlisted_variants),
        "candidate_freeze": False,
        "2020_2022_confirmation_authorized": False,
        "core_mt4_authorized": False,
        "2025_authorized": False,
        "production_authorized": False,
        "live_authorized": False,
    }
    return a, b, shortlist
