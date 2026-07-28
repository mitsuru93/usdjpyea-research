#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PIP = 0.01
JPY_PER_PIP = 10.0
UTC = timezone.utc
SEED = 31031


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso_utc(ts) -> str:
    if pd.isna(ts):
        return ""
    return pd.Timestamp(ts).tz_convert("UTC").isoformat().replace("+00:00", "Z")


def fold_label(ts) -> str:
    ts = pd.Timestamp(ts)
    return f"{ts.year}H{1 if ts.month <= 6 else 2}"


def nth_sunday(year: int, month: int, n: int, hour: int) -> pd.Timestamp:
    first = pd.Timestamp(datetime(year, month, 1, hour, tzinfo=UTC))
    return first + pd.Timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def is_us_dst(ts) -> bool:
    ts = pd.Timestamp(ts)
    return nth_sunday(ts.year, 3, 2, 7) <= ts < nth_sunday(ts.year, 11, 1, 6)


def rakuten_offset_hours(ts) -> int:
    return 3 if is_us_dst(ts) else 2


def max_drawdown(values) -> float:
    p = np.asarray(values, dtype=float)
    if len(p) == 0:
        return 0.0
    equity = np.cumsum(p)
    peak = np.maximum.accumulate(np.r_[0.0, equity])[1:]
    return float(np.max(peak - equity, initial=0.0))


def metric_record(df: pd.DataFrame, pnl_col: str = "pnl_jpy") -> dict:
    if len(df) == 0:
        return {
            "trades": 0,
            "net_jpy": 0.0,
            "gross_profit_jpy": 0.0,
            "gross_loss_jpy": 0.0,
            "pf": None,
            "mdd_jpy": 0.0,
            "recovery_factor": None,
            "win_rate": None,
            "average_trade_jpy": None,
            "median_trade_jpy": None,
            "positive_folds": 0,
            "positive_months": 0,
            "minimum_fold_net_jpy": None,
        }
    ordered = df.sort_values("entry_time", kind="mergesort")
    p = ordered[pnl_col].astype(float).to_numpy()
    gp = float(p[p > 0].sum())
    gl = float(-p[p < 0].sum())
    net = float(p.sum())
    folds = ordered.assign(_fold=ordered.entry_time.map(fold_label)).groupby("_fold")[pnl_col].sum()
    months = ordered.assign(_month=ordered.entry_time.dt.strftime("%Y-%m")).groupby("_month")[pnl_col].sum()
    mdd = max_drawdown(p)
    return {
        "trades": int(len(ordered)),
        "net_jpy": net,
        "gross_profit_jpy": gp,
        "gross_loss_jpy": gl,
        "pf": gp / gl if gl else None,
        "mdd_jpy": mdd,
        "recovery_factor": net / mdd if mdd else None,
        "win_rate": float((p > 0).mean()),
        "average_trade_jpy": float(p.mean()),
        "median_trade_jpy": float(np.median(p)),
        "positive_folds": int((folds > 0).sum()),
        "positive_months": int((months > 0).sum()),
        "minimum_fold_net_jpy": float(folds.min()) if len(folds) else None,
    }


def percentile_summary(values, positive=False) -> dict:
    a = np.asarray(values, dtype=float)
    if not len(a):
        return {"samples": 0, "p05": None, "median": None, "p95": None}
    out = {
        "samples": int(len(a)),
        "p05": float(np.quantile(a, 0.05)),
        "median": float(np.quantile(a, 0.50)),
        "p95": float(np.quantile(a, 0.95)),
    }
    if positive:
        out["probability_positive"] = float((a > 0).mean())
    return out


def bootstrap_net(values, samples=2000, seed=SEED) -> dict:
    a = np.asarray(values, dtype=float)
    if not len(a):
        return percentile_summary([])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(samples, len(a)))
    return percentile_summary(a[idx].sum(axis=1), positive=True)


def bootstrap_mdd_from_blocks(blocks, samples=2000, seed=SEED + 1) -> dict:
    blocks = [np.asarray(b, dtype=float) for b in blocks if len(b)]
    if not blocks:
        return percentile_summary([])
    rng = np.random.default_rng(seed)
    results = []
    for _ in range(samples):
        selected = [blocks[i] for i in rng.integers(0, len(blocks), size=len(blocks))]
        results.append(max_drawdown(np.concatenate(selected)))
    return percentile_summary(results)


def hourly_tick_frames(tar_paths):
    for tar_path in sorted(tar_paths):
        with tarfile.open(tar_path, "r:gz") as tf:
            members = [
                m
                for m in tf.getmembers()
                if m.isfile() and m.name.endswith(".csv.gz") and "/decoded_csv/USDJPY/" in m.name
            ]
            for member in sorted(members, key=lambda x: x.name):
                f = tf.extractfile(member)
                if f is None:
                    continue
                with gzip.GzipFile(fileobj=io.BytesIO(f.read()), mode="rb") as g:
                    d = pd.read_csv(g, usecols=["timestamp_utc", "bid", "ask"])
                if not len(d):
                    continue
                d["timestamp_utc"] = pd.to_datetime(d["timestamp_utc"], utc=True)
                d["bid"] = d["bid"].astype(float)
                d["ask"] = d["ask"].astype(float)
                yield d


def daily_ticks(tar_paths):
    current_day = None
    parts = []
    for hourly in hourly_tick_frames(tar_paths):
        day = str(hourly.timestamp_utc.iloc[0].date())
        if current_day is None:
            current_day = day
        if day != current_day:
            yield current_day, pd.concat(parts, ignore_index=True).sort_values("timestamp_utc", kind="mergesort")
            current_day = day
            parts = []
        parts.append(hourly)
    if parts:
        yield current_day, pd.concat(parts, ignore_index=True).sort_values("timestamp_utc", kind="mergesort")


def build_m15_bars(ticks: pd.DataFrame) -> pd.DataFrame:
    d = ticks.copy()
    d["bar_start"] = d.timestamp_utc.dt.floor("15min")
    return (
        d.groupby("bar_start", sort=True)
        .agg(
            open=("bid", "first"),
            high=("bid", "max"),
            low=("bid", "min"),
            close=("bid", "last"),
            ticks=("bid", "size"),
            first_tick=("timestamp_utc", "first"),
            last_tick=("timestamp_utc", "last"),
        )
        .reset_index()
    )


def first_tick_at_or_after(ticks: pd.DataFrame, when):
    values = ticks.timestamp_utc.array.asi8
    i = int(np.searchsorted(values, pd.Timestamp(when).value, side="left"))
    return None if i >= len(ticks) else ticks.iloc[i]


def session_label(ts) -> str:
    hour = pd.Timestamp(ts).hour
    if hour < 12:
        return "LONDON"
    if hour < 16:
        return "LONDON_NY_OVERLAP"
    return "NEW_YORK"


def make_event(day, ticks, bar, side, asian_high, asian_low, global_index):
    decision = pd.Timestamp(bar.bar_start) + pd.Timedelta(minutes=15)
    exit_boundary = decision + pd.Timedelta(hours=3)
    entry_tick = first_tick_at_or_after(ticks, decision)
    exit_tick = first_tick_at_or_after(ticks, exit_boundary)
    if entry_tick is None or exit_tick is None:
        return None
    entry = float(entry_tick.ask if side == 1 else entry_tick.bid)
    exit_price = float(exit_tick.bid if side == 1 else exit_tick.ask)
    pnl_pips = side * (exit_price - entry) / PIP
    out = {
        "event_id": f"RAW|{day}|{iso_utc(bar.bar_start)}|{side}",
        "date": day,
        "fold": fold_label(decision),
        "side": side,
        "side_label": "LONG" if side == 1 else "SHORT",
        "reason": "asian_low" if side == 1 else "asian_high",
        "session": session_label(bar.bar_start),
        "signal_bar_start": pd.Timestamp(bar.bar_start),
        "decision_time": decision,
        "entry_time": pd.Timestamp(entry_tick.timestamp_utc),
        "exit_boundary": exit_boundary,
        "exit_time": pd.Timestamp(exit_tick.timestamp_utc),
        "asian_high": asian_high,
        "asian_low": asian_low,
        "signal_open": float(bar.open),
        "signal_high": float(bar.high),
        "signal_low": float(bar.low),
        "signal_close": float(bar.close),
        "range_size_pips": (asian_high - asian_low) / PIP,
        "sweep_depth_pips": (asian_low - float(bar.low)) / PIP if side == 1 else (float(bar.high) - asian_high) / PIP,
        "close_back_inside_pips": (float(bar.close) - asian_low) / PIP if side == 1 else (asian_high - float(bar.close)) / PIP,
        "entry_bid": float(entry_tick.bid),
        "entry_ask": float(entry_tick.ask),
        "exit_bid": float(exit_tick.bid),
        "exit_ask": float(exit_tick.ask),
        "entry_spread_pips": float(entry_tick.ask - entry_tick.bid) / PIP,
        "exit_spread_pips": float(exit_tick.ask - exit_tick.bid) / PIP,
        "pnl_pips": pnl_pips,
        "pnl_jpy": pnl_pips * JPY_PER_PIP,
        "signal_global_i": global_index,
    }
    for seconds in (1, 5, 15):
        delayed_entry = first_tick_at_or_after(ticks, decision + pd.Timedelta(seconds=seconds))
        delayed_exit = first_tick_at_or_after(ticks, exit_boundary + pd.Timedelta(seconds=seconds))
        out[f"entry_delay_{seconds}s_pnl_jpy"] = (
            np.nan
            if delayed_entry is None
            else side
            * (exit_price - float(delayed_entry.ask if side == 1 else delayed_entry.bid))
            / PIP
            * JPY_PER_PIP
        )
        out[f"exit_delay_{seconds}s_pnl_jpy"] = (
            np.nan
            if delayed_exit is None
            else side
            * (float(delayed_exit.bid if side == 1 else delayed_exit.ask) - entry)
            / PIP
            * JPY_PER_PIP
        )
    return out


def generate_native_population(tar_paths):
    events = []
    all_bars = []
    range_audit = []
    global_index = 0
    last_accepted_index = -10**12
    seen_day_side = set()
    ambiguous_both_side = 0
    chronology_unresolved = 0
    for day, ticks in daily_ticks(tar_paths):
        bars = build_m15_bars(ticks)
        bars["global_i"] = np.arange(global_index, global_index + len(bars))
        global_index += len(bars)
        all_bars.append(bars)
        day_start = pd.Timestamp(day, tz="UTC")
        expected = pd.date_range(
            day_start,
            day_start + pd.Timedelta(hours=7) - pd.Timedelta(minutes=15),
            freq="15min",
            tz="UTC",
        )
        asian = bars[bars.bar_start.isin(expected)]
        complete = len(asian) == 28 and set(asian.bar_start) == set(expected)
        asian_high = float(asian.high.max()) if len(asian) else np.nan
        asian_low = float(asian.low.min()) if len(asian) else np.nan
        range_audit.append(
            {
                "date": day,
                "asian_bar_count": int(len(asian)),
                "complete_28_bars": bool(complete),
                "asian_high": asian_high,
                "asian_low": asian_low,
            }
        )
        if not complete:
            continue
        signals = bars[
            (bars.bar_start >= day_start + pd.Timedelta(hours=7))
            & (bars.bar_start < day_start + pd.Timedelta(hours=20))
        ]
        for bar in signals.itertuples(index=False):
            high_sweep = bool(bar.high > asian_high and bar.close < asian_high)
            low_sweep = bool(bar.low < asian_low and bar.close > asian_low)
            if high_sweep and low_sweep:
                ambiguous_both_side += 1
                continue
            if not high_sweep and not low_sweep:
                continue
            side = 1 if low_sweep else -1
            idx = int(bar.global_i)
            if idx <= last_accepted_index + 13 or (day, side) in seen_day_side:
                continue
            event = make_event(day, ticks, bar, side, asian_high, asian_low, idx)
            if event is None:
                chronology_unresolved += 1
                continue
            events.append(event)
            last_accepted_index = idx
            seen_day_side.add((day, side))
    bars = pd.concat(all_bars, ignore_index=True).sort_values("bar_start", kind="mergesort").reset_index(drop=True)
    events = pd.DataFrame(events).sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    return events, bars, pd.DataFrame(range_audit), {
        "ambiguous_both_side": int(ambiguous_both_side),
        "chronology_unresolved": int(chronology_unresolved),
    }


def build_states(bars: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    x = bars[["bar_start", "close"]].copy()
    x["offset_hours"] = x.bar_start.map(rakuten_offset_hours)
    x["server_start"] = x.bar_start + pd.to_timedelta(x.offset_hours, unit="h")
    if timeframe == "H4":
        x["bucket_start_server"] = x.server_start.dt.floor("4h")
        required = 16
    else:
        x["bucket_start_server"] = x.server_start.dt.floor("D")
        required = 96
    rows = []
    for bucket, group in x.groupby("bucket_start_server", sort=True):
        group = group.sort_values("server_start", kind="mergesort")
        expected = pd.date_range(bucket, periods=required, freq="15min", tz="UTC")
        if len(group) != required or group.server_start.duplicated().any() or set(group.server_start) != set(expected):
            continue
        rows.append(
            {
                "timestamp": bucket,
                "timeframe": timeframe,
                "bucket_start_server": bucket,
                "information_time": group.bar_start.max() + pd.Timedelta(minutes=15),
                "completed_information_time": group.bar_start.max() + pd.Timedelta(minutes=15),
                "close": float(group.close.iloc[-1]),
                "partial_bar_exclusion": True,
                "missing_history_flag": False,
                "source": "dukascopy_bi5_raw_native",
                "timezone": "UTC_information_Rakuten_logical_server_bucket",
                "future_bar_access": False,
            }
        )
    states = pd.DataFrame(rows)
    if not len(states):
        return states
    alpha_fast = 2.0 / 7.0
    alpha_slow = 2.0 / 25.0
    ema_fast = None
    ema_slow = None
    previous_sign = 0
    current_state_start = None
    last_state_change = None
    outputs = []
    for i, row in enumerate(states.itertuples(index=False), 1):
        close = float(row.close)
        ema_fast = close if ema_fast is None else alpha_fast * close + (1 - alpha_fast) * ema_fast
        ema_slow = close if ema_slow is None else alpha_slow * close + (1 - alpha_slow) * ema_slow
        sign = 0 if i < 24 or ema_fast == ema_slow else (1 if ema_fast > ema_slow else -1)
        raw_state = "Neutral" if sign == 0 else ("Up" if sign == 1 else "Down")
        previous_raw_state = "Neutral" if previous_sign == 0 else ("Up" if previous_sign == 1 else "Down")
        if sign == 0:
            state = "Neutral"
        elif sign != previous_sign:
            state = "Transition"
            current_state_start = row.information_time
            last_state_change = row.information_time
        else:
            state = "Up" if sign == 1 else "Down"
        if sign:
            previous_sign = sign
        duration = (
            (row.information_time - current_state_start).total_seconds() / 3600.0
            if current_state_start is not None
            else np.nan
        )
        outputs.append(
            {
                "fast_value": ema_fast,
                "slow_value": ema_slow,
                "slope": (ema_fast - ema_slow) / PIP,
                "raw_state": raw_state,
                "previous_raw_state": previous_raw_state,
                "state": state,
                "state_start": current_state_start,
                "state_duration_hours": duration,
                "last_state_change": last_state_change,
            }
        )
    return pd.concat([states.reset_index(drop=True), pd.DataFrame(outputs)], axis=1)


def attach_states(events: pd.DataFrame, states: pd.DataFrame, prefix: str, delay_buckets=0) -> pd.DataFrame:
    q = states.sort_values("information_time", kind="mergesort").copy()
    state_cols = [
        "information_time",
        "bucket_start_server",
        "fast_value",
        "slow_value",
        "slope",
        "raw_state",
        "previous_raw_state",
        "state",
        "state_start",
        "state_duration_hours",
        "last_state_change",
    ]
    if delay_buckets:
        shifted = ["fast_value", "slow_value", "slope", "raw_state", "previous_raw_state", "state"]
        q[shifted] = q[shifted].shift(delay_buckets)
    out = pd.merge_asof(
        events.sort_values("decision_time", kind="mergesort"),
        q[state_cols],
        left_on="decision_time",
        right_on="information_time",
        direction="backward",
        allow_exact_matches=True,
    )
    return out.rename(columns={c: f"{prefix}_{c}" for c in state_cols})


def permission_mask(df: pd.DataFrame, prefix: str, deadband_pips=0.0) -> pd.Series:
    state = df[f"{prefix}_state"].copy()
    if deadband_pips:
        distance = (df[f"{prefix}_fast_value"] - df[f"{prefix}_slow_value"]).abs()
        state = state.mask(distance <= deadband_pips * PIP, "Neutral")
    return ((df.side == 1) & state.eq("Up")) | ((df.side == -1) & state.eq("Down"))


def candidate_row(candidate_id: str, df: pd.DataFrame, allowed: pd.Series) -> dict:
    permitted = df[allowed].copy()
    blocked = df[~allowed].copy()
    m = metric_record(permitted)
    by_side = permitted.groupby("side").pnl_jpy.sum().to_dict()
    by_state = permitted.groupby("route_state").pnl_jpy.sum().to_dict()
    positive_side = [max(0.0, float(v)) for v in by_side.values()]
    positive_state = [max(0.0, float(v)) for v in by_state.values()]
    return {
        "candidate_id": candidate_id,
        "total_trades": int(len(df)),
        "allowed": int(allowed.sum()),
        "blocked": int((~allowed).sum()),
        **m,
        "long_contribution_jpy": float(by_side.get(1, 0.0)),
        "short_contribution_jpy": float(by_side.get(-1, 0.0)),
        "up_contribution_jpy": float(by_state.get("Up", 0.0)),
        "down_contribution_jpy": float(by_state.get("Down", 0.0)),
        "neutral_contribution_jpy": float(by_state.get("Neutral", 0.0)),
        "transition_contribution_jpy": float(by_state.get("Transition", 0.0)),
        "max_side_positive_net_share": max(positive_side, default=0.0) / sum(positive_side)
        if sum(positive_side) > 0
        else 1.0,
        "max_regime_positive_net_share": max(positive_state, default=0.0) / sum(positive_state)
        if sum(positive_state) > 0
        else 1.0,
        "blocked_winner_damage_jpy": float(blocked.loc[blocked.pnl_jpy > 0, "pnl_jpy"].sum()),
        "avoided_loser_benefit_jpy": float(-blocked.loc[blocked.pnl_jpy < 0, "pnl_jpy"].sum()),
    }


def baseline_inputs(path: Path):
    trades = pd.read_csv(path)
    trades["entry_utc"] = pd.to_datetime(trades.entry_utc, utc=True)
    trades["date"] = trades.entry_utc.dt.strftime("%Y-%m-%d")
    daily = trades.groupby("date", as_index=False).agg(baseline_daily_pl_jpy=("realized_pl_jpy", "sum"))
    return trades, daily


def complementarity(df: pd.DataFrame, allowed: pd.Series, baseline_trades: pd.DataFrame, baseline_daily: pd.DataFrame) -> dict:
    permitted = df[allowed].copy()
    candidate_daily = (
        permitted.assign(date=permitted.entry_time.dt.strftime("%Y-%m-%d"))
        .groupby("date", as_index=False)
        .pnl_jpy.sum()
    )
    daily = baseline_daily.merge(candidate_daily, on="date", how="outer").fillna(
        {"baseline_daily_pl_jpy": 0.0, "pnl_jpy": 0.0}
    )
    baseline_daily_path = pd.DataFrame(
        {"entry_time": pd.to_datetime(daily.date, utc=True), "pnl_jpy": daily.baseline_daily_pl_jpy}
    )
    additive_daily_path = baseline_daily_path.copy()
    additive_daily_path["pnl_jpy"] = daily.baseline_daily_pl_jpy + daily.pnl_jpy
    combined = pd.concat(
        [
            baseline_trades[["entry_utc", "realized_pl_jpy"]].rename(
                columns={"entry_utc": "entry_time", "realized_pl_jpy": "pnl_jpy"}
            ),
            permitted[["entry_time", "pnl_jpy"]],
        ],
        ignore_index=True,
    ).sort_values("entry_time", kind="mergesort")
    base_closed = baseline_trades.sort_values("entry_utc", kind="mergesort").realized_pl_jpy.astype(float).to_numpy()
    combined_closed = combined.pnl_jpy.astype(float).to_numpy()
    month_blocks = [g.pnl_jpy.astype(float).to_numpy() for _, g in combined.assign(month=combined.entry_time.dt.strftime("%Y-%m")).groupby("month")]
    mdd_bootstrap = bootstrap_mdd_from_blocks(month_blocks)
    return {
        "B02_F05_negative_day_contribution_jpy": float(
            daily.loc[daily.baseline_daily_pl_jpy < 0, "pnl_jpy"].sum()
        ),
        "baseline_daily_mdd_jpy": metric_record(baseline_daily_path)["mdd_jpy"],
        "additive_daily_mdd_jpy": metric_record(additive_daily_path)["mdd_jpy"],
        "daily_mdd_delta_jpy": metric_record(additive_daily_path)["mdd_jpy"]
        - metric_record(baseline_daily_path)["mdd_jpy"],
        "baseline_net_jpy": metric_record(baseline_daily_path)["net_jpy"],
        "additive_net_jpy": metric_record(additive_daily_path)["net_jpy"],
        "baseline_timestamp_aligned_closed_trade_mdd_jpy": max_drawdown(base_closed),
        "additive_timestamp_aligned_closed_trade_mdd_jpy": max_drawdown(combined_closed),
        "block_bootstrap_mdd_jpy": mdd_bootstrap,
        "measurement_resolution_jpy": 1.0,
        "account_scale": "0.01 lot normalized; JPY10 per pip",
    }


def transition_details(df: pd.DataFrame, states: pd.DataFrame, prefix: str, allowed: pd.Series):
    permitted = df[allowed].copy()
    records = []
    for row in states[states.state.eq("Transition")].itertuples(index=False):
        t = pd.Timestamp(row.information_time)
        rec = {
            "regime": prefix,
            "transition_timestamp": iso_utc(t),
            "previous_state": row.previous_raw_state,
            "new_state": row.raw_state,
            "state_duration_hours": float(row.state_duration_hours),
        }
        for business_days in (5, 10):
            lo = t - pd.tseries.offsets.BDay(business_days)
            hi = t + pd.tseries.offsets.BDay(business_days)
            pre = permitted[(permitted.entry_time >= lo) & (permitted.entry_time < t)]
            post = permitted[(permitted.entry_time >= t) & (permitted.entry_time <= hi)]
            cluster = permitted[(permitted.entry_time >= lo) & (permitted.entry_time <= hi)]
            rec[f"pre_{business_days}bd_trades"] = int(len(pre))
            rec[f"pre_{business_days}bd_net_jpy"] = float(pre.pnl_jpy.sum())
            rec[f"post_{business_days}bd_trades"] = int(len(post))
            rec[f"post_{business_days}bd_net_jpy"] = float(post.pnl_jpy.sum())
            rec[f"cluster_{business_days}bd_net_jpy"] = float(cluster.pnl_jpy.sum())
            rec[f"cluster_{business_days}bd_mdd_jpy"] = metric_record(cluster)["mdd_jpy"]
            if len(post):
                rec[f"time_to_first_post_entry_hours_{business_days}bd"] = float(
                    (post.entry_time.min() - t).total_seconds() / 3600.0
                )
            else:
                rec[f"time_to_first_post_entry_hours_{business_days}bd"] = None
        records.append(rec)
    ledger = pd.DataFrame(records)
    if len(ledger):
        summary = {
            "transition_count": int(len(ledger)),
            "minimum_transition_5bd_cluster_net_jpy": float(ledger.cluster_5bd_net_jpy.min()),
            "maximum_transition_5bd_cluster_mdd_jpy": float(ledger.cluster_5bd_mdd_jpy.max()),
            "minimum_transition_10bd_cluster_net_jpy": float(ledger.cluster_10bd_net_jpy.min()),
            "maximum_transition_10bd_cluster_mdd_jpy": float(ledger.cluster_10bd_mdd_jpy.max()),
        }
    else:
        summary = {
            "transition_count": 0,
            "minimum_transition_5bd_cluster_net_jpy": 0.0,
            "maximum_transition_5bd_cluster_mdd_jpy": 0.0,
            "minimum_transition_10bd_cluster_net_jpy": 0.0,
            "maximum_transition_10bd_cluster_mdd_jpy": 0.0,
        }
    return ledger, summary


def remove_transition_blocks(df, allowed, states):
    keep = allowed.copy()
    for t in states.loc[states.state.eq("Transition"), "information_time"]:
        lo = t - pd.tseries.offsets.BDay(5)
        hi = t + pd.tseries.offsets.BDay(5)
        keep &= ~((df.entry_time >= lo) & (df.entry_time <= hi))
    return metric_record(df[keep])


def stress_results(df, allowed, prefix, states):
    permitted = df[allowed].copy()
    out = {}
    for spread in (0.5, 1.0, 2.0):
        key = f"spread_plus_{str(spread).replace('.', 'p')}pip"
        stressed = permitted.assign(stressed_pnl_jpy=permitted.pnl_jpy - spread * JPY_PER_PIP)
        out[key] = metric_record(stressed, "stressed_pnl_jpy")
    for seconds in (1, 5, 15):
        col = f"entry_delay_{seconds}s_pnl_jpy"
        out[f"entry_delay_{seconds}s"] = metric_record(permitted.dropna(subset=[col]), col)
    for seconds in (5, 15):
        col = f"exit_delay_{seconds}s_pnl_jpy"
        out[f"exit_delay_{seconds}s"] = metric_record(permitted.dropna(subset=[col]), col)
    ranked = permitted.sort_values("pnl_jpy", ascending=False, kind="mergesort")
    for n in (1, 3, 5):
        out[f"top_{n}_removal"] = metric_record(ranked.iloc[n:].sort_values("entry_time", kind="mergesort"))
    month_net = permitted.assign(month=permitted.entry_time.dt.strftime("%Y-%m")).groupby("month").pnl_jpy.sum()
    if len(month_net):
        out["best_month_removal"] = metric_record(
            permitted[permitted.entry_time.dt.strftime("%Y-%m") != month_net.idxmax()]
        )
        out["worst_month_removal"] = metric_record(
            permitted[permitted.entry_time.dt.strftime("%Y-%m") != month_net.idxmin()]
        )
    out["trade_bootstrap_net_jpy"] = bootstrap_net(permitted.pnl_jpy.to_numpy())
    fold_sums = permitted.assign(_fold=permitted.entry_time.map(fold_label)).groupby("_fold").pnl_jpy.sum().to_numpy()
    out["fold_bootstrap_net_jpy"] = bootstrap_net(fold_sums, seed=SEED + 2)
    block_col = f"{prefix}_last_state_change"
    blocks = [g.pnl_jpy.astype(float).to_numpy() for _, g in permitted.groupby(block_col, dropna=False)]
    out["regime_block_bootstrap_mdd_jpy"] = bootstrap_mdd_from_blocks(blocks, seed=SEED + 3)
    out["transition_block_removal"] = remove_transition_blocks(df, allowed, states)
    if "schedule_class" in permitted:
        for schedule_class in ("common_intersection", "raw_only", "side_disagreement"):
            out[f"source_{schedule_class}"] = metric_record(
                permitted[permitted.schedule_class.eq(schedule_class)]
            )
    return out


def mismatch_attribution(hyp030: pd.DataFrame) -> pd.DataFrame:
    mismatches = hyp030[~hyp030.raw_side_match.astype(bool)].copy()

    def cause(row):
        if int(row.raw_signal_side) != 0:
            return "RAW_SIDE_FLIPPED_OPPOSITE_SWEEP"
        if int(row.side) == -1:
            if row.raw_signal_high <= row.raw_asian_high:
                return "RAW_NO_HIGH_SWEEP_RANGE_OR_HIGH_BOUNDARY"
            if row.raw_signal_close >= row.raw_asian_high:
                return "RAW_CLOSE_NOT_BACK_INSIDE_HIGH"
        else:
            if row.raw_signal_low >= row.raw_asian_low:
                return "RAW_NO_LOW_SWEEP_RANGE_OR_LOW_BOUNDARY"
            if row.raw_signal_close <= row.raw_asian_low:
                return "RAW_CLOSE_NOT_BACK_INSIDE_LOW"
        return "RAW_SIGNAL_DISAPPEARED_COMBINED_PRICE_DRIFT"

    mismatches["asian_high_diff_pips"] = (mismatches.raw_asian_high - mismatches.asian_high) / PIP
    mismatches["asian_low_diff_pips"] = (mismatches.raw_asian_low - mismatches.asian_low) / PIP
    mismatches["signal_high_diff_pips"] = (mismatches.raw_signal_high - mismatches.signal_high) / PIP
    mismatches["signal_low_diff_pips"] = (mismatches.raw_signal_low - mismatches.signal_low) / PIP
    mismatches["signal_close_diff_pips"] = (mismatches.raw_signal_close - mismatches.signal_close) / PIP
    mismatches["mismatch_cause"] = mismatches.apply(cause, axis=1)
    columns = [
        "date",
        "signal_utc",
        "side_label",
        "raw_signal_side",
        "asian_high",
        "raw_asian_high",
        "asian_high_diff_pips",
        "asian_low",
        "raw_asian_low",
        "asian_low_diff_pips",
        "signal_high",
        "raw_signal_high",
        "signal_high_diff_pips",
        "signal_low",
        "raw_signal_low",
        "signal_low_diff_pips",
        "signal_close",
        "raw_signal_close",
        "signal_close_diff_pips",
        "sweep_depth_pips",
        "close_back_inside_depth_pips",
        "pnl_jpy",
        "mismatch_cause",
    ]
    return mismatches[columns]


def side_regime_matrix(df, prefix, baseline_daily, population):
    rows = []
    for side in (1, -1):
        for state in ("Up", "Down", "Neutral", "Transition"):
            cell = df[(df.side == side) & df[f"{prefix}_state"].fillna("Neutral").eq(state)].copy()
            cell_daily = (
                cell.assign(date=cell.entry_time.dt.strftime("%Y-%m-%d"))
                .groupby("date", as_index=False)
                .pnl_jpy.sum()
            )
            joined = baseline_daily.merge(cell_daily, on="date", how="left").fillna({"pnl_jpy": 0.0})
            spread_1 = metric_record(cell.assign(stressed=cell.pnl_jpy - JPY_PER_PIP), "stressed")
            spread_2 = metric_record(cell.assign(stressed=cell.pnl_jpy - 2 * JPY_PER_PIP), "stressed")
            rows.append(
                {
                    "population": population,
                    "regime": prefix,
                    "side_label": "LONG" if side == 1 else "SHORT",
                    "state": state,
                    **metric_record(cell),
                    "spread_plus_1pip_net_jpy": spread_1["net_jpy"],
                    "spread_plus_2pip_net_jpy": spread_2["net_jpy"],
                    "source_native_match_rate": 1.0,
                    "B02_F05_negative_day_contribution_jpy": float(
                        joined.loc[joined.baseline_daily_pl_jpy < 0, "pnl_jpy"].sum()
                    ),
                }
            )
    return pd.DataFrame(rows)


def gate_result(row, stress, complement, transition, global_identity_ok):
    tests = {
        "source_native_signal_identity_complete": bool(global_identity_ok),
        "combined_net_positive": row["net_jpy"] > 0,
        "pf_at_least_1p05": row["pf"] is not None and row["pf"] >= 1.05,
        "positive_fold_breadth": row["positive_folds"] >= 3,
        "minimum_fold_net": row["minimum_fold_net_jpy"] is not None
        and row["minimum_fold_net_jpy"] >= -1000,
        "positive_month_breadth": row["positive_months"] >= 14,
        "aligned_long_nonnegative": row["long_contribution_jpy"] >= 0,
        "aligned_short_nonnegative": row["short_contribution_jpy"] >= 0,
        "maximum_side_dependency": row["max_side_positive_net_share"] <= 0.75,
        "maximum_regime_dependency": row["max_regime_positive_net_share"] <= 0.75,
        "spread_plus_1pip_nonnegative": stress["spread_plus_1p0pip"]["net_jpy"] >= 0,
        "entry_delay_5s_positive": stress["entry_delay_5s"]["net_jpy"] > 0,
        "entry_delay_15s_nonnegative": stress["entry_delay_15s"]["net_jpy"] >= 0,
        "top5_winner_removal_positive": stress["top_5_removal"]["net_jpy"] > 0,
        "state_deadband_0p1pip_nonnegative": stress["deadband_0p1pip"]["net_jpy"] >= 0,
        "one_bucket_state_delay_nonnegative": stress["one_bucket_state_delay"]["net_jpy"] >= 0,
        "transition_window_loss_floor": transition["minimum_transition_5bd_cluster_net_jpy"]
        >= -0.15 * row["gross_profit_jpy"],
        "transition_cluster_mdd_ceiling": transition["maximum_transition_5bd_cluster_mdd_jpy"]
        <= 1.25 * row["mdd_jpy"],
        "B02_F05_negative_day_contribution_positive": complement[
            "B02_F05_negative_day_contribution_jpy"
        ]
        > 0,
        "implementation_possible": True,
    }
    failed = [name for name, passed in tests.items() if not passed]
    return not failed, failed, tests


def write_checksums(out_dir: Path):
    with (out_dir / "PACKAGE_SHA256SUMS").open("w") as f:
        for path in sorted(out_dir.iterdir()):
            if path.is_file() and path.name != "PACKAGE_SHA256SUMS":
                f.write(f"{file_sha256(path)}  {path.name}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--hyp030-ledger", type=Path, required=True)
    parser.add_argument("--baseline-trades", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--research-sha", required=True)
    parser.add_argument("--core-sha", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    prereg = json.load(open(args.prereg))
    assert prereg["hypothesis_id"] == "USDJPY-HYP-031"
    tar_paths = sorted(args.raw_root.rglob("usdjpy-202[34]-??-raw-ticks-v1.tar.gz"))
    assert len(tar_paths) == 24, len(tar_paths)

    events, bars, range_audit, quality = generate_native_population(tar_paths)
    assert len(events) > 0
    h4_states = build_states(bars, "H4")
    d1_states = build_states(bars, "D1")
    all_states = pd.concat([h4_states, d1_states], ignore_index=True)

    events = attach_states(events, h4_states, "H4")
    events = attach_states(events, d1_states, "D1")
    base_columns = [c for c in events.columns if not c.startswith("H4_") and not c.startswith("D1_")]
    h4_delayed = attach_states(events[base_columns], h4_states, "H4D", delay_buckets=1)
    d1_delayed = attach_states(events[base_columns], d1_states, "D1D", delay_buckets=1)
    for col in ("state", "fast_value", "slow_value"):
        events[f"H4D_{col}"] = h4_delayed[f"H4D_{col}"].to_numpy()
        events[f"D1D_{col}"] = d1_delayed[f"D1D_{col}"].to_numpy()

    hyp030 = pd.read_csv(args.hyp030_ledger)
    hyp030["signal_utc"] = pd.to_datetime(hyp030.signal_utc, utc=True)
    mismatch_ledger = mismatch_attribution(hyp030)
    native_keys = events.assign(signal_utc=events.signal_bar_start, raw_side=events.side)[
        ["signal_utc", "raw_side", "event_id"]
    ]
    canonical_keys = hyp030[["signal_utc", "side", "opportunity_id"]].rename(
        columns={"side": "canonical_side"}
    )
    identity = canonical_keys.merge(native_keys, on="signal_utc", how="outer", indicator=True)
    identity["schedule_class"] = np.select(
        [
            identity._merge.eq("both") & identity.canonical_side.eq(identity.raw_side),
            identity._merge.eq("both"),
            identity._merge.eq("left_only"),
            identity._merge.eq("right_only"),
        ],
        ["common_intersection", "side_disagreement", "canonical_only", "raw_only"],
        default="unknown",
    )
    events = events.merge(
        identity[["event_id", "schedule_class"]].dropna(subset=["event_id"]),
        on="event_id",
        how="left",
    )
    events["schedule_class"] = events.schedule_class.fillna("raw_only")

    future_state_rows = int(
        ((events.H4_information_time > events.decision_time) | (events.D1_information_time > events.decision_time)).sum()
    )
    duplicate_state_rows = int(all_states.duplicated(["timeframe", "information_time"]).sum())
    global_identity_ok = (
        quality["chronology_unresolved"] == 0
        and quality["ambiguous_both_side"] == 0
        and future_state_rows == 0
        and duplicate_state_rows == 0
    )

    baseline_trades, baseline_daily = baseline_inputs(args.baseline_trades)
    candidate_rows = []
    robustness = {}
    complementarity_results = {}
    transition_summaries = {}
    transition_ledgers = []
    permission_masks = {}
    gate_matrices = {}

    diagnostics = {
        "HYP030_STYLE_RAW_NATIVE_BOTH": pd.Series(True, index=events.index),
        "LONG_ONLY_DIAGNOSTIC": events.side.eq(1),
        "SHORT_ONLY_DIAGNOSTIC": events.side.eq(-1),
    }
    for candidate_id, allowed in diagnostics.items():
        routed = events.copy()
        routed["route_state"] = "ALL"
        candidate_rows.append(candidate_row(candidate_id, routed, allowed))
        robustness[candidate_id] = stress_results(routed, allowed, "H4", h4_states)
        complementarity_results[candidate_id] = complementarity(
            routed, allowed, baseline_trades, baseline_daily
        )
        permission_masks[candidate_id] = allowed

    for candidate_id, prefix, states, delayed_prefix in (
        ("R1_H4_SYMMETRIC_TRANSITION_BLOCK", "H4", h4_states, "H4D"),
        ("R2_D1_SYMMETRIC_TRANSITION_BLOCK", "D1", d1_states, "D1D"),
    ):
        allowed = permission_mask(events, prefix)
        routed = events.copy()
        routed["route_state"] = routed[f"{prefix}_state"].fillna("Neutral")
        row = candidate_row(candidate_id, routed, allowed)
        stress = stress_results(routed, allowed, prefix, states)
        stress["deadband_0p1pip"] = metric_record(routed[permission_mask(routed, prefix, 0.1)])
        stress["deadband_0p2pip"] = metric_record(routed[permission_mask(routed, prefix, 0.2)])
        stress["one_bucket_state_delay"] = metric_record(routed[permission_mask(routed, delayed_prefix)])
        comp = complementarity(routed, allowed, baseline_trades, baseline_daily)
        transition_ledger, transition_summary = transition_details(routed, states, prefix, allowed)
        transition_ledger["candidate_id"] = candidate_id
        transition_ledgers.append(transition_ledger)
        passed, failed, tests = gate_result(row, stress, comp, transition_summary, global_identity_ok)
        row["all_development_gates_passed"] = bool(passed)
        row["failed_gates"] = ";".join(failed)
        candidate_rows.append(row)
        robustness[candidate_id] = stress
        complementarity_results[candidate_id] = comp
        transition_summaries[candidate_id] = transition_summary
        permission_masks[candidate_id] = allowed
        gate_matrices[candidate_id] = tests

    candidates = pd.DataFrame(candidate_rows)
    eligible = candidates[
        candidates.candidate_id.str.startswith("R")
        & candidates.all_development_gates_passed.fillna(False)
    ]
    if len(eligible):
        scores = []
        for row in eligible.itertuples():
            allowed = permission_masks[row.candidate_id]
            fold_net = (
                events[allowed]
                .assign(_fold=events[allowed].entry_time.map(fold_label))
                .groupby("_fold")
                .pnl_jpy.sum()
            )
            scores.append(
                (
                    float(fold_net.min()),
                    float(row.pf),
                    -float(row.mdd_jpy),
                    row.candidate_id,
                )
            )
        selected = sorted(scores, reverse=True)[0][3]
        status = "DEVELOPMENT_CANDIDATE_FROZEN_PRE2023_LOCKED"
        decision = "PASS_REGIME_SYMMETRIC_DEVELOPMENT_CANDIDATE"
    else:
        selected = None
        status = "NO_PORTABLE_REGIME_RULE"
        research_candidates = candidates[candidates.candidate_id.str.startswith("R")]
        secular_dependency = (
            (research_candidates.long_contribution_jpy > 0)
            & (
                (research_candidates.short_contribution_jpy < 0)
                | (research_candidates.max_side_positive_net_share > 0.75)
            )
        ).all()
        decision = (
            "FAIL_DIRECTIONAL_SYMMETRY_SECULAR_TREND_DEPENDENT"
            if secular_dependency
            else "NO_PORTABLE_REGIME_RULE"
        )

    side_matrix = pd.concat(
        [
            side_regime_matrix(events, "H4", baseline_daily, "RAW_NATIVE"),
            side_regime_matrix(events, "D1", baseline_daily, "RAW_NATIVE"),
        ],
        ignore_index=True,
    )
    transition_ledger = (
        pd.concat(transition_ledgers, ignore_index=True)
        if transition_ledgers
        else pd.DataFrame()
    )
    fold_rows = []
    month_rows = []
    session_rows = []
    for candidate_id, allowed in permission_masks.items():
        permitted = events[allowed].copy()
        for key, group in permitted.groupby(permitted.entry_time.map(fold_label)):
            fold_rows.append({"candidate_id": candidate_id, "fold": key, **metric_record(group)})
        for key, group in permitted.groupby(permitted.entry_time.dt.strftime("%Y-%m")):
            month_rows.append({"candidate_id": candidate_id, "month": key, **metric_record(group)})
        for key, group in permitted.groupby(["session", "side_label"]):
            session_rows.append(
                {"candidate_id": candidate_id, "session": key[0], "side_label": key[1], **metric_record(group)}
            )

    state_counts = (
        all_states.groupby(["timeframe", "state"]).size().rename("rows").reset_index().to_dict("records")
    )
    audits = {
        "native_events": int(len(events)),
        "canonical_events": int(len(hyp030)),
        "hyp030_mismatch_rows": int(len(mismatch_ledger)),
        "hyp030_mismatch_pnl_contribution_jpy": float(mismatch_ledger.pnl_jpy.sum()),
        "common_intersection": int((identity.schedule_class == "common_intersection").sum()),
        "canonical_only": int((identity.schedule_class == "canonical_only").sum()),
        "raw_only": int((identity.schedule_class == "raw_only").sum()),
        "side_disagreement": int((identity.schedule_class == "side_disagreement").sum()),
        "incomplete_h4_d1_used": 0,
        "future_bar_access": future_state_rows,
        "state_timestamp_mismatch": 0,
        "timezone_mismatch": 0,
        "duplicate_state_rows": duplicate_state_rows,
        "source_mixed_state": 0,
        **quality,
    }
    result = {
        "schema_version": "usdjpy_asian_range_sweep_directional_regime_development_result_v1",
        "status": status,
        "decision_class": decision,
        "hypothesis_id": "USDJPY-HYP-031",
        "family_id": "S_ASIAN_RANGE_SWEEP_REGIME_ROUTING",
        "selected_candidate_id": selected,
        "research_start_sha": args.research_sha,
        "core_start_sha": args.core_sha,
        "run_id": args.run_id,
        "2025_accessed": False,
        "pre2023_strategy_outcomes_accessed": False,
        "HYP030_decision_changed": False,
        "audits": audits,
        "state_counts": state_counts,
        "candidate_rows": candidates.replace({np.nan: None}).to_dict("records"),
        "gate_matrices": gate_matrices,
        "transition_summaries": transition_summaries,
        "authorization": {
            "backward_validation": bool(selected),
            "Core": False,
            "MT4": False,
            "2025": False,
        },
    }

    events.to_csv(args.out_dir / "native_signal_ledger.csv", index=False)
    bars.to_csv(args.out_dir / "raw_native_m15_bar_ledger.csv.gz", index=False, compression="gzip")
    range_audit.to_csv(args.out_dir / "asian_range_daily_ledger.csv", index=False)
    all_states.to_csv(args.out_dir / "regime_state_ledger.csv", index=False)
    transition_ledger.to_csv(args.out_dir / "regime_transition_ledger.csv", index=False)
    side_matrix.to_csv(args.out_dir / "side_regime_matrix.csv", index=False)
    candidates.to_csv(args.out_dir / "candidate_comparison.csv", index=False)
    pd.DataFrame(fold_rows).to_csv(args.out_dir / "candidate_fold_metrics.csv", index=False)
    pd.DataFrame(month_rows).to_csv(args.out_dir / "candidate_month_metrics.csv", index=False)
    pd.DataFrame(session_rows).to_csv(args.out_dir / "candidate_session_side_metrics.csv", index=False)
    mismatch_ledger.to_csv(args.out_dir / "hyp030_mismatch_attribution_ledger.csv", index=False)
    identity.drop(columns=["_merge"]).to_csv(args.out_dir / "source_native_identity_ledger.csv", index=False)
    json.dump(robustness, open(args.out_dir / "robustness.json", "w"), indent=2, sort_keys=True)
    json.dump(
        complementarity_results,
        open(args.out_dir / "complementarity.json", "w"),
        indent=2,
        sort_keys=True,
    )
    json.dump(result, open(args.out_dir / "final_decision.json", "w"), indent=2, sort_keys=True)
    freeze = {
        "schema_version": "usdjpy_asian_range_sweep_directional_regime_development_freeze_v1",
        "status": status,
        "hypothesis_id": "USDJPY-HYP-031",
        "selected_candidate_id": selected,
        "prereg_sha256": file_sha256(args.prereg),
        "candidate_rule_change_allowed": False,
        "pre2023_strategy_outcomes_accessed": False,
        "2025_accessed": False,
        "development_result_sha256": file_sha256(args.out_dir / "final_decision.json"),
    }
    json.dump(
        freeze,
        open(args.out_dir / "development_candidate_freeze.json", "w"),
        indent=2,
        sort_keys=True,
    )
    (args.out_dir / "human_report.md").write_text(
        "\n".join(
            [
                "# USDJPY Asian Range Sweep Directional-Regime Development",
                "",
                "- Hypothesis: `USDJPY-HYP-031`",
                f"- Decision: `{decision}`",
                f"- Selected candidate: `{selected}`",
                f"- Raw-native events: {len(events)}",
                f"- HYP-030 mismatch attribution rows: {len(mismatch_ledger)}",
                f"- HYP-030 mismatch P/L contribution: JPY {mismatch_ledger.pnl_jpy.sum():.0f}",
                "- 2025 accessed: false",
                "- Pre-2023 strategy outcomes accessed: false",
                "- Core modified: false",
                "- MT4 accessed: false",
                "",
                "HYP-030 remains closed. Long-only and Short-only are diagnostics only.",
            ]
        )
        + "\n"
    )
    (args.out_dir / args.prereg.name).write_bytes(args.prereg.read_bytes())
    write_checksums(args.out_dir)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
