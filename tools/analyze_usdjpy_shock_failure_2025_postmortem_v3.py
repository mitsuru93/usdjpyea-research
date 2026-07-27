#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import re
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance

PIP = 0.01
JPY_PER_PIP_001 = 10.0
FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2", "2025H1", "2025H2"]
DEV_FOLDS = FOLDS[:4]
EXT_FOLDS = FOLDS[4:]
ORACLE_LABEL = "ORACLE_DIAGNOSTIC_NOT_IMPLEMENTABLE_CANDIDATE"


def clean(v):
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else float(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v


def write_json(path: Path, obj):
    path.write_text(json.dumps(clean(obj), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv_robust(path: Path, **kwargs):
    path = Path(path)
    raw = path.read_bytes()
    has_gzip_magic = raw[:2] == b"\x1f\x8b"
    if path.suffix.lower() == ".gz" and not has_gzip_magic:
        raise RuntimeError(f"gzip suffix without gzip magic: {path}")
    if has_gzip_magic:
        try:
            raw = gzip.decompress(raw)
        except OSError as exc:
            raise RuntimeError(f"invalid gzip payload: {path}") from exc
    for encoding in ("utf-8-sig", "utf-8", "cp932", "cp1252", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"unable to decode CSV: {path}")


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pf(values):
    s = pd.Series(values, dtype=float)
    gp = s[s > 0].sum()
    gl = -s[s < 0].sum()
    return None if gl <= 0 else float(gp / gl)


def maxdd(values):
    s = pd.Series(values, dtype=float).cumsum()
    if s.empty:
        return 0.0
    return float((s.cummax() - s).max())


def fold_of(ts):
    t = pd.Timestamp(ts)
    y = t.year
    return f"{y}H{1 if t.month <= 6 else 2}"


def session_of(ts):
    h = pd.Timestamp(ts).hour
    if h < 7:
        return "TOKYO"
    if h < 12:
        return "LONDON"
    if h < 16:
        return "LONDON_NY_OVERLAP"
    if h < 21:
        return "NEW_YORK"
    return "TRANSITION"


def normalize_ts(v):
    s = str(v or "").strip()
    if not s:
        return pd.NaT
    s = s.replace(".", "-")
    return pd.to_datetime(s, utc=True, format="mixed")


def parse_detail(v):
    out = {}
    for item in str(v or "").split(";"):
        if "=" in item:
            k, z = item.split("=", 1)
            out[k.strip()] = z.strip()
    return out


class TickArchiveStore:
    """Hourly Bid/Ask tick reader for annual monthly tar.gz release assets."""

    def __init__(self, roots):
        self.month = {}
        self.tars = {}
        self.member_maps = {}
        self.cache = {}
        for root in roots:
            for p in Path(root).glob("*.tar.gz"):
                m = re.search(r"usdjpy-(20\d\d)-(\d\d)-raw-ticks-v1\.tar\.gz$", p.name)
                if m:
                    self.month[(int(m.group(1)), int(m.group(2)))] = p
        if not self.month:
            raise RuntimeError(f"no monthly tick archives in {roots}")

    def tf(self, year, month):
        k = (year, month)
        if k not in self.month:
            raise KeyError(f"missing raw tick month {k}")
        if k not in self.tars:
            self.tars[k] = tarfile.open(self.month[k], "r:gz")
        return self.tars[k]

    def member_map(self, year, month):
        k = (year, month)
        if k in self.member_maps:
            return self.member_maps[k]
        tf = self.tf(year, month)
        mapping = {}
        pattern = re.compile(r"/(20\d\d)/(\d\d)/(\d\d)/(\d\d)\.csv\.gz$")
        for name in tf.getnames():
            if not name.endswith(".csv.gz"):
                continue
            mm = pattern.search("/" + name.lstrip("./"))
            if mm:
                y, mo, d, h = map(int, mm.groups())
                mapping[pd.Timestamp(year=y, month=mo, day=d, hour=h, tz="UTC")] = name
        self.member_maps[k] = mapping
        return mapping

    def hour(self, t):
        h = pd.Timestamp(t).tz_convert("UTC").floor("h")
        key = h.isoformat()
        if key in self.cache:
            return self.cache[key]
        try:
            name = self.member_map(h.year, h.month)[h]
            raw = self.tf(h.year, h.month).extractfile(name).read()
            d = pd.read_csv(io.BytesIO(gzip.decompress(raw)), usecols=["timestamp_utc", "bid", "ask"])
            d["timestamp_utc"] = pd.to_datetime(d.timestamp_utc, utc=True)
            d = d.sort_values("timestamp_utc").drop_duplicates("timestamp_utc").reset_index(drop=True)
        except (KeyError, FileNotFoundError, AttributeError):
            d = pd.DataFrame(columns=["timestamp_utc", "bid", "ask"])
        self.cache[key] = d
        return d

    def between(self, start, end, include_end=False):
        start = pd.Timestamp(start).tz_convert("UTC")
        end = pd.Timestamp(end).tz_convert("UTC")
        frames = []
        for h in pd.date_range(start.floor("h"), end.floor("h"), freq="h"):
            q = self.hour(h)
            if len(q):
                frames.append(q)
        if not frames:
            return pd.DataFrame(columns=["timestamp_utc", "bid", "ask"])
        z = pd.concat(frames, ignore_index=True).sort_values("timestamp_utc").drop_duplicates("timestamp_utc")
        mask = (z.timestamp_utc >= start) & (z.timestamp_utc <= end if include_end else z.timestamp_utc < end)
        return z[mask].reset_index(drop=True)

    def first_at_or_after(self, t, max_wait="8h"):
        t = pd.Timestamp(t).tz_convert("UTC")
        z = self.between(t, t + pd.Timedelta(max_wait), include_end=True)
        return None if z.empty else z.iloc[0]

    def build_m15(self, year):
        rows = []
        for month in range(1, 13):
            mapping = self.member_map(year, month)
            for hour_start, name in sorted(mapping.items()):
                raw = self.tf(year, month).extractfile(name).read()
                d = pd.read_csv(io.BytesIO(gzip.decompress(raw)), usecols=["timestamp_utc", "bid", "ask"])
                if d.empty:
                    continue
                d["timestamp_utc"] = pd.to_datetime(d.timestamp_utc, utc=True)
                d["bucket"] = d.timestamp_utc.dt.floor("15min")
                for t, g in d.groupby("bucket", sort=True):
                    rows.append({
                        "time": t,
                        "open": float(g.bid.iloc[0]),
                        "high": float(g.bid.max()),
                        "low": float(g.bid.min()),
                        "close": float(g.bid.iloc[-1]),
                        "ask_open": float(g.ask.iloc[0]),
                        "ask_close": float(g.ask.iloc[-1]),
                        "median_spread_pips": float(((g.ask - g.bid) / PIP).median()),
                        "ticks": int(len(g)),
                    })
        q = pd.DataFrame(rows)
        if q.empty:
            raise RuntimeError(f"no M15 bars built for {year}")
        return q.sort_values("time").drop_duplicates("time").reset_index(drop=True)


def load_bars23(path: Path):
    d = read_csv_robust(path)
    t = pd.to_datetime(d["first_timestamp_mt4_server"], utc=True)

    def sunday(y, m, n, hour):
        x = pd.Timestamp(year=y, month=m, day=1, hour=hour, tz="UTC")
        return x + pd.Timedelta(days=(6 - x.weekday()) % 7 + 7 * (n - 1))

    def histutc(z):
        winter = z - pd.Timedelta(hours=2)
        return z - pd.Timedelta(hours=3) if sunday(z.year, 3, 2, 7) <= winter < sunday(z.year, 11, 1, 6) else winter

    tt = pd.DatetimeIndex([histutc(z) for z in t])
    q = pd.DataFrame({"time": tt, "open": d.open.astype(float), "high": d.high.astype(float), "low": d.low.astype(float), "close": d.close.astype(float)})
    return q[(q.time >= pd.Timestamp("2023-01-01", tz="UTC")) & (q.time < pd.Timestamp("2024-01-01", tz="UTC"))].sort_values("time").drop_duplicates("time").reset_index(drop=True)


def load_bars24(path: Path):
    d = read_csv_robust(path)
    q = pd.DataFrame({"time": pd.to_datetime(d.time, utc=True), "open": d.bid_open.astype(float), "high": d.bid_high.astype(float), "low": d.bid_low.astype(float), "close": d.bid_close.astype(float)})
    return q[(q.time >= pd.Timestamp("2024-01-01", tz="UTC")) & (q.time < pd.Timestamp("2025-01-01", tz="UTC"))].sort_values("time").drop_duplicates("time").reset_index(drop=True)


def enrich_bars(b):
    x = b.copy().sort_values("time").reset_index(drop=True)
    pc = x.close.shift()
    x["tr_pips"] = pd.concat([x.high - x.low, (x.high - pc).abs(), (x.low - pc).abs()], axis=1).max(axis=1) / PIP
    x["body_pips"] = (x.close - x.open).abs() / PIP
    x["median_tr96"] = x.tr_pips.rolling(96).median()
    x["shock_ratio"] = x.tr_pips / x.median_tr96
    x["atr14_pips"] = x.tr_pips.rolling(14).mean()
    x["ret"] = x.close.diff()
    x["dir"] = np.sign(x.close - x.open)
    x["prior_4h_return_pips"] = (x.close - x.close.shift(16)) / PIP
    x["prior_24h_return_pips"] = (x.close - x.close.shift(96)) / PIP
    x["directional_persistence_4h"] = x.dir.rolling(16).mean().abs()
    x["directional_autocorr_24h"] = x.ret.rolling(96).corr(x.ret.shift())
    # Rolling empirical ATR percentile over approximately 20 trading days.
    x["atr_percentile_20d"] = x.atr14_pips.rolling(1920, min_periods=200).apply(lambda a: pd.Series(a).rank(pct=True).iloc[-1], raw=False)
    x["date"] = x.time.dt.floor("D")
    daily = x.groupby("date").agg(day_high=("high", "max"), day_low=("low", "min"), day_open=("open", "first"), day_close=("close", "last"))
    daily["prior_day_high"] = daily.day_high.shift()
    daily["prior_day_low"] = daily.day_low.shift()
    daily["prior_day_close"] = daily.day_close.shift()
    x = x.merge(daily[["prior_day_high", "prior_day_low", "prior_day_close"]], left_on="date", right_index=True, how="left")
    x["distance_prior_day_high_pips"] = (x.close - x.prior_day_high) / PIP
    x["distance_prior_day_low_pips"] = (x.close - x.prior_day_low) / PIP
    x["gap_from_prior_close_pips"] = (x.open - x.prior_day_close) / PIP
    x["previous_day_breakout_state"] = np.select([x.close > x.prior_day_high, x.close < x.prior_day_low], ["ABOVE_PRIOR_HIGH", "BELOW_PRIOR_LOW"], default="INSIDE_PRIOR_RANGE")
    # H1/H4 EMA states mapped back to M15.
    for freq, label in [("1h", "h1"), ("4h", "h4")]:
        r = x.set_index("time").resample(freq, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        r[f"{label}_ema20"] = r.close.ewm(span=20, adjust=False).mean()
        r[f"{label}_ema50"] = r.close.ewm(span=50, adjust=False).mean()
        r[f"{label}_trend_state"] = np.select([r.close > r[f"{label}_ema20"], r.close < r[f"{label}_ema20"]], ["UP", "DOWN"], default="FLAT")
        x = pd.merge_asof(x.sort_values("time"), r[[f"{label}_trend_state"]].reset_index().sort_values("time"), on="time", direction="backward")
    return x


def reproduce_events(x):
    x = x.copy()
    pos = (x.close - x.low) / (x.high - x.low).replace(0, np.nan)
    shock = (x.tr_pips >= 2.5 * x.median_tr96) & (x.body_pips >= 0.65 * x.tr_pips)
    up = shock & (x.close > x.open) & (pos >= 0.80)
    down = shock & (x.close < x.open) & (pos <= 0.20)
    rows = []
    midpoint = (x.high.shift() + x.low.shift()) / 2
    for i in x.index[up.shift().fillna(False) & (x.close < midpoint) & (x.close < x.open)]:
        rows.append((int(i), -1, "up_shock_failed"))
    for i in x.index[down.shift().fillna(False) & (x.close > midpoint) & (x.close > x.open)]:
        rows.append((int(i), 1, "down_shock_failed"))
    rows.sort()
    keep, active = [], -1
    for failure_i, side, reason in rows:
        entry_i, exit_i = failure_i + 1, failure_i + 9
        if failure_i < 100 or exit_i >= len(x) or fold_of(x.time.iloc[entry_i]) != fold_of(x.time.iloc[exit_i]) or failure_i <= active:
            continue
        keep.append({"failure_i": failure_i, "shock_i": failure_i - 1, "entry_i": entry_i, "exit_i": exit_i, "side": side, "reason": reason})
        active = failure_i + 9
    out = []
    for r in keep:
        s, f, e, q = r["shock_i"], r["failure_i"], r["entry_i"], r["exit_i"]
        entry = x.time.iloc[e]
        fold = fold_of(entry)
        out.append({
            **r,
            "event_id": f"{fold}|D_SHOCK_FAILURE|{entry.isoformat()}|{r['side']}",
            "fold": fold,
            "shock_start_utc": x.time.iloc[s],
            "shock_end_utc": x.time.iloc[f],
            "failure_start_utc": x.time.iloc[f],
            "failure_completion_utc": entry,
            "entry_decision_utc": entry,
            "exit_boundary_utc": x.time.iloc[q],
            "side_label": "LONG" if r["side"] > 0 else "SHORT",
            "session": session_of(entry),
        })
    return pd.DataFrame(out)


def feature_for_event(x, row):
    s = int(row["shock_i"])
    r = x.iloc[s]
    direction = int(np.sign(r.close - r.open))
    run = 0
    k = s
    while k >= 0 and int(np.sign(x.close.iloc[k] - x.open.iloc[k])) == direction:
        run += 1
        k -= 1
    prior_shocks = x.loc[:s - 1, "shock_ratio"] >= 2.5
    prior_idx = prior_shocks[prior_shocks].index
    prev = int(prior_idx[-1]) if len(prior_idx) else None
    return {
        "shock_magnitude_pips": float(r.tr_pips),
        "shock_ratio": float(r.shock_ratio),
        "shock_body_pips": float(r.body_pips),
        "shock_duration_bars": run,
        "failure_confirmation_delay_bars": 1,
        "atr14_pips": float(r.atr14_pips) if pd.notna(r.atr14_pips) else np.nan,
        "atr_percentile_20d": float(r.atr_percentile_20d) if pd.notna(r.atr_percentile_20d) else np.nan,
        "prior_4h_return_pips": float(r.prior_4h_return_pips) if pd.notna(r.prior_4h_return_pips) else np.nan,
        "prior_24h_return_pips": float(r.prior_24h_return_pips) if pd.notna(r.prior_24h_return_pips) else np.nan,
        "directional_persistence_4h": float(r.directional_persistence_4h) if pd.notna(r.directional_persistence_4h) else np.nan,
        "directional_autocorr_24h": float(r.directional_autocorr_24h) if pd.notna(r.directional_autocorr_24h) else np.nan,
        "distance_prior_day_high_pips": float(r.distance_prior_day_high_pips) if pd.notna(r.distance_prior_day_high_pips) else np.nan,
        "distance_prior_day_low_pips": float(r.distance_prior_day_low_pips) if pd.notna(r.distance_prior_day_low_pips) else np.nan,
        "gap_from_prior_close_pips": float(r.gap_from_prior_close_pips) if pd.notna(r.gap_from_prior_close_pips) else np.nan,
        "previous_day_breakout_state": r.previous_day_breakout_state,
        "h1_trend_state": r.h1_trend_state,
        "h4_trend_state": r.h4_trend_state,
        "time_since_previous_shock_minutes": np.nan if prev is None else float((r.time - x.time.iloc[prev]).total_seconds() / 60),
        "shock_count_prior_24h": int(((x.time >= r.time - pd.Timedelta("24h")) & (x.time < r.time) & (x.shock_ratio >= 2.5)).sum()),
        "shock_count_prior_7d": int(((x.time >= r.time - pd.Timedelta("7d")) & (x.time < r.time) & (x.shock_ratio >= 2.5)).sum()),
    }


def path_diagnostics(store, entry_time, side, entry_price=None, exit_boundary=None, fixed_spread_pips=None):
    entry_time = pd.Timestamp(entry_time).tz_convert("UTC")
    if exit_boundary is None:
        exit_boundary = entry_time + pd.Timedelta("120m")
    exit_boundary = pd.Timestamp(exit_boundary).tz_convert("UTC")
    end240 = entry_time + pd.Timedelta("240m")
    entry_tick = store.first_at_or_after(entry_time)
    exit_tick = store.first_at_or_after(exit_boundary)
    if entry_tick is None or exit_tick is None:
        return {"data_anomaly": True, "anomaly_reason": "missing_entry_or_exit_tick"}
    if entry_price is None:
        entry_price = float(entry_tick.ask if side > 0 else entry_tick.bid)
    path = store.between(entry_tick.timestamp_utc, end240, include_end=True)
    if path.empty:
        return {"data_anomaly": True, "anomaly_reason": "empty_path"}
    if side > 0:
        net = (path.bid.astype(float) - float(entry_price)) / PIP
        gross = (path.bid.astype(float) - float(entry_tick.bid)) / PIP
    else:
        net = (float(entry_price) - path.ask.astype(float)) / PIP
        gross = (float(entry_tick.ask) - path.ask.astype(float)) / PIP
    times = path.timestamp_utc
    before120 = times <= exit_tick.timestamp_utc
    net120 = net[before120]
    gross120 = gross[before120]
    if net120.empty:
        return {"data_anomaly": True, "anomaly_reason": "empty_120m_path"}
    imax = net120.idxmax(); imin = net120.idxmin()
    positive = net > 0
    positive120 = positive & before120
    first_profit = times[positive].iloc[0] if positive.any() else pd.NaT
    first_profit120 = times[positive120].iloc[0] if positive120.any() else pd.NaT
    boundary_values = {}
    for minute in (30, 60, 90, 120, 180, 240):
        target = entry_time + pd.Timedelta(minutes=minute)
        z = path[path.timestamp_utc >= target]
        boundary_values[f"pnl_{minute}m_pips"] = np.nan if z.empty else float(net.loc[z.index[0]])
    mfe = float(net120.max()); mae = float(net120.min())
    time_mfe = float((times.loc[imax] - entry_tick.timestamp_utc).total_seconds() / 60)
    time_mae = float((times.loc[imin] - entry_tick.timestamp_utc).total_seconds() / 60)
    pnl120 = float(net.loc[path[path.timestamp_utc >= exit_tick.timestamp_utc].index[0]])
    later = net[times > exit_tick.timestamp_utc]
    max_after120 = float(later.max()) if len(later) else np.nan
    giveback = float(mfe - pnl120)
    # 50% giveback oracle after MFE.
    after_mfe = net.loc[imax:]
    giveback_exit = np.nan
    if mfe > 0:
        hit = after_mfe[after_mfe <= mfe * 0.5]
        if len(hit): giveback_exit = float(hit.iloc[0])
    return {
        "data_anomaly": False,
        "entry_execution_utc_raw": entry_tick.timestamp_utc,
        "entry_bid_raw": float(entry_tick.bid),
        "entry_ask_raw": float(entry_tick.ask),
        "entry_spread_raw_pips": float((entry_tick.ask - entry_tick.bid) / PIP),
        "exit_execution_utc_raw": exit_tick.timestamp_utc,
        "exit_bid_raw": float(exit_tick.bid),
        "exit_ask_raw": float(exit_tick.ask),
        "exit_spread_raw_pips": float((exit_tick.ask - exit_tick.bid) / PIP),
        "pnl_120m_raw_path_pips": pnl120,
        "mfe_pips": mfe,
        "mae_pips": mae,
        "gross_mfe_pips": float(gross120.max()),
        "time_to_mfe_minutes": time_mfe,
        "time_to_mae_minutes": time_mae,
        "first_profitable_time_utc": first_profit,
        "first_profitable_time_before_120_utc": first_profit120,
        "first_profitable_minutes": np.nan if pd.isna(first_profit) else float((first_profit - entry_tick.timestamp_utc).total_seconds() / 60),
        "maximum_profitable_excursion_pips": mfe,
        "profitable_at_any_time": bool(positive.any()),
        "profitable_before_120_minutes": bool(positive120.any()),
        "profit_giveback_pips": giveback,
        "maximum_pnl_after_120_to_240_pips": max_after120,
        "oracle_mfe_exit_pips": mfe,
        "oracle_first_profit_exit_pips": np.nan if not positive.any() else float(net[positive].iloc[0]),
        "oracle_breakeven_reached": bool(positive.any()),
        "oracle_giveback_50pct_exit_pips": giveback_exit,
        "fixed_spread_assumption_pips": fixed_spread_pips,
        **boundary_values,
    }


def classify(row):
    if bool(row.get("data_anomaly", False)):
        return "G_EXECUTION_DATA_ANOMALY"
    mfe = float(row.get("mfe_pips", np.nan))
    gross_mfe = float(row.get("gross_mfe_pips", np.nan))
    pnl120 = float(row.get("pnl_120m_raw_path_pips", np.nan))
    first = row.get("first_profitable_minutes", np.nan)
    max_after = row.get("maximum_pnl_after_120_to_240_pips", np.nan)
    shock = abs(float(row.get("shock_magnitude_pips", np.nan)))
    mae = float(row.get("mae_pips", np.nan))
    if (not bool(row.get("profitable_before_120_minutes", False))) and pd.notna(max_after) and max_after > 0:
        return "E_TIMEOUT_TRUNCATION"
    if gross_mfe > 0 and mfe <= 0:
        return "C_INSUFFICIENT_REVERSAL"
    if bool(row.get("profitable_before_120_minutes", False)) and pnl120 < 0 and pd.notna(shock) and mae <= -0.5 * shock:
        return "F_CONTINUATION_RESUMPTION"
    if bool(row.get("profitable_before_120_minutes", False)) and (pnl120 <= 0 or (mfe > 0 and pnl120 < 0.5 * mfe)):
        return "D_PROFIT_THEN_GIVEBACK"
    if pd.notna(first) and first > 60 and first <= 120:
        return "B_DELAYED_REVERSAL"
    if not bool(row.get("profitable_before_120_minutes", False)):
        return "A_IMMEDIATE_SIGNAL_FAILURE"
    return "H_SUSTAINED_REVERSAL"


def parse_shock_audit(path: Path, half):
    d = read_csv_robust(path)
    op = d[d.event == "order_opened"].copy()
    cl = d[d.event == "order_closed"].copy()
    for c in ["shock_utc", "failure_utc", "decision_utc", "utc_time"]:
        if c in op: op[c] = pd.to_datetime(op[c].astype(str).str.replace(".", "-", regex=False), utc=True, format="mixed", errors="coerce")
        if c in cl: cl[c] = pd.to_datetime(cl[c].astype(str).str.replace(".", "-", regex=False), utc=True, format="mixed", errors="coerce")
    cl = cl[["ticket", "utc_time", "price", "gross_pips", "error_code"]].rename(columns={"utc_time": "mt4_exit_execution_utc", "price": "mt4_exit_price", "gross_pips": "mt4_gross_pips", "error_code": "close_error_code"})
    z = op.merge(cl, on="ticket", how="left", validate="one_to_one")
    z["half"] = half
    z["fold"] = "2025H1" if half == "h1" else "2025H2"
    z["event_id"] = [f"{fold}|D_SHOCK_FAILURE|{t.isoformat()}|{int(s)}" for fold, t, s in zip(z.fold, z.decision_utc, z.side)]
    z["side_label"] = np.where(z.side.astype(int) > 0, "LONG", "SHORT")
    z["session"] = [session_of(t) for t in z.decision_utc]
    z["month"] = z.decision_utc.dt.strftime("%Y-%m")
    z["day"] = z.decision_utc.dt.strftime("%Y-%m-%d")
    z["mt4_entry_execution_utc"] = z.utc_time
    z["mt4_entry_price"] = z.price.astype(float)
    z["mt4_pnl_jpy"] = z.mt4_gross_pips.astype(float) * JPY_PER_PIP_001
    z["mt4_entry_spread_pips"] = 0.5
    z["mt4_exit_boundary_utc"] = z.decision_utc + pd.Timedelta("120m")
    return z


def parse_base_trades(path: Path):
    d = read_csv_robust(path)
    op = d[d.event == "order_opened"].copy()
    cl = d[d.event == "order_closed"].copy()
    for c in ["signal_utc", "entry_utc", "utc_time"]:
        if c in op: op[c] = pd.to_datetime(op[c].astype(str).str.replace(".", "-", regex=False), utc=True, format="mixed", errors="coerce")
        if c in cl: cl[c] = pd.to_datetime(cl[c].astype(str).str.replace(".", "-", regex=False), utc=True, format="mixed", errors="coerce")
    close = cl[["ticket", "utc_time", "gross_pips", "price"]].rename(columns={"utc_time": "close_utc", "gross_pips": "gross_pips_close", "price": "close_price"})
    z = op.merge(close, on="ticket", how="left")
    z["pnl_jpy"] = z.gross_pips_close.astype(float) * JPY_PER_PIP_001
    return z


def portfolio_context(events, base):
    base = base.copy()
    daily = base.groupby(base.close_utc.dt.strftime("%Y-%m-%d")).pnl_jpy.sum()
    base_sorted = base.sort_values("close_utc")
    csum = base_sorted.pnl_jpy.cumsum(); peaks = csum.cummax()
    rows = []
    for r in events.itertuples():
        active = base[(base.entry_utc < r.mt4_exit_boundary_utc) & (base.close_utc > r.decision_utc)]
        done = base_sorted[base_sorted.close_utc <= r.decision_utc]
        eq = float(done.pnl_jpy.sum()); peak = float(done.pnl_jpy.cumsum().cummax().max()) if len(done) else 0.0
        rows.append({
            "event_id": r.event_id,
            "b02_overlap": bool((active.strategy == "B02").any()),
            "f05_overlap": bool((active.strategy == "F05").any()),
            "same_direction_exposure": bool((active.side.astype(int) == int(r.side)).any()),
            "opposite_direction_exposure": bool((active.side.astype(int) != int(r.side)).any()),
            "simultaneous_baseline_position_count": int(len(active)),
            "baseline_daily_pnl_jpy": float(daily.get(r.day, 0.0)),
            "portfolio_drawdown_state_jpy": max(0.0, peak - eq),
            "active_trade_ids": ";".join(f"{x.strategy}|{x.entry_utc.isoformat()}|{int(x.side)}" for x in active.itertuples()),
        })
    return pd.DataFrame(rows)


def load_mt4_context(root: Path):
    files=sorted(Path(root).glob("mt4_events_*.json"))
    if len(files)!=5:
        raise RuntimeError(f"mt4 context packet count={len(files)}")
    events=[]
    authority=None
    for path in files:
        payload=json.loads(path.read_text(encoding="utf-8"))
        if authority is None: authority=payload["authority"]
        elif payload["authority"]!=authority: raise RuntimeError("MT4 context authority mismatch")
        events.extend(payload["events"])
    if len(events)!=47 or len({x["event_id"] for x in events})!=47:
        raise RuntimeError(f"MT4 event identity failure count={len(events)}")
    d=pd.DataFrame(events)
    for c in ["decision_utc","failure_utc","shock_utc","mt4_entry_time","mt4_exit_time"]:
        d[c]=pd.to_datetime(d[c],utc=True)
    d["fold"]=d["half"]
    d["mt4_entry_execution_utc"]=d["mt4_entry_time"]
    d["mt4_exit_execution_utc"]=d["mt4_exit_time"]
    d["mt4_exit_boundary_utc"]=d["decision_utc"]+pd.Timedelta("120m")
    d["mt4_gross_pips"]=d["mt4_pnl_pips"].astype(float)
    d["mt4_pnl_jpy"]=d["mt4_gross_pips"]*JPY_PER_PIP_001
    d["mt4_entry_spread_pips"]=0.5
    d["simultaneous_baseline_position_count"]=d["simultaneous_baseline_positions"].astype(int)
    d["portfolio_drawdown_state_jpy"]=np.nan
    d["active_trade_ids"]=""
    d["error_code"]=d["runtime_execution_errors"].astype(int)
    d["close_error_code"]=0
    return d,authority

def metrics(g, pnl_col):
    s = g[pnl_col].dropna().astype(float)
    return {
        "trades": int(len(s)), "net": float(s.sum()), "pf": pf(s), "win_rate": float((s > 0).mean()) if len(s) else None,
        "median": float(s.median()) if len(s) else None, "gross_profit": float(s[s > 0].sum()), "gross_loss": float(s[s < 0].sum()),
        "mdd": maxdd(s), "mean_mfe_pips": float(g.mfe_pips.mean()) if "mfe_pips" in g and len(g) else None,
        "mean_mae_pips": float(g.mae_pips.mean()) if "mae_pips" in g and len(g) else None,
        "profit_then_giveback_rate": float((g.failure_class == "D_PROFIT_THEN_GIVEBACK").mean()) if "failure_class" in g and len(g) else None,
        "immediate_failure_rate": float((g.failure_class == "A_IMMEDIATE_SIGNAL_FAILURE").mean()) if "failure_class" in g and len(g) else None,
        "timeout_truncation_rate": float((g.failure_class == "E_TIMEOUT_TRUNCATION").mean()) if "failure_class" in g and len(g) else None,
        "positive_months": int((g.assign(month=g.entry_decision_utc.dt.strftime("%Y-%m")).groupby("month")[pnl_col].sum() > 0).sum()) if len(g) else 0,
    }


def distribution_shift(df, features, group_a, group_b, seed=20260727):
    rng = np.random.default_rng(seed)
    rows = []
    for feat in features:
        a = df[df.fold.isin(group_a)][feat].dropna().astype(float).to_numpy()
        b = df[df.fold.isin(group_b)][feat].dropna().astype(float).to_numpy()
        if len(a) < 2 or len(b) < 2:
            continue
        pooled = math.sqrt(((len(a)-1)*np.var(a,ddof=1)+(len(b)-1)*np.var(b,ddof=1))/(len(a)+len(b)-2)) if len(a)+len(b)>2 else np.nan
        smd = (np.mean(b)-np.mean(a))/pooled if pooled and np.isfinite(pooled) else np.nan
        ks = ks_2samp(a,b)
        wd = wasserstein_distance(a,b)
        reps=[]
        for _ in range(2000):
            reps.append(rng.choice(b,len(b),replace=True).mean()-rng.choice(a,len(a),replace=True).mean())
        rows.append({"feature":feat,"group_a":"+".join(group_a),"group_b":"+".join(group_b),"n_a":len(a),"n_b":len(b),"mean_a":np.mean(a),"mean_b":np.mean(b),"standardized_mean_difference":smd,"ks_statistic":ks.statistic,"ks_pvalue":ks.pvalue,"wasserstein_distance":wd,"mean_difference_bootstrap_ci95_low":np.quantile(reps,.025),"mean_difference_bootstrap_ci95_high":np.quantile(reps,.975)})
    return pd.DataFrame(rows)


def concentration(g, pnl_col):
    rows=[]
    def add(scenario,z):
        m=metrics(z,pnl_col);m.update(scenario=scenario);rows.append(m)
    add("BASELINE",g)
    worst=g.sort_values(pnl_col)
    for n in (1,3,5): add(f"REMOVE_WORST_{n}_TRADES",worst.iloc[n:])
    day=g.assign(key=g.entry_decision_utc.dt.strftime("%Y-%m-%d")).groupby("key")[pnl_col].sum(); wd=day.idxmin(); add("REMOVE_WORST_DAY",g[g.entry_decision_utc.dt.strftime("%Y-%m-%d")!=wd])
    mon=g.assign(key=g.entry_decision_utc.dt.strftime("%Y-%m")).groupby("key")[pnl_col].sum(); wm=mon.idxmin(); add("REMOVE_WORST_MONTH",g[g.entry_decision_utc.dt.strftime("%Y-%m")!=wm])
    for side in sorted(g.side_label.unique()): add(f"REMOVE_SIDE_{side}",g[g.side_label!=side])
    for ses in sorted(g.session.unique()): add(f"REMOVE_SESSION_{ses}",g[g.session!=ses])
    return pd.DataFrame(rows)


def oracle_report(g):
    rows=[]
    cols=["pnl_30m_pips","pnl_60m_pips","pnl_90m_pips","pnl_120m_pips","pnl_180m_pips","pnl_240m_pips","oracle_mfe_exit_pips","oracle_first_profit_exit_pips","oracle_giveback_50pct_exit_pips"]
    for c in cols:
        if c not in g: continue
        s=g[c].dropna().astype(float)
        rows.append({"label":ORACLE_LABEL,"oracle":c,"trades":len(s),"net_pips":s.sum(),"pf":pf(s),"win_rate":(s>0).mean() if len(s) else None,"median_pips":s.median() if len(s) else None})
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--phase2-ledger",type=Path,required=True)
    ap.add_argument("--m15-2023",type=Path,required=True)
    ap.add_argument("--m15-2024",type=Path,required=True)
    ap.add_argument("--raw-2025",type=Path,required=True)
    ap.add_argument("--mt4-context-dir",type=Path,required=True)
    ap.add_argument("--portfolio-context",type=Path,required=True)
    ap.add_argument("--corrected-p6",type=Path,required=True)
    ap.add_argument("--protocol",type=Path,required=True)
    ap.add_argument("--out-dir",type=Path,required=True)
    ap.add_argument("--research-sha",default="UNKNOWN")
    ap.add_argument("--core-sha",default="UNKNOWN")
    ap.add_argument("--run-id",default="LOCAL")
    a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
    protocol=json.load(open(a.protocol));assert protocol["candidate_id"]=="B_EXECUTABLE_T0_8BAR" and protocol["fixed_candidate_changes_permitted"] is False
    p6=json.load(open(a.corrected_p6));assert p6["status"]=="FAIL_P6_2025_GATE_RESEARCH_ONLY_NO_RETUNING"

    store=TickArchiveStore([a.raw_2025])
    b23=enrich_bars(load_bars23(a.m15_2023));b24=enrich_bars(load_bars24(a.m15_2024));b25=enrich_bars(store.build_m15(2025))
    bars_by_year={2023:b23,2024:b24,2025:b25}

    phase=read_csv_robust(a.phase2_ledger)
    dev=phase[(phase.candidate_id=="B_EXECUTABLE_T0_8BAR") & phase.admitted.fillna(False)].copy()
    for c in ["entry_utc","exit_utc","entry_tick_utc","exit_tick_utc","shock_start_utc","failure_end_utc"]: dev[c]=pd.to_datetime(dev[c],utc=True,format='mixed')
    dev["event_id"]=dev.opportunity_id;dev["entry_decision_utc"]=dev.entry_utc;dev["month"]=dev.entry_utc.dt.strftime("%Y-%m");dev["day"]=dev.entry_utc.dt.strftime("%Y-%m-%d")
    dev["shock_magnitude_pips"]=dev.shock_tr_pips;dev["shock_duration_bars"]=dev.impulse_run_bars;dev["failure_confirmation_delay_bars"]=1
    dev_rows=[]
    for r in dev.itertuples():
        # Historical lifecycle authority comes directly from the frozen Phase 2 Raw Tick ledger.
        # Exact intra-trade timing was not retained there, so it is not reconstructed or imputed.
        mfe=float(r.mfe_pips);mae=float(r.mae_pips);final=float(r.pnl_pips)
        hist_class=("A_IMMEDIATE_SIGNAL_FAILURE" if mfe<=0 else
                    ("F_CONTINUATION_RESUMPTION" if final<=0 and mae<=-0.5*abs(float(r.shock_tr_pips)) else
                     ("D_PROFIT_THEN_GIVEBACK" if final<=0 or final<0.5*mfe else "H_SUSTAINED_REVERSAL")))
        row={"event_id":r.event_id,"fold":r.fold,"entry_decision_utc":r.entry_utc,"side":int(r.side),"side_label":r.side_label,"session":r.session,"month":r.month,"day":r.day,"shock_start_utc":r.shock_start_utc,"failure_completion_utc":r.entry_utc,"shock_magnitude_pips":r.shock_tr_pips,"shock_ratio":r.shock_ratio,"shock_duration_bars":r.impulse_run_bars,"pnl_jpy":r.pnl_jpy,"pnl_pips":r.pnl_pips,"mfe_pips":mfe,"mae_pips":mae,"maximum_profitable_excursion_pips":mfe,"profitable_at_any_time":bool(mfe>0),"profitable_before_120_minutes":bool(mfe>0),"profit_giveback_pips":float(mfe-final),"first_profitable_minutes":np.nan,"time_to_mfe_minutes":np.nan,"time_to_mae_minutes":np.nan,"entry_spread_raw_pips":float(r.observed_spread_entry_pips),"exit_spread_raw_pips":float(r.observed_spread_exit_pips),"b02_overlap":r.b02_active,"f05_overlap":r.f05_active,"same_direction_exposure":r.same_direction_overlap,"opposite_direction_exposure":r.opposite_direction_overlap,"baseline_daily_pnl_jpy":r.baseline_day_pnl_jpy,"portfolio_drawdown_state_jpy":r.baseline_existing_drawdown_jpy,"failure_class":hist_class,"historical_lifecycle_timing_available":False}
        # Regime features using nearest shock timestamp.
        x=bars_by_year[pd.Timestamp(r.entry_utc).year];idx=x.time.searchsorted(pd.Timestamp(r.shock_start_utc));idx=min(max(int(idx),0),len(x)-1)
        row.update(feature_for_event(x,{"shock_i":idx}));dev_rows.append(row)
    dev_enriched=pd.DataFrame(dev_rows)

    mt4,mt4_authority=load_mt4_context(a.mt4_context_dir)
    portfolio_authority=json.load(open(a.portfolio_context,encoding="utf-8"))
    assert portfolio_authority["authority"]["core_run_id"]==30229496015
    assert portfolio_authority["authority"]["core_artifact_id"]==8639969385
    mt4_rows=[]
    for r in mt4.itertuples():
        # Map expected shock bar from the decision boundary, independent of whether raw source reproduces signal.
        x=b25;shock_time=pd.Timestamp(r.decision_utc)-pd.Timedelta("30m");idx=x.time.searchsorted(shock_time);idx=min(max(int(idx),0),len(x)-1)
        feat=feature_for_event(x,{"shock_i":idx})
        path=path_diagnostics(store,r.decision_utc,int(r.side),entry_price=float(r.mt4_entry_price),exit_boundary=r.mt4_exit_boundary_utc,fixed_spread_pips=.5)
        row={k:getattr(r,k) for k in mt4.columns if hasattr(r,k)};row.update(feat);row.update(path);row["pnl_jpy"]=r.mt4_pnl_jpy;row["pnl_pips"]=r.mt4_gross_pips;row["failure_class"]=classify(row);row["runtime_execution_errors"]=int(r.error_code)+int(r.close_error_code if pd.notna(r.close_error_code) else 0);mt4_rows.append(row)
    mt4_enriched=pd.DataFrame(mt4_rows);mt4_enriched['entry_decision_utc']=mt4_enriched['decision_utc']

    raw_events=reproduce_events(b25);raw_rows=[]
    for r in raw_events.to_dict("records"):
        feat=feature_for_event(b25,r);path=path_diagnostics(store,r["entry_decision_utc"],int(r["side"]),exit_boundary=r["exit_boundary_utc"])
        row={**r,**feat,**path};row["month"]=pd.Timestamp(r["entry_decision_utc"]).strftime("%Y-%m");row["day"]=pd.Timestamp(r["entry_decision_utc"]).strftime("%Y-%m-%d");row["pnl_pips"]=path.get("pnl_120m_raw_path_pips",np.nan);row["pnl_jpy"]=row["pnl_pips"]*JPY_PER_PIP_001 if pd.notna(row["pnl_pips"]) else np.nan;row["failure_class"]=classify(row);raw_rows.append(row)
    raw25=pd.DataFrame(raw_rows)

    mt4_keys=set(zip(mt4_enriched.decision_utc.dt.strftime("%Y-%m-%d %H:%M:%S"),mt4_enriched.side.astype(int)))
    raw_keys=set(zip(raw25.entry_decision_utc.dt.strftime("%Y-%m-%d %H:%M:%S"),raw25.side.astype(int)))
    matched=mt4_keys&raw_keys
    parity={"mt4_events":len(mt4_keys),"raw_events":len(raw_keys),"matched":len(matched),"mt4_only":len(mt4_keys-raw_keys),"raw_only":len(raw_keys-mt4_keys),"recall_vs_mt4":len(matched)/len(mt4_keys) if mt4_keys else None,"precision_vs_mt4":len(matched)/len(raw_keys) if raw_keys else None,"mt4_only_keys":sorted(mt4_keys-raw_keys),"raw_only_keys":sorted(raw_keys-mt4_keys)}

    combined=pd.concat([dev_enriched,mt4_enriched],ignore_index=True,sort=False)
    combined["entry_decision_utc"]=pd.to_datetime(combined.entry_decision_utc,utc=True)
    combined.to_csv(a.out_dir/"fold_comparison_event_ledger.csv",index=False)
    mt4_enriched.to_csv(a.out_dir/"event_ledger_2025_mt4_enriched.csv",index=False)
    raw25.to_csv(a.out_dir/"event_ledger_2025_raw_candidate.csv",index=False)
    write_json(a.out_dir/"source_history_spread_parity.json",parity)

    # Fold, side, session, month and failure-class metrics.
    for name,by in [("fold",["fold"]),("side",["fold","side_label"]),("session",["fold","session"]),("month",["month"]),("failure_class",["fold","failure_class"])]:
        rows=[]
        for keys,g in combined.groupby(by,dropna=False):
            keys=(keys,) if not isinstance(keys,tuple) else keys;m=metrics(g,"pnl_jpy");m.update({k:v for k,v in zip(by,keys)});rows.append(m)
        pd.DataFrame(rows).to_csv(a.out_dir/f"{name}_comparison.csv",index=False)

    features=["shock_magnitude_pips","shock_ratio","shock_duration_bars","atr14_pips","atr_percentile_20d","prior_4h_return_pips","prior_24h_return_pips","directional_persistence_4h","directional_autocorr_24h","distance_prior_day_high_pips","distance_prior_day_low_pips","gap_from_prior_close_pips","time_since_previous_shock_minutes","shock_count_prior_24h","mfe_pips","mae_pips","first_profitable_minutes","profit_giveback_pips"]
    shifts=pd.concat([distribution_shift(combined,features,["2023H2"],["2025H1","2025H2"]),distribution_shift(combined,features,["2023H1","2024H1","2024H2"],["2025H1","2025H2"])],ignore_index=True)
    shifts.to_csv(a.out_dir/"distribution_shift_report.csv",index=False)
    concentration(mt4_enriched,"pnl_jpy").to_csv(a.out_dir/"concentration_report_2025.csv",index=False)
    oracle_report(mt4_enriched).to_csv(a.out_dir/"oracle_exit_diagnostics_2025.csv",index=False)

    # Portfolio interaction uses immutable Core-derived aggregate and daily evidence.
    shock_daily=mt4_enriched.groupby(mt4_enriched.decision_utc.dt.strftime("%Y-%m-%d")).pnl_jpy.sum()
    baseline_daily=pd.Series(portfolio_authority["baseline_daily_pnl_jpy"],dtype=float)
    baseline_daily.index=baseline_daily.index.astype(str)
    idx=shock_daily.index.union(baseline_daily.index);sd=shock_daily.reindex(idx,fill_value=0.0);bd=baseline_daily.reindex(idx,fill_value=0.0)
    event_days=sorted(set(mt4_enriched.day.astype(str)))
    sed=sd.reindex(event_days,fill_value=0.0);bed=bd.reindex(event_days,fill_value=0.0)
    portfolio={
      "authority":portfolio_authority["authority"],
      "baseline":portfolio_authority["baseline"],
      "integrated":portfolio_authority["integrated"],
      "shock_closed_trades":len(mt4_enriched),
      "shock_net_jpy":float(mt4_enriched.pnl_jpy.sum()),
      "shock_pf":pf(mt4_enriched.pnl_jpy),
      "daily_correlation_all_days":float(sd.corr(bd)) if sd.std()>0 and bd.std()>0 else 0.0,
      "daily_correlation_event_days":float(sed.corr(bed)) if sed.std()>0 and bed.std()>0 else 0.0,
      "loss_day_overlap_count":int(((sd<0)&(bd<0)).sum()),
      "shock_loss_days":int((sd<0).sum()),
      "baseline_loss_days":int((bd<0).sum()),
      "overlap_rate_of_shock_loss_days":float(((sd<0)&(bd<0)).sum()/max(1,(sd<0).sum())),
      "b02_negative_day_contribution_jpy":portfolio_authority["b02_negative_day_contribution_jpy"],
      "f05_negative_day_contribution_jpy":portfolio_authority["f05_negative_day_contribution_jpy"],
      "same_direction_overlap_events":int(mt4_enriched.same_direction_exposure.fillna(False).sum()),
      "opposite_direction_overlap_events":int(mt4_enriched.opposite_direction_exposure.fillna(False).sum()),
      "maximum_simultaneous_baseline_positions":int(mt4_enriched.simultaneous_baseline_position_count.max()),
      "halves":p6["halves"],"portfolio_gates":p6["portfolio_gates"]}
    write_json(a.out_dir/"portfolio_interaction_report.json",portfolio)

    raw_metrics=metrics(raw25,"pnl_jpy") if len(raw25) else {}
    mt4_metrics=metrics(mt4_enriched,"pnl_jpy")
    class_share=mt4_enriched.failure_class.value_counts(normalize=True).to_dict()
    integrity_blocked = parity["recall_vs_mt4"] is not None and parity["recall_vs_mt4"] < 0.80
    exit_share=sum(class_share.get(k,0) for k in ["D_PROFIT_THEN_GIVEBACK","E_TIMEOUT_TRUNCATION","B_DELAYED_REVERSAL"])
    signal_share=sum(class_share.get(k,0) for k in ["A_IMMEDIATE_SIGNAL_FAILURE","C_INSUFFICIENT_REVERSAL","F_CONTINUATION_RESUMPTION"])
    side_net=mt4_enriched.groupby("side_label").pnl_jpy.sum();session_net=mt4_enriched.groupby("session").pnl_jpy.sum()
    directional_concentrated = len(side_net)>=2 and abs(side_net.min()) > abs(mt4_enriched.pnl_jpy.sum())*0.75
    if integrity_blocked and ((raw_metrics.get("net",0)>0) != (mt4_metrics.get("net",0)>0)):
        decision="DATA_OR_EXECUTION_INTEGRITY_BLOCKED"
    elif exit_share>=0.50 and exit_share>signal_share:
        decision="SHOCK_FAILURE_EXIT_LIFECYCLE_FAILED"
    elif directional_concentrated:
        decision="DIRECTIONAL_OR_REGIME_CONDITIONAL_MECHANISM"
    elif signal_share>=0.50:
        decision="SHOCK_FAILURE_SIGNAL_MECHANISM_FAILED"
    else:
        decision="CURRENT_FIXED_CANDIDATE_EXTERNAL_PORTABILITY_FAILED_FAMILY_RETAINED"
    final={"schema_version":"usdjpy_shock_failure_2025_postmortem_decision_v1","status":"PASS_POSTMORTEM_COMPLETED_NO_RETUNING","candidate_id":"B_EXECUTABLE_T0_8BAR","decision_class":decision,"fixed_candidate_status":"REJECTED_FOR_PRODUCTION_AND_PORTABLE_CORE_ADOPTION","family_status":"RETAIN_FOR_NEW_HYPOTHESIS_ONLY" if decision!="SHOCK_FAILURE_FAMILY_REJECTED" else "REJECTED","mt4_2025_metrics":mt4_metrics,"raw_2025_metrics":raw_metrics,"source_parity":parity,"failure_class_share":class_share,"exit_failure_share":exit_share,"signal_failure_share":signal_share,"side_net_jpy":side_net.to_dict(),"session_net_jpy":session_net.to_dict(),"new_candidate_allowed_only_with_new_id":True,"2025_available_as_future_holdout":False,"production_authorized":False,"live_orders_authorized":False,"next_external_period":"2026 only after complete immutable data availability and new preregistration; otherwise reserve the next fully unused future period","macro_event_proximity":"PENDING_PRIMARY_SOURCE_ANNOTATION_FOR_WORST_EVENTS"}
    write_json(a.out_dir/"final_decision.json",final)

    # Human-readable report.
    fold_table=pd.read_csv(a.out_dir/"fold_comparison.csv").to_markdown(index=False)
    class_table=pd.read_csv(a.out_dir/"failure_class_comparison.csv").query("fold in ['2025H1','2025H2']").to_markdown(index=False)
    side_table=pd.read_csv(a.out_dir/"side_comparison.csv").query("fold in ['2025H1','2025H2']").to_markdown(index=False)
    session_table=pd.read_csv(a.out_dir/"session_comparison.csv").query("fold in ['2025H1','2025H2']").to_markdown(index=False)
    report=f"""# USDJPY Shock Failure 2025 External-Gate Failure Postmortem v1\n\n## Boundary\n\nCandidate `B_EXECUTABLE_T0_8BAR` was not changed. No direction, session, month, threshold, median length, failure rule, entry timing, timeout or exit was selected. Oracle diagnostics are labelled `{ORACLE_LABEL}` and are not implementation candidates.\n\n## Authority\n\n- Research SHA: `{a.research_sha}`\n- Core SHA: `{a.core_sha}`\n- P6 Run: `30229496015`\n- Original artifact: `8639969385`, SHA-256 `70088c66cd1014391cabbb6f533462dcd3dbedbd7d6c537a5dc0798343594a6a`\n- Corrected evidence status: `{p6['status']}`\n\n## Evidence repair\n\nThe integrated Shock audit omitted a duplicate `account_contract` row. The original evaluator raised before writing the P6 JSON. Packaging was repaired by reading the same integrated test's base-audit contract. Logs, outcomes, periods, gates, formulas and MT4 code were unchanged.\n\n## Fold metrics\n\n{fold_table}\n\n## 2025 side metrics\n\n{side_table}\n\n## 2025 session metrics\n\n{session_table}\n\n## Signal vs Exit lifecycle classification\n\n{class_table}\n\n## Source/history/spread comparison\n\n- MT4 events: {parity['mt4_events']}\n- Raw Tick candidate events: {parity['raw_events']}\n- Matched: {parity['matched']}\n- MT4-only: {parity['mt4_only']}\n- Raw-only: {parity['raw_only']}\n\n## Decision\n\n`{decision}`\n\nThe fixed candidate failed its consumed 2025 external gate and is not eligible for production. Any continuation requires a new hypothesis ID, candidate ID and preregistration using only 2023H1–2024H2 for development. 2025 remains postmortem evidence and cannot be reused as holdout.\n"""
    (a.out_dir/"human_readable_report.md").write_text(report,encoding="utf-8")

    reproduction=f"python tools/analyze_usdjpy_shock_failure_2025_postmortem_v3.py --phase2-ledger <candidate_trade_ledger.csv.gz> --m15-2023 <2023_m15.csv.gz> --m15-2024 <2024_m15.csv.gz> --raw-2025 <dir> --mt4-context-dir <dir> --portfolio-context <json> --corrected-p6 <json> --protocol <json> --out-dir <dir>\n"
    (a.out_dir/"REPRODUCE.md").write_text(reproduction,encoding="utf-8")
    # Source inventory and manifest.
    write_json(a.out_dir/"source_inventory.json",{"research_sha":a.research_sha,"core_sha":a.core_sha,"run_id":a.run_id,"phase2_ledger_sha256":sha256_file(a.phase2_ledger),"m15_2023_sha256":sha256_file(a.m15_2023),"m15_2024_sha256":sha256_file(a.m15_2024),"corrected_p6_sha256":sha256_file(a.corrected_p6),"portfolio_context_sha256":sha256_file(a.portfolio_context),"mt4_context_authority":mt4_authority,"candidate_changed":False,"2025_used_for_selection":False})
    files=[]
    for p in sorted(a.out_dir.iterdir()):
        if p.is_file() and p.name not in ["MANIFEST.json","SHA256SUMS"]:files.append({"path":p.name,"bytes":p.stat().st_size,"sha256":sha256_file(p)})
    write_json(a.out_dir/"MANIFEST.json",{"schema_version":"usdjpy_shock_failure_2025_postmortem_manifest_v1","files":files})
    with (a.out_dir/"SHA256SUMS").open("w") as f:
        for p in sorted(a.out_dir.iterdir()):
            if p.is_file() and p.name!="SHA256SUMS":f.write(f"{sha256_file(p)}  {p.name}\n")
    print(json.dumps(clean(final),indent=2,sort_keys=True))

if __name__=="__main__":main()
