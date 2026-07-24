#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path

import pandas as pd

TIMEFRAMES = {"m5": "5min", "m15": "15min", "m30": "30min", "h1": "1h", "h4": "4h"}
FIELDS = [
    "time",
    "bid_open", "bid_high", "bid_low", "bid_close",
    "ask_open", "ask_high", "ask_low", "ask_close",
    "mid_open", "mid_high", "mid_low", "mid_close",
    "tick_count", "spread_open", "spread_mean", "spread_max",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_deterministic_gzip_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=1) as gz:
            with io.TextIOWrapper(gz, encoding="utf-8", newline="") as text:
                df.to_csv(
                    text,
                    index=False,
                    columns=FIELDS,
                    date_format="%Y-%m-%d %H:%M:%S",
                    float_format="%.9f",
                    lineterminator="\n",
                )


def read_bar_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["time"], date_format="%Y-%m-%d %H:%M:%S")
    if list(df.columns) != FIELDS:
        raise RuntimeError(f"unexpected bar columns in {path.name}: {list(df.columns)}")
    df["tick_count"] = df["tick_count"].astype("int64")
    if not df["time"].is_monotonic_increasing or df["time"].duplicated().any():
        raise RuntimeError(f"invalid timestamp order in {path.name}")
    return df


def aggregate_ticks_to_m1(source: Path, year: int, month: int) -> tuple[pd.DataFrame, int]:
    df = pd.read_csv(
        source,
        usecols=["datetime_utc", "bid", "ask"],
        dtype={"bid": "float64", "ask": "float64"},
    )
    if df.empty:
        raise RuntimeError(f"no ticks in {source.name}")
    df["datetime_utc"] = pd.to_datetime(
        df["datetime_utc"], format="%Y.%m.%d %H:%M:%S.%f", errors="raise"
    )
    if not df["datetime_utc"].is_monotonic_increasing:
        raise RuntimeError(f"non-monotonic tick timestamps in {source.name}")
    if not ((df["datetime_utc"].dt.year == year) & (df["datetime_utc"].dt.month == month)).all():
        raise RuntimeError(f"out-of-month tick in {source.name}")
    if (df["ask"] < df["bid"]).any():
        raise RuntimeError(f"negative spread in {source.name}")

    df["time"] = df["datetime_utc"].dt.floor("min")
    df["mid"] = (df["bid"] + df["ask"]) / 2.0
    df["spread"] = df["ask"] - df["bid"]
    g = df.groupby("time", sort=True, observed=True)
    out = g.agg(
        bid_open=("bid", "first"), bid_high=("bid", "max"), bid_low=("bid", "min"), bid_close=("bid", "last"),
        ask_open=("ask", "first"), ask_high=("ask", "max"), ask_low=("ask", "min"), ask_close=("ask", "last"),
        mid_open=("mid", "first"), mid_high=("mid", "max"), mid_low=("mid", "min"), mid_close=("mid", "last"),
        tick_count=("bid", "size"), spread_open=("spread", "first"), spread_mean=("spread", "mean"), spread_max=("spread", "max"),
    ).reset_index()
    out["tick_count"] = out["tick_count"].astype("int64")
    return out[FIELDS], len(df)


def aggregate_bars(source: pd.DataFrame, freq: str) -> pd.DataFrame:
    df = source.copy()
    df["bucket"] = df["time"].dt.floor(freq)
    df["spread_weighted"] = df["spread_mean"] * df["tick_count"]
    g = df.groupby("bucket", sort=True, observed=True)
    out = g.agg(
        bid_open=("bid_open", "first"), bid_high=("bid_high", "max"), bid_low=("bid_low", "min"), bid_close=("bid_close", "last"),
        ask_open=("ask_open", "first"), ask_high=("ask_high", "max"), ask_low=("ask_low", "min"), ask_close=("ask_close", "last"),
        mid_open=("mid_open", "first"), mid_high=("mid_high", "max"), mid_low=("mid_low", "min"), mid_close=("mid_close", "last"),
        tick_count=("tick_count", "sum"), spread_open=("spread_open", "first"), spread_weighted=("spread_weighted", "sum"), spread_max=("spread_max", "max"),
    ).reset_index().rename(columns={"bucket": "time"})
    out["spread_mean"] = out["spread_weighted"] / out["tick_count"]
    out.drop(columns=["spread_weighted"], inplace=True)
    out["tick_count"] = out["tick_count"].astype("int64")
    return out[FIELDS]


def asset_meta(path: Path, df: pd.DataFrame) -> dict:
    return {
        "asset": path.name,
        "rows": int(len(df)),
        "sha256": sha256(path),
        "first_time_utc": df.iloc[0]["time"].isoformat(sep=" "),
        "last_time_utc": df.iloc[-1]["time"].isoformat(sep=" "),
    }


def build_month(args: argparse.Namespace) -> None:
    source = args.input_file
    expected_name = f"USDJPY-{args.year}-{args.month:02d}-mt4-tick-import-v1.csv.gz"
    if source.name != expected_name:
        raise RuntimeError(f"expected source name {expected_name}, got {source.name}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    m1, tick_rows = aggregate_ticks_to_m1(source, args.year, args.month)
    if tick_rows != args.expected_tick_rows:
        raise RuntimeError(f"expected {args.expected_tick_rows} ticks, got {tick_rows}")

    m1_path = args.output_dir / f"USDJPY-{args.year}-{args.month:02d}-m1-derived-bars-v1.csv.gz"
    write_deterministic_gzip_csv(m1, m1_path)
    m5 = aggregate_bars(m1, "5min")
    m5_path = args.output_dir / f"USDJPY-{args.year}-{args.month:02d}-m5-derived-bars-v1.csv.gz"
    write_deterministic_gzip_csv(m5, m5_path)

    month_receipt = {
        "schema_version": "usdjpy_2024_derived_bars_month_receipt_v1",
        "accepted": True,
        "year": args.year,
        "month": args.month,
        "source_release_tag": args.source_release_tag,
        "source_asset": source.name,
        "source_sha256": sha256(source),
        "tick_rows": tick_rows,
        "m1": asset_meta(m1_path, m1),
        "m5": asset_meta(m5_path, m5),
    }
    receipt_path = args.output_dir / f"USDJPY-{args.year}-{args.month:02d}-derived-bars-v1.receipt.json"
    receipt_path.write_text(json.dumps(month_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"accepted": True, "month": args.month, "tick_rows": tick_rows, "m1_rows": len(m1), "m5_rows": len(m5)}, sort_keys=True))


def write_package_docs(output_dir: Path, year: int, manifest: dict) -> None:
    readme_text = f"""# USDJPY {year} Derived Bars v1

Deterministic OHLC bars derived from the durable GitHub Release `usdjpy-{year}-mt4-tick-import-v1`.

## Time and boundary contract

- Timestamp timezone: UTC.
- Bars are left-closed and right-open: `[bar_open, next_bar_open)`.
- M5/M15/M30 align to UTC minute multiples; H1 aligns to UTC hour; H4 aligns to UTC hours 00/04/08/12/16/20.
- No synthetic empty bars are inserted.
- Bid, Ask and midpoint OHLC are retained.
- `spread_mean` is tick-weighted when bars are aggregated.
- Gzip output is deterministic (`mtime=0`).

## Assets

- Monthly M1 and M5 files.
- Annual M1, M5, M15, M30, H1 and H4 files.
- Manifest and `SHA256SUMS`.

The source is Dukascopy public Bid/Ask ticks. It reproduces the accepted 2024 USDJPY market series, but it is not Rakuten quote history.
"""
    (output_dir / "README.md").write_text(readme_text, encoding="utf-8")
    manifest_path = output_dir / f"USDJPY-{year}-derived-bars-v1.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksum_lines = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            checksum_lines.append(f"{sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")


def combine(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    monthly_m1 = []
    monthly_meta = []
    total_ticks = 0
    for month in range(1, 13):
        receipt_path = args.input_dir / f"USDJPY-{args.year}-{month:02d}-derived-bars-v1.receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not receipt.get("accepted") or receipt["month"] != month or receipt["year"] != args.year:
            raise RuntimeError(f"invalid month receipt {receipt_path.name}")
        m1_source = args.input_dir / receipt["m1"]["asset"]
        m5_source = args.input_dir / receipt["m5"]["asset"]
        if sha256(m1_source) != receipt["m1"]["sha256"] or sha256(m5_source) != receipt["m5"]["sha256"]:
            raise RuntimeError(f"monthly output digest mismatch for {month:02d}")
        m1 = read_bar_csv(m1_source)
        if len(m1) != receipt["m1"]["rows"]:
            raise RuntimeError(f"monthly M1 row mismatch for {month:02d}")
        monthly_m1.append(m1)
        total_ticks += int(receipt["tick_rows"])
        monthly_meta.append(receipt)
        for source in (m1_source, m5_source):
            target = args.output_dir / source.name
            target.write_bytes(source.read_bytes())

    if total_ticks != args.expected_tick_rows:
        raise RuntimeError(f"expected {args.expected_tick_rows} ticks, got {total_ticks}")
    annual_m1 = pd.concat(monthly_m1, ignore_index=True).sort_values("time", kind="stable").reset_index(drop=True)
    if annual_m1["time"].duplicated().any() or not annual_m1["time"].is_monotonic_increasing:
        raise RuntimeError("invalid annual M1 timestamp order")
    if len(annual_m1) != args.expected_m1_rows:
        raise RuntimeError(f"expected {args.expected_m1_rows} M1 bars, got {len(annual_m1)}")

    annual = {}
    annual_m1_path = args.output_dir / f"USDJPY-{args.year}-m1-derived-bars-v1.csv.gz"
    write_deterministic_gzip_csv(annual_m1, annual_m1_path)
    annual["m1"] = asset_meta(annual_m1_path, annual_m1)
    for timeframe, freq in TIMEFRAMES.items():
        bars = aggregate_bars(annual_m1, freq)
        path = args.output_dir / f"USDJPY-{args.year}-{timeframe}-derived-bars-v1.csv.gz"
        write_deterministic_gzip_csv(bars, path)
        annual[timeframe] = asset_meta(path, bars)

    manifest = {
        "schema_version": "usdjpy_2024_derived_bars_manifest_v1",
        "accepted": True,
        "symbol": "USDJPY",
        "year": args.year,
        "source_release_tag": args.source_release_tag,
        "output_release_tag": args.output_release_tag,
        "source_format": "UTC Bid/Ask tick CSV gzip",
        "source_tick_rows": total_ticks,
        "bar_timezone": "UTC",
        "bar_boundary": "left_closed_right_open",
        "empty_bar_policy": "omit",
        "price_columns": "Bid Ask Mid OHLC",
        "statistics": ["tick_count", "spread_open", "tick_weighted_spread_mean", "spread_max"],
        "generator": "tools/build_usdjpy_2024_derived_bars_v1.py",
        "first_time_utc": annual["m1"]["first_time_utc"],
        "last_time_utc": annual["m1"]["last_time_utc"],
        "annual": annual,
        "months": monthly_meta,
    }
    write_package_docs(args.output_dir, args.year, manifest)
    for path in args.output_dir.glob("*.csv.gz"):
        with gzip.open(path, "rb") as f:
            while f.read(1024 * 1024):
                pass
    print(json.dumps({"accepted": True, "tick_rows": total_ticks, "annual_rows": {k: v["rows"] for k, v in annual.items()}, "asset_count": len(list(args.output_dir.iterdir()))}, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    month = sub.add_parser("build-month")
    month.add_argument("--input-file", type=Path, required=True)
    month.add_argument("--output-dir", type=Path, required=True)
    month.add_argument("--year", type=int, default=2024)
    month.add_argument("--month", type=int, required=True)
    month.add_argument("--expected-tick-rows", type=int, required=True)
    month.add_argument("--source-release-tag", default="usdjpy-2024-mt4-tick-import-v1")

    combined = sub.add_parser("combine")
    combined.add_argument("--input-dir", type=Path, required=True)
    combined.add_argument("--output-dir", type=Path, required=True)
    combined.add_argument("--year", type=int, default=2024)
    combined.add_argument("--expected-tick-rows", type=int, default=40_969_081)
    combined.add_argument("--expected-m1-rows", type=int, default=373_383)
    combined.add_argument("--source-release-tag", default="usdjpy-2024-mt4-tick-import-v1")
    combined.add_argument("--output-release-tag", default="usdjpy-2024-derived-bars-v1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "build-month":
        build_month(args)
    else:
        combine(args)


if __name__ == "__main__":
    main()
