#!/usr/bin/env python3
"""Archive accepted USDJPY 2024 GitHub Actions artifacts before expiry.

The script:
- resolves every day-part artifact from the frozen source runs;
- selects monthly aggregate, baseline and reference artifacts by explicit ID;
- records artifact ID, digest and creation/expiry time;
- downloads and verifies each original ZIP;
- packages source ZIPs by month for publication as durable release assets.

It does not inspect or use any 2025 artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tarfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


API_ROOT = "https://api.github.com"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class GitHubAPI:
    def __init__(self, repository: str, token: str) -> None:
        self.repository = repository
        self.token = token
        self._run_cache: dict[int, list[dict[str, Any]]] = {}

    def _request(self, url: str) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "usdjpy-r0-artifact-archive-v1",
            },
        )

    def get_json(self, url: str) -> dict[str, Any]:
        with urllib.request.urlopen(self._request(url), timeout=120) as response:
            return json.load(response)

    def list_run_artifacts(self, run_id: int) -> list[dict[str, Any]]:
        if run_id in self._run_cache:
            return self._run_cache[run_id]

        artifacts: list[dict[str, Any]] = []
        page = 1
        while True:
            payload = self.get_json(
                f"{API_ROOT}/repos/{self.repository}/actions/runs/{run_id}"
                f"/artifacts?per_page=100&page={page}"
            )
            batch = payload.get("artifacts", [])
            artifacts.extend(batch)
            if len(batch) < 100:
                break
            page += 1

        self._run_cache[run_id] = artifacts
        return artifacts

    def get_artifact(self, artifact_id: int) -> dict[str, Any]:
        return self.get_json(
            f"{API_ROOT}/repos/{self.repository}/actions/artifacts/{artifact_id}"
        )

    def download_artifact(self, artifact_id: int, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        request = self._request(
            f"{API_ROOT}/repos/{self.repository}/actions/artifacts/{artifact_id}/zip"
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                with target.open("wb") as handle:
                    shutil.copyfileobj(response, handle, length=1024 * 1024)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"artifact download failed: id={artifact_id}, status={exc.code}"
            ) from exc


def validate_explicit_artifact(
    api: GitHubAPI,
    spec: dict[str, Any],
    role: str,
    month: str | None = None,
) -> dict[str, Any]:
    artifact = api.get_artifact(int(spec["artifact_id"]))
    expected = {
        "name": spec["artifact_name"],
        "digest": spec["digest"],
    }
    for key, value in expected.items():
        if artifact.get(key) != value:
            raise ValueError(
                f"{role} artifact mismatch for {month or '-'}: "
                f"id={spec['artifact_id']} {key}={artifact.get(key)!r}, expected={value!r}"
            )
    if artifact.get("expired"):
        raise ValueError(f"{role} artifact expired: id={spec['artifact_id']}")
    return artifact


def manifest_row(
    artifact: dict[str, Any],
    role: str,
    local_path: Path,
    month: str | None = None,
) -> dict[str, Any]:
    return {
        "role": role,
        "month": month,
        "artifact_id": int(artifact["id"]),
        "artifact_name": artifact["name"],
        "artifact_digest": artifact.get("digest"),
        "created_at": artifact.get("created_at"),
        "updated_at": artifact.get("updated_at"),
        "expires_at": artifact.get("expires_at"),
        "size_in_bytes": artifact.get("size_in_bytes"),
        "archive_file": local_path.name,
        "local_sha256": f"sha256:{sha256_file(local_path)}",
    }


def verify_download(path: Path, artifact: dict[str, Any]) -> None:
    expected_digest = artifact.get("digest")
    if not expected_digest or not expected_digest.startswith("sha256:"):
        raise ValueError(f"missing SHA-256 digest for artifact {artifact['id']}")
    actual = f"sha256:{sha256_file(path)}"
    if actual != expected_digest:
        raise ValueError(
            f"download digest mismatch: id={artifact['id']} "
            f"actual={actual}, expected={expected_digest}"
        )


def create_tar(source_dir: Path, target: Path) -> None:
    with tarfile.open(target, "w:gz", compresslevel=6) as archive:
        for path in sorted(source_dir.iterdir()):
            archive.add(path, arcname=path.name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["year"] != 2024:
        raise ValueError("archive is restricted to 2024")
    if any("2025" in json.dumps(item) for item in config["months"]):
        raise ValueError("2025 reference detected in monthly archive config")

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is required")

    output_dir = args.output_dir
    raw_dir = output_dir / "raw"
    assets_dir = output_dir / "release_assets"
    raw_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    api = GitHubAPI(config["repository"], token)
    manifest: dict[str, Any] = {
        "version": config["version"],
        "repository": config["repository"],
        "year": config["year"],
        "release_tag": config["release_tag"],
        "excluded_artifacts": config["excluded_artifacts"],
        "artifacts": [],
        "source_month_packages": [],
    }

    for month_spec in config["months"]:
        month = month_spec["month"]
        run_id = int(month_spec["source_run_id"])
        day_pattern = re.compile(month_spec["day_artifact_regex"])
        run_artifacts = api.list_run_artifacts(run_id)
        day_artifacts = [
            artifact
            for artifact in run_artifacts
            if day_pattern.fullmatch(artifact["name"])
        ]

        by_name: dict[str, list[dict[str, Any]]] = {}
        for artifact in day_artifacts:
            by_name.setdefault(artifact["name"], []).append(artifact)
        duplicate_names = {
            name: items for name, items in by_name.items() if len(items) != 1
        }
        if duplicate_names:
            detail = {
                name: [
                    {
                        "id": item["id"],
                        "digest": item.get("digest"),
                        "created_at": item.get("created_at"),
                    }
                    for item in items
                ]
                for name, items in duplicate_names.items()
            }
            raise ValueError(f"ambiguous day artifacts for {month}: {detail}")

        expected_count = int(month_spec["expected_day_artifact_count"])
        if len(day_artifacts) != expected_count:
            raise ValueError(
                f"{month}: day artifact count {len(day_artifacts)} != {expected_count}"
            )
        if any(artifact.get("expired") for artifact in day_artifacts):
            raise ValueError(f"{month}: expired day artifact found")

        aggregate = validate_explicit_artifact(
            api, month_spec["source_aggregate"], "source_aggregate", month
        )

        month_dir = raw_dir / "source" / month
        month_dir.mkdir(parents=True, exist_ok=True)
        selected = sorted(day_artifacts, key=lambda item: (item["name"], int(item["id"])))
        selected.append(aggregate)

        for artifact in selected:
            target = month_dir / f"{artifact['id']}__{artifact['name']}.zip"
            api.download_artifact(int(artifact["id"]), target)
            verify_download(target, artifact)
            role = (
                "source_aggregate"
                if int(artifact["id"]) == int(aggregate["id"])
                else "source_day"
            )
            manifest["artifacts"].append(
                manifest_row(artifact, role=role, local_path=target, month=month)
            )

        package = assets_dir / f"usdjpy-{month}-source-artifacts-v1.tar.gz"
        create_tar(month_dir, package)
        manifest["source_month_packages"].append(
            {
                "month": month,
                "file": package.name,
                "sha256": f"sha256:{sha256_file(package)}",
                "artifact_count": len(selected),
            }
        )

        baseline = validate_explicit_artifact(
            api, month_spec["baseline"], "baseline", month
        )
        baseline_target = assets_dir / (
            f"usdjpy-{month}-baseline-id-{baseline['id']}.zip"
        )
        api.download_artifact(int(baseline["id"]), baseline_target)
        verify_download(baseline_target, baseline)
        manifest["artifacts"].append(
            manifest_row(
                baseline, role="baseline", local_path=baseline_target, month=month
            )
        )

    for reference_spec in config["reference_artifacts"]:
        artifact = validate_explicit_artifact(
            api, reference_spec, reference_spec["role"]
        )
        target = assets_dir / f"{reference_spec['role']}-id-{artifact['id']}.zip"
        api.download_artifact(int(artifact["id"]), target)
        verify_download(target, artifact)
        manifest["artifacts"].append(
            manifest_row(
                artifact,
                role=reference_spec["role"],
                local_path=target,
            )
        )

    manifest_path = assets_dir / "usdjpy-r0-artifact-archive-manifest-v1.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checksums = []
    for path in sorted(assets_dir.iterdir()):
        if path.name == "SHA256SUMS":
            continue
        checksums.append(f"{sha256_file(path)}  {path.name}")
    (assets_dir / "SHA256SUMS").write_text(
        "\n".join(checksums) + "\n",
        encoding="utf-8",
    )

    summary = {
        "status": "PASS",
        "source_months": len(config["months"]),
        "preserved_original_artifacts": len(manifest["artifacts"]),
        "release_assets": len(list(assets_dir.iterdir())),
        "manifest": manifest_path.name,
    }
    (output_dir / "archive_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
