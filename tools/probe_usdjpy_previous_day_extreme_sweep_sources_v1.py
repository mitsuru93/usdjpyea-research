#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def decoded_sample(raw: bytes, name: str) -> str:
    if name.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8-sig", errors="replace")


def inspect_tar(path: Path) -> dict[str, Any]:
    with tarfile.open(path, "r:gz") as archive:
        files = [m for m in archive.getmembers() if m.isfile()]
        if not files:
            raise RuntimeError(f"no files in {path}")
        member = files[0]
        extracted = archive.extractfile(member)
        if extracted is None:
            raise RuntimeError(f"cannot extract {member.name}")
        raw = extracted.read()
    text = decoded_sample(raw, member.name)
    lines = text.splitlines()
    if not lines:
        raise RuntimeError(f"empty member {member.name}")
    dialect = csv.Sniffer().sniff("\n".join(lines[:20]), delimiters=",;\t|")
    reader = csv.reader(io.StringIO(text), dialect)
    rows = list(reader)
    header = [c.strip() for c in rows[0]]
    lower = [c.lower() for c in header]
    timestamp_candidates = [header[i] for i, c in enumerate(lower) if any(k in c for k in ("timestamp", "datetime", "time", "date"))]
    bid_candidates = [header[i] for i, c in enumerate(lower) if "bid" in c]
    ask_candidates = [header[i] for i, c in enumerate(lower) if "ask" in c]
    return {
        "archive": path.name,
        "archive_sha256": sha256(path),
        "member_count": len(files),
        "first_member": member.name,
        "first_member_bytes": member.size,
        "delimiter": dialect.delimiter,
        "header": header,
        "timestamp_candidates": timestamp_candidates,
        "bid_candidates": bid_candidates,
        "ask_candidates": ask_candidates,
        "sample_rows": rows[1:4],
        "row_count_first_member": max(0, len(rows) - 1),
        "required_columns_detected": bool(timestamp_candidates and bid_candidates and ask_candidates),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-2023", type=Path, required=True)
    parser.add_argument("--raw-2024", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    p23 = sorted(args.raw_2023.glob("*.tar.gz"))
    p24 = sorted(args.raw_2024.glob("*.tar.gz"))
    if len(p23) != 1 or len(p24) != 1:
        raise RuntimeError({"2023_archives": [p.name for p in p23], "2024_archives": [p.name for p in p24]})

    result = {
        "schema_version": "usdjpy_previous_day_extreme_sweep_source_probe_v1",
        "status": "TECHNICAL_SOURCE_PROBE_PASS",
        "candidate_outcomes_computed": False,
        "protected_period_accessed": False,
        "years": {"2023": inspect_tar(p23[0]), "2024": inspect_tar(p24[0])},
    }
    if not all(v["required_columns_detected"] for v in result["years"].values()):
        result["status"] = "TECHNICAL_NO_RESULT_SOURCE_COLUMNS_UNRESOLVED"

    out = args.output / "source_probe.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    if result["status"] != "TECHNICAL_SOURCE_PROBE_PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
