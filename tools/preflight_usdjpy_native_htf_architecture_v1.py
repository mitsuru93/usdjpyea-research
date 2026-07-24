#!/usr/bin/env python3
"""Pre-outcome feasibility audit for native H1/H4 USDJPY architecture.

This tool constructs no strategy signals and computes no strategy P/L. It only
proves a deterministic logical-M15 -> historical-server H1/H4 aggregation
contract for the accepted 2023/2024 lineages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nth_sunday(year: int, month: int, nth: int, hour_utc: int) -> pd.Timestamp:
    first = datetime(year, month, 1, hour_utc, tzinfo=timezone.utc)
    days = (6 - first.weekday()) % 7 + 7 * (nth - 1)
    return pd.Timestamp(first + timedelta(days=days))


def is_us_dst_utc(ts: pd.Timestamp) -> bool:
    return nth_sunday(ts.year, 3, 2, 7) <= ts < nth_sunday(ts.year, 11, 1, 6)


def server_to_historical_utc(server_ts: pd.Timestamp) -> pd.Timestamp:
    winter_candidate = server_ts - pd.Timedelta(hours=2)
    return server_ts - pd.Timedelta(hours=3) if is_us_dst_utc(winter_candidate) else winter_candidate


def historical_utc_to_server(utc_ts: pd.Timestamp) -> pd.Timestamp:
    return utc_ts + pd.Timedelta(hours=3 if is_us_dst_utc(utc_ts) else 2)


def load_2023(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw = pd.read_csv(path)
    required = {
        "timestamp_utc", "open", "high", "low", "close",
        "first_timestamp_mt4_server", "source_count", "incomplete_source_count",
    }
    if not required.issubset(raw.columns):
        raise AssertionError(sorted(required - set(raw.columns)))
    true_utc = pd.to_datetime(raw["timestamp_utc"], utc=True, errors="raise")
    first_server = pd.to_datetime(raw["first_timestamp_mt4_server"], utc=True, errors="raise")
    accepted_first_tick_utc = pd.DatetimeIndex([server_to_historical_utc(value) for value in first_server])
    logical_server = first_server.dt.floor("15min")
    logical_utc = pd.DatetimeIndex([server_to_historical_utc(value) for value in logical_server])
    frame = pd.DataFrame(
        {
            "logical_utc": logical_utc,
            "logical_server": logical_server,
            "open": pd.to_numeric(raw["open"], errors="raise"),
            "high": pd.to_numeric(raw["high"], errors="raise"),
            "low": pd.to_numeric(raw["low"], errors="raise"),
            "close": pd.to_numeric(raw["close"], errors="raise"),
            "source_count": pd.to_numeric(raw["source_count"], errors="raise"),
            "incomplete_source_count": raw["incomplete_source_count"].astype(bool),
        }
    ).sort_values("logical_server").reset_index(drop=True)
    identity = {
        "rows": int(len(frame)),
        "accepted_first_tick_shifted_rows": int((accepted_first_tick_utc != pd.DatetimeIndex(true_utc)).sum()),
        "logical_bucket_shifted_rows": int((logical_utc != pd.DatetimeIndex(true_utc)).sum()),
        "logical_vs_accepted_first_tick_different_rows": int((logical_utc != accepted_first_tick_utc).sum()),
        "maximum_first_tick_offset_minutes": float(np.max(np.abs((accepted_first_tick_utc - logical_utc).total_seconds() / 60.0))),
        "logical_utc_duplicates": int(frame["logical_utc"].duplicated().sum()),
        "logical_server_duplicates": int(frame["logical_server"].duplicated().sum()),
        "logical_server_monotonic": bool(frame["logical_server"].is_monotonic_increasing),
        "source_count_distribution": {str(key): int(value) for key, value in raw["source_count"].value_counts().sort_index().items()},
        "incomplete_m15_rows": int(raw["incomplete_source_count"].astype(bool).sum()),
    }
    return frame, identity


def load_2024(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw = pd.read_csv(path, compression="gzip")
    required = {"timestamp_utc", "mid_open", "mid_high", "mid_low", "mid_close"}
    if not required.issubset(raw.columns):
        raise AssertionError(sorted(required - set(raw.columns)))
    logical_utc = pd.to_datetime(raw["timestamp_utc"], utc=True, errors="raise")
    logical_server = pd.DatetimeIndex([historical_utc_to_server(value) for value in logical_utc])
    roundtrip = pd.DatetimeIndex([server_to_historical_utc(value) for value in logical_server])
    frame = pd.DataFrame(
        {
            "logical_utc": logical_utc,
            "logical_server": logical_server,
            "open": pd.to_numeric(raw["mid_open"], errors="raise"),
            "high": pd.to_numeric(raw["mid_high"], errors="raise"),
            "low": pd.to_numeric(raw["mid_low"], errors="raise"),
            "close": pd.to_numeric(raw["mid_close"], errors="raise"),
            "source_count": np.nan,
            "incomplete_source_count": False,
        }
    ).sort_values("logical_server").reset_index(drop=True)
    identity = {
        "rows": int(len(frame)),
        "utc_to_server_to_utc_mismatches": int((roundtrip != pd.DatetimeIndex(logical_utc)).sum()),
        "logical_utc_duplicates": int(frame["logical_utc"].duplicated().sum()),
        "logical_server_duplicates": int(frame["logical_server"].duplicated().sum()),
        "logical_server_monotonic": bool(frame["logical_server"].is_monotonic_increasing),
        "server_offset_hours": sorted({int((server - utc).total_seconds() / 3600) for server, utc in zip(logical_server, logical_utc)}),
    }
    return frame, identity


def aggregate(frame: pd.DataFrame, label: str, expected_slots: int, frequency: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    bucket = frame["logical_server"].dt.floor(frequency)
    work = frame.assign(bucket_server=bucket)
    grouped = work.groupby("bucket_server", sort=True).agg(
        constituent_m15=("logical_server", "size"),
        first_m15_server=("logical_server", "min"),
        last_m15_server=("logical_server", "max"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        incomplete_constituent_m15=("incomplete_source_count", "sum"),
    )
    exact: list[bool] = []
    for bucket_start, row in grouped.iterrows():
        expected = set(pd.date_range(bucket_start, periods=expected_slots, freq="15min"))
        actual = set(work.loc[work["bucket_server"] == bucket_start, "logical_server"])
        exact.append(actual == expected)
    grouped["exact_constituent_slots"] = exact
    grouped["timeframe"] = label
    grouped["bucket_close_server"] = grouped.index + pd.tseries.frequencies.to_offset(frequency)
    grouped["information_utc"] = [server_to_historical_utc(value) for value in grouped["bucket_close_server"]]
    partial = grouped[~grouped["exact_constituent_slots"]].copy()
    summary = {
        "timeframe": label,
        "expected_m15_slots": expected_slots,
        "nonempty_buckets": int(len(grouped)),
        "exact_slot_buckets": int(grouped["exact_constituent_slots"].sum()),
        "partial_buckets": int((~grouped["exact_constituent_slots"]).sum()),
        "exact_buckets_with_incomplete_source_m15": int(((grouped["exact_constituent_slots"]) & (grouped["incomplete_constituent_m15"] > 0)).sum()),
        "partial_constituent_count_distribution": {str(key): int(value) for key, value in partial["constituent_m15"].value_counts().sort_index().items()},
        "information_time_monotonic": bool(grouped["information_utc"].is_monotonic_increasing),
        "information_time_duplicates": int(grouped["information_utc"].duplicated().sum()),
    }
    return grouped.reset_index(), summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m15-2023", required=True, type=Path)
    parser.add_argument("--m15-2024", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    frame23, identity23 = load_2023(args.m15_2023)
    frame24, identity24 = load_2024(args.m15_2024)
    if identity23["accepted_first_tick_shifted_rows"] != 1543:
        raise AssertionError(identity23)
    if identity23["logical_utc_duplicates"] or identity23["logical_server_duplicates"]:
        raise AssertionError(identity23)
    if identity24["utc_to_server_to_utc_mismatches"]:
        raise AssertionError(identity24)

    summary_rows: list[dict[str, Any]] = []
    partial_rows: list[pd.DataFrame] = []
    aggregate_summary: dict[str, Any] = {}
    for year, frame in [(2023, frame23), (2024, frame24)]:
        for timeframe, slots, frequency in [("H1", 4, "1h"), ("H4", 16, "4h")]:
            aggregated, summary = aggregate(frame, timeframe, slots, frequency)
            summary["year"] = year
            aggregate_summary[f"{year}_{timeframe}"] = summary
            summary_rows.append(summary)
            partial = aggregated[~aggregated["exact_constituent_slots"]].copy()
            partial.insert(0, "year", year)
            partial_rows.append(partial)

    summary_path = output / "usdjpy_native_htf_construction_summary_v1.csv"
    partial_path = output / "usdjpy_native_htf_partial_bucket_inventory_v1.csv"
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False, lineterminator="\n")
    pd.concat(partial_rows, ignore_index=True).to_csv(partial_path, index=False, lineterminator="\n")

    result = {
        "schema_version": "usdjpy_native_htf_construction_feasibility_result_v1",
        "status": "PASS_DETERMINISTIC_NATIVE_H1_H4_CONSTRUCTION",
        "decision": "USE_LOGICAL_MT4_SERVER_M15_BUCKETS_NOT_ACCEPTED_FIRST_TICK_DISPLAY_TIMESTAMPS",
        "source_identity": {
            "2023_m15_sha256": sha256_file(args.m15_2023),
            "2024_m15_sha256": sha256_file(args.m15_2024),
        },
        "2023_identity": identity23,
        "2024_identity": identity24,
        "aggregation": aggregate_summary,
        "contract": {
            "2023_membership_key": "floor(first_timestamp_mt4_server, 15 minutes)",
            "2024_membership_key": "historical UTC converted to MT4 server UTC+2 winter / UTC+3 US-DST, already aligned to 15 minutes",
            "H1_bucket": "floor logical MT4 server timestamp to one hour",
            "H4_bucket": "floor logical MT4 server timestamp to four hours",
            "OHLC": "first open, maximum high, minimum low, last close in logical server order",
            "complete_bar_information_time": "server bucket close converted by historical ServerToUtc",
            "state_update_eligibility": "only exact constituent-slot buckets; partial H1/H4 buckets are inventoried and do not update state",
            "execution_time": "first accepted M15 open at or after completed higher-timeframe information time",
            "lookahead": false,
            "historical_2024_mutated": false,
        },
        "interpretation": [
            "The accepted 2023 first-tick timestamps reproduce the binding 1,543 shifted-row identity but 123 bars are not logical 15-minute boundaries.",
            "Higher-timeframe membership must therefore use the source server bucket boundary, while the accepted first-tick timestamp remains preserved for historical M15 trade identity.",
            "H1 and H4 aggregation is deterministic in both years; partial market-open, market-close and holiday buckets are excluded from state updates rather than imputed.",
        ],
        "boundaries": {
            "strategy_signal_generated": false,
            "strategy_PL_calculated": false,
            "parameter_selected_from_outcomes": false,
            "MT4_accessed": false,
            "2025_accessed": false,
            "live_orders": false,
        },
        "output_sha256": {
            summary_path.name: sha256_file(summary_path),
            partial_path.name: sha256_file(partial_path),
        },
    }
    result_path = output / "usdjpy_native_htf_construction_feasibility_result_v1.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
