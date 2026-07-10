#!/usr/bin/env python3
"""Build market/cost profile tables from normalized FX bar CSV files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PIP_SIZE = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "AUDUSD": 0.0001,
    "USDCAD": 0.0001,
    "USDCHF": 0.0001,
    "USDJPY": 0.01,
}

RAKUTEN_BASE_SPREAD_PIPS = {
    "EURUSD": 0.6,
    "USDJPY": 0.5,
    "GBPUSD": 1.2,
    "AUDUSD": 1.2,
    "USDCAD": 2.0,
    "USDCHF": 1.6,
}


def load_normalized(paths: list[str]) -> pd.DataFrame:
    frames = []
    for p in paths:
        frame = pd.read_csv(p)
        frame["_input_path"] = p
        frames.append(frame)
    if not frames:
        raise ValueError("at least one --input is required")
    df = pd.concat(frames, ignore_index=True)
    if "timestamp_utc" not in df.columns or "symbol" not in df.columns:
        raise ValueError("normalized files must contain timestamp_utc and symbol")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp_utc", "symbol"])
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["symbol"] = out["symbol"].astype(str).str.upper()
    out["hour_utc"] = out["timestamp_utc"].dt.hour
    out["weekday"] = out["timestamp_utc"].dt.day_name()
    out["date"] = out["timestamp_utc"].dt.date.astype(str)
    if {"mid_high", "mid_low"}.issubset(out.columns):
        high = pd.to_numeric(out["mid_high"], errors="coerce")
        low = pd.to_numeric(out["mid_low"], errors="coerce")
    else:
        high = pd.to_numeric(out["high"], errors="coerce")
        low = pd.to_numeric(out["low"], errors="coerce")
    out["bar_range_pips"] = (high - low) / out["symbol"].map(PIP_SIZE)
    if "spread_mean_pips" not in out.columns:
        out["spread_mean_pips"] = out["symbol"].map(RAKUTEN_BASE_SPREAD_PIPS)
        out["spread_source"] = "rakuten_base_spread_proxy"
    else:
        out["spread_source"] = "public_bid_ask_proxy"
    out["rakuten_base_spread_pips"] = out["symbol"].map(RAKUTEN_BASE_SPREAD_PIPS)
    out["spread_to_range"] = out["spread_mean_pips"] / out["bar_range_pips"].replace(0, pd.NA)
    out["rakuten_spread_to_range"] = out["rakuten_base_spread_pips"] / out["bar_range_pips"].replace(0, pd.NA)
    return out


def summarize(group: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    return (
        group.groupby(keys, dropna=False)
        .agg(
            bars=("timestamp_utc", "count"),
            median_range_pips=("bar_range_pips", "median"),
            p90_range_pips=("bar_range_pips", lambda s: s.quantile(0.90)),
            p95_range_pips=("bar_range_pips", lambda s: s.quantile(0.95)),
            median_spread_pips=("spread_mean_pips", "median"),
            p90_spread_pips=("spread_mean_pips", lambda s: s.quantile(0.90)),
            median_spread_to_range=("spread_to_range", "median"),
            median_rakuten_spread_to_range=("rakuten_spread_to_range", "median"),
        )
        .reset_index()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build market profile CSVs from normalized FX data.")
    parser.add_argument("--input", action="append", required=True, help="Normalized CSV path. Repeatable.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = add_features(load_normalized(args.input))
    overall = summarize(df, ["symbol"])
    hourly = summarize(df, ["symbol", "hour_utc"])
    weekday = summarize(df, ["symbol", "weekday"])
    overall.to_csv(output_dir / "market_profile_overall.csv", index=False)
    hourly.to_csv(output_dir / "market_profile_hourly.csv", index=False)
    weekday.to_csv(output_dir / "market_profile_weekday.csv", index=False)
    payload = {
        "rows": int(len(df)),
        "symbols": sorted(df["symbol"].dropna().unique().tolist()),
        "outputs": [
            str(output_dir / "market_profile_overall.csv"),
            str(output_dir / "market_profile_hourly.csv"),
            str(output_dir / "market_profile_weekday.csv"),
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
