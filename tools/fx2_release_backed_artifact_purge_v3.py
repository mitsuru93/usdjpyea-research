#!/usr/bin/env python3
"""Semantic dependency wrapper for Release-backed Artifact cleanup.

An Artifact ID embedded in a durable Release asset filename or provenance record is
not a live Actions dependency.  Only executable Actions download/API retrieval
contexts block deletion.  All v1 Release, digest, source-run, candidate-digest,
and readback gates remain authoritative.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import fx2_release_backed_artifact_purge_v1 as v1
from tools import fx2_release_backed_artifact_purge_v2 as v2

ACTIONS_RETRIEVAL_PATTERNS = tuple(
    re.compile(pattern, re.I)
    for pattern in (
        r"actions/download-artifact",
        r"\bgh\s+run\s+download\b",
        r"/actions/artifacts(?:/|\?)",
        r"archive_download_url",
        r"\bdownload(?:workflow)?artifact\b",
        r"\blist(?:workflowrun)?artifacts\b",
        r"\bgetartifact\b",
        r"\bartifact_url\b",
    )
)
RELEASE_RETRIEVAL_PATTERNS = tuple(
    re.compile(pattern, re.I)
    for pattern in (
        r"\bgh\s+release\s+download\b",
        r"/releases/assets/",
        r"releases/download/",
    )
)
CONTEXT_RADIUS = 12


def _occurrence_lines(text: str, term: str) -> list[int]:
    return [index for index, line in enumerate(text.splitlines()) if term and term in line]


def _is_live_actions_context(lines: list[str], index: int) -> bool:
    start = max(0, index - CONTEXT_RADIUS)
    end = min(len(lines), index + CONTEXT_RADIUS + 1)
    context = "\n".join(lines[start:end])
    has_actions_retrieval = any(pattern.search(context) for pattern in ACTIONS_RETRIEVAL_PATTERNS)
    if not has_actions_retrieval:
        return False

    # A Release download can legitimately carry the old Artifact ID in the
    # immutable asset filename.  It does not depend on Actions retention.
    line = lines[index]
    local = "\n".join(lines[max(0, index - 3): min(len(lines), index + 4)])
    if any(pattern.search(local) for pattern in RELEASE_RETRIEVAL_PATTERNS):
        # Still block if the exact local block also contains an Actions API.
        if not any(pattern.search(local) for pattern in ACTIONS_RETRIEVAL_PATTERNS):
            return False
    if any(pattern.search(line) for pattern in RELEASE_RETRIEVAL_PATTERNS):
        return False
    return True


def semantic_dependency_refs(
    artifact: dict[str, Any],
    files: list[tuple[str, str]],
) -> list[str]:
    terms = [
        str(artifact.get("id") or ""),
        str((artifact.get("workflow_run") or {}).get("id") or ""),
        str(artifact.get("name") or ""),
    ]
    refs: list[str] = []
    for path, text in files:
        lines = text.splitlines()
        blocked = False
        for term in terms:
            for index in _occurrence_lines(text, term):
                if _is_live_actions_context(lines, index):
                    blocked = True
                    break
            if blocked:
                break
        if blocked:
            refs.append(path)
    return sorted(set(refs))


def main() -> int:
    v1.GitHubApi.download_asset_text = v2.selective_download_asset_text
    v1.list_release_evidence = v2.indexed_list_release_evidence
    v1.artifact_release_match = v2.fast_artifact_release_match
    v1.dependency_refs = semantic_dependency_refs
    return v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
