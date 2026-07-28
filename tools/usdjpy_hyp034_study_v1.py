#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usdjpy_hyp034_bi5_source_v1 import iter_tick_days, m15_bars, source_inventory, tick_day_audit

PIP = 0.01
JPY_PER_PRICE_UNIT = 1000.0
BAR_HOLD = 12
FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]


def fold_of(timestamp: pd.Timestamp) -> str | None:
    timestamp = pd.Timestamp(timestamp).tz_convert("UTC")
    year = timestamp.year
    if year not in (2023, 2024):
        return None
    return f"{year}H{1 if timestamp.month <= 6 else 2}"


def session_of(timestamp: pd.Timestamp) -> str:
    hour = pd.Timestamp(timestamp).hour
    if hour < 7:
        return "ASIA"
    if hour < 13:
        return "LONDON"
    if hour < 20:
        return "NEW_YORK"
    return "LATE"


def signed_minutes_to(timestamp: pd.Timestamp, hour: int) -> float:
    target = pd.Timestamp(timestamp).normalize() + pd.Timedelta(hours=hour)
    return float((target - pd.Timestamp(timestamp)).total_seconds() / 60.0)


def safe_summary_status(text: str | None) -> str:
    if not text:
        return "MISSING"
    try:
        payload = json.loads(text)
    except Exception:
        return "PARSE_ERROR"
    if "parse_error" in payload:
        return "PARSE_ERROR"
    for key in ("status", "result", "download_status", "state"):
        if key in payload:
            return str(payload[key])
    return "PRESENT"


def build_source_tables(raw_dirs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    daily_rows: list[dict[str, Any]] = []
    bar_frames: list[pd.DataFrame] = []
    for day in iter_tick_days(raw_dirs):
        audit = tick_day_audit(day)
        if not day.empty:
            high_index = int(np.argmax(day.bid))
            low_index = int(np.argmin(day.bid))
            audit["bid_high_formation_utc"] = pd.Timestamp(int(day.timestamp_ns[high_index]), tz="UTC").isoformat()
            audit["bid_low_formation_utc"] = pd.Timestamp(int(day.timestamp_ns[low_index]), tz="UTC").isoformat()
        else:
            audit["bid_high_formation_utc"] = None
            audit["bid_low_formation_utc"] = None
        audit["weekday"] = int(pd.Timestamp(day.date_utc).weekday())
        audit["summary_status"] = safe_summary_status(audit.get("day_summary_json"))
        daily_rows.append(audit)
        bars = m15_bars(day)
        if not bars.empty:
            bars["date_utc"] = day.date_utc
            bars["source_archive"] = day.source_archive
            bars["source_archive_sha256"] = day.source_archive_sha256
            bar_frames.append(bars)
    daily = pd.DataFrame(daily_rows).sort_values("date_utc", kind="mergesort").reset_index(drop=True)
    bars = pd.concat(bar_frames, ignore_index=True).sort_values("bar_start_utc", kind="mergesort").reset_index(drop=True)
    bars["bar_index"] = np.arange(len(bars), dtype=int)
    bars["bar_end_utc"] = bars["bar_start_utc"] + pd.Timedelta(minutes=15)
    bars["fold"] = bars["bar_start_utc"].map(fold_of)
    bars["month"] = bars["bar_start_utc"].dt.strftime("%Y-%m")
    bars["session"] = bars["bar_start_utc"].map(session_of)
    inventory = source_inventory(raw_dirs)
    return daily, bars, inventory


def previous_trading_day_map(daily: pd.DataFrame) -> tuple[dict[str, str], list[str], list[str]]:
    eligible = daily[(daily.weekday < 5) & (daily.tick_count > 0) & ~daily.summary_status.eq("PARSE_ERROR")].date_utc.tolist()
    mapping: dict[str, str] = {}
    previous: str | None = None
    warmup_unavailable: list[str] = []
    for current in eligible:
        if previous is None:
            warmup_unavailable.append(current)
        else:
            mapping[current] = previous
        previous = current
    no_tick_weekdays = daily[(daily.weekday < 5) & (daily.tick_count == 0)].date_utc.tolist()
    return mapping, warmup_unavailable, no_tick_weekdays


def range_percentiles(daily: pd.DataFrame) -> dict[str, float]:
    work = daily[(daily.weekday < 5) & (daily.tick_count > 0)].copy()
    work["range"] = work.bid_high - work.bid_low
    result: dict[str, float] = {}
    values: list[float] = []
    for row in work.itertuples(index=False):
        current = float(row.range)
        history = values[-60:]
        if history:
            result[row.date_utc] = float(np.mean(np.asarray(history) <= current))
        else:
            result[row.date_utc] = np.nan
        values.append(current)
    return result


def add_bar_features(bars: pd.DataFrame) -> pd.DataFrame:
    bars = bars.copy()
    close = bars.bid_close.astype(float)
    bar_range = bars.bid_high.astype(float) - bars.bid_low.astype(float)
    bars["completed_m15_return_pips"] = (close.shift(1) - close.shift(2)) / PIP
    bars["completed_h1_return_pips"] = (close.shift(1) - close.shift(5)) / PIP
    bars["completed_h4_return_pips"] = (close.shift(1) - close.shift(17)) / PIP
    bars["completed_bar_volatility_pips"] = bar_range.shift(1).rolling(20, min_periods=8).mean() / PIP
    bars["recent_local_excursion_pips"] = (
        bars.bid_high.shift(1).rolling(8, min_periods=4).max() - bars.bid_low.shift(1).rolling(8, min_periods=4).min()
    ) / PIP
    recent = bar_range.shift(1).rolling(4, min_periods=4).mean()
    prior = bar_range.shift(5).rolling(16, min_periods=8).mean()
    bars["recent_compression_expansion_ratio"] = recent / prior.replace(0, np.nan)
    bars["tick_velocity_per_second"] = bars.tick_count.astype(float) / 900.0
    return bars


def directional_raw_trade(bars: pd.DataFrame, entry_index: int, exit_index: int, side: int) -> tuple[float, float, float]:
    entry = bars.iloc[entry_index]
    exit_row = bars.iloc[exit_index]
    if side == 1:
        entry_price = float(entry.ask_open)
        exit_price = float(exit_row.bid_open)
        pl = (exit_price - entry_price) * JPY_PER_PRICE_UNIT
    else:
        entry_price = float(entry.bid_open)
        exit_price = float(exit_row.ask_open)
        pl = (entry_price - exit_price) * JPY_PER_PRICE_UNIT
    return entry_price, exit_price, float(pl)


def build_events_and_trades(daily: pd.DataFrame, bars: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    bars = add_bar_features(bars)
    day_map = daily.set_index("date_utc").to_dict("index")
    previous_map, warmup_unavailable, no_tick_weekdays = previous_trading_day_map(daily)
    percentile = range_percentiles(daily)
    rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    by_date = {key: group for key, group in bars.groupby("date_utc", sort=True)}
    for current_date, previous_date in previous_map.items():
        if current_date not in by_date:
            continue
        previous = day_map[previous_date]
        current = day_map[current_date]
        pd_high = float(previous["bid_high"])
        pd_low = float(previous["bid_low"])
        pd_range = pd_high - pd_low
        if not np.isfinite(pd_range) or pd_range <= 0:
            continue
        group = by_date[current_date]
        side_specs = [
            ("HIGH", -1, group.index[group.bid_high.astype(float) > pd_high].tolist()),
            ("LOW", 1, group.index[group.bid_low.astype(float) < pd_low].tolist()),
        ]
        both_side = bool(side_specs[0][2] and side_specs[1][2])
        for sweep_side, side, sweep_indexes in side_specs:
            if not sweep_indexes:
                continue
            first_sweep_index = int(sweep_indexes[0])
            if side == -1:
                signal_indexes = group.index[(group.index >= first_sweep_index) & (group.bid_high.astype(float) > pd_high) & (group.bid_close.astype(float) < pd_high)].tolist()
            else:
                signal_indexes = group.index[(group.index >= first_sweep_index) & (group.bid_low.astype(float) < pd_low) & (group.bid_close.astype(float) > pd_low)].tolist()
            signal_index = int(signal_indexes[0]) if signal_indexes else None
            sweep_bar = bars.loc[first_sweep_index]
            decision = bars.loc[signal_index].bar_end_utc if signal_index is not None else pd.NaT
            decision_row = bars.loc[signal_index] if signal_index is not None else sweep_bar
            entry_index = signal_index + 1 if signal_index is not None else None
            exit_index = entry_index + BAR_HOLD if entry_index is not None else None
            candidate_resolved = bool(exit_index is not None and exit_index < len(bars))
            if candidate_resolved:
                entry_row = bars.loc[entry_index]
                exit_row = bars.loc[exit_index]
                candidate_resolved = fold_of(entry_row.bar_start_utc) == fold_of(exit_row.bar_start_utc) == fold_of(decision_row.bar_start_utc)
            raw_entry_index = first_sweep_index + 1
            raw_exit_index = raw_entry_index + BAR_HOLD
            raw_resolved = raw_exit_index < len(bars)
            raw_entry_price = raw_exit_price = raw_pl = np.nan
            if raw_resolved:
                raw_entry_price, raw_exit_price, raw_pl = directional_raw_trade(bars, raw_entry_index, raw_exit_index, side)
            overshoot = (float(decision_row.bid_high) - pd_high) if side == -1 else (pd_low - float(decision_row.bid_low))
            reclaim_depth = (pd_high - float(decision_row.bid_close)) if side == -1 else (float(decision_row.bid_close) - pd_low)
            current_open = float(current["bid_open"])
            boundary = pd_high if side == -1 else pd_low
            feature = {
                "previous_day_range_pips": pd_range / PIP,
                "current_day_open_location": (current_open - pd_low) / pd_range,
                "distance_open_to_boundary_pips": abs(current_open - boundary) / PIP,
                "overshoot_ratio": max(0.0, overshoot / pd_range),
                "reclaim_depth_ratio": reclaim_depth / pd_range if signal_index is not None else np.nan,
                "current_day_range_to_decision_pips": (float(decision_row.bid_high) - float(decision_row.bid_low)) / PIP,
                "distance_from_daily_open_pips": (float(decision_row.bid_close) - current_open) / PIP,
                "previous_day_direction_pips": (float(previous["bid_close"]) - float(previous["bid_open"])) / PIP,
                "previous_day_range_percentile": percentile.get(previous_date, np.nan),
                "completed_m15_return_pips": float(decision_row.completed_m15_return_pips) if pd.notna(decision_row.completed_m15_return_pips) else np.nan,
                "completed_h1_return_pips": float(decision_row.completed_h1_return_pips) if pd.notna(decision_row.completed_h1_return_pips) else np.nan,
                "completed_h4_return_pips": float(decision_row.completed_h4_return_pips) if pd.notna(decision_row.completed_h4_return_pips) else np.nan,
                "completed_bar_volatility_pips": float(decision_row.completed_bar_volatility_pips) if pd.notna(decision_row.completed_bar_volatility_pips) else np.nan,
                "tick_velocity_per_second": float(decision_row.tick_velocity_per_second),
                "spread_at_decision_pips": float(decision_row.spread_close_pips),
                "recent_local_excursion_pips": float(decision_row.recent_local_excursion_pips) if pd.notna(decision_row.recent_local_excursion_pips) else np.nan,
                "recent_compression_expansion_ratio": float(decision_row.recent_compression_expansion_ratio) if pd.notna(decision_row.recent_compression_expansion_ratio) else np.nan,
            }
            prior_group = group[group.index < first_sweep_index]
            if side == -1:
                touch_count = int((prior_group.bid_high.astype(float) > pd_high).sum())
                opposite_touch = bool((prior_group.bid_low.astype(float) < pd_low).any())
                formation = previous.get("bid_high_formation_utc")
            else:
                touch_count = int((prior_group.bid_low.astype(float) < pd_low).sum())
                opposite_touch = bool((prior_group.bid_high.astype(float) > pd_high).any())
                formation = previous.get("bid_low_formation_utc")
            feature["same_boundary_touch_count"] = touch_count
            feature["opposite_boundary_touch_flag"] = opposite_touch
            event_key = f"{current_date}|{sweep_side}"
            row = {
                "event_key": event_key,
                "event_id": event_key,
                "previous_trading_date": previous_date,
                "current_trading_date": current_date,
                "previous_day_high_bid": pd_high,
                "previous_day_low_bid": pd_low,
                "sweep_side": sweep_side,
                "side": side,
                "sweep_bar_start_utc": sweep_bar.bar_start_utc,
                "sweep_timestamp": pd.NaT,
                "first_boundary_cross_timestamp": pd.NaT,
                "reclaim_timestamp": pd.NaT,
                "entry_decision_timestamp": decision,
                "first_executable_timestamp": bars.loc[entry_index].first_tick_utc if candidate_resolved else pd.NaT,
                "fixed_exit_timestamp": bars.loc[exit_index].first_tick_utc if candidate_resolved else pd.NaT,
                "source_sha": str(current["source_archive_sha256"]),
                "fold": fold_of(decision_row.bar_start_utc),
                "timezone_contract": "UTC terminal BI5 member suffix; no DST conversion",
                "candidate_signal": signal_index is not None,
                "candidate_chronology_resolved": candidate_resolved,
                "candidate_permission": False,
                "candidate_block_reason": "PENDING_ACTIVE_SUPPRESSION" if candidate_resolved else "NO_COMPLETED_M15_RECLAIM_OR_FOLD_EXIT",
                "both_side_sweep": both_side,
                "same_day_repeated_sweep_count": max(0, len(sweep_indexes) - 1),
                "raw_diagnostic_entry_price": raw_entry_price,
                "raw_diagnostic_exit_price": raw_exit_price,
                "raw_diagnostic_pl_jpy": raw_pl,
                "raw_diagnostic_resolved": raw_resolved,
                "sweep_utc": sweep_bar.bar_start_utc,
                "session": session_of(decision_row.bar_start_utc),
                "minutes_to_london_open": signed_minutes_to(decision_row.bar_start_utc, 7),
                "minutes_to_ny_open": signed_minutes_to(decision_row.bar_start_utc, 13),
                "minutes_from_rollover": float((decision_row.bar_start_utc - decision_row.bar_start_utc.normalize()).total_seconds() / 60),
                "previous_day_boundary_formation_utc": formation,
                "boundary_age_minutes": float((decision_row.bar_start_utc - pd.Timestamp(formation)).total_seconds() / 60) if formation else np.nan,
                "outside_duration_seconds": np.nan,
                "first_reclaim_distance_pips": np.nan,
                "reclaim_speed_pips_per_minute": np.nan,
                "reclaim_retained_duration_seconds": np.nan,
                "boundary_retest_count": np.nan,
                "second_sweep": len(sweep_indexes) > 1,
                "opposite_boundary_reached": False,
                "path_class": "UNRESOLVED",
                **feature,
            }
            rows.append(row)
            if candidate_resolved:
                entry_price, exit_price, pl_jpy = directional_raw_trade(bars, entry_index, exit_index, side)
                trade_rows.append({
                    "event_key": event_key,
                    "event_id": event_key,
                    "fold": row["fold"],
                    "session": row["session"],
                    "side": side,
                    "sweep_side": sweep_side,
                    "entry_decision_utc": decision,
                    "entry_utc": bars.loc[entry_index].first_tick_utc,
                    "exit_utc": bars.loc[exit_index].first_tick_utc,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pl_jpy": pl_jpy,
                    "entry_date": pd.Timestamp(bars.loc[entry_index].first_tick_utc).strftime("%Y-%m-%d"),
                    "exit_date": pd.Timestamp(bars.loc[exit_index].first_tick_utc).strftime("%Y-%m-%d"),
                    "month": pd.Timestamp(bars.loc[entry_index].first_tick_utc).strftime("%Y-%m"),
                    **feature,
                })
    events = pd.DataFrame(rows).sort_values(["sweep_bar_start_utc", "sweep_side"], kind="mergesort").reset_index(drop=True)
    trades = pd.DataFrame(trade_rows).sort_values(["entry_utc", "event_key"], kind="mergesort").reset_index(drop=True)
    active_until = pd.Timestamp.min.tz_localize("UTC")
    permitted: set[str] = set()
    for row in trades.itertuples(index=False):
        if pd.Timestamp(row.entry_utc) < active_until:
            continue
        permitted.add(row.event_key)
        active_until = pd.Timestamp(row.exit_utc)
    events.loc[events.event_key.isin(permitted), "candidate_permission"] = True
    events.loc[events.event_key.isin(permitted), "candidate_block_reason"] = "PERMITTED"
    events.loc[events.candidate_chronology_resolved & ~events.event_key.isin(permitted), "candidate_block_reason"] = "ACTIVE_POSITION"
    trades = trades[trades.event_key.isin(permitted)].copy().reset_index(drop=True)
    metadata = {
        "previous_day_map_count": len(previous_map),
        "warmup_unavailable_dates": warmup_unavailable,
        "verified_no_tick_weekdays": no_tick_weekdays,
        "raw_event_count": int(len(events)),
        "candidate_signal_count_before_active_suppression": int(events.candidate_chronology_resolved.sum()),
        "candidate_trade_count_after_active_suppression": int(len(trades)),
    }
    return events, trades, metadata


def classify_trade(row: pd.Series) -> str:
    if not np.isfinite(float(row.get("mfe_pips", np.nan))) or not np.isfinite(float(row.get("mae_pips", np.nan))):
        return "unresolved_chronology"
    mfe = float(row.mfe_pips)
    mae = float(row.mae_pips)
    pl = float(row.pl_jpy)
    time_mfe = float(row.time_to_mfe_seconds) if pd.notna(row.time_to_mfe_seconds) else np.inf
    outside_share = float(row.outside_tick_share) if pd.notna(row.outside_tick_share) else 0.0
    redeparture = bool(row.boundary_outside_redeparture)
    if outside_share >= 0.70 and pl < 0:
        return "outside_acceptance"
    if pl < 0 and redeparture:
        return "false_reclaim_then_continuation"
    if mfe >= 5 and time_mfe <= 15 * 60:
        return "immediate_rejection"
    if mfe >= 5 and time_mfe > 15 * 60:
        return "delayed_rejection"
    if redeparture and pl > 0:
        return "boundary_retest_then_rejection"
    if pl > 0 and outside_share <= 0.25:
        return "sustained_range_reentry"
    if mfe < 5 and mae <= -5 and pl < 0:
        return "immediate_continuation"
    return "shallow_reclaim"


def enrich_exact_paths(raw_dirs: list[Path], events: pd.DataFrame, trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    events = events.copy()
    trades = trades.copy()
    event_index = {row.event_key: index for index, row in events.iterrows()}
    trade_index = {row.event_key: index for index, row in trades.iterrows()}
    accum: dict[str, dict[str, Any]] = {}
    for row in trades.itertuples(index=False):
        accum[row.event_key] = {
            "mae_pips": np.inf,
            "mfe_pips": -np.inf,
            "time_to_mae_seconds": np.nan,
            "time_to_mfe_seconds": np.nan,
            "pl_delay_5s_jpy": np.nan,
            "pl_delay_10s_jpy": np.nan,
            "return_5m_pips": np.nan,
            "return_15m_pips": np.nan,
            "return_30m_pips": np.nan,
            "return_60m_pips": np.nan,
            "return_120m_pips": np.nan,
            "return_180m_pips": np.nan,
            "previous_day_midpoint_reached": False,
            "opposite_boundary_reached": False,
            "boundary_outside_redeparture": False,
            "outside_ticks": 0,
            "path_ticks": 0,
            "first_tp5_utc": pd.NaT,
            "first_sl5_utc": pd.NaT,
            "entry_price_tick_verified": False,
            "exit_price_tick_verified": False,
        }
    mismatch_rows: list[dict[str, Any]] = []
    events_by_date = {key: group.index.tolist() for key, group in events.groupby("current_trading_date", sort=False)}
    for day in iter_tick_days(raw_dirs):
        if day.empty:
            continue
        timestamps = day.timestamp_ns
        first_ns = int(timestamps[0])
        last_ns = int(timestamps[-1])
        for event_row_index in events_by_date.get(day.date_utc, []):
            event = events.loc[event_row_index]
            high = float(event.previous_day_high_bid)
            low = float(event.previous_day_low_bid)
            if event.sweep_side == "HIGH":
                cross = np.flatnonzero(day.bid > high)
            else:
                cross = np.flatnonzero(day.bid < low)
            if not len(cross):
                mismatch_rows.append({"event_key": event.event_key, "mismatch": "FIRST_BOUNDARY_CROSS_NOT_FOUND", "detail": day.date_utc})
                continue
            first_cross = int(cross[0])
            cross_ns = int(timestamps[first_cross])
            if event.sweep_side == "HIGH":
                reclaim = np.flatnonzero((np.arange(len(day.bid)) > first_cross) & (day.bid < high))
            else:
                reclaim = np.flatnonzero((np.arange(len(day.bid)) > first_cross) & (day.bid > low))
            reclaim_index = int(reclaim[0]) if len(reclaim) else None
            reclaim_ns = int(timestamps[reclaim_index]) if reclaim_index is not None else None
            decision_ns = int(pd.Timestamp(event.entry_decision_timestamp).value) if pd.notna(event.entry_decision_timestamp) else last_ns
            cutoff = int(np.searchsorted(timestamps, decision_ns, side="right"))
            segment = day.bid[first_cross:max(first_cross + 1, cutoff)]
            if event.sweep_side == "HIGH":
                overshoot = float(np.max(segment) - high)
                transitions = np.diff((segment > high).astype(np.int8))
                first_reclaim_distance = high - float(day.bid[reclaim_index]) if reclaim_index is not None else np.nan
            else:
                overshoot = float(low - np.min(segment))
                transitions = np.diff((segment < low).astype(np.int8))
                first_reclaim_distance = float(day.bid[reclaim_index]) - low if reclaim_index is not None else np.nan
            retests = int(np.sum(transitions == 1))
            events.at[event_row_index, "first_boundary_cross_timestamp"] = pd.Timestamp(cross_ns, tz="UTC")
            events.at[event_row_index, "sweep_timestamp"] = pd.Timestamp(cross_ns, tz="UTC")
            events.at[event_row_index, "reclaim_timestamp"] = pd.Timestamp(reclaim_ns, tz="UTC") if reclaim_ns is not None else pd.NaT
            events.at[event_row_index, "outside_duration_seconds"] = float(((reclaim_ns if reclaim_ns is not None else decision_ns) - cross_ns) / 1_000_000_000)
            events.at[event_row_index, "first_reclaim_distance_pips"] = float(first_reclaim_distance / PIP) if np.isfinite(first_reclaim_distance) else np.nan
            duration_minutes = max(float(events.at[event_row_index, "outside_duration_seconds"]) / 60.0, 1e-9)
            events.at[event_row_index, "reclaim_speed_pips_per_minute"] = float((overshoot / PIP) / duration_minutes)
            events.at[event_row_index, "boundary_retest_count"] = retests
            events.at[event_row_index, "event_id"] = f"HYP034|{event.current_trading_date}|{event.sweep_side}|{pd.Timestamp(cross_ns, tz='UTC').isoformat()}"
            if pd.notna(event.entry_decision_timestamp) and reclaim_ns is not None and reclaim_ns > decision_ns:
                mismatch_rows.append({"event_key": event.event_key, "mismatch": "RECLAIM_AFTER_DECISION", "detail": pd.Timestamp(reclaim_ns, tz="UTC").isoformat()})
        for event_key, state in accum.items():
            trade = trades.loc[trade_index[event_key]]
            entry_ns = int(pd.Timestamp(trade.entry_utc).value)
            exit_ns = int(pd.Timestamp(trade.exit_utc).value)
            max_ns = max(exit_ns, entry_ns + 180 * 60 * 1_000_000_000)
            if max_ns < first_ns or entry_ns > last_ns:
                continue
            start = int(np.searchsorted(timestamps, entry_ns, side="left"))
            end = int(np.searchsorted(timestamps, max_ns, side="right"))
            if start >= end:
                continue
            local_ts = timestamps[start:end]
            local_bid = day.bid[start:end]
            local_ask = day.ask[start:end]
            path_end = int(np.searchsorted(local_ts, exit_ns, side="right"))
            if path_end > 0:
                path_ts = local_ts[:path_end]
                if int(trade.side) == 1:
                    executable = (local_bid[:path_end] - float(trade.entry_price)) / PIP
                else:
                    executable = (float(trade.entry_price) - local_ask[:path_end]) / PIP
                if len(executable):
                    minimum_index = int(np.argmin(executable))
                    maximum_index = int(np.argmax(executable))
                    if float(executable[minimum_index]) < state["mae_pips"]:
                        state["mae_pips"] = float(executable[minimum_index])
                        state["time_to_mae_seconds"] = float((int(path_ts[minimum_index]) - entry_ns) / 1_000_000_000)
                    if float(executable[maximum_index]) > state["mfe_pips"]:
                        state["mfe_pips"] = float(executable[maximum_index])
                        state["time_to_mfe_seconds"] = float((int(path_ts[maximum_index]) - entry_ns) / 1_000_000_000)
                    if pd.isna(state["first_tp5_utc"]):
                        hits = np.flatnonzero(executable >= 5)
                        if len(hits): state["first_tp5_utc"] = pd.Timestamp(int(path_ts[int(hits[0])]), tz="UTC")
                    if pd.isna(state["first_sl5_utc"]):
                        hits = np.flatnonzero(executable <= -5)
                        if len(hits): state["first_sl5_utc"] = pd.Timestamp(int(path_ts[int(hits[0])]), tz="UTC")
                    high = float(events.loc[event_index[event_key], "previous_day_high_bid"])
                    low = float(events.loc[event_index[event_key], "previous_day_low_bid"])
                    midpoint = (high + low) / 2
                    if int(trade.side) == 1:
                        outside = local_bid[:path_end] < low
                        state["previous_day_midpoint_reached"] |= bool(np.any(local_bid[:path_end] >= midpoint))
                        state["opposite_boundary_reached"] |= bool(np.any(local_bid[:path_end] >= high))
                    else:
                        outside = local_bid[:path_end] > high
                        state["previous_day_midpoint_reached"] |= bool(np.any(local_bid[:path_end] <= midpoint))
                        state["opposite_boundary_reached"] |= bool(np.any(local_bid[:path_end] <= low))
                    state["outside_ticks"] += int(np.sum(outside))
                    state["path_ticks"] += int(len(outside))
                    if len(outside) > 1 and np.any(np.diff(outside.astype(np.int8)) == 1):
                        state["boundary_outside_redeparture"] = True
            for delay, name in ((5, "pl_delay_5s_jpy"), (10, "pl_delay_10s_jpy")):
                if pd.isna(state[name]):
                    target = entry_ns + delay * 1_000_000_000
                    position = int(np.searchsorted(local_ts, target, side="left"))
                    if position < len(local_ts):
                        delayed_entry = float(local_ask[position]) if int(trade.side) == 1 else float(local_bid[position])
                        if int(trade.side) == 1:
                            state[name] = (float(trade.exit_price) - delayed_entry) * JPY_PER_PRICE_UNIT
                        else:
                            state[name] = (delayed_entry - float(trade.exit_price)) * JPY_PER_PRICE_UNIT
            for minutes in (5, 15, 30, 60, 120, 180):
                name = f"return_{minutes}m_pips"
                if pd.isna(state[name]):
                    target = entry_ns + minutes * 60 * 1_000_000_000
                    position = int(np.searchsorted(local_ts, target, side="left"))
                    if position < len(local_ts):
                        if int(trade.side) == 1:
                            state[name] = (float(local_bid[position]) - float(trade.entry_price)) / PIP
                        else:
                            state[name] = (float(trade.entry_price) - float(local_ask[position])) / PIP
            entry_position = int(np.searchsorted(timestamps, entry_ns, side="left"))
            if entry_position < len(timestamps) and int(timestamps[entry_position]) == entry_ns:
                observed = float(day.ask[entry_position]) if int(trade.side) == 1 else float(day.bid[entry_position])
                state["entry_price_tick_verified"] |= abs(observed - float(trade.entry_price)) <= 1e-12
            exit_position = int(np.searchsorted(timestamps, exit_ns, side="left"))
            if exit_position < len(timestamps) and int(timestamps[exit_position]) == exit_ns:
                observed = float(day.bid[exit_position]) if int(trade.side) == 1 else float(day.ask[exit_position])
                state["exit_price_tick_verified"] |= abs(observed - float(trade.exit_price)) <= 1e-12
    for event_key, state in accum.items():
        index = trade_index[event_key]
        for key, value in state.items():
            trades.at[index, key] = value
        trades.at[index, "outside_tick_share"] = float(state["outside_ticks"] / state["path_ticks"]) if state["path_ticks"] else np.nan
        trades.at[index, "tp_sl_5p_order"] = (
            "TP_FIRST" if pd.notna(state["first_tp5_utc"]) and (pd.isna(state["first_sl5_utc"]) or state["first_tp5_utc"] <= state["first_sl5_utc"])
            else "SL_FIRST" if pd.notna(state["first_sl5_utc"]) else "NEITHER"
        )
        if not state["entry_price_tick_verified"]:
            mismatch_rows.append({"event_key": event_key, "mismatch": "ENTRY_TICK_OR_PRICE_MISMATCH", "detail": str(trades.at[index, "entry_utc"])})
        if not state["exit_price_tick_verified"]:
            mismatch_rows.append({"event_key": event_key, "mismatch": "EXIT_TICK_OR_PRICE_MISMATCH", "detail": str(trades.at[index, "exit_utc"])})
        trades.at[index, "path_class"] = classify_trade(trades.loc[index])
        event_row = event_index[event_key]
        events.at[event_row, "path_class"] = trades.at[index, "path_class"]
        events.at[event_row, "opposite_boundary_reached"] = bool(state["opposite_boundary_reached"])
    trade_lookup = trades.set_index("event_key") if not trades.empty else pd.DataFrame()
    for index, event in events.iterrows():
        if event.event_key in trade_index:
            continue
        if pd.isna(event.reclaim_timestamp):
            events.at[index, "path_class"] = "outside_acceptance" if float(event.raw_diagnostic_pl_jpy) <= 0 else "immediate_continuation"
        elif float(event.raw_diagnostic_pl_jpy) > 0:
            events.at[index, "path_class"] = "delayed_rejection"
        else:
            events.at[index, "path_class"] = "false_reclaim_then_continuation"
    duplicate_ids = events.event_id.duplicated(keep=False)
    for event_id in events.loc[duplicate_ids, "event_id"].unique():
        mismatch_rows.append({"event_key": event_id, "mismatch": "DUPLICATE_EVENT_ID", "detail": event_id})
    mismatch = pd.DataFrame(mismatch_rows, columns=["event_key", "mismatch", "detail"])
    return events, trades, mismatch


def _component_path(timestamps: np.ndarray, bid: np.ndarray, ask: np.ndarray, trades: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    n = len(timestamps)
    if n == 0:
        return np.array([], dtype=float), np.array([], dtype=float)
    coef_bid_diff = np.zeros(n + 1, dtype=float)
    coef_ask_diff = np.zeros(n + 1, dtype=float)
    const_diff = np.zeros(n + 1, dtype=float)
    realized_delta = np.zeros(n, dtype=float)
    first_ns, last_ns = int(timestamps[0]), int(timestamps[-1])
    for row in trades.itertuples(index=False):
        entry_ns = int(pd.Timestamp(row.entry_utc).value)
        exit_ns = int(pd.Timestamp(row.exit_utc).value)
        if exit_ns < first_ns or entry_ns > last_ns:
            continue
        start = int(np.searchsorted(timestamps, entry_ns, side="left"))
        end = int(np.searchsorted(timestamps, exit_ns, side="left"))
        if start < n and end > 0 and start < end:
            left, right = max(0, start), min(n, end)
            if int(row.side) == 1:
                coef_bid_diff[left] += JPY_PER_PRICE_UNIT
                coef_bid_diff[right] -= JPY_PER_PRICE_UNIT
                const_diff[left] -= float(row.entry_price) * JPY_PER_PRICE_UNIT
                const_diff[right] += float(row.entry_price) * JPY_PER_PRICE_UNIT
            else:
                coef_ask_diff[left] -= JPY_PER_PRICE_UNIT
                coef_ask_diff[right] += JPY_PER_PRICE_UNIT
                const_diff[left] += float(row.entry_price) * JPY_PER_PRICE_UNIT
                const_diff[right] -= float(row.entry_price) * JPY_PER_PRICE_UNIT
        close_index = int(np.searchsorted(timestamps, exit_ns, side="left"))
        if 0 <= close_index < n and first_ns <= exit_ns <= last_ns:
            realized_delta[close_index] += float(row.pl_jpy)
    floating = np.cumsum(coef_bid_diff[:-1]) * bid + np.cumsum(coef_ask_diff[:-1]) * ask + np.cumsum(const_diff[:-1])
    return floating, realized_delta


def full_equity_replay(raw_dirs: list[Path], baseline: pd.DataFrame, candidates: dict[str, pd.DataFrame], initial_capital: float = 1_000_000.0) -> tuple[dict[str, Any], pd.DataFrame]:
    baseline = baseline.copy()
    trackers: dict[str, dict[str, float]] = {"BASELINE": {"peak": initial_capital, "mdd": 0.0, "minimum": initial_capital}}
    for candidate_id in candidates:
        trackers[candidate_id] = {"peak": initial_capital, "mdd": 0.0, "minimum": initial_capital}
    daily_rows: list[dict[str, Any]] = []
    for day in iter_tick_days(raw_dirs):
        if day.empty:
            continue
        timestamps, bid, ask = day.timestamp_ns, day.bid, day.ask
        first_ns = int(timestamps[0])
        baseline_before = float(baseline.loc[baseline.exit_utc.map(lambda value: int(pd.Timestamp(value).value)) < first_ns, "pl_jpy"].sum())
        base_floating, base_delta = _component_path(timestamps, bid, ask, baseline)
        base_equity = initial_capital + baseline_before + np.cumsum(base_delta) + base_floating
        base_tracker = trackers["BASELINE"]
        combined_peak = np.maximum.accumulate(np.r_[base_tracker["peak"], base_equity])[1:]
        base_tracker["mdd"] = max(base_tracker["mdd"], float(np.max(combined_peak - base_equity)))
        base_tracker["peak"] = max(base_tracker["peak"], float(np.max(base_equity)))
        base_tracker["minimum"] = min(base_tracker["minimum"], float(np.min(base_equity)))
        daily_rows.append({"date_utc": day.date_utc, "candidate_id": "BASELINE", "minimum_equity_jpy": float(np.min(base_equity)), "maximum_drawdown_jpy_to_date": base_tracker["mdd"]})
        for candidate_id, candidate in candidates.items():
            candidate_before = float(candidate.loc[candidate.exit_utc.map(lambda value: int(pd.Timestamp(value).value)) < first_ns, "pl_jpy"].sum())
            candidate_floating, candidate_delta = _component_path(timestamps, bid, ask, candidate)
            equity = initial_capital + baseline_before + candidate_before + np.cumsum(base_delta + candidate_delta) + base_floating + candidate_floating
            tracker = trackers[candidate_id]
            peak = np.maximum.accumulate(np.r_[tracker["peak"], equity])[1:]
            tracker["mdd"] = max(tracker["mdd"], float(np.max(peak - equity)))
            tracker["peak"] = max(tracker["peak"], float(np.max(equity)))
            tracker["minimum"] = min(tracker["minimum"], float(np.min(equity)))
            daily_rows.append({"date_utc": day.date_utc, "candidate_id": candidate_id, "minimum_equity_jpy": float(np.min(equity)), "maximum_drawdown_jpy_to_date": tracker["mdd"]})
    summary = {
        candidate_id: {
            "full_equity_mdd_jpy": values["mdd"],
            "minimum_equity_jpy": values["minimum"],
            "maximum_equity_jpy": values["peak"],
        }
        for candidate_id, values in trackers.items()
    }
    return summary, pd.DataFrame(daily_rows)


def concurrency_metrics(baseline: pd.DataFrame, candidate: pd.DataFrame) -> dict[str, Any]:
    def peak(frame: pd.DataFrame) -> int:
        events: list[tuple[pd.Timestamp, int]] = []
        for row in frame.itertuples(index=False):
            events.append((pd.Timestamp(row.entry_utc), 1))
            events.append((pd.Timestamp(row.exit_utc), -1))
        active = maximum = 0
        for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
            active += delta
            maximum = max(maximum, active)
        return maximum
    same = opposite = simultaneous = 0
    for row in candidate.itertuples(index=False):
        overlap = baseline[(baseline.entry_utc < row.exit_utc) & (baseline.exit_utc > row.entry_utc)]
        simultaneous += int(len(overlap))
        same += int((overlap.side.astype(int) == int(row.side)).sum())
        opposite += int((overlap.side.astype(int) == -int(row.side)).sum())
    return {
        "candidate_peak_concurrency": peak(candidate),
        "baseline_peak_concurrency": peak(baseline),
        "combined_peak_concurrency": peak(pd.concat([baseline, candidate], ignore_index=True)),
        "simultaneous_holding_pairs": simultaneous,
        "same_direction_overlap_pairs": same,
        "opposite_direction_overlap_pairs": opposite,
        "incremental_lots": 0.01,
        "incremental_gross_notional_usd": 1000.0,
    }
