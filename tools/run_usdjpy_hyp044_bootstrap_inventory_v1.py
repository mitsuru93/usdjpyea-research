#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("HYP044_INPUT_ROOT", "hyp044_inputs"))
OUT = Path(os.environ.get("HYP044_OUTPUT_ROOT", "hyp044_bootstrap_output"))
OUT.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_shape(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"parse_error": f"{type(exc).__name__}: {exc}"}
    if isinstance(obj, dict):
        return {
            "type": "object",
            "keys": sorted(obj.keys())[:200],
            "schema_version": obj.get("schema_version"),
            "hypothesis_id": obj.get("hypothesis_id"),
            "candidate_id": obj.get("candidate_id"),
            "status": obj.get("status"),
            "decision": obj.get("decision") or obj.get("formal_decision"),
        }
    if isinstance(obj, list):
        first = obj[0] if obj else None
        return {
            "type": "array",
            "length": len(obj),
            "first_keys": sorted(first.keys())[:200] if isinstance(first, dict) else None,
        }
    return {"type": type(obj).__name__}


def csv_shape(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            sample = []
            for _ in range(3):
                try:
                    sample.append(next(reader))
                except StopIteration:
                    break
        return {"header": header, "sample": sample}
    except Exception as exc:
        return {"parse_error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    inventory: list[dict[str, Any]] = []
    candidate_files: list[dict[str, Any]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        rec: dict[str, Any] = {
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "suffix": path.suffix.lower(),
        }
        if path.suffix.lower() == ".json" and path.stat().st_size <= 10_000_000:
            rec["shape"] = json_shape(path)
        elif path.suffix.lower() in {".csv", ".tsv"} and path.stat().st_size <= 2_000_000_000:
            rec["shape"] = csv_shape(path)
        elif path.suffix.lower() in {".md", ".txt", ".sha256"} and path.stat().st_size <= 2_000_000:
            try:
                rec["preview"] = path.read_text(encoding="utf-8", errors="replace")[:4000]
            except Exception as exc:
                rec["preview_error"] = str(exc)
        inventory.append(rec)
        hay = (rel + " " + json.dumps(rec.get("shape", {}), ensure_ascii=False)).lower()
        if any(token in hay for token in [
            "trade", "ledger", "candidate", "portfolio", "baseline", "hyp039", "hyp042", "hyp043",
            "b02", "f05", "short_pullback", "short-pullback", "tick_authority", "portability",
        ]):
            candidate_files.append(rec)

    release_metadata = None
    release_path = ROOT / "release_metadata.json"
    if release_path.exists():
        try:
            release_metadata = json.loads(release_path.read_text(encoding="utf-8"))
        except Exception as exc:
            release_metadata = {"parse_error": str(exc)}

    summary = {
        "schema_version": "usdjpy_hyp044_bootstrap_inventory_v1",
        "root": str(ROOT),
        "file_count": len(inventory),
        "total_bytes": sum(x["bytes"] for x in inventory),
        "candidate_file_count": len(candidate_files),
        "release_count": len(release_metadata) if isinstance(release_metadata, list) else None,
        "2025H2_accessed": False,
    }
    (OUT / "inventory.json").write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "candidate_file_inventory.json").write_text(json.dumps(candidate_files, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (OUT / "candidate_file_inventory.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "bytes", "sha256", "suffix", "shape"])
        writer.writeheader()
        for rec in candidate_files:
            writer.writerow({
                "path": rec["path"],
                "bytes": rec["bytes"],
                "sha256": rec["sha256"],
                "suffix": rec["suffix"],
                "shape": json.dumps(rec.get("shape", {}), ensure_ascii=False),
            })

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
