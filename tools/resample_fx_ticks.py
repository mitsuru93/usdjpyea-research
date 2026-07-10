#!/usr/bin/env python3
"""Resample normalized FX tick CSV.GZ files into M1/M5/M15/H1 bid/ask OHLC bars."""

from __future__ import annotations

import argparse
import hashlib
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

TIMEFRAME_RULES = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "H1": "1h",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_ticks(paths: list[str]) -> pd.DataFrame:
    frames = []
    for raw in paths:
        path = Path(raw)
        frame = pd.read_csv(path)
        frame["_input_path"] = str(path)
        frames.append(frame)
    if not frames:
        raise ValueError("at least one --input is required")
    df = pd.concat(frames, ignore_index=True)
    required = {"timestamp_utc", "symbol", "bid", "ask"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"tick files missing required columns: {sorted(missing)}")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.upper()
    df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
    df["ask"] = pd.to_numeric(df["ask"], errors="coerce")
    df = df.dropna(subset=["timestamp_utc", "symbol", "bid", "ask"])
    if df.empty:
        raise ValueError("no valid ticks after parsing")
    return df.sort_values(["symbol", "timestamp_utc"])


def resample_symbol(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    symbol = str(df["symbol"].iloc[0])
    pip = PIP_SIZE.get(symbol)
    if pip is None:
        raise ValueError(f"unsupported symbol: {symbol}")
    rule = TIMEFRAME_RULES[timeframe]
    indexed = df.set_index("timestamp_utc")
    bid_ohlc = indexed["bid"].resample(rule, label="left", closed="left").ohlc()
    ask_ohlc = indexed["ask"].resample(rule, label="left", closed="left").ohlc()
    tick_count = indexed["bid"].resample(rule, label="left", closed="left").count().rename("tick_count")
    bars = pd.concat({"bid": bid_ohlc, "ask": ask_ohlc}, axis=1)
    bars.columns = [f"{side}_{field}" for side, field in bars.columns]
    bars = bars.join(tick_count)
    bars = bars.dropna(subset=["bid_open", "ask_open", "bid_close", "ask_close"])
    bars = bars.reset_index().rename(columns={"timestamp_utc": "timestamp_utc"})
    bars.insert(1, "symbol", symbol)
    for field in ("open", "high", "low", "close"):
        bars[f"mid_{field}"] = (bars[f"bid_{field}"] + bars[f"ask_{field}"]) / 2.0
        bars[f"spread_{field}_pips"] = (bars[f"ask_{field}"] - bars[f"bid_{field}"]) / pip
    bars["spread_mean_pips"] = bars[["spread_open_pips", "spread_high_pips", "spread_low_pips", "spread_close_pips"]].mean(axis=1)
    bars["source"] = "dukascopy_bi5"
    bars["source_build_id"] = f"dukascopy_bi5_{symbol}_{timeframe}"
    bars["timestamp_utc"] = bars["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return bars


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resample tick CSV.GZ files into bid/ask OHLC bars.")
    parser.add_argument("--input", action="append", required=True, help="Tick CSV or CSV.GZ path. Repeatable.")
    parser.add_argument("--output-dir", required=True, help="Output directory for bars.")
    parser.add_argument("--timeframes", nargs="+", default=["M1", "M5", "M15"], choices=sorted(TIMEFRAME_RULES), help="Derived timeframes.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = load_ticks(args.input)
    records = []
    for timeframe in args.timeframes:
        for symbol, group in df.groupby("symbol", sort=True):
            bars = resample_symbol(group, timeframe=timeframe)
            out_path = output_dir / timeframe / f"{symbol}_{timeframe}.csv.gz"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            bars.to_csv(out_path, index=False, compression="gzip")
            record = {
                "symbol": symbol,
                "timeframe": timeframe,
                "rows": int(len(bars)),
                "output": str(out_path),
                "sha256": sha256_file(out_path),
            }
            records.append(record)
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    manifest = output_dir / "resample_manifest.jsonl"
    manifest.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records) + "\n", encoding="utf-8")
    print(f"wrote manifest: {manifest}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
