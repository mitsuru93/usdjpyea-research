#!/usr/bin/env python3
"""Delete Actions Artifacts whose durable Release archive is proven by a Git receipt.

This controller is for large data authorities where the committed receipt binds the
Actions Artifact IDs/sizes/digests to a published Release whose assets are independent
of Actions retention. It refuses deletion unless all receipt, Release, run, dependency,
candidate-digest, and post-delete readback gates pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import fx2_release_backed_artifact_purge_v1 as base
from tools import fx2_release_backed_artifact_purge_v3 as semantic


class ReceiptPurgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReceiptAuthority:
    path: str
    release_tag: str
    expected_asset_count: int | None
    published_at: str | None
    artifacts: tuple[dict[str, Any], ...]
    receipt_sha256: str


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    number = float(value)
    unit = 0
    while number >= 1024 and unit < len(units) - 1:
        number /= 1024
        unit += 1
    return f"{number:.2f} {units[unit]}" if unit else f"{int(number)} B"


def parse_artifact_node(node: Any, output: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        artifact_id = node.get("id")
        size = node.get("size_bytes")
        digest = node.get("sha256")
        if isinstance(artifact_id, int) and isinstance(size, int) and isinstance(digest, str):
            digest = digest.removeprefix("sha256:").lower()
            if re.fullmatch(r"[0-9a-f]{64}", digest):
                row = {
                    "artifact_id": artifact_id,
                    "expected_bytes": size,
                    "expected_digest": f"sha256:{digest}",
                }
                if isinstance(node.get("name"), str) and node["name"]:
                    row["expected_name"] = node["name"]
                if isinstance(node.get("month"), str):
                    row["receipt_month"] = node["month"]
                output.append(row)
        for value in node.values():
            parse_artifact_node(value, output)
    elif isinstance(node, list):
        for value in node:
            parse_artifact_node(value, output)


def receipt_is_authoritative(value: dict[str, Any]) -> bool:
    durable = value.get("durable_release")
    if not isinstance(durable, dict) or not isinstance(durable.get("tag"), str):
        return False
    status = str(value.get("archive_status") or "").lower()
    expiry_independent = durable.get("actions_artifact_expiry_independent") is True
    durable_status = "durably_archived" in status and "release" in status
    accepted = value.get("annual_validation", {}).get("accepted") is True if isinstance(value.get("annual_validation"), dict) else False
    return (expiry_independent or durable_status) and accepted


def load_authorities(root: Path, requested_paths: set[str] | None) -> list[ReceiptAuthority]:
    authorities: list[ReceiptAuthority] = []
    candidates = sorted(root.rglob("receipt.json"))
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        if requested_paths is not None and relative not in requested_paths:
            continue
        if path.stat().st_size > 5_000_000:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or not receipt_is_authoritative(value):
            continue
        artifacts: list[dict[str, Any]] = []
        parse_artifact_node(value.get("actions_artifacts"), artifacts)
        unique = {row["artifact_id"]: row for row in artifacts}
        if not unique:
            continue
        durable = value["durable_release"]
        expected_count = durable.get("asset_count") if isinstance(durable.get("asset_count"), int) else None
        authorities.append(
            ReceiptAuthority(
                path=relative,
                release_tag=durable["tag"],
                expected_asset_count=expected_count,
                published_at=durable.get("published_at_utc") if isinstance(durable.get("published_at_utc"), str) else None,
                artifacts=tuple(unique[key] for key in sorted(unique)),
                receipt_sha256=file_sha256(path),
            )
        )
    if requested_paths is not None:
        found = {authority.path for authority in authorities}
        missing = sorted(requested_paths - found)
        if missing:
            raise ReceiptPurgeError(f"requested authoritative receipts not found: {missing}")
    return authorities


def stable_release_identity(api: base.GitHubApi, authority: ReceiptAuthority) -> dict[str, Any]:
    encoded = __import__("urllib.parse").parse.quote(authority.release_tag, safe="")
    release = api.json(f"/repos/{api.repository}/releases/tags/{encoded}")
    if release.get("draft") is True or release.get("prerelease") is True:
        raise ReceiptPurgeError(f"Release is not stable: {authority.release_tag}")
    if release.get("tag_name") != authority.release_tag:
        raise ReceiptPurgeError(f"Release tag mismatch: {authority.release_tag}")
    if authority.published_at and release.get("published_at") != authority.published_at:
        raise ReceiptPurgeError(
            f"Release publication timestamp mismatch for {authority.release_tag}: "
            f"{release.get('published_at')} != {authority.published_at}"
        )
    assets = [asset for asset in release.get("assets", []) if isinstance(asset, dict)]
    if authority.expected_asset_count is not None and len(assets) != authority.expected_asset_count:
        raise ReceiptPurgeError(
            f"Release asset count mismatch for {authority.release_tag}: "
            f"{len(assets)} != {authority.expected_asset_count}"
        )
    identities: list[dict[str, Any]] = []
    for asset in assets:
        digest = str(asset.get("digest") or "")
        if asset.get("state") != "uploaded" or int(asset.get("size") or 0) <= 0:
            raise ReceiptPurgeError(f"Release has incomplete asset: {authority.release_tag}/{asset.get('name')}")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest, flags=re.I):
            raise ReceiptPurgeError(f"Release asset lacks SHA-256 digest: {authority.release_tag}/{asset.get('name')}")
        identities.append(
            {
                "id": int(asset["id"]),
                "name": str(asset["name"]),
                "size": int(asset["size"]),
                "digest": digest.lower(),
            }
        )
    identities.sort(key=lambda row: row["id"])
    return {
        "release_id": int(release["id"]),
        "tag": authority.release_tag,
        "published_at": str(release.get("published_at") or ""),
        "asset_count": len(identities),
        "asset_identity_sha256": sha256_json(identities),
        "assets": identities,
    }


def artifact_inventory(api: base.GitHubApi) -> dict[int, dict[str, Any]]:
    artifacts = api.paginate(f"/repos/{api.repository}/actions/artifacts?", cap=20_000)
    return {int(row["id"]): row for row in artifacts if isinstance(row, dict) and isinstance(row.get("id"), int)}


def build_candidates(
    api: base.GitHubApi,
    root: Path,
    requested_paths: set[str] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    authorities = load_authorities(root, requested_paths)
    inventory = artifact_inventory(api)
    classification = base.load_workflow_classification(root)
    dependency_files = list(base.iter_dependency_files(root, classification))
    releases: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    run_cache: dict[int, dict[str, Any]] = {}

    for authority in authorities:
        release_identity = stable_release_identity(api, authority)
        releases.append({
            "receipt_path": authority.path,
            "receipt_sha256": authority.receipt_sha256,
            **{key: release_identity[key] for key in ("release_id", "tag", "published_at", "asset_count", "asset_identity_sha256")},
        })
        for expected in authority.artifacts:
            artifact_id = expected["artifact_id"]
            artifact = inventory.get(artifact_id)
            if artifact is None:
                continue
            errors: list[str] = []
            if int(artifact.get("size_in_bytes") or -1) != expected["expected_bytes"]:
                errors.append("size_mismatch")
            if str(artifact.get("digest") or "").lower() != expected["expected_digest"]:
                errors.append("digest_mismatch")
            if expected.get("expected_name") and artifact.get("name") != expected["expected_name"]:
                errors.append("name_mismatch")
            if artifact.get("expired") is True:
                errors.append("artifact_expired_before_controlled_delete")
            run_id = int((artifact.get("workflow_run") or {}).get("id") or 0)
            if run_id <= 0:
                errors.append("missing_workflow_run")
            if errors:
                raise ReceiptPurgeError(
                    f"receipt/current Artifact mismatch for {authority.path} Artifact {artifact_id}: {errors}"
                )
            if run_id not in run_cache:
                run_cache[run_id] = api.json(f"/repos/{api.repository}/actions/runs/{run_id}")
            run = run_cache[run_id]
            refs = semantic.semantic_dependency_refs(artifact, dependency_files)
            run_ok = run.get("status") == "completed" and run.get("conclusion") == "success"
            row = {
                "artifact_id": artifact_id,
                "artifact_name": str(artifact.get("name") or ""),
                "bytes": int(artifact["size_in_bytes"]),
                "artifact_digest": str(artifact["digest"]).lower(),
                "run_id": run_id,
                "workflow_name": str(run.get("name") or ""),
                "head_sha": str(run.get("head_sha") or ""),
                "receipt_path": authority.path,
                "receipt_sha256": authority.receipt_sha256,
                "release_id": release_identity["release_id"],
                "release_tag": authority.release_tag,
                "release_asset_count": release_identity["asset_count"],
                "release_asset_identity_sha256": release_identity["asset_identity_sha256"],
            }
            if refs or not run_ok:
                row["blocking_reasons"] = refs or [f"run_not_success:{run.get('status')}/{run.get('conclusion')}"]
                blocked.append(row)
            else:
                candidates.append(row)

    candidates.sort(key=lambda row: (row["receipt_path"], row["artifact_id"]))
    blocked.sort(key=lambda row: row["bytes"], reverse=True)
    releases.sort(key=lambda row: row["tag"])
    metadata = {
        "authority_count": len(authorities),
        "release_count": len(releases),
        "inventory_artifact_count": len(inventory),
        "dependency_file_count": len(dependency_files),
    }
    return candidates, blocked, releases, metadata


def candidate_identity(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = (
        "artifact_id", "artifact_name", "bytes", "artifact_digest", "run_id",
        "receipt_path", "receipt_sha256", "release_id", "release_tag",
        "release_asset_count", "release_asset_identity_sha256",
    )
    return [{key: row[key] for key in keys} for row in candidates]


def render_report(receipt: dict[str, Any]) -> str:
    lines = [
        "## FX2 Archive-receipt-backed Artifact Purge",
        "",
        f"- Mode: `{receipt['mode']}`",
        f"- Authoritative receipts: `{receipt['authority_count']}`",
        f"- Stable Releases: `{receipt['release_count']}`",
        f"- Selected: `{receipt['candidate_count']}` ({format_bytes(receipt['candidate_bytes'])})",
        f"- Blocked: `{receipt['blocked_count']}` ({format_bytes(receipt['blocked_bytes'])})",
        f"- Deleted: `{receipt['deleted_count']}` ({format_bytes(receipt['deleted_bytes'])})",
        f"- Remaining selected after readback: `{receipt['remaining_candidate_count']}`",
        f"- Candidate digest: `{receipt['candidate_digest']}`",
        f"- Errors: `{receipt['error_count']}`",
        "",
        "| Artifact | Receipt | Release | Run | Size |",
        "|---|---|---|---:|---:|",
    ]
    for row in receipt["candidates"]:
        lines.append(
            f"| `{row['artifact_name']}` (`{row['artifact_id']}`) | `{row['receipt_path']}` | "
            f"`{row['release_tag']}` | {row['run_id']} | {format_bytes(row['bytes'])} |"
        )
    if receipt["blocked"]:
        lines.extend(["", "### Blocked", "", "| Artifact | Size | Reason |", "|---|---:|---|"])
        for row in receipt["blocked"][:30]:
            reasons = "<br>".join(f"`{value}`" for value in row["blocking_reasons"][:8])
            lines.append(f"| `{row['artifact_name']}` (`{row['artifact_id']}`) | {format_bytes(row['bytes'])} | {reasons} |")
    summary_keys = (
        "schema_version", "mode", "repository", "generated_at", "authority_count", "release_count",
        "inventory_artifact_count", "dependency_file_count", "candidate_count", "candidate_bytes",
        "candidate_digest", "blocked_count", "blocked_bytes", "deleted_count", "deleted_bytes",
        "remaining_candidate_count", "error_count", "errors",
    )
    lines.extend([
        "", "<details><summary>Machine-readable summary</summary>", "", "```json",
        canonical_json({key: receipt[key] for key in summary_keys}), "```", "</details>",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "apply"), required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--receipt-path", action="append", default=[])
    parser.add_argument("--expected-candidate-digest")
    parser.add_argument("--max-deletions", type=int, default=1000)
    parser.add_argument("--max-bytes", type=int, default=20_000_000_000)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    api = base.GitHubApi(os.environ.get("GITHUB_TOKEN", ""), args.repository)
    requested = set(args.receipt_path) if args.receipt_path else None
    candidates, blocked, releases, metadata = build_candidates(api, Path(args.root).resolve(), requested)
    if len(candidates) > args.max_deletions:
        raise ReceiptPurgeError(f"candidate count exceeds cap: {len(candidates)} > {args.max_deletions}")
    candidate_bytes = sum(row["bytes"] for row in candidates)
    if candidate_bytes > args.max_bytes:
        raise ReceiptPurgeError(f"candidate bytes exceed cap: {candidate_bytes} > {args.max_bytes}")
    digest = sha256_json(candidate_identity(candidates))
    if args.mode == "apply" and args.expected_candidate_digest != digest:
        raise ReceiptPurgeError(
            f"candidate digest mismatch: expected={args.expected_candidate_digest!r} observed={digest}"
        )

    # Re-read every receipt and Release immediately before apply. Any mutation changes the digest.
    if args.mode == "apply":
        second_candidates, second_blocked, second_releases, _ = build_candidates(
            api, Path(args.root).resolve(), requested
        )
        if sha256_json(candidate_identity(second_candidates)) != digest:
            raise ReceiptPurgeError("candidate set changed during pre-delete revalidation")
        if canonical_json(second_releases) != canonical_json(releases):
            raise ReceiptPurgeError("Release identity changed during pre-delete revalidation")
        if canonical_json(second_blocked) != canonical_json(blocked):
            raise ReceiptPurgeError("blocked set changed during pre-delete revalidation")

    deleted: list[int] = []
    errors: list[str] = []
    if args.mode == "apply":
        for row in candidates:
            try:
                api.delete_artifact(row["artifact_id"])
                deleted.append(row["artifact_id"])
            except base.PurgeError as exc:
                errors.append(f"Artifact {row['artifact_id']}: {exc}")

    after = artifact_inventory(api)
    remaining = {row["artifact_id"] for row in candidates if row["artifact_id"] in after}
    for artifact_id in deleted:
        if artifact_id in remaining:
            errors.append(f"deleted Artifact still present: {artifact_id}")

    # Release identities must remain byte-for-byte stable after deletion.
    post_releases: list[dict[str, Any]] = []
    for authority in load_authorities(Path(args.root).resolve(), requested):
        identity = stable_release_identity(api, authority)
        post_releases.append({
            "receipt_path": authority.path,
            "receipt_sha256": authority.receipt_sha256,
            **{key: identity[key] for key in ("release_id", "tag", "published_at", "asset_count", "asset_identity_sha256")},
        })
    post_releases.sort(key=lambda row: row["tag"])
    if canonical_json(post_releases) != canonical_json(releases):
        errors.append("Release identity changed after Artifact deletion")

    deleted_set = set(deleted)
    receipt = {
        "schema_version": "fx2_archive_receipt_artifact_purge_receipt_v1",
        "mode": args.mode,
        "repository": args.repository,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **metadata,
        "candidate_count": len(candidates),
        "candidate_bytes": candidate_bytes,
        "candidate_digest": digest,
        "blocked_count": len(blocked),
        "blocked_bytes": sum(row["bytes"] for row in blocked),
        "deleted_count": len(deleted),
        "deleted_bytes": sum(row["bytes"] for row in candidates if row["artifact_id"] in deleted_set),
        "remaining_candidate_count": len(remaining),
        "error_count": len(errors),
        "errors": errors,
        "releases": releases,
        "candidates": candidates,
        "blocked": blocked,
    }
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report).write_text(render_report(receipt) + "\n", encoding="utf-8")
    print(canonical_json({
        key: receipt[key]
        for key in (
            "candidate_count", "candidate_bytes", "candidate_digest", "blocked_count",
            "deleted_count", "deleted_bytes", "remaining_candidate_count", "error_count",
        )
    }))
    if errors:
        raise ReceiptPurgeError(f"completed with {len(errors)} errors")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReceiptPurgeError, base.PurgeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
