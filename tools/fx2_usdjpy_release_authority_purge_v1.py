#!/usr/bin/env python3
"""Delete USDJPY Actions Tick copies superseded by accepted Release authorities.

Covered authorities:
- 2019Q4 warmup + 2020-2022 source-native authority Release and committed manifest.
- Complete 2023 raw Bid/Ask monthly Release.
- Complete 2025 raw Bid/Ask monthly Release.

The controller never reads Tick payloads. It validates metadata, SHA-256 identities,
source coverage, live Actions dependencies, a reviewed candidate digest, and remote
readback before deleting Actions copies.
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

SOURCE_NATIVE_TAG = "usdjpy-2020-2022-source-native-bidask-tick-authority-v1"
SOURCE_NATIVE_MANIFEST = "docs/data_authorities/usdjpy_2020_2022_tick_authority_v1/release_manifest.json"
SOURCE_NATIVE_FINAL = "docs/data_authorities/usdjpy_2020_2022_tick_authority_v1/final_result.json"
YEAR_RELEASES = {
    2023: "usdjpy-2023-raw-bidask-ticks-v1",
    2025: "usdjpy-2025-raw-bidask-ticks-v1",
}
COVERED_MONTHS = {(year, month) for year in (2020, 2021, 2022, 2023, 2025) for month in range(1, 13)}
COVERED_MONTHS |= {(2019, 10), (2019, 11), (2019, 12)}


class Error(RuntimeError):
    pass


def cj(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sj(value: Any) -> str:
    return hashlib.sha256(cj(value).encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    number = float(value)
    unit = 0
    while number >= 1024 and unit < len(units) - 1:
        number /= 1024
        unit += 1
    return f"{number:.2f} {units[unit]}" if unit else f"{int(number)} B"


def stable_assets(api: base.GitHubApi, tag: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    release = api.json(f"/repos/{api.repository}/releases/tags/{tag}")
    if release.get("draft") is True or release.get("prerelease") is True or release.get("tag_name") != tag:
        raise Error(f"Release is not stable: {tag}")
    assets: dict[str, dict[str, Any]] = {}
    identities: list[dict[str, Any]] = []
    for asset in release.get("assets", []):
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "")
        digest = str(asset.get("digest") or "").lower()
        size = int(asset.get("size") or 0)
        if not name or asset.get("state") != "uploaded" or size <= 0 or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise Error(f"invalid Release asset: {tag}/{name}")
        if name in assets:
            raise Error(f"duplicate Release asset name: {tag}/{name}")
        row = {"id": int(asset["id"]), "name": name, "size": size, "digest": digest}
        assets[name] = row
        identities.append(row)
    identities.sort(key=lambda row: row["name"])
    identity = {
        "release_id": int(release["id"]),
        "tag": tag,
        "published_at": str(release.get("published_at") or ""),
        "target_commitish": str(release.get("target_commitish") or ""),
        "asset_count": len(identities),
        "asset_identity_sha256": sj(identities),
    }
    return identity, assets


def validate_year_release(api: base.GitHubApi, year: int, tag: str) -> dict[str, Any]:
    identity, assets = stable_assets(api, tag)
    expected = {"SHA256SUMS"}
    expected |= {f"usdjpy-{year}-{month:02d}-raw-ticks-v1.{suffix}" for month in range(1, 13) for suffix in ("tar.gz", "manifest.json", "SHA256SUMS")}
    if set(assets) != expected:
        raise Error(f"year Release inventory mismatch {tag}: missing={sorted(expected-set(assets))} extra={sorted(set(assets)-expected)}")
    return {"authority_type": "complete_year_raw_release", "year": year, **identity}


def validate_source_native(api: base.GitHubApi, root: Path) -> dict[str, Any]:
    manifest_path = root / SOURCE_NATIVE_MANIFEST
    final_path = root / SOURCE_NATIVE_FINAL
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    final_result = json.loads(final_path.read_text(encoding="utf-8"))
    if manifest.get("immutability_contract") != "NO_REUPLOAD_AFTER_FINAL_PUBLICATION":
        raise Error("source-native immutability contract mismatch")
    if manifest.get("work_id") != "USDJPY-DATA-2020-2022-TICK-AUTHORITY-001":
        raise Error("source-native Work ID mismatch")
    if manifest.get("workflow_run_id") != 30513521957 or manifest.get("workflow_run_attempt") != 1:
        raise Error("source-native binding Run mismatch")
    payload = manifest.get("payload_assets")
    metadata_ids = manifest.get("metadata_release_asset_ids")
    if not isinstance(payload, list) or len(payload) < 150 or not isinstance(metadata_ids, dict) or len(metadata_ids) < 10:
        raise Error("source-native manifest is incomplete")
    identity, assets = stable_assets(api, SOURCE_NATIVE_TAG)
    assets_by_id = {row["id"]: row for row in assets.values()}
    months: set[tuple[int, int]] = set()
    seen_ids: set[int] = set()
    for row in payload:
        if not isinstance(row, dict):
            raise Error("invalid source-native payload row")
        year = row.get("year")
        month = row.get("month")
        name = row.get("name")
        asset_id = row.get("release_asset_id")
        size = row.get("bytes")
        digest = row.get("sha256")
        if not isinstance(year, int) or not isinstance(month, int) or not isinstance(name, str) or not isinstance(asset_id, int) or not isinstance(size, int) or not isinstance(digest, str):
            raise Error("source-native payload identity is incomplete")
        if (year, month) not in COVERED_MONTHS or year in (2023, 2025):
            raise Error(f"unexpected source-native period: {year}-{month:02d}")
        if row.get("readback_status") != "PASS_BYTE_IDENTICAL_RELEASE_READBACK" or row.get("readback_bytes") != size or row.get("readback_sha256") != digest:
            raise Error(f"source-native readback mismatch: {name}")
        observed = assets_by_id.get(asset_id)
        if observed != {"id": asset_id, "name": name, "size": size, "digest": f"sha256:{digest.lower()}"):
            raise Error(f"source-native Release asset mismatch: {name}")
        months.add((year, month))
        seen_ids.add(asset_id)
    expected_months = {(year, month) for year in (2020, 2021, 2022) for month in range(1, 13)} | {(2019, 10), (2019, 11), (2019, 12)}
    if months != expected_months:
        raise Error(f"source-native month coverage mismatch: missing={sorted(expected_months-months)} extra={sorted(months-expected_months)}")
    for name, asset_id in metadata_ids.items():
        if not isinstance(name, str) or not isinstance(asset_id, int) or asset_id not in assets_by_id:
            raise Error(f"source-native metadata Release asset mismatch: {name}")
        seen_ids.add(asset_id)
    if len(seen_ids) != identity["asset_count"]:
        raise Error(f"source-native Release has unbound assets: bound={len(seen_ids)} total={identity['asset_count']}")
    return {
        "authority_type": "source_native_tick_authority",
        "covered_month_count": len(expected_months),
        "manifest_sha256": file_sha(manifest_path),
        "final_result_sha256": file_sha(final_path),
        "final_result_identity_sha256": sj(final_result),
        **identity,
    }


def parse_period(name: str) -> tuple[int, int | None] | None:
    lower = name.lower()
    if "usdjpy" not in lower:
        return None
    patterns = (
        r"(?:^|[-_])(20(?:19|20|21|22|23|25))[-_](0[1-9]|1[0-2])(?:[-_]|$)",
        r"(?:^|[-_])(20(?:19|20|21|22|23|25))[-_]raw[-_]ticks[-_]month[-_](0[1-9]|1[0-2])(?:[-_]|$)",
        r"month[-_](0[1-9]|1[0-2])[-_].*?(20(?:19|20|21|22|23|25))",
        r"month[-_]receipt[-_](20(?:19|20|21|22|23|25))[-_](0[1-9]|1[0-2])",
    )
    for index, pattern in enumerate(patterns):
        match = re.search(pattern, lower)
        if not match:
            continue
        if index == 2:
            return int(match.group(2)), int(match.group(1))
        return int(match.group(1)), int(match.group(2))
    year_match = re.search(r"(?:^|[-_])(20(?:19|20|21|22|23|25))(?:[-_]|$)", lower)
    if year_match and any(token in lower for token in ("raw-ticks", "raw_ticks", "tick-authority", "release-receipt")):
        return int(year_match.group(1)), None
    return None


def authority_for_period(year: int, month: int | None, authorities: list[dict[str, Any]]) -> dict[str, Any] | None:
    if month is not None and (year, month) not in COVERED_MONTHS:
        return None
    if year in (2019, 2020, 2021, 2022):
        return next(row for row in authorities if row["tag"] == SOURCE_NATIVE_TAG)
    if year in YEAR_RELEASES:
        return next(row for row in authorities if row.get("year") == year)
    return None


def candidate_identity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = (
        "artifact_id", "artifact_name", "bytes", "artifact_digest", "run_id", "run_conclusion", "head_sha",
        "covered_year", "covered_month", "release_id", "release_tag", "release_asset_identity_sha256",
        "authority_evidence_sha256",
    )
    return [{key: row[key] for key in keys} for row in rows]


def build(api: base.GitHubApi, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    authorities = [validate_source_native(api, root)]
    authorities.extend(validate_year_release(api, year, tag) for year, tag in YEAR_RELEASES.items())
    authority_rows = []
    for row in authorities:
        evidence = {
            key: row[key]
            for key in sorted(row)
            if key not in {"release_asset_identity_sha256"}
        }
        copy = dict(row)
        copy["authority_evidence_sha256"] = sj(evidence)
        authority_rows.append(copy)
    inventory = api.paginate(f"/repos/{api.repository}/actions/artifacts?", cap=20_000)
    classification = base.load_workflow_classification(root)
    files = list(base.iter_dependency_files(root, classification))
    run_cache: dict[int, dict[str, Any]] = {}
    selected: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for artifact in inventory:
        if not isinstance(artifact, dict) or artifact.get("expired") is True:
            continue
        name = str(artifact.get("name") or "")
        period = parse_period(name)
        if period is None:
            continue
        year, month = period
        authority = authority_for_period(year, month, authority_rows)
        if authority is None:
            continue
        lower = name.lower()
        if not any(token in lower for token in ("raw-ticks", "raw_ticks", "tick-authority", "release-receipt")):
            continue
        artifact_id = int(artifact.get("id") or 0)
        size = int(artifact.get("size_in_bytes") or 0)
        digest = str(artifact.get("digest") or "").lower()
        run_id = int((artifact.get("workflow_run") or {}).get("id") or 0)
        if artifact_id <= 0 or size <= 0 or run_id <= 0 or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise Error(f"invalid Actions Artifact identity: {artifact_id}/{name}")
        if run_id not in run_cache:
            run_cache[run_id] = api.json(f"/repos/{api.repository}/actions/runs/{run_id}")
        run = run_cache[run_id]
        if run.get("status") != "completed":
            row = {"artifact_id": artifact_id, "artifact_name": name, "bytes": size, "blocking_reasons": [f"run_not_completed:{run.get('status')}"]}
            blocked.append(row)
            continue
        row = {
            "artifact_id": artifact_id,
            "artifact_name": name,
            "bytes": size,
            "artifact_digest": digest,
            "run_id": run_id,
            "run_conclusion": str(run.get("conclusion") or ""),
            "head_sha": str(run.get("head_sha") or ""),
            "covered_year": year,
            "covered_month": month,
            "release_id": authority["release_id"],
            "release_tag": authority["tag"],
            "release_asset_identity_sha256": authority["asset_identity_sha256"],
            "authority_evidence_sha256": authority["authority_evidence_sha256"],
        }
        refs = semantic.semantic_dependency_refs(artifact, files)
        if refs:
            row["blocking_reasons"] = refs
            blocked.append(row)
        else:
            selected.append(row)
    selected.sort(key=lambda row: (row["covered_year"], row["covered_month"] or 0, row["artifact_id"]))
    blocked.sort(key=lambda row: row["bytes"], reverse=True)
    authority_rows.sort(key=lambda row: row["tag"])
    return selected, blocked, authority_rows, {
        "inventory_artifact_count": len(inventory),
        "dependency_file_count": len(files),
        "source_run_count": len(run_cache),
    }


def report(receipt: dict[str, Any]) -> str:
    lines = [
        "## FX2 USDJPY Release-authority Artifact Purge", "",
        f"- Mode: `{receipt['mode']}`",
        f"- Authorities: `{receipt['authority_count']}`",
        f"- Selected: `{receipt['candidate_count']}` ({fmt_bytes(receipt['candidate_bytes'])})",
        f"- Blocked: `{receipt['blocked_count']}` ({fmt_bytes(receipt['blocked_bytes'])})",
        f"- Deleted: `{receipt['deleted_count']}` ({fmt_bytes(receipt['deleted_bytes'])})",
        f"- Remaining selected: `{receipt['remaining_candidate_count']}`",
        f"- Candidate digest: `{receipt['candidate_digest']}`",
        f"- Errors: `{receipt['error_count']}`", "",
        "| Artifact | Period | Authority | Run | Conclusion | Size |",
        "|---|---|---|---:|---|---:|",
    ]
    for row in receipt["candidates"][:300]:
        period = f"{row['covered_year']}-{row['covered_month']:02d}" if row["covered_month"] else str(row["covered_year"])
        lines.append(f"| `{row['artifact_name']}` (`{row['artifact_id']}`) | {period} | `{row['release_tag']}` | {row['run_id']} | `{row['run_conclusion']}` | {fmt_bytes(row['bytes'])} |")
    if len(receipt["candidates"]) > 300:
        lines.append(f"\n_Additional selected rows omitted: {len(receipt['candidates'])-300}_")
    if receipt["blocked"]:
        lines.extend(["", "### Blocked", "", "| Artifact | Size | Reason |", "|---|---:|---|"])
        for row in receipt["blocked"][:50]:
            reasons = "<br>".join(f"`{value}`" for value in row.get("blocking_reasons", [])[:8])
            lines.append(f"| `{row['artifact_name']}` (`{row['artifact_id']}`) | {fmt_bytes(row['bytes'])} | {reasons} |")
    summary_keys = (
        "schema_version", "mode", "repository", "generated_at", "authority_count", "inventory_artifact_count",
        "dependency_file_count", "source_run_count", "candidate_count", "candidate_bytes", "candidate_digest",
        "blocked_count", "blocked_bytes", "deleted_count", "deleted_bytes", "remaining_candidate_count",
        "error_count", "errors",
    )
    lines.extend(["", "<details><summary>Machine-readable summary</summary>", "", "```json", cj({key: receipt[key] for key in summary_keys}), "```", "</details>"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "apply"), required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--expected-candidate-digest")
    parser.add_argument("--max-deletions", type=int, default=5000)
    parser.add_argument("--max-bytes", type=int, default=15_000_000_000)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    api = base.GitHubApi(os.environ.get("GITHUB_TOKEN", ""), args.repository)
    root = Path(args.root).resolve()
    candidates, blocked, authorities, metadata = build(api, root)
    digest = sj(candidate_identity(candidates))
    total = sum(row["bytes"] for row in candidates)
    if len(candidates) > args.max_deletions or total > args.max_bytes:
        raise Error(f"safety cap exceeded: count={len(candidates)} bytes={total}")
    if args.mode == "apply":
        if args.expected_candidate_digest != digest:
            raise Error(f"candidate digest mismatch: expected={args.expected_candidate_digest!r} observed={digest}")
        second, second_blocked, second_authorities, _ = build(api, root)
        if sj(candidate_identity(second)) != digest or cj(second_blocked) != cj(blocked) or cj(second_authorities) != cj(authorities):
            raise Error("pre-delete evidence changed")
    deleted: list[int] = []
    errors: list[str] = []
    if args.mode == "apply":
        for row in candidates:
            try:
                api.delete_artifact(row["artifact_id"])
                deleted.append(row["artifact_id"])
            except base.PurgeError as exc:
                errors.append(f"Artifact {row['artifact_id']}: {exc}")
    remaining_inventory = {int(row["id"]) for row in api.paginate(f"/repos/{api.repository}/actions/artifacts?", cap=20_000)}
    remaining = {row["artifact_id"] for row in candidates if row["artifact_id"] in remaining_inventory}
    for artifact_id in deleted:
        if artifact_id in remaining:
            errors.append(f"deleted Artifact still present: {artifact_id}")
    post_candidates, post_blocked, post_authorities, _ = build(api, root)
    if cj(post_authorities) != cj(authorities):
        errors.append("Release authority identity changed after deletion")
    if args.mode == "apply" and post_candidates:
        errors.append(f"selected Release-backed Artifacts remain after deletion: {len(post_candidates)}")
    deleted_set = set(deleted)
    receipt = {
        "schema_version": "fx2_usdjpy_release_authority_purge_receipt_v1",
        "mode": args.mode,
        "repository": args.repository,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **metadata,
        "authority_count": len(authorities),
        "candidate_count": len(candidates),
        "candidate_bytes": total,
        "candidate_digest": digest,
        "blocked_count": len(blocked),
        "blocked_bytes": sum(row["bytes"] for row in blocked),
        "deleted_count": len(deleted),
        "deleted_bytes": sum(row["bytes"] for row in candidates if row["artifact_id"] in deleted_set),
        "remaining_candidate_count": len(remaining),
        "error_count": len(errors),
        "errors": errors,
        "authorities": authorities,
        "candidates": candidates,
        "blocked": blocked,
        "post_blocked_count": len(post_blocked),
    }
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report).write_text(report(receipt), encoding="utf-8")
    print(cj({key: receipt[key] for key in ("candidate_count", "candidate_bytes", "candidate_digest", "blocked_count", "deleted_count", "deleted_bytes", "remaining_candidate_count", "error_count")}))
    if errors:
        raise Error(f"completed with {len(errors)} errors")


if __name__ == "__main__":
    try:
        main()
    except (Error, base.PurgeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
