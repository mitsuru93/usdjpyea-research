#!/usr/bin/env python3
"""Validate normalized/resampled FX bar artifacts before research use."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REQUIRED = {
    "timestamp_utc",
    "symbol",
    "bid_open",
    "bid_high",
    "bid_low",
    "bid_close",
    "ask_open",
    "ask_high",
    "ask_low",
    "ask_close",
    "spread_open_pips",
    "spread_high_pips",
    "spread_low_pips",
    "spread_close_pips",
    "spread_mean_pips",
    "tick_count",
}


def validate_one(path: Path) -> dict[str, object]:
    df = pd.read_csv(path)
    missing = sorted(REQUIRED - set(df.columns))
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    if df.empty:
        raise ValueError(f"{path}: empty file")

    numeric_cols = [c for c in REQUIRED if c not in {"timestamp_utc", "symbol"}]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[numeric_cols].isna().any().any():
        bad = df[numeric_cols].isna().sum()
        raise ValueError(f"{path}: numeric nulls {bad[bad > 0].to_dict()}")

    ts = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    if ts.isna().any():
        raise ValueError(f"{path}: invalid timestamps={int(ts.isna().sum())}")
    duplicate_ts = int(ts.duplicated().sum())
    if duplicate_ts:
        raise ValueError(f"{path}: duplicate timestamps={duplicate_ts}")
    if not ts.is_monotonic_increasing:
        raise ValueError(f"{path}: timestamps are not monotonic")

    checks = {
        "bid_ohlc": (df["bid_high"] >= df[["bid_open", "bid_close", "bid_low"]].max(axis=1))
        & (df["bid_low"] <= df[["bid_open", "bid_close", "bid_high"]].min(axis=1)),
        "ask_ohlc": (df["ask_high"] >= df[["ask_open", "ask_close", "ask_low"]].max(axis=1))
        & (df["ask_low"] <= df[["ask_open", "ask_close", "ask_high"]].min(axis=1)),
        "spread_nonnegative": df["spread_low_pips"] >= 0,
        "spread_bounds": (df["spread_high_pips"] >= df["spread_low_pips"])
        & (df["spread_mean_pips"] >= df["spread_low_pips"] - 1e-12)
        & (df["spread_mean_pips"] <= df["spread_high_pips"] + 1e-12)
        & (df["spread_open_pips"] >= df["spread_low_pips"] - 1e-12)
        & (df["spread_open_pips"] <= df["spread_high_pips"] + 1e-12)
        & (df["spread_close_pips"] >= df["spread_low_pips"] - 1e-12)
        & (df["spread_close_pips"] <= df["spread_high_pips"] + 1e-12),
        "tick_count_positive": df["tick_count"] > 0,
    }
    failures = {name: int((~mask).sum()) for name, mask in checks.items() if (~mask).any()}
    if failures:
        raise ValueError(f"{path}: validation failures {failures}")

    return {
        "path": str(path),
        "rows": int(len(df)),
        "symbol": sorted(df["symbol"].astype(str).unique().tolist()),
        "start": ts.min().isoformat(),
        "end": ts.max().isoformat(),
        "median_spread_pips": float(df["spread_mean_pips"].median()),
        "p90_spread_pips": float(df["spread_mean_pips"].quantile(0.90)),
        "max_spread_pips": float(df["spread_high_pips"].max()),
        "min_tick_count": int(df["tick_count"].min()),
        "status": "ok",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate FX bar artifacts.")
    parser.add_argument("--input", action="append", required=True, help="CSV or CSV.GZ path. Repeatable.")
    parser.add_argument("--output", required=True, help="JSON output path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = [validate_one(Path(raw)) for raw in args.input]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"files": records, "file_count": len(records), "status": "ok"}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
