#!/usr/bin/env python3
"""Delete residual Tick-related Actions Artifacts superseded by durable Releases.

Safety contract:
- validate every durable Release authority and its SHA-256 asset inventory;
- treat USDJPY 2019-01..09 as outside the fixed development period and before the
  only accepted 2019 warmup window (2019Q4);
- require completed source runs and no executable Actions dependency;
- freeze a candidate digest in dry-run and require an identical re-read on apply;
- verify deletion readback and immutable Release identities after apply.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import fx2_release_backed_artifact_purge_v1 as base
from tools import fx2_release_backed_artifact_purge_v3 as semantic
from tools import fx2_eurusd_release_mirror_purge_v1 as eur_year
from tools import fx2_eurusd_2024_release_mirror_purge_v2 as eur_2024
from tools.fx2_usdjpy_release_authority_purge_v3 import load_fixed
from tools.fx2_usdjpy_release_authority_purge_v4 import exact_year_release

USDJPY_2024_RECEIPT = ROOT / "docs/research_reboot/artifact_archives/usdjpy_2024_raw_ticks_v1/receipt.json"
USDJPY_2024_TAG = "usdjpy-2024-raw-bidask-ticks-v1"
TICK_TOKENS = ("raw-ticks", "raw_ticks", "tick-authority", "tick_authority", "bidask", "dukas")


class Error(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt_bytes(value: int) -> str:
    number = float(value)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    index = 0
    while number >= 1024 and index < len(units) - 1:
        number /= 1024
        index += 1
    return f"{number:.2f} {units[index]}" if index else f"{int(number)} B"


def stable_release(api: base.GitHubApi, tag: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    release = api.json(f"/repos/{api.repository}/releases/tags/{tag}")
    if release.get("draft") or release.get("prerelease") or release.get("tag_name") != tag:
        raise Error(f"unstable Release: {tag}")
    assets: dict[str, dict[str, Any]] = {}
    identity_rows: list[dict[str, Any]] = []
    for asset in release.get("assets", []):
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        digest = str(asset.get("digest") or "").lower()
        size = int(asset.get("size") or 0)
        if not name or asset.get("state") != "uploaded" or size <= 0 or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise Error(f"invalid Release asset: {tag}/{name}")
        if name in assets:
            raise Error(f"duplicate Release asset: {tag}/{name}")
        row = {"id": int(asset["id"]), "name": name, "size": size, "digest": digest}
        assets[name] = row
        identity_rows.append(row)
    identity_rows.sort(key=lambda row: row["name"])
    identity = {
        "release_id": int(release["id"]),
        "tag": tag,
        "published_at": str(release.get("published_at") or ""),
        "asset_count": len(identity_rows),
        "asset_identity_sha256": sha(identity_rows),
    }
    return identity, assets


def validate_usdjpy_2024(api: base.GitHubApi) -> dict[str, Any]:
    receipt = json.loads(USDJPY_2024_RECEIPT.read_text(encoding="utf-8"))
    durable = receipt.get("durable_release") or {}
    validation = receipt.get("annual_validation") or {}
    if receipt.get("archive_status") != "durably_archived_in_github_release_and_receipt_committed":
        raise Error("USDJPY 2024 archive status mismatch")
    if durable.get("tag") != USDJPY_2024_TAG or durable.get("asset_count") != 64:
        raise Error("USDJPY 2024 receipt Release identity mismatch")
    if durable.get("actions_artifact_expiry_independent") is not True:
        raise Error("USDJPY 2024 Release is not declared Actions-expiry independent")
    if validation.get("accepted") is not True or validation.get("present_days") != 366 or validation.get("resolved_hours") != 8784:
        raise Error("USDJPY 2024 annual validation mismatch")
    if validation.get("missing_404_hours") != 0 or validation.get("error_hours") != 0:
        raise Error("USDJPY 2024 annual validation has unresolved errors")
    identity, assets = stable_release(api, USDJPY_2024_TAG)
    expected = {
        f"usdjpy-2024-{month:02d}-raw-ticks-v1.{suffix}"
        for month in range(1, 13)
        for suffix in ("tar.gz", "manifest.json", "source-artifacts.json", "repair-artifacts.json", "SHA256SUMS")
    }
    expected |= {
        "usdjpy-2024-raw-ticks-v1.annual-manifest.json",
        "usdjpy-2024-raw-tick-repair-lock-v1.json",
        "RELEASE_NOTES.md",
        "SHA256SUMS",
    }
    if set(assets) != expected or identity["asset_count"] != 64:
        raise Error(f"USDJPY 2024 Release inventory mismatch missing={sorted(expected-set(assets))} extra={sorted(set(assets)-expected)}")
    return {
        "authority_type": "complete_year_raw_release",
        "year": 2024,
        "receipt_sha256": file_sha(USDJPY_2024_RECEIPT),
        **identity,
    }


def validate_authorities(api: base.GitHubApi) -> dict[str, dict[str, Any]]:
    fixed = load_fixed()
    fixed.validate_year_release = lambda api_obj, year, tag: exact_year_release(fixed, api_obj, year, tag)
    authorities: dict[str, dict[str, Any]] = {}

    source_native = fixed.validate_source_native(api, ROOT)
    authorities["USDJPY:2019Q4-2022"] = {"authority_type": "source_native_tick_authority", **source_native}
    for year, tag in ((2023, "usdjpy-2023-raw-bidask-ticks-v1"), (2025, "usdjpy-2025-raw-bidask-ticks-v1")):
        authorities[f"USDJPY:{year}"] = fixed.validate_year_release(api, year, tag)
    authorities["USDJPY:2024"] = validate_usdjpy_2024(api)

    for year in (2020, 2021, 2022, 2023):
        authorities[f"EURUSD:{year}"] = eur_year.release_identity(api, year)
    authorities["EURUSD:2024"] = eur_2024.release_identity(api)

    for key, row in authorities.items():
        row["authority_key"] = key
        row["authority_evidence_sha256"] = sha(row)
    return dict(sorted(authorities.items()))


def parse_period(name: str) -> tuple[str, int, int | None] | None:
    lower = name.lower()
    symbol = "USDJPY" if "usdjpy" in lower else "EURUSD" if "eurusd" in lower else None
    if symbol is None or not any(token in lower for token in TICK_TOKENS):
        return None
    patterns = (
        r"(?:^|[-_])(20\d{2})[-_](0[1-9]|1[0-2])[-_](?:0[1-9]|[12]\d|3[01])(?:[-_]|$)",
        r"(?:^|[-_])(20\d{2})[-_](0[1-9]|1[0-2])(?:[-_]|$)",
        r"(?:^|[-_])(20\d{2})[-_]raw[-_]ticks[-_]month[-_](0[1-9]|1[0-2])(?:[-_]|$)",
        r"month[-_](0[1-9]|1[0-2])[-_].*?(20\d{2})",
    )
    for index, pattern in enumerate(patterns):
        match = re.search(pattern, lower)
        if match:
            if index == 3:
                return symbol, int(match.group(2)), int(match.group(1))
            return symbol, int(match.group(1)), int(match.group(2))
    year = re.search(r"(?:^|[-_])(20\d{2})(?:[-_]|$)", lower)
    if year:
        return symbol, int(year.group(1)), None
    return None


def authority_for(symbol: str, year: int, month: int | None, authorities: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any] | None]:
    if symbol == "USDJPY" and year == 2019 and month is not None and 1 <= month <= 9:
        return "outside_fixed_period_before_2019Q4_warmup", authorities["USDJPY:2019Q4-2022"]
    if symbol == "USDJPY" and ((year == 2019 and month in (10, 11, 12)) or year in (2020, 2021, 2022)):
        return "release_backed_source_native", authorities["USDJPY:2019Q4-2022"]
    key = f"{symbol}:{year}"
    if key in authorities:
        return "release_backed_complete_year", authorities[key]
    return "unsupported_period", None


def identity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = (
        "artifact_id", "artifact_name", "bytes", "artifact_digest", "run_id", "run_conclusion", "head_sha",
        "symbol", "year", "month", "selection_reason", "authority_key", "release_id", "release_tag",
        "release_asset_identity_sha256", "authority_evidence_sha256",
    )
    return [{key: row[key] for key in keys} for row in rows]


def build(api: base.GitHubApi, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    authorities = validate_authorities(api)
    inventory = api.paginate(f"/repos/{api.repository}/actions/artifacts?", cap=20_000)
    classification = base.load_workflow_classification(root)
    files = list(base.iter_dependency_files(root, classification))
    selected: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    run_cache: dict[int, dict[str, Any]] = {}

    for artifact in inventory:
        if not isinstance(artifact, dict) or artifact.get("expired") is True:
            continue
        name = str(artifact.get("name") or "")
        period = parse_period(name)
        if period is None:
            continue
        symbol, year, month = period
        reason, authority = authority_for(symbol, year, month, authorities)
        artifact_id = int(artifact.get("id") or 0)
        size = int(artifact.get("size_in_bytes") or 0)
        digest = str(artifact.get("digest") or "").lower()
        run_id = int((artifact.get("workflow_run") or {}).get("id") or 0)
        base_row = {
            "artifact_id": artifact_id,
            "artifact_name": name,
            "bytes": size,
            "symbol": symbol,
            "year": year,
            "month": month,
            "selection_reason": reason,
        }
        if authority is None:
            unsupported.append(base_row)
            continue
        if artifact_id <= 0 or size <= 0 or run_id <= 0 or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise Error(f"invalid Actions Artifact identity: {artifact_id}/{name}")
        if run_id not in run_cache:
            run_cache[run_id] = api.json(f"/repos/{api.repository}/actions/runs/{run_id}")
        run = run_cache[run_id]
        row = {
            **base_row,
            "artifact_digest": digest,
            "run_id": run_id,
            "run_conclusion": str(run.get("conclusion") or ""),
            "head_sha": str(run.get("head_sha") or ""),
            "authority_key": str(authority["authority_key"]),
            "release_id": int(authority["release_id"]),
            "release_tag": str(authority.get("tag") or authority.get("release_tag") or ""),
            "release_asset_identity_sha256": str(authority.get("asset_identity_sha256") or ""),
            "authority_evidence_sha256": str(authority["authority_evidence_sha256"]),
        }
        if run.get("status") != "completed":
            row["blocking_reasons"] = [f"run_not_completed:{run.get('status')}"]
            blocked.append(row)
            continue
        refs = semantic.semantic_dependency_refs(artifact, files)
        if refs:
            row["blocking_reasons"] = refs
            blocked.append(row)
        else:
            selected.append(row)

    selected.sort(key=lambda row: (row["symbol"], row["year"], row["month"] or 0, row["artifact_id"]))
    blocked.sort(key=lambda row: (-row["bytes"], row["artifact_id"]))
    unsupported.sort(key=lambda row: (-row["bytes"], row["artifact_id"]))
    return selected, blocked, unsupported, authorities, {
        "inventory_artifact_count": len(inventory),
        "dependency_file_count": len(files),
        "source_run_count": len(run_cache),
    }


def report(receipt: dict[str, Any]) -> str:
    lines = [
        "## FX2 residual Tick Artifact purge", "",
        f"- Mode: `{receipt['mode']}`",
        f"- Selected: **{receipt['candidate_count']:,}** ({fmt_bytes(receipt['candidate_bytes'])})",
        f"- Blocked: `{receipt['blocked_count']:,}` ({fmt_bytes(receipt['blocked_bytes'])})",
        f"- Unsupported Tick: `{receipt['unsupported_count']:,}` ({fmt_bytes(receipt['unsupported_bytes'])})",
        f"- Deleted: **{receipt['deleted_count']:,}** ({fmt_bytes(receipt['deleted_bytes'])})",
        f"- Remaining selected: `{receipt['remaining_candidate_count']:,}`",
        f"- Candidate digest: `{receipt['candidate_digest']}`",
        f"- Errors: **{receipt['error_count']}**", "",
        "### Selected by reason", "", "| Reason | Count | Size |", "|---|---:|---:|",
    ]
    for reason, row in receipt["reason_summary"].items():
        lines.append(f"| `{reason}` | {row['count']:,} | {fmt_bytes(row['bytes'])} |")
    if receipt["blocked"]:
        lines += ["", "### Blocked", "", "| Artifact | Size | Reason |", "|---|---:|---|"]
        for row in receipt["blocked"][:50]:
            reasons = "<br>".join(f"`{item}`" for item in row.get("blocking_reasons", [])[:8])
            lines.append(f"| `{row['artifact_name']}` (`{row['artifact_id']}`) | {fmt_bytes(row['bytes'])} | {reasons} |")
    if receipt["unsupported"]:
        lines += ["", "### Unsupported Tick periods", "", "| Artifact | Period | Size |", "|---|---|---:|"]
        for row in receipt["unsupported"][:50]:
            period = f"{row['symbol']} {row['year']}-{row['month']:02d}" if row.get("month") else f"{row['symbol']} {row['year']}"
            lines.append(f"| `{row['artifact_name']}` (`{row['artifact_id']}`) | `{period}` | {fmt_bytes(row['bytes'])} |")
    summary = {key: receipt[key] for key in (
        "schema_version", "mode", "repository", "generated_at", "candidate_count", "candidate_bytes",
        "candidate_digest", "blocked_count", "blocked_bytes", "unsupported_count", "unsupported_bytes",
        "deleted_count", "deleted_bytes", "remaining_candidate_count", "error_count", "errors", "reason_summary",
    )}
    lines += ["", "<details><summary>Machine-readable summary</summary>", "", "```json", canonical(summary), "```", "</details>"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "apply"), required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--expected-candidate-digest")
    parser.add_argument("--max-deletions", type=int, default=2000)
    parser.add_argument("--max-bytes", type=int, default=4_000_000_000)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    api = base.GitHubApi(os.environ.get("GITHUB_TOKEN", ""), args.repository)
    root = Path(args.root).resolve()
    rows, blocked, unsupported, authorities, meta = build(api, root)
    digest = sha(identity(rows))
    total = sum(row["bytes"] for row in rows)
    if len(rows) > args.max_deletions or total > args.max_bytes:
        raise Error("safety cap exceeded")

    if args.mode == "apply":
        if args.expected_candidate_digest != digest:
            raise Error(f"candidate digest mismatch expected={args.expected_candidate_digest} observed={digest}")
        rows2, blocked2, unsupported2, authorities2, _ = build(api, root)
        if sha(identity(rows2)) != digest or canonical(blocked2) != canonical(blocked) or canonical(unsupported2) != canonical(unsupported) or canonical(authorities2) != canonical(authorities):
            raise Error("pre-delete evidence changed")

    deleted: list[int] = []
    errors: list[str] = []
    if args.mode == "apply":
        for row in rows:
            try:
                api.delete_artifact(row["artifact_id"])
                deleted.append(row["artifact_id"])
            except base.PurgeError as exc:
                errors.append(f"{row['artifact_id']}: {exc}")

    remaining_ids = {int(row["id"]) for row in api.paginate(f"/repos/{api.repository}/actions/artifacts?", cap=20_000)}
    remaining = {row["artifact_id"] for row in rows if row["artifact_id"] in remaining_ids}
    for artifact_id in deleted:
        if artifact_id in remaining:
            errors.append(f"deleted Artifact still present: {artifact_id}")
    if canonical(validate_authorities(api)) != canonical(authorities):
        errors.append("Release authority identity changed")

    reason_summary: dict[str, dict[str, int]] = {}
    for row in rows:
        item = reason_summary.setdefault(row["selection_reason"], {"count": 0, "bytes": 0})
        item["count"] += 1
        item["bytes"] += row["bytes"]
    reason_summary = dict(sorted(reason_summary.items()))
    deleted_set = set(deleted)
    receipt = {
        "schema_version": "fx2_residual_tick_artifact_purge_receipt_v1",
        "mode": args.mode,
        "repository": args.repository,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **meta,
        "authority_count": len(authorities),
        "authority_identity_sha256": sha(authorities),
        "candidate_count": len(rows),
        "candidate_bytes": total,
        "candidate_digest": digest,
        "blocked_count": len(blocked),
        "blocked_bytes": sum(row["bytes"] for row in blocked),
        "unsupported_count": len(unsupported),
        "unsupported_bytes": sum(row["bytes"] for row in unsupported),
        "deleted_count": len(deleted),
        "deleted_bytes": sum(row["bytes"] for row in rows if row["artifact_id"] in deleted_set),
        "remaining_candidate_count": len(remaining),
        "error_count": len(errors),
        "errors": errors,
        "reason_summary": reason_summary,
        "authorities": authorities,
        "candidates": rows,
        "blocked": blocked,
        "unsupported": unsupported,
    }
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(args.report).write_text(report(receipt), encoding="utf-8")
    print(canonical({key: receipt[key] for key in (
        "candidate_count", "candidate_bytes", "candidate_digest", "blocked_count", "blocked_bytes",
        "unsupported_count", "unsupported_bytes", "deleted_count", "deleted_bytes", "remaining_candidate_count", "error_count",
    )}))
    if errors:
        raise Error(f"{len(errors)} errors")


if __name__ == "__main__":
    try:
        main()
    except (Error, base.PurgeError, eur_year.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
