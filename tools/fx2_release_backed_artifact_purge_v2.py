#!/usr/bin/env python3
"""Indexed execution wrapper for the v1 Release-backed Artifact purge controller."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import fx2_release_backed_artifact_purge_v1 as v1

_ORIGINAL_DOWNLOAD = v1.GitHubApi.download_asset_text
_ORIGINAL_LIST_RELEASE_EVIDENCE = v1.list_release_evidence
_NUMERIC_INDEX: dict[int, frozenset[str]] = {}

EVIDENCE_ASSET_MARKERS = (
    "receipt",
    "manifest",
    "checksum",
    "sha256",
    "sha-256",
    "provenance",
    "authority",
    "readback",
    "publication",
    "inventory",
    "index",
    "ledger",
    "source",
)


def selective_download_asset_text(self: v1.GitHubApi, asset: dict[str, Any]) -> str:
    """Download only assets likely to contain source binding evidence."""
    name = str(asset.get("name") or "").lower()
    suffix = Path(name).suffix.lower()
    if suffix not in {".sha256", ".sha256sums"} and not any(
        marker in name for marker in EVIDENCE_ASSET_MARKERS
    ):
        return ""
    return _ORIGINAL_DOWNLOAD(self, asset)


def indexed_list_release_evidence(api: v1.GitHubApi) -> list[v1.ReleaseEvidence]:
    releases = _ORIGINAL_LIST_RELEASE_EVIDENCE(api)
    _NUMERIC_INDEX.clear()
    for release in releases:
        _NUMERIC_INDEX[release.release_id] = frozenset(
            re.findall(r"(?<!\d)\d{6,14}(?!\d)", release.text)
        )
    return releases


def fast_artifact_release_match(
    artifact: dict[str, Any],
    releases: list[v1.ReleaseEvidence],
) -> tuple[v1.ReleaseEvidence, dict[str, bool]] | None:
    artifact_id = str(artifact.get("id") or "")
    name = str(artifact.get("name") or "")
    run_id = str((artifact.get("workflow_run") or {}).get("id") or "")
    digest = str(artifact.get("digest") or "")
    choices: list[tuple[int, v1.ReleaseEvidence, dict[str, bool]]] = []

    for release in releases:
        numeric = _NUMERIC_INDEX.get(release.release_id, frozenset())
        id_hit = artifact_id in numeric
        run_hit = run_id in numeric
        if not id_hit and not run_hit:
            continue
        text = release.text
        hits = {
            "artifact_id": id_hit,
            "artifact_name": bool(name and name in text),
            "run_id": run_hit,
            "artifact_digest": bool(digest and digest in text),
        }
        score = sum(1 for value in hits.values() if value)
        strong = (
            hits["artifact_id"]
            and (hits["artifact_name"] or hits["run_id"] or hits["artifact_digest"])
        ) or (
            hits["artifact_name"]
            and hits["run_id"]
            and hits["artifact_digest"]
        )
        if strong:
            choices.append((score, release, hits))

    if not choices:
        return None
    choices.sort(key=lambda row: (row[0], row[1].published_at), reverse=True)
    return choices[0][1], choices[0][2]


def main() -> int:
    v1.GitHubApi.download_asset_text = selective_download_asset_text
    v1.list_release_evidence = indexed_list_release_evidence
    v1.artifact_release_match = fast_artifact_release_match
    return v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
