#!/usr/bin/env python3
"""EURUSD 2024 H1-development / H2-validation screen on H1 bars.

The literature-derived registry is fixed before result inspection. Development and
validation are separate phases: H2 cannot nominate a family or alter a parameter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PIP = 0.0001
SYMBOL = "EURUSD"
ONE_HOUR = pd.Timedelta(hours=1)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def finite(value: float) -> float | str:
    if math.isinf(value):
        return "inf"
    if math.isnan(value):
        return 0.0
    return float(value)


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def load_bars(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {
        "timestamp_utc", "symbol", "mid_open", "mid_high", "mid_low", "mid_close",
        "spread_mean_pips", "tick_count",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    df = df[list(required)].copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    for col in ["mid_open", "mid_high", "mid_low", "mid_close", "spread_mean_pips", "tick_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.upper()
    df = df.dropna(subset=["timestamp_utc", "mid_open", "mid_high", "mid_low", "mid_close", "spread_mean_pips"])
    if set(df["symbol"]) != {SYMBOL}:
        raise ValueError(f"unexpected symbols: {sorted(set(df['symbol']))}")
    if df["timestamp_utc"].duplicated().any():
        raise ValueError("duplicate H1 timestamps")
    df = df.sort_values("timestamp_utc").reset_index(drop=True)
    if not df["timestamp_utc"].is_monotonic_increasing:
        raise ValueError("timestamps not increasing")
    if (df["timestamp_utc"].dt.minute != 0).any() or (df["timestamp_utc"].dt.second != 0).any():
        raise ValueError("H1 timestamp grid violation")
    if (df["spread_mean_pips"] < 0).any():
        raise ValueError("negative spread")
    if ((df["mid_high"] < df[["mid_open", "mid_close", "mid_low"]].max(axis=1)) |
            (df["mid_low"] > df[["mid_open", "mid_close", "mid_high"]].min(axis=1))).any():
        raise ValueError("invalid OHLC")
    df["date_utc"] = df["timestamp_utc"].dt.strftime("%Y-%m-%d")
    df["hour_utc"] = df["timestamp_utc"].dt.hour.astype(int)
    return df


def frame_content_sha256(df: pd.DataFrame) -> str:
    columns = [
        "timestamp_utc", "symbol", "mid_open", "mid_high", "mid_low", "mid_close",
        "spread_mean_pips", "tick_count",
    ]
    work = df[columns].copy()
    work["timestamp_utc"] = work["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = work.to_csv(index=False, float_format="%.15g", lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hard_exclusion_mask(entry_ts: pd.Series, config: dict[str, Any]) -> pd.Series:
    mask = pd.Series(False, index=entry_ts.index)
    for window in config.get("hard_no_trade_windows", []):
        applies = {str(x).upper() for x in window.get("applies_to", ["*"])}
        if "*" not in applies and SYMBOL not in applies:
            continue
        local = entry_ts.dt.tz_convert(ZoneInfo(str(window["timezone"])))
        start_h, start_m = map(int, str(window["start_local"]).split(":"))
        end_h, end_m = map(int, str(window["end_local"]).split(":"))
        minute = local.dt.hour * 60 + local.dt.minute
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        current = (minute >= start) & (minute < end) if start <= end else (minute >= start) | (minute < end)
        mask |= current
    return mask


def kaufman_efficiency_ratio(close: pd.Series, lookback: int) -> pd.Series:
    direction = (close - close.shift(lookback)).abs()
    volatility = close.diff().abs().rolling(lookback, min_periods=lookback).sum()
    return direction / volatility.replace(0, np.nan)


def rsi_wilder(close: pd.Series, lookback: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / lookback, adjust=False, min_periods=lookback).mean()
    avg_loss = loss.ewm(alpha=1.0 / lookback, adjust=False, min_periods=lookback).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    out = out.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    out = out.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    return out


def atr_simple(bars: pd.DataFrame, lookback: int) -> pd.Series:
    prev_close = bars["mid_close"].shift(1)
    tr = pd.concat([
        bars["mid_high"] - bars["mid_low"],
        (bars["mid_high"] - prev_close).abs(),
        (bars["mid_low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(lookback, min_periods=lookback).mean()


def expand_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for family in registry["families"]:
        fid = family["family_id"]
        name = family["family"]
        evidence = family["evidence_class"]
        common = {"family_id": fid, "family": name, "evidence_class": evidence}
        if fid in {"A", "J"}:
            for raw in family["candidates"]:
                specs.append({**common, **raw, "robustness_group": f"{fid}_explicit"})
        elif fid == "B":
            for lb in family["lookback_bars"]:
                for hold in family["hold_bars"]:
                    specs.append({**common, "id": f"B_lb{lb}_hold{hold}", "lookback_bars": lb, "hold_bars": hold, "robustness_group": "B_grid"})
        elif fid == "C":
            for fast, slow in family["ma_pairs"]:
                for hold in family["hold_bars"]:
                    specs.append({**common, "id": f"C_sma{fast}_{slow}_hold{hold}", "fast_bars": fast, "slow_bars": slow, "hold_bars": hold, "robustness_group": "C_grid"})
        elif fid == "D":
            for lb in family["lookback_bars"]:
                for hold in family["hold_bars"]:
                    specs.append({**common, "id": f"D_lb{lb}_hold{hold}", "lookback_bars": lb, "hold_bars": hold, "robustness_group": "D_grid"})
        elif fid == "E":
            for hold in family["hold_bars"]:
                specs.append({**common, "id": f"E_asia_london_hold{hold}", "reference_start_hour": family["reference_start_hour"], "reference_end_hour_exclusive": family["reference_end_hour_exclusive"], "entry_start_hour": family["entry_start_hour"], "entry_end_hour_inclusive": family["entry_end_hour_inclusive"], "hold_bars": hold, "robustness_group": "E_grid"})
        elif fid == "F":
            rf = family["regime_filter"]
            for lb in family["lookback_bars"]:
                for z in family["entry_abs_z"]:
                    for hold in family["hold_bars"]:
                        ztag = str(z).replace(".", "p")
                        specs.append({**common, "id": f"F_z_lb{lb}_thr{ztag}_hold{hold}", "lookback_bars": lb, "entry_abs_z": z, "hold_bars": hold, "er_lookback_bars": rf["lookback_bars"], "er_maximum": rf["maximum"], "robustness_group": "F_grid"})
        elif fid == "G":
            rf = family["regime_filter"]
            for lower, upper in family["threshold_pairs"]:
                for hold in family["hold_bars"]:
                    specs.append({**common, "id": f"G_rsi{family['rsi_lookback_bars']}_{lower}_{upper}_hold{hold}", "rsi_lookback_bars": family["rsi_lookback_bars"], "lower": lower, "upper": upper, "hold_bars": hold, "er_lookback_bars": rf["lookback_bars"], "er_maximum": rf["maximum"], "robustness_group": "G_grid"})
        elif fid == "H":
            for lb in family["reference_lookback_bars"]:
                for hold in family["hold_bars"]:
                    specs.append({**common, "id": f"H_failed_lb{lb}_hold{hold}", "reference_lookback_bars": lb, "minimum_excursion_atr_fraction": family["minimum_excursion_atr_fraction"], "atr_lookback_bars": family["atr_lookback_bars"], "hold_bars": hold, "robustness_group": "H_grid"})
        elif fid == "I":
            for window in family["compression_window_bars"]:
                for pct in family["compression_percentile"]:
                    ptag = int(round(float(pct) * 100))
                    for hold in family["hold_bars"]:
                        specs.append({**common, "id": f"I_comp{window}_pct{ptag}_hold{hold}", "compression_window_bars": window, "compression_percentile": pct, "percentile_history_sessions": family["percentile_history_sessions"], "hold_bars": hold, "robustness_group": "I_grid"})
        else:
            raise ValueError(f"unsupported family_id {fid}")
    ids = [s["id"] for s in specs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate IDs")
    return specs


def signal_for_candidate(bars: pd.DataFrame, spec: dict[str, Any]) -> pd.Series:
    fid = spec["family_id"]
    close = bars["mid_close"]
    side = pd.Series(0, index=bars.index, dtype=int)
    if fid == "A":
        entry_ts = bars["timestamp_utc"].shift(-1)
        local = entry_ts.dt.tz_convert(ZoneInfo(spec["timezone"]))
        allowed = local.dt.hour.eq(int(spec["entry_local_hour"]))
        side.loc[allowed] = 1 if spec["side"] == "long" else -1
    elif fid == "B":
        ret = close - close.shift(int(spec["lookback_bars"]))
        side.loc[ret > 0] = 1
        side.loc[ret < 0] = -1
    elif fid == "C":
        fast = close.rolling(int(spec["fast_bars"]), min_periods=int(spec["fast_bars"])).mean()
        slow = close.rolling(int(spec["slow_bars"]), min_periods=int(spec["slow_bars"])).mean()
        side.loc[fast > slow] = 1
        side.loc[fast < slow] = -1
    elif fid == "D":
        lb = int(spec["lookback_bars"])
        prev_high = bars["mid_high"].shift(1).rolling(lb, min_periods=lb).max()
        prev_low = bars["mid_low"].shift(1).rolling(lb, min_periods=lb).min()
        side.loc[close > prev_high] = 1
        side.loc[close < prev_low] = -1
    elif fid == "E":
        start = int(spec["reference_start_hour"])
        end = int(spec["reference_end_hour_exclusive"])
        ref_rows = bars[(bars["hour_utc"] >= start) & (bars["hour_utc"] < end)]
        daily = ref_rows.groupby("date_utc").agg(ref_high=("mid_high", "max"), ref_low=("mid_low", "min"))
        ref = bars[["date_utc"]].join(daily, on="date_utc")
        allowed = bars["hour_utc"].between(int(spec["entry_start_hour"]), int(spec["entry_end_hour_inclusive"]))
        raw = pd.Series(0, index=bars.index, dtype=int)
        raw.loc[allowed & (close > ref["ref_high"])] = 1
        raw.loc[allowed & (close < ref["ref_low"])] = -1
        selected = pd.DataFrame({"side": raw, "date": bars["date_utc"], "ts": bars["timestamp_utc"]})
        selected = selected[selected["side"].isin([1, -1])].sort_values("ts").groupby("date", sort=False).head(1)
        side.loc[selected.index] = selected["side"].astype(int)
    elif fid == "F":
        lb = int(spec["lookback_bars"])
        mean = close.rolling(lb, min_periods=lb).mean()
        std = close.rolling(lb, min_periods=lb).std(ddof=0).replace(0, np.nan)
        z = (close - mean) / std
        er = kaufman_efficiency_ratio(close, int(spec["er_lookback_bars"]))
        regime = er <= float(spec["er_maximum"])
        threshold = float(spec["entry_abs_z"])
        side.loc[regime & (z <= -threshold)] = 1
        side.loc[regime & (z >= threshold)] = -1
    elif fid == "G":
        rsi = rsi_wilder(close, int(spec["rsi_lookback_bars"]))
        er = kaufman_efficiency_ratio(close, int(spec["er_lookback_bars"]))
        regime = er <= float(spec["er_maximum"])
        side.loc[regime & (rsi < float(spec["lower"]))] = 1
        side.loc[regime & (rsi > float(spec["upper"]))] = -1
    elif fid == "H":
        lb = int(spec["reference_lookback_bars"])
        ref_high = bars["mid_high"].shift(1).rolling(lb, min_periods=lb).max()
        ref_low = bars["mid_low"].shift(1).rolling(lb, min_periods=lb).min()
        atr = atr_simple(bars, int(spec["atr_lookback_bars"]))
        min_exc = float(spec["minimum_excursion_atr_fraction"]) * atr
        failed_high = (bars["mid_high"] > ref_high) & (close <= ref_high) & (close >= ref_low) & ((bars["mid_high"] - ref_high) >= min_exc)
        failed_low = (bars["mid_low"] < ref_low) & (close >= ref_low) & (close <= ref_high) & ((ref_low - bars["mid_low"]) >= min_exc)
        side.loc[failed_high & ~failed_low] = -1
        side.loc[failed_low & ~failed_high] = 1
    elif fid == "I":
        n = int(spec["compression_window_bars"])
        hist = int(spec["percentile_history_sessions"])
        high = bars["mid_high"].shift(1).rolling(n, min_periods=n).max()
        low = bars["mid_low"].shift(1).rolling(n, min_periods=n).min()
        width = high - low
        comparable = pd.concat([width.shift(24 * k) for k in range(1, hist + 1)], axis=1)
        threshold = comparable.quantile(float(spec["compression_percentile"]), axis=1, interpolation="linear")
        compressed = width <= threshold
        side.loc[compressed & (close > high)] = 1
        side.loc[compressed & (close < low)] = -1
    elif fid == "J":
        tz = ZoneInfo(spec["timezone"])
        local = bars["timestamp_utc"].dt.tz_convert(tz)
        local_date = local.dt.strftime("%Y-%m-%d")
        local_hour = local.dt.hour
        formation = list(map(int, spec["formation_local_hours"]))
        first_h, last_h = formation[0], formation[-1]
        temp = pd.DataFrame({"local_date": local_date, "local_hour": local_hour, "open": bars["mid_open"], "close": close})
        first = temp[temp["local_hour"] == first_h].set_index("local_date")["open"]
        last = temp[temp["local_hour"] == last_h].set_index("local_date")["close"]
        formation_ret = (last - first).rename("formation_ret")
        mapped = local_date.map(formation_ret)
        entry_ts = bars["timestamp_utc"].shift(-1)
        entry_local = entry_ts.dt.tz_convert(tz)
        allowed = entry_local.dt.hour.eq(int(spec["entry_local_hour"])) & local_hour.eq(last_h)
        side.loc[allowed & (mapped > 0)] = 1
        side.loc[allowed & (mapped < 0)] = -1
    else:
        raise ValueError(fid)
    return side
