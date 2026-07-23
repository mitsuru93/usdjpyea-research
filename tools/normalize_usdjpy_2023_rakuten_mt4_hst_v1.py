#!/usr/bin/env python3
"""Normalize accepted Rakuten MT4 USDJPY 2023 M1 HST bars to UTC.

The source clock is GMT+2 in standard time and GMT+3 in summer time. This
normalizer freezes the Europe/EET-EEST transition rule and fails on ambiguous
or nonexistent local server timestamps instead of guessing.
"""

from __future__ import annotations

import argparse
import calendar
import gzip
import hashlib
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def last_sunday_utc(year: int, month: int) -> datetime:
    day = calendar.monthrange(year, month)[1]
    value = datetime(year, month, day, tzinfo=timezone.utc)
    while value.weekday() != 6:
        value -= timedelta(days=1)
    return value


def write_gzip_csv(frame: pd.DataFrame, path: Path) -> None:
    payload = frame.to_csv(
        index=False, lineterminator="\n", float_format="%.5f"
    ).encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9
        ) as compressed:
            compressed.write(payload)


def load_artifact(path: Path) -> tuple[pd.DataFrame, dict]:
    m1_name = "tester/usdjpy_2023_m1_mt4_server_v1.csv"
    manifest_name = "tester/usdjpy_2023_mt4_hst_manifest_v1.json"
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = [x for x in (m1_name, manifest_name) if x not in names]
        if missing:
            raise RuntimeError(f"artifact missing required files: {missing}")
        frame = pd.read_csv(io.BytesIO(archive.read(m1_name)))
        manifest = json.loads(archive.read(manifest_name).decode("utf-8-sig"))
    return frame, manifest


def normalize(frame: pd.DataFrame, year: int) -> tuple[pd.DataFrame, dict]:
    required = {
        "timestamp_mt4_server", "open", "high", "low", "close",
        "volume", "spread", "real_volume",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"M1 source missing columns: {missing}")

    server = pd.to_datetime(
        frame["timestamp_mt4_server"],
        format="%Y-%m-%dT%H:%M:%S",
        errors="raise",
    )
    dst_start = pd.Timestamp(last_sunday_utc(year, 3).replace(hour=1))
    dst_end = pd.Timestamp(last_sunday_utc(year, 10).replace(hour=1))

    standard_utc = (server - pd.Timedelta(hours=2)).dt.tz_localize("UTC")
    summer_utc = (server - pd.Timedelta(hours=3)).dt.tz_localize("UTC")
    summer_valid = (summer_utc >= dst_start) & (summer_utc < dst_end)
    standard_valid = ~(
        (standard_utc >= dst_start) & (standard_utc < dst_end)
    )
    ambiguous = summer_valid & standard_valid
    nonexistent = ~summer_valid & ~standard_valid
    if bool(ambiguous.any()) or bool(nonexistent.any()):
        bad = frame.loc[
            ambiguous | nonexistent, "timestamp_mt4_server"
        ].head(20).tolist()
        raise RuntimeError(
            "ambiguous/nonexistent MT4 server timestamps: " + repr(bad)
        )

    offset = pd.Series(2, index=frame.index, dtype="int64")
    offset.loc[summer_valid] = 3
    utc_ns = standard_utc.astype("int64")
    utc_ns.loc[summer_valid] = summer_utc.loc[summer_valid].astype("int64")
    utc = pd.to_datetime(utc_ns, utc=True)

    result = pd.DataFrame({
        "timestamp_utc": utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timestamp_mt4_server": frame["timestamp_mt4_server"],
        "server_utc_offset_hours": offset,
        "open": frame["open"].astype(float),
        "high": frame["high"].astype(float),
        "low": frame["low"].astype(float),
        "close": frame["close"].astype(float),
        "volume": frame["volume"].astype("int64"),
        "spread": frame["spread"].astype("int64"),
        "real_volume": frame["real_volume"].astype("int64"),
    })

    timestamp = pd.to_datetime(result["timestamp_utc"], utc=True)
    duplicates = int(timestamp.duplicated().sum())
    nonascending = int((timestamp.diff().dt.total_seconds() <= 0).sum())
    invalid_ohlc = int((~(
        (result["high"] >= result[["open", "close", "low"]].max(axis=1))
        & (result["low"] <= result[["open", "close", "high"]].min(axis=1))
    )).sum())
    if duplicates or nonascending or invalid_ohlc:
        raise RuntimeError(
            f"M1 validation failed: duplicates={duplicates}, "
            f"nonascending={nonascending}, invalid_ohlc={invalid_ohlc}"
        )

    diagnostics = {
        "dst_start_utc": dst_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dst_end_utc": dst_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "offset_2_records": int((offset == 2).sum()),
        "offset_3_records": int((offset == 3).sum()),
        "ambiguous_server_timestamps": int(ambiguous.sum()),
        "nonexistent_server_timestamps": int(nonexistent.sum()),
        "duplicate_timestamps": duplicates,
        "nonascending_timestamps": nonascending,
        "invalid_ohlc_records": invalid_ohlc,
    }
    return result, diagnostics


def derive_m15(m1: pd.DataFrame) -> pd.DataFrame:
    work = m1.copy()
    work["_bucket"] = pd.to_datetime(
        work["timestamp_utc"], utc=True
    ).dt.floor("15min")
    grouped = work.groupby("_bucket", sort=True, observed=True)
    result = grouped.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        source_count=("volume", "size"),
        first_timestamp_mt4_server=("timestamp_mt4_server", "first"),
        last_timestamp_mt4_server=("timestamp_mt4_server", "last"),
        offset_min=("server_utc_offset_hours", "min"),
        offset_max=("server_utc_offset_hours", "max"),
    ).reset_index().rename(columns={"_bucket": "timestamp_utc"})
    result["timestamp_utc"] = result["timestamp_utc"].dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    result["incomplete_source_count"] = result["source_count"] != 15
    return result[[
        "timestamp_utc", "open", "high", "low", "close", "volume",
        "source_count", "incomplete_source_count",
        "first_timestamp_mt4_server", "last_timestamp_mt4_server",
        "offset_min", "offset_max",
    ]]


def derive_gaps(m1: pd.DataFrame) -> pd.DataFrame:
    utc = pd.to_datetime(m1["timestamp_utc"], utc=True)
    minutes = utc.diff().dt.total_seconds().div(60)
    mask = minutes > 1
    return pd.DataFrame({
        "previous_timestamp_utc": utc.shift(1)[mask].dt.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "next_timestamp_utc": utc[mask].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "missing_minutes": (minutes[mask] - 1).astype("int64"),
        "previous_timestamp_mt4_server": m1["timestamp_mt4_server"]
            .shift(1)[mask].values,
        "next_timestamp_mt4_server": m1["timestamp_mt4_server"][mask].values,
        "previous_offset_hours": m1["server_utc_offset_hours"]
            .shift(1)[mask].astype("int64").values,
        "next_offset_hours": m1["server_utc_offset_hours"]
            [mask].astype("int64").values,
    }).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-zip", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--year", type=int, default=2023)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source, source_manifest = load_artifact(args.artifact_zip)
    m1, diagnostics = normalize(source, args.year)
    m15 = derive_m15(m1)
    gaps = derive_gaps(m1)

    m1_path = args.output_dir / "usdjpy_2023_m1_bid_utc_rakuten_mt4_v1.csv.gz"
    m15_path = args.output_dir / "usdjpy_2023_m15_bid_utc_rakuten_mt4_v1.csv.gz"
    gaps_path = args.output_dir / "usdjpy_2023_m1_gap_inventory_utc_rakuten_mt4_v1.csv"
    manifest_path = args.output_dir / "usdjpy_2023_rakuten_mt4_hst_normalization_manifest_v1.json"
    write_gzip_csv(m1, m1_path)
    write_gzip_csv(m15, m15_path)
    gaps.to_csv(gaps_path, index=False, lineterminator="\n")

    manifest = {
        "schema_version": "usdjpy_2023_rakuten_mt4_hst_normalization_manifest_v1",
        "status": "PASS",
        "source": {
            "artifact_zip_sha256": sha256_file(args.artifact_zip),
            "source_hst_relative_path": source_manifest["source"]["selected_hst_relative_path"],
            "source_hst_sha256": source_manifest["source"]["selected_hst_sha256"],
            "hst_version": source_manifest["source"]["hst_version"],
            "symbol": source_manifest["source"]["symbol"],
            "period_minutes": source_manifest["source"]["period_minutes"],
            "price_side": source_manifest["source"]["price_side"],
        },
        "timezone": {
            "standard_offset": "UTC+02:00",
            "summer_offset": "UTC+03:00",
            "transition_rule": "Europe/EET convention: last Sunday in March 01:00 UTC through last Sunday in October 01:00 UTC",
            **diagnostics,
        },
        "coverage": {
            "first_timestamp_utc": m1["timestamp_utc"].iloc[0],
            "last_timestamp_utc": m1["timestamp_utc"].iloc[-1],
            "M1_records": int(len(m1)),
            "M15_records": int(len(m15)),
            "incomplete_M15_records": int(m15["incomplete_source_count"].sum()),
            "gap_count": int(len(gaps)),
            "max_missing_minutes": int(gaps["missing_minutes"].max()),
        },
        "files": {
            "M1": {"file": m1_path.name, "bytes": m1_path.stat().st_size, "sha256": sha256_file(m1_path)},
            "M15": {"file": m15_path.name, "bytes": m15_path.stat().st_size, "sha256": sha256_file(m15_path)},
            "gaps": {"file": gaps_path.name, "bytes": gaps_path.stat().st_size, "sha256": sha256_file(gaps_path)},
        },
        "boundaries": {
            "candidate_signal_generation": False,
            "candidate_outcome_evaluation": False,
            "parameter_selection": False,
            "2024_H2_access": False,
            "2025_access": False,
            "live_orders": False,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
