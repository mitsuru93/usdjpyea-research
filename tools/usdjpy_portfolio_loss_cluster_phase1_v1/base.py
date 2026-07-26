#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]
PIP = 0.01
START_BALANCE = 100000.0
SEED = 20260726


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def iso(ts: Any) -> str | None:
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def pf(series: pd.Series) -> float | None:
    x = pd.to_numeric(series, errors="coerce").fillna(0.0)
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    if gl == 0:
        return None if gp == 0 else math.inf
    return gp / gl


def session_label(ts: pd.Timestamp) -> str:
    h = int(ts.hour)
    if 0 <= h < 7:
        return "Tokyo"
    if 7 <= h < 13:
        return "London"
    if 13 <= h < 16:
        return "London_NY_overlap"
    if 16 <= h < 20:
        return "New_York"
    return "session_transition"


def session_key(ts: pd.Timestamp) -> str:
    return f"{ts.strftime('%Y-%m-%d')}|{session_label(ts)}"


def load_trade_diag(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path, compression="gzip" if path.suffix == ".gz" else None)
    for c in ["signal_utc", "entry_utc", "close_utc", "first_positive_utc", "established_utc", "mfe_utc"]:
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], utc=True, errors="coerce")
    if "trade_id" not in d:
        d["trade_id"] = (
            d.fold.astype(str) + "|" + d.strategy.astype(str) + "|" + d.entry_utc.astype(str) + "|" + d.side.astype(int).astype(str)
        )
    d["side"] = d.side.astype(int)
    d["winner"] = d.realized_pl_jpy.astype(float) > 0
    d["session"] = d.entry_utc.map(session_label)
    d["entry_session_key"] = d.entry_utc.map(session_key)
    d["exit_session"] = d.close_utc.map(session_label)
    d["exit_session_key"] = d.close_utc.map(session_key)
    d["month"] = d.entry_utc.dt.strftime("%Y-%m")
    d["entry_date"] = d.entry_utc.dt.strftime("%Y-%m-%d")
    d["normalized_exposure"] = 1.0
    assert len(d) == 1882
    assert d.trade_id.nunique() == 1882
    assert set(d.fold) == set(FOLDS)
    return d.sort_values(["entry_utc", "strategy", "trade_id"], kind="mergesort").reset_index(drop=True)


def load_states(path: Path) -> pd.DataFrame:
    s = pd.read_csv(path, compression="gzip" if path.suffix == ".gz" else None)
    s["observation_utc"] = pd.to_datetime(s.observation_utc, utc=True)
    s["observation_index"] = s.observation_index.astype(int)
    s["executable_pips"] = s.executable_pips.astype(float)
    s = s.sort_values(["trade_id", "observation_utc"], kind="mergesort").reset_index(drop=True)
    s["running_min_pips"] = s.groupby("trade_id", sort=False).executable_pips.cummin()
    s["running_max_pips"] = s.groupby("trade_id", sort=False).executable_pips.cummax()
    assert s.trade_id.nunique() == 1882
    return s


def load_market(m15_2023: Path, m15_2024h1: Path, events_2024h2: Path) -> pd.DataFrame:
    a = pd.read_csv(m15_2023)
    a = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(a.timestamp_utc, utc=True),
        "open": a.open.astype(float), "high": a.high.astype(float), "low": a.low.astype(float), "close": a.close.astype(float),
    })
    b = pd.read_csv(m15_2024h1)
    b = pd.DataFrame({
        "timestamp_utc": pd.to_datetime(b.utc_time, utc=True),
        "open": b.open.astype(float), "high": b.high.astype(float), "low": b.low.astype(float), "close": b.close.astype(float),
    })
    e = pd.read_csv(events_2024h2)
    e = e[e.event.eq("portfolio_snapshot")].copy()
    e["timestamp_utc"] = pd.to_datetime(e.utc_time, utc=True)
    e = e[e.timestamp_utc.dt.year.eq(2024)].sort_values("timestamp_utc").drop_duplicates("timestamp_utc", keep="last")
    c = pd.DataFrame({"timestamp_utc": e.timestamp_utc, "open": e.price.astype(float), "high": e.price.astype(float), "low": e.price.astype(float), "close": e.price.astype(float)})
    out = []
    for fold, frame, lo, hi in [
        ("2023H1", a, "2023-01-01", "2023-07-01"),
        ("2023H2", a, "2023-07-01", "2024-01-01"),
        ("2024H1", b, "2024-01-01", "2024-07-01"),
        ("2024H2", c, "2024-07-01", "2025-01-01"),
    ]:
        g = frame[(frame.timestamp_utc >= pd.Timestamp(lo, tz="UTC")) & (frame.timestamp_utc < pd.Timestamp(hi, tz="UTC"))].copy()
        g = g.sort_values("timestamp_utc").drop_duplicates("timestamp_utc", keep="last")
        g["fold"] = fold
        g["abs_open_move_pips"] = g.open.diff().abs() / PIP
        shifted = g.abs_open_move_pips.shift(1)
        g["trail_med96"] = shifted.rolling(96, min_periods=32).median()
        g["trail_q25"] = shifted.rolling(96, min_periods=32).quantile(0.25)
        g["trail_q75"] = shifted.rolling(96, min_periods=32).quantile(0.75)
        g["trail_q95"] = shifted.rolling(96, min_periods=32).quantile(0.95)
        threshold = np.maximum(15.0, np.maximum(g.trail_q95.fillna(15.0), 4.0 * g.trail_med96.fillna(0.0)))
        g["shock"] = g.abs_open_move_pips.ge(threshold)
        g["volatility_state"] = np.select(
            [g.shock, g.abs_open_move_pips.le(g.trail_q25), g.abs_open_move_pips.le(g.trail_q75)],
            ["shock", "contraction", "normal"], default="expansion"
        )
        last_shock = pd.NaT
        elapsed = []
        for r in g.itertuples(index=False):
            if bool(r.shock):
                last_shock = r.timestamp_utc
            elapsed.append(np.nan if pd.isna(last_shock) else (r.timestamp_utc - last_shock).total_seconds() / 60.0)
        g["shock_elapsed_min"] = elapsed
        g.loc[(~g.shock) & g.shock_elapsed_min.le(60), "volatility_state"] = "post_shock"
        out.append(g)
    return pd.concat(out, ignore_index=True)


def market_at_entries(d: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for fold in FOLDS:
        t = d[d.fold.eq(fold)].sort_values("entry_utc")
        m = market[market.fold.eq(fold)].sort_values("timestamp_utc")
        z = pd.merge_asof(
            t[["trade_id", "entry_utc"]],
            m[["timestamp_utc", "abs_open_move_pips", "volatility_state", "shock_elapsed_min", "shock"]],
            left_on="entry_utc", right_on="timestamp_utc", direction="backward", tolerance=pd.Timedelta(minutes=15),
        )
        z["fold"] = fold
        rows.append(z)
    return pd.concat(rows, ignore_index=True).drop(columns=["timestamp_utc"])

