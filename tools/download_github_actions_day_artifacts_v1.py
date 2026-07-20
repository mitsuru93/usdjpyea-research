#!/usr/bin/env python3
"""Download exact GitHub Actions day-packet artifacts with REST pagination.

`actions/download-artifact` is convenient for small runs, but this project has
more than 100 artifacts in a single collection run. This helper enumerates every
REST page, resolves the exact expected artifact names, downloads each ZIP, and
extracts it with path-traversal checks.
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import shutil
import stat
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

API_ROOT = "https://api.github.com"
USER_AGENT = "usdjpyea-research-artifact-recovery-v1"
REDIRECT_CODES = {301, 302, 303, 307, 308}


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Expose GitHub's signed artifact redirect instead of following it with auth."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def api_request(url: str, token: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        },
    )


def storage_request(url: str) -> urllib.request.Request:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise RuntimeError(f"invalid signed artifact URL: {url!r}")
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def read_json(url: str, token: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(api_request(url, token), timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API HTTP {exc.code} for {url}: {body[:1000]}") from exc


def list_run_artifacts(repository: str, run_id: int, token: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"{API_ROOT}/repos/{repository}/actions/runs/{run_id}/artifacts"
            f"?per_page=100&page={page}"
        )
        payload = read_json(url, token)
        rows = payload.get("artifacts")
        if not isinstance(rows, list):
            raise RuntimeError(f"GitHub artifact response has no artifact list on page {page}")
        artifacts.extend(rows)
        if len(rows) < 100:
            break
        page += 1
        if page > 100:
            raise RuntimeError("artifact pagination exceeded 100 pages")
    return artifacts


def expected_dates(mode: str, month: int, lock_path: Path | None) -> list[str]:
    if mode == "source-month":
        days = calendar.monthrange(2024, month)[1]
        return [date(2024, month, day).isoformat() for day in range(1, days + 1)]
    if lock_path is None:
        raise ValueError("--lock is required for repair-month mode")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    affected = [str(value) for value in lock["repair_scope"]["affected_dates"]]
    selected = sorted(value for value in affected if value.startswith(f"2024-{month:02d}-"))
    if len(selected) != len(set(selected)):
        raise RuntimeError("repair lock contains duplicate affected dates")
    return selected


def expected_name(mode: str, day: str, run_id: int, run_attempt: int) -> str:
    prefix = "usdjpy-raw-ticks-" if mode == "source-month" else "usdjpy-raw-ticks-repair-"
    return f"{prefix}{day}-{run_id}-{run_attempt}"


def safe_extract(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            relative = PurePosixPath(member.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError(f"unsafe artifact ZIP member: {member.filename!r}")
            unix_mode = member.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise RuntimeError(f"symbolic links are not allowed in artifact ZIP: {member.filename!r}")
            target = destination.joinpath(*relative.parts)
            resolved = target.resolve()
            if root != resolved and root not in resolved.parents:
                raise RuntimeError(f"artifact ZIP member escapes destination: {member.filename!r}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)


def resolve_artifact_download_url(repository: str, artifact_id: int, token: str) -> str:
    url = f"{API_ROOT}/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(api_request(url, token), timeout=120) as response:
            location = response.headers.get("Location")
            if location:
                return location
            raise RuntimeError(
                f"GitHub artifact endpoint returned HTTP {response.status} without a redirect for artifact {artifact_id}"
            )
    except urllib.error.HTTPError as exc:
        if exc.code in REDIRECT_CODES:
            location = exc.headers.get("Location")
            if not location:
                raise RuntimeError(
                    f"GitHub artifact redirect has no Location header for artifact {artifact_id}"
                ) from exc
            return location
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub artifact redirect HTTP {exc.code} for artifact {artifact_id}: {body[:1000]}"
        ) from exc


def download_artifact(repository: str, artifact_id: int, token: str, target_zip: Path) -> None:
    signed_url = resolve_artifact_download_url(repository, artifact_id, token)
    request = storage_request(signed_url)
    try:
        with urllib.request.urlopen(request, timeout=300) as response, target_zip.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"signed artifact download HTTP {exc.code} for artifact {artifact_id}: {body[:1000]}"
        ) from exc
    if target_zip.stat().st_size == 0:
        raise RuntimeError(f"downloaded artifact ZIP is empty: {artifact_id}")
    if not zipfile.is_zipfile(target_zip):
        raise RuntimeError(f"downloaded artifact is not a ZIP archive: {artifact_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--month", required=True, type=int, choices=range(1, 13))
    parser.add_argument("--mode", required=True, choices=("source-month", "repair-month"))
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"required token environment variable is empty: {args.token_env}")

    days = expected_dates(args.mode, args.month, args.lock)
    all_artifacts = list_run_artifacts(args.repository, args.run_id, token)
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in all_artifacts:
        by_name.setdefault(str(row.get("name")), []).append(row)

    selected: list[tuple[str, dict[str, Any]]] = []
    failures: list[str] = []
    for day in days:
        name = expected_name(args.mode, day, args.run_id, args.run_attempt)
        matches = by_name.get(name, [])
        if len(matches) != 1:
            failures.append(f"{name}: expected one artifact, found {len(matches)}")
            continue
        artifact = matches[0]
        if bool(artifact.get("expired")):
            failures.append(f"{name}: artifact is expired")
            continue
        selected.append((day, artifact))
    if failures:
        raise SystemExit("artifact selection failed: " + "; ".join(failures))

    args.output.mkdir(parents=True, exist_ok=True)
    receipts: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="gh-artifact-download-") as temp:
        temp_root = Path(temp)
        for day, artifact in selected:
            artifact_id = int(artifact["id"])
            name = str(artifact["name"])
            zip_path = temp_root / f"{artifact_id}.zip"
            print(json.dumps({"event": "download_start", "date": day, "artifact_id": artifact_id, "name": name}))
            download_artifact(args.repository, artifact_id, token, zip_path)
            safe_extract(zip_path, args.output)
            day_root = args.output / day
            required = ("day_summary.json", "download_manifest.jsonl", "SHA256SUMS")
            missing = [item for item in required if not (day_root / item).is_file()]
            if missing:
                raise RuntimeError(f"{name}: extracted day packet missing {missing}")
            receipts.append(
                {
                    "date": day,
                    "artifact_id": artifact_id,
                    "artifact_name": name,
                    "artifact_digest": artifact.get("digest"),
                    "artifact_size_in_bytes": int(artifact.get("size_in_bytes", 0)),
                    "created_at": artifact.get("created_at"),
                    "expired": bool(artifact.get("expired")),
                }
            )

    if len(receipts) != len(days):
        raise RuntimeError(f"downloaded day count mismatch: {len(receipts)} != {len(days)}")
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": "github_actions_day_artifact_download_v1",
        "repository": args.repository,
        "run_id": args.run_id,
        "run_attempt": args.run_attempt,
        "mode": args.mode,
        "month": f"2024-{args.month:02d}",
        "total_artifacts_enumerated": len(all_artifacts),
        "expected_day_count": len(days),
        "downloaded_day_count": len(receipts),
        "artifacts": receipts,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in (
        "repository", "run_id", "run_attempt", "mode", "month",
        "total_artifacts_enumerated", "expected_day_count", "downloaded_day_count"
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
