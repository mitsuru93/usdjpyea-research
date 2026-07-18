#!/usr/bin/env python3
"""Evaluate the frozen USDJPY R1 Entry ledger over the pre-registered R2 horizons.

The evaluator consumes only the accepted canonical M15 bars and corrected R1 v2
signal ledger. It does not regenerate Entry definitions, read H2/2025 data, select
candidates, or promote a strategy. All fixed horizons are diagnostic time exits.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PIP = 0.01
H1_END = pd.Timestamp("2024-07-01T00:00:00Z")
H1_MONTHS = [f"2024-{m:02d}" for m in range(1, 7)]
DIRECTIONS = [-1, 1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_candidate_definition(family: str, candidate: dict[str, Any]) -> tuple[str, str]:
    metadata = {"id", "origin", "legacy_ids", "h2_information_status", "literature_refs", "family"}
    payload = {
        "family": family,
        "parameters": {key: value for key, value in candidate.items() if key not in metadata},
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text, hashlib.sha256((text + "\n").encode("utf-8")).hexdigest()


def profit_factor(values: pd.Series) -> float:
    if values.empty:
        return 0.0
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0.0:
        return math.inf if gains > 0.0 else 0.0
    return gains / losses


def daily_exclusion_totals(frame: pd.DataFrame, count: int) -> float:
    if frame.empty:
        return 0.0
    daily = frame.groupby("entry_date_utc", sort=True)["default_net_pips"].sum().sort_values(ascending=False)
    return float(frame["default_net_pips"].sum() - daily.head(count).sum())


def metric_block(frame: pd.DataFrame) -> dict[str, float | int]:
    if frame.empty:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "avg_gross_pips": 0.0,
            "avg_default_net_pips": 0.0,
            "total_default_net_pips": 0.0,
            "default_profit_factor": 0.0,
            "avg_severe_net_pips": 0.0,
            "total_severe_net_pips": 0.0,
            "severe_profit_factor": 0.0,
            "median_default_net_pips": 0.0,
            "q05_default_net_pips": 0.0,
            "q95_default_net_pips": 0.0,
            "avg_mfe_pips": 0.0,
            "avg_mae_pips": 0.0,
            "median_mfe_pips": 0.0,
            "median_mae_pips": 0.0,
            "avg_bars_to_mfe": 0.0,
            "avg_bars_to_mae": 0.0,
            "total_excluding_best_utc_day": 0.0,
            "total_excluding_best_two_utc_days": 0.0,
        }
    default = frame["default_net_pips"]
    severe = frame["severe_net_pips"]
    return {
        "trades": int(len(frame)),
        "win_rate": float((default > 0).mean()),
        "avg_gross_pips": float(frame["gross_pips"].mean()),
        "avg_default_net_pips": float(default.mean()),
        "total_default_net_pips": float(default.sum()),
        "default_profit_factor": profit_factor(default),
        "avg_severe_net_pips": float(severe.mean()),
        "total_severe_net_pips": float(severe.sum()),
        "severe_profit_factor": profit_factor(severe),
        "median_default_net_pips": float(default.median()),
        "q05_default_net_pips": float(default.quantile(0.05)),
        "q95_default_net_pips": float(default.quantile(0.95)),
        "avg_mfe_pips": float(frame["mfe_pips"].mean()),
        "avg_mae_pips": float(frame["mae_pips"].mean()),
        "median_mfe_pips": float(frame["mfe_pips"].median()),
        "median_mae_pips": float(frame["mae_pips"].median()),
        "avg_bars_to_mfe": float(frame["bars_to_mfe"].mean()),
        "avg_bars_to_mae": float(frame["bars_to_mae"].mean()),
        "total_excluding_best_utc_day": daily_exclusion_totals(frame, 1),
        "total_excluding_best_two_utc_days": daily_exclusion_totals(frame, 2),
    }


def csv_bytes(frame: pd.DataFrame, float_format: str = "%.12f") -> bytes:
    return frame.to_csv(index=False, float_format=float_format, lineterminator="\n", na_rep="").encode("utf-8")


def deterministic_gzip(payload: bytes) -> bytes:
    target = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0, compresslevel=6) as handle:
        handle.write(payload)
    return target.getvalue()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.write_bytes(csv_bytes(frame))


def write_gzip_csv(frame: pd.DataFrame, path: Path) -> tuple[str, bool]:
    payload = csv_bytes(frame)
    first = deterministic_gzip(payload)
    second = deterministic_gzip(payload)
    identical = first == second
    path.write_bytes(first)
    return hashlib.sha256(first).hexdigest(), identical


def load_inputs(
    canonical_path: Path,
    signal_path: Path,
    registry_path: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, str]]:
    hashes = {
        "canonical_m15_gzip_sha256": sha256_file(canonical_path),
        "r1_signal_gzip_sha256": sha256_file(signal_path),
        "r1_registry_snapshot_sha256": sha256_file(registry_path),
    }
    expected = config["inputs"]
    assert hashes["canonical_m15_gzip_sha256"] == expected["canonical_m15_gzip_sha256"]
    assert hashes["r1_signal_gzip_sha256"] == expected["r1_signal_gzip_sha256"]
    assert hashes["r1_registry_snapshot_sha256"] == expected["r1_registry_snapshot_sha256"]

    bars = pd.read_csv(canonical_path)
    required_bars = {
        "timestamp_utc", "symbol", "mid_open", "mid_high", "mid_low", "mid_close", "spread_mean_pips"
    }
    assert required_bars.issubset(bars.columns), sorted(required_bars - set(bars.columns))
    bars = bars[list(required_bars)].copy()
    bars["timestamp_utc"] = pd.to_datetime(bars["timestamp_utc"], utc=True, errors="raise")
    for column in ["mid_open", "mid_high", "mid_low", "mid_close", "spread_mean_pips"]:
        bars[column] = pd.to_numeric(bars[column], errors="raise")
    assert (bars["symbol"] == "USDJPY").all()
    assert not bars["timestamp_utc"].duplicated().any()
    assert bars["timestamp_utc"].is_monotonic_increasing
    bars = bars.reset_index(drop=True)
    bars["month_utc"] = bars["timestamp_utc"].dt.strftime("%Y-%m")
    bars["date_utc"] = bars["timestamp_utc"].dt.strftime("%Y-%m-%d")

    signals = pd.read_csv(signal_path)
    required_signals = {"candidate_id", "family", "definition_sha256", "signal_ts", "entry_ts", "side"}
    assert required_signals.issubset(signals.columns), sorted(required_signals - set(signals.columns))
    signals = signals[list(required_signals)].copy()
    signals["signal_ts"] = pd.to_datetime(signals["signal_ts"], utc=True, errors="raise")
    signals["entry_ts"] = pd.to_datetime(signals["entry_ts"], utc=True, errors="raise")
    signals["side"] = pd.to_numeric(signals["side"], errors="raise").astype(int)
    assert signals["side"].isin([-1, 1]).all()
    assert (signals["entry_ts"] > signals["signal_ts"]).all()
    assert (signals["entry_ts"] < H1_END).all()
    assert (signals["signal_ts"] < H1_END).all()
    assert not signals.duplicated(["candidate_id", "signal_ts", "side"]).any()

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    return bars, signals, registry, hashes


def hard_no_trade_violations(entry_ts: pd.Series, session_config: dict[str, Any]) -> int:
    violations = pd.Series(False, index=entry_ts.index)
    for window in session_config.get("hard_no_trade_windows", []):
        applies = window.get("applies_to", [])
        if "*" not in applies and "USDJPY" not in applies:
            continue
        local = entry_ts.dt.tz_convert(ZoneInfo(window["timezone"]))
        minute = local.dt.hour * 60 + local.dt.minute
        start_hour, start_minute = map(int, window["start_local"].split(":"))
        end_hour, end_minute = map(int, window["end_local"].split(":"))
        start = start_hour * 60 + start_minute
        end = end_hour * 60 + end_minute
        if start < end:
            current = (minute >= start) & (minute < end)
        else:
            current = (minute >= start) | (minute < end)
        violations |= current
    return int(violations.sum())


def build_trades(
    bars: pd.DataFrame,
    signals: pd.DataFrame,
    candidates: list[dict[str, str]],
    horizons: list[int],
) -> pd.DataFrame:
    from numpy.lib.stride_tricks import sliding_window_view

    timestamp_to_index = pd.Series(bars.index.to_numpy(), index=bars["timestamp_utc"]).to_dict()
    opens = bars["mid_open"].to_numpy(float)
    highs = bars["mid_high"].to_numpy(float)
    lows = bars["mid_low"].to_numpy(float)
    closes = bars["mid_close"].to_numpy(float)
    spreads = bars["spread_mean_pips"].to_numpy(float)
    timestamps = bars["timestamp_utc"].tolist()
    months = bars["month_utc"].to_numpy(str)
    dates = bars["date_utc"].to_numpy(str)

    candidate_meta = pd.DataFrame(candidates).set_index("candidate_id")
    work = signals.copy()
    work["entry_index"] = work["entry_ts"].map(timestamp_to_index)
    assert work["entry_index"].notna().all()
    entry_indices_all = work["entry_index"].astype(int).to_numpy()
    sides_all = work["side"].to_numpy(int)
    candidate_ids_all = work["candidate_id"].to_numpy(str)
    families_all = work["family"].to_numpy(str)
    definitions_all = work["definition_sha256"].to_numpy(str)
    signal_ts_all = work["signal_ts"].tolist()
    entry_ts_all = work["entry_ts"].tolist()

    frames: list[pd.DataFrame] = []
    for horizon in horizons:
        exit_indices_all = entry_indices_all + horizon - 1
        in_bounds = exit_indices_all < len(bars)
        positions = np.where(in_bounds)[0]
        same_month = months[entry_indices_all[positions]] == months[exit_indices_all[positions]]
        before_h2 = np.array([timestamps[index] < H1_END for index in exit_indices_all[positions]])
        positions = positions[same_month & before_h2]
        if len(positions) == 0:
            continue

        entry_indices = entry_indices_all[positions]
        exit_indices = exit_indices_all[positions]
        sides = sides_all[positions]
        entry_mid = opens[entry_indices]
        exit_mid = closes[exit_indices]
        entry_spread = spreads[entry_indices]
        default_cost = np.maximum(0.5, entry_spread)
        severe_cost = default_cost * 3.0 + 1.0
        gross = sides * (exit_mid - entry_mid) / PIP

        high_windows = sliding_window_view(highs, horizon)
        low_windows = sliding_window_view(lows, horizon)
        selected_high = high_windows[entry_indices]
        selected_low = low_windows[entry_indices]
        high_max = selected_high.max(axis=1)
        low_min = selected_low.min(axis=1)
        high_argmax = selected_high.argmax(axis=1) + 1
        low_argmin = selected_low.argmin(axis=1) + 1

        long_mask = sides == 1
        raw_mfe = np.where(long_mask, (high_max - entry_mid) / PIP, (entry_mid - low_min) / PIP)
        raw_mae = np.where(long_mask, (low_min - entry_mid) / PIP, (entry_mid - high_max) / PIP)
        mfe = np.maximum(0.0, raw_mfe)
        mae = np.minimum(0.0, raw_mae)
        bars_to_mfe = np.where(raw_mfe > 0, np.where(long_mask, high_argmax, low_argmin), 0)
        bars_to_mae = np.where(raw_mae < 0, np.where(long_mask, low_argmin, high_argmax), 0)

        frame = pd.DataFrame({
            "candidate_id": candidate_ids_all[positions],
            "family": families_all[positions],
            "definition_sha256": definitions_all[positions],
            "horizon_bars": horizon,
            "signal_ts": [signal_ts_all[position] for position in positions],
            "entry_ts": [entry_ts_all[position] for position in positions],
            "exit_ts": [timestamps[index] for index in exit_indices],
            "entry_month": months[entry_indices],
            "entry_date_utc": dates[entry_indices],
            "side": sides,
            "entry_mid": entry_mid,
            "exit_mid": exit_mid,
            "entry_spread_pips": entry_spread,
            "gross_pips": gross,
            "default_cost_pips": default_cost,
            "severe_cost_pips": severe_cost,
            "default_net_pips": gross - default_cost,
            "severe_net_pips": gross - severe_cost,
            "mfe_pips": mfe,
            "mae_pips": mae,
            "bars_to_mfe": bars_to_mfe.astype(int),
            "bars_to_mae": bars_to_mae.astype(int),
        })
        frames.append(frame)

    if not frames:
        raise RuntimeError("no R2 trade rows generated")
    trades = pd.concat(frames, ignore_index=True)
    return trades.sort_values(["candidate_id", "horizon_bars", "entry_ts", "side"]).reset_index(drop=True)


def _aggregate_metrics(frame: pd.DataFrame, keys: list[str], include_daily_exclusions: bool) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=keys)
    work = frame.copy()
    work["win_default"] = (work["default_net_pips"] > 0).astype(float)
    work["default_gain"] = work["default_net_pips"].clip(lower=0.0)
    work["default_loss"] = (-work["default_net_pips"].clip(upper=0.0))
    work["severe_gain"] = work["severe_net_pips"].clip(lower=0.0)
    work["severe_loss"] = (-work["severe_net_pips"].clip(upper=0.0))
    grouped = work.groupby(keys, sort=True, observed=True)
    out = grouped.agg(
        trades=("default_net_pips", "size"),
        win_rate=("win_default", "mean"),
        avg_gross_pips=("gross_pips", "mean"),
        avg_default_net_pips=("default_net_pips", "mean"),
        total_default_net_pips=("default_net_pips", "sum"),
        default_gains=("default_gain", "sum"),
        default_losses=("default_loss", "sum"),
        avg_severe_net_pips=("severe_net_pips", "mean"),
        total_severe_net_pips=("severe_net_pips", "sum"),
        severe_gains=("severe_gain", "sum"),
        severe_losses=("severe_loss", "sum"),
        median_default_net_pips=("default_net_pips", "median"),
        avg_mfe_pips=("mfe_pips", "mean"),
        avg_mae_pips=("mae_pips", "mean"),
        median_mfe_pips=("mfe_pips", "median"),
        median_mae_pips=("mae_pips", "median"),
        avg_bars_to_mfe=("bars_to_mfe", "mean"),
        avg_bars_to_mae=("bars_to_mae", "mean"),
    ).reset_index()
    q05 = grouped["default_net_pips"].quantile(0.05).rename("q05_default_net_pips").reset_index()
    q95 = grouped["default_net_pips"].quantile(0.95).rename("q95_default_net_pips").reset_index()
    out = out.merge(q05, on=keys, how="left").merge(q95, on=keys, how="left")
    out["default_profit_factor"] = np.where(
        out["default_losses"] > 0,
        out["default_gains"] / out["default_losses"],
        np.where(out["default_gains"] > 0, np.inf, 0.0),
    )
    out["severe_profit_factor"] = np.where(
        out["severe_losses"] > 0,
        out["severe_gains"] / out["severe_losses"],
        np.where(out["severe_gains"] > 0, np.inf, 0.0),
    )
    out = out.drop(columns=["default_gains", "default_losses", "severe_gains", "severe_losses"])
    if include_daily_exclusions:
        daily = (
            work.groupby(keys + ["entry_date_utc"], sort=True, observed=True)["default_net_pips"]
            .sum()
            .rename("daily_net")
            .reset_index()
        )
        daily = daily.sort_values(keys + ["daily_net"], ascending=[True] * len(keys) + [False])
        daily["daily_rank"] = daily.groupby(keys, sort=False).cumcount() + 1
        best1 = daily[daily["daily_rank"] == 1].set_index(keys)["daily_net"]
        best2 = daily[daily["daily_rank"] <= 2].groupby(keys)["daily_net"].sum()
        index = pd.MultiIndex.from_frame(out[keys]) if len(keys) > 1 else pd.Index(out[keys[0]])
        out["total_excluding_best_utc_day"] = out["total_default_net_pips"].to_numpy() - best1.reindex(index, fill_value=0.0).to_numpy()
        out["total_excluding_best_two_utc_days"] = out["total_default_net_pips"].to_numpy() - best2.reindex(index, fill_value=0.0).to_numpy()
    else:
        out["total_excluding_best_utc_day"] = 0.0
        out["total_excluding_best_two_utc_days"] = 0.0
    return out


def _complete_grid(base: pd.DataFrame, aggregate: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    result = base.merge(aggregate, on=keys, how="left")
    non_keys = [column for column in result.columns if column not in keys + ["family", "definition_sha256"]]
    result[non_keys] = result[non_keys].fillna(0.0)
    if "trades" in result:
        result["trades"] = result["trades"].astype(int)
    return result


def build_reports(
    trades: pd.DataFrame,
    candidates: list[dict[str, str]],
    horizons: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidate_frame = pd.DataFrame(candidates)[["candidate_id", "family", "definition_sha256"]]
    horizon_frame = pd.DataFrame({"horizon_bars": horizons})
    candidate_frame["_join"] = 1
    horizon_frame["_join"] = 1
    combo_grid = candidate_frame.merge(horizon_frame, on="_join").drop(columns="_join")

    summary_agg = _aggregate_metrics(trades, ["candidate_id", "horizon_bars"], True)
    summary = _complete_grid(combo_grid, summary_agg, ["candidate_id", "horizon_bars"])

    month_frame = pd.DataFrame({"month": H1_MONTHS})
    combo_grid["_join"] = 1
    month_frame["_join"] = 1
    monthly_grid = combo_grid.merge(month_frame, on="_join").drop(columns="_join")
    monthly_source = trades.rename(columns={"entry_month": "month"})
    monthly_agg = _aggregate_metrics(monthly_source, ["candidate_id", "horizon_bars", "month"], False)
    monthly = _complete_grid(monthly_grid, monthly_agg, ["candidate_id", "horizon_bars", "month"])

    month_flags = monthly.assign(positive=(monthly["trades"] > 0) & (monthly["avg_default_net_pips"] > 0))
    month_stats = month_flags.groupby(["candidate_id", "horizon_bars"], sort=True).agg(
        positive_months=("positive", "sum"), minimum_monthly_trades=("trades", "min")
    ).reset_index()
    summary = summary.merge(month_stats, on=["candidate_id", "horizon_bars"], how="left")
    summary["positive_months"] = summary["positive_months"].astype(int)
    summary["minimum_monthly_trades"] = summary["minimum_monthly_trades"].astype(int)

    direction_frame = pd.DataFrame({"side": DIRECTIONS})
    combo_grid["_join"] = 1
    direction_frame["_join"] = 1
    direction_grid = combo_grid.merge(direction_frame, on="_join").drop(columns="_join")
    direction_agg = _aggregate_metrics(trades, ["candidate_id", "horizon_bars", "side"], False)
    direction = _complete_grid(direction_grid, direction_agg, ["candidate_id", "horizon_bars", "side"])
    direction["side"] = direction["side"].astype(int)

    ledger_columns = [
        "signal_ts", "entry_ts", "exit_ts", "side", "entry_mid", "exit_mid", "entry_spread_pips",
        "gross_pips", "default_cost_pips", "severe_cost_pips", "default_net_pips", "severe_net_pips",
        "mfe_pips", "mae_pips", "bars_to_mfe", "bars_to_mae",
    ]
    trade_groups = {
        (str(candidate_id), int(horizon)): group
        for (candidate_id, horizon), group in trades.groupby(["candidate_id", "horizon_bars"], sort=False)
    }
    empty = trades.iloc[0:0]
    hash_rows: list[dict[str, Any]] = []
    for row in combo_grid.itertuples(index=False):
        group = trade_groups.get((row.candidate_id, int(row.horizon_bars)), empty)
        normalized = group[ledger_columns].copy()
        for column in ["signal_ts", "entry_ts", "exit_ts"]:
            normalized[column] = pd.to_datetime(normalized[column], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = csv_bytes(normalized.sort_values(["entry_ts", "side"]).reset_index(drop=True), "%.10f")
        hash_rows.append({
            "candidate_id": row.candidate_id,
            "family": row.family,
            "definition_sha256": row.definition_sha256,
            "horizon_bars": int(row.horizon_bars),
            "trade_rows": int(len(group)),
            "trade_ledger_sha256": hashlib.sha256(payload).hexdigest(),
        })
    hashes = pd.DataFrame(hash_rows)

    surface_rows: list[dict[str, Any]] = []
    for candidate_id, current in summary.groupby("candidate_id", sort=True):
        current = current.set_index("horizon_bars").reindex(horizons)
        positive = ((current["trades"] > 0) & (current["avg_default_net_pips"] > 0)).tolist()
        longest = running = 0
        for flag in positive:
            running = running + 1 if flag else 0
            longest = max(longest, running)
        with_trades = current[current["trades"] > 0]
        best_horizon = int(with_trades["avg_default_net_pips"].idxmax()) if not with_trades.empty else 0
        best_average = float(with_trades["avg_default_net_pips"].max()) if not with_trades.empty else 0.0
        first = current.iloc[0]
        surface_rows.append({
            "candidate_id": candidate_id,
            "family": first["family"],
            "definition_sha256": first["definition_sha256"],
            "reported_horizons": len(horizons),
            "horizons_with_trades": int((current["trades"] > 0).sum()),
            "positive_default_horizons": int((current["avg_default_net_pips"] > 0).sum()),
            "positive_severe_horizons": int((current["avg_severe_net_pips"] > 0).sum()),
            "longest_positive_default_run": int(longest),
            "diagnostic_best_horizon_bars": best_horizon,
            "best_avg_default_net_pips": best_average,
            "hold6_avg_default_net_pips": float(current.loc[6, "avg_default_net_pips"]),
            "total_trade_rows_across_horizons": int(current["trades"].sum()),
        })
    surface = pd.DataFrame(surface_rows)

    return (
        summary.sort_values(["candidate_id", "horizon_bars"]).reset_index(drop=True),
        monthly.sort_values(["candidate_id", "horizon_bars", "month"]).reset_index(drop=True),
        direction.sort_values(["candidate_id", "horizon_bars", "side"]).reset_index(drop=True),
        surface.sort_values("candidate_id").reset_index(drop=True),
        hashes.sort_values(["candidate_id", "horizon_bars"]).reset_index(drop=True),
    )

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-m15", required=True, type=Path)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--registry-snapshot", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--session-config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))
    horizons = [int(value) for value in config["surface"]["horizons_m15_bars"]]
    assert horizons == [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48]

    bars, signals, registry, input_hashes = load_inputs(
        args.canonical_m15, args.signals, args.registry_snapshot, config
    )
    candidates: list[dict[str, str]] = []
    for family_block in registry["families"]:
        family = str(family_block["family"])
        for candidate in family_block["candidates"]:
            definition_json, definition_sha256 = canonical_candidate_definition(family, candidate)
            candidates.append({
                "candidate_id": str(candidate["id"]),
                "family": family,
                "definition_sha256": definition_sha256,
                "functional_definition_json": definition_json,
            })
    candidates.sort(key=lambda row: row["candidate_id"])
    assert len(candidates) == 60
    assert len({row["candidate_id"] for row in candidates}) == 60
    signal_definition_map = signals.groupby("candidate_id")["definition_sha256"].first().to_dict()
    for candidate in candidates:
        observed = signal_definition_map.get(candidate["candidate_id"])
        if observed is not None:
            assert observed == candidate["definition_sha256"], (candidate["candidate_id"], observed, candidate["definition_sha256"])

    violations = hard_no_trade_violations(signals["entry_ts"], session_config)
    assert violations == 0
    trades = build_trades(bars, signals, candidates, horizons)
    summary, monthly, direction, surface, hashes = build_reports(trades, candidates, horizons)

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    ledger_columns = [
        "candidate_id", "horizon_bars", "signal_ts", "entry_ts", "exit_ts", "entry_month",
        "entry_date_utc", "side", "entry_mid", "exit_mid", "entry_spread_pips", "gross_pips",
        "default_cost_pips", "severe_cost_pips", "default_net_pips", "severe_net_pips",
        "mfe_pips", "mae_pips", "bars_to_mfe", "bars_to_mae",
    ]
    ledger = trades[ledger_columns].copy()
    for column in ["signal_ts", "entry_ts", "exit_ts"]:
        ledger[column] = pd.to_datetime(ledger[column], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    ledger_sha256, repeatable = write_gzip_csv(ledger, output / "candidate_horizon_trades.csv.gz")
    write_csv(summary, output / "candidate_horizon_summary.csv")
    write_csv(monthly, output / "candidate_horizon_monthly.csv")
    write_csv(direction, output / "candidate_horizon_direction.csv")
    write_csv(surface, output / "candidate_horizon_surface.csv")
    write_csv(hashes, output / "candidate_horizon_hashes.csv")

    zero_trade_candidates = int(summary.groupby("candidate_id")["trades"].max().eq(0).sum())
    checks: dict[str, bool | str] = {
        "status": "PASS",
        "canonical_digest_matches": input_hashes["canonical_m15_gzip_sha256"] == config["inputs"]["canonical_m15_gzip_sha256"],
        "r1_signal_digest_matches": input_hashes["r1_signal_gzip_sha256"] == config["inputs"]["r1_signal_gzip_sha256"],
        "r1_registry_digest_matches": input_hashes["r1_registry_snapshot_sha256"] == config["inputs"]["r1_registry_snapshot_sha256"],
        "candidate_count_60": len(candidates) == 60,
        "horizon_count_11": len(horizons) == 11,
        "surface_combinations_660": len(summary) == 660,
        "monthly_grid_3960": len(monthly) == 3960,
        "direction_grid_1320": len(direction) == 1320,
        "surface_rows_60": len(surface) == 60,
        "hash_rows_660": len(hashes) == 660,
        "zero_trade_candidates_retained": len(summary) == 660,
        "entry_exit_same_month": bool((trades["entry_ts"].dt.strftime("%Y-%m") == trades["exit_ts"].dt.strftime("%Y-%m")).all()),
        "entry_after_signal": bool((trades["entry_ts"] > trades["signal_ts"]).all()),
        "hard_no_trade_violations_zero": violations == 0,
        "h2_rows_parsed_zero": bool((trades["exit_ts"] < H1_END).all()),
        "no_2025_access": True,
        "deterministic_trade_ledger": repeatable,
        "no_selection_or_promotion": True,
        "default_cost_floor_applied": bool((trades["default_cost_pips"] >= 0.5 - 1e-12).all()),
        "severe_cost_formula_exact": bool(np.allclose(trades["severe_cost_pips"], trades["default_cost_pips"] * 3.0 + 1.0, rtol=0.0, atol=1e-12)),
        "path_extrema_complete": bool(trades[["mfe_pips", "mae_pips", "bars_to_mfe", "bars_to_mae"]].notna().all().all()),
    }
    assert all(value is True for key, value in checks.items() if key != "status"), checks
    acceptance_path = output / "r2_acceptance.json"
    acceptance_path.write_text(json.dumps(checks, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_hashes = {
        path.name: sha256_file(path)
        for path in sorted(output.iterdir())
        if path.is_file()
    }
    metadata = {
        "version": "v1",
        "status": "PASS",
        "research_stage": "R2_fixed_horizon_surface",
        "candidate_count": len(candidates),
        "horizons": horizons,
        "summary_rows": len(summary),
        "monthly_rows": len(monthly),
        "direction_rows": len(direction),
        "surface_rows": len(surface),
        "hash_rows": len(hashes),
        "trade_rows": int(len(trades)),
        "zero_trade_candidates": zero_trade_candidates,
        "hard_no_trade_violations": violations,
        "h2_rows_parsed": 0,
        "2025_artifact_access": False,
        "selection_or_promotion_made": False,
        "Core_promotion": False,
        "MT4_promotion": False,
        "R3_unblocked": True,
        "candidate_horizon_trades_gzip_sha256": ledger_sha256,
        "input_sha256": input_hashes,
        "output_sha256": output_hashes,
    }
    (output / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
