#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import lzma
import re
import struct
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BI5_RECORD = struct.Struct(">3I2f")
USDJPY_PRICE_SCALE = 1000.0
BI5_PATH = re.compile(r"(?:^|/)(20\d{2})/(\d{2})/(\d{2})/(\d{2})h_ticks\.bi5$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def member_hour_utc(name: str) -> datetime:
    match = BI5_PATH.search(name)
    if not match:
        raise ValueError(f"cannot derive BI5 hour from terminal member suffix: {name}")
    year, month, day, hour = (int(value) for value in match.groups())
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def inspect_bi5(files: list[tarfile.TarInfo], archive: tarfile.TarFile) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    for member in files:
        if not member.name.lower().endswith(".bi5"):
            continue
        extracted = archive.extractfile(member)
        if extracted is None:
            continue
        compressed = extracted.read()
        try:
            payload = lzma.decompress(compressed)
        except Exception as exc:
            errors.append({"member": member.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        if not payload:
            continue
        if len(payload) % BI5_RECORD.size:
            errors.append({"member": member.name, "error": f"decoded bytes {len(payload)} not divisible by {BI5_RECORD.size}"})
            continue
        hour = member_hour_utc(member.name)
        record_count = len(payload) // BI5_RECORD.size
        sample_rows: list[dict[str, Any]] = []
        inversion_count = 0
        previous_ms = -1
        nonmonotonic_ms = 0
        for index in range(min(record_count, 1000)):
            ms, ask_i, bid_i, ask_volume, bid_volume = BI5_RECORD.unpack_from(payload, index * BI5_RECORD.size)
            if ask_i < bid_i:
                inversion_count += 1
            if ms < previous_ms:
                nonmonotonic_ms += 1
            previous_ms = ms
            if index < 3:
                sample_rows.append({
                    "timestamp_utc": (hour + timedelta(milliseconds=ms)).isoformat(),
                    "millisecond_offset": ms,
                    "ask": ask_i / USDJPY_PRICE_SCALE,
                    "bid": bid_i / USDJPY_PRICE_SCALE,
                    "ask_volume": ask_volume,
                    "bid_volume": bid_volume,
                })
        return {
            "format": "DUKASCOPY_BI5_LZMA_BIG_ENDIAN_20_BYTE",
            "record_struct": ">3I2f",
            "price_scale": USDJPY_PRICE_SCALE,
            "member_hour_regex": BI5_PATH.pattern,
            "first_nonempty_member": member.name,
            "first_nonempty_member_compressed_bytes": len(compressed),
            "first_nonempty_member_decoded_bytes": len(payload),
            "row_count_first_nonempty_member": record_count,
            "sample_rows": sample_rows,
            "sample_ask_bid_inversion_count": inversion_count,
            "sample_nonmonotonic_millisecond_count": nonmonotonic_ms,
            "timestamp_candidates": ["terminal member /YYYY/MM/DD/HHh_ticks.bi5 UTC hour + record millisecond offset"],
            "bid_candidates": ["record bid int / 1000"],
            "ask_candidates": ["record ask int / 1000"],
            "required_columns_detected": bool(sample_rows and inversion_count == 0 and nonmonotonic_ms == 0),
            "decode_errors_before_first_nonempty_member": errors[:10],
        }
    raise RuntimeError({"reason": "no decodable nonempty BI5 member", "errors": errors[:20]})


def inspect_delimited(files: list[tarfile.TarInfo], archive: tarfile.TarFile) -> dict[str, Any]:
    member = files[0]
    extracted = archive.extractfile(member)
    if extracted is None:
        raise RuntimeError(f"cannot extract {member.name}")
    raw = extracted.read()
    if member.name.endswith(".gz"):
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8-sig", errors="strict")
    lines = text.splitlines()
    if not lines:
        raise RuntimeError(f"empty member {member.name}")
    dialect = csv.Sniffer().sniff("\n".join(lines[:20]), delimiters=",;\t|")
    rows = list(csv.reader(io.StringIO(text), dialect))
    header = [cell.strip() for cell in rows[0]]
    lower = [cell.lower() for cell in header]
    timestamp_candidates = [header[index] for index, cell in enumerate(lower) if any(key in cell for key in ("timestamp", "datetime", "time", "date"))]
    bid_candidates = [header[index] for index, cell in enumerate(lower) if "bid" in cell]
    ask_candidates = [header[index] for index, cell in enumerate(lower) if "ask" in cell]
    return {
        "format": "DELIMITED_TEXT",
        "first_nonempty_member": member.name,
        "delimiter": dialect.delimiter,
        "header": header,
        "timestamp_candidates": timestamp_candidates,
        "bid_candidates": bid_candidates,
        "ask_candidates": ask_candidates,
        "sample_rows": rows[1:4],
        "row_count_first_nonempty_member": max(0, len(rows) - 1),
        "required_columns_detected": bool(timestamp_candidates and bid_candidates and ask_candidates),
    }


def inspect_tar(path: Path) -> dict[str, Any]:
    with tarfile.open(path, "r:gz") as archive:
        files = [member for member in archive.getmembers() if member.isfile()]
        if not files:
            raise RuntimeError(f"no files in {path}")
        names = [member.name for member in files]
        if any(name.lower().endswith(".bi5") for name in names):
            payload = inspect_bi5(files, archive)
        else:
            payload = inspect_delimited(files, archive)
    return {
        "archive": path.name,
        "archive_sha256": sha256(path),
        "member_count": len(files),
        "first_member": names[0],
        "last_member": names[-1],
        "member_extensions": sorted({Path(name).suffix.lower() for name in names}),
        **payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-2023", type=Path, required=True)
    parser.add_argument("--raw-2024", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    archives_2023 = sorted(args.raw_2023.glob("*.tar.gz"))
    archives_2024 = sorted(args.raw_2024.glob("*.tar.gz"))
    if len(archives_2023) != 1 or len(archives_2024) != 1:
        raise RuntimeError({"2023_archives": [path.name for path in archives_2023], "2024_archives": [path.name for path in archives_2024]})

    result = {
        "schema_version": "usdjpy_previous_day_extreme_sweep_source_probe_v1",
        "status": "TECHNICAL_SOURCE_PROBE_PASS",
        "source_contract": "Dukascopy BI5 source-native Bid/Ask Tick",
        "candidate_outcomes_computed": False,
        "protected_period_accessed": False,
        "years": {"2023": inspect_tar(archives_2023[0]), "2024": inspect_tar(archives_2024[0])},
    }
    if not all(year["required_columns_detected"] for year in result["years"].values()):
        result["status"] = "TECHNICAL_NO_RESULT_SOURCE_COLUMNS_UNRESOLVED"

    output = args.output / "source_probe.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    if result["status"] != "TECHNICAL_SOURCE_PROBE_PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
