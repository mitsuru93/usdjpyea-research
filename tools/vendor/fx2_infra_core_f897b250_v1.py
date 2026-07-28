#!/usr/bin/env python3
"""Fixed technical subset of FX2 MT4 Research Infrastructure Hardening v1.

Origin repository: mitsuru93/usdjpyea-core
Origin commit: f897b250b808207d960417b2306935dcb0655acf
Origin path: tools/research_infra/fx2_infra.py
Origin Git blob: da4a05f3fb509a5944fda57d3982206eba894475

This source-preserving subset contains only runner capability probing,
deterministic POSIX-path evidence archive creation/readback, storage routing,
and technical-no-result receipt generation. It never reads strategy data,
computes candidate outcomes, accesses protected periods, or executes MT4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "fx2_research_infra_v1"
ARCHIVE_SCHEMA = "fx2_deterministic_evidence_zip_v1"
RECEIPT_SCHEMA = "fx2_technical_no_result_receipt_v1"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
ORIGIN_CORE_SHA = "f897b250b808207d960417b2306935dcb0655acf"
ORIGIN_BLOB_SHA = "da4a05f3fb509a5944fda57d3982206eba894475"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_member_path(raw: str) -> str:
    if not raw or "\x00" in raw:
        raise ValueError("unexpected path")
    value = raw.replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"path traversal or invalid path: {raw}")
    if path.parts and path.parts[0].endswith(":"):
        raise ValueError(f"drive-qualified path rejected: {raw}")
    return path.as_posix()


def run_version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        text = (result.stdout or result.stderr).strip()
        return text.splitlines()[0] if text else None
    except Exception:
        return None


def runner_probe(output_json: Path, output_md: Path) -> dict[str, Any]:
    temp_candidates = [os.getenv("RUNNER_TEMP"), tempfile.gettempdir(), os.getenv("TEMP"), os.getenv("TMP")]
    temp_dirs: list[dict[str, Any]] = []
    for item in temp_candidates:
        if item and item not in [row["path"] for row in temp_dirs]:
            path = Path(item)
            temp_dirs.append({"path": str(path), "exists": path.exists(), "writable": os.access(path, os.W_OK) if path.exists() else False})
    cwd = Path.cwd()
    disk = shutil.disk_usage(cwd)
    terminal_candidates = [os.getenv("MT4_TERMINAL_PATH"), os.getenv("METAEDITOR_PATH")]
    portable_root = os.getenv("MT4_PORTABLE_ROOT")
    history_dir = os.getenv("MT4_HISTORY_DIR")
    active_mt4: list[str] = []
    try:
        if os.name == "nt":
            proc = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10, check=False)
        else:
            proc = subprocess.run(["ps", "-eo", "comm="], capture_output=True, text=True, timeout=10, check=False)
        active_mt4 = [line.strip() for line in proc.stdout.splitlines() if any(token in line.lower() for token in ("terminal.exe", "metatester", "metaeditor"))]
    except Exception:
        pass
    lock_path = os.getenv("FX2_TESTER_LOCK_PATH")
    long_paths = None
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
                long_paths = bool(winreg.QueryValueEx(key, "LongPathsEnabled")[0])
        except Exception:
            long_paths = None
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": utc_now(),
        "origin_core_sha": ORIGIN_CORE_SHA,
        "origin_blob_sha": ORIGIN_BLOB_SHA,
        "os": {"name": os.name, "platform": platform.platform(), "system": platform.system(), "release": platform.release()},
        "runner": {"name": os.getenv("RUNNER_NAME"), "labels": [x for x in os.getenv("RUNNER_LABELS", "").split(",") if x]},
        "powershell_version": run_version(["pwsh", "-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"]),
        "python_version": platform.python_version(),
        "git": {"path": shutil.which("git"), "version": run_version(["git", "--version"]) if shutil.which("git") else None},
        "long_paths_enabled": long_paths,
        "temp_directories": temp_dirs,
        "disk": {"root": str(cwd), "free_bytes": disk.free, "total_bytes": disk.total},
        "tool_paths": {"candidates": [{"path": x, "exists": bool(x and Path(x).exists())} for x in terminal_candidates if x]},
        "portable_terminal_root": {"path": portable_root, "exists": bool(portable_root and Path(portable_root).exists())},
        "history_directory": {"path": history_dir, "exists": bool(history_dir and Path(history_dir).exists())},
        "path_max": os.pathconf(str(cwd), "PC_PATH_MAX") if hasattr(os, "pathconf") and os.name != "nt" else 32767 if long_paths else 260,
        "zip": {"create": hasattr(zipfile, "ZipFile"), "extract": hasattr(zipfile, "ZipFile")},
        "sha256": True,
        "github_api_auth": bool(os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")),
        "ui_session_required": os.getenv("FX2_UI_SESSION_REQUIRED", "false").lower() == "true",
        "service_runner": os.getenv("RUNNER_ENVIRONMENT", "").lower() == "self-hosted" and os.getenv("FX2_UI_SESSION_REQUIRED", "false").lower() != "true",
        "active_mt4_processes": active_mt4,
        "active_tester_lock": {"path": lock_path, "exists": bool(lock_path and Path(lock_path).exists())},
        "scientific_result_generated": False,
        "protected_period_accessed": False,
        "mt4_executed": False,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# Runner Capability Report", "", f"Generated: {result['generated_utc']}", ""]
    for key in ("origin_core_sha", "origin_blob_sha", "os", "runner", "powershell_version", "python_version", "git", "long_paths_enabled", "temp_directories", "disk", "tool_paths", "portable_terminal_root", "history_directory", "path_max", "zip", "sha256", "github_api_auth", "ui_session_required", "service_runner", "active_mt4_processes", "active_tester_lock"):
        lines.extend([f"## {key}", "```json", json.dumps(result[key], indent=2, sort_keys=True), "```"])
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def collect_members(input_root: Path) -> list[tuple[str, bytes]]:
    members: list[tuple[str, bytes]] = []
    seen: set[str] = set()
    for path in sorted((x for x in input_root.rglob("*") if x.is_file()), key=lambda x: x.as_posix()):
        name = normalize_member_path(path.relative_to(input_root).as_posix())
        if name in seen:
            raise ValueError("duplicate normalized path")
        seen.add(name)
        members.append((name, path.read_bytes()))
    return members


def build_archive(input_root: Path, archive_path: Path, source_sha: str, workflow_run_id: str, classification: str, generated_utc: str | None = None) -> dict[str, Any]:
    if classification not in ("scientific", "non-scientific"):
        raise ValueError("classification must be scientific or non-scientific")
    members = collect_members(input_root)
    manifest = {
        "schema_version": ARCHIVE_SCHEMA,
        "source_commit_sha": source_sha,
        "workflow_run_id": str(workflow_run_id),
        "generated_utc": generated_utc or "1980-01-01T00:00:00Z",
        "classification": classification,
        "origin_core_sha": ORIGIN_CORE_SHA,
        "origin_blob_sha": ORIGIN_BLOB_SHA,
        "members": [{"path": name, "sha256": sha256_bytes(payload), "byte_size": len(payload)} for name, payload in members],
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(members + [("evidence_manifest.json", manifest_bytes)], key=lambda row: row[0]):
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            info.flag_bits |= 0x800
            archive.writestr(info, payload)
    return {"archive_path": str(archive_path), "archive_sha256": sha256_file(archive_path), **manifest}


def readback_archive(archive_path: Path) -> dict[str, Any]:
    archive_sha = sha256_file(archive_path)
    with zipfile.ZipFile(archive_path, "r") as archive:
        normalized: dict[str, zipfile.ZipInfo] = {}
        for info in archive.infolist():
            name = normalize_member_path(info.filename)
            if name in normalized:
                raise ValueError("duplicate normalized path")
            normalized[name] = info
        if "evidence_manifest.json" not in normalized:
            raise ValueError("manifest missing")
        manifest = json.loads(archive.read(normalized["evidence_manifest.json"]).decode("utf-8"))
        if manifest.get("schema_version") != ARCHIVE_SCHEMA:
            raise ValueError("schema mismatch")
        expected = {member["path"]: member for member in manifest.get("members", [])}
        actual = set(normalized) - {"evidence_manifest.json"}
        if actual != set(expected):
            raise ValueError(f"missing/extra member: expected={sorted(expected)} actual={sorted(actual)}")
        for name, specification in expected.items():
            payload = archive.read(normalized[name])
            if len(payload) != specification["byte_size"] or sha256_bytes(payload) != specification["sha256"]:
                raise ValueError(f"member integrity failure: {name}")
    return {"status": "PASS", "archive_sha256": archive_sha, "manifest": manifest}


def storage_route(actions_available: bool, release_allowed: bool, release_available: bool, local_retained: bool) -> dict[str, Any]:
    if actions_available:
        return {"mode": "ACTIONS_ARTIFACT", "status": "READY", "artifact_id": "PENDING_UPLOAD"}
    if release_allowed and release_available:
        return {"mode": "GITHUB_RELEASE_ASSET", "status": "READY", "artifact_id": None, "reason": "ACTIONS_ARTIFACT_UNAVAILABLE"}
    if local_retained:
        return {"mode": "LOCAL_RETAINED_PENDING_PUBLICATION", "status": "PENDING_PUBLICATION", "artifact_id": None}
    return {"mode": "NO_EVIDENCE_NO_RESULT", "status": "TECHNICAL_NO_RESULT", "artifact_id": None, "reason": "EVIDENCE_STORAGE_UNAVAILABLE"}


def technical_no_result(stage: str, reason_code: str, reason: str, repository: str, source_sha: str, workflow_run_id: str, runner: str, storage_mode: str, repair_boundary: str, retry_eligibility: bool = True) -> dict[str, Any]:
    return {
        "schema_version": RECEIPT_SCHEMA,
        "status": "TECHNICAL_NO_RESULT",
        "stage": stage,
        "reason_code": reason_code,
        "human_readable_reason": reason,
        "repository": repository,
        "source_sha": source_sha,
        "workflow_run_id": str(workflow_run_id),
        "runner": runner,
        "evidence_storage_mode": storage_mode,
        "candidate_outcome_computed": False,
        "protected_period_accessed": False,
        "mt4_executed": False,
        "retry_eligibility": bool(retry_eligibility),
        "repair_boundary": repair_boundary,
    }


def cli() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    command = sub.add_parser("probe"); command.add_argument("--json", required=True); command.add_argument("--markdown", required=True)
    command = sub.add_parser("archive"); command.add_argument("--input", required=True); command.add_argument("--output", required=True); command.add_argument("--source-sha", required=True); command.add_argument("--run-id", required=True); command.add_argument("--classification", default="non-scientific")
    command = sub.add_parser("readback"); command.add_argument("--archive", required=True)
    command = sub.add_parser("technical-no-result"); command.add_argument("--stage", required=True); command.add_argument("--reason-code", required=True); command.add_argument("--reason", required=True); command.add_argument("--repository", required=True); command.add_argument("--source-sha", required=True); command.add_argument("--run-id", required=True); command.add_argument("--runner", required=True); command.add_argument("--storage-mode", required=True); command.add_argument("--repair-boundary", required=True); command.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.cmd == "probe":
        runner_probe(Path(args.json), Path(args.markdown))
    elif args.cmd == "archive":
        print(json.dumps(build_archive(Path(args.input), Path(args.output), args.source_sha, args.run_id, args.classification), indent=2))
    elif args.cmd == "readback":
        print(json.dumps(readback_archive(Path(args.archive)), indent=2))
    elif args.cmd == "technical-no-result":
        Path(args.output).write_text(json.dumps(technical_no_result(args.stage, args.reason_code, args.reason, args.repository, args.source_sha, args.run_id, args.runner, args.storage_mode, args.repair_boundary), indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    cli()
