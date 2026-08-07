#!/usr/bin/env python3
"""Delete Actions Artifacts only when a durable GitHub Release is proven authoritative.

The controller is intentionally conservative.  It requires:
- a completed successful source workflow run;
- a published non-prerelease Release with immutable-looking SHA-256 asset metadata;
- exact source Artifact evidence in the Release body or small receipt/manifest assets;
- no direct dependency from an active or unresolved development workflow;
- a dry-run candidate digest repeated unchanged for apply;
- post-delete Artifact absence and Release asset readback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

API = "https://api.github.com"
TEXT_SUFFIXES = {".json", ".txt", ".csv", ".md", ".sha256", ".sha256sums", ".yml", ".yaml"}
MAX_TEXT_ASSET_BYTES = 5_000_000
MIN_AGE_SECONDS = 24 * 60 * 60
MAX_RELEASES = 1000
MAX_ARTIFACTS = 20_000
PUBLISHER_TOKENS = (
    "archive", "publish", "publication", "release", "finalize", "receipt", "purge", "audit", "migrate"
)
EVIDENCE_MARKERS = (
    "source_artifact", "source artifact", "artifact_id", "artifact id", "workflow_run",
    "workflow run", "sha256", "sha-256", "readback", "authority", "canonical", "publication_receipt"
)


class PurgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseEvidence:
    release_id: int
    tag: str
    target: str
    published_at: str
    text: str
    assets: tuple[dict[str, Any], ...]
    durable_assets: tuple[dict[str, Any], ...]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    number = float(value)
    unit = 0
    while number >= 1024 and unit < len(units) - 1:
        number /= 1024
        unit += 1
    return f"{number:.2f} {units[unit]}" if unit else f"{int(number)} B"


class GitHubApi:
    def __init__(self, token: str, repository: str) -> None:
        if not token:
            raise PurgeError("GITHUB_TOKEN is required")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise PurgeError("repository must be owner/name")
        self.token = token
        self.repository = repository

    def request(self, method: str, url_or_path: str, *, accept: str = "application/vnd.github+json") -> tuple[bytes, dict[str, str], int]:
        url = url_or_path if url_or_path.startswith("http") else API + url_or_path
        request = urllib.request.Request(url, method=method)
        request.add_header("Authorization", f"Bearer {self.token}")
        request.add_header("Accept", accept)
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        request.add_header("User-Agent", "fx2-release-backed-artifact-purge-v1")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read(), {k.lower(): v for k, v in response.headers.items()}, response.status
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise PurgeError(f"GitHub API {method} {url} failed: {exc.code} {body[:500]}") from exc

    def json(self, path: str) -> Any:
        body, _, _ = self.request("GET", path)
        return json.loads(body.decode("utf-8"))

    def paginate(self, path: str, *, cap: int) -> list[Any]:
        output: list[Any] = []
        page = 1
        separator = "&" if "?" in path else "?"
        while True:
            current = f"{path}{separator}per_page=100&page={page}"
            value = self.json(current)
            if isinstance(value, dict):
                rows = value.get("artifacts") or value.get("workflow_runs") or []
            elif isinstance(value, list):
                rows = value
            else:
                raise PurgeError(f"unexpected paginated response for {path}")
            if not isinstance(rows, list):
                raise PurgeError(f"invalid pagination rows for {path}")
            output.extend(rows)
            if len(output) > cap:
                raise PurgeError(f"pagination safety cap exceeded for {path}: {len(output)}")
            if len(rows) < 100:
                return output
            page += 1

    def download_asset_text(self, asset: dict[str, Any]) -> str:
        size = int(asset.get("size") or 0)
        if size <= 0 or size > MAX_TEXT_ASSET_BYTES:
            return ""
        suffix = Path(str(asset.get("name") or "")).suffix.lower()
        if suffix not in TEXT_SUFFIXES and "manifest" not in str(asset.get("name") or "").lower() and "receipt" not in str(asset.get("name") or "").lower():
            return ""
        body, _, _ = self.request("GET", str(asset["url"]), accept="application/octet-stream")
        if len(body) > MAX_TEXT_ASSET_BYTES:
            return ""
        return body.decode("utf-8", errors="replace")

    def delete_artifact(self, artifact_id: int) -> None:
        self.request("DELETE", f"/repos/{self.repository}/actions/artifacts/{artifact_id}")


def parse_utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_workflow_classification(root: Path) -> dict[str, str]:
    path = root / "artifacts/research/fx2_environment_consolidation_001/workflow_classification.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for row in value.get("workflows", []):
        if isinstance(row, dict) and isinstance(row.get("path"), str) and isinstance(row.get("classification"), str):
            result[row["path"]] = row["classification"]
    return result


def iter_dependency_files(root: Path, classification: dict[str, str]) -> Iterable[tuple[str, str]]:
    for directory in (".github/workflows", "tools", "scripts"):
        base = root / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".yml", ".yaml", ".py", ".sh", ".ps1", ".js", ".json"}:
                continue
            relative = path.relative_to(root).as_posix()
            lower = relative.lower()
            if any(token in lower for token in PUBLISHER_TOKENS):
                continue
            if relative.startswith(".github/workflows/"):
                state = classification.get(relative, "UNKNOWN_REQUIRES_REVIEW")
                if state not in {"ACTIVE_STUDY_WRAPPER", "UNKNOWN_REQUIRES_REVIEW"}:
                    continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            yield relative, text


def list_release_evidence(api: GitHubApi) -> list[ReleaseEvidence]:
    releases = api.paginate(f"/repos/{api.repository}/releases?", cap=MAX_RELEASES)
    output: list[ReleaseEvidence] = []
    for release in releases:
        if release.get("draft") is True or release.get("prerelease") is True:
            continue
        tag = str(release.get("tag_name") or "")
        published_at = str(release.get("published_at") or "")
        if not tag or not published_at:
            continue
        assets = tuple(asset for asset in release.get("assets", []) if isinstance(asset, dict) and asset.get("state") == "uploaded")
        durable = tuple(
            asset for asset in assets
            if int(asset.get("size") or 0) > 0 and re.fullmatch(r"sha256:[0-9a-f]{64}", str(asset.get("digest") or ""), flags=re.I)
        )
        if not durable:
            continue
        pieces = [str(release.get("body") or ""), tag, str(release.get("name") or "")]
        for asset in assets:
            text = api.download_asset_text(asset)
            if text:
                pieces.append(text)
        combined = "\n".join(pieces)
        if not any(marker in combined.lower() for marker in EVIDENCE_MARKERS):
            continue
        output.append(ReleaseEvidence(
            release_id=int(release["id"]),
            tag=tag,
            target=str(release.get("target_commitish") or ""),
            published_at=published_at,
            text=combined,
            assets=assets,
            durable_assets=durable,
        ))
    return output


def artifact_release_match(artifact: dict[str, Any], releases: list[ReleaseEvidence]) -> tuple[ReleaseEvidence, dict[str, bool]] | None:
    artifact_id = str(artifact.get("id") or "")
    name = str(artifact.get("name") or "")
    run_id = str((artifact.get("workflow_run") or {}).get("id") or "")
    digest = str(artifact.get("digest") or "")
    choices: list[tuple[int, ReleaseEvidence, dict[str, bool]]] = []
    for release in releases:
        text = release.text
        hits = {
            "artifact_id": bool(artifact_id and re.search(rf"(?<!\d){re.escape(artifact_id)}(?!\d)", text)),
            "artifact_name": bool(name and name in text),
            "run_id": bool(run_id and re.search(rf"(?<!\d){re.escape(run_id)}(?!\d)", text)),
            "artifact_digest": bool(digest and digest in text),
        }
        score = sum(1 for value in hits.values() if value)
        strong = (
            hits["artifact_id"] and (hits["artifact_name"] or hits["run_id"] or hits["artifact_digest"])
        ) or (
            hits["artifact_name"] and hits["run_id"] and hits["artifact_digest"]
        )
        if strong:
            choices.append((score, release, hits))
    if not choices:
        return None
    choices.sort(key=lambda row: (row[0], row[1].published_at), reverse=True)
    return choices[0][1], choices[0][2]


def dependency_refs(artifact: dict[str, Any], files: list[tuple[str, str]]) -> list[str]:
    terms = [
        str(artifact.get("id") or ""),
        str((artifact.get("workflow_run") or {}).get("id") or ""),
        str(artifact.get("name") or ""),
    ]
    refs: list[str] = []
    for path, text in files:
        if any(term and term in text for term in terms):
            refs.append(path)
    return sorted(set(refs))


def validate_release_readback(api: GitHubApi, release: ReleaseEvidence) -> None:
    current = api.json(f"/repos/{api.repository}/releases/{release.release_id}")
    if current.get("draft") is True or current.get("prerelease") is True or current.get("tag_name") != release.tag:
        raise PurgeError(f"Release changed or is no longer stable: {release.tag}")
    expected = {int(asset["id"]): (int(asset.get("size") or 0), str(asset.get("digest") or "")) for asset in release.durable_assets}
    observed = {
        int(asset["id"]): (int(asset.get("size") or 0), str(asset.get("digest") or ""))
        for asset in current.get("assets", []) if isinstance(asset, dict)
    }
    for asset_id, identity in expected.items():
        if observed.get(asset_id) != identity:
            raise PurgeError(f"Release asset readback mismatch: {release.tag} asset {asset_id}")


def build_candidates(api: GitHubApi, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    artifacts = api.paginate(f"/repos/{api.repository}/actions/artifacts?", cap=MAX_ARTIFACTS)
    releases = list_release_evidence(api)
    classification = load_workflow_classification(root)
    files = list(iter_dependency_files(root, classification))
    now = datetime.now(timezone.utc)
    candidates: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    run_cache: dict[int, dict[str, Any]] = {}

    for artifact in artifacts:
        if artifact.get("expired") is True:
            continue
        created = parse_utc(str(artifact.get("created_at")))
        if (now - created).total_seconds() < MIN_AGE_SECONDS:
            continue
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(artifact.get("digest") or ""), flags=re.I):
            continue
        run_id = int((artifact.get("workflow_run") or {}).get("id") or 0)
        if run_id <= 0:
            continue
        match = artifact_release_match(artifact, releases)
        if match is None:
            continue
        release, hits = match
        refs = dependency_refs(artifact, files)
        if refs:
            blocked.append({
                "artifact_id": int(artifact["id"]),
                "artifact_name": artifact["name"],
                "bytes": int(artifact.get("size_in_bytes") or 0),
                "run_id": run_id,
                "release_tag": release.tag,
                "dependency_refs": refs[:20],
            })
            continue
        if run_id not in run_cache:
            run_cache[run_id] = api.json(f"/repos/{api.repository}/actions/runs/{run_id}")
        run = run_cache[run_id]
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            blocked.append({
                "artifact_id": int(artifact["id"]),
                "artifact_name": artifact["name"],
                "bytes": int(artifact.get("size_in_bytes") or 0),
                "run_id": run_id,
                "release_tag": release.tag,
                "dependency_refs": [f"run_not_success:{run.get('status')}/{run.get('conclusion')}"],
            })
            continue
        candidates.append({
            "artifact_id": int(artifact["id"]),
            "artifact_name": str(artifact["name"]),
            "bytes": int(artifact.get("size_in_bytes") or 0),
            "artifact_digest": str(artifact["digest"]),
            "created_at": str(artifact["created_at"]),
            "run_id": run_id,
            "workflow_name": str(run.get("name") or ""),
            "head_sha": str(run.get("head_sha") or ""),
            "release_id": release.release_id,
            "release_tag": release.tag,
            "release_target": release.target,
            "release_asset_ids": [int(asset["id"]) for asset in release.durable_assets],
            "release_asset_identity_sha256": sha256_json([
                {"id": int(asset["id"]), "name": asset["name"], "size": int(asset["size"]), "digest": asset["digest"]}
                for asset in release.durable_assets
            ]),
            "evidence_hits": hits,
        })

    candidates.sort(key=lambda row: (row["release_tag"], row["artifact_id"]))
    blocked.sort(key=lambda row: row["bytes"], reverse=True)
    metadata = {
        "artifact_count": len(artifacts),
        "release_evidence_count": len(releases),
        "dependency_file_count": len(files),
    }
    return candidates, blocked, metadata


def receipt_for(mode: str, repository: str, candidates: list[dict[str, Any]], blocked: list[dict[str, Any]], metadata: dict[str, Any], deleted: list[int], remaining_ids: set[int], errors: list[str]) -> dict[str, Any]:
    identity = [
        {key: row[key] for key in ("artifact_id", "artifact_name", "bytes", "artifact_digest", "run_id", "release_id", "release_tag", "release_asset_identity_sha256")}
        for row in candidates
    ]
    return {
        "schema_version": "fx2_release_backed_artifact_purge_receipt_v1",
        "mode": mode,
        "repository": repository,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **metadata,
        "candidate_count": len(candidates),
        "candidate_bytes": sum(row["bytes"] for row in candidates),
        "candidate_digest": sha256_json(identity),
        "blocked_count": len(blocked),
        "blocked_bytes": sum(row["bytes"] for row in blocked),
        "deleted_count": len(deleted),
        "deleted_bytes": sum(row["bytes"] for row in candidates if row["artifact_id"] in set(deleted)),
        "remaining_candidate_count": sum(1 for row in candidates if row["artifact_id"] in remaining_ids),
        "error_count": len(errors),
        "errors": errors,
        "candidates": candidates,
        "blocked": blocked,
    }


def render_markdown(receipt: dict[str, Any], *, limit: int = 80) -> str:
    lines = [
        "## FX2 Release-backed Artifact Purge",
        "",
        f"- Mode: `{receipt['mode']}`",
        f"- Release evidence sets: `{receipt['release_evidence_count']}`",
        f"- Selected: `{receipt['candidate_count']}` ({format_bytes(receipt['candidate_bytes'])})",
        f"- Blocked by live dependency or run state: `{receipt['blocked_count']}` ({format_bytes(receipt['blocked_bytes'])})",
        f"- Deleted: `{receipt['deleted_count']}` ({format_bytes(receipt['deleted_bytes'])})",
        f"- Remaining selected after readback: `{receipt['remaining_candidate_count']}`",
        f"- Candidate digest: `{receipt['candidate_digest']}`",
        f"- Errors: `{receipt['error_count']}`",
        "",
        "| Artifact | Run | Release | Size | Evidence |",
        "|---|---:|---|---:|---|",
    ]
    for row in receipt["candidates"][:limit]:
        hits = ",".join(key for key, value in row["evidence_hits"].items() if value)
        lines.append(f"| `{row['artifact_name']}` (`{row['artifact_id']}`) | {row['run_id']} | `{row['release_tag']}` | {format_bytes(row['bytes'])} | {hits} |")
    if len(receipt["candidates"]) > limit:
        lines.append(f"\n_Additional candidates omitted from comment: {len(receipt['candidates']) - limit}_")
    if receipt["blocked"]:
        lines.extend(["", "### Largest blocked items", "", "| Artifact | Release | Size | Blocking reference |", "|---|---|---:|---|"])
        for row in receipt["blocked"][:20]:
            refs = "<br>".join(f"`{value}`" for value in row["dependency_refs"][:5])
            lines.append(f"| `{row['artifact_name']}` (`{row['artifact_id']}`) | `{row['release_tag']}` | {format_bytes(row['bytes'])} | {refs} |")
    summary = {key: receipt[key] for key in (
        "schema_version", "mode", "repository", "generated_at", "artifact_count", "release_evidence_count",
        "dependency_file_count", "candidate_count", "candidate_bytes", "candidate_digest", "blocked_count",
        "blocked_bytes", "deleted_count", "deleted_bytes", "remaining_candidate_count", "error_count", "errors"
    )}
    lines.extend(["", "<details><summary>Machine-readable summary</summary>", "", "```json", canonical_json(summary), "```", "</details>"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "apply"), required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--expected-candidate-digest")
    parser.add_argument("--max-deletions", type=int, default=2000)
    parser.add_argument("--max-bytes", type=int, default=20_000_000_000)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    api = GitHubApi(os.environ.get("GITHUB_TOKEN", ""), args.repository)
    candidates, blocked, metadata = build_candidates(api, Path(args.root).resolve())
    if len(candidates) > args.max_deletions:
        raise PurgeError(f"candidate count exceeds safety cap: {len(candidates)} > {args.max_deletions}")
    total_bytes = sum(row["bytes"] for row in candidates)
    if total_bytes > args.max_bytes:
        raise PurgeError(f"candidate bytes exceed safety cap: {total_bytes} > {args.max_bytes}")

    identity = [
        {key: row[key] for key in ("artifact_id", "artifact_name", "bytes", "artifact_digest", "run_id", "release_id", "release_tag", "release_asset_identity_sha256")}
        for row in candidates
    ]
    candidate_digest = sha256_json(identity)
    if args.mode == "apply":
        if not args.expected_candidate_digest or args.expected_candidate_digest != candidate_digest:
            raise PurgeError(f"candidate digest mismatch: expected={args.expected_candidate_digest!r} observed={candidate_digest}")
        release_map: dict[int, ReleaseEvidence] = {}
        for release in list_release_evidence(api):
            if release.release_id in {row["release_id"] for row in candidates}:
                release_map[release.release_id] = release
        if len(release_map) != len({row["release_id"] for row in candidates}):
            raise PurgeError("release evidence set changed before deletion")
        for release in release_map.values():
            validate_release_readback(api, release)

    deleted: list[int] = []
    errors: list[str] = []
    if args.mode == "apply":
        for row in candidates:
            try:
                api.delete_artifact(row["artifact_id"])
                deleted.append(row["artifact_id"])
            except PurgeError as exc:
                errors.append(f"artifact {row['artifact_id']}: {exc}")
        for release_id in sorted({row["release_id"] for row in candidates}):
            try:
                validate_release_readback(api, release_map[release_id])
            except PurgeError as exc:
                errors.append(str(exc))

    after = api.paginate(f"/repos/{api.repository}/actions/artifacts?", cap=MAX_ARTIFACTS)
    remaining_ids = {int(row["id"]) for row in after}
    if args.mode == "apply":
        for artifact_id in deleted:
            if artifact_id in remaining_ids:
                errors.append(f"deleted Artifact still present after readback: {artifact_id}")

    receipt = receipt_for(args.mode, args.repository, candidates, blocked, metadata, deleted, remaining_ids, errors)
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report).write_text(render_markdown(receipt) + "\n", encoding="utf-8")
    print(canonical_json({key: receipt[key] for key in ("candidate_count", "candidate_bytes", "candidate_digest", "blocked_count", "deleted_count", "deleted_bytes", "remaining_candidate_count", "error_count")}))
    if errors:
        raise PurgeError(f"purge completed with {len(errors)} errors")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PurgeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
