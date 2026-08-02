#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

WORK_ID = "USDJPY-A2A-A3-INTEGRATED-F05-LONG-CONTROL-001"
HYPOTHESIS_ID = "USDJPY-HYP-046"
PARENT_HYPOTHESIS_ID = "USDJPY-HYP-045"
RELEASE_ID = 363909176
RELEASE_TAG = "usdjpy-hyp045-b0-cross-regime-stability-improvement-v5"
ASSET_ID = 499322218
ASSET_NAME = "usdjpy-b0-cross-regime-stability-improvement-001-v5.zip"
ARCHIVE_SHA256 = "aa54091ed2149b2c8d6ce5da1f11c739ee0d213eb2dda2928e7dfa1c5c153065"
A2A_RULE_HASH = "2ec036e50da92fd6c1280b63d0c2a2b2b60b2c875851b03544b0c9bcf2254cf8"
A3_RULE_HASH = "1425b4caf6c0a5e8c4f21be7efdf410442bbd6d24d329f87c9c4931eecbd4b7f"
IMPLEMENTATION_HASH = "fc9aa82e9ecd74951a00c0d06f260bca5ec54f91358152268dfd993f4f4157d2"
CORE_SOURCE_SHA256 = "7bdcaa5eeed0b711edc44a155e3f485ee888c490d82eac951aaf2634e36f9089"
EX4_SHA256 = "b5fba35009f3da131f3f3c12d49cc1a35338a6a0bf4bfa8fc0e0432b3c2fd09f"


def run(*args: str, binary: bool = False) -> bytes | str:
    proc = subprocess.run(args, check=True, capture_output=True, text=not binary)
    return proc.stdout


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def locate(root: Path, filename: str) -> Path:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {filename}, found {len(matches)}")
    return matches[0]


def csv_metadata(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            rows = sum(1 for _ in reader)
        return {"columns": header, "rows": rows, "read_error": None}
    except Exception as exc:
        return {"columns": [], "rows": None, "read_error": f"{type(exc).__name__}: {exc}"}


def extract_rule_hash(contract: dict[str, Any], hashes: dict[str, Any], key: str) -> str | None:
    value = contract.get("rule_hash") or contract.get("rule_hash_sha256")
    if value:
        return str(value)
    hash_value = hashes.get(key)
    if isinstance(hash_value, dict):
        return str(hash_value.get("rule_hash") or hash_value.get("sha256") or "") or None
    return str(hash_value) if hash_value else None


def main() -> int:
    out = Path(os.environ.get(
        "HYP046_OUT",
        "artifacts/research/usdjpy_a2a_a3_integrated_f05_long_control_001/preflight_v1",
    ))
    temp = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "hyp046_parent_release"
    shutil.rmtree(out, ignore_errors=True)
    shutil.rmtree(temp, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)

    release = json.loads(str(run("gh", "api", f"repos/mitsuru93/usdjpyea-research/releases/{RELEASE_ID}")))
    if release.get("tag_name") != RELEASE_TAG:
        raise RuntimeError(f"release tag mismatch: {release.get('tag_name')}")
    assets = release.get("assets", [])
    matches = [a for a in assets if int(a.get("id", -1)) == ASSET_ID and a.get("name") == ASSET_NAME]
    if len(matches) != 1:
        raise RuntimeError(f"release asset mismatch: {matches}")
    asset = matches[0]

    archive = temp / ASSET_NAME
    payload = run(
        "gh", "api", f"repos/mitsuru93/usdjpyea-research/releases/assets/{ASSET_ID}",
        "-H", "Accept: application/octet-stream", binary=True,
    )
    assert isinstance(payload, bytes)
    archive.write_bytes(payload)
    observed_archive_sha = sha256(archive)
    if observed_archive_sha != ARCHIVE_SHA256:
        raise RuntimeError(f"archive sha mismatch: {observed_archive_sha}")

    extract_root = temp / "extract"
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        zf.extractall(extract_root)

    contracts_path = locate(extract_root, "candidate_rule_contracts.json")
    hashes_path = locate(extract_root, "candidate_rule_hashes.json")
    final_path = locate(extract_root, "final_decision.json")
    manifest_path = locate(extract_root, "release_manifest.json")
    contracts = json.loads(contracts_path.read_text(encoding="utf-8"))
    hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
    a2a_contract = contracts.get("A2A_F05_LONG_HIGHVOL_EXTENSION4_PERMISSION")
    a3_contract = contracts.get("A3_B0_LOCALIZED_F05_LONG_SESSION_CLUSTER_CONTROL")
    if not isinstance(a2a_contract, dict) or not isinstance(a3_contract, dict):
        raise RuntimeError("A2A/A3 contracts not present in parent release")
    observed_a2a = extract_rule_hash(a2a_contract, hashes, "A2A_F05_LONG_HIGHVOL_EXTENSION4_PERMISSION")
    observed_a3 = extract_rule_hash(a3_contract, hashes, "A3_B0_LOCALIZED_F05_LONG_SESSION_CLUSTER_CONTROL")
    if observed_a2a != A2A_RULE_HASH:
        raise RuntimeError(f"A2A hash mismatch: {observed_a2a}")
    if observed_a3 != A3_RULE_HASH:
        raise RuntimeError(f"A3 hash mismatch: {observed_a3}")

    receipt = {
        "schema_version": "parent_hyp045_authority_receipt_v1",
        "work_id": WORK_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "release_id": RELEASE_ID,
        "release_tag_expected": RELEASE_TAG,
        "release_tag_observed": release.get("tag_name"),
        "release_target_commitish": release.get("target_commitish"),
        "release_published_at": release.get("published_at"),
        "asset_id": ASSET_ID,
        "asset_name": ASSET_NAME,
        "asset_size_remote": asset.get("size"),
        "asset_digest_remote": asset.get("digest"),
        "archive_sha256_expected": ARCHIVE_SHA256,
        "archive_sha256_observed": observed_archive_sha,
        "archive_member_count": len(infos),
        "a2a_rule_hash_expected": A2A_RULE_HASH,
        "a2a_rule_hash_observed": observed_a2a,
        "a3_rule_hash_expected": A3_RULE_HASH,
        "a3_rule_hash_observed": observed_a3,
        "parent_implementation_hash": IMPLEMENTATION_HASH,
        "parent_core_source_sha256": CORE_SOURCE_SHA256,
        "parent_ex4_sha256": EX4_SHA256,
        "remote_readback_status": "PASS_BYTE_IDENTICAL_RELEASE_ARCHIVE_AND_RULE_HASHES",
        "parent_mutated": False,
        "2025H2_accessed": False,
    }
    write_json(out / "parent_hyp045_authority_receipt.json", receipt)

    csv_rows: list[dict[str, Any]] = []
    for p in sorted(extract_root.rglob("*.csv")):
        md = csv_metadata(p)
        csv_rows.append({
            "path": p.relative_to(extract_root).as_posix(),
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
            "rows_excluding_header": md["rows"],
            "columns": md["columns"],
            "read_error": md["read_error"],
        })
    write_json(out / "candidate_csv_inventory.json", csv_rows)
    with (out / "candidate_csv_inventory.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "bytes", "sha256", "rows_excluding_header", "column_count", "columns", "read_error"])
        for row in csv_rows:
            writer.writerow([
                row["path"], row["bytes"], row["sha256"], row["rows_excluding_header"],
                len(row["columns"]), "|".join(row["columns"]), row["read_error"],
            ])

    with (out / "archive_member_inventory.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["member", "bytes", "compressed_bytes", "crc32"])
        for info in sorted(infos, key=lambda x: x.filename):
            writer.writerow([info.filename, info.file_size, info.compress_size, f"{info.CRC:08x}"])

    candidate_col_tokens = {
        "entry_time", "close_time", "strategy", "side", "net_jpy", "pnl_jpy",
        "volatility", "volatility_state", "extension_atr", "session", "utc_day",
        "candidate_id", "blocked", "block_reason", "reason", "result",
    }
    interaction_ready = []
    for row in csv_rows:
        normalized = {str(c).strip().lower() for c in row["columns"]}
        matched = sorted(normalized & candidate_col_tokens)
        if len(matched) >= 4:
            interaction_ready.append({
                "path": row["path"],
                "rows": row["rows_excluding_header"],
                "matched_columns": matched,
                "columns": row["columns"],
            })

    inventory = {
        "schema_version": "hyp046_authority_inventory_v1",
        "work_id": WORK_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_release_archive_member_count": len(infos),
        "parent_release_csv_count": len(csv_rows),
        "parent_release_json_count": len(list(extract_root.rglob("*.json"))),
        "interaction_ready_files": interaction_ready,
        "contract_files": {
            "candidate_rule_contracts": contracts_path.relative_to(extract_root).as_posix(),
            "candidate_rule_hashes": hashes_path.relative_to(extract_root).as_posix(),
            "final_decision": final_path.relative_to(extract_root).as_posix(),
            "release_manifest": manifest_path.relative_to(extract_root).as_posix(),
        },
        "authority_limitation": {
            "latest_binding_f05_trades": 1464,
            "retained_row_certified_f05_c2_trades": 1451,
            "gap_trades": 13,
            "synthetic_reconstruction_permitted": False,
        },
        "2025H2_accessed": False,
    }
    write_json(out / "authority_inventory.json", inventory)
    write_json(out / "authority_lineage_status.json", {
        "schema_version": "hyp046_authority_lineage_status_v1",
        "parent_release_readback": "PASS",
        "source_native_row_certified_authority": "SEPARATE_FROM_RAKUTEN_BROKER_REALIZATION",
        "rakuten_mt4_broker_realization": "PARENT_RELEASE_CONFIRMED",
        "reconstructed_aggregate_authority": "NON_ROW_PARITY_ONLY",
        "exact_row_parity_period": "PENDING_CORE_LOCAL_LEDGER_BINDING",
        "authority_limited_period": "F05_13_TRADE_GAP_REMAINS_EXPLICIT",
        "synthetic_gap_fill_used": False,
        "a2a_threshold_retuned": False,
        "a3_rule_retuned": False,
        "counterfactual_state_update_permitted": False,
        "2025H2_accessed": False,
        "production_authorized": False,
        "live_authorized": False,
    })
    write_json(out / "a2a_contract.json", a2a_contract)
    write_json(out / "a3_contract.json", a3_contract)
    write_json(out / "preflight_summary.json", {
        "schema_version": "hyp046_parent_release_preflight_summary_v1",
        "status": "PASS_PARENT_RELEASE_READBACK_AND_AUTHORITY_INVENTORY",
        "work_id": WORK_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "release_tag": RELEASE_TAG,
        "archive_sha256": observed_archive_sha,
        "archive_member_count": len(infos),
        "csv_count": len(csv_rows),
        "interaction_ready_file_count": len(interaction_ready),
        "exact_next_action": "BIND_CORE_LOCAL_ROW_LEVEL_INPUTS_AND_RUN_C0_C1_C2_INTERACTION_REPLAY",
        "2025H2_accessed": False,
    })

    checksum_lines = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "sha256sums.txt":
            checksum_lines.append(f"{sha256(p)}  {p.relative_to(out).as_posix()}")
    (out / "sha256sums.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print((out / "preflight_summary.json").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
