#!/usr/bin/env python3
"""Build one deterministic annual FX bar bundle from daily and repair artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

TIMEFRAMES = ("M1", "M5", "M15", "H1")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_files(roots: list[Path], symbol: str, timeframe: str) -> list[Path]:
    expected = f"{symbol}_{timeframe}.csv.gz"
    found: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob(expected):
            if path.is_file() and path.parent.name == timeframe:
                found.add(path.resolve())
    return sorted(found)


def source_priority(path: Path) -> int:
    raw = str(path).lower()
    if "aggregate_repair" in raw or "annual_repair" in raw:
        return 2
    return 1


def values_equal(left: pd.DataFrame, right: pd.DataFrame, columns: list[str]) -> bool:
    if len(left) != len(right):
        return False
    for column in columns:
        a = left[column].reset_index(drop=True)
        b = right[column].reset_index(drop=True)
        if pd.api.types.is_numeric_dtype(a) or pd.api.types.is_numeric_dtype(b):
            av = pd.to_numeric(a, errors="coerce")
            bv = pd.to_numeric(b, errors="coerce")
            if not ((av == bv) | (av.isna() & bv.isna())).all():
                return False
        else:
            if not ((a.astype(str) == b.astype(str)) | (a.isna() & b.isna())).all():
                return False
    return True


def load_timeframe(
    paths: list[Path],
    symbol: str,
    timeframe: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, list[dict[str, Any]], int, int]:
    frames: list[pd.DataFrame] = []
    inputs: list[dict[str, Any]] = []
    for path in paths:
        frame = pd.read_csv(path)
        required = {"timestamp_utc", "symbol"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{path} missing columns: {sorted(missing)}")
        frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True, errors="coerce")
        frame["symbol"] = frame["symbol"].astype(str).str.upper()
        invalid_ts = int(frame["timestamp_utc"].isna().sum())
        if invalid_ts:
            raise ValueError(f"{path} has invalid timestamp rows: {invalid_ts}")
        unexpected_symbols = sorted(set(frame["symbol"]) - {symbol})
        if unexpected_symbols:
            raise ValueError(f"{path} contains unexpected symbols: {unexpected_symbols}")
        frame = frame[(frame["timestamp_utc"] >= start) & (frame["timestamp_utc"] < end)].copy()
        if frame.empty:
            continue
        frame["_source_path"] = str(path)
        frame["_priority"] = source_priority(path)
        frames.append(frame)
        inputs.append(
            {
                "timeframe": timeframe,
                "path": str(path),
                "priority": source_priority(path),
                "rows_in_year": int(len(frame)),
                "start_utc": frame["timestamp_utc"].min().isoformat(),
                "end_utc": frame["timestamp_utc"].max().isoformat(),
                "sha256": sha256_file(path),
            }
        )
    if not frames:
        raise FileNotFoundError(f"no {timeframe} {symbol} bar files found in annual range")

    combined = pd.concat(frames, ignore_index=True, sort=False)
    rows_before = int(len(combined))
    duplicate_rows = combined[combined.duplicated("timestamp_utc", keep=False)].copy()
    conflict_columns = [
        column
        for column in combined.columns
        if column not in {"_source_path", "_priority"}
    ]
    for timestamp, group in duplicate_rows.groupby("timestamp_utc", sort=False):
        max_priority = int(group["_priority"].max())
        preferred = group[group["_priority"] == max_priority]
        if len(preferred) > 1:
            first = preferred.iloc[[0]]
            for idx in range(1, len(preferred)):
                other = preferred.iloc[[idx]]
                if not values_equal(first, other, conflict_columns):
                    sources = preferred["_source_path"].tolist()
                    raise ValueError(
                        f"conflicting same-priority bars for {timeframe} {timestamp}: {sources}"
                    )

    combined = combined.sort_values(["timestamp_utc", "_priority", "_source_path"])
    combined = combined.drop_duplicates("timestamp_utc", keep="last")
    combined = combined.sort_values("timestamp_utc").reset_index(drop=True)
    rows_after = int(len(combined))
    if combined["timestamp_utc"].duplicated().any():
        raise AssertionError(f"duplicate {timeframe} timestamps remain")
    if not combined["timestamp_utc"].is_monotonic_increasing:
        raise AssertionError(f"{timeframe} timestamps are not increasing")

    combined = combined.drop(columns=["_source_path", "_priority"])
    combined["timestamp_utc"] = combined["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return combined, inputs, rows_before, rows_after


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a deterministic annual FX bar bundle.")
    parser.add_argument("--input-root", action="append", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--timeframes", nargs="+", default=list(TIMEFRAMES), choices=TIMEFRAMES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()
    roots = [path.resolve() for path in args.input_root]
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    start = pd.Timestamp(f"{args.year}-01-01T00:00:00Z")
    end = pd.Timestamp(f"{args.year + 1}-01-01T00:00:00Z")

    input_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    bundle_files: list[dict[str, Any]] = []

    for timeframe in args.timeframes:
        paths = discover_files(roots, symbol, timeframe)
        bars, inputs, rows_before, rows_after = load_timeframe(
            paths, symbol, timeframe, start, end
        )
        input_rows.extend(inputs)
        target = output / "bars" / timeframe / f"{symbol}_{timeframe}.csv.gz"
        target.parent.mkdir(parents=True, exist_ok=True)
        bars.to_csv(target, index=False, compression="gzip")

        parsed = pd.to_datetime(bars["timestamp_utc"], utc=True)
        month_counts = parsed.dt.strftime("%Y-%m").value_counts().sort_index()
        for month in [f"{args.year}-{month:02d}" for month in range(1, 13)]:
            monthly_rows.append(
                {
                    "symbol": symbol,
                    "year": args.year,
                    "timeframe": timeframe,
                    "month": month,
                    "rows": int(month_counts.get(month, 0)),
                }
            )
        bundle_files.append(
            {
                "symbol": symbol,
                "year": args.year,
                "timeframe": timeframe,
                "path": str(target.relative_to(output)),
                "input_files": len(paths),
                "rows_before_dedup": rows_before,
                "rows_after_dedup": rows_after,
                "duplicate_rows_removed": rows_before - rows_after,
                "start_utc": parsed.min().isoformat(),
                "end_utc": parsed.max().isoformat(),
                "sha256": sha256_file(target),
            }
        )

    input_manifest = output / "input_bar_files.csv"
    pd.DataFrame(input_rows).sort_values(["timeframe", "path"]).to_csv(input_manifest, index=False)
    monthly_manifest = output / "monthly_bar_rows.csv"
    pd.DataFrame(monthly_rows).to_csv(monthly_manifest, index=False)

    metadata = {
        "symbol": symbol,
        "year": args.year,
        "start_utc": start.isoformat(),
        "end_utc_exclusive": end.isoformat(),
        "input_roots": [str(path) for path in roots],
        "timeframes": list(args.timeframes),
        "priority_rule": "annual_or_aggregate_repair_over_day_bar_then_lexical_path",
        "files": bundle_files,
        "input_bar_files_csv": {
            "path": input_manifest.name,
            "sha256": sha256_file(input_manifest),
        },
        "monthly_bar_rows_csv": {
            "path": monthly_manifest.name,
            "sha256": sha256_file(monthly_manifest),
        },
    }
    metadata_path = output / "annual_bundle_manifest.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
