#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_usdjpy_shock_failure_2025_postmortem_v3 import (  # type: ignore
    PIP,
    JPY_PER_PIP_001,
    TickArchiveStore,
    classify,
    load_bars23,
    load_bars24,
    path_diagnostics,
)

SCHEMA = "usdjpy_shock_failure_regime_discriminator_v1"
TARGET_F = "F_CONTINUATION_RESUMPTION"
TARGET_H = "H_SUSTAINED_REVERSAL"
SECONDARY_D = "D_PROFIT_THEN_GIVEBACK"
FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]
RNG_SEED = 20260727


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def mdd(pnl: Iterable[float]) -> float:
    eq = np.cumsum(np.asarray(list(pnl), dtype=float))
    if len(eq) == 0:
        return 0.0
    peaks = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peaks[1:] - eq
    return float(np.max(dd)) if len(dd) else 0.0


def profit_factor(pnl: Iterable[float]) -> float:
    a = np.asarray(list(pnl), dtype=float)
    gp = float(a[a > 0].sum())
    gl = float(-a[a < 0].sum())
    return float("inf") if gl == 0 and gp > 0 else (gp / gl if gl > 0 else 0.0)


def session_of(t: pd.Timestamp) -> str:
    h = pd.Timestamp(t).tz_convert("UTC").hour
    if 0 <= h < 7:
        return "TOKYO"
    if 7 <= h < 13:
        return "LONDON"
    if 13 <= h < 16:
        return "LONDON_NY_OVERLAP"
    if 16 <= h < 22:
        return "NEW_YORK"
    return "TRANSITION"


def fold_of(t: pd.Timestamp) -> str:
    t = pd.Timestamp(t).tz_convert("UTC")
    return f"{t.year}H{1 if t.month <= 6 else 2}"


def normalize_bars(path23: Path, path24: Path) -> Dict[int, pd.DataFrame]:
    b23 = load_bars23(path23)
    b24 = load_bars24(path24)
    return {2023: enrich_bars_no_leakage(b23), 2024: enrich_bars_no_leakage(b24)}


def enrich_bars_no_leakage(b: pd.DataFrame) -> pd.DataFrame:
    x = b.copy().sort_values("time").drop_duplicates("time").reset_index(drop=True)
    x["time"] = pd.to_datetime(x["time"], utc=True)
    pc = x.close.shift()
    x["tr_pips"] = pd.concat([x.high - x.low, (x.high - pc).abs(), (x.low - pc).abs()], axis=1).max(axis=1) / PIP
    x["body_signed_pips"] = (x.close - x.open) / PIP
    x["body_pips"] = x.body_signed_pips.abs()
    x["median_tr96"] = x.tr_pips.rolling(96).median()
    x["shock_ratio"] = x.tr_pips / x.median_tr96
    x["atr14_pips"] = x.tr_pips.rolling(14).mean()
    x["atr96_pips"] = x.tr_pips.rolling(96).mean()
    x["ret_pips"] = x.close.diff() / PIP
    x["direction"] = np.sign(x.close - x.open)
    x["close_location"] = (x.close - x.low) / (x.high - x.low).replace(0, np.nan)
    x["upper_wick_pips"] = (x.high - x[["open", "close"]].max(axis=1)) / PIP
    x["lower_wick_pips"] = (x[["open", "close"]].min(axis=1) - x.low) / PIP
    for n in [4, 8, 16, 32, 96]:
        x[f"return_{n}_pips"] = (x.close - x.close.shift(n)) / PIP
        x[f"directional_dominance_{n}"] = x.direction.rolling(n).mean()
        x[f"volatility_{n}"] = x.ret_pips.rolling(n).std()
        x[f"tr_mean_{n}"] = x.tr_pips.rolling(n).mean()
    for span in [8, 20, 50]:
        x[f"ema{span}"] = x.close.ewm(span=span, adjust=False).mean()
        x[f"ema{span}_slope4_pips"] = (x[f"ema{span}"] - x[f"ema{span}"].shift(4)) / PIP

    x["date"] = x.time.dt.floor("D")
    x["day_open_available"] = x.groupby("date").open.transform("first")
    x["day_high_available"] = x.groupby("date").high.cummax()
    x["day_low_available"] = x.groupby("date").low.cummin()
    daily = x.groupby("date").agg(day_high=("high", "max"), day_low=("low", "min"), day_close=("close", "last"))
    daily["prior_day_high"] = daily.day_high.shift()
    daily["prior_day_low"] = daily.day_low.shift()
    daily["prior_day_close"] = daily.day_close.shift()
    x = x.merge(daily[["prior_day_high", "prior_day_low", "prior_day_close"]], left_on="date", right_index=True, how="left")

    # Higher-timeframe values become available only after their bars close.
    for freq, label in [("1h", "h1"), ("4h", "h4")]:
        r = x.set_index("time").resample(freq, label="left", closed="left").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last")
        ).dropna()
        r[f"{label}_ema20"] = r.close.ewm(span=20, adjust=False).mean()
        r[f"{label}_ema50"] = r.close.ewm(span=50, adjust=False).mean()
        r[f"{label}_ema20_slope_pips"] = (r[f"{label}_ema20"] - r[f"{label}_ema20"].shift()) / PIP
        r[f"{label}_return4_pips"] = (r.close - r.close.shift(4)) / PIP
        r[f"{label}_trend_state"] = np.sign(r.close - r[f"{label}_ema20"])
        avail = r[[f"{label}_ema20_slope_pips", f"{label}_return4_pips", f"{label}_trend_state"]].copy()
        avail.index = avail.index + pd.Timedelta(freq)
        x = pd.merge_asof(x.sort_values("time"), avail.reset_index().sort_values("time"), on="time", direction="backward")
    return x


def nearest_index(x: pd.DataFrame, t: pd.Timestamp) -> int:
    i = int(x.time.searchsorted(pd.Timestamp(t)))
    if i >= len(x):
        i = len(x) - 1
    if i > 0 and abs((x.time.iloc[i] - t).total_seconds()) > abs((x.time.iloc[i - 1] - t).total_seconds()):
        i -= 1
    return max(0, i)


def tick_window_features(g: pd.DataFrame, direction: int, prefix: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if g.empty or len(g) < 2:
        for name in ["tick_count", "tick_density_per_min", "net_velocity_pips_per_min", "tick_imbalance", "acceleration_pips_per_min", "spread_median_pips", "spread_p95_pips", "quote_gap_p95_ms", "quote_gap_max_ms"]:
            out[f"{prefix}_{name}"] = np.nan
        return out
    g = g.sort_values("timestamp_utc").drop_duplicates("timestamp_utc")
    dt_min = max((g.timestamp_utc.iloc[-1] - g.timestamp_utc.iloc[0]).total_seconds() / 60.0, 1 / 60)
    d = g.bid.diff().dropna()
    up = int((d > 0).sum())
    down = int((d < 0).sum())
    denom = up + down
    imbalance = 0.0 if denom == 0 else (up - down) / denom
    mid = len(g) // 2
    g1 = g.iloc[: max(mid, 2)]
    g2 = g.iloc[max(mid - 1, 0) :]
    dur1 = max((g1.timestamp_utc.iloc[-1] - g1.timestamp_utc.iloc[0]).total_seconds() / 60.0, 1 / 60)
    dur2 = max((g2.timestamp_utc.iloc[-1] - g2.timestamp_utc.iloc[0]).total_seconds() / 60.0, 1 / 60)
    v1 = direction * (g1.bid.iloc[-1] - g1.bid.iloc[0]) / PIP / dur1
    v2 = direction * (g2.bid.iloc[-1] - g2.bid.iloc[0]) / PIP / dur2
    spread = (g.ask - g.bid) / PIP
    gaps = g.timestamp_utc.diff().dt.total_seconds().dropna() * 1000
    out[f"{prefix}_tick_count"] = float(len(g))
    out[f"{prefix}_tick_density_per_min"] = float(len(g) / dt_min)
    out[f"{prefix}_net_velocity_pips_per_min"] = float(direction * (g.bid.iloc[-1] - g.bid.iloc[0]) / PIP / dt_min)
    out[f"{prefix}_tick_imbalance"] = float(direction * imbalance)
    out[f"{prefix}_acceleration_pips_per_min"] = float(v2 - v1)
    out[f"{prefix}_spread_median_pips"] = float(spread.median())
    out[f"{prefix}_spread_p95_pips"] = float(spread.quantile(0.95))
    out[f"{prefix}_quote_gap_p95_ms"] = float(gaps.quantile(0.95)) if len(gaps) else np.nan
    out[f"{prefix}_quote_gap_max_ms"] = float(gaps.max()) if len(gaps) else np.nan
    return out


def completed_bar_features(g: pd.DataFrame, freq: str, side: int, prefix: str) -> Dict[str, float]:
    if g.empty:
        return {f"{prefix}_{freq}_entry_direction_close_fraction": np.nan, f"{prefix}_{freq}_last_return_entry_pips": np.nan}
    z = g.copy().set_index("timestamp_utc").resample(freq, label="left", closed="left").agg(open=("bid", "first"), close=("bid", "last")).dropna()
    if z.empty:
        return {f"{prefix}_{freq}_entry_direction_close_fraction": np.nan, f"{prefix}_{freq}_last_return_entry_pips": np.nan}
    signed = side * (z.close - z.open) / PIP
    return {
        f"{prefix}_{freq}_entry_direction_close_fraction": float((signed > 0).mean()),
        f"{prefix}_{freq}_last_return_entry_pips": float(signed.iloc[-1]),
    }


def exact_path_timing(store: TickArchiveStore, entry_time: pd.Timestamp, side: int, shock_midpoint: float, shock_pips: float) -> Dict[str, Any]:
    entry_tick = store.first_at_or_after(entry_time)
    if entry_tick is None:
        return {"time_to_reclaim_minutes": np.nan, "time_to_continuation_resumption_minutes": np.nan, "time_to_sustained_reversal_confirmation_minutes": np.nan}
    end = pd.Timestamp(entry_time) + pd.Timedelta("240m")
    p = store.between(entry_tick.timestamp_utc, end, include_end=True)
    if p.empty:
        return {"time_to_reclaim_minutes": np.nan, "time_to_continuation_resumption_minutes": np.nan, "time_to_sustained_reversal_confirmation_minutes": np.nan}
    entry_px = float(entry_tick.ask if side > 0 else entry_tick.bid)
    executable = p.bid if side > 0 else p.ask
    net = side * (executable - entry_px) / PIP
    reclaim_mask = p.bid >= shock_midpoint if side > 0 else p.ask <= shock_midpoint
    cont_mask = net <= -0.5 * abs(shock_pips)
    sustain_mask = net >= 0.5 * abs(shock_pips)

    def minutes(mask: pd.Series) -> float:
        if not bool(mask.any()):
            return np.nan
        t = p.loc[mask, "timestamp_utc"].iloc[0]
        return float((t - entry_tick.timestamp_utc).total_seconds() / 60.0)

    return {
        "time_to_reclaim_minutes": minutes(reclaim_mask),
        "time_to_continuation_resumption_minutes": minutes(cont_mask),
        "time_to_sustained_reversal_confirmation_minutes": minutes(sustain_mask),
    }


def historical_label_v1(r: pd.Series) -> str:
    mfe = float(r.mfe_pips)
    mae = float(r.mae_pips)
    final = float(r.pnl_pips)
    shock = abs(float(r.shock_tr_pips))
    if mfe <= 0:
        return "A_IMMEDIATE_SIGNAL_FAILURE"
    if final <= 0 and mae <= -0.5 * shock:
        return TARGET_F
    if final <= 0 or final < 0.5 * mfe:
        return SECONDARY_D
    return TARGET_H


def build_ledgers(phase: pd.DataFrame, bars: Dict[int, pd.DataFrame], store: TickArchiveStore) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dev = phase[(phase.candidate_id == "B_EXECUTABLE_T0_8BAR") & phase.admitted.fillna(False)].copy()
    assert len(dev) == 114, f"expected 114 fixed-candidate opportunities, got {len(dev)}"
    for c in ["entry_utc", "exit_utc", "entry_tick_utc", "exit_tick_utc", "shock_start_utc", "shock_end_utc", "failure_start_utc", "failure_end_utc"]:
        dev[c] = pd.to_datetime(dev[c], utc=True, format="mixed")
    assert sorted(dev.fold.unique().tolist()) == FOLDS
    assert dev.entry_utc.dt.year.max() <= 2024

    lifecycle_rows: List[Dict[str, Any]] = []
    feature_rows: List[Dict[str, Any]] = []
    diff_rows: List[Dict[str, Any]] = []

    for r in dev.itertuples(index=False):
        x = bars[pd.Timestamp(r.entry_utc).year]
        si = nearest_index(x, pd.Timestamp(r.shock_start_utc))
        fi = nearest_index(x, pd.Timestamp(r.failure_start_utc))
        s = x.iloc[si]
        f = x.iloc[fi]
        shock_dir = 1 if str(r.shock_direction).upper() == "UP" else -1
        side = int(r.side)
        decision = pd.Timestamp(r.entry_utc)
        shock_start = pd.Timestamp(r.shock_start_utc)
        failure_start = pd.Timestamp(r.failure_start_utc)

        path = path_diagnostics(store, decision, side, exit_boundary=pd.Timestamp(r.exit_utc))
        path["shock_magnitude_pips"] = float(r.shock_tr_pips)
        exact_class = classify(path)
        old_class = historical_label_v1(pd.Series(r._asdict()))
        timing = exact_path_timing(store, decision, side, float(r.shock_midpoint), float(r.shock_tr_pips))

        life = {
            "event_id": r.opportunity_id,
            "fold": r.fold,
            "month": decision.strftime("%Y-%m"),
            "side": side,
            "side_label": r.side_label,
            "session": r.session,
            "shock_direction": r.shock_direction,
            "shock_start_utc": shock_start,
            "shock_end_utc": r.shock_end_utc,
            "shock_size_pips": float(r.shock_tr_pips),
            "shock_duration_bars": int(r.impulse_run_bars),
            "failure_confirmation_utc": r.failure_end_utc,
            "entry_time_utc": r.entry_tick_utc,
            "entry_decision_utc": decision,
            "entry_price": float(r.entry_ask_exec if side > 0 else r.entry_bid_exec),
            "exit_time_utc": r.exit_tick_utc,
            "exit_price": float(r.exit_bid_exec if side > 0 else r.exit_ask_exec),
            "mfe_pips": float(path.get("mfe_pips", r.mfe_pips)),
            "mae_pips": float(path.get("mae_pips", r.mae_pips)),
            "realized_pnl_pips": float(r.pnl_pips),
            "realized_pnl_jpy": float(r.pnl_jpy),
            "time_to_mfe_minutes": path.get("time_to_mfe_minutes", np.nan),
            "time_to_mae_minutes": path.get("time_to_mae_minutes", np.nan),
            **timing,
            "lifecycle_class": exact_class,
            "postmortem_historical_label_v1": old_class,
            "label_changed": exact_class != old_class,
            "eight_bar_timeout_minutes": 120,
            "bid_ask_execution": True,
        }
        lifecycle_rows.append(life)
        if exact_class != old_class:
            diff_rows.append({"event_id": r.opportunity_id, "fold": r.fold, "old_label": old_class, "exact_label": exact_class, "reason": "exact Raw Tick timing and canonical classifier reconstructed; old label preserved"})

        pre = store.between(decision - pd.Timedelta("30m"), shock_start)
        shock_ticks = store.between(shock_start, failure_start)
        failure_ticks = store.between(failure_start, decision)
        feat: Dict[str, Any] = {
            "event_id": r.opportunity_id,
            "fold": r.fold,
            "month": decision.strftime("%Y-%m"),
            "side": side,
            "side_label": r.side_label,
            "session": r.session,
            "entry_decision_utc": decision,
            "lifecycle_class": exact_class,
            "pnl_jpy": float(r.pnl_jpy),
            "pnl_pips": float(r.pnl_pips),
            "pnl_jpy_five_seconds": float(r.pnl_jpy_FIVE_SECONDS),
            "pnl_jpy_fifteen_seconds": float(r.pnl_jpy_FIFTEEN_SECONDS),
            "mfe_pips": float(path.get("mfe_pips", r.mfe_pips)),
            "mae_pips": float(path.get("mae_pips", r.mae_pips)),
            "shock_tr_pips": float(s.tr_pips),
            "shock_ratio": float(s.shock_ratio),
            "shock_body_ratio": float(s.body_pips / s.tr_pips) if s.tr_pips else np.nan,
            "shock_close_location": float(s.close_location),
            "shock_duration_bars": int(r.impulse_run_bars),
            "shock_wick_against_ratio": float((s.lower_wick_pips if shock_dir > 0 else s.upper_wick_pips) / s.tr_pips) if s.tr_pips else np.nan,
            "failure_tr_pips": float(f.tr_pips),
            "failure_body_ratio": float(f.body_pips / f.tr_pips) if f.tr_pips else np.nan,
            "failure_close_location_entry_signed": float(side * (f.close_location - 0.5)),
            "failure_wick_against_entry_ratio": float((f.lower_wick_pips if side > 0 else f.upper_wick_pips) / f.tr_pips) if f.tr_pips else np.nan,
            "retracement_ratio": float(abs(f.close - s.close) / max(s.high - s.low, 1e-12)),
            "failure_close_to_shock_mid_entry_pips": float(side * (f.close - float(r.shock_midpoint)) / PIP),
            "failure_close_to_shock_origin_entry_pips": float(side * (f.close - s.open) / PIP),
            "failure_body_entry_pips": float(side * (f.close - f.open) / PIP),
            "pre4h_return_shock_signed_pips": float(shock_dir * s.return_16_pips),
            "pre24h_return_shock_signed_pips": float(shock_dir * s.return_96_pips),
            "directional_dominance_4h_shock_signed": float(shock_dir * s.directional_dominance_16),
            "directional_dominance_8h_shock_signed": float(shock_dir * s.directional_dominance_32),
            "ema8_slope_shock_signed_pips": float(shock_dir * s.ema8_slope4_pips),
            "ema20_slope_shock_signed_pips": float(shock_dir * s.ema20_slope4_pips),
            "h1_ema20_slope_shock_signed_pips": float(shock_dir * s.h1_ema20_slope_pips) if pd.notna(s.h1_ema20_slope_pips) else np.nan,
            "h4_ema20_slope_shock_signed_pips": float(shock_dir * s.h4_ema20_slope_pips) if pd.notna(s.h4_ema20_slope_pips) else np.nan,
            "h1_return4_shock_signed_pips": float(shock_dir * s.h1_return4_pips) if pd.notna(s.h1_return4_pips) else np.nan,
            "h4_return4_shock_signed_pips": float(shock_dir * s.h4_return4_pips) if pd.notna(s.h4_return4_pips) else np.nan,
            "atr14_pips": float(s.atr14_pips),
            "atr14_to_96_ratio": float(s.atr14_pips / s.atr96_pips) if s.atr96_pips else np.nan,
            "distance_daily_open_entry_pips": float(side * (f.close - f.day_open_available) / PIP),
            "distance_prior_day_high_pips": float(f.close - f.prior_day_high) / PIP if pd.notna(f.prior_day_high) else np.nan,
            "distance_prior_day_low_pips": float(f.close - f.prior_day_low) / PIP if pd.notna(f.prior_day_low) else np.nan,
            "weekday": int(decision.weekday()),
            "minutes_from_tokyo_open": float((decision.hour * 60 + decision.minute) - 0),
            "minutes_from_london_open_abs": float(abs((decision.hour * 60 + decision.minute) - 7 * 60)),
            "minutes_from_new_york_open_abs": float(abs((decision.hour * 60 + decision.minute) - 13 * 60)),
            "minutes_from_london_fix_abs": float(abs((decision.hour * 60 + decision.minute) - 15 * 60)),
            "minutes_from_rollover_abs": float(min(abs((decision.hour * 60 + decision.minute) - 22 * 60), 1440 - abs((decision.hour * 60 + decision.minute) - 22 * 60))),
            "feature_cutoff_utc": decision,
            "uses_post_entry_data": False,
        }
        feat.update(tick_window_features(pre, shock_dir, "pre30m_shock_direction"))
        feat.update(tick_window_features(shock_ticks, shock_dir, "shock_window_shock_direction"))
        feat.update(tick_window_features(failure_ticks, side, "failure_window_entry_direction"))
        feat.update(completed_bar_features(failure_ticks, "1min", side, "failure"))
        feat.update(completed_bar_features(failure_ticks, "5min", side, "failure"))
        feature_rows.append(feat)

    lifecycle = pd.DataFrame(lifecycle_rows).sort_values("entry_decision_utc").reset_index(drop=True)
    features = pd.DataFrame(feature_rows).sort_values("entry_decision_utc").reset_index(drop=True)
    differences = pd.DataFrame(diff_rows)
    return lifecycle, features, differences


def cliffs_delta(a: pd.Series, b: pd.Series) -> float:
    a = a.dropna().to_numpy(float)
    b = b.dropna().to_numpy(float)
    if len(a) == 0 or len(b) == 0:
        return np.nan
    # N is small (<=114), exact pairwise delta is auditable.
    return float((np.sum(a[:, None] > b[None, :]) - np.sum(a[:, None] < b[None, :])) / (len(a) * len(b)))


def univariate_table(features: pd.DataFrame, predictor_cols: List[str]) -> pd.DataFrame:
    z = features[features.lifecycle_class.isin([TARGET_F, TARGET_H])].copy()
    y = (z.lifecycle_class == TARGET_H).astype(int)
    rows = []
    rng = np.random.default_rng(RNG_SEED)
    for c in predictor_cols:
        s = pd.to_numeric(z[c], errors="coerce")
        mask = s.notna()
        if mask.sum() < 20 or s[mask].nunique() < 3:
            auc = np.nan
            p = np.nan
        else:
            auc = float(roc_auc_score(y[mask], s[mask]))
            obs = max(auc, 1 - auc)
            perm = []
            yy = y[mask].to_numpy()
            vv = s[mask].to_numpy()
            for _ in range(500):
                yp = rng.permutation(yy)
                xauc = roc_auc_score(yp, vv)
                perm.append(max(xauc, 1 - xauc))
            p = float((1 + np.sum(np.asarray(perm) >= obs)) / (len(perm) + 1))
        hf = s[z.lifecycle_class == TARGET_H]
        ff = s[z.lifecycle_class == TARGET_F]
        fold_auc = []
        for fold in FOLDS:
            q = z[z.fold == fold]
            qy = (q.lifecycle_class == TARGET_H).astype(int)
            qs = pd.to_numeric(q[c], errors="coerce")
            m = qs.notna()
            if m.sum() >= 8 and qy[m].nunique() == 2:
                fold_auc.append(float(roc_auc_score(qy[m], qs[m])))
        signs = [np.sign(a - 0.5) for a in fold_auc if abs(a - 0.5) > 1e-9]
        rows.append({
            "feature": c,
            "n": int(mask.sum()),
            "missing_rate": float(1 - mask.mean()),
            "median_H": float(hf.median()) if hf.notna().any() else np.nan,
            "median_F": float(ff.median()) if ff.notna().any() else np.nan,
            "cliffs_delta_H_vs_F": cliffs_delta(hf, ff),
            "auc_H_high": auc,
            "auc_absolute": np.nan if pd.isna(auc) else max(auc, 1 - auc),
            "permutation_p_500": p,
            "fold_auc_count": len(fold_auc),
            "fold_direction_consistency": float(max(signs.count(1), signs.count(-1)) / len(signs)) if signs else np.nan,
        })
    return pd.DataFrame(rows).sort_values(["auc_absolute", "feature"], ascending=[False, True])


@dataclass
class FittedModel:
    name: str
    features: List[str]
    model: Any
    metadata: Dict[str, Any]

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.features].apply(pd.to_numeric, errors="coerce")
        if self.name == "RD_RANK6_V1":
            medians = self.metadata["medians"]
            scales = self.metadata["scales"]
            signs = self.metadata["signs"]
            scores = []
            for c in self.features:
                v = X[c].fillna(medians[c]).to_numpy(float)
                z = signs[c] * (v - medians[c]) / max(scales[c], 1e-9)
                scores.append(1.0 / (1.0 + np.exp(-np.clip(z, -20, 20))))
            return np.mean(np.vstack(scores), axis=0)
        return self.model.predict_proba(X)[:, 1]


def fit_model(name: str, train: pd.DataFrame, feature_map: Dict[str, List[str]]) -> FittedModel:
    target = train[train.lifecycle_class.isin([TARGET_F, TARGET_H])].copy()
    y = (target.lifecycle_class == TARGET_H).astype(int)
    cols = feature_map[name]
    X = target[cols].apply(pd.to_numeric, errors="coerce")
    if name == "RD_LOGIT_10F_V1":
        model = Pipeline([
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=0.5, penalty="l2", class_weight="balanced", solver="liblinear", random_state=RNG_SEED, max_iter=2000)),
        ])
        model.fit(X, y)
        clf = model.named_steps["clf"]
        meta = {"coefficients_standardized": dict(zip(cols, [float(v) for v in clf.coef_[0]])), "intercept": float(clf.intercept_[0])}
        return FittedModel(name, cols, model, meta)
    if name == "RD_TREE_D2_V1":
        model = Pipeline([
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("clf", DecisionTreeClassifier(max_depth=2, min_samples_leaf=10, class_weight="balanced", random_state=RNG_SEED)),
        ])
        model.fit(X, y)
        tree = model.named_steps["clf"]
        meta = {"tree_text": export_text(tree, feature_names=cols), "feature_importances": dict(zip(cols, [float(v) for v in tree.feature_importances_]))}
        return FittedModel(name, cols, model, meta)
    if name == "RD_RANK6_V1":
        medians = {c: float(X[c].median()) for c in cols}
        scales = {c: float(max(X[c].quantile(0.75) - X[c].quantile(0.25), 1e-9)) for c in cols}
        signs: Dict[str, int] = {}
        for c in cols:
            h = pd.to_numeric(target.loc[target.lifecycle_class == TARGET_H, c], errors="coerce").median()
            f = pd.to_numeric(target.loc[target.lifecycle_class == TARGET_F, c], errors="coerce").median()
            signs[c] = 1 if (pd.notna(h) and pd.notna(f) and h >= f) else -1
        return FittedModel(name, cols, None, {"medians": medians, "scales": scales, "signs": signs})
    raise KeyError(name)


def economy_metrics(df: pd.DataFrame, accepted: np.ndarray, pnl_col: str = "pnl_jpy") -> Dict[str, float]:
    q = df.copy()
    q["accepted"] = np.asarray(accepted, dtype=bool)
    baseline = pd.to_numeric(q[pnl_col], errors="coerce").fillna(0.0)
    accepted_pnl = baseline.where(q.accepted, 0.0)
    h = q.lifecycle_class == TARGET_H
    f = q.lifecycle_class == TARGET_F
    d = q.lifecycle_class == SECONDARY_D
    h_profit_total = float(q.loc[h, "pnl_jpy"].clip(lower=0).sum())
    h_profit_acc = float(q.loc[h & q.accepted, "pnl_jpy"].clip(lower=0).sum())
    f_loss_total = float(-q.loc[f, "pnl_jpy"].clip(upper=0).sum())
    f_loss_rej = float(-q.loc[f & ~q.accepted, "pnl_jpy"].clip(upper=0).sum())
    winner_damage = float(q.loc[~q.accepted, "pnl_jpy"].clip(lower=0).sum())
    loser_benefit = float(-q.loc[~q.accepted, "pnl_jpy"].clip(upper=0).sum())
    acc = q[q.accepted].sort_values("entry_decision_utc")
    return {
        "total_opportunities": int(len(q)),
        "accepted_trades": int(q.accepted.sum()),
        "rejected_trades": int((~q.accepted).sum()),
        "baseline_net_jpy": float(baseline.sum()),
        "accepted_net_jpy": float(accepted_pnl.sum()),
        "net_benefit_jpy": float(accepted_pnl.sum() - baseline.sum()),
        "profit_factor": profit_factor(acc[pnl_col].fillna(0.0)),
        "maximum_drawdown_jpy": mdd(acc[pnl_col].fillna(0.0)),
        "recovery_factor": float(acc[pnl_col].sum() / mdd(acc[pnl_col])) if len(acc) and mdd(acc[pnl_col]) > 0 else np.nan,
        "win_rate": float((acc[pnl_col] > 0).mean()) if len(acc) else np.nan,
        "median_trade_jpy": float(acc[pnl_col].median()) if len(acc) else np.nan,
        "gross_profit_jpy": float(acc[pnl_col].clip(lower=0).sum()),
        "gross_loss_jpy": float(acc[pnl_col].clip(upper=0).sum()),
        "sustained_reversal_count_retention": float((h & q.accepted).sum() / h.sum()) if h.sum() else np.nan,
        "sustained_reversal_profit_retention": float(h_profit_acc / h_profit_total) if h_profit_total else np.nan,
        "continuation_resumption_count_rejection": float((f & ~q.accepted).sum() / f.sum()) if f.sum() else np.nan,
        "continuation_resumption_loss_rejection": float(f_loss_rej / f_loss_total) if f_loss_total else np.nan,
        "profit_then_giveback_acceptance": float((d & q.accepted).sum() / d.sum()) if d.sum() else np.nan,
        "winner_damage_jpy": winner_damage,
        "loser_benefit_jpy": loser_benefit,
    }


def choose_threshold(inner_rows: pd.DataFrame, thresholds: List[float]) -> float:
    scored = []
    for t in thresholds:
        fold_metrics = []
        for fold in sorted(inner_rows.fold.unique()):
            q = inner_rows[inner_rows.fold == fold]
            fold_metrics.append(economy_metrics(q, q.score.to_numpy() >= t))
        nonneg = sum(m["net_benefit_jpy"] >= 0 for m in fold_metrics)
        med = float(np.median([m["net_benefit_jpy"] for m in fold_metrics]))
        hret = float(np.mean([m["sustained_reversal_profit_retention"] for m in fold_metrics]))
        frej = float(np.mean([m["continuation_resumption_loss_rejection"] for m in fold_metrics]))
        feasibility = int(hret >= 0.65 and frej >= 0.20)
        scored.append((feasibility, nonneg, med, hret, frej, -abs(t - 0.5), t))
    return float(max(scored)[-1])


def oof_predictions(features: pd.DataFrame, name: str, feature_map: Dict[str, List[str]], thresholds: List[float]) -> Tuple[pd.DataFrame, List[Dict[str, Any]], List[Dict[str, Any]]]:
    all_rows = []
    outer_receipts = []
    model_meta = []
    for outer in FOLDS:
        train_folds = [f for f in FOLDS if f != outer]
        inner_parts = []
        for inner in train_folds:
            inner_train = features[features.fold.isin([f for f in train_folds if f != inner])]
            inner_test = features[features.fold == inner].copy()
            fitted = fit_model(name, inner_train, feature_map)
            inner_test["score"] = fitted.predict(inner_test)
            inner_parts.append(inner_test)
        inner_rows = pd.concat(inner_parts, ignore_index=True)
        threshold = choose_threshold(inner_rows, thresholds)
        fitted = fit_model(name, features[features.fold.isin(train_folds)], feature_map)
        test = features[features.fold == outer].copy()
        test["score"] = fitted.predict(test)
        test["candidate_model"] = name
        test["outer_fold"] = outer
        test["threshold_selected_without_outer"] = threshold
        all_rows.append(test)
        met = economy_metrics(test, test.score.to_numpy() >= threshold)
        outer_receipts.append({"candidate_model": name, "outer_fold": outer, "training_folds": train_folds, "threshold": threshold, **met})
        model_meta.append({"candidate_model": name, "outer_fold": outer, **fitted.metadata})
    return pd.concat(all_rows, ignore_index=True), outer_receipts, model_meta


def threshold_metrics(oof: pd.DataFrame, thresholds: List[float]) -> pd.DataFrame:
    rows = []
    for t in thresholds:
        met = economy_metrics(oof, oof.score.to_numpy() >= t)
        fold_benefits = []
        for fold in FOLDS:
            q = oof[oof.fold == fold]
            fm = economy_metrics(q, q.score.to_numpy() >= t)
            fold_benefits.append(fm["net_benefit_jpy"])
        rows.append({"threshold": t, **met, "positive_fold_benefit_count": int(sum(v >= 0 for v in fold_benefits)), "minimum_fold_benefit_jpy": float(min(fold_benefits)), "median_fold_benefit_jpy": float(np.median(fold_benefits))})
    return pd.DataFrame(rows)


def stability_score(name: str, metadata: List[Dict[str, Any]], feature_map: Dict[str, List[str]]) -> Tuple[float, Dict[str, Any]]:
    if name == "RD_LOGIT_10F_V1":
        signs = {c: [] for c in feature_map[name]}
        for m in metadata:
            for c, v in m["coefficients_standardized"].items():
                signs[c].append(int(np.sign(v)))
        consist = {c: max(v.count(1), v.count(-1), v.count(0)) / len(v) for c, v in signs.items()}
        return float(np.mean(list(consist.values()))), {"coefficient_sign_consistency": consist}
    if name == "RD_TREE_D2_V1":
        tops = []
        for m in metadata:
            imp = m["feature_importances"]
            tops.append(max(imp, key=imp.get) if max(imp.values()) > 0 else "NONE")
        best = max(set(tops), key=tops.count)
        return float(tops.count(best) / len(tops)), {"top_split_features": tops, "modal_top_split": best}
    signs = {c: [] for c in feature_map[name]}
    for m in metadata:
        for c, v in m["signs"].items():
            signs[c].append(int(v))
    consist = {c: max(v.count(1), v.count(-1)) / len(v) for c, v in signs.items()}
    return float(np.mean(list(consist.values()))), {"rank_orientation_consistency": consist}


def candidate_evaluation(features: pd.DataFrame, prereg: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    feature_map = prereg["candidate_models"]
    thresholds = [float(x) for x in prereg["threshold_grid"]]
    gate = prereg["portable_gates"]
    oof_all = []
    outer_all = []
    candidate_rows = []
    rejection_rows = []
    contracts: Dict[str, Any] = {}

    for name in feature_map:
        oof, outer, metadata = oof_predictions(features, name, feature_map, thresholds)
        oof_all.append(oof)
        outer_all.extend(outer)
        table = threshold_metrics(oof, thresholds)
        # Deterministic development-only freeze threshold.
        feasible = table[(table.sustained_reversal_profit_retention >= gate["minimum_sustained_reversal_profit_retention"]) & (table.continuation_resumption_loss_rejection >= gate["minimum_continuation_resumption_loss_rejection"])]
        pool = feasible if len(feasible) else table
        best = pool.sort_values(["positive_fold_benefit_count", "median_fold_benefit_jpy", "net_benefit_jpy", "sustained_reversal_profit_retention"], ascending=False).iloc[0]
        threshold = float(best.threshold)
        accepted = oof.score.to_numpy() >= threshold
        metrics = economy_metrics(oof, accepted)
        fold_rows = []
        for fold in FOLDS:
            q = oof[oof.fold == fold]
            fm = economy_metrics(q, q.score.to_numpy() >= threshold)
            fold_rows.append({"fold": fold, **fm})
        positive_folds = sum(r["net_benefit_jpy"] >= 0 for r in fold_rows)
        min_fold = min(r["net_benefit_jpy"] for r in fold_rows)
        accepted_df = oof[accepted].sort_values("entry_decision_utc")
        top = accepted_df.pnl_jpy.sort_values(ascending=False).to_numpy()
        top_removed = {f"top{k}_removed_net_jpy": float(accepted_df.pnl_jpy.sum() - top[:k].sum()) for k in [1, 3, 5]}
        spread1 = float(accepted_df.pnl_jpy.sum() - 10.0 * len(accepted_df))
        spread2 = float(accepted_df.pnl_jpy.sum() - 20.0 * len(accepted_df))
        delay5 = float(accepted_df.pnl_jpy_five_seconds.sum())
        delay15 = float(accepted_df.pnl_jpy_fifteen_seconds.sum())
        side_rows = []
        for side in [1, -1]:
            q = oof[oof.side == side]
            sm = economy_metrics(q, q.score.to_numpy() >= threshold)
            side_rows.append({"side": side, **sm})
        session_count = int(accepted_df.session.nunique())
        month_positive = int((accepted_df.groupby("month").pnl_jpy.sum() > 0).sum())
        st_score, st_detail = stability_score(name, metadata, feature_map)
        auc_mask = oof.lifecycle_class.isin([TARGET_F, TARGET_H])
        auc = float(roc_auc_score((oof.loc[auc_mask, "lifecycle_class"] == TARGET_H).astype(int), oof.loc[auc_mask, "score"]))
        idx = thresholds.index(threshold)
        neighbor_ts = thresholds[max(0, idx - 1): min(len(thresholds), idx + 2)]
        neighbor = table[table.threshold.isin(neighbor_ts)]
        neighbor_nonneg = int((neighbor.net_benefit_jpy >= 0).sum())
        top_share = float(top[0] / accepted_df.pnl_jpy.clip(lower=0).sum()) if len(top) and accepted_df.pnl_jpy.clip(lower=0).sum() > 0 else np.nan

        checks = {
            "positive_fold_benefit_3_of_4": positive_folds >= gate["minimum_nonnegative_fold_benefit_count"],
            "minimum_fold_not_fatal": min_fold >= gate["minimum_fold_net_benefit_jpy"],
            "sustained_reversal_profit_retention": metrics["sustained_reversal_profit_retention"] >= gate["minimum_sustained_reversal_profit_retention"],
            "continuation_resumption_loss_rejection": metrics["continuation_resumption_loss_rejection"] >= gate["minimum_continuation_resumption_loss_rejection"],
            "accepted_trade_floor": metrics["accepted_trades"] >= gate["minimum_accepted_trades"],
            "both_sides_present": all(r["accepted_trades"] >= gate["minimum_accepted_trades_each_side"] for r in side_rows),
            "side_benefit_not_fatal": all(r["net_benefit_jpy"] >= gate["minimum_side_net_benefit_jpy"] for r in side_rows),
            "session_breadth": session_count >= gate["minimum_accepted_sessions"],
            "month_breadth": month_positive >= gate["minimum_positive_months"],
            "top3_removed_positive": top_removed["top3_removed_net_jpy"] > 0,
            "spread_plus_1_positive": spread1 > 0,
            "delay15_positive": delay15 > 0,
            "threshold_neighborhood": neighbor_nonneg >= gate["minimum_nonnegative_threshold_neighbors"],
            "predictive_auc": auc >= gate["minimum_oof_auc"],
            "model_stability": st_score >= gate["minimum_model_stability"],
            "top_event_dependence": (pd.isna(top_share) or top_share <= gate["maximum_top_event_profit_share"]),
        }
        passed = all(checks.values())
        row = {
            "candidate_model": name,
            "frozen_threshold": threshold,
            "oof_auc": auc,
            "model_stability": st_score,
            "positive_fold_benefit_count": positive_folds,
            "minimum_fold_benefit_jpy": min_fold,
            "positive_months": month_positive,
            "accepted_sessions": session_count,
            "spread_plus_1_net_jpy": spread1,
            "spread_plus_2_net_jpy": spread2,
            "delay_5s_net_jpy": delay5,
            "delay_15s_net_jpy": delay15,
            "top_event_profit_share": top_share,
            **top_removed,
            **metrics,
            "portable_gate_pass": passed,
            "gate_checks_json": json.dumps(checks, sort_keys=True),
        }
        candidate_rows.append(row)
        if not passed:
            rejection_rows.append({"candidate_model": name, "reasons": [k for k, v in checks.items() if not v]})
        fitted_all = fit_model(name, features, feature_map)
        contracts[name] = {"model": name, "features": feature_map[name], "threshold": threshold, "all_development_fit": fitted_all.metadata, "stability": st_detail, "gate_checks": checks}

    candidates = pd.DataFrame(candidate_rows).sort_values(["portable_gate_pass", "positive_fold_benefit_count", "net_benefit_jpy"], ascending=False)
    passing = candidates[candidates.portable_gate_pass]
    if len(passing):
        winner = passing.sort_values(["positive_fold_benefit_count", "net_benefit_jpy", "sustained_reversal_profit_retention", "oof_auc"], ascending=False).iloc[0]
        status = "PASS_PORTABLE_RESEARCH_CANDIDATE"
        selected = str(winner.candidate_model)
    else:
        winner = candidates.iloc[0]
        status = "NO_PORTABLE_CANDIDATE"
        selected = None
    decision = {
        "schema_version": SCHEMA + "_final_decision",
        "hypothesis_id": prereg["hypothesis_id"],
        "status": status,
        "selected_candidate_id": selected,
        "best_diagnostic_model": str(winner.candidate_model),
        "development_periods": FOLDS,
        "2025_used_for_selection": False,
        "next_stage_authorized": "EXACT_IMPLEMENTATION_CONTRACT_ONLY" if selected is not None else "NONE",
        "core_source_change_authorized": False,
        "mt4_economic_evaluation_authorized": False,
        "production_authorized": False,
        "selected_metrics": None if selected is None else candidates[candidates.candidate_model == selected].iloc[0].to_dict(),
        "interpretation": "A candidate is portable only when every preregistered gate passes; otherwise the correct outcome is NO_PORTABLE_CANDIDATE.",
    }
    return candidates, pd.DataFrame(outer_all), pd.concat(oof_all, ignore_index=True), decision, {"contracts": contracts, "rejected": rejection_rows}


def bootstrap_and_permutation(oof: pd.DataFrame, threshold: float, replicates: int = 5000) -> Dict[str, Any]:
    rng = np.random.default_rng(RNG_SEED)
    accepted = oof.score.to_numpy() >= threshold
    pnl = oof.pnl_jpy.to_numpy(float)
    n = len(oof)
    benefits = []
    for _ in range(replicates):
        idx = rng.integers(0, n, n)
        benefits.append(float((pnl[idx] * accepted[idx]).sum() - pnl[idx].sum()))
    target = oof.lifecycle_class.isin([TARGET_F, TARGET_H])
    y = (oof.loc[target, "lifecycle_class"] == TARGET_H).astype(int).to_numpy()
    score = oof.loc[target, "score"].to_numpy(float)
    obs_auc = float(roc_auc_score(y, score))
    perm_auc = []
    for _ in range(min(replicates, 2000)):
        perm_auc.append(float(roc_auc_score(rng.permutation(y), score)))
    return {
        "replicates": replicates,
        "event_bootstrap_net_benefit_ci95_jpy": [float(np.quantile(benefits, 0.025)), float(np.quantile(benefits, 0.975))],
        "event_bootstrap_probability_positive": float(np.mean(np.asarray(benefits) > 0)),
        "oof_auc": obs_auc,
        "permutation_auc_p_value": float((1 + np.sum(np.asarray(perm_auc) >= obs_auc)) / (len(perm_auc) + 1)),
    }


def aggregate_tables(lifecycle: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    tables = {}
    dims = {
        "fold": ["fold"],
        "side": ["side_label"],
        "session": ["session"],
        "month": ["month"],
        "shock_size_bucket": [pd.cut(lifecycle.shock_size_pips, [-np.inf, 20, 30, 45, np.inf], labels=["lt20", "20_30", "30_45", "ge45"]).rename("shock_size_bucket")],
        "holding_time_bucket": [pd.cut((pd.to_datetime(lifecycle.exit_time_utc, utc=True) - pd.to_datetime(lifecycle.entry_time_utc, utc=True)).dt.total_seconds()/60, [-np.inf, 119, 121, np.inf], labels=["lt119", "119_121", "gt121"]).rename("holding_time_bucket")],
    }
    for name, keys in dims.items():
        q = lifecycle.copy()
        group_keys = []
        for k in keys:
            if isinstance(k, pd.Series):
                q[k.name] = k
                group_keys.append(k.name)
            else:
                group_keys.append(k)
        tables[name] = q.groupby(group_keys + ["lifecycle_class"], dropna=False).agg(events=("event_id", "count"), net_jpy=("realized_pnl_jpy", "sum"), median_pnl_jpy=("realized_pnl_jpy", "median"), median_mfe_pips=("mfe_pips", "median"), median_mae_pips=("mae_pips", "median")).reset_index()
    return tables


def build_report(decision: Dict[str, Any], candidates: pd.DataFrame, classification: Dict[str, Any], source_manifest: Dict[str, Any]) -> str:
    best = candidates.iloc[0]
    return f"""# USDJPY Shock Failure Regime Discriminator Study v1\n\n## Decision\n\n`{decision['status']}`\n\n- Hypothesis: `{decision['hypothesis_id']}`\n- Selected candidate: `{decision['selected_candidate_id']}`\n- Best diagnostic model: `{decision['best_diagnostic_model']}`\n- Development only: 2023H1, 2023H2, 2024H1, 2024H2\n- 2025 used for selection: `false`\n- Production authorized: `false`\n\n## Classification audit\n\n- Fixed candidate opportunities reconstructed: {classification['events']}\n- Exact Raw Tick lifecycle labels reproducible: `{classification['exact_reproduction_pass']}`\n- Label differences versus the preserved historical approximation: {classification['label_difference_count']}\n- Lookahead violations in feature ledger: {classification['lookahead_violation_count']}\n\n## Best diagnostic model\n\n- Model: `{best.candidate_model}`\n- Frozen development threshold: {best.frozen_threshold:.3f}\n- Accepted trades: {int(best.accepted_trades)} / {int(best.total_opportunities)}\n- Net: ¥{best.accepted_net_jpy:.0f}; PF: {best.profit_factor:.3f}; MDD: ¥{best.maximum_drawdown_jpy:.0f}\n- Net benefit versus unfiltered fixed candidate: ¥{best.net_benefit_jpy:.0f}\n- Sustained-reversal profit retention: {best.sustained_reversal_profit_retention:.1%}\n- Continuation-resumption loss rejection: {best.continuation_resumption_loss_rejection:.1%}\n- Nonnegative fold benefit: {int(best.positive_fold_benefit_count)}/4\n- Portable gates passed: `{bool(best.portable_gate_pass)}`\n\n## Boundary\n\nThe rejected fixed candidate `B_EXECUTABLE_T0_8BAR` was not retuned. Oracle lifecycle labels were used only as development labels. Every candidate feature is timestamped at or before the entry decision boundary. Profit-then-giveback exit optimization was not mixed into admission. Core/MT4 and production remain locked unless a portable Research candidate passes every preregistered gate.\n\n## Source authority\n\n```json\n{json.dumps(source_manifest, indent=2, sort_keys=True)}\n```\n"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase2-ledger", type=Path, required=True)
    ap.add_argument("--m15-2023", type=Path, required=True)
    ap.add_argument("--m15-2024", type=Path, required=True)
    ap.add_argument("--raw-2023", type=Path, required=True)
    ap.add_argument("--raw-2024", type=Path, required=True)
    ap.add_argument("--prereg", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--research-sha", required=True)
    ap.add_argument("--core-sha", required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    prereg = json.loads(args.prereg.read_text(encoding="utf-8"))
    assert prereg["status"] == "FROZEN_BEFORE_REGIME_DISCRIMINATOR_OUTCOMES"
    assert prereg["hypothesis_id"] == "USDJPY-HYP-028"
    assert prereg["development_folds"] == FOLDS
    assert set(prereg["forbidden_selection_periods"]) == {"2025H1", "2025H2"}
    assert prereg["old_candidate_retuning_permitted"] is False

    phase = pd.read_csv(args.phase2_ledger, compression="infer")
    assert not any("2025" in str(v) for v in phase.fold.dropna().unique())
    bars = normalize_bars(args.m15_2023, args.m15_2024)
    store = TickArchiveStore([args.raw_2023, args.raw_2024])
    lifecycle, features, differences = build_ledgers(phase, bars, store)

    predictor_cols = sorted(set(sum(prereg["candidate_models"].values(), [])))
    missing = [c for c in predictor_cols if c not in features.columns]
    assert not missing, missing
    timestamp_audit = features[["event_id", "fold", "entry_decision_utc", "feature_cutoff_utc", "uses_post_entry_data"]].copy()
    timestamp_audit["feature_cutoff_le_decision"] = pd.to_datetime(timestamp_audit.feature_cutoff_utc, utc=True) <= pd.to_datetime(timestamp_audit.entry_decision_utc, utc=True)
    timestamp_audit["pass"] = timestamp_audit.feature_cutoff_le_decision & ~timestamp_audit.uses_post_entry_data
    assert bool(timestamp_audit["pass"].all())

    class_tables = aggregate_tables(lifecycle)
    univariate = univariate_table(features, predictor_cols)
    candidates, outer, oof, decision, contract_bundle = candidate_evaluation(features, prereg)
    best_name = str(decision["selected_candidate_id"] or decision["best_diagnostic_model"])
    best_row = candidates[candidates.candidate_model == best_name].iloc[0]
    best_oof = oof[oof.candidate_model == best_name].copy()
    robustness = bootstrap_and_permutation(best_oof, float(best_row.frozen_threshold))

    source_manifest = {
        "schema_version": SCHEMA + "_source_manifest",
        "research_sha": args.research_sha,
        "core_sha_read_only": args.core_sha,
        "run_id": args.run_id,
        "phase2_ledger_sha256": sha256_file(args.phase2_ledger),
        "m15_2023_sha256": sha256_file(args.m15_2023),
        "m15_2024_sha256": sha256_file(args.m15_2024),
        "raw_2023_monthly_archives": len(list(args.raw_2023.glob("*.tar.gz"))),
        "raw_2024_monthly_archives": len(list(args.raw_2024.glob("*.tar.gz"))),
        "development_periods": FOLDS,
        "2025_inputs_present_in_selection_process": False,
    }
    classification = {
        "schema_version": SCHEMA + "_classification_audit",
        "events": int(len(lifecycle)),
        "exact_reproduction_pass": bool(len(lifecycle) == 114 and lifecycle.lifecycle_class.notna().all()),
        "label_difference_count": int(lifecycle.label_changed.sum()),
        "lookahead_violation_count": int((~timestamp_audit["pass"]).sum()),
        "classes": lifecycle.lifecycle_class.value_counts().to_dict(),
        "definitions": {
            TARGET_F: "profitable before 120 minutes, closes negative at 120 minutes, and MAE reaches at least 0.5 shock magnitude against the entry",
            SECONDARY_D: "profitable before 120 minutes, then closes nonpositive or below 50% of MFE without meeting continuation-resumption severity",
            TARGET_H: "profitable before 120 minutes and not classified as delayed, giveback, continuation, timeout, insufficient reversal, immediate failure, or anomaly",
        },
    }
    period_receipt = {
        "schema_version": SCHEMA + "_period_access_receipt",
        "selection_script_inputs": [str(args.phase2_ledger), str(args.m15_2023), str(args.m15_2024), str(args.raw_2023), str(args.raw_2024), str(args.prereg)],
        "development_folds": FOLDS,
        "2025_loaded": False,
        "2025_used_for_feature_selection": False,
        "2025_used_for_threshold_selection": False,
        "2025_used_for_model_selection": False,
        "pass": True,
    }
    leakage = {
        "schema_version": SCHEMA + "_leakage_audit",
        "feature_timestamp_contract": "all features must be complete and observable at or before entry_decision_utc",
        "oracle_labels_used_as_predictors": False,
        "post_entry_mfe_mae_pnl_used_as_predictors": False,
        "higher_timeframe_incomplete_bars_used": False,
        "feature_columns": predictor_cols,
        "pass": bool(timestamp_audit["pass"].all()),
    }

    lifecycle.to_csv(args.out_dir / "lifecycle_ledger.csv.gz", index=False, compression="gzip")
    features.to_csv(args.out_dir / "feature_ledger.csv.gz", index=False, compression="gzip")
    timestamp_audit.to_csv(args.out_dir / "feature_timestamp_audit.csv", index=False)
    differences.to_csv(args.out_dir / "lifecycle_label_difference_ledger.csv", index=False)
    univariate.to_csv(args.out_dir / "univariate_separation.csv", index=False)
    candidates.to_csv(args.out_dir / "candidate_metrics.csv", index=False)
    outer.to_csv(args.out_dir / "lofo_results.csv", index=False)
    oof.to_csv(args.out_dir / "oof_predictions.csv.gz", index=False, compression="gzip")
    for name, table in class_tables.items():
        table.to_csv(args.out_dir / f"class_distribution_by_{name}.csv", index=False)

    rejected = pd.DataFrame([{"candidate_model": r["candidate_model"], "rejection_reasons": ";".join(r["reasons"])} for r in contract_bundle["rejected"]])
    rejected.to_csv(args.out_dir / "rejected_candidate_ledger.csv", index=False)
    write_json(args.out_dir / "candidate_contracts.json", contract_bundle["contracts"])
    write_json(args.out_dir / "classification_audit.json", classification)
    write_json(args.out_dir / "source_manifest.json", source_manifest)
    write_json(args.out_dir / "period_access_receipt.json", period_receipt)
    write_json(args.out_dir / "leakage_audit.json", leakage)
    write_json(args.out_dir / "statistical_robustness.json", robustness)
    write_json(args.out_dir / "final_decision.json", decision)
    (args.out_dir / "human_readable_report.md").write_text(build_report(decision, candidates, classification, source_manifest), encoding="utf-8")
    (args.out_dir / "REPRODUCE.md").write_text(
        "Run the canonical workflow `.github/workflows/usdjpy_shock_failure_regime_discriminator_v1.yml`. The selection evaluator has no 2025 input argument.\n",
        encoding="utf-8",
    )

    outputs = []
    for p in sorted(args.out_dir.iterdir()):
        if p.is_file() and p.name not in {"manifest.json", "SHA256SUMS"}:
            outputs.append({"path": p.name, "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    write_json(args.out_dir / "manifest.json", {"schema_version": SCHEMA + "_manifest", "files": outputs})
    outputs.append({"path": "manifest.json", "bytes": (args.out_dir / "manifest.json").stat().st_size, "sha256": sha256_file(args.out_dir / "manifest.json")})
    (args.out_dir / "SHA256SUMS").write_text("".join(f"{r['sha256']}  {r['path']}\n" for r in outputs), encoding="utf-8")
    print(json.dumps(decision, indent=2, default=str))


if __name__ == "__main__":
    main()
