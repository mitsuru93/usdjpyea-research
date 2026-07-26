#!/usr/bin/env python3
"""Read-only inventory and validation for existing USDJPY B02/F05 research sources.

The inventory is intentionally metadata-first. It never downloads or regenerates Tick
sources. Missing sources are reported as requirements instead of triggering collection.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import csv
import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "usdjpy_b02_f05_source_inventory_v1"
ALLOWED_KINDS = {"release", "repository_file", "archive_member"}
ALLOWED_STATES = {"available", "declared", "missing", "unverified"}


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    kind: str
    state: str
    locator: str
    sha256_hex: str | None = None
    rows: int | None = None
    notes: str = ""

    def validate(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if self.kind not in ALLOWED_KINDS:
            raise ValueError(f"unsupported source kind: {self.kind}")
        if self.state not in ALLOWED_STATES:
            raise ValueError(f"unsupported source state: {self.state}")
        if not self.locator.strip():
            raise ValueError("locator is required")
        if self.sha256_hex is not None:
            value = self.sha256_hex.removeprefix("sha256:")
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
                raise ValueError(f"invalid sha256: {self.sha256_hex}")
        if self.rows is not None and self.rows < 0:
            raise ValueError("rows must be non-negative")


def load_inventory(path: str | Path) -> list[SourceRecord]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected inventory schema")
    records = [SourceRecord(**item) for item in document.get("sources", [])]
    if not records:
        raise ValueError("inventory must contain sources")
    seen: set[str] = set()
    for record in records:
        record.validate()
        if record.source_id in seen:
            raise ValueError(f"duplicate source_id: {record.source_id}")
        seen.add(record.source_id)
    return records


def deterministic_inventory_sha256(records: Iterable[SourceRecord]) -> str:
    rows = []
    for record in sorted(records, key=lambda r: r.source_id):
        record.validate()
        rows.append(asdict(record))
    payload = {"schema_version": SCHEMA_VERSION, "sources": rows}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def inspect_repository_file(root: str | Path, record: SourceRecord) -> dict[str, Any]:
    record.validate()
    if record.kind != "repository_file":
        raise ValueError("inspect_repository_file requires repository_file kind")
    path = Path(root) / record.locator
    result: dict[str, Any] = {
        "source_id": record.source_id,
        "exists": path.is_file(),
        "locator": record.locator,
    }
    if not path.is_file():
        return result
    raw = path.read_bytes()
    result["size_bytes"] = len(raw)
    result["sha256"] = sha256(raw).hexdigest()
    result["sha_match"] = record.sha256_hex is None or result["sha256"] == record.sha256_hex.removeprefix("sha256:")
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            result["data_rows"] = sum(1 for _ in csv.DictReader(handle))
        result["row_match"] = record.rows is None or result["data_rows"] == record.rows
    return result


def collection_required(records: Iterable[SourceRecord]) -> bool:
    """True only when a source explicitly marked missing has no accepted substitute."""
    return any(record.state == "missing" for record in records)
