#!/usr/bin/env python3
"""Bounded publication-time compatibility wrapper for archive receipt cleanup.

GitHub can expose a Release publication timestamp one second earlier than the
human-readable timestamp captured in a committed receipt.  This wrapper accepts
at most a two-second difference, while still binding the actual API timestamp,
Release ID, asset count, sizes, and SHA-256 identities into the candidate digest.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import fx2_archive_receipt_artifact_purge_v1 as v1

_ORIGINAL_STABLE_RELEASE_IDENTITY = v1.stable_release_identity
MAX_PUBLICATION_TIME_DELTA_SECONDS = 2.0


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def tolerant_stable_release_identity(
    api: v1.base.GitHubApi,
    authority: v1.ReceiptAuthority,
) -> dict[str, Any]:
    if not authority.published_at:
        return _ORIGINAL_STABLE_RELEASE_IDENTITY(api, authority)

    encoded = quote(authority.release_tag, safe="")
    observed = api.json(f"/repos/{api.repository}/releases/tags/{encoded}")
    actual = observed.get("published_at")
    if not isinstance(actual, str) or not actual:
        raise v1.ReceiptPurgeError(
            f"Release API has no publication timestamp: {authority.release_tag}"
        )
    delta = abs((parse_utc(actual) - parse_utc(authority.published_at)).total_seconds())
    if delta > MAX_PUBLICATION_TIME_DELTA_SECONDS:
        raise v1.ReceiptPurgeError(
            f"Release publication timestamp mismatch exceeds tolerance for {authority.release_tag}: "
            f"api={actual} receipt={authority.published_at} delta_seconds={delta}"
        )

    identity = _ORIGINAL_STABLE_RELEASE_IDENTITY(
        api,
        replace(authority, published_at=actual),
    )
    identity["receipt_published_at"] = authority.published_at
    identity["publication_time_delta_seconds"] = delta
    return identity


def main() -> int:
    v1.stable_release_identity = tolerant_stable_release_identity
    return v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
