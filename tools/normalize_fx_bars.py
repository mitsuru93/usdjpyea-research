#!/usr/bin/env python3
"""Normalize public FX OHLC/Bid-Ask CSV files into the research M1 contract.

The normalizer accepts either bid/ask OHLC columns or mid-only OHLC columns.
It does not assume a vendor-specific column order unless --format is specified.
"""

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

MID_ALIASES = {
    "timestamp": ["timestamp", "datetime", "time", "timestamp_utc", "date_time"],
    "open": ["open", "Open", "bid_open", "mid_open"],
    "high": ["high", "High", "bid_high", "mid_high"],
    "low": ["low", "Low", "bid_low", "mid_low"],
    "close": ["close", "Close", "bid_close", "mid_close"],
    "volume": ["volume", "Volume", "tick_volume", "vol"],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def first_existing(df: pd.DataFrame, names: list[str]) -> str | None:
    cols = set(df.columns)
    for name in names:
        if name in cols:
            return name
    return None


def read_source(path: Path, fmt: str) -> pd.DataFrame:
    if fmt == "histdata_m1_csv_no_header":
        return pd.read_csv(
            path,
            header=None,
            names=["date", "time", "open", "high", "low", "close", "volume"],
        )
    return pd.read_csv(path)


def normalize_timestamp(df: pd.DataFrame, fmt: str, timezone: str) -> pd.Series:
    if fmt == "histdata_m1_csv_no_header":
        raw = df["date"].astype(str) + " " + df["time"].astype(str)
        ts = pd.to_datetime(raw, format="%Y.%m.%d %H:%M", errors="coerce")
    else:
        col = first_existing(df, MID_ALIASES["timestamp"])
        if col is None:
            raise ValueError("timestamp column not found")
        ts = pd.to_datetime(df[col], errors="coerce")
    if timezone.upper() == "UTC":
        if getattr(ts.dt, "tz", None) is None:
            return ts.dt.tz_localize("UTC")
        return ts.dt.tz_convert("UTC")
    if getattr(ts.dt, "tz", None) is None:
        return ts.dt.tz_localize(timezone).dt.tz_convert("UTC")
    return ts.dt.tz_convert("UTC")


def pick_numeric(df: pd.DataFrame, aliases: list[str], required: bool = True) -> pd.Series | None:
    col = first_existing(df, aliases)
    if col is None:
        if required:
            raise ValueError(f"missing required column from aliases: {aliases}")
        return None
    return pd.to_numeric(df[col], errors="coerce")


def normalize_mid_only(df: pd.DataFrame, symbol: str, source: str, build_id: str, fmt: str, timezone: str) -> pd.DataFrame:
    out = pd.DataFrame()
    out["timestamp_utc"] = normalize_timestamp(df, fmt=fmt, timezone=timezone).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out["symbol"] = symbol
    out["open"] = pick_numeric(df, MID_ALIASES["open"])
    out["high"] = pick_numeric(df, MID_ALIASES["high"])
    out["low"] = pick_numeric(df, MID_ALIASES["low"])
    out["close"] = pick_numeric(df, MID_ALIASES["close"])
    volume = pick_numeric(df, MID_ALIASES["volume"], required=False)
    out["volume"] = volume if volume is not None else pd.NA
    out["source"] = source
    out["source_build_id"] = build_id
    return out.dropna(subset=["timestamp_utc", "open", "high", "low", "close"])


def normalize_bid_ask(df: pd.DataFrame, symbol: str, source: str, build_id: str, fmt: str, timezone: str) -> pd.DataFrame:
    pip = PIP_SIZE[symbol]
    out = pd.DataFrame()
    out["timestamp_utc"] = normalize_timestamp(df, fmt=fmt, timezone=timezone).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out["symbol"] = symbol
    for prefix in ("bid", "ask"):
        for field in ("open", "high", "low", "close"):
            out[f"{prefix}_{field}"] = pick_numeric(df, [f"{prefix}_{field}", f"{prefix.capitalize()}_{field.capitalize()}"])
    for field in ("open", "high", "low", "close"):
        out[f"mid_{field}"] = (out[f"bid_{field}"] + out[f"ask_{field}"]) / 2.0
        out[f"spread_{field}_pips"] = (out[f"ask_{field}"] - out[f"bid_{field}"]) / pip
    out["spread_mean_pips"] = out[["spread_open_pips", "spread_high_pips", "spread_low_pips", "spread_close_pips"]].mean(axis=1)
    out["source"] = source
    out["source_build_id"] = build_id
    return out.dropna(subset=["timestamp_utc", "bid_open", "ask_open", "mid_close"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize public FX bars into the research schema.")
    parser.add_argument("--input", required=True, help="Input CSV path.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    parser.add_argument("--symbol", required=True, choices=sorted(PIP_SIZE), help="FX symbol.")
    parser.add_argument("--source", required=True, help="Source identifier, e.g. histdata or dukascopy_export.")
    parser.add_argument("--format", default="auto_header_csv", choices=["auto_header_csv", "histdata_m1_csv_no_header"], help="Input format.")
    parser.add_argument("--timezone", default="UTC", help="Timezone of naive input timestamps.")
    parser.add_argument("--schema", default="auto", choices=["auto", "mid_only", "bid_ask"], help="Output schema detection/choice.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    source_hash = sha256_file(input_path)[:16]
    build_id = f"{args.source}_{args.symbol.upper()}_{source_hash}"
    df = read_source(input_path, args.format)
    has_bid_ask = {"bid_open", "ask_open", "bid_close", "ask_close"}.issubset(set(df.columns))
    if args.schema == "bid_ask" or (args.schema == "auto" and has_bid_ask):
        out = normalize_bid_ask(df, args.symbol.upper(), args.source, build_id, args.format, args.timezone)
    else:
        out = normalize_mid_only(df, args.symbol.upper(), args.source, build_id, args.format, args.timezone)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    meta = {
        "input": str(input_path),
        "input_sha256": sha256_file(input_path),
        "output": str(output_path),
        "output_sha256": sha256_file(output_path),
        "rows": int(len(out)),
        "symbol": args.symbol.upper(),
        "source": args.source,
        "source_build_id": build_id,
        "schema": "bid_ask" if "bid_open" in out.columns else "mid_only",
    }
    print(json.dumps(meta, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
