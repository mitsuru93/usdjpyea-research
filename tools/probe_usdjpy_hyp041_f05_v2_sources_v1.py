#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def open_text(path: Path):
    if path.name.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


def inspect_csv(path: Path) -> dict[str, Any]:
    row_count = 0
    event_counts: Counter[str] = Counter()
    strategy_counts: Counter[str] = Counter()
    side_counts: Counter[str] = Counter()
    nonempty_counts: Counter[str] = Counter()
    min_values: dict[str, str] = {}
    max_values: dict[str, str] = {}
    time_fields = {
        "utc_time", "entry_utc", "close_utc", "signal_utc", "observation_utc",
        "server_time", "entry_server", "close_server", "timestamp", "time"
    }
    with open_text(path) as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        for row in reader:
            row_count += 1
            event = (row.get("event") or row.get("event_type") or "").strip()
            strategy = (row.get("strategy") or row.get("strategy_id") or "").strip()
            side = (row.get("side") or row.get("direction") or "").strip()
            if event:
                event_counts[event] += 1
            if strategy:
                strategy_counts[strategy] += 1
            if side:
                side_counts[side] += 1
            for key, value in row.items():
                value = (value or "").strip()
                if value:
                    nonempty_counts[key] += 1
                    if key in time_fields:
                        if key not in min_values or value < min_values[key]:
                            min_values[key] = value
                        if key not in max_values or value > max_values[key]:
                            max_values[key] = value
    return {
        "type": "csv",
        "columns": fields,
        "row_count": row_count,
        "event_counts": dict(event_counts.most_common()),
        "strategy_counts": dict(strategy_counts.most_common()),
        "side_counts": dict(side_counts.most_common()),
        "nonempty_counts": dict(nonempty_counts),
        "time_min": min_values,
        "time_max": max_values,
        "has_trade_lifecycle": bool(event_counts.get("order_opened") and event_counts.get("order_closed")),
        "has_tick_risk": any(k in event_counts for k in ("risk_summary", "risk_trough", "period_end_mark")),
        "has_entry_decisions": any("decision" in k.lower() or "blocked" in k.lower() for k in event_counts),
    }


def inspect_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(obj, dict):
        return {
            "type": "json",
            "root_type": "object",
            "root_keys": sorted(obj.keys()),
            "schema_version": obj.get("schema_version"),
            "status": obj.get("status"),
            "decision": obj.get("decision"),
            "hypothesis_id": obj.get("hypothesis_id"),
            "candidate_id": obj.get("candidate_id"),
        }
    return {"type": "json", "root_type": type(obj).__name__, "length": len(obj) if hasattr(obj, "__len__") else None}


def iter_files(root: Path) -> Iterable[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def inventory_root(label: str, root: Path) -> dict[str, Any]:
    records = []
    errors = []
    for path in iter_files(root):
        rel = path.relative_to(root).as_posix()
        record: dict[str, Any] = {
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        try:
            lower = path.name.lower()
            if lower.endswith(".csv") or lower.endswith(".csv.gz"):
                record.update(inspect_csv(path))
            elif lower.endswith(".json"):
                record.update(inspect_json(path))
            else:
                record["type"] = "other"
        except Exception as exc:
            record["inspection_error"] = f"{type(exc).__name__}: {exc}"
            errors.append({"path": rel, "error": record["inspection_error"]})
        records.append(record)
    lifecycle = [r["path"] for r in records if r.get("has_trade_lifecycle")]
    tick_risk = [r["path"] for r in records if r.get("has_tick_risk")]
    decision_ledgers = [r["path"] for r in records if r.get("has_entry_decisions")]
    f05_files = [r["path"] for r in records if "f05" in r["path"].lower()]
    return {
        "label": label,
        "root": str(root),
        "file_count": len(records),
        "total_bytes": sum(r["bytes"] for r in records),
        "inspection_errors": errors,
        "trade_lifecycle_csvs": lifecycle,
        "tick_risk_csvs": tick_risk,
        "entry_decision_csvs": decision_ledgers,
        "f05_named_files": f05_files,
        "files": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-release-dir", type=Path, required=True)
    parser.add_argument("--phase1-dir", type=Path, required=True)
    parser.add_argument("--historical-dir", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-report", type=Path, required=True)
    parser.add_argument("--research-sha", default="UNKNOWN")
    parser.add_argument("--run-id", default="LOCAL")
    args = parser.parse_args()

    for root in (args.core_release_dir, args.phase1_dir, args.historical_dir):
        if not root.exists():
            raise RuntimeError(f"missing source root: {root}")

    roots = [
        inventory_root("core_2025H1_release", args.core_release_dir),
        inventory_root("research_phase1_2023_2024", args.phase1_dir),
        inventory_root("historical_2023_2024_authorities", args.historical_dir),
    ]
    result = {
        "schema_version": "usdjpy_hyp041_source_inventory_v1",
        "status": "PASS_SOURCE_INVENTORY_NO_CANDIDATE_OUTCOME",
        "hypothesis_id": "USDJPY-HYP-041",
        "family_id": "F05_V2_PORTABLE_LOSS_RECOVERY_ARCHITECTURE",
        "research_sha": args.research_sha,
        "run_id": args.run_id,
        "candidate_outcomes_computed": False,
        "2025H1_candidate_version_accessed": False,
        "2025H2_accessed": False,
        "roots": roots,
        "summary": {
            "trade_lifecycle_csvs": {r["label"]: r["trade_lifecycle_csvs"] for r in roots},
            "tick_risk_csvs": {r["label"]: r["tick_risk_csvs"] for r in roots},
            "entry_decision_csvs": {r["label"]: r["entry_decision_csvs"] for r in roots},
            "f05_named_files": {r["label"]: r["f05_named_files"] for r in roots},
            "inspection_error_count": sum(len(r["inspection_errors"]) for r in roots),
        },
        "next_action": "Use the identified exact lifecycle Tick-risk and decision ledgers to build the common-schema F05 failure decomposition before freezing any candidate contract.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# USDJPY-HYP-041 Source Inventory v1",
        "",
        "- Status: `PASS_SOURCE_INVENTORY_NO_CANDIDATE_OUTCOME`",
        "- Candidate outcomes computed: `false`",
        "- 2025H2 accessed: `false`",
        "",
    ]
    for root in roots:
        lines.extend([
            f"## {root['label']}",
            "",
            f"- Files: {root['file_count']}",
            f"- Bytes: {root['total_bytes']}",
            f"- Trade lifecycle CSVs: {', '.join(root['trade_lifecycle_csvs']) or 'none'}",
            f"- Tick-risk CSVs: {', '.join(root['tick_risk_csvs']) or 'none'}",
            f"- Entry-decision CSVs: {', '.join(root['entry_decision_csvs']) or 'none'}",
            f"- Inspection errors: {len(root['inspection_errors'])}",
            "",
        ])
    lines.extend(["## Exact next action", "", result["next_action"], ""])
    args.out_report.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
