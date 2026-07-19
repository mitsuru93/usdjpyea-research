#!/usr/bin/env python3
"""Validate, bar-crosscheck, and package one month of FX tick data.

The output is a deterministic TAR.GZ containing exact Dukascopy BI5 payloads,
deterministic normalized tick CSV.GZ files, and audit metadata. Reconstructed
bars must match the accepted annual bar bundle for the same month.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from download_dukascopy_bi5_ticks import decode_bi5
from download_dukascopy_tick_archive_v1 import normalized_tick_csv_bytes, sha256_file
from resample_fx_ticks import load_ticks, resample_symbol

TIMEFRAMES = ("M1", "M5", "M15", "H1")
SUCCESS = {"downloaded", "exists"}
SOFT_MISSING = {"missing_404", "no_ticks", "market_closed"}
EXPECTED_TICK_COLUMNS = [
    "timestamp_utc",
    "symbol",
    "bid",
    "ask",
    "bid_volume",
    "ask_volume",
    "source",
]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_month(raw: str) -> tuple[dt.datetime, dt.datetime]:
    start = dt.datetime.strptime(raw, "%Y-%m")
    if start.month == 12:
        end = dt.datetime(start.year + 1, 1, 1)
    else:
        end = dt.datetime(start.year, start.month + 1, 1)
    return start, end


def load_final_manifest(path: Path) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
        key = (str(row.get("symbol", "")).upper(), str(row.get("hour_start_utc", "")))
        latest[key] = row
    return [latest[key] for key in sorted(latest)]


def relative_under(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def validate_hour(
    row: dict[str, Any], *, symbol: str, bi5_root: Path, tick_root: Path
) -> dict[str, Any]:
    hour = dt.datetime.strptime(str(row["hour_start_utc"]), "%Y-%m-%dT%H:%M:%SZ")
    bi5_path = Path(str(row["bi5_path"]))
    tick_path = Path(str(row["tick_path"]))
    if not bi5_path.exists() or not tick_path.exists():
        raise FileNotFoundError(f"missing archived hour files: {bi5_path} / {tick_path}")
    bi5_payload = bi5_path.read_bytes()
    tick_gzip = tick_path.read_bytes()
    if tick_gzip[4:8] != b"\x00\x00\x00\x00":
        raise ValueError(f"tick gzip mtime is not zero: {tick_path}")
    tick_content = gzip.decompress(tick_gzip)

    expected_rows = decode_bi5(bi5_payload, symbol=symbol, hour_start=hour)
    expected_content = normalized_tick_csv_bytes(expected_rows, symbol)
    if expected_content != tick_content:
        raise ValueError(f"normalized ticks are not an exact decode of BI5: {hour}")

    frame = pd.read_csv(io.BytesIO(tick_content))
    if list(frame.columns) != EXPECTED_TICK_COLUMNS:
        raise ValueError(f"unexpected tick columns at {hour}: {list(frame.columns)}")
    if len(frame) != len(expected_rows) or len(frame) != int(row["rows"]):
        raise ValueError(f"tick row count mismatch at {hour}")
    parsed = pd.to_datetime(frame["timestamp_utc"], utc=True, errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"invalid timestamps at {hour}")
    lower = pd.Timestamp(hour, tz="UTC")
    upper = lower + pd.Timedelta(hours=1)
    if ((parsed < lower) | (parsed >= upper)).any():
        raise ValueError(f"tick outside source hour at {hour}")
    if not parsed.is_monotonic_increasing:
        raise ValueError(f"ticks not monotonic at {hour}")
    if set(frame["symbol"].astype(str).str.upper()) != {symbol}:
        raise ValueError(f"unexpected symbol at {hour}")
    bid = pd.to_numeric(frame["bid"], errors="coerce")
    ask = pd.to_numeric(frame["ask"], errors="coerce")
    if bid.isna().any() or ask.isna().any() or (ask < bid).any():
        raise ValueError(f"invalid bid/ask at {hour}")

    checks = {
        "bi5_sha256": sha256_bytes(bi5_payload),
        "bi5_bytes": len(bi5_payload),
        "tick_gzip_sha256": sha256_bytes(tick_gzip),
        "tick_gzip_bytes": len(tick_gzip),
        "tick_content_sha256": sha256_bytes(tick_content),
        "tick_content_bytes": len(tick_content),
    }
    for field, actual in checks.items():
        if str(row.get(field)) != str(actual):
            raise ValueError(f"manifest {field} mismatch at {hour}: {row.get(field)} != {actual}")
    return {
        "symbol": symbol,
        "hour_start_utc": row["hour_start_utc"],
        "url": row["url"],
        "status": "downloaded",
        "rows": len(frame),
        "vendor_bi5_archive_path": "vendor_bi5/" + relative_under(bi5_path, bi5_root),
        "normalized_tick_archive_path": "normalized_ticks/" + relative_under(tick_path, tick_root),
        **checks,
        "tick_gzip_mtime": 0,
    }


def compare_bars(
    *, symbol: str, month: str, tick_paths: list[str], accepted_root: Path
) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    start, end = parse_month(month)
    ticks = load_ticks(tick_paths)
    result: dict[str, Any] = {
        "symbol": symbol,
        "month": month,
        "total_ticks": int(len(ticks)),
        "timeframes": {},
        "status": "PASS",
    }
    generated: dict[str, pd.DataFrame] = {}
    for timeframe in TIMEFRAMES:
        candidate = resample_symbol(ticks, timeframe=timeframe)
        accepted_path = accepted_root / "bundle" / "bars" / timeframe / f"{symbol}_{timeframe}.csv.gz"
        if not accepted_path.exists():
            raise FileNotFoundError(f"accepted annual bar missing: {accepted_path}")
        accepted = pd.read_csv(accepted_path)
        accepted_ts = pd.to_datetime(accepted["timestamp_utc"], utc=True, errors="raise")
        lower = pd.Timestamp(start, tz="UTC")
        upper = pd.Timestamp(end, tz="UTC")
        accepted = accepted.loc[(accepted_ts >= lower) & (accepted_ts < upper)].reset_index(drop=True)
        candidate = candidate.reset_index(drop=True)
        if list(candidate.columns) != list(accepted.columns):
            raise ValueError(
                f"{timeframe} columns differ: candidate={list(candidate.columns)} accepted={list(accepted.columns)}"
            )
        if len(candidate) != len(accepted):
            raise ValueError(f"{timeframe} row count differs: {len(candidate)} != {len(accepted)}")

        exact_columns = ["timestamp_utc", "symbol", "source", "source_build_id", "tick_count"]
        for column in exact_columns:
            left = candidate[column].astype(str).reset_index(drop=True)
            right = accepted[column].astype(str).reset_index(drop=True)
            if not left.equals(right):
                mismatch = int((left != right).sum())
                raise ValueError(f"{timeframe} exact column mismatch {column}: {mismatch}")

        numeric_columns = [c for c in candidate.columns if c not in exact_columns]
        max_diff: dict[str, float] = {}
        for column in numeric_columns:
            left = pd.to_numeric(candidate[column], errors="raise").to_numpy(dtype=float)
            right = pd.to_numeric(accepted[column], errors="raise").to_numpy(dtype=float)
            diff = float(np.max(np.abs(left - right))) if len(left) else 0.0
            max_diff[column] = diff
            if not np.allclose(left, right, rtol=0.0, atol=1e-10, equal_nan=True):
                raise ValueError(f"{timeframe} numeric mismatch {column}, max_abs_diff={diff}")
        result["timeframes"][timeframe] = {
            "rows": int(len(candidate)),
            "accepted_rows": int(len(accepted)),
            "max_abs_diff": max_diff,
            "status": "PASS",
        }
        generated[timeframe] = candidate
    return result, generated


def add_bytes(tar: tarfile.TarFile, arcname: str, payload: bytes) -> None:
    info = tarfile.TarInfo(arcname)
    info.size = len(payload)
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(payload))


def add_file(tar: tarfile.TarFile, arcname: str, path: Path) -> None:
    with path.open("rb") as fh:
        payload = fh.read()
    add_bytes(tar, arcname, payload)


def create_deterministic_tar_gz(
    *, asset_path: Path, file_entries: list[tuple[str, Path]], byte_entries: list[tuple[str, bytes]]
) -> None:
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw_tar = Path(tmp) / "archive.tar"
        with tarfile.open(raw_tar, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for arcname, path in sorted(file_entries, key=lambda x: x[0]):
                add_file(tar, arcname, path)
            for arcname, payload in sorted(byte_entries, key=lambda x: x[0]):
                add_bytes(tar, arcname, payload)
        with raw_tar.open("rb") as source, asset_path.open("wb") as target:
            with gzip.GzipFile(filename="", mode="wb", fileobj=target, compresslevel=9, mtime=0) as zipped:
                shutil.copyfileobj(source, zipped, length=1024 * 1024)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build one verified monthly FX tick archive.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--download-summary", required=True)
    parser.add_argument("--bi5-root", required=True)
    parser.add_argument("--tick-root", required=True)
    parser.add_argument("--accepted-annual-root", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()
    month = args.month
    start, end = parse_month(month)
    manifest_path = Path(args.manifest)
    summary_path = Path(args.download_summary)
    bi5_root = Path(args.bi5_root)
    tick_root = Path(args.tick_root)
    accepted_root = Path(args.accepted_annual_root)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    records = load_final_manifest(manifest_path)
    expected_hours = int((end - start).total_seconds() // 3600)
    if len(records) != expected_hours:
        raise ValueError(f"manifest hour count differs: {len(records)} != {expected_hours}")
    expected_keys = {
        (symbol, (start + dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        for i in range(expected_hours)
    }
    actual_keys = {(str(r.get("symbol", "")).upper(), str(r.get("hour_start_utc", ""))) for r in records}
    if actual_keys != expected_keys:
        raise ValueError("manifest does not contain exactly one final state for every calendar hour")
    terminal_errors = [r for r in records if str(r.get("status")) == "error"]
    unexpected = [r for r in records if str(r.get("status")) not in SUCCESS | SOFT_MISSING]
    if terminal_errors or unexpected:
        raise ValueError(f"terminal or unexpected manifest states: errors={len(terminal_errors)} unexpected={len(unexpected)}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    required_summary = {
        "expected_records": expected_hours,
        "observed_records": expected_hours,
        "unobserved_records": 0,
        "hard_error_records": 0,
        "effective_coverage": 1.0,
        "expected_records_mode": "calendar",
    }
    for key, expected in required_summary.items():
        if summary.get(key) != expected:
            raise ValueError(f"download summary mismatch {key}: {summary.get(key)} != {expected}")

    final_rows: list[dict[str, Any]] = []
    tick_paths: list[str] = []
    files: list[tuple[str, Path]] = []
    total_ticks = 0
    for row in records:
        status = str(row["status"])
        if status in SUCCESS:
            checked = validate_hour(row, symbol=symbol, bi5_root=bi5_root, tick_root=tick_root)
            final_rows.append(checked)
            total_ticks += int(checked["rows"])
            bi5_path = bi5_root / checked["vendor_bi5_archive_path"].removeprefix("vendor_bi5/")
            tick_path = tick_root / checked["normalized_tick_archive_path"].removeprefix("normalized_ticks/")
            tick_paths.append(str(tick_path))
            files.append((str(checked["vendor_bi5_archive_path"]), bi5_path))
            files.append((str(checked["normalized_tick_archive_path"]), tick_path))
        else:
            final_rows.append(
                {
                    "symbol": symbol,
                    "hour_start_utc": row["hour_start_utc"],
                    "url": row["url"],
                    "status": status,
                    "rows": 0,
                }
            )

    bar_equivalence, _generated = compare_bars(
        symbol=symbol,
        month=month,
        tick_paths=sorted(tick_paths),
        accepted_root=accepted_root,
    )
    if int(bar_equivalence["total_ticks"]) != total_ticks:
        raise ValueError("tick count differs between hourly validation and monthly load")

    final_manifest_text = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) for row in final_rows
    ) + "\n"
    metadata = {
        "version": "v1",
        "status": "verified",
        "symbol": symbol,
        "month": month,
        "source": "Dukascopy public hourly BI5",
        "representations": ["exact_vendor_bi5", "deterministic_normalized_bid_ask_tick_csv_gz"],
        "calendar_hours": expected_hours,
        "downloaded_hours": sum(str(r["status"]) in SUCCESS for r in records),
        "soft_missing_hours": sum(str(r["status"]) in SOFT_MISSING for r in records),
        "total_ticks": total_ticks,
        "normalized_tick_schema": EXPECTED_TICK_COLUMNS,
        "bar_equivalence": bar_equivalence,
        "accepted_bar_source": "eurusd-2024-source-artifact-id-8441596981.zip",
        "mt4_boundary": "The normalized ticks are conversion input. MT4 still requires an explicit FXT/HST or compatible tick-import conversion step.",
    }
    readme = f"""# {symbol} {month} Tick Archive v1\n\nThis package contains exact Dukascopy BI5 payloads and deterministic normalized bid/ask ticks.\n\n- Month: {month}\n- Total ticks: {total_ticks}\n- Bar equivalence to accepted 2024 annual bundle: PASS for M1, M5, M15 and H1\n- MT4 use: convert `normalized_ticks/` into the selected MT4 tick-testing format; these files are not broker-native Rakuten ticks.\n"""
    byte_entries = [
        ("audit/download_manifest.final.jsonl", final_manifest_text.encode("utf-8")),
        ("audit/download_summary.json", (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8")),
        ("audit/bar_equivalence.json", (json.dumps(bar_equivalence, indent=2, sort_keys=True) + "\n").encode("utf-8")),
        ("audit/month_metadata.json", (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")),
        ("README.md", readme.encode("utf-8")),
    ]
    asset_name = f"{symbol.lower()}-{month}-ticks-v1.tar.gz"
    asset_path = output / asset_name
    create_deterministic_tar_gz(asset_path=asset_path, file_entries=files, byte_entries=byte_entries)
    receipt = {
        "version": "v1",
        "status": "verified",
        "symbol": symbol,
        "month": month,
        "asset_name": asset_name,
        "asset_size_in_bytes": asset_path.stat().st_size,
        "asset_sha256": sha256_file(asset_path),
        "calendar_hours": expected_hours,
        "downloaded_hours": metadata["downloaded_hours"],
        "soft_missing_hours": metadata["soft_missing_hours"],
        "total_ticks": total_ticks,
        "bar_equivalence_status": bar_equivalence["status"],
        "timeframe_rows": {tf: bar_equivalence["timeframes"][tf]["rows"] for tf in TIMEFRAMES},
    }
    receipt_path = output / f"{symbol.lower()}-{month}-ticks-receipt-v1.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
