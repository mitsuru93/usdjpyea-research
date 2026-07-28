#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

SOURCE_RUN_ID = 30375885665
SOURCE_JOB_ID = 90331330687
SOURCE_ARTIFACT_ID = 8695321156
SOURCE_ARTIFACT_DIGEST = "sha256:4eefbcc77962dc9f72fa647b386088c18f9efa196b7f70be1e970ccf9ed8964b"
SOURCE_HEAD_SHA = "b94d09c0dc057f6a811cf79664cff81adf0fc922"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source(output: Path) -> dict:
    result = json.loads((output / "final_result.json").read_text(encoding="utf-8"))
    checks = {
        "hypothesis": result.get("hypothesis_id") == "USDJPY-HYP-034",
        "family": result.get("family_id") == "S_PREVIOUS_DAY_EXTREME_SWEEP_REJECTION",
        "decision": result.get("decision") == "NO_PORTABLE_REJECTION_MECHANISM",
        "events": result.get("source_native_event_count") == 510,
        "high": result.get("high_sweep_count") == 284,
        "low": result.get("low_sweep_count") == 226,
        "trades": result.get("calendar_metadata", {}).get("candidate_trade_count_after_active_suppression") == 432,
        "net": abs(float(result.get("unfiltered_candidate_metrics", {}).get("net_jpy")) - 4450.0) < 1e-6,
        "pf": abs(float(result.get("unfiltered_candidate_metrics", {}).get("profit_factor")) - 1.0888259012335741) < 1e-12,
        "folds": result.get("positive_folds") == 2,
        "catalog": result.get("candidate_catalog_size") == 0,
        "selected": result.get("selected_candidate") is None,
        "historical_locked": result.get("historical_validation_authorized") is False,
        "core_locked": result.get("core_mt4_authorized") is False,
        "external_locked": result.get("external_2025_authorized") is False,
        "production_locked": result.get("production_authorized") is False,
        "live_locked": result.get("live_authorized") is False,
        "historical_unopened": result.get("protected_2020_2022_accessed") is False,
        "2025_unopened": result.get("protected_2025_accessed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"scientific identity mismatch: {failed}")
    verified = []
    for line in (output / "PACKAGE_SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if name == "run.log":
            continue
        path = output / name
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError(f"source member mismatch: {name}")
        verified.append(name)
    return {"result": result, "verified_members_excluding_mutable_log": verified}


def load_infra(path: Path):
    spec = importlib.util.spec_from_file_location("fx2_infra", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Infrastructure v1 snapshot")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if getattr(module, "ORIGIN_CORE_SHA", None) != "f897b250b808207d960417b2306935dcb0655acf":
        raise RuntimeError("Core Infrastructure origin mismatch")
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--repaired", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--infra", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    source_output = args.source / "output"
    source_evidence = args.source / "evidence"
    if not source_output.is_dir() or not source_evidence.is_dir():
        raise RuntimeError("source artifact layout unresolved")
    verification = verify_source(source_output)

    scientific = args.repaired / "scientific_output"
    technical = args.repaired / "technical_evidence"
    if args.repaired.exists():
        shutil.rmtree(args.repaired)
    scientific.mkdir(parents=True)
    technical.mkdir(parents=True)
    for path in source_output.iterdir():
        if path.is_file() and path.name not in {"run.log", "PACKAGE_MANIFEST.json", "PACKAGE_SHA256SUMS"}:
            shutil.copy2(path, scientific / path.name)
    shutil.copytree(source_evidence, technical, dirs_exist_ok=True)
    shutil.copy2(source_output / "run.log", technical / "evaluator_stdout.log")

    repair_receipt = {
        "schema_version": "usdjpy_hyp034_development_evidence_repair_receipt_v1",
        "status": "TECHNICAL_PACKAGE_REPAIR_SCIENTIFIC_RESULT_UNCHANGED",
        "hypothesis_id": "USDJPY-HYP-034",
        "family_id": "S_PREVIOUS_DAY_EXTREME_SWEEP_REJECTION",
        "scientific_decision": "NO_PORTABLE_REJECTION_MECHANISM",
        "source_run_id": SOURCE_RUN_ID,
        "source_job_id": SOURCE_JOB_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "source_head_sha": SOURCE_HEAD_SHA,
        "repair_scope": "Move mutable run.log outside the scientific package and recompute manifests; no evaluator, input, event, feature, threshold, gate, period, metric or decision changed.",
        "verified_scientific_members_excluding_mutable_log": len(verification["verified_members_excluding_mutable_log"]),
        "protected_2020_2022_accessed": False,
        "protected_2025_accessed": False,
        "core_changed": False,
        "mt4_executed": False,
        "scientific_result_changed": False,
    }
    (technical / "evidence_repair_receipt.json").write_text(json.dumps(repair_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    rows = []
    for path in sorted(scientific.iterdir()):
        if path.is_file():
            rows.append({"path": path.name, "byte_size": path.stat().st_size, "sha256": sha256(path)})
    manifest = {"file_count": len(rows), "files": rows}
    (scientific / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sums = rows + [{"path": "PACKAGE_MANIFEST.json", "sha256": sha256(scientific / "PACKAGE_MANIFEST.json")}]
    (scientific / "PACKAGE_SHA256SUMS").write_text("".join(f"{row['sha256']}  {row['path']}\n" for row in sums), encoding="utf-8")
    for row in sums:
        if sha256(scientific / row["path"]) != row["sha256"]:
            raise RuntimeError(f"repaired scientific checksum mismatch: {row['path']}")
    if (scientific / "run.log").exists() or (scientific / "development_run.log").exists():
        raise RuntimeError("mutable log remained in scientific package")

    infra = load_infra(args.infra)
    build_receipt = infra.build_archive(args.repaired, args.archive, args.source_sha, args.run_id, "scientific")
    readback = infra.readback_archive(args.archive)
    if readback.get("status") != "PASS":
        raise RuntimeError("Infrastructure v1 archive readback failed")
    (technical / "archive_build_receipt.json").write_text(json.dumps(build_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (technical / "archive_readback.json").write_text(json.dumps(readback, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (technical / "archive_sha256.txt").write_text(f"{sha256(args.archive)}  {args.archive.name}\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "decision": "NO_PORTABLE_REJECTION_MECHANISM", "archive_sha256": sha256(args.archive)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
