#!/usr/bin/env python3
"""Comprehensive, outcome-locked structural-stop atlas for USDJPY B02/F05.

The evaluator intentionally separates broad discovery from confirmatory portfolio/MT4
validation. It searches diverse online-only price-path mechanisms using exact 2023/2024
accepted trade authorities, leave-one-fold-out selection, multiple-testing control,
robustness delays/costs, supervised checkpoint models and unsupervised path clustering.
No candidate is frozen or implementation-authorized by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, wilcoxon
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from usdjpy_structural_sl_v1.common import (
    EXPECTED_COUNTS,
    EXPECTED_SHA,
    FOLDS,
    PIP,
    aggregate_bars,
    historical_2023_trades,
    load_2023_m15,
    load_m1,
    parse_event_trades,
    sha256_file,
    write_json,
)

SCOPES = ["ALL", "B02", "F05"]
CHECKPOINTS = [5, 15, 30, 60, 120]
MODEL_NAMES = ["LOGISTIC_L2", "TREE_D2", "TREE_D3", "HIST_GB"]


def stable_id(family: str, params: dict[str, Any]) -> str:
    body = json.dumps(params, sort_keys=True, separators=(",", ":"))
    short = hashlib.sha256(body.encode()).hexdigest()[:10]
    human = "_".join(f"{k}-{str(v).replace('.', 'p')}" for k, v in params.items())
    return f"{family}__{human}__{short}"


def product_specs(family: str, grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(grid)
    out: list[dict[str, Any]] = []
    for vals in itertools.product(*(grid[k] for k in keys)):
        params = dict(zip(keys, vals))
        out.append({"candidate_id": stable_id(family, params), "family": family, "params": params})
    return out


def generate_specs(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for family in protocol["deterministic_families"]:
        specs.extend(product_specs(family["family"], family["grid"]))
    expected = int(protocol["candidate_count"])
    assert len(specs) == expected, (len(specs), expected)
    assert len({x["candidate_id"] for x in specs}) == expected
    return specs


def verify_protocol(path: Path) -> dict[str, Any]:
    p = json.loads(path.read_text())
    assert p["schema_version"] == "usdjpy_b02_f05_structural_sl_atlas_protocol_v2"
    assert p["status"] == "FROZEN_BEFORE_OUTCOME_EXECUTION"
    assert p["population"]["trade_count"] == 1882
    assert p["population"]["folds"] == FOLDS
    assert p["authorization"]["direct_user_instruction"] is True
    assert p["authorization"]["notion_task_dependency"] is False
    assert p["boundaries"]["fixed_pip_stop_evaluated"] is False
    assert p["boundaries"]["mt4_accessed"] is False
    assert p["boundaries"]["2025_accessed"] is False
    specs = generate_specs(p)
    assert len(specs) >= 250
    return p


def load_authorities(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    actual_sha = {
        "m15_2023": sha256_file(args.m15_2023),
        "m1_2023": sha256_file(args.m1_2023),
        "events_2024h1": sha256_file(args.events_2024h1),
        "events_2024h2": sha256_file(args.events_2024h2),
        "m1_2024": sha256_file(args.m1_2024),
    }
    assert actual_sha == EXPECTED_SHA, (actual_sha, EXPECTED_SHA)
    trades = pd.concat(
        [
            historical_2023_trades(load_2023_m15(args.m15_2023)),
            parse_event_trades(args.events_2024h1, "2024H1", False),
            parse_event_trades(args.events_2024h2, "2024H2", True),
        ],
        ignore_index=True,
    ).sort_values(["fold", "entry_utc", "strategy"], kind="mergesort").reset_index(drop=True)
    counts = {
        fold: {strategy: int(n) for strategy, n in g.groupby("strategy").size().items()}
        for fold, g in trades.groupby("fold")
    }
    assert len(trades) == 1882 and counts == EXPECTED_COUNTS, (len(trades), counts)
    for c in ["signal_utc", "entry_utc", "close_utc"]:
        trades[c] = pd.to_datetime(trades[c], utc=True)
    trades["trade_id"] = [
        f"{r.fold}|{r.strategy}|{pd.Timestamp(r.entry_utc).isoformat()}|{int(r.side)}"
        for r in trades.itertuples(index=False)
    ]
    m23, m24 = load_m1(args.m1_2023, args.m1_2024)
    return trades, m23, m24, actual_sha


def exec_fields(frame: pd.DataFrame, side: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    prefix = "bid" if side == 1 else "ask"
    o = frame[f"{prefix}_open"].to_numpy(float)
    c = frame[f"{prefix}_close"].to_numpy(float)
    if side == 1:
        fav = frame["bid_high"].to_numpy(float)
        adv = frame["bid_low"].to_numpy(float)
    else:
        fav = frame["ask_low"].to_numpy(float)
        adv = frame["ask_high"].to_numpy(float)
    return o, c, fav, adv


def side_return(price: np.ndarray | float, entry: float, side: int) -> np.ndarray | float:
    return side * (price - entry) / PIP


def consecutive_first(mask: np.ndarray, persistence: int, start: int = 0) -> int | None:
    if persistence <= 1:
        q = np.flatnonzero(mask[start:])
        return None if len(q) == 0 else int(start + q[0])
    run = 0
    for i in range(start, len(mask)):
        run = run + 1 if bool(mask[i]) else 0
        if run >= persistence:
            return i
    return None


def rolling_tstat(y: np.ndarray) -> float:
    n = len(y)
    if n < 3 or not np.isfinite(y).all():
        return math.nan
    x = np.arange(n, dtype=float)
    xm = x.mean(); ym = y.mean()
    ssx = float(((x - xm) ** 2).sum())
    if ssx <= 0:
        return math.nan
    slope = float(((x - xm) * (y - ym)).sum() / ssx)
    resid = y - (ym + slope * (x - xm))
    dof = n - 2
    if dof <= 0:
        return math.nan
    mse = float((resid ** 2).sum() / dof)
    if mse <= 1e-18:
        return math.copysign(99.0, slope) if slope != 0 else 0.0
    se = math.sqrt(mse / ssx)
    return slope / se


def pre_context(m1_all: pd.DataFrame, entry: pd.Timestamp, side: int) -> dict[str, Any]:
    pre = m1_all[(m1_all.index < entry) & (m1_all.index >= entry - pd.Timedelta(minutes=120))].tail(120)
    assert len(pre) >= 30, (entry, len(pre))
    p60 = pre.tail(60)
    prev = p60.bid_close.shift(1)
    tr = pd.concat(
        [
            p60.bid_high - p60.bid_low,
            (p60.bid_high - prev).abs(),
            (p60.bid_low - prev).abs(),
        ], axis=1,
    ).max(axis=1).dropna()
    pre_range = float(p60.bid_high.max() - p60.bid_low.min())
    median_tr = float(tr.median()) if len(tr) else pre_range / 10.0
    scale_price = max(pre_range, 8.0 * median_tr, np.finfo(float).eps)
    close_diff = p60.bid_close.diff().dropna().to_numpy(float)
    sigma1 = float(np.std(close_diff, ddof=1)) if len(close_diff) >= 3 else median_tr
    sigma1 = max(sigma1, median_tr / 2.0, np.finfo(float).eps)
    levels: dict[int, dict[str, float]] = {}
    for lb in [15, 30, 60, 120]:
        q = pre.tail(lb)
        hi = float(q.bid_high.max()); lo = float(q.bid_low.min())
        if side == 1:
            levels[lb] = {"midpoint": (hi + lo) / 2, "opposite_quartile": lo + 0.25 * (hi - lo), "opposite_edge": lo}
        else:
            levels[lb] = {"midpoint": (hi + lo) / 2, "opposite_quartile": hi - 0.25 * (hi - lo), "opposite_edge": hi}
    return {
        "scale_price": scale_price,
        "scale_pips": scale_price / PIP,
        "sigma1_price": sigma1,
        "pre_levels": levels,
        "pre_range_pips": pre_range / PIP,
    }


def path_frame(bars: pd.DataFrame, tr: Any, tf: int, context: dict[str, Any]) -> dict[str, Any]:
    entry = pd.Timestamp(tr.entry_utc); close = pd.Timestamp(tr.close_utc); side = int(tr.side)
    if tf == 1:
        q = bars[(bars.index >= entry) & ((bars.index + pd.Timedelta(minutes=1)) < close)].copy()
        completion = q.index + pd.Timedelta(minutes=1)
    else:
        q = bars[(bars.completion > entry) & (bars.completion < close)].copy()
        completion = pd.DatetimeIndex(q.completion)
    if q.empty:
        return {"n": 0}
    o, c, fav_px, adv_px = exec_fields(q, side)
    entry_price = float(tr.entry_price)
    ret = np.asarray(side_return(c, entry_price, side), float)
    fav = np.asarray(side_return(fav_px, entry_price, side), float)
    adv = np.asarray(side_return(adv_px, entry_price, side), float)
    mfe = np.maximum.accumulate(fav)
    mae = np.minimum.accumulate(adv)
    level_dist = side * (c - float(tr.breakout_level)) / PIP
    entry_dist = ret.copy()
    delta = np.diff(ret, prepend=0.0)
    return {
        "n": len(q), "frame": q, "completion": completion, "open": o, "close": c,
        "ret": ret, "fav": fav, "adv": adv, "mfe": mfe, "mae": mae,
        "level_dist": level_dist, "entry_dist": entry_dist, "delta": delta,
        "scale_pips": float(context["scale_pips"]),
        "sigma_pips": float(context["sigma1_price"] * math.sqrt(tf) / PIP),
        "tf": tf, "side": side,
    }


def event_level_reentry(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    level = p["level_dist"] if params["level"] == "breakout" else p["entry_dist"]
    mask = level <= 1e-12
    if params["arm"] == "unprofitable":
        mask &= p["mfe"] <= 1e-12
    return consecutive_first(mask, int(params["persistence"]))


def event_failed_reclaim(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    persistence = int(params["persistence"])
    inside = p["level_dist"] <= 1e-12
    first = consecutive_first(inside, persistence)
    if first is None:
        return None
    outside = p["level_dist"] > 1e-12
    reclaim = consecutive_first(outside, persistence, first + 1)
    if reclaim is None:
        return None
    failure = consecutive_first(inside, persistence, reclaim + 1)
    if failure is None:
        return None
    if p["mfe"][failure] > float(params["max_mfe_atr"]) * p["scale_pips"] + 1e-12:
        return None
    return failure


def event_cross_count(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    window_bars = max(2, int(math.ceil(int(params["window_minutes"]) / p["tf"])))
    signs = np.sign(p["level_dist"])
    for i in range(1, len(signs)):
        if signs[i] == 0:
            signs[i] = signs[i - 1]
    crosses = np.zeros(len(signs), dtype=int)
    crosses[1:] = (signs[1:] * signs[:-1] < 0).astype(int)
    cs = np.cumsum(crosses)
    for i in range(len(signs)):
        j = max(0, i - window_bars + 1)
        n = int(cs[i] - (cs[j - 1] if j else 0))
        if n >= int(params["crossings"]) and abs(p["level_dist"][i]) <= float(params["max_displacement_atr"]) * p["scale_pips"]:
            return i
    return None


def event_mfe_giveback(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    arm = float(params["arm_atr"]) * p["scale_pips"]
    give = float(params["giveback_frac"])
    cond = (p["mfe"] >= arm) & (p["ret"] <= p["mfe"] * (1.0 - give) + 1e-12)
    return consecutive_first(cond, int(params["persistence"]))


def event_stagnation(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    arm = float(params["arm_atr"]) * p["scale_pips"]
    give = float(params["giveback_frac"])
    stagnation_bars = max(1, int(math.ceil(int(params["stagnation_minutes"]) / p["tf"])))
    armed = np.flatnonzero(p["mfe"] >= arm)
    if len(armed) == 0:
        return None
    last_peak = int(armed[0]); peak = p["mfe"][last_peak]
    for i in range(last_peak + 1, p["n"]):
        if p["mfe"][i] > peak + 1e-12:
            peak = p["mfe"][i]; last_peak = i
        if i - last_peak >= stagnation_bars and p["ret"][i] <= peak * (1.0 - give) + 1e-12:
            return i
    return None


def event_channel_break(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    lb = int(params["lookback"]); pers = int(params["persistence"])
    mask = np.zeros(p["n"], dtype=bool)
    for i in range(lb, p["n"]):
        prior_min = float(np.min(p["ret"][i-lb:i]))
        mask[i] = p["ret"][i] < prior_min - 1e-12
        if params["arm"] == "positive":
            mask[i] &= p["mfe"][i] > 1e-12
    return consecutive_first(mask, pers, lb)


def event_adverse_run(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    n = int(params["bars"]); threshold = float(params["cumulative_atr"]) * p["scale_pips"]
    d = np.diff(p["ret"], prepend=0.0)
    for i in range(n - 1, p["n"]):
        w = d[i-n+1:i+1]
        if np.all(w < -1e-12) and -float(w.sum()) >= threshold - 1e-12:
            return i
    return None


def event_cusum(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    h = float(params["h"]); drift = float(params["drift"]); sigma = max(p["sigma_pips"], 1e-9)
    s = 0.0
    for i, d in enumerate(p["delta"]):
        s = min(0.0, s + d / sigma + drift)
        armed = params["arm"] == "any" or p["mfe"][i] > 1e-12
        if armed and s <= -h:
            return i
    return None


def event_slope(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    lb = int(params["lookback"]); threshold = float(params["tstat"])
    for i in range(lb - 1, p["n"]):
        armed = params["arm"] == "any" or p["mfe"][i] > 1e-12
        if armed and rolling_tstat(p["ret"][i-lb+1:i+1]) <= threshold:
            return i
    return None


def event_underwater(p1: dict[str, Any], params: dict[str, Any]) -> int | None:
    dur = int(params["duration_minutes"]); threshold = -float(params["depth_atr"]) * p1["scale_pips"]
    run = 0; reentered = False
    for i in range(p1["n"]):
        if p1["ret"][i] <= threshold + 1e-12:
            run += 1
            reentered = reentered or p1["level_dist"][i] <= 1e-12
        else:
            run = 0; reentered = False
        if run >= dur and (not bool(params["reentry_required"]) or reentered):
            return i
    return None


def event_vol_shock(p: dict[str, Any], params: dict[str, Any]) -> int | None:
    q = p["frame"]; side = int(p["side"])
    oc = side * (p["close"] - p["open"]) / PIP
    if side == 1:
        high = q["bid_high"].to_numpy(float); low = q["bid_low"].to_numpy(float)
        close_frac = (p["close"] - low) / np.maximum(high - low, 1e-12)
    else:
        high = q["ask_high"].to_numpy(float); low = q["ask_low"].to_numpy(float)
        close_frac = (high - p["close"]) / np.maximum(high - low, 1e-12)
    bar_range_pips = (high - low) / PIP
    cond = (
        (oc < -1e-12)
        & (bar_range_pips >= float(params["range_atr"]) * p["scale_pips"] - 1e-12)
        & (close_frac <= float(params["close_frac"]) + 1e-12)
    )
    if params["arm"] == "positive":
        cond &= p["mfe"] > 1e-12
    return consecutive_first(cond, 1)


def event_pre_range(p1: dict[str, Any], params: dict[str, Any], context: dict[str, Any], side: int) -> int | None:
    level = float(context["pre_levels"][int(params["pre_lookback"])][params["level"]])
    px = p1["close"]
    invalid = px <= level + 1e-12 if side == 1 else px >= level - 1e-12
    return consecutive_first(invalid, int(params["persistence"]))


def candidate_trigger(spec: dict[str, Any], paths: dict[int, dict[str, Any]], context: dict[str, Any], side: int) -> tuple[pd.Timestamp, int] | None:
    f = spec["family"]; x = spec["params"]
    tf = int(x.get("tf", 1)); p = paths[tf]
    if p.get("n", 0) == 0:
        return None
    idx: int | None
    if f == "LEVEL_REENTRY_PERSISTENCE": idx = event_level_reentry(p, x)
    elif f == "FAILED_RECLAIM_SEQUENCE": idx = event_failed_reclaim(p, x)
    elif f == "CROSS_COUNT_CHOP": idx = event_cross_count(p, x)
    elif f == "MFE_GIVEBACK": idx = event_mfe_giveback(p, x)
    elif f == "STAGNATION_GIVEBACK": idx = event_stagnation(p, x)
    elif f == "ROLLING_CHANNEL_BREAK": idx = event_channel_break(p, x)
    elif f == "ADVERSE_RUN": idx = event_adverse_run(p, x)
    elif f == "CUSUM_REVERSAL": idx = event_cusum(p, x)
    elif f == "SLOPE_BREAK": idx = event_slope(p, x)
    elif f == "TIME_UNDERWATER": idx = event_underwater(paths[1], x); p = paths[1]
    elif f == "VOL_SHOCK_REVERSAL": idx = event_vol_shock(p, x)
    elif f == "PRE_RANGE_INVALIDATION": idx = event_pre_range(paths[1], x, context, side); p = paths[1]
    else: raise KeyError(f)
    if idx is None:
        return None
    return pd.Timestamp(p["completion"][idx]), int(idx)


def exit_pips(m1: pd.DataFrame, tr: Any, trigger: pd.Timestamp, delay: int) -> tuple[pd.Timestamp, float] | None:
    target = trigger + pd.Timedelta(minutes=delay)
    q = m1[m1.index >= target]
    if q.empty or q.index[0] >= pd.Timestamp(tr.close_utc):
        return None
    row = q.iloc[0]; side = int(tr.side)
    px = float(row.bid_open if side == 1 else row.ask_open)
    return pd.Timestamp(q.index[0]), float(side_return(px, float(tr.entry_price), side))


def session_name(ts: pd.Timestamp) -> str:
    h = int(ts.hour)
    if 0 <= h < 7: return "ASIA"
    if 7 <= h < 13: return "LONDON"
    if 13 <= h < 20: return "NEW_YORK"
    return "OFF_HOURS"


def build_paths_and_events(
    trades: pd.DataFrame, m23: pd.DataFrame, m24: pd.DataFrame, specs: list[dict[str, Any]]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bars = {
        "2023": {1: m23.assign(completion=m23.index + pd.Timedelta(minutes=1)), 5: aggregate_bars(m23, 5), 15: aggregate_bars(m23, 15)},
        "2024": {1: m24.assign(completion=m24.index + pd.Timedelta(minutes=1)), 5: aggregate_bars(m24, 5), 15: aggregate_bars(m24, 15)},
    }
    event_rows: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    shapes: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for ntr, tr in enumerate(trades.itertuples(index=False), start=1):
        year = "2023" if str(tr.fold).startswith("2023") else "2024"
        m1_all = m23 if year == "2023" else m24
        context = pre_context(m1_all, pd.Timestamp(tr.entry_utc), int(tr.side))
        tf_paths = {tf: path_frame(bars[year][tf], tr, tf, context) for tf in [1, 5, 15]}
        p1 = tf_paths[1]
        if p1.get("n", 0) == 0:
            continue
        first_positive_idx = np.flatnonzero(p1["mfe"] > 1e-12)
        first_inside_idx = np.flatnonzero(p1["level_dist"] <= 1e-12)
        peak_idx = int(np.argmax(p1["mfe"]))
        diagnostics.append({
            "trade_id": tr.trade_id, "fold": tr.fold, "strategy": tr.strategy, "side": int(tr.side),
            "baseline_pips": float(tr.baseline_pips), "baseline_loser": bool(float(tr.baseline_pips) <= 0),
            "scale_pips": context["scale_pips"], "pre_range_pips": context["pre_range_pips"],
            "first_positive_minutes": None if len(first_positive_idx)==0 else int(first_positive_idx[0]+1),
            "first_breakout_reentry_minutes": None if len(first_inside_idx)==0 else int(first_inside_idx[0]+1),
            "peak_mfe_minutes": int(peak_idx+1), "final_mfe_pips": float(p1["mfe"][-1]),
            "final_mae_pips": float(p1["mae"][-1]), "underwater_fraction": float(np.mean(p1["ret"] <= 0)),
            "breakout_crossings": int(np.sum(np.sign(p1["level_dist"])[1:] * np.sign(p1["level_dist"][:-1]) < 0)),
            "session": session_name(pd.Timestamp(tr.entry_utc)),
        })

        for cp in CHECKPOINTS:
            trigger = pd.Timestamp(tr.entry_utc) + pd.Timedelta(minutes=cp)
            ex = exit_pips(m1_all.loc[pd.Timestamp(tr.entry_utc):pd.Timestamp(tr.close_utc)], tr, trigger, 0)
            q = p1["completion"] <= trigger
            if ex is None or not np.any(q):
                continue
            last = int(np.flatnonzero(q)[-1])
            recent = p1["ret"][max(0,last-14):last+1]
            crossings = int(np.sum(np.sign(p1["level_dist"][:last+1])[1:] * np.sign(p1["level_dist"][:last+1])[:-1] < 0))
            snapshots.append({
                "trade_id": tr.trade_id, "fold": tr.fold, "strategy": tr.strategy, "side": int(tr.side),
                "session": session_name(pd.Timestamp(tr.entry_utc)), "checkpoint": cp,
                "baseline_pips": float(tr.baseline_pips), "baseline_loser": int(float(tr.baseline_pips) <= 0),
                "exit_pips": ex[1], "delta_pips": ex[1] - float(tr.baseline_pips),
                "current_norm": p1["ret"][last] / context["scale_pips"],
                "mfe_norm": p1["mfe"][last] / context["scale_pips"],
                "mae_norm": p1["mae"][last] / context["scale_pips"],
                "giveback_norm": (p1["mfe"][last] - p1["ret"][last]) / context["scale_pips"],
                "level_distance_norm": p1["level_dist"][last] / context["scale_pips"],
                "underwater_fraction": float(np.mean(p1["ret"][:last+1] <= 0)),
                "crossings": crossings,
                "realized_range_norm": (float(np.max(p1["fav"][:last+1])) - float(np.min(p1["adv"][:last+1]))) / context["scale_pips"],
                "slope_tstat": rolling_tstat(recent),
                "pre_range_pips": context["pre_range_pips"],
                "breakout_distance_norm": (int(tr.side)*(float(tr.entry_bid)-float(tr.breakout_level))/PIP) / context["scale_pips"],
            })
            p5 = tf_paths[5]
            mask5 = p5["completion"] <= trigger
            vals = p5["ret"][mask5] / context["scale_pips"] if p5.get("n",0) else np.array([])
            need = cp // 5
            if len(vals) >= need:
                row = {"trade_id": tr.trade_id, "fold": tr.fold, "strategy": tr.strategy, "side": int(tr.side),
                       "checkpoint": cp, "baseline_pips": float(tr.baseline_pips), "baseline_loser": int(float(tr.baseline_pips)<=0),
                       "exit_pips": ex[1], "delta_pips": ex[1]-float(tr.baseline_pips)}
                row.update({f"v{i+1}": float(vals[i]) for i in range(need)})
                shapes.append(row)

        m1_window = m1_all.loc[pd.Timestamp(tr.entry_utc):pd.Timestamp(tr.close_utc)]
        for spec in specs:
            hit = candidate_trigger(spec, tf_paths, context, int(tr.side))
            if hit is None:
                continue
            trigger, _ = hit
            exits = {d: exit_pips(m1_window, tr, trigger, d) for d in [0,1,2,5]}
            if exits[0] is None:
                continue
            cp = exits[0][1]
            baseline = float(tr.baseline_pips)
            event_rows.append({
                "candidate_id": spec["candidate_id"], "family": spec["family"], "params_json": json.dumps(spec["params"], sort_keys=True),
                "trade_id": tr.trade_id, "fold": tr.fold, "strategy": tr.strategy, "side": int(tr.side),
                "entry_utc": tr.entry_utc, "trigger_utc": trigger, "exit_utc": exits[0][0],
                "session": session_name(pd.Timestamp(tr.entry_utc)), "baseline_pips": baseline,
                "baseline_loser": bool(baseline <= 0), "candidate_pips": cp, "delta_pips": cp-baseline,
                "severe1_delta_pips": cp-1.0-baseline, "severe2_delta_pips": cp-2.0-baseline,
                "delay1_delta_pips": None if exits[1] is None else exits[1][1]-baseline,
                "delay2_delta_pips": None if exits[2] is None else exits[2][1]-baseline,
                "delay5_delta_pips": None if exits[5] is None else exits[5][1]-baseline,
                "trigger_minutes": int((trigger-pd.Timestamp(tr.entry_utc)).total_seconds()/60),
                "scale_pips": context["scale_pips"], "pre_range_pips": context["pre_range_pips"],
            })
        if ntr % 100 == 0:
            print(json.dumps({"progress_trades": ntr, "events": len(event_rows)}, sort_keys=True), file=sys.stderr)
    return pd.DataFrame(event_rows), pd.DataFrame(snapshots), pd.DataFrame(shapes), pd.DataFrame(diagnostics)


def scope_filter(df: pd.DataFrame, scope: str) -> pd.DataFrame:
    return df if scope == "ALL" else df[df.strategy == scope]


def bh_adjust(pvalues: pd.Series) -> pd.Series:
    n = len(pvalues); order = np.argsort(pvalues.to_numpy(float)); out = np.empty(n, float); prev = 1.0
    vals = pvalues.to_numpy(float)
    for rank_rev, idx in enumerate(order[::-1], start=1):
        rank = n - rank_rev + 1
        prev = min(prev, vals[idx] * n / rank)
        out[idx] = prev
    return pd.Series(out, index=pvalues.index)


def date_pvalue(g: pd.DataFrame, all_dates: pd.Index) -> float:
    d = g.assign(date=pd.to_datetime(g.entry_utc, utc=True).dt.strftime("%Y-%m-%d")).groupby("date").delta_pips.sum().reindex(all_dates, fill_value=0.0)
    z = d[d != 0].to_numpy(float)
    if len(z) < 5:
        return 1.0
    try:
        return float(wilcoxon(z, alternative="greater", zero_method="wilcox").pvalue)
    except ValueError:
        return 1.0


def metrics_one(g: pd.DataFrame, scope_trades: pd.DataFrame, folds: Iterable[str] = FOLDS) -> dict[str, Any]:
    losers = g[g.baseline_loser]; winners = g[~g.baseline_loser]
    fold = g.groupby("fold").delta_pips.sum().reindex(list(folds), fill_value=0.0)
    fold_severe = g.groupby("fold").severe1_delta_pips.sum().reindex(list(folds), fill_value=0.0)
    direction = g.groupby("side").delta_pips.sum().reindex([1,-1], fill_value=0.0)
    strat = g.groupby("strategy").delta_pips.sum().reindex(["B02","F05"], fill_value=0.0)
    date = g.assign(date=pd.to_datetime(g.entry_utc, utc=True).dt.strftime("%Y-%m-%d")).groupby("date").delta_pips.sum().sort_values(ascending=False)
    month = g.assign(month=pd.to_datetime(g.entry_utc, utc=True).dt.strftime("%Y-%m")).groupby("month").delta_pips.sum()
    total = float(g.delta_pips.sum()); severe1=float(g.severe1_delta_pips.sum()); severe2=float(g.severe2_delta_pips.sum())
    delay2=float(g.delay2_delta_pips.fillna(0).sum()); delay5=float(g.delay5_delta_pips.fillna(0).sum())
    benefit=float(losers.delta_pips.sum()); damage=float(winners.delta_pips.sum())
    min_triggers = 15 if len(scope_trades) > 1000 else (12 if len(scope_trades)>500 else 8)
    active_months=int(len(month)); positive_months=int((month>0).sum())
    exbest=total-(float(date.iloc[0]) if len(date) else 0.0)
    prelim=(
        len(g)>=min_triggers and len(losers)>=max(5,min_triggers//2) and total>0 and severe1>0 and delay2>0
        and float(fold.min())>=0 and float(fold_severe.min())>=0 and float(direction.min())>=0
        and exbest>0 and (benefit>0) and damage>=-0.60*benefit
        and active_months>=4 and positive_months/max(active_months,1)>=0.60
    )
    return {
        "triggers":int(len(g)),"losers_triggered":int(len(losers)),"winners_triggered":int(len(winners)),
        "loser_coverage":round(len(losers)/max(int((scope_trades.baseline_pips<=0).sum()),1),6),
        "loser_benefit_pips":round(benefit,1),"winner_damage_pips":round(damage,1),"total_delta_pips":round(total,1),
        "severe1_delta_pips":round(severe1,1),"severe2_delta_pips":round(severe2,1),
        "delay2_delta_pips":round(delay2,1),"delay5_delta_pips":round(delay5,1),
        "fold_delta_pips":json.dumps({f:round(float(fold[f]),1) for f in folds},sort_keys=True),
        "fold_severe1_pips":json.dumps({f:round(float(fold_severe[f]),1) for f in folds},sort_keys=True),
        "long_delta_pips":round(float(direction[1]),1),"short_delta_pips":round(float(direction[-1]),1),
        "b02_delta_pips":round(float(strat["B02"]),1),"f05_delta_pips":round(float(strat["F05"]),1),
        "active_months":active_months,"positive_months":positive_months,"ex_best_date_delta_pips":round(exbest,1),
        "median_trigger_minutes":float(g.trigger_minutes.median()) if len(g) else math.nan,
        "preliminary_pass":bool(prelim),
        "conservative_score":round(min(total,severe1,delay2,exbest,float(fold.min())*len(list(folds))),1),
    }


def candidate_metrics(events: pd.DataFrame, trades: pd.DataFrame, specs: list[dict[str, Any]]) -> pd.DataFrame:
    rows=[]
    spec_map={x["candidate_id"]:x for x in specs}
    for scope in SCOPES:
        st=scope_filter(trades,scope); se=scope_filter(events,scope)
        all_dates=pd.Index(sorted(pd.to_datetime(st.entry_utc,utc=True).dt.strftime("%Y-%m-%d").unique()))
        grouped={cid:g for cid,g in se.groupby("candidate_id")}
        for cid,spec in spec_map.items():
            g=grouped.get(cid,se.iloc[0:0])
            m=metrics_one(g,st)
            m.update({"scope":scope,"candidate_id":cid,"family":spec["family"],"params_json":json.dumps(spec["params"],sort_keys=True)})
            m["date_pvalue"]=date_pvalue(g,all_dates)
            rows.append(m)
    out=pd.DataFrame(rows)
    out["date_qvalue"]=out.groupby("scope").date_pvalue.transform(bh_adjust)
    return out


def adjacent(a: dict[str, Any], b: dict[str, Any], grids: dict[str, dict[str,list[Any]]]) -> bool:
    if a["family"]!=b["family"]: return False
    pa=a["params"]; pb=b["params"]; diffs=[k for k in pa if pa[k]!=pb[k]]
    if len(diffs)!=1: return False
    k=diffs[0]; vals=grids[a["family"]][k]
    try: return abs(vals.index(pa[k])-vals.index(pb[k]))==1
    except ValueError: return False


def apply_region_gate(metrics: pd.DataFrame, specs: list[dict[str, Any]], protocol: dict[str,Any]) -> pd.DataFrame:
    grids={x["family"]:x["grid"] for x in protocol["deterministic_families"]}
    spec_map={x["candidate_id"]:x for x in specs}
    metrics=metrics.copy(); metrics["preliminary_neighbors"]=0
    for scope,g in metrics.groupby("scope"):
        prelim=set(g[g.preliminary_pass].candidate_id)
        for idx,row in g.iterrows():
            if row.candidate_id not in prelim: continue
            n=sum(adjacent(spec_map[row.candidate_id],spec_map[o],grids) for o in prelim if o!=row.candidate_id)
            metrics.loc[idx,"preliminary_neighbors"]=n
    metrics["exact_discovery_eligible"]=(metrics.preliminary_pass & (metrics.date_qvalue<=0.10) & (metrics.preliminary_neighbors>=2))
    return metrics


def training_gate(g: pd.DataFrame, st: pd.DataFrame, train_folds: list[str]) -> tuple[bool,float]:
    if g.empty: return False,-1e18
    m=metrics_one(g,st,train_folds)
    ok=(m["triggers"]>=8 and m["losers_triggered"]>=5 and m["total_delta_pips"]>0 and m["severe1_delta_pips"]>0
        and m["delay2_delta_pips"]>0 and min(json.loads(m["fold_delta_pips"]).values())>=0
        and m["ex_best_date_delta_pips"]>0 and m["winner_damage_pips"]>=-0.7*max(m["loser_benefit_pips"],1e-9))
    return ok,float(m["conservative_score"])


def nested_family_cv(events: pd.DataFrame, trades: pd.DataFrame, specs: list[dict[str,Any]]) -> pd.DataFrame:
    rows=[]; spec_df=pd.DataFrame(specs)
    for scope in SCOPES:
        st=scope_filter(trades,scope); se=scope_filter(events,scope)
        for family,fs in spec_df.groupby("family"):
            ids=fs.candidate_id.tolist()
            for holdout in FOLDS:
                train=[f for f in FOLDS if f!=holdout]
                st_train=st[st.fold.isin(train)]
                candidates=[]
                for cid in ids:
                    g=se[(se.candidate_id==cid)&(se.fold.isin(train))]
                    ok,score=training_gate(g,st_train,train)
                    if ok: candidates.append((score,cid))
                if not candidates:
                    rows.append({"scope":scope,"family":family,"holdout":holdout,"selected_candidate":None,"train_eligible":0,"holdout_triggers":0,"holdout_delta_pips":0.0,"holdout_severe1_pips":0.0,"holdout_delay2_pips":0.0})
                    continue
                candidates.sort(reverse=True); cid=candidates[0][1]
                h=se[(se.candidate_id==cid)&(se.fold==holdout)]
                rows.append({"scope":scope,"family":family,"holdout":holdout,"selected_candidate":cid,"train_eligible":len(candidates),
                             "holdout_triggers":len(h),"holdout_delta_pips":round(float(h.delta_pips.sum()),1),
                             "holdout_severe1_pips":round(float(h.severe1_delta_pips.sum()),1),"holdout_delay2_pips":round(float(h.delay2_delta_pips.fillna(0).sum()),1)})
    out=pd.DataFrame(rows)
    return out


def prep_model_matrix(train: pd.DataFrame, test: pd.DataFrame) -> tuple[np.ndarray,np.ndarray,np.ndarray,np.ndarray,list[str]]:
    features=["current_norm","mfe_norm","mae_norm","giveback_norm","level_distance_norm","underwater_fraction","crossings","realized_range_norm","slope_tstat","pre_range_pips","breakout_distance_norm"]
    a=train[features+["strategy","session","side"]].copy(); b=test[features+["strategy","session","side"]].copy()
    both=pd.concat([a,b],ignore_index=True)
    both=pd.get_dummies(both,columns=["strategy","session","side"],dtype=float)
    both=both.replace([np.inf,-np.inf],np.nan).fillna(0.0)
    X=both.iloc[:len(a)].to_numpy(float); Z=both.iloc[len(a):].to_numpy(float)
    y=train.baseline_loser.to_numpy(int); yt=test.baseline_loser.to_numpy(int)
    return X,y,Z,yt,both.columns.tolist()


def fit_model(name:str,X:np.ndarray,y:np.ndarray):
    if name=="LOGISTIC_L2":
        scaler=StandardScaler(); Xs=scaler.fit_transform(X); model=LogisticRegression(C=1.0,max_iter=2000,class_weight="balanced",random_state=17).fit(Xs,y); return lambda z:model.predict_proba(scaler.transform(z))[:,1]
    if name=="TREE_D2":
        model=DecisionTreeClassifier(max_depth=2,min_samples_leaf=20,class_weight="balanced",random_state=17).fit(X,y); return lambda z:model.predict_proba(z)[:,1]
    if name=="TREE_D3":
        model=DecisionTreeClassifier(max_depth=3,min_samples_leaf=20,class_weight="balanced",random_state=17).fit(X,y); return lambda z:model.predict_proba(z)[:,1]
    if name=="HIST_GB":
        model=HistGradientBoostingClassifier(max_leaf_nodes=7,max_iter=100,learning_rate=0.05,l2_regularization=1.0,random_state=17).fit(X,y); return lambda z:model.predict_proba(z)[:,1]
    raise KeyError(name)


def model_selection_score(df:pd.DataFrame,probs:np.ndarray,threshold:float)->tuple[bool,float,dict[str,float]]:
    mask=probs>=threshold; g=df.loc[mask]
    if len(g)==0:return False,-1e18,{}
    losers=g[g.baseline_loser==1]; winners=g[g.baseline_loser==0]
    total=float(g.delta_pips.sum()); severe=total-len(g); benefit=float(losers.delta_pips.sum()); damage=float(winners.delta_pips.sum())
    fold=g.groupby("fold").delta_pips.sum()
    ok=len(g)>=10 and len(losers)>=6 and total>0 and severe>0 and (len(fold)==3 and fold.min()>=0) and benefit>0 and damage>=-0.7*benefit
    score=min(total,severe,float(fold.min())*3 if len(fold) else -1e18)
    return ok,score,{"triggers":len(g),"delta":total,"severe":severe,"benefit":benefit,"damage":damage}


def nested_model_cv(snapshots:pd.DataFrame)->pd.DataFrame:
    rows=[]; thresholds=[0.50,0.60,0.70,0.80,0.90]
    for scope in SCOPES:
        d=scope_filter(snapshots,scope)
        for cp in CHECKPOINTS:
            x=d[d.checkpoint==cp]
            for holdout in FOLDS:
                tr=x[x.fold!=holdout].copy(); te=x[x.fold==holdout].copy()
                if len(tr)<100 or len(te)<20 or tr.baseline_loser.nunique()<2: continue
                X,y,Z,_,_=prep_model_matrix(tr,te)
                for name in MODEL_NAMES:
                    pred=fit_model(name,X,y); ptrain=pred(X); ptest=pred(Z)
                    eligible=[]
                    for th in thresholds:
                        ok,score,diag=model_selection_score(tr,ptrain,th)
                        if ok: eligible.append((score,th,diag))
                    if not eligible:
                        rows.append({"scope":scope,"checkpoint":cp,"model":name,"holdout":holdout,"selected_threshold":None,"train_eligible":0,"holdout_triggers":0,"holdout_delta_pips":0.0,"holdout_severe1_pips":0.0,"holdout_winner_damage_pips":0.0})
                        continue
                    eligible.sort(reverse=True,key=lambda z:z[0]); th=eligible[0][1]
                    g=te.loc[ptest>=th]; w=g[g.baseline_loser==0]
                    rows.append({"scope":scope,"checkpoint":cp,"model":name,"holdout":holdout,"selected_threshold":th,"train_eligible":len(eligible),
                                 "holdout_triggers":len(g),"holdout_delta_pips":round(float(g.delta_pips.sum()),1),
                                 "holdout_severe1_pips":round(float(g.delta_pips.sum()-len(g)),1),"holdout_winner_damage_pips":round(float(w.delta_pips.sum()),1)})
    return pd.DataFrame(rows)


def nested_kmeans_cv(shapes:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for scope in SCOPES:
        d=scope_filter(shapes,scope)
        for cp in [30,60]:
            x=d[d.checkpoint==cp].copy(); vec=[f"v{i+1}" for i in range(cp//5)]
            for k in [3,4,5]:
                for holdout in FOLDS:
                    tr=x[x.fold!=holdout].dropna(subset=vec); te=x[x.fold==holdout].dropna(subset=vec)
                    if len(tr)<k*20 or len(te)<20: continue
                    scaler=StandardScaler(); X=scaler.fit_transform(tr[vec]); Z=scaler.transform(te[vec])
                    km=KMeans(n_clusters=k,n_init=20,random_state=17).fit(X)
                    tc=km.labels_; hc=km.predict(Z); base_rate=float(tr.baseline_loser.mean())
                    selected=[]
                    for cl in range(k):
                        g=tr[tc==cl]; los=g[g.baseline_loser==1]; win=g[g.baseline_loser==0]
                        total=float(g.delta_pips.sum()); benefit=float(los.delta_pips.sum()); damage=float(win.delta_pips.sum())
                        if len(g)>=10 and float(g.baseline_loser.mean())>=base_rate+0.10 and total>0 and total-len(g)>0 and benefit>0 and damage>=-0.7*benefit:
                            selected.append(cl)
                    mask=np.isin(hc,selected); g=te[mask]; w=g[g.baseline_loser==0]
                    rows.append({"scope":scope,"checkpoint":cp,"k":k,"holdout":holdout,"selected_clusters":json.dumps(selected),"holdout_triggers":len(g),
                                 "holdout_delta_pips":round(float(g.delta_pips.sum()),1),"holdout_severe1_pips":round(float(g.delta_pips.sum()-len(g)),1),
                                 "holdout_winner_damage_pips":round(float(w.delta_pips.sum()),1)})
    return pd.DataFrame(rows)


def survival_diagnostics(diag:pd.DataFrame)->dict[str,Any]:
    out={}
    for strategy in ["B02","F05"]:
        s=diag[diag.strategy==strategy]
        out[strategy]={}
        for feature in ["first_positive_minutes","first_breakout_reentry_minutes","peak_mfe_minutes","underwater_fraction","breakout_crossings","final_mfe_pips","final_mae_pips"]:
            a=pd.to_numeric(s.loc[~s.baseline_loser,feature],errors="coerce").dropna(); b=pd.to_numeric(s.loc[s.baseline_loser,feature],errors="coerce").dropna()
            if len(a)<3 or len(b)<3: continue
            u=mannwhitneyu(a,b,alternative="two-sided")
            delta=2*float(u.statistic)/(len(a)*len(b))-1
            out[strategy][feature]={"winner_median":round(float(a.median()),4),"loser_median":round(float(b.median()),4),"rank_biserial":round(delta,4),"pvalue":float(u.pvalue)}
    return out


def aggregate_cv(cv:pd.DataFrame,keys:list[str])->list[dict[str,Any]]:
    rows=[]
    for k,g in cv.groupby(keys,dropna=False):
        if not isinstance(k,tuple):k=(k,)
        row=dict(zip(keys,k)); row.update({
            "folds":int(g.holdout.nunique()),"holdout_triggers":int(g.holdout_triggers.sum()),
            "holdout_delta_pips":round(float(g.holdout_delta_pips.sum()),1),"holdout_severe1_pips":round(float(g.holdout_severe1_pips.sum()),1),
            "all_fold_default_nonnegative":bool((g.holdout_delta_pips>=0).all()),"all_fold_severe_nonnegative":bool((g.holdout_severe1_pips>=0).all()),
        }); rows.append(row)
    return rows


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--protocol",type=Path,required=True); ap.add_argument("--preflight-only",action="store_true")
    ap.add_argument("--m15-2023",type=Path);ap.add_argument("--m1-2023",type=Path);ap.add_argument("--events-2024h1",type=Path);ap.add_argument("--events-2024h2",type=Path);ap.add_argument("--m1-2024",type=Path)
    ap.add_argument("--out-dir",type=Path);ap.add_argument("--research-commit",default="");ap.add_argument("--workflow-run-id",default="");ap.add_argument("--workflow-run-attempt",default="")
    args=ap.parse_args(); protocol=verify_protocol(args.protocol); specs=generate_specs(protocol)
    preflight={"schema_version":"usdjpy_b02_f05_structural_sl_atlas_preflight_v2","status":"PASS_NO_OUTCOMES","protocol_sha256":sha256_file(args.protocol),"evaluator_sha256":sha256_file(Path(__file__)),"candidate_count":len(specs),"families":len(protocol["deterministic_families"]),"supervised_models":MODEL_NAMES,"outcomes_computed":False,"portfolio_replay_computed":False,"mt4_accessed":False,"2025_accessed":False,"notion_task_dependency":False}
    if args.preflight_only:
        print(json.dumps(preflight,indent=2,sort_keys=True));return 0
    required=[args.m15_2023,args.m1_2023,args.events_2024h1,args.events_2024h2,args.m1_2024,args.out_dir]
    if any(x is None for x in required):raise SystemExit("full evaluation requires all authorities and --out-dir")
    args.out_dir.mkdir(parents=True,exist_ok=True);write_json(args.out_dir/"preflight_result_v2.json",preflight)
    trades,m23,m24,actual_sha=load_authorities(args)
    events,snapshots,shapes,diag=build_paths_and_events(trades,m23,m24,specs)
    metrics=apply_region_gate(candidate_metrics(events,trades,specs),specs,protocol)
    family_cv=nested_family_cv(events,trades,specs)
    model_cv=nested_model_cv(snapshots)
    kmeans_cv=nested_kmeans_cv(shapes)
    surv=survival_diagnostics(diag)

    exact=metrics[metrics.exact_discovery_eligible].sort_values(["scope","conservative_score"],ascending=[True,False])
    family_agg=aggregate_cv(family_cv,["scope","family"])
    model_agg=aggregate_cv(model_cv,["scope","checkpoint","model"])
    kmeans_agg=aggregate_cv(kmeans_cv,["scope","checkpoint","k"])
    cv_promising=[x for x in family_agg if x["all_fold_default_nonnegative"] and x["all_fold_severe_nonnegative"] and x["holdout_delta_pips"]>0 and x["holdout_triggers"]>=10]
    model_promising=[x for x in model_agg if x["all_fold_default_nonnegative"] and x["all_fold_severe_nonnegative"] and x["holdout_delta_pips"]>0 and x["holdout_triggers"]>=10]
    kmeans_promising=[x for x in kmeans_agg if x["all_fold_default_nonnegative"] and x["all_fold_severe_nonnegative"] and x["holdout_delta_pips"]>0 and x["holdout_triggers"]>=10]
    status="ATLAS_COMPLETE_SHORTLIST_READY_FOR_FULL_REPLAY" if len(exact) or cv_promising or model_promising or kmeans_promising else "ATLAS_COMPLETE_NO_ROBUST_FAMILY"

    events.to_csv(args.out_dir/"deterministic_event_ledger_v2.csv.gz",index=False,compression="gzip",float_format="%.6f")
    metrics.to_csv(args.out_dir/"deterministic_candidate_metrics_v2.csv",index=False,float_format="%.6f")
    family_cv.to_csv(args.out_dir/"deterministic_nested_cv_v2.csv",index=False,float_format="%.6f")
    model_cv.to_csv(args.out_dir/"supervised_nested_cv_v2.csv",index=False,float_format="%.6f")
    kmeans_cv.to_csv(args.out_dir/"unsupervised_nested_cv_v2.csv",index=False,float_format="%.6f")
    diag.to_csv(args.out_dir/"trajectory_diagnostics_v2.csv",index=False,float_format="%.6f")
    result={
        "schema_version":"usdjpy_b02_f05_structural_sl_atlas_result_v2","status":status,
        "research_commit":args.research_commit,"workflow_run_id":int(args.workflow_run_id) if args.workflow_run_id else None,"workflow_run_attempt":int(args.workflow_run_attempt) if args.workflow_run_attempt else None,
        "source_sha256":actual_sha,"population":{"trade_count":len(trades),"baseline_loser_count":int((trades.baseline_pips<=0).sum()),"counts":EXPECTED_COUNTS},
        "search":{"deterministic_candidate_count":len(specs),"deterministic_family_count":len(protocol["deterministic_families"]),"event_rows":len(events),"checkpoint_snapshots":len(snapshots),"shape_rows":len(shapes),"methods":["deterministic_structural_grid","leave_one_fold_out_family_selection","date_level_multiple_testing_control","cost_and_delay_robustness","supervised_checkpoint_models","unsupervised_path_clustering","trajectory_survival_diagnostics"]},
        "deterministic":{"exact_discovery_eligible_count":len(exact),"exact_discovery_eligible":exact.head(25).to_dict("records"),"nested_cv_promising":cv_promising,"top_by_scope":metrics.sort_values(["scope","conservative_score"],ascending=[True,False]).groupby("scope").head(10).to_dict("records")},
        "supervised":{"nested_cv_promising":model_promising,"aggregate":model_agg},
        "unsupervised":{"nested_cv_promising":kmeans_promising,"aggregate":kmeans_agg},
        "trajectory_diagnostics":surv,
        "decision":{"candidate_frozen":False,"implementation_authorized":False,"full_admission_portfolio_replay_required_for_any_shortlist":True,"raw_tick_event_order_required_for_2024_shortlist":True,"mt4_parity_required_after_research_confirmation":True},
        "boundaries":{"fixed_pip_stop_evaluated":False,"existing_accepted_trade_overlay_computed":True,"full_admission_portfolio_replay_computed":False,"mt4_accessed":False,"2025H1_accessed":False,"2025H2_accessed":False,"notion_used_as_task_source":False,"closed_hypotheses_reopened":False},
    }
    write_json(args.out_dir/"result_v2.json",result)
    manifest={"schema_version":"usdjpy_b02_f05_structural_sl_atlas_output_manifest_v2","files":{p.name:{"bytes":p.stat().st_size,"sha256":sha256_file(p)} for p in sorted(args.out_dir.iterdir()) if p.is_file()}}
    write_json(args.out_dir/"output_manifest_v2.json",manifest)
    print(json.dumps({"status":status,"trades":len(trades),"candidates":len(specs),"events":len(events),"exact":len(exact),"cv_promising":len(cv_promising),"model_promising":len(model_promising),"kmeans_promising":len(kmeans_promising)},sort_keys=True))
    return 0

if __name__=="__main__":raise SystemExit(main())
