#!/usr/bin/env python3
"""Run the v1 USDJPY R0 archiver with redirect-safe GitHub authentication.

GitHub's artifact download endpoint redirects to a signed storage URL. The
Authorization header must be sent to api.github.com but must not be forwarded
to the signed storage host.
"""
from __future__ import annotations

import urllib.request

import archive_usdjpy_r0_artifacts_v1 as archive


def redirect_safe_request(
    self: archive.GitHubAPI, url: str
) -> urllib.request.Request:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "usdjpy-r0-artifact-archive-v2",
        },
    )
    request.add_unredirected_header(
        "Authorization", f"Bearer {self.token}"
    )
    return request


archive.GitHubAPI._request = redirect_safe_request


if __name__ == "__main__":
    raise SystemExit(archive.main())
