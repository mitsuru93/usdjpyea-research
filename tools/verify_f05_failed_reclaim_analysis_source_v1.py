#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zipfile
from pathlib import Path

EXPECTED_REPORT_SHA256 = "489a2484be135209fd731951990e508b67d6ff11cd2aeff3a4fbac23dffdfad5"
EXPECTED_BUNDLE_SHA256 = "463850652d08f7c3d6b170a345ba92a1f7228c9efb24eb0f89f90b13a59b686d"
EXPECTED_CANDIDATE = "F05_FAILED_RECLAIM_BASIC_V1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--bundle-b64", type=Path, required=True)
    parser.add_argument("--repository-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    restored_zip = args.output_dir / "F05_structural_SL_event_sequence_bundle_v1.zip"
    extracted_dir = args.output_dir / "bundle_members"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    report_sha = sha256_file(args.report)
    if report_sha != EXPECTED_REPORT_SHA256:
        raise AssertionError(("report_sha256", report_sha, EXPECTED_REPORT_SHA256))

    encoded = b"".join(args.bundle_b64.read_bytes().split())
    decoded = base64.b64decode(encoded, validate=True)
    restored_zip.write_bytes(decoded)
    bundle_sha = sha256_bytes(decoded)
    if bundle_sha != EXPECTED_BUNDLE_SHA256:
        raise AssertionError(("bundle_sha256", bundle_sha, EXPECTED_BUNDLE_SHA256))

    repository_manifest_bytes = args.repository_manifest.read_bytes()
    repository_manifest = json.loads(repository_manifest_bytes)
    member_results: list[dict[str, object]] = []

    with zipfile.ZipFile(restored_zip) as archive:
        names = sorted(n for n in archive.namelist() if not n.endswith("/"))
        if "manifest.json" not in names:
            raise AssertionError("manifest.json missing from restored bundle")
        embedded_manifest_bytes = archive.read("manifest.json")
        embedded_manifest = json.loads(embedded_manifest_bytes)
        if embedded_manifest != repository_manifest:
            raise AssertionError("repository manifest and embedded manifest differ")
        expected_names = sorted(item["name"] for item in embedded_manifest["files"])
        if names != sorted(expected_names + ["manifest.json"]):
            raise AssertionError(("member_names", names, expected_names + ["manifest.json"]))
        for item in embedded_manifest["files"]:
            payload = archive.read(item["name"])
            actual = {
                "name": item["name"],
                "size_bytes": len(payload),
                "sha256": sha256_bytes(payload),
            }
            if actual["size_bytes"] != item["size_bytes"]:
                raise AssertionError((item["name"], "size", actual["size_bytes"], item["size_bytes"]))
            if actual["sha256"] != item["sha256"]:
                raise AssertionError((item["name"], "sha256", actual["sha256"], item["sha256"]))
            (extracted_dir / item["name"]).write_bytes(payload)
            member_results.append(actual)
        (extracted_dir / "manifest.json").write_bytes(embedded_manifest_bytes)

    receipt = {
        "schema_version": "f05_failed_reclaim_analysis_source_verification_v1",
        "status": "PASS_EXACT_SOURCE_RESTORED",
        "source_commit": args.source_commit,
        "candidate_scope": {
            "binding": EXPECTED_CANDIDATE,
            "non_binding_sensitivity": "F05_FAILED_RECLAIM_WEAK_QUICK_V1",
        },
        "report": {
            "path": str(args.report),
            "size_bytes": args.report.stat().st_size,
            "sha256": report_sha,
        },
        "bundle": {
            "base64_path": str(args.bundle_b64),
            "decoded_path": str(restored_zip),
            "decoded_size_bytes": restored_zip.stat().st_size,
            "sha256": bundle_sha,
        },
        "repository_manifest_sha256": sha256_bytes(repository_manifest_bytes),
        "embedded_manifest_sha256": sha256_bytes(embedded_manifest_bytes),
        "member_count": len(member_results),
        "members": member_results,
        "boundaries": {
            "outcomes_computed": False,
            "portfolio_replay_computed": False,
            "mt4_accessed": False,
            "2025H1_accessed": False,
            "2025H2_accessed": False,
            "notion_task_dependency": False,
        },
    }
    receipt_path = args.output_dir / "f05_failed_reclaim_analysis_source_verification_v1.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
