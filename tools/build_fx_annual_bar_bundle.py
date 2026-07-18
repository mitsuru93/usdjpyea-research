#!/usr/bin/env python3
"""Build a deterministic annual FX bar bundle from daily and repair artifacts."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd

TIMEFRAMES = ("M1", "M5", "M15", "H1")
CANONICAL_COLUMNS = (
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
    "tick_count",
    "spread_open_pips",
    "spread_high_pips",
    "spread_low_pips",
    "spread_close_pips",
    "spread_mean_pips",
    "mid_open",
    "mid_high",
    "mid_low",
    "mid_close",
    "source",
    "source_build_id",
)
PRICE_COLUMNS = (
    "bid_open", "bid_high", "bid_low", "bid_close",
    "ask_open", "ask_high", "ask_low", "ask_close",
    "mid_open", "mid_high", "mid_low", "mid_close",
)
SPREAD_COLUMNS = (
    "spread_open_pips", "spread_high_pips", "spread_low_pips",
    "spread_close_pips", "spread_mean_pips",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def timeframe_minutes(timeframe: str) -> int:
    return {"M1": 1, "M5": 5, "M15": 15, "H1": 60}[timeframe]


def validate_frame(frame: pd.DataFrame, path: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    missing = set(CANONICAL_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing canonical columns: {sorted(missing)}")
    frame = frame[list(CANONICAL_COLUMNS)].copy()
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True, errors="coerce")
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    invalid_ts = int(frame["timestamp_utc"].isna().sum())
    if invalid_ts:
        raise ValueError(f"{path} has invalid timestamp rows: {invalid_ts}")
    unexpected_symbols = sorted(set(frame["symbol"]) - {symbol})
    if unexpected_symbols:
        raise ValueError(f"{path} contains unexpected symbols: {unexpected_symbols}")

    numeric_columns = list(PRICE_COLUMNS) + list(SPREAD_COLUMNS) + ["tick_count"]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    invalid_numeric = frame[numeric_columns].isna().any(axis=1)
    if invalid_numeric.any():
        raise ValueError(f"{path} has rows with invalid canonical numeric values: {int(invalid_numeric.sum())}")

    minutes = timeframe_minutes(timeframe)
    ts = frame["timestamp_utc"]
    misaligned = (ts.dt.second != 0) | (ts.dt.microsecond != 0)
    if minutes == 60:
        misaligned |= ts.dt.minute != 0
    else:
        misaligned |= (ts.dt.minute % minutes) != 0
    if misaligned.any():
        raise ValueError(f"{path} has timestamp-grid violations: {int(misaligned.sum())}")

    for prefix in ("bid", "ask", "mid"):
        high = frame[f"{prefix}_high"]
        low = frame[f"{prefix}_low"]
        open_ = frame[f"{prefix}_open"]
        close = frame[f"{prefix}_close"]
        invalid_ohlc = (high < low) | (high < open_) | (high < close) | (low > open_) | (low > close)
        if invalid_ohlc.any():
            raise ValueError(f"{path} has invalid {prefix} OHLC rows: {int(invalid_ohlc.sum())}")
    invalid_market = pd.Series(False, index=frame.index)
    for suffix in ("open", "high", "low", "close"):
        invalid_market |= frame[f"ask_{suffix}"] < frame[f"bid_{suffix}"]
    if invalid_market.any():
        raise ValueError(f"{path} has ask below bid rows: {int(invalid_market.sum())}")
    if (frame["tick_count"] < 0).any():
        raise ValueError(f"{path} has negative tick_count")
    if (frame[list(SPREAD_COLUMNS)] < 0).any(axis=None):
        raise ValueError(f"{path} has negative spread values")
    return frame


def rows_equal(left: pd.Series, right: pd.Series, columns: list[str]) -> bool:
    for column in columns:
        a = left[column]
        b = right[column]
        if pd.isna(a) and pd.isna(b):
            continue
        if pd.api.types.is_number(a) or pd.api.types.is_number(b):
            try:
                if float(a) != float(b):
                    return False
            except (TypeError, ValueError):
                if str(a) != str(b):
                    return False
        elif str(a) != str(b):
            return False
    return True


def load_timeframe(
    paths: list[Path],
    symbol: str,
    timeframe: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]], int, int]:
    frames: list[pd.DataFrame] = []
    inputs: list[dict[str, Any]] = []
    for path in paths:
        frame = validate_frame(pd.read_csv(path), path, symbol, timeframe)
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
    duplicate_audit: list[dict[str, Any]] = []
    payload_columns = list(CANONICAL_COLUMNS)
    duplicate_rows = combined[combined.duplicated("timestamp_utc", keep=False)].copy()
    for timestamp, group in duplicate_rows.groupby("timestamp_utc", sort=True):
        max_priority = int(group["_priority"].max())
        min_priority = int(group["_priority"].min())
        preferred = group[group["_priority"] == max_priority].sort_values("_source_path")
        first = preferred.iloc[0]
        for idx in range(1, len(preferred)):
            other = preferred.iloc[idx]
            if not rows_equal(first, other, payload_columns):
                sources = preferred["_source_path"].tolist()
                raise ValueError(
                    f"conflicting same-priority bars for {timeframe} {timestamp}: {sources}"
                )
        resolution = "repair_override" if max_priority > min_priority else "identical_consolidation"
        duplicate_audit.append(
            {
                "timeframe": timeframe,
                "timestamp_utc": timestamp.isoformat(),
                "rows": int(len(group)),
                "preferred_priority": max_priority,
                "lower_priority_rows": int((group["_priority"] < max_priority).sum()),
                "same_priority_rows": int(len(preferred)),
                "resolution": resolution,
                "selected_source": str(preferred.iloc[-1]["_source_path"]),
                "all_sources": "|".join(sorted(group["_source_path"].astype(str))),
            }
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
    combined = combined[list(CANONICAL_COLUMNS)]
    combined["timestamp_utc"] = combined["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return combined, inputs, duplicate_audit, rows_before, rows_after


def canonical_csv_bytes(frame: pd.DataFrame) -> bytes:
    text = io.StringIO(newline="")
    frame.to_csv(
        text,
        index=False,
        columns=list(CANONICAL_COLUMNS),
        float_format="%.17g",
        lineterminator="\n",
    )
    return text.getvalue().encode("utf-8")


def write_deterministic_gzip(payload: bytes, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            compressed.write(payload)


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
    duplicate_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    bundle_files: list[dict[str, Any]] = []

    for timeframe in args.timeframes:
        paths = discover_files(roots, symbol, timeframe)
        bars, inputs, duplicate_audit, rows_before, rows_after = load_timeframe(
            paths, symbol, timeframe, start, end
        )
        input_rows.extend(inputs)
        duplicate_rows.extend(duplicate_audit)
        target = output / "bars" / timeframe / f"{symbol}_{timeframe}.csv.gz"
        payload = canonical_csv_bytes(bars)
        write_deterministic_gzip(payload, target)

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
                "repair_override_timestamps": sum(
                    row["resolution"] == "repair_override" for row in duplicate_audit
                ),
                "identical_duplicate_timestamps": sum(
                    row["resolution"] == "identical_consolidation" for row in duplicate_audit
                ),
                "start_utc": parsed.min().isoformat(),
                "end_utc": parsed.max().isoformat(),
                "canonical_content_sha256": sha256_bytes(payload),
                "gzip_sha256": sha256_file(target),
                "gzip_mtime": 0,
                "column_count": len(CANONICAL_COLUMNS),
                "columns": list(CANONICAL_COLUMNS),
            }
        )

    input_manifest = output / "input_bar_files.csv"
    pd.DataFrame(input_rows).sort_values(["timeframe", "priority", "path"]).to_csv(
        input_manifest, index=False, lineterminator="\n"
    )
    monthly_manifest = output / "monthly_bar_rows.csv"
    pd.DataFrame(monthly_rows).to_csv(monthly_manifest, index=False, lineterminator="\n")
    duplicate_manifest = output / "duplicate_resolution_audit.csv"
    duplicate_frame = pd.DataFrame(duplicate_rows)
    if duplicate_frame.empty:
        duplicate_frame = pd.DataFrame(
            columns=[
                "timeframe", "timestamp_utc", "rows", "preferred_priority",
                "lower_priority_rows", "same_priority_rows", "resolution",
                "selected_source", "all_sources",
            ]
        )
    duplicate_frame.to_csv(duplicate_manifest, index=False, lineterminator="\n")

    metadata = {
        "version": "deterministic_v1",
        "symbol": symbol,
        "year": args.year,
        "start_utc": start.isoformat(),
        "end_utc_exclusive": end.isoformat(),
        "input_roots": [str(path) for path in roots],
        "timeframes": list(args.timeframes),
        "priority_rule": "aggregate_or_annual_repair_over_day_bar; identical_same_priority_consolidated; conflicting_same_priority_hard_fail",
        "serialization": {
            "encoding": "utf-8",
            "line_terminator": "LF",
            "float_format": "%.17g",
            "gzip_compresslevel": 9,
            "gzip_mtime": 0,
            "gzip_filename": "",
        },
        "files": bundle_files,
        "input_bar_files_csv": {
            "path": input_manifest.name,
            "sha256": sha256_file(input_manifest),
        },
        "monthly_bar_rows_csv": {
            "path": monthly_manifest.name,
            "sha256": sha256_file(monthly_manifest),
        },
        "duplicate_resolution_audit_csv": {
            "path": duplicate_manifest.name,
            "sha256": sha256_file(duplicate_manifest),
            "rows": int(len(duplicate_frame)),
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
