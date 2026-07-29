#!/usr/bin/env python3
"""USDJPY-HYP-038 delayed right-tail continuation / loss-decoupling evaluator.

The evaluator is intentionally finite and deterministic. It consumes the immutable
HYP-037 Short ledger, the HYP-037 mechanism feature ledger, source-native 2023-2024
Dukascopy Bid/Ask ticks, and the canonical B02/F05 portfolio authority. It uses only
information observable at entry or at frozen 15/30/60/90/120-minute checkpoints.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from usdjpy_hyp034_bi5_source_v1 import iter_tick_days, m15_bars, source_inventory

HYP = "USDJPY-HYP-038"
FAMILY = "S_SHORT_PULLBACK_DELAYED_CONTINUATION_LOSS_DECOUPLING"
REFERENCE = "C0_HYP037_REFERENCE"
PIP = 0.01
JPY_PER_PIP = 10.0
CAPITAL = 1_000_000.0
TOL = 1e-9
FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]
CHECKPOINTS = [15, 30, 60, 90, 120]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(clean(obj), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_gzip_csv(path: Path, df: pd.DataFrame) -> None:
    raw = df.to_csv(index=False, lineterminator="\n", na_rep="", float_format="%.10f").encode("utf-8")
    with path.open("wb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, compresslevel=9, mtime=0) as zipped:
            zipped.write(raw)


def parse_ts(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], utc=True, format="mixed")
    return df


def profit_factor(values: pd.Series | np.ndarray) -> float | None:
    x = np.asarray(values, dtype=float)
    gross_profit = x[x > 0].sum()
    gross_loss = -x[x < 0].sum()
    return None if gross_loss <= TOL else float(gross_profit / gross_loss)


def realized_curve(values: pd.Series | np.ndarray, initial: float = CAPITAL) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    return np.r_[initial, initial + np.cumsum(x)]


def drawdown(equity: pd.Series | np.ndarray) -> tuple[float, float, int]:
    x = np.asarray(equity, dtype=float)
    if len(x) == 0:
        return 0.0, CAPITAL, 0
    peak = np.maximum.accumulate(x)
    dd = peak - x
    worst = int(np.argmax(dd))
    recovery = 0
    if dd[worst] > 0:
        peak_value = peak[worst]
        future = np.flatnonzero(x[worst:] >= peak_value - TOL)
        recovery = int(future[0]) if len(future) else int(len(x) - worst - 1)
    return float(dd.max()), float(x.min()), recovery


def fold_for_timestamp(ts: pd.Timestamp) -> str:
    year = ts.year
    half = "H1" if ts.month <= 6 else "H2"
    return f"{year}{half}"


def business_window_min(daily: pd.Series, n: int) -> float:
    if daily.empty:
        return 0.0
    start = pd.Timestamp(daily.index.min(), tz="UTC")
    end = pd.Timestamp(daily.index.max(), tz="UTC")
    idx = pd.date_range(start, end, freq="B", tz="UTC").strftime("%Y-%m-%d")
    values = daily.reindex(idx, fill_value=0.0)
    roll = values.rolling(n, min_periods=n).sum()
    return float(roll.min()) if roll.notna().any() else float(values.sum())


def expected_shortfall(values: pd.Series | np.ndarray, alpha: float = 0.05) -> float:
    x = np.sort(np.asarray(values, dtype=float))
    if len(x) == 0:
        return 0.0
    count = max(1, int(math.ceil(len(x) * alpha)))
    return float(x[:count].mean())


def longest_losing_streak(values: pd.Series | np.ndarray) -> int:
    best = current = 0
    for value in np.asarray(values, dtype=float):
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return int(best)


def payoff_skew(values: pd.Series | np.ndarray) -> float:
    s = pd.Series(np.asarray(values, dtype=float))
    return float(s.skew()) if len(s) >= 3 else 0.0


def tail_ratio(values: pd.Series | np.ndarray) -> float | None:
    x = np.asarray(values, dtype=float)
    if len(x) == 0:
        return None
    upper = float(np.quantile(x, 0.95))
    lower = abs(float(np.quantile(x, 0.05)))
    return None if lower <= TOL else upper / lower


@dataclass(frozen=True)
class Variant:
    candidate_id: str
    variant_id: str
    complexity: int
    portability: int
    description: str


VARIANTS: dict[str, list[Variant]] = {
    "C1_ENTRY_TIME_ADMISSION": [
        Variant("C1_ENTRY_TIME_ADMISSION", "C1_E1_SEP_GE_1_5", 1, 3, "admit when separation_atr_ratio >= 1.5"),
        Variant("C1_ENTRY_TIME_ADMISSION", "C1_E2_SEP_GE_2_0", 1, 3, "admit when separation_atr_ratio >= 2.0"),
        Variant("C1_ENTRY_TIME_ADMISSION", "C1_E3_SLOPE_SPREAD", 2, 3, "admit when EMA20 directional slope >=1 pip/4 bars and spread <=2 pips"),
    ],
    "C2_30_MIN_FAILURE_EXIT": [
        Variant("C2_30_MIN_FAILURE_EXIT", "C2_F30_M10", 1, 3, "exit at 30m when current P/L <= -10 pips"),
        Variant("C2_30_MIN_FAILURE_EXIT", "C2_F30_M15", 1, 3, "exit at 30m when current P/L <= -15 pips"),
        Variant("C2_30_MIN_FAILURE_EXIT", "C2_F30_M20", 1, 3, "exit at 30m when current P/L <= -20 pips"),
    ],
    "C3_60_MIN_NO_PROGRESS_EXIT": [
        Variant("C3_60_MIN_NO_PROGRESS_EXIT", "C3_NP60_MFE5_PL0", 2, 3, "exit at 60m when MFE<5 pips and current P/L<=0"),
        Variant("C3_60_MIN_NO_PROGRESS_EXIT", "C3_NP60_MFE10_PL0", 2, 3, "exit at 60m when MFE<10 pips and current P/L<=0"),
        Variant("C3_60_MIN_NO_PROGRESS_EXIT", "C3_NP60_MFE10_PLM5", 2, 3, "exit at 60m when MFE<10 pips and current P/L<=-5"),
    ],
    "C4_CONTINUATION_ALIVE_STATE_MACHINE": [
        Variant("C4_CONTINUATION_ALIVE_STATE_MACHINE", "C4_S1_NEW_LOW", 2, 2, "30/60/90m loss thresholds -20/-10/0 with no new low"),
        Variant("C4_CONTINUATION_ALIVE_STATE_MACHINE", "C4_S2_NEW_LOW", 2, 2, "30/60/90m loss thresholds -25/-15/-5 with no new low"),
        Variant("C4_CONTINUATION_ALIVE_STATE_MACHINE", "C4_S3_EMA_RECROSS", 2, 2, "30/60/90m loss thresholds -20/-10/0 with EMA20 adverse recross"),
    ],
    "C5_PORTFOLIO_LOSS_DECOUPLING": [
        Variant("C5_PORTFOLIO_LOSS_DECOUPLING", "C5_COEXPOSURE_SKIP", 1, 3, "skip entry when B02/F05 has any open position"),
        Variant("C5_PORTFOLIO_LOSS_DECOUPLING", "C5_RECENT_LOSS_SKIP", 1, 3, "skip entry when B02/F05 has a realized loss in prior 24 hours"),
        Variant("C5_PORTFOLIO_LOSS_DECOUPLING", "C5_DD_GE_4000_SKIP", 1, 3, "skip entry when baseline full-equity DD >= JPY 4,000"),
    ],
    "C6_BEST_ADMISSIBLE_COMBINED": [
        Variant("C6_BEST_ADMISSIBLE_COMBINED", "C6_K1_E1_NP60_1", 3, 2, "separation>=1.5 plus 60m MFE<5/current<=0 exit"),
        Variant("C6_BEST_ADMISSIBLE_COMBINED", "C6_K2_E2_S2", 3, 1, "separation>=2.0 plus conservative new-low state machine"),
        Variant("C6_BEST_ADMISSIBLE_COMBINED", "C6_K3_E3_NP60_3", 4, 1, "slope/spread admission plus 60m MFE<10/current<=-5 exit"),
    ],
}


def build_candidate_catalog() -> pd.DataFrame:
    rows = [{
        "candidate_id": REFERENCE,
        "variant_id": REFERENCE,
        "reference_only": True,
        "complexity": 0,
        "portability": 3,
        "description": "unchanged HYP-037 16-bar Short reference; never frozen in HYP-038",
    }]
    for variants in VARIANTS.values():
        for v in variants:
            rows.append({
                "candidate_id": v.candidate_id,
                "variant_id": v.variant_id,
                "reference_only": False,
                "complexity": v.complexity,
                "portability": v.portability,
                "description": v.description,
            })
    return pd.DataFrame(rows)


def baseline_full_equity(baseline_trades: pd.DataFrame, baseline_states: pd.DataFrame) -> pd.DataFrame:
    bt = baseline_trades.copy()
    bs = baseline_states.copy()
    if "trade_id" not in bt.columns:
        bt["trade_id"] = [f"{r.fold}|{r.strategy}|{pd.Timestamp(r.entry_utc)}|{int(r.side)}" for r in bt.itertuples(index=False)]
    close_map = bt.set_index("trade_id")["close_utc"]
    bs["close_utc"] = bs["trade_id"].map(close_map)
    if bs.close_utc.isna().any():
        raise ValueError("baseline state ledger has unresolved trade close timestamps")
    grid = pd.DatetimeIndex(sorted(bs.observation_utc.unique()))
    open_mask = bs.observation_utc < bs.close_utc
    floating = bs[open_mask].groupby("observation_utc").executable_pips.sum().mul(JPY_PER_PIP).reindex(grid, fill_value=0.0)
    closes = bt.groupby("close_utc").realized_pl_jpy.sum().sort_index().cumsum()
    realized = closes.reindex(grid, method="ffill").fillna(0.0)
    equity = CAPITAL + realized + floating
    open_count = bs[open_mask].groupby("observation_utc").trade_id.nunique().reindex(grid, fill_value=0)
    return pd.DataFrame({
        "timestamp_utc": grid,
        "realized_jpy": realized.to_numpy(float),
        "floating_jpy": floating.to_numpy(float),
        "equity_jpy": equity.to_numpy(float),
        "open_count": open_count.to_numpy(int),
    })


def add_baseline_context(shorts: pd.DataFrame, bt: pd.DataFrame, base_eq: pd.DataFrame) -> pd.DataFrame:
    out = shorts.copy()
    bt = bt.sort_values("entry_utc").copy()
    grid = pd.DatetimeIndex(base_eq.timestamp_utc)
    eq = base_eq.equity_jpy.to_numpy(float)
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    grid_ns = grid.view("i8")
    contexts: list[dict[str, Any]] = []
    for row in out.itertuples(index=False):
        t = pd.Timestamp(row.entry_tick_utc)
        pos = np.searchsorted(grid_ns, t.value, side="right") - 1
        pos = max(0, min(pos, len(grid_ns) - 1))
        open_now = bt[(bt.entry_utc <= t) & (bt.close_utc > t)]
        recent = bt[(bt.close_utc < t) & (bt.close_utc >= t - pd.Timedelta(hours=24))]
        contexts.append({
            "baseline_full_equity_at_entry_jpy": float(eq[pos]),
            "baseline_full_equity_dd_at_entry_jpy": float(dd[pos]),
            "baseline_open_count_at_entry": int(len(open_now)),
            "baseline_same_direction_open_count": int((open_now.side.astype(float) < 0).sum()) if "side" in open_now else 0,
            "baseline_recent_24h_loss_count": int((recent.realized_pl_jpy < 0).sum()),
            "baseline_recent_24h_realized_jpy": float(recent.realized_pl_jpy.sum()),
        })
    return pd.concat([out.reset_index(drop=True), pd.DataFrame(contexts)], axis=1)


def stream_tick_features(shorts: pd.DataFrame, raw_dirs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    records = shorts[["trade_id", "entry_tick_utc", "exit_tick_utc", "entry_bid"]].copy()
    records["entry_ns"] = records.entry_tick_utc.astype("int64")
    records["exit_ns"] = records.exit_tick_utc.astype("int64")
    state: dict[str, dict[str, Any]] = {}
    for row in records.itertuples(index=False):
        per_cp = {}
        for minute in CHECKPOINTS:
            per_cp[minute] = {
                "target_ns": int(row.entry_ns + minute * 60 * 1_000_000_000),
                "resolved": False,
                "tick_ns": None,
                "bid": None,
                "ask": None,
                "min_ask": math.inf,
                "max_ask": -math.inf,
                "min_bid": math.inf,
                "max_bid": -math.inf,
                "tick_count": 0,
                "last5_tick_count": 0,
            }
        state[row.trade_id] = {"entry_ns": int(row.entry_ns), "exit_ns": int(row.exit_ns), "entry_bid": float(row.entry_bid), "cp": per_cp}

    bars: list[pd.DataFrame] = []
    day_count = 0
    tick_count = 0
    for day in iter_tick_days(raw_dirs):
        day_count += 1
        tick_count += len(day.timestamp_ns)
        bar = m15_bars(day)
        if len(bar):
            bars.append(bar)
        if day.empty:
            continue
        day_lo = int(day.timestamp_ns[0])
        day_hi = int(day.timestamp_ns[-1])
        overlapping = records[(records.entry_ns <= day_hi) & (records.exit_ns >= day_lo)]
        for row in overlapping.itertuples(index=False):
            st = state[row.trade_id]
            for minute, cp in st["cp"].items():
                segment_end = min(cp["target_ns"], st["exit_ns"], day_hi)
                segment_start = max(st["entry_ns"], day_lo)
                if segment_end >= segment_start:
                    lo = int(np.searchsorted(day.timestamp_ns, segment_start, side="left"))
                    hi = int(np.searchsorted(day.timestamp_ns, segment_end, side="right"))
                    if hi > lo:
                        asks = day.ask[lo:hi]
                        bids = day.bid[lo:hi]
                        cp["min_ask"] = min(cp["min_ask"], float(np.min(asks)))
                        cp["max_ask"] = max(cp["max_ask"], float(np.max(asks)))
                        cp["min_bid"] = min(cp["min_bid"], float(np.min(bids)))
                        cp["max_bid"] = max(cp["max_bid"], float(np.max(bids)))
                        cp["tick_count"] += int(hi - lo)
                if not cp["resolved"] and cp["target_ns"] <= day_hi and cp["target_ns"] <= st["exit_ns"]:
                    pos = int(np.searchsorted(day.timestamp_ns, max(cp["target_ns"], day_lo), side="left"))
                    if pos < len(day.timestamp_ns) and int(day.timestamp_ns[pos]) <= st["exit_ns"]:
                        cp["resolved"] = True
                        cp["tick_ns"] = int(day.timestamp_ns[pos])
                        cp["bid"] = float(day.bid[pos])
                        cp["ask"] = float(day.ask[pos])
                        last5 = cp["target_ns"] - 5 * 60 * 1_000_000_000
                        lo5 = int(np.searchsorted(day.timestamp_ns, last5, side="left"))
                        cp["last5_tick_count"] = int(max(0, pos - lo5 + 1))

    if not bars:
        raise ValueError("no M15 bars reconstructed from raw authority")
    m15 = pd.concat(bars, ignore_index=True).drop_duplicates("bar_start_utc", keep="first").sort_values("bar_start_utc").reset_index(drop=True)
    m15["bar_start_utc"] = pd.to_datetime(m15.bar_start_utc, utc=True)
    prev_close = m15.bid_close.shift(1)
    tr = pd.concat([(m15.bid_high - m15.bid_low), (m15.bid_high - prev_close).abs(), (m15.bid_low - prev_close).abs()], axis=1).max(axis=1)
    m15["atr14"] = tr.rolling(14, min_periods=14).mean()
    m15["ema20"] = m15.bid_close.ewm(span=20, adjust=False).mean()
    m15["recent_swing_low_8"] = m15.bid_low.shift(1).rolling(8, min_periods=1).min()
    m15["recent_swing_high_8"] = m15.bid_high.shift(1).rolling(8, min_periods=1).max()

    feature_rows: list[dict[str, Any]] = []
    bar_ns = pd.DatetimeIndex(m15.bar_start_utc).view("i8")
    for row in records.itertuples(index=False):
        st = state[row.trade_id]
        entry_bar_pos = np.searchsorted(bar_ns, int(row.entry_ns), side="left") - 1
        entry_bar_pos = max(0, entry_bar_pos)
        swing_low = float(m15.iloc[entry_bar_pos].recent_swing_low_8)
        for minute in CHECKPOINTS:
            cp = st["cp"][minute]
            cp_ts = pd.Timestamp(cp["tick_ns"], tz="UTC") if cp["tick_ns"] is not None else pd.NaT
            bar_pos = np.searchsorted(bar_ns, cp["target_ns"], side="left") - 1
            bar_pos = max(0, min(bar_pos, len(m15) - 1))
            bar_row = m15.iloc[bar_pos]
            if cp["resolved"]:
                current_pl = (st["entry_bid"] - cp["ask"]) / PIP
                mfe = (st["entry_bid"] - cp["min_ask"]) / PIP if cp["min_ask"] < math.inf else np.nan
                mae = (st["entry_bid"] - cp["max_ask"]) / PIP if cp["max_ask"] > -math.inf else np.nan
                new_low = bool(cp["min_bid"] < swing_low - TOL) if np.isfinite(swing_low) else False
                ema20_recross = bool(cp["ask"] > float(bar_row.ema20))
                range_pips = (cp["max_bid"] - cp["min_bid"]) / PIP if cp["max_bid"] > -math.inf else np.nan
                vol_ratio = range_pips / (float(bar_row.atr14) / PIP) if np.isfinite(bar_row.atr14) and bar_row.atr14 > 0 else np.nan
                close_loc = (float(bar_row.bid_close) - float(bar_row.bid_low)) / max(float(bar_row.bid_high - bar_row.bid_low), TOL)
                velocity = cp["last5_tick_count"] / 300.0
            else:
                current_pl = mfe = mae = range_pips = vol_ratio = close_loc = velocity = np.nan
                new_low = ema20_recross = False
            feature_rows.append({
                "trade_id": row.trade_id,
                "checkpoint_minute": minute,
                "checkpoint_target_utc": pd.Timestamp(cp["target_ns"], tz="UTC"),
                "checkpoint_tick_utc": cp_ts,
                "checkpoint_resolved": bool(cp["resolved"]),
                "checkpoint_bid": cp["bid"],
                "checkpoint_ask": cp["ask"],
                "current_pl_pips": current_pl,
                "realized_favorable_excursion_pips": mfe,
                "realized_adverse_excursion_pips": mae,
                "new_low_formed": new_low,
                "ema20_adverse_recross": ema20_recross,
                "tick_velocity_last5_per_second": velocity,
                "directional_close_location": 1.0 - close_loc if np.isfinite(close_loc) else np.nan,
                "volatility_expansion_atr": vol_ratio,
                "realized_range_pips": range_pips,
                "tick_count_since_entry": int(cp["tick_count"]),
                "pre_entry_recent_swing_low": swing_low,
            })
    checkpoint = pd.DataFrame(feature_rows)
    audit = {
        "tick_days": day_count,
        "ticks_streamed": tick_count,
        "m15_bars": len(m15),
        "checkpoint_rows": len(checkpoint),
        "unresolved_checkpoints": int((~checkpoint.checkpoint_resolved).sum()),
    }
    return checkpoint, m15, audit


def checkpoint_wide(checkpoint: pd.DataFrame) -> pd.DataFrame:
    value_columns = [
        "checkpoint_tick_utc", "checkpoint_resolved", "checkpoint_bid", "checkpoint_ask", "current_pl_pips",
        "realized_favorable_excursion_pips", "realized_adverse_excursion_pips", "new_low_formed",
        "ema20_adverse_recross", "tick_velocity_last5_per_second", "directional_close_location",
        "volatility_expansion_atr", "realized_range_pips", "tick_count_since_entry",
    ]
    frames = []
    for minute in CHECKPOINTS:
        part = checkpoint[checkpoint.checkpoint_minute.eq(minute)][["trade_id"] + value_columns].copy()
        part = part.rename(columns={c: f"{c}_{minute}m" for c in value_columns})
        frames.append(part.set_index("trade_id"))
    return pd.concat(frames, axis=1).reset_index()


def apply_variant(base: pd.DataFrame, variant_id: str) -> pd.DataFrame:
    out = base.copy()
    out["admitted"] = True
    out["candidate_exit_tick_utc"] = out.exit_tick_utc
    out["candidate_exit_ask"] = out.exit_ask.astype(float)
    out["exit_checkpoint_minute"] = 240
    out["transition_reason"] = "REFERENCE_HOLD_240M"

    def skip(mask: pd.Series, reason: str) -> None:
        out.loc[mask, "admitted"] = False
        out.loc[mask, "candidate_exit_tick_utc"] = pd.NaT
        out.loc[mask, "candidate_exit_ask"] = np.nan
        out.loc[mask, "exit_checkpoint_minute"] = 0
        out.loc[mask, "transition_reason"] = reason

    def early_exit(mask: pd.Series, minute: int, reason: str) -> None:
        active = mask & out.admitted & out[f"checkpoint_resolved_{minute}m"].astype(bool)
        out.loc[active, "candidate_exit_tick_utc"] = out.loc[active, f"checkpoint_tick_utc_{minute}m"]
        out.loc[active, "candidate_exit_ask"] = out.loc[active, f"checkpoint_ask_{minute}m"].astype(float)
        out.loc[active, "exit_checkpoint_minute"] = minute
        out.loc[active, "transition_reason"] = reason

    if variant_id == REFERENCE:
        pass
    elif variant_id == "C1_E1_SEP_GE_1_5":
        skip(out.separation_atr_ratio < 1.5, "ENTRY_REJECT_SEPARATION_LT_1_5")
    elif variant_id == "C1_E2_SEP_GE_2_0":
        skip(out.separation_atr_ratio < 2.0, "ENTRY_REJECT_SEPARATION_LT_2_0")
    elif variant_id == "C1_E3_SLOPE_SPREAD":
        skip((out.ema20_slope_4bar_pips_directional < 1.0) | (out.first_executable_spread_pips > 2.0), "ENTRY_REJECT_SLOPE_OR_SPREAD")
    elif variant_id.startswith("C2_F30_"):
        threshold = {"C2_F30_M10": -10.0, "C2_F30_M15": -15.0, "C2_F30_M20": -20.0}[variant_id]
        early_exit(out.current_pl_pips_30m <= threshold, 30, f"EXIT_30M_PL_LE_{threshold:g}")
    elif variant_id.startswith("C3_NP60_"):
        params = {
            "C3_NP60_MFE5_PL0": (5.0, 0.0),
            "C3_NP60_MFE10_PL0": (10.0, 0.0),
            "C3_NP60_MFE10_PLM5": (10.0, -5.0),
        }[variant_id]
        early_exit((out.realized_favorable_excursion_pips_60m < params[0]) & (out.current_pl_pips_60m <= params[1]), 60, "EXIT_60M_NO_PROGRESS")
    elif variant_id in {"C4_S1_NEW_LOW", "C4_S2_NEW_LOW", "C4_S3_EMA_RECROSS"}:
        thresholds = (-20.0, -10.0, 0.0) if variant_id != "C4_S2_NEW_LOW" else (-25.0, -15.0, -5.0)
        for minute, threshold in zip([30, 60, 90], thresholds):
            still_reference = out.exit_checkpoint_minute.eq(240)
            discriminator = out[f"ema20_adverse_recross_{minute}m"].astype(bool) if variant_id == "C4_S3_EMA_RECROSS" else ~out[f"new_low_formed_{minute}m"].astype(bool)
            early_exit(still_reference & (out[f"current_pl_pips_{minute}m"] <= threshold) & discriminator, minute, f"STATE_DEAD_{minute}M")
    elif variant_id == "C5_COEXPOSURE_SKIP":
        skip(out.baseline_open_count_at_entry >= 1, "ENTRY_REJECT_BASELINE_COEXPOSURE")
    elif variant_id == "C5_RECENT_LOSS_SKIP":
        skip(out.baseline_recent_24h_loss_count >= 1, "ENTRY_REJECT_RECENT_BASELINE_LOSS")
    elif variant_id == "C5_DD_GE_4000_SKIP":
        skip(out.baseline_full_equity_dd_at_entry_jpy >= 4000.0, "ENTRY_REJECT_BASELINE_DD_GE_4000")
    elif variant_id == "C6_K1_E1_NP60_1":
        skip(out.separation_atr_ratio < 1.5, "ENTRY_REJECT_SEPARATION_LT_1_5")
        early_exit((out.realized_favorable_excursion_pips_60m < 5.0) & (out.current_pl_pips_60m <= 0.0), 60, "EXIT_60M_NO_PROGRESS")
    elif variant_id == "C6_K2_E2_S2":
        skip(out.separation_atr_ratio < 2.0, "ENTRY_REJECT_SEPARATION_LT_2_0")
        for minute, threshold in zip([30, 60, 90], [-25.0, -15.0, -5.0]):
            still_reference = out.exit_checkpoint_minute.eq(240)
            early_exit(still_reference & (out[f"current_pl_pips_{minute}m"] <= threshold) & (~out[f"new_low_formed_{minute}m"].astype(bool)), minute, f"STATE_DEAD_{minute}M")
    elif variant_id == "C6_K3_E3_NP60_3":
        skip((out.ema20_slope_4bar_pips_directional < 1.0) | (out.first_executable_spread_pips > 2.0), "ENTRY_REJECT_SLOPE_OR_SPREAD")
        early_exit((out.realized_favorable_excursion_pips_60m < 10.0) & (out.current_pl_pips_60m <= -5.0), 60, "EXIT_60M_NO_PROGRESS")
    else:
        raise KeyError(f"unknown variant {variant_id}")

    out["candidate_pl_jpy"] = np.where(out.admitted, (out.entry_bid.astype(float) - out.candidate_exit_ask.astype(float)) / PIP * JPY_PER_PIP, 0.0)
    out["candidate_spread_plus_1_pl_jpy"] = np.where(out.admitted, out.candidate_pl_jpy - 1.0 * JPY_PER_PIP, 0.0)
    out["candidate_slippage_0_5_each_pl_jpy"] = np.where(out.admitted, out.candidate_pl_jpy - 1.0 * JPY_PER_PIP, 0.0)
    out["candidate_entry_delay_15s_pl_jpy"] = np.where(out.admitted, (out.e15_bid.astype(float) - out.candidate_exit_ask.astype(float)) / PIP * JPY_PER_PIP, 0.0)
    out["candidate_id"] = next((v.candidate_id for variants in VARIANTS.values() for v in variants if v.variant_id == variant_id), REFERENCE)
    out["variant_id"] = variant_id
    return out


def standalone_metrics(candidate: pd.DataFrame, pl_col: str = "candidate_pl_jpy") -> dict[str, Any]:
    d = candidate.sort_values("candidate_exit_tick_utc", na_position="last").copy()
    pl = d[pl_col].astype(float)
    active = d.admitted.astype(bool)
    active_pl = pl[active]
    eq = realized_curve(active_pl)
    mdd, min_eq, recovery = drawdown(eq)
    fold = d.groupby("fold")[pl_col].agg(["count", "sum"])
    month = d.groupby(d.entry_tick_utc.dt.strftime("%Y-%m"))[pl_col].agg(["count", "sum"])
    session = d.groupby("session")[pl_col].agg(["count", "sum"])
    return {
        "reference_population": int(len(d)),
        "admitted_trades": int(active.sum()),
        "net_jpy": float(pl.sum()),
        "profit_factor": profit_factor(active_pl),
        "win_rate": float((active_pl > 0).mean()) if len(active_pl) else 0.0,
        "median_pl_jpy": float(active_pl.median()) if len(active_pl) else 0.0,
        "mdd_jpy": mdd,
        "minimum_equity_jpy": min_eq,
        "recovery_event_count": recovery,
        "positive_folds": int((fold["sum"] > 0).sum()),
        "minimum_fold_net_jpy": float(fold["sum"].min()),
        "positive_months": int((month["sum"] > 0).sum()),
        "fold_results": fold.to_dict("index"),
        "month_results": month.to_dict("index"),
        "session_results": session.to_dict("index"),
        "tail_ratio": tail_ratio(active_pl),
        "payoff_skewness": payoff_skew(active_pl),
        "expected_shortfall_5pct_jpy": expected_shortfall(active_pl),
        "longest_losing_streak": longest_losing_streak(active_pl),
        "p90_jpy": float(np.quantile(active_pl, 0.90)) if len(active_pl) else 0.0,
        "p95_jpy": float(np.quantile(active_pl, 0.95)) if len(active_pl) else 0.0,
        "p99_jpy": float(np.quantile(active_pl, 0.99)) if len(active_pl) else 0.0,
        "upper_tail_mean_jpy": float(active_pl[active_pl >= np.quantile(active_pl, 0.90)].mean()) if len(active_pl) else 0.0,
    }


def concentration_metrics(candidate: pd.DataFrame) -> dict[str, Any]:
    pl = candidate.candidate_pl_jpy.astype(float)
    ordered = pl.sort_values(ascending=False)
    winners = ordered[ordered > 0]
    n = int(math.ceil(len(winners) * 0.10))
    net = float(pl.sum())
    fold = candidate.groupby("fold").candidate_pl_jpy.sum()
    month = candidate.groupby(candidate.entry_tick_utc.dt.strftime("%Y-%m")).candidate_pl_jpy.sum()
    session = candidate.groupby("session").candidate_pl_jpy.sum()

    def share(series: pd.Series) -> float | None:
        positive = series[series > 0]
        return None if positive.empty else float(positive.max() / positive.sum())

    return {
        "best_event_removed_net_jpy": float(net - ordered.head(1).sum()),
        "top3_removed_net_jpy": float(net - ordered.head(3).sum()),
        "top5_removed_net_jpy": float(net - ordered.head(5).sum()),
        "top_decile_winners_removed_net_jpy": float(net - winners.head(n).sum()),
        "top_decile_winner_count": n,
        "largest_positive_fold_share": share(fold),
        "largest_positive_month_share": share(month),
        "largest_positive_session_share": share(session),
    }


def bootstrap_metrics(candidate: pd.DataFrame, reps: int = 10000, seed: int = 38038) -> dict[str, Any]:
    rng = np.random.default_rng(seed)

    def boot(values: np.ndarray) -> dict[str, float]:
        chunks = []
        for start in range(0, reps, 500):
            size = min(500, reps - start)
            chunks.append(rng.choice(values, size=(size, len(values)), replace=True).sum(axis=1))
        z = np.concatenate(chunks)
        return {
            "lower_95_jpy": float(np.quantile(z, 0.025)),
            "median_jpy": float(np.median(z)),
            "p_nonpositive": float((z <= 0).mean()),
        }

    event = candidate.candidate_pl_jpy.to_numpy(float)
    date = candidate.groupby(candidate.entry_tick_utc.dt.strftime("%Y-%m-%d")).candidate_pl_jpy.sum().to_numpy(float)
    block = candidate.groupby([candidate.entry_tick_utc.dt.strftime("%Y-%m-%d"), candidate.session]).candidate_pl_jpy.sum().to_numpy(float)
    return {"replicates": reps, "seed": seed, "event": boot(event), "date": boot(date), "session_block": boot(block)}


def right_tail_audit(reference: pd.DataFrame, candidate: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    ref = reference[["trade_id", "realized_pl_jpy", "time_to_mfe_seconds", "exit_tick_utc", "entry_tick_utc"]].copy()
    cand = candidate[["trade_id", "candidate_pl_jpy", "admitted", "candidate_exit_tick_utc", "transition_reason"]].copy()
    merged = ref.merge(cand, on="trade_id", how="left", validate="one_to_one")
    merged["reference_rank"] = merged.realized_pl_jpy.rank(method="first", ascending=False).astype(int)
    merged["reference_winner"] = merged.realized_pl_jpy > 0
    merged["candidate_preserved_50pct"] = merged.admitted & (merged.candidate_pl_jpy >= 0.5 * merged.realized_pl_jpy.clip(lower=0))
    merged["avoided_loss_jpy"] = np.where(merged.realized_pl_jpy < 0, (-merged.realized_pl_jpy) - np.maximum(-merged.candidate_pl_jpy, 0), 0.0)
    merged["sacrificed_profit_jpy"] = np.where(merged.realized_pl_jpy > 0, merged.realized_pl_jpy - np.maximum(merged.candidate_pl_jpy, 0), 0.0)
    top25 = merged.nsmallest(25, "reference_rank")
    top5 = merged.nsmallest(5, "reference_rank")
    winner_count = int((merged.realized_pl_jpy > 0).sum())
    top_decile_count = int(math.ceil(winner_count * 0.10))
    top_decile = merged[merged.reference_winner].nsmallest(top_decile_count, "reference_rank")
    ref_gross_profit = float(merged.loc[merged.realized_pl_jpy > 0, "realized_pl_jpy"].sum())
    cand_gross_profit_on_ref_winners = float(np.maximum(merged.loc[merged.realized_pl_jpy > 0, "candidate_pl_jpy"], 0).sum())
    top5_ref = float(top5.realized_pl_jpy.sum())
    top5_cand = float(np.maximum(top5.candidate_pl_jpy, 0).sum())
    top_decile_ref = float(top_decile.realized_pl_jpy.sum())
    top_decile_cand = float(np.maximum(top_decile.candidate_pl_jpy, 0).sum())
    avoided = float(merged.avoided_loss_jpy.sum())
    sacrificed = float(merged.sacrificed_profit_jpy.sum())
    reference_loss = float(-merged.loc[merged.realized_pl_jpy < 0, "realized_pl_jpy"].sum())
    result = {
        "reference_top25_preserved_count": int(top25.candidate_preserved_50pct.sum()),
        "reference_top25_preserved_rate": float(top25.candidate_preserved_50pct.mean()),
        "top5_winner_pl_retention": None if top5_ref <= TOL else top5_cand / top5_ref,
        "top_decile_gross_profit_retention": None if top_decile_ref <= TOL else top_decile_cand / top_decile_ref,
        "overall_profit_retention_ratio": None if ref_gross_profit <= TOL else cand_gross_profit_on_ref_winners / ref_gross_profit,
        "avoided_loss_jpy": avoided,
        "sacrificed_profit_jpy": sacrificed,
        "net_benefit_jpy": avoided - sacrificed,
        "loss_rejection_ratio": None if reference_loss <= TOL else avoided / reference_loss,
        "winner_mean_reference_hold_minutes": float(((merged.loc[merged.reference_winner, "exit_tick_utc"] - merged.loc[merged.reference_winner, "entry_tick_utc"]).dt.total_seconds() / 60).mean()),
        "winner_mean_mfe_arrival_minutes": float((merged.loc[merged.reference_winner, "time_to_mfe_seconds"] / 60).mean()),
        "deleted_or_early_reference_winners": int(((merged.reference_winner) & ((~merged.admitted) | (merged.candidate_exit_tick_utc < merged.exit_tick_utc))).sum()),
        "deleted_or_early_reference_losers": int(((~merged.reference_winner) & ((~merged.admitted) | (merged.candidate_exit_tick_utc < merged.exit_tick_utc))).sum()),
    }
    result["right_tail_pass"] = bool(
        (result["top5_winner_pl_retention"] or 0) >= 0.90
        and (result["top_decile_gross_profit_retention"] or 0) >= 0.80
        and avoided > sacrificed + TOL
        and result["reference_top25_preserved_count"] >= 13
    )
    return result, merged.sort_values("reference_rank")


def candidate_on_grid(candidate: pd.DataFrame, grid: pd.DatetimeIndex, ask_series: pd.Series) -> pd.DataFrame:
    out = pd.DataFrame({"timestamp_utc": grid})
    out["realized_jpy"] = 0.0
    out["floating_jpy"] = 0.0
    out["open_count"] = 0
    active = candidate[candidate.admitted].copy()
    closes = active.groupby("candidate_exit_tick_utc").candidate_pl_jpy.sum().sort_index().cumsum()
    out["realized_jpy"] = closes.reindex(grid, method="ffill").fillna(0.0).to_numpy(float)
    ask_idx = ask_series.index.view("i8")
    ask_val = ask_series.to_numpy(float)
    grid_ns = grid.view("i8")
    floating = np.zeros(len(grid), dtype=float)
    open_count = np.zeros(len(grid), dtype=int)
    for row in active.itertuples(index=False):
        lo = int(np.searchsorted(grid_ns, pd.Timestamp(row.entry_tick_utc).value, side="left"))
        hi = int(np.searchsorted(grid_ns, pd.Timestamp(row.candidate_exit_tick_utc).value, side="left"))
        if lo >= hi:
            continue
        ts = grid_ns[lo:hi]
        positions = np.searchsorted(ask_idx, ts, side="left")
        valid = positions < len(ask_idx)
        values = np.zeros(len(ts), dtype=float)
        values[valid] = (float(row.entry_bid) - ask_val[positions[valid]]) / PIP * JPY_PER_PIP
        floating[lo:hi] += values
        open_count[lo:hi] += valid.astype(int)
    out["floating_jpy"] = floating
    out["open_count"] = open_count
    out["equity_jpy"] = CAPITAL + out.realized_jpy + out.floating_jpy
    return out


def portfolio_metrics(bt: pd.DataFrame, base_eq: pd.DataFrame, candidate: pd.DataFrame, m15: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    grid = pd.DatetimeIndex(base_eq.timestamp_utc)
    asks = pd.Series(m15.ask_open.to_numpy(float), index=pd.DatetimeIndex(m15.bar_start_utc)).sort_index()
    cand_eq = candidate_on_grid(candidate, grid, asks)
    combined = base_eq.copy()
    combined["candidate_realized_jpy"] = cand_eq.realized_jpy
    combined["candidate_floating_jpy"] = cand_eq.floating_jpy
    combined["equity_jpy"] = base_eq.equity_jpy + cand_eq.realized_jpy + cand_eq.floating_jpy
    combined["open_count"] = base_eq.open_count + cand_eq.open_count
    bdd, bmin, brecovery = drawdown(base_eq.equity_jpy)
    cdd, cmin, crecovery = drawdown(combined.equity_jpy)

    bevents = bt[["close_utc", "realized_pl_jpy"]].rename(columns={"close_utc": "t"})
    cevents = candidate[candidate.admitted][["candidate_exit_tick_utc", "candidate_pl_jpy"]].rename(columns={"candidate_exit_tick_utc": "t", "candidate_pl_jpy": "realized_pl_jpy"})
    brdd, brmin, _ = drawdown(realized_curve(bevents.sort_values("t").realized_pl_jpy))
    crdd, crmin, _ = drawdown(realized_curve(pd.concat([bevents, cevents]).sort_values("t").realized_pl_jpy))

    dates = sorted(set(bt.entry_utc.dt.strftime("%Y-%m-%d")) | set(candidate.entry_tick_utc.dt.strftime("%Y-%m-%d")))
    bd = bt.groupby(bt.entry_utc.dt.strftime("%Y-%m-%d")).realized_pl_jpy.sum().reindex(dates, fill_value=0.0)
    cd = candidate.groupby(candidate.entry_tick_utc.dt.strftime("%Y-%m-%d")).candidate_pl_jpy.sum().reindex(dates, fill_value=0.0)
    b02 = bt[bt.strategy.eq("B02")].groupby(bt[bt.strategy.eq("B02")].entry_utc.dt.strftime("%Y-%m-%d")).realized_pl_jpy.sum().reindex(dates, fill_value=0.0)
    f05 = bt[bt.strategy.eq("F05")].groupby(bt[bt.strategy.eq("F05")].entry_utc.dt.strftime("%Y-%m-%d")).realized_pl_jpy.sum().reindex(dates, fill_value=0.0)
    weekly_index = pd.to_datetime(pd.Index(dates), utc=True).to_period("W").astype(str)
    cd_week = cd.groupby(weekly_index).sum()
    b02_week = b02.groupby(weekly_index).sum()
    f05_week = f05.groupby(weekly_index).sum()

    def corr(a: pd.Series, b: pd.Series) -> float:
        return 0.0 if a.std() <= TOL or b.std() <= TOL else float(a.corr(b))

    base_dd_series = np.maximum.accumulate(base_eq.equity_jpy.to_numpy(float)) - base_eq.equity_jpy.to_numpy(float)
    baseline_dd_mask = base_dd_series > 0
    candidate_contribution_during_dd = float((cand_eq.realized_jpy.diff().fillna(cand_eq.realized_jpy.iloc[0]) + cand_eq.floating_jpy.diff().fillna(cand_eq.floating_jpy.iloc[0]))[baseline_dd_mask].sum())

    grid_ns = grid.view("i8")
    candidate_margin = np.zeros(len(grid), dtype=float)
    base_margin = np.zeros(len(grid), dtype=float)
    for row in candidate[candidate.admitted].itertuples(index=False):
        lo = int(np.searchsorted(grid_ns, pd.Timestamp(row.entry_tick_utc).value, side="left"))
        hi = int(np.searchsorted(grid_ns, pd.Timestamp(row.candidate_exit_tick_utc).value, side="left"))
        candidate_margin[lo:hi] += abs(1000.0 * float(row.entry_bid)) / 25.0
    for row in bt.itertuples(index=False):
        lo = int(np.searchsorted(grid_ns, pd.Timestamp(row.entry_utc).value, side="left"))
        hi = int(np.searchsorted(grid_ns, pd.Timestamp(row.close_utc).value, side="left"))
        base_margin[lo:hi] += abs(1000.0 * float(row.entry_bid)) / 25.0
    total_margin = base_margin + candidate_margin
    valid = total_margin > 0
    min_margin_level = float(np.min(combined.equity_jpy.to_numpy(float)[valid] / total_margin[valid] * 100.0)) if valid.any() else None

    def session_label(ts: pd.Timestamp) -> str:
        hour = pd.Timestamp(ts).hour
        if hour < 7:
            return "ASIA"
        if hour < 13:
            return "LONDON"
        if hour < 20:
            return "NEW_YORK"
        return "TRANSITION"

    same_direction = 0
    opposite_direction = 0
    same_session = 0
    same_hour = 0
    realized_loss_cluster_overlap = 0
    for row in candidate[candidate.admitted].itertuples(index=False):
        overlaps = bt[(bt.entry_utc < row.candidate_exit_tick_utc) & (bt.close_utc > row.entry_tick_utc)]
        same_direction += int((overlaps.side.astype(float) < 0).sum()) if "side" in overlaps else 0
        opposite_direction += int((overlaps.side.astype(float) > 0).sum()) if "side" in overlaps else 0
        if "session" in overlaps.columns:
            same_session += int(overlaps.session.astype(str).eq(str(row.session)).sum())
        else:
            same_session += int(overlaps.entry_utc.map(session_label).eq(session_label(pd.Timestamp(row.entry_tick_utc))).sum())
        same_hour += int((overlaps.entry_utc.dt.floor("h") == pd.Timestamp(row.entry_tick_utc).floor("h")).sum())
        prior_losses = bt[(bt.close_utc < row.entry_tick_utc) & (bt.close_utc >= row.entry_tick_utc - pd.Timedelta(hours=6)) & (bt.realized_pl_jpy < 0)]
        realized_loss_cluster_overlap += int(len(prior_losses) > 0)

    baseline_month = bd.groupby(pd.Index(dates).str[:7]).sum()
    combined_month = (bd + cd).groupby(pd.Index(dates).str[:7]).sum()
    result = {
        "baseline_net_jpy": float(bt.realized_pl_jpy.sum()),
        "candidate_net_jpy": float(candidate.candidate_pl_jpy.sum()),
        "combined_net_jpy": float(bt.realized_pl_jpy.sum() + candidate.candidate_pl_jpy.sum()),
        "baseline_realized_dd_jpy": brdd,
        "combined_realized_dd_jpy": crdd,
        "baseline_minimum_realized_equity_jpy": brmin,
        "combined_minimum_realized_equity_jpy": crmin,
        "baseline_full_equity_dd_jpy": bdd,
        "combined_full_equity_dd_jpy": cdd,
        "baseline_minimum_full_equity_jpy": bmin,
        "combined_minimum_full_equity_jpy": cmin,
        "baseline_recovery_grid_points": brecovery,
        "combined_recovery_grid_points": crecovery,
        "baseline_worst_1_business_day_jpy": float(bd.min()),
        "combined_worst_1_business_day_jpy": float((bd + cd).min()),
        "baseline_worst_5_business_day_jpy": business_window_min(bd, 5),
        "combined_worst_5_business_day_jpy": business_window_min(bd + cd, 5),
        "baseline_worst_20_business_day_jpy": business_window_min(bd, 20),
        "combined_worst_20_business_day_jpy": business_window_min(bd + cd, 20),
        "baseline_worst_calendar_month_jpy": float(baseline_month.min()),
        "combined_worst_calendar_month_jpy": float(combined_month.min()),
        "daily_correlation_to_B02": corr(cd, b02),
        "daily_correlation_to_F05": corr(cd, f05),
        "weekly_correlation_to_B02": corr(cd_week, b02_week),
        "weekly_correlation_to_F05": corr(cd_week, f05_week),
        "negative_baseline_day_candidate_contribution_jpy": float(cd[bd < 0].sum()),
        "baseline_dd_candidate_contribution_jpy": candidate_contribution_during_dd,
        "same_direction_concurrency_count": same_direction,
        "opposite_direction_concurrency_count": opposite_direction,
        "same_session_overlap_count": same_session,
        "same_hour_overlap_count": same_hour,
        "realized_loss_cluster_overlap_count": realized_loss_cluster_overlap,
        "candidate_peak_concurrency": int(cand_eq.open_count.max()),
        "baseline_peak_concurrency": int(base_eq.open_count.max()),
        "combined_peak_concurrency": int(combined.open_count.max()),
        "incremental_margin_jpy_max": float(candidate_margin.max()),
        "minimum_margin_level_percent": min_margin_level,
        "chronology_mismatch": int((candidate.loc[candidate.admitted, "candidate_exit_tick_utc"] < candidate.loc[candidate.admitted, "entry_tick_utc"]).sum()),
        "currency_mismatch": 0,
        "full_equity_grid_points": int(len(grid)),
    }
    return result, combined


def hard_gate_rows(stand: dict[str, Any], concentration: dict[str, Any], execution: dict[str, Any], portfolio: dict[str, Any], right_tail: dict[str, Any], integrity: dict[str, Any], training: bool = False) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(stage: str, gate: str, value: Any, threshold: Any, passed: bool) -> None:
        rows.append({"stage": stage, "gate": gate, "value": value, "threshold": threshold, "pass": bool(passed)})

    required_positive_folds = 2 if training else 3
    add("INTEGRITY", "source_integrity", integrity.get("source_integrity", False), True, integrity.get("source_integrity", False))
    add("INTEGRITY", "lookahead_violation_zero", integrity.get("lookahead_violation", 0), 0, integrity.get("lookahead_violation", 0) == 0)
    add("INTEGRITY", "chronology_mismatch_zero", portfolio.get("chronology_mismatch", 0), 0, portfolio.get("chronology_mismatch", 0) == 0)
    add("INTEGRITY", "currency_mismatch_zero", portfolio.get("currency_mismatch", 0), 0, portfolio.get("currency_mismatch", 0) == 0)
    add("INTEGRITY", "duplicate_unresolved_zero", integrity.get("duplicates", 0) + integrity.get("unresolved", 0), 0, integrity.get("duplicates", 0) + integrity.get("unresolved", 0) == 0)
    add("STANDALONE", "observed_bid_ask_net_positive", stand["net_jpy"], 0, stand["net_jpy"] > 0)
    add("STANDALONE", "pf_ge_1_10", stand["profit_factor"], 1.10, (stand["profit_factor"] or 0) >= 1.10)
    add("STANDALONE", "positive_folds", stand["positive_folds"], required_positive_folds, stand["positive_folds"] >= required_positive_folds)
    add("STANDALONE", "minimum_fold_net", stand["minimum_fold_net_jpy"], -1500, stand["minimum_fold_net_jpy"] >= -1500)
    add("CONCENTRATION", "top5_removed_net_positive", concentration["top5_removed_net_jpy"], 0, concentration["top5_removed_net_jpy"] > 0)
    add("EXECUTION", "spread_plus_1_net_positive", execution["spread_plus_1_net_jpy"], 0, execution["spread_plus_1_net_jpy"] > 0)
    add("EXECUTION", "entry_delay_15s_net_positive", execution["entry_delay_15s_net_jpy"], 0, execution["entry_delay_15s_net_jpy"] > 0)
    add("EXECUTION", "slippage_0_5_each_net_positive", execution["slippage_0_5_each_net_jpy"], 0, execution["slippage_0_5_each_net_jpy"] > 0)
    add("PORTFOLIO", "combined_net_above_baseline", portfolio["combined_net_jpy"], portfolio["baseline_net_jpy"], portfolio["combined_net_jpy"] > portfolio["baseline_net_jpy"])
    add("PORTFOLIO", "realized_dd_nonworse", portfolio["combined_realized_dd_jpy"], portfolio["baseline_realized_dd_jpy"], portfolio["combined_realized_dd_jpy"] <= portfolio["baseline_realized_dd_jpy"] + TOL)
    add("PORTFOLIO", "full_equity_dd_nonworse", portfolio["combined_full_equity_dd_jpy"], portfolio["baseline_full_equity_dd_jpy"], portfolio["combined_full_equity_dd_jpy"] <= portfolio["baseline_full_equity_dd_jpy"] + TOL)
    add("PORTFOLIO", "minimum_full_equity_nonworse", portfolio["combined_minimum_full_equity_jpy"], portfolio["baseline_minimum_full_equity_jpy"], portfolio["combined_minimum_full_equity_jpy"] >= portfolio["baseline_minimum_full_equity_jpy"] - TOL)
    add("PORTFOLIO", "worst_5_business_day_nonworse", portfolio["combined_worst_5_business_day_jpy"], portfolio["baseline_worst_5_business_day_jpy"], portfolio["combined_worst_5_business_day_jpy"] >= portfolio["baseline_worst_5_business_day_jpy"] - TOL)
    add("PORTFOLIO", "worst_20_business_day_nonworse", portfolio["combined_worst_20_business_day_jpy"], portfolio["baseline_worst_20_business_day_jpy"], portfolio["combined_worst_20_business_day_jpy"] >= portfolio["baseline_worst_20_business_day_jpy"] - TOL)
    add("PORTFOLIO", "worst_month_nonworse", portfolio["combined_worst_calendar_month_jpy"], portfolio["baseline_worst_calendar_month_jpy"], portfolio["combined_worst_calendar_month_jpy"] >= portfolio["baseline_worst_calendar_month_jpy"] - TOL)
    add("PORTFOLIO", "negative_baseline_day_contribution_nonnegative", portfolio["negative_baseline_day_candidate_contribution_jpy"], 0, portfolio["negative_baseline_day_candidate_contribution_jpy"] >= 0)
    add("PORTFOLIO", "margin_concurrency_pass", min(portfolio["minimum_margin_level_percent"] or 0, 999999), 500, (portfolio["minimum_margin_level_percent"] or 0) >= 500 and portfolio["candidate_peak_concurrency"] <= 1)
    add("RIGHT_TAIL", "top5_winner_retention", right_tail["top5_winner_pl_retention"], 0.90, (right_tail["top5_winner_pl_retention"] or 0) >= 0.90)
    add("RIGHT_TAIL", "top_decile_profit_retention", right_tail["top_decile_gross_profit_retention"], 0.80, (right_tail["top_decile_gross_profit_retention"] or 0) >= 0.80)
    add("RIGHT_TAIL", "avoided_loss_gt_sacrificed_profit", right_tail["net_benefit_jpy"], 0, right_tail["net_benefit_jpy"] > 0)
    add("RIGHT_TAIL", "top25_majority_preserved", right_tail["reference_top25_preserved_count"], 13, right_tail["reference_top25_preserved_count"] >= 13)
    return pd.DataFrame(rows)


def execution_metrics(candidate: pd.DataFrame) -> dict[str, float]:
    return {
        "observed_net_jpy": float(candidate.candidate_pl_jpy.sum()),
        "spread_plus_1_net_jpy": float(candidate.candidate_spread_plus_1_pl_jpy.sum()),
        "entry_delay_15s_net_jpy": float(candidate.candidate_entry_delay_15s_pl_jpy.sum()),
        "slippage_0_5_each_net_jpy": float(candidate.candidate_slippage_0_5_each_pl_jpy.sum()),
    }


def evaluate_variant(base: pd.DataFrame, variant: Variant | None, bt: pd.DataFrame, base_eq: pd.DataFrame, m15: pd.DataFrame, integrity: dict[str, Any], training: bool = False) -> dict[str, Any]:
    variant_id = REFERENCE if variant is None else variant.variant_id
    cand = apply_variant(base, variant_id)
    stand = standalone_metrics(cand)
    conc = concentration_metrics(cand)
    execution = execution_metrics(cand)
    portfolio, combined_eq = portfolio_metrics(bt, base_eq, cand, m15)
    reference = apply_variant(base, REFERENCE)
    right_tail, tail_ledger = right_tail_audit(reference, cand)
    gates = hard_gate_rows(stand, conc, execution, portfolio, right_tail, integrity, training=training)
    return {
        "variant_id": variant_id,
        "candidate_id": REFERENCE if variant is None else variant.candidate_id,
        "complexity": 0 if variant is None else variant.complexity,
        "portability": 3 if variant is None else variant.portability,
        "candidate": cand,
        "standalone": stand,
        "concentration": conc,
        "execution": execution,
        "portfolio": portfolio,
        "right_tail": right_tail,
        "right_tail_ledger": tail_ledger,
        "gates": gates,
        "hard_pass": bool(gates["pass"].all()),
        "combined_equity": combined_eq,
    }


def ranking_key(result: dict[str, Any]) -> tuple[Any, ...]:
    p = result["portfolio"]
    s = result["standalone"]
    return (
        int(result["hard_pass"]),
        p["negative_baseline_day_candidate_contribution_jpy"],
        -p["combined_full_equity_dd_jpy"],
        p["combined_worst_5_business_day_jpy"],
        p["combined_net_jpy"],
        s["profit_factor"] or 0,
        -result["complexity"],
        result["portability"],
    )


def subset_authorities(base: pd.DataFrame, bt: pd.DataFrame, base_eq: pd.DataFrame, m15: pd.DataFrame, folds: set[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cand = base[base.fold.isin(folds)].copy()
    btr = bt[bt.fold.isin(folds)].copy() if "fold" in bt.columns else bt[bt.entry_utc.map(fold_for_timestamp).isin(folds)].copy()
    start = min(cand.entry_tick_utc.min(), btr.entry_utc.min())
    end = max(cand.exit_tick_utc.max(), btr.close_utc.max())
    eq = base_eq[(base_eq.timestamp_utc >= start) & (base_eq.timestamp_utc <= end)].copy()
    # Rebase realized/equity to retain drawdown shape within the fold subset.
    if not eq.empty:
        realized0 = float(eq.realized_jpy.iloc[0])
        eq["realized_jpy"] = eq.realized_jpy - realized0
        eq["equity_jpy"] = CAPITAL + eq.realized_jpy + eq.floating_jpy
    bars = m15[(m15.bar_start_utc >= start.floor("D") - pd.Timedelta(days=5)) & (m15.bar_start_utc <= end.ceil("D") + pd.Timedelta(days=1))].copy()
    return cand, btr, eq, bars


def cross_fit(base: pd.DataFrame, bt: pd.DataFrame, base_eq: pd.DataFrame, m15: pd.DataFrame, integrity: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    selection_rows: list[dict[str, Any]] = []
    oof_rows: list[pd.DataFrame] = []
    family_results: dict[str, Any] = {}
    for family_id, variants in VARIANTS.items():
        selected_ids: list[str] = []
        family_oof: list[pd.DataFrame] = []
        for holdout in FOLDS:
            train_folds = set(FOLDS) - {holdout}
            train_base, train_bt, train_eq, train_m15 = subset_authorities(base, bt, base_eq, m15, train_folds)
            scored = []
            for variant in variants:
                result = evaluate_variant(train_base, variant, train_bt, train_eq, train_m15, integrity, training=True)
                scored.append(result)
                selection_rows.append({
                    "candidate_id": family_id,
                    "holdout_fold": holdout,
                    "train_folds": ",".join(sorted(train_folds)),
                    "variant_id": variant.variant_id,
                    "training_hard_pass": result["hard_pass"],
                    "training_gate_pass_count": int(result["gates"]["pass"].sum()),
                    "training_gate_count": int(len(result["gates"])),
                    "training_net_jpy": result["standalone"]["net_jpy"],
                    "training_pf": result["standalone"]["profit_factor"],
                    "training_negative_day_contribution_jpy": result["portfolio"]["negative_baseline_day_candidate_contribution_jpy"],
                    "training_full_equity_dd_jpy": result["portfolio"]["combined_full_equity_dd_jpy"],
                    "training_worst_5d_jpy": result["portfolio"]["combined_worst_5_business_day_jpy"],
                    "complexity": variant.complexity,
                    "portability": variant.portability,
                })
            selected = max(scored, key=ranking_key)
            selected_ids.append(selected["variant_id"])
            holdout_base = base[base.fold.eq(holdout)].copy()
            holdout_variant = next(v for v in variants if v.variant_id == selected["variant_id"])
            holdout_applied = apply_variant(holdout_base, holdout_variant.variant_id)
            holdout_applied["oof_selected_variant"] = holdout_variant.variant_id
            family_oof.append(holdout_applied)
            selection_rows.append({
                "candidate_id": family_id,
                "holdout_fold": holdout,
                "train_folds": ",".join(sorted(train_folds)),
                "variant_id": holdout_variant.variant_id,
                "selected_for_holdout": True,
                "training_hard_pass": selected["hard_pass"],
                "training_gate_pass_count": int(selected["gates"]["pass"].sum()),
                "training_gate_count": int(len(selected["gates"])),
                "training_net_jpy": selected["standalone"]["net_jpy"],
                "training_pf": selected["standalone"]["profit_factor"],
                "training_negative_day_contribution_jpy": selected["portfolio"]["negative_baseline_day_candidate_contribution_jpy"],
                "training_full_equity_dd_jpy": selected["portfolio"]["combined_full_equity_dd_jpy"],
                "training_worst_5d_jpy": selected["portfolio"]["combined_worst_5_business_day_jpy"],
                "complexity": selected["complexity"],
                "portability": selected["portability"],
            })
        oof = pd.concat(family_oof, ignore_index=True).sort_values("entry_tick_utc")
        oof_result = evaluate_variant_from_applied(base, oof, bt, base_eq, m15, integrity)
        counts = Counter(selected_ids)
        max_count = max(counts.values())
        modal_candidates = [variant_id for variant_id, count in counts.items() if count == max_count]
        modal_variant = min((v for v in variants if v.variant_id in modal_candidates), key=lambda v: (v.complexity, -v.portability, v.variant_id))
        full_result = evaluate_variant(base, modal_variant, bt, base_eq, m15, integrity, training=False)
        family_results[family_id] = {
            "selected_variants_by_holdout": dict(zip(FOLDS, selected_ids)),
            "modal_exact_variant": modal_variant.variant_id,
            "oof": oof_result,
            "full": full_result,
            "candidate_freeze_eligible": bool(oof_result["hard_pass"] and full_result["hard_pass"]),
        }
        oof["candidate_id"] = family_id
        oof_rows.append(oof)
    return pd.DataFrame(selection_rows), pd.concat(oof_rows, ignore_index=True), family_results


def evaluate_variant_from_applied(reference_base: pd.DataFrame, applied: pd.DataFrame, bt: pd.DataFrame, base_eq: pd.DataFrame, m15: pd.DataFrame, integrity: dict[str, Any]) -> dict[str, Any]:
    stand = standalone_metrics(applied)
    conc = concentration_metrics(applied)
    execution = execution_metrics(applied)
    portfolio, combined_eq = portfolio_metrics(bt, base_eq, applied, m15)
    reference = apply_variant(reference_base, REFERENCE)
    right_tail, tail_ledger = right_tail_audit(reference, applied)
    gates = hard_gate_rows(stand, conc, execution, portfolio, right_tail, integrity, training=False)
    return {
        "variant_id": "OOF_CROSSFIT",
        "candidate_id": str(applied.candidate_id.iloc[0]) if "candidate_id" in applied.columns and len(applied) else "OOF",
        "complexity": 0,
        "portability": 0,
        "candidate": applied,
        "standalone": stand,
        "concentration": conc,
        "execution": execution,
        "portfolio": portfolio,
        "right_tail": right_tail,
        "right_tail_ledger": tail_ledger,
        "gates": gates,
        "hard_pass": bool(gates["pass"].all()),
        "combined_equity": combined_eq,
    }


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "variant_id": result["variant_id"],
        "hard_pass": result["hard_pass"],
        "standalone": result["standalone"],
        "concentration": result["concentration"],
        "execution": result["execution"],
        "portfolio": result["portfolio"],
        "right_tail": result["right_tail"],
        "failed_gates": result["gates"].loc[~result["gates"]["pass"], ["stage", "gate", "value", "threshold"]].to_dict("records"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hyp037-ledger", type=Path, required=True)
    parser.add_argument("--entry-features", type=Path, required=True)
    parser.add_argument("--baseline-trades", type=Path, required=True)
    parser.add_argument("--baseline-states", type=Path, required=True)
    parser.add_argument("--raw-2023", type=Path, required=True)
    parser.add_argument("--raw-2024", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--startup-receipt", type=Path, required=True)
    parser.add_argument("--duplicate-audit", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--research-sha", required=True)
    parser.add_argument("--core-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    prereg = json.loads(args.prereg.read_text(encoding="utf-8"))
    startup = json.loads(args.startup_receipt.read_text(encoding="utf-8"))
    duplicate = json.loads(args.duplicate_audit.read_text(encoding="utf-8"))
    source_manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    assert prereg["hypothesis_id"] == HYP
    assert prereg["candidate_catalog"]["maximum_nonreference_candidates"] == 6
    assert prereg["period_roles"]["2025"] == "UNSEEN_EXTERNAL_VALIDATION_LOCKED"
    assert startup["base_is_current"] is True
    assert duplicate["new_hypothesis_is_not_hyp037_reopening"] is True
    assert source_manifest["2025_accessed"] is False

    required_paths = [args.hyp037_ledger, args.entry_features, args.baseline_trades, args.baseline_states]
    raw_count = len(list(args.raw_2023.glob("*.tar.gz"))) + len(list(args.raw_2024.glob("*.tar.gz")))
    preflight = {
        "schema_version": "usdjpy_hyp038_preflight_receipt_v1",
        "hypothesis_id": HYP,
        "research_sha": args.research_sha,
        "core_sha": args.core_sha,
        "inputs_exist": all(path.exists() for path in required_paths),
        "raw_archive_count": raw_count,
        "candidate_catalog_size": sum(len(v) for v in VARIANTS.values()),
        "2020_2022_accessed": False,
        "2025_accessed": False,
        "outcomes_authorized": not args.preflight_only,
    }
    preflight["pass"] = bool(preflight["inputs_exist"] and raw_count == 24 and preflight["candidate_catalog_size"] == 18)
    write_json(args.out_dir / "preflight_receipt.json", preflight)
    if args.preflight_only:
        print(json.dumps(clean(preflight), indent=2))
        return 0 if preflight["pass"] else 2
    if not preflight["pass"]:
        raise RuntimeError("preflight failed")

    reference = pd.read_csv(args.hyp037_ledger)
    parse_ts(reference, ["signal_utc", "decision_utc", "entry_tick_utc", "exit_tick_utc", "e15_tick_utc"])
    if len(reference) != 500 or not reference.side_label.eq("SHORT").all():
        raise ValueError("HYP-037 Short reference identity mismatch")
    features = pd.read_csv(args.entry_features)
    features = features[features.side_label.eq("SHORT")].copy()
    if len(features) != 500:
        raise ValueError("mechanism feature Short identity mismatch")
    feature_cols = [c for c in features.columns if c not in {"side_label", "fold", "session"}]
    base = reference.merge(features[feature_cols], on="trade_id", how="left", validate="one_to_one")
    required_feature_columns = [
        "separation_atr_ratio", "ema20_slope_4bar_pips_directional",
        "first_executable_spread_pips", "time_to_mfe_minutes",
    ]
    if base[required_feature_columns].isna().any(axis=1).any():
        raise ValueError("entry feature join unresolved")

    bt = pd.read_csv(args.baseline_trades)
    bs = pd.read_csv(args.baseline_states)
    parse_ts(bt, ["signal_utc", "entry_utc", "close_utc"])
    parse_ts(bs, ["observation_utc"])
    if "fold" not in bt.columns:
        bt["fold"] = bt.entry_utc.map(fold_for_timestamp)
    base_eq = baseline_full_equity(bt, bs)
    base = add_baseline_context(base, bt, base_eq)

    checkpoint_long, m15, tick_audit = stream_tick_features(base, [args.raw_2023, args.raw_2024])
    if tick_audit["unresolved_checkpoints"] != 0:
        raise ValueError(f"unresolved checkpoints: {tick_audit['unresolved_checkpoints']}")
    wide = checkpoint_wide(checkpoint_long)
    base = base.merge(wide, on="trade_id", how="left", validate="one_to_one")

    integrity = {
        "source_integrity": True,
        "lookahead_violation": int((checkpoint_long.checkpoint_tick_utc < checkpoint_long.checkpoint_target_utc).sum()),
        "duplicates": int(base.trade_id.duplicated().sum()),
        "unresolved": int((~checkpoint_long.checkpoint_resolved).sum()),
        "chronology": int((base.entry_tick_utc < base.decision_utc).sum()),
    }
    if integrity["chronology"] != 0:
        raise ValueError("entry chronology mismatch")

    catalog = build_candidate_catalog()
    catalog.to_csv(args.out_dir / "finite_candidate_catalog.csv", index=False)
    checkpoint_long.to_csv(args.out_dir / "checkpoint_feature_catalog.csv", index=False)
    base[["trade_id", "fold"]].assign(oof_holdout_fold=base.fold).to_csv(args.out_dir / "oof_fold_assignments.csv", index=False)

    reference_result = evaluate_variant(base, None, bt, base_eq, m15, integrity)
    selection, oof_ledger, family_results = cross_fit(base, bt, base_eq, m15, integrity)
    selection.to_csv(args.out_dir / "oof_selection_ledger.csv", index=False)
    write_gzip_csv(args.out_dir / "lifecycle_transition_ledger.csv.gz", oof_ledger)

    comparison_rows = []
    gate_frames = []
    right_tail_rows = []
    for family_id, bundle in family_results.items():
        for scope in ["OOF", "FULL_EXACT"]:
            result = bundle["oof"] if scope == "OOF" else bundle["full"]
            s = result["standalone"]
            p = result["portfolio"]
            r = result["right_tail"]
            comparison_rows.append({
                "candidate_id": family_id,
                "scope": scope,
                "exact_variant": bundle["modal_exact_variant"],
                "hard_pass": result["hard_pass"],
                "candidate_freeze_eligible": bundle["candidate_freeze_eligible"],
                "admitted_trades": s["admitted_trades"],
                "net_jpy": s["net_jpy"],
                "pf": s["profit_factor"],
                "positive_folds": s["positive_folds"],
                "minimum_fold_net_jpy": s["minimum_fold_net_jpy"],
                "negative_baseline_day_contribution_jpy": p["negative_baseline_day_candidate_contribution_jpy"],
                "combined_full_equity_dd_jpy": p["combined_full_equity_dd_jpy"],
                "combined_worst_5d_jpy": p["combined_worst_5_business_day_jpy"],
                "combined_worst_20d_jpy": p["combined_worst_20_business_day_jpy"],
                "combined_worst_month_jpy": p["combined_worst_calendar_month_jpy"],
                "top5_retention": r["top5_winner_pl_retention"],
                "top_decile_retention": r["top_decile_gross_profit_retention"],
                "avoided_loss_jpy": r["avoided_loss_jpy"],
                "sacrificed_profit_jpy": r["sacrificed_profit_jpy"],
                "right_tail_pass": r["right_tail_pass"],
            })
            gates = result["gates"].copy()
            gates.insert(0, "scope", scope)
            gates.insert(0, "candidate_id", family_id)
            gate_frames.append(gates)
            right_tail_rows.append({"candidate_id": family_id, "scope": scope, **r})
    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(args.out_dir / "candidate_comparison.csv", index=False)
    pd.concat(gate_frames, ignore_index=True).to_csv(args.out_dir / "candidate_gate_matrix.csv", index=False)
    pd.DataFrame(right_tail_rows).to_csv(args.out_dir / "right_tail_preservation_audit.csv", index=False)

    eligible = [
        (family_id, bundle)
        for family_id, bundle in family_results.items()
        if bundle["candidate_freeze_eligible"]
    ]
    if eligible:
        selected_family, selected_bundle = max(eligible, key=lambda item: ranking_key(item[1]["oof"]))
        decision = "RESEARCH_CANDIDATE_FREEZE_AUTHORIZED"
        candidate_freeze = True
    else:
        selected_family, selected_bundle = max(family_results.items(), key=lambda item: ranking_key(item[1]["oof"]))
        candidate_freeze = False
        reference_portfolio = reference_result["portfolio"]
        improvements = []
        for family_id, bundle in family_results.items():
            oof = bundle["oof"]
            p = oof["portfolio"]
            r = oof["right_tail"]
            improvements.append(
                r["right_tail_pass"]
                and p["negative_baseline_day_candidate_contribution_jpy"] > reference_portfolio["negative_baseline_day_candidate_contribution_jpy"]
                and p["combined_worst_5_business_day_jpy"] >= reference_portfolio["combined_worst_5_business_day_jpy"]
            )
        decision = "MECHANISM_CONFIRMED_NO_DEPLOYABLE_LOSS_DECOUPLING_RULE" if any(improvements) else "NO_PORTABLE_DELAYED_CONTINUATION_CANDIDATE"

    selected_oof = selected_bundle["oof"]
    selected_full = selected_bundle["full"]
    selected_full["combined_equity"].to_csv(args.out_dir / "selected_full_equity_replay.csv", index=False)
    selected_full["right_tail_ledger"].to_csv(args.out_dir / "selected_right_tail_event_audit.csv", index=False)

    diagnostics = {}
    portfolio_audit = {}
    execution_audit = {}
    for family_id, bundle in family_results.items():
        diagnostics[family_id] = {
            "oof_concentration": bundle["oof"]["concentration"],
            "oof_bootstrap": bootstrap_metrics(bundle["oof"]["candidate"]),
            "full_concentration": bundle["full"]["concentration"],
            "full_bootstrap": bootstrap_metrics(bundle["full"]["candidate"]),
        }
        portfolio_audit[family_id] = {"oof": bundle["oof"]["portfolio"], "full_exact": bundle["full"]["portfolio"]}
        execution_audit[family_id] = {"oof": bundle["oof"]["execution"], "full_exact": bundle["full"]["execution"]}
    write_json(args.out_dir / "concentration_bootstrap_diagnostics.json", diagnostics)
    write_json(args.out_dir / "portfolio_loss_decoupling_audit.json", portfolio_audit)
    write_json(args.out_dir / "execution_robustness.json", execution_audit)
    write_json(args.out_dir / "right_tail_preservation_audit.json", {row["candidate_id"] + ":" + row["scope"]: row for row in right_tail_rows})
    write_json(args.out_dir / "source_native_tick_audit.json", tick_audit)
    write_json(args.out_dir / "source_manifest_runtime.json", {
        "schema_version": "usdjpy_hyp038_source_manifest_runtime_v1",
        "hypothesis_id": HYP,
        "research_sha": args.research_sha,
        "core_sha": args.core_sha,
        "hyp037_ledger_sha256": sha256_file(args.hyp037_ledger),
        "entry_features_sha256": sha256_file(args.entry_features),
        "baseline_trades_sha256": sha256_file(args.baseline_trades),
        "baseline_states_sha256": sha256_file(args.baseline_states),
        "raw_source_inventory": source_inventory([args.raw_2023, args.raw_2024]),
        "2020_2022_accessed": False,
        "2025_accessed": False,
    })

    final_result = {
        "schema_version": "usdjpy_hyp038_final_result_v1",
        "hypothesis_id": HYP,
        "family_id": FAMILY,
        "status": "COMPLETE_RESEARCH_DECISION" if not candidate_freeze else "RESEARCH_PASS_PENDING_CORE_MT4",
        "decision": decision,
        "research_start_sha": startup["research_main_sha"],
        "research_execution_sha": args.research_sha,
        "core_start_sha": startup["core_main_sha"],
        "core_end_sha": args.core_sha,
        "run_id": args.run_id,
        "hyp037_relationship": "INDEPENDENT_SUCCESSOR; HYP-037 FAIL_2023_2024_RESEARCH_CANDIDATE_GATE_NO_RETUNING unchanged",
        "period_access": {"2020_2022": False, "2023_2024": True, "2025H1": False, "2025H2": False},
        "reference": compact_result(reference_result),
        "selected_candidate_family": selected_family,
        "selected_exact_variant": selected_bundle["modal_exact_variant"],
        "selected_oof": compact_result(selected_oof),
        "selected_full_exact": compact_result(selected_full),
        "candidate_freeze_authorized": candidate_freeze,
        "core_mt4_authorized": candidate_freeze,
        "production_authorized": False,
        "live_authorized": False,
        "all_candidates": {
            family_id: {
                "selected_variants_by_holdout": bundle["selected_variants_by_holdout"],
                "modal_exact_variant": bundle["modal_exact_variant"],
                "candidate_freeze_eligible": bundle["candidate_freeze_eligible"],
                "oof": compact_result(bundle["oof"]),
                "full_exact": compact_result(bundle["full"]),
            }
            for family_id, bundle in family_results.items()
        },
        "atlas_comparison_status": "DEFERRED_UNTIL_REMAINING_FAMILY_ATLAS_CANONICAL_RESULT_AVAILABLE",
        "technical_failure": False,
    }
    write_json(args.out_dir / "final_result.json", final_result)
    write_json(args.out_dir / "candidate_registry.json", {
        "schema_version": "usdjpy_hyp038_candidate_registry_v1",
        "hypothesis_id": HYP,
        "family_id": FAMILY,
        "decision": decision,
        "selected_candidate_family": selected_family,
        "selected_exact_variant": selected_bundle["modal_exact_variant"],
        "candidate_freeze_authorized": candidate_freeze,
        "core_mt4_authorized": candidate_freeze,
        "2025H1_authorized": False,
        "2025H2_authorized": False,
        "production_authorized": False,
        "live_authorized": False,
    })
    write_json(args.out_dir / "period_access_receipt.json", {
        "schema_version": "usdjpy_hyp038_period_access_receipt_v1",
        "hypothesis_id": HYP,
        "2020_2022_role": "NONBINDING_ANALYSIS_NOT_USED",
        "2020_2022_accessed": False,
        "2023_2024_research_accessed": True,
        "2025H1_accessed": False,
        "2025H2_accessed": False,
        "candidate_freeze_authorized": candidate_freeze,
        "next_protected_period_action": "CORE_MT4_PARITY_BEFORE_2025H1" if candidate_freeze else "NONE_RESEARCH_CLOSED",
    })

    selected = compact_result(selected_oof)
    report = f"""# USDJPY-HYP-038 Delayed Right-Tail Continuation Result v1

Decision: `{decision}`

HYP-037 remains closed as `FAIL_2023_2024_RESEARCH_CANDIDATE_GATE_NO_RETUNING`; this is an independent successor using its mechanism evidence only.

The finite catalog contained six non-reference candidate families and 18 fixed variants. Each family used four leave-one-half-year-out selections and concatenated OOF evaluation before any exact full-period freeze decision.

Selected family: `{selected_family}`; exact modal variant: `{selected_bundle['modal_exact_variant']}`. OOF net: ¥{selected['standalone']['net_jpy']:.0f}; PF: {selected['standalone']['profit_factor']}; negative-baseline-day contribution: ¥{selected['portfolio']['negative_baseline_day_candidate_contribution_jpy']:.0f}; combined full-equity DD: ¥{selected['portfolio']['combined_full_equity_dd_jpy']:.0f}; worst 5 business days: ¥{selected['portfolio']['combined_worst_5_business_day_jpy']:.0f}.

Right-tail top-5 retention: {selected['right_tail']['top5_winner_pl_retention']}; top-decile retention: {selected['right_tail']['top_decile_gross_profit_retention']}; avoided loss: ¥{selected['right_tail']['avoided_loss_jpy']:.0f}; sacrificed profit: ¥{selected['right_tail']['sacrificed_profit_jpy']:.0f}.

Candidate freeze: `{str(candidate_freeze).lower()}`. 2025 was not accessed. Production and live authorization remain false.
"""
    (args.out_dir / "human_report.md").write_text(report, encoding="utf-8")

    files = []
    for path in sorted(args.out_dir.iterdir()):
        if path.is_file() and path.name not in {"artifact_manifest.json", "PACKAGE_SHA256SUMS"}:
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(args.out_dir / "artifact_manifest.json", {
        "schema_version": "usdjpy_hyp038_artifact_manifest_v1",
        "hypothesis_id": HYP,
        "decision": decision,
        "files": files,
        "2020_2022_accessed": False,
        "2025_accessed": False,
    })
    files.append({"path": "artifact_manifest.json", "bytes": (args.out_dir / "artifact_manifest.json").stat().st_size, "sha256": sha256_file(args.out_dir / "artifact_manifest.json")})
    (args.out_dir / "PACKAGE_SHA256SUMS").write_text("".join(f"{row['sha256']}  {row['path']}\n" for row in files), encoding="utf-8")
    print(json.dumps(clean({
        "decision": decision,
        "selected_candidate_family": selected_family,
        "selected_exact_variant": selected_bundle["modal_exact_variant"],
        "candidate_freeze_authorized": candidate_freeze,
        "selected_oof_net_jpy": selected["standalone"]["net_jpy"],
        "selected_oof_pf": selected["standalone"]["profit_factor"],
        "2025_accessed": False,
    }), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
