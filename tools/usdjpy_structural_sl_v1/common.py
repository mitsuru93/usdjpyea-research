"""Canonical source materialization and execution-price helpers for structural SL v1."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PIP = 0.01
SPREAD_2023 = 0.005
FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]
EXPECTED_SHA = {
    "m15_2023": "4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78",
    "m1_2023": "167509bde6553a468ffe48b082ed79de183cc57991f668cf4b3e7341350d307e",
    "events_2024h1": "9560d6382e2457eaec83415316fb59d4989244d49c9977ce76cbdd717f32f09a",
    "events_2024h2": "a5a871d7105c6e68548e804c9ab517ee6bc0b08553474b158799f47ebd32edcd",
    "m1_2024": "f9f56be2daa39f07dc39cec197306fb87821ead01e4a640a73f17715bf27dde0",
}
EXPECTED_COUNTS = {
    "2023H1": {"B02": 121, "F05": 367},
    "2023H2": {"B02": 109, "F05": 363},
    "2024H1": {"B02": 97, "F05": 331},
    "2024H2": {"B02": 102, "F05": 392},
}
EVENT_IDS = [
    "SHARED_EARLY_M5_REENTRY_NO_PROFIT_V1",
    "SHARED_EARLY_REENTRY_NO_RECLAIM_120_V1",
    "SHARED_FAILED_RECLAIM_STRICT_NO_PROFIT_V1",
    "B02_FIRST_M15_REENTRY_NO_PROFIT_V1",
    "B02_M15_FAILED_RECLAIM_NO_PROFIT_V1",
    "B02_M15_NO_RECLAIM_120_NO_PROFIT_V1",
    "PROFIT_ARMED_M5_RANGE_FAILURE_V1",
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")


def r1(x: float) -> float:
    return float(round(float(x) + 0.0, 1))


def nth_sunday(year: int, month: int, n: int, hour: int) -> pd.Timestamp:
    d = datetime(year, month, 1, hour, tzinfo=timezone.utc)
    return pd.Timestamp(d + timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1)))


def us_dst(ts: pd.Timestamp) -> bool:
    return nth_sunday(ts.year, 3, 2, 7) <= ts < nth_sunday(ts.year, 11, 1, 6)


def server_to_historical_utc(ts: pd.Timestamp) -> pd.Timestamp:
    winter_candidate = ts - pd.Timedelta(hours=2)
    return ts - pd.Timedelta(hours=3) if us_dst(winter_candidate) else winter_candidate


def hard_exclusion(entry: pd.Series) -> pd.Series:
    local = entry.dt.tz_convert(ZoneInfo("America/New_York")).dt.time
    return (local >= time(16, 0)) & (local < time(19, 0))


def enrich_m15(d: pd.DataFrame) -> pd.DataFrame:
    x = d.copy()
    x["timestamp_utc"] = pd.to_datetime(x.timestamp_utc, utc=True)
    x = x.sort_values("timestamp_utc").reset_index(drop=True)
    x["date_utc"] = x.timestamp_utc.dt.strftime("%Y-%m-%d")
    x["hour_utc"] = x.timestamp_utc.dt.hour.astype(int)
    return x


def load_2023_m15(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    server = pd.to_datetime(d.first_timestamp_mt4_server, utc=True)
    historical = pd.DatetimeIndex([server_to_historical_utc(x) for x in server])
    assert historical.is_monotonic_increasing and not historical.duplicated().any()
    return enrich_m15(pd.DataFrame({
        "timestamp_utc": historical,
        "open": d.open.astype(float),
        "high": d.high.astype(float),
        "low": d.low.astype(float),
        "close": d.close.astype(float),
    }))


def first_direction_per_day(side: pd.Series, bars: pd.DataFrame) -> pd.Series:
    keep = pd.Series(0, index=side.index, dtype="int8")
    signals = pd.DataFrame({"side": side, "date": bars.date_utc, "ts": bars.timestamp_utc})
    signals = signals[signals.side.isin([1, -1])]
    if len(signals):
        idx = signals.sort_values("ts").groupby(["date", "side"], sort=False).head(1).index
        keep.loc[idx] = side.loc[idx].astype("int8")
    return keep


def historical_2023_trades(bars: pd.DataFrame) -> pd.DataFrame:
    start = pd.Timestamp("2023-01-01T00:00:00Z")
    end = pd.Timestamp("2024-01-01T00:00:00Z")
    frames: list[pd.DataFrame] = []

    ref = bars[(bars.hour_utc >= 0) & (bars.hour_utc < 7)].groupby("date_utc").agg(
        hi=("high", "max"), lo=("low", "min"), n=("open", "size")
    )
    r = bars[["date_utc"]].join(ref, on="date_utc")
    allow = (bars.hour_utc >= 7) & (bars.hour_utc <= 12)
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allow & (bars.close > r.hi)] = 1
    side.loc[allow & (bars.close < r.lo)] = -1
    side = first_direction_per_day(side, bars)
    b02 = pd.DataFrame({
        "signal_utc": bars.timestamp_utc,
        "entry_utc": bars.timestamp_utc.shift(-1),
        "side": side,
        "breakout_level": np.where(side.eq(1), r.hi, r.lo),
        "reference_count": r.n,
    })
    b02 = b02[b02.side.isin([1, -1]) & b02.entry_utc.notna()]
    b02 = b02[(b02.entry_utc >= start) & (b02.entry_utc < end)]
    b02 = b02[~hard_exclusion(b02.entry_utc) & (b02.reference_count >= 28)].copy()
    b02["strategy"] = "B02"
    b02["cap_bars"] = 48
    frames.append(b02)

    hi = bars.high.shift(1).rolling(96, min_periods=96).max()
    lo = bars.low.shift(1).rolling(96, min_periods=96).min()
    entry = bars.timestamp_utc.shift(-1)
    allow = entry.dt.hour.isin(range(20))
    side = pd.Series(0, index=bars.index, dtype="int8")
    side.loc[allow & (bars.close > hi) & (bars.close.shift(1) <= hi.shift(1))] = 1
    side.loc[allow & (bars.close < lo) & (bars.close.shift(1) >= lo.shift(1))] = -1
    f05 = pd.DataFrame({
        "signal_utc": bars.timestamp_utc,
        "entry_utc": entry,
        "side": side,
        "breakout_level": np.where(side.eq(1), hi, lo),
    })
    f05 = f05[f05.side.isin([1, -1]) & f05.entry_utc.notna()]
    f05 = f05[(f05.entry_utc >= start) & (f05.entry_utc < end)]
    f05 = f05[~hard_exclusion(f05.entry_utc)].copy()
    f05["strategy"] = "F05"
    f05["cap_bars"] = 32
    frames.append(f05)

    signals = pd.concat(frames).sort_values(["entry_utc", "strategy"], kind="mergesort")
    index_by_time = pd.Series(bars.index, index=bars.timestamp_utc).to_dict()
    rows: list[dict[str, object]] = []
    for tr in signals.itertuples(index=False):
        entry_index = int(index_by_time[tr.entry_utc])
        close_index = entry_index + int(tr.cap_bars)
        if close_index >= len(bars) or bars.timestamp_utc.iloc[close_index] >= end:
            continue
        side_i = int(tr.side)
        entry_bid = float(bars.open.iloc[entry_index])
        entry_price = entry_bid + SPREAD_2023 if side_i == 1 else entry_bid
        close_bid = float(bars.open.iloc[close_index])
        close_price = close_bid if side_i == 1 else close_bid + SPREAD_2023
        rows.append({
            "fold": "2023H1" if tr.entry_utc < pd.Timestamp("2023-07-01T00:00:00Z") else "2023H2",
            "strategy": tr.strategy,
            "signal_utc": tr.signal_utc,
            "entry_utc": tr.entry_utc,
            "close_utc": bars.timestamp_utc.iloc[close_index],
            "side": side_i,
            "entry_price": entry_price,
            "entry_bid": entry_bid,
            "breakout_level": float(tr.breakout_level),
            "baseline_pips": r1(side_i * (close_price - entry_price) / PIP),
        })
    return pd.DataFrame(rows)


def parse_level(detail: str, strategy: str, side: int) -> float:
    fields = dict(re.findall(r"(\w+)=([^;]+)", str(detail)))
    if strategy == "B02":
        return float(fields["session_high"] if side == 1 else fields["session_low"])
    return float(fields["current_high"] if side == 1 else fields["current_low"])


def parse_event_trades(path: Path, fold: str, include_period_mark: bool) -> pd.DataFrame:
    d = pd.read_csv(path, encoding="utf-8-sig")
    opened = d[d.event == "order_opened"][[
        "ticket", "strategy", "signal_utc", "entry_utc", "side", "price", "detail"
    ]].copy()
    closed = d[d.event == "order_closed"][["ticket", "utc_time", "gross_pips"]].rename(
        columns={"utc_time": "close_utc"}
    )
    t = opened.merge(closed, on="ticket", how="left", validate="one_to_one")
    for col in ["signal_utc", "entry_utc"]:
        t[col] = pd.to_datetime(t[col], format="%Y.%m.%d %H:%M:%S", utc=True)
    t["close_utc"] = pd.to_datetime(t.close_utc, format="%Y.%m.%d %H:%M:%S", utc=True)
    if include_period_mark:
        missing = t.close_utc.isna()
        assert int(missing.sum()) == 1
        period = d[d.event == "period_end_open_position"].iloc[0]
        snaps = d[d.event == "portfolio_snapshot"].copy()
        snaps["obs"] = pd.to_datetime(snaps.utc_time, format="%Y.%m.%d %H:%M:%S", utc=True)
        snaps = snaps[snaps.obs.dt.year == 2024]
        t.loc[missing, "close_utc"] = snaps.obs.max()
        floating = float(re.search(r"floating_pl=([-0-9.]+)", str(period.detail)).group(1))
        t.loc[missing, "gross_pips"] = floating / 10.0
    else:
        t = t[t.close_utc.notna()].copy()
    t["fold"] = fold
    t["entry_price"] = t.price.astype(float)
    t["entry_bid"] = t.entry_price - np.where(t.side.eq(1), SPREAD_2023, 0.0)
    t["breakout_level"] = [parse_level(r.detail, r.strategy, int(r.side)) for r in t.itertuples(index=False)]
    t["baseline_pips"] = t.gross_pips.astype(float).round(1)
    return t[[
        "fold", "strategy", "signal_utc", "entry_utc", "close_utc", "side",
        "entry_price", "entry_bid", "breakout_level", "baseline_pips",
    ]]


def load_m1(m1_2023: Path, m1_2024: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = pd.read_csv(m1_2023)
    server = pd.to_datetime(d.timestamp_mt4_server, utc=True)
    historical = pd.DatetimeIndex([server_to_historical_utc(x) for x in server])
    m23 = pd.DataFrame({
        "t": historical,
        "bid_open": d.open.astype(float),
        "bid_high": d.high.astype(float),
        "bid_low": d.low.astype(float),
        "bid_close": d.close.astype(float),
    })
    for field in ["open", "high", "low", "close"]:
        m23[f"ask_{field}"] = m23[f"bid_{field}"] + SPREAD_2023
    m23 = m23.sort_values("t").drop_duplicates("t").set_index("t")

    d = pd.read_csv(m1_2024)
    d["t"] = pd.to_datetime(d.time, utc=True)
    m24 = d.set_index("t").sort_index()[[
        "bid_open", "bid_high", "bid_low", "bid_close",
        "ask_open", "ask_high", "ask_low", "ask_close",
    ]]
    return m23, m24


def aggregate_bars(m1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    rule = f"{minutes}min"
    aggregation: dict[str, str] = {}
    for prefix in ["bid", "ask"]:
        aggregation.update({
            f"{prefix}_open": "first",
            f"{prefix}_high": "max",
            f"{prefix}_low": "min",
            f"{prefix}_close": "last",
        })
    x = m1.resample(rule, closed="left", label="left").agg(aggregation).dropna()
    x["completion"] = x.index + pd.Timedelta(minutes=minutes)
    return x


def executable_price(row: pd.Series, side: int, field: str) -> float:
    return float(row[f"bid_{field}" if side == 1 else f"ask_{field}"])


def pnl(price: float, entry_price: float, side: int) -> float:
    return side * (price - entry_price) / PIP


def max_exec(m1: pd.DataFrame, entry: pd.Timestamp, end: pd.Timestamp, entry_price: float, side: int) -> float:
    w = m1[(m1.index >= entry) & ((m1.index + pd.Timedelta(minutes=1)) <= end)]
    if w.empty:
        return math.nan
    return (float(w.bid_high.max()) - entry_price) / PIP if side == 1 else (entry_price - float(w.ask_low.min())) / PIP


def min_exec(m1: pd.DataFrame, entry: pd.Timestamp, end: pd.Timestamp, entry_price: float, side: int) -> float:
    w = m1[(m1.index >= entry) & ((m1.index + pd.Timedelta(minutes=1)) <= end)]
    if w.empty:
        return math.nan
    return (float(w.bid_low.min()) - entry_price) / PIP if side == 1 else (entry_price - float(w.ask_high.max())) / PIP


def inside(price: float, level: float, side: int, buffer_price: float = 0.0) -> bool:
    return price <= level - buffer_price + 1e-12 if side == 1 else price >= level + buffer_price - 1e-12


def outside(price: float, level: float, side: int) -> bool:
    return price > level + 1e-12 if side == 1 else price < level - 1e-12


def next_exit(m1: pd.DataFrame, trigger: pd.Timestamp, baseline_close: pd.Timestamp) -> tuple[pd.Timestamp, pd.Series] | None:
    q = m1[m1.index >= trigger]
    if q.empty or q.index[0] >= baseline_close:
        return None
    return q.index[0], q.iloc[0]
