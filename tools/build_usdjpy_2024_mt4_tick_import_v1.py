#!/usr/bin/env python3
"""Build deterministic MT4/Tick Data Suite import CSV.GZ files from preserved USDJPY tick packages."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

SOURCE_HEADER = b"timestamp_utc,symbol,bid,ask,bid_volume,ask_volume,source\n"
OUTPUT_HEADER = b"datetime_utc,bid,ask,bid_volume,ask_volume\n"
MEMBER_RE = re.compile(r"^2024-\d{2}-\d{2}/decoded_csv/USDJPY/2024/(\d{2})/(\d{2})/(\d{2})\.csv\.gz$")


@dataclass
class MonthStats:
    month: str
    source_archive: str
    output_file: str
    rows: int = 0
    input_members: int = 0
    first_timestamp_utc: str | None = None
    last_timestamp_utc: str | None = None
    negative_spread_rows: int = 0
    non_monotonic_rows: int = 0
    symbol_mismatch_rows: int = 0
    invalid_rows: int = 0
    output_bytes: int = 0
    output_sha256: str = ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def price_to_mills(value: bytes) -> tuple[bytes, int]:
    whole, dot, fraction = value.partition(b".")
    if dot != b"." or not whole.isdigit() or not fraction.isdigit() or len(fraction) < 3:
        raise ValueError(f"invalid USDJPY price {value!r}")
    if any(byte != 48 for byte in fraction[3:]):
        raise ValueError(f"USDJPY price not representable at 3 digits {value!r}")
    rendered = whole + b"." + fraction[:3]
    return rendered, int(whole) * 1000 + int(fraction[:3])


def timestamp_to_mt4(value: bytes) -> tuple[bytes, str]:
    if len(value) != 27 or value[4:5] != b"-" or value[7:8] != b"-" or value[10:11] != b"T" or value[19:20] != b"." or value[-1:] != b"Z":
        raise ValueError(f"invalid timestamp {value!r}")
    if value[:4] != b"2024":
        raise ValueError(f"timestamp outside locked year {value!r}")
    rendered = value[:4] + b"." + value[5:7] + b"." + value[8:10] + b" " + value[11:19] + b"." + value[20:23]
    iso_ms = (value[:23] + b"Z").decode("ascii")
    return rendered, iso_ms


def validate_volume(value: bytes) -> bytes:
    if not value or value.startswith(b"-"):
        raise ValueError(f"invalid volume {value!r}")
    if not value.replace(b".", b"", 1).isdigit():
        raise ValueError(f"invalid volume {value!r}")
    return value


def iter_members(archive: tarfile.TarFile, month: str) -> Iterator[tarfile.TarInfo]:
    matched: list[tuple[str, tarfile.TarInfo]] = []
    for member in archive.getmembers():
        if not member.isfile():
            continue
        match = MEMBER_RE.match(member.name)
        if match and match.group(1) == month:
            matched.append((member.name, member))
    for _, member in sorted(matched, key=lambda item: item[0]):
        yield member


def convert_month(source_archive: Path, output_path: Path, symbol: str, month: str) -> MonthStats:
    stats = MonthStats(month=f"2024-{month}", source_archive=source_archive.name, output_file=output_path.name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    expected_symbol = symbol.encode("ascii")
    previous_timestamp: bytes | None = None

    with output_path.open("wb", buffering=1024 * 1024) as raw_output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, compresslevel=6, mtime=0) as output:
            output.write(OUTPUT_HEADER)
            with tarfile.open(source_archive, mode="r:gz") as archive:
                members = list(iter_members(archive, month))
                if not members:
                    raise SystemExit(f"no decoded CSV members found in {source_archive}")
                stats.input_members = len(members)
                for member in members:
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise SystemExit(f"unable to extract {member.name}")
                    with extracted, gzip.GzipFile(fileobj=extracted, mode="rb") as source:
                        header = source.readline()
                        if header != SOURCE_HEADER:
                            raise SystemExit(f"unexpected header in {member.name}: {header!r}")
                        for row_number, raw_line in enumerate(source, start=2):
                            try:
                                fields = raw_line.rstrip(b"\r\n").split(b",")
                                if len(fields) != 7:
                                    raise ValueError(f"expected 7 fields, got {len(fields)}")
                                timestamp, row_symbol, bid_raw, ask_raw, bid_volume_raw, ask_volume_raw, _source = fields
                                mt4_time, iso_ms = timestamp_to_mt4(timestamp)
                                bid, bid_mills = price_to_mills(bid_raw)
                                ask, ask_mills = price_to_mills(ask_raw)
                                bid_volume = validate_volume(bid_volume_raw)
                                ask_volume = validate_volume(ask_volume_raw)
                            except Exception as exc:
                                stats.invalid_rows += 1
                                raise SystemExit(f"invalid row {member.name}:{row_number}: {exc}") from exc

                            if row_symbol != expected_symbol:
                                stats.symbol_mismatch_rows += 1
                                raise SystemExit(f"symbol mismatch {member.name}:{row_number}: {row_symbol!r}")
                            if ask_mills < bid_mills:
                                stats.negative_spread_rows += 1
                                raise SystemExit(f"negative spread {member.name}:{row_number}")
                            if previous_timestamp is not None and timestamp < previous_timestamp:
                                stats.non_monotonic_rows += 1
                                raise SystemExit(f"non-monotonic timestamp {member.name}:{row_number}")

                            if stats.first_timestamp_utc is None:
                                stats.first_timestamp_utc = iso_ms
                            stats.last_timestamp_utc = iso_ms
                            previous_timestamp = timestamp
                            output.write(mt4_time + b"," + bid + b"," + ask + b"," + bid_volume + b"," + ask_volume + b"\n")
                            stats.rows += 1

    stats.output_bytes = output_path.stat().st_size
    stats.output_sha256 = sha256_file(output_path)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--symbol", default="USDJPY")
    parser.add_argument("--year", type=int, default=2024)
    args = parser.parse_args()

    if args.year != 2024:
        raise SystemExit("this locked converter only accepts year 2024")
    if args.symbol != "USDJPY":
        raise SystemExit("this locked converter only accepts USDJPY")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_stats: list[MonthStats] = []
    for month_number in range(1, 13):
        month = f"{month_number:02d}"
        source = args.input_dir / f"usdjpy-2024-{month}-raw-ticks-v1.tar.gz"
        if not source.is_file():
            raise SystemExit(f"missing source archive: {source}")
        output = args.output_dir / f"USDJPY-2024-{month}-mt4-tick-import-v1.csv.gz"
        stats = convert_month(source, output, args.symbol, month)
        print(json.dumps(asdict(stats), sort_keys=True), flush=True)
        all_stats.append(stats)

    total_rows = sum(item.rows for item in all_stats)
    if total_rows != 40_969_081:
        raise SystemExit(f"annual row count mismatch: {total_rows} != 40969081")

    manifest = {
        "schema_version": "usdjpy_2024_mt4_tick_import_v1",
        "symbol": args.symbol,
        "year": args.year,
        "source_release_tag": "usdjpy-2024-raw-bidask-ticks-v1",
        "source": "Dukascopy BI5 public Bid/Ask ticks",
        "timestamp_timezone": "UTC",
        "output_format": {
            "encoding": "UTF-8",
            "compression": "gzip",
            "delimiter": ",",
            "header": ["datetime_utc", "bid", "ask", "bid_volume", "ask_volume"],
            "datetime_format": "yyyy.MM.dd HH:mm:ss.fff",
            "price_digits": 3,
            "column_order": ["datetime_utc", "bid", "ask", "bid_volume", "ask_volume"],
            "intended_importer": "Tick Data Suite custom CSV import"
        },
        "annual_rows": total_rows,
        "months": [asdict(item) for item in all_stats],
        "accepted": True,
        "boundaries": {
            "contains_real_bid_and_ask": True,
            "contains_variable_spread": True,
            "direct_standard_mt4_import": False,
            "requires_tick_data_suite_or_equivalent_mt4_tick_integration": True,
            "rakuten_quote_equivalence": False
        }
    }
    (args.output_dir / "USDJPY-2024-mt4-tick-import-v1.manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    guide = """# USDJPY 2024 MT4 Tick Import v1

This package contains twelve monthly UTC CSV.GZ files for importing the preserved USDJPY 2024 Dukascopy Bid/Ask ticks into Tick Data Suite (or an equivalent MT4 tick integration).

Columns: `datetime_utc,bid,ask,bid_volume,ask_volume`

Datetime format: `yyyy.MM.dd HH:mm:ss.fff` (UTC)

The files preserve separate Bid and Ask prices and therefore the recorded variable spread. Standard MT4 cannot consume these CSV files directly. Import them as a custom source in Tick Data Manager, map the five columns exactly, set the source timezone to UTC, and run MT4 with tick data enabled.

Do not treat the resulting tests as Rakuten quote history. The data source remains Dukascopy; Rakuten account parameters must be configured separately.
"""
    (args.output_dir / "IMPORT_GUIDE.md").write_text(guide, encoding="utf-8")

    checksum_lines = []
    for path in sorted(args.output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            checksum_lines.append(f"{sha256_file(path)}  {path.name}")
    (args.output_dir / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps({"accepted": True, "annual_rows": total_rows, "months": 12}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
