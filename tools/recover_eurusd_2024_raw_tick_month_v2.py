#!/usr/bin/env python3
"""Run EURUSD month recovery with deterministic duplicate-artifact resolution.

GitHub Actions can expose multiple artifacts with the same logical name when
identical reusable-workflow jobs were emitted more than once.  The v1 recovery
script intentionally rejects ambiguous names.  This wrapper removes ambiguity
only when every duplicate has identical digest, size, and creation timestamp;
it then selects the greatest artifact ID and records the decision in the log.
Non-identical duplicates remain untouched so v1 still fails closed.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import recover_eurusd_2024_raw_tick_month_v1 as base


_original_list_run_artifacts = base.list_run_artifacts


def _identity(row: dict[str, Any]) -> tuple[str, int, str]:
    return (
        str(row.get("digest", "")),
        int(row.get("size_in_bytes", 0)),
        str(row.get("created_at", "")),
    )


def list_run_artifacts_deduplicated(
    repository: str,
    run_id: int,
    token: str,
) -> list[dict[str, Any]]:
    rows = _original_list_run_artifacts(repository, run_id, token)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("name", ""))].append(row)

    resolved: list[dict[str, Any]] = []
    for name, matches in grouped.items():
        if len(matches) == 1:
            resolved.append(matches[0])
            continue

        identities = {_identity(row) for row in matches}
        if len(identities) != 1:
            print(
                json.dumps(
                    {
                        "event": "duplicate_artifact_conflict",
                        "name": name,
                        "candidates": [
                            {
                                "artifact_id": int(row.get("id", 0)),
                                "digest": row.get("digest"),
                                "size_in_bytes": int(row.get("size_in_bytes", 0)),
                                "created_at": row.get("created_at"),
                                "expired": bool(row.get("expired")),
                            }
                            for row in sorted(matches, key=lambda item: int(item.get("id", 0)))
                        ],
                    },
                    sort_keys=True,
                )
            )
            resolved.extend(matches)
            continue

        selected = max(matches, key=lambda row: int(row.get("id", 0)))
        print(
            json.dumps(
                {
                    "event": "duplicate_artifact_resolved",
                    "name": name,
                    "selected_artifact_id": int(selected["id"]),
                    "duplicate_artifact_ids": sorted(int(row["id"]) for row in matches),
                    "digest": selected.get("digest"),
                    "size_in_bytes": int(selected.get("size_in_bytes", 0)),
                    "created_at": selected.get("created_at"),
                    "rule": "identical_identity_select_max_artifact_id",
                },
                sort_keys=True,
            )
        )
        resolved.append(selected)

    return resolved


base.list_run_artifacts = list_run_artifacts_deduplicated


if __name__ == "__main__":
    base.main()
