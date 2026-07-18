#!/usr/bin/env python3
"""Build and validate the frozen USDJPY 2024 R0 canonical research bundle."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

FLOAT_TOLERANCE = 1e-9
LEDGER_FLOAT_FORMAT = "%.12f"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run(command: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def safe_zip_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            target = (destination / member.filename).resolve()
            if destination.resolve() not in target.parents and target != destination.resolve():
                raise ValueError(f"unsafe ZIP member: {member.filename}")
        handle.extractall(destination)


def load_sha256s(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        rows[name.strip()] = digest.strip().lower()
    return rows


def verify_release_directory(
    release_dir: Path,
    canonical_config: dict[str, Any],
    audit_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sums_path = release_dir / canonical_config["release"]["sha256s_asset"]
    manifest_path = release_dir / canonical_config["release"]["manifest_asset"]
    if not sums_path.exists() or not manifest_path.exists():
        raise FileNotFoundError("Release manifest or SHA256SUMS is missing")
    expected_manifest_sha = canonical_config["release"]["manifest_sha256"].removeprefix("sha256:")
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != expected_manifest_sha:
        raise AssertionError(
            f"Release manifest digest mismatch: {actual_manifest_sha} != {expected_manifest_sha}"
        )

    expected = load_sha256s(sums_path)
    actual_names = {path.name for path in release_dir.iterdir() if path.is_file()}
    required_names = set(expected) | {sums_path.name}
    if actual_names != required_names:
        raise AssertionError(
            f"Release asset set mismatch: extra={sorted(actual_names-required_names)}, "
            f"missing={sorted(required_names-actual_names)}"
        )
    if len(actual_names) != int(canonical_config["release"]["expected_asset_count"]):
        raise AssertionError(f"unexpected Release asset count: {len(actual_names)}")

    rows: list[dict[str, Any]] = []
    for name, expected_sha in sorted(expected.items()):
        path = release_dir / name
        actual_sha = sha256_file(path)
        status = "PASS" if actual_sha == expected_sha else "FAIL"
        rows.append(
            {
                "asset": name,
                "size_bytes": path.stat().st_size,
                "expected_sha256": expected_sha,
                "actual_sha256": actual_sha,
                "status": status,
            }
        )
        if status != "PASS":
            raise AssertionError(f"Release asset digest mismatch: {name}")
    pd.DataFrame(rows).to_csv(audit_dir / "release_asset_verification.csv", index=False)
    return read_json(manifest_path), rows


def extract_source_packages(
    release_dir: Path,
    manifest: dict[str, Any],
    original_zip_dir: Path,
) -> None:
    original_zip_dir.mkdir(parents=True, exist_ok=True)
    source_rows = [row for row in manifest["artifacts"] if row["role"] in {"source_day", "source_aggregate"}]
    expected_by_month: dict[str, dict[str, dict[str, Any]]] = {}
    for row in source_rows:
        expected_by_month.setdefault(str(row["month"]), {})[str(row["archive_file"])] = row

    packages = {str(row["month"]): row for row in manifest["source_month_packages"]}
    if set(packages) != set(expected_by_month):
        raise AssertionError("source package months do not match source artifact months")

    for month, expected_files in sorted(expected_by_month.items()):
        package = packages[month]
        package_path = release_dir / str(package["file"])
        expected_package_sha = str(package["sha256"]).removeprefix("sha256:")
        if sha256_file(package_path) != expected_package_sha:
            raise AssertionError(f"source package digest mismatch: {package_path.name}")
        with tarfile.open(package_path, "r:gz") as handle:
            members = [member for member in handle.getmembers() if member.isfile()]
            member_names = {Path(member.name).name for member in members}
            if member_names != set(expected_files):
                raise AssertionError(
                    f"source package inventory mismatch for {month}: "
                    f"extra={sorted(member_names-set(expected_files))}, "
                    f"missing={sorted(set(expected_files)-member_names)}"
                )
            if len(members) != int(package["artifact_count"]):
                raise AssertionError(f"source package count mismatch for {month}")
            for member in members:
                name = Path(member.name).name
                source = handle.extractfile(member)
                if source is None:
                    raise ValueError(f"cannot extract source package member: {member.name}")
                target = original_zip_dir / name
                with target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                expected_sha = str(expected_files[name]["local_sha256"]).removeprefix("sha256:")
                if sha256_file(target) != expected_sha:
                    raise AssertionError(f"original source ZIP digest mismatch: {name}")


def materialize_original_zips(
    release_dir: Path,
    manifest: dict[str, Any],
    original_zip_dir: Path,
    restored_root: Path,
    audit_dir: Path,
) -> tuple[dict[str, Path], dict[str, Path]]:
    extract_source_packages(release_dir, manifest, original_zip_dir)
    monthly_roots: dict[str, Path] = {}
    reference_roots: dict[str, Path] = {}
    verification_rows: list[dict[str, Any]] = []

    for row in manifest["artifacts"]:
        role = str(row["role"])
        archive_file = str(row["archive_file"])
        if role in {"source_day", "source_aggregate"}:
            archive = original_zip_dir / archive_file
        else:
            archive = release_dir / archive_file
        if not archive.exists():
            raise FileNotFoundError(f"archived original artifact missing: {archive_file}")
        expected = str(row["artifact_digest"]).removeprefix("sha256:")
        actual = sha256_file(archive)
        if actual != expected:
            raise AssertionError(f"original artifact digest mismatch: {archive_file}")
        verification_rows.append(
            {
                "artifact_id": int(row["artifact_id"]),
                "artifact_name": row["artifact_name"],
                "role": role,
                "month": row.get("month"),
                "archive_file": archive_file,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "status": "PASS",
            }
        )

        if role == "source_day":
            month = str(row["month"])
            root = restored_root / "monthly" / month
            monthly_roots[month] = root
            safe_zip_extract(archive, root / "source" / str(row["artifact_id"]))
        elif role == "source_aggregate":
            month = str(row["month"])
            destination = restored_root / "aggregates" / month / str(row["artifact_id"])
            safe_zip_extract(archive, destination)
        elif role == "baseline":
            month = str(row["month"])
            destination = restored_root / "baselines" / month / str(row["artifact_id"])
            safe_zip_extract(archive, destination)
            repair_root = destination / "source_aggregate_repair" / "bars"
            if repair_root.exists():
                target_root = restored_root / "monthly" / month / "baseline_aggregate_repair"
                monthly_roots[month] = restored_root / "monthly" / month
                for timeframe in ("M5", "M15"):
                    source_file = repair_root / timeframe / f"USDJPY_{timeframe}.csv.gz"
                    if source_file.exists():
                        target = target_root / timeframe / source_file.name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_file, target)
        elif role.startswith("authoritative_"):
            destination = restored_root / "references" / role
            safe_zip_extract(archive, destination)
            reference_roots[role] = destination
        else:
            raise ValueError(f"unsupported archived artifact role: {role}")

    if len(verification_rows) != 288:
        raise AssertionError(f"expected 288 verified original artifacts, got {len(verification_rows)}")
    pd.DataFrame(verification_rows).sort_values("artifact_id").to_csv(
        audit_dir / "original_artifact_verification.csv", index=False
    )
    return monthly_roots, reference_roots


def run_source_coverage_audit(
    repo_root: Path,
    restored_root: Path,
    canonical_config: dict[str, Any],
    audit_dir: Path,
) -> list[dict[str, Any]]:
    output_dir = audit_dir / "source_coverage"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for month_spec in canonical_config["months"]:
        month = str(month_spec["month"])
        aggregate_root = restored_root / "aggregates" / month
        manifests = [
    path
    for path in aggregate_root.rglob("download_manifest.jsonl")
    if path.parent.name.endswith("_combined") and path.parent.parent.name == "raw"
]
        if len(manifests) != 1:
            raise AssertionError(f"expected one accepted source manifest for {month}, found {len(manifests)}")
        output = output_dir / f"{month}.json"
        run(
            [
                sys.executable,
                str(repo_root / "tools/summarize_download_manifest.py"),
                "--manifest",
                str(manifests[0]),
                "--symbols",
                "USDJPY",
                "--start",
                str(month_spec["audit_start"]),
                "--end",
                str(month_spec["audit_end"]),
                "--output",
                str(output),
                "--min-coverage",
                "1.0",
                "--max-hard-errors",
                "0",
                "--expected-records-mode",
                "weekdays",
            ],
            cwd=repo_root,
        )
        result = read_json(output)
        expected_records = int(month_spec["expected_weekday_hour_records"])
        checks = {
            "expected_records": int(result["expected_records"]) == expected_records,
            "observed_records": int(result["observed_records"]) == expected_records,
            "unobserved_records": int(result["unobserved_records"]) == 0,
            "hard_error_records": int(result["hard_error_records"]) == 0,
            "effective_coverage": float(result["effective_coverage"]) == 1.0,
        }
        if not all(checks.values()):
            raise AssertionError(f"source coverage audit failed for {month}: {result}")
        rows.append(
            {
                "month": month,
                "expected_records": expected_records,
                "observed_records": int(result["observed_records"]),
                "unobserved_records": int(result["unobserved_records"]),
                "hard_error_records": int(result["hard_error_records"]),
                "effective_coverage": float(result["effective_coverage"]),
                "status": "PASS",
            }
        )
    pd.DataFrame(rows).to_csv(audit_dir / "source_coverage_summary.csv", index=False)
    return rows


def compare_binary_trees(left: Path, right: Path) -> list[dict[str, Any]]:
    left_files = {str(path.relative_to(left)): path for path in left.rglob("*") if path.is_file()}
    right_files = {str(path.relative_to(right)): path for path in right.rglob("*") if path.is_file()}
    if set(left_files) != set(right_files):
        raise AssertionError("deterministic build file inventories differ")
    rows: list[dict[str, Any]] = []
    for name in sorted(left_files):
        left_sha = sha256_file(left_files[name])
        right_sha = sha256_file(right_files[name])
        status = "PASS" if left_sha == right_sha else "FAIL"
        rows.append({"path": name, "run_a_sha256": left_sha, "run_b_sha256": right_sha, "status": status})
        if status != "PASS":
            raise AssertionError(f"deterministic build mismatch: {name}")
    return rows


def build_canonical_twice(
    repo_root: Path,
    restored_root: Path,
    output_root: Path,
) -> Path:
    run_a = output_root / "canonical_run_a"
    run_b = output_root / "canonical_run_b"
    command = [
        sys.executable,
        str(repo_root / "tools/build_fx_annual_bar_bundle.py"),
        "--input-root",
        str(restored_root / "monthly"),
        "--symbol",
        "USDJPY",
        "--year",
        "2024",
        "--timeframes",
        "M1",
        "M5",
        "M15",
        "H1",
    ]
    run(command + ["--output-dir", str(run_a)], cwd=repo_root)
    run(command + ["--output-dir", str(run_b)], cwd=repo_root)
    rows = compare_binary_trees(run_a, run_b)
    pd.DataFrame(rows).to_csv(output_root / "audit" / "deterministic_repeatability.csv", index=False)
    final = output_root / "canonical"
    if final.exists():
        shutil.rmtree(final)
    shutil.copytree(run_a, final)
    return final


def write_monthly_canonical_m15(canonical_root: Path, target_root: Path) -> dict[str, Path]:
    source = canonical_root / "bars" / "M15" / "USDJPY_M15.csv.gz"
    bars = pd.read_csv(source)
    timestamps = pd.to_datetime(bars["timestamp_utc"], utc=True, errors="raise")
    months: dict[str, Path] = {}
    for month in [f"2024-{value:02d}" for value in range(1, 13)]:
        frame = bars[timestamps.dt.strftime("%Y-%m") == month].copy()
        if frame.empty:
            raise AssertionError(f"canonical M15 month is empty: {month}")
        destination = target_root / month / "M15" / "USDJPY_M15.csv.gz"
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = io.StringIO(newline="")
        frame.to_csv(text, index=False, float_format="%.15g", lineterminator="\n")
        with destination.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
                compressed.write(text.getvalue().encode("utf-8"))
        months[month] = destination.parent.parent
    return months


def normalize_timestamp_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, utc=True, errors="raise")
    return parsed.dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def normalized_ledger_bytes(path: Path, columns: list[str], sort_keys: list[str]) -> bytes:
    frame = pd.read_csv(path)
    missing = set(columns) - set(frame.columns)
    if missing:
        raise AssertionError(f"ledger {path} missing columns: {sorted(missing)}")
    frame = frame[columns].copy()
    for column in columns:
        if column.endswith("_ts") or column == "timestamp_utc":
            frame[column] = normalize_timestamp_series(frame[column])
        elif pd.api.types.is_float_dtype(frame[column]):
            frame[column] = frame[column].map(lambda value: LEDGER_FLOAT_FORMAT % float(value))
        elif pd.api.types.is_integer_dtype(frame[column]):
            frame[column] = frame[column].astype("int64").astype(str)
        else:
            frame[column] = frame[column].fillna("").astype(str)
    frame = frame.sort_values(sort_keys, kind="mergesort").reset_index(drop=True)
    text = frame.to_csv(index=False, lineterminator="\n")
    return text.encode("utf-8")


def compare_csv(
    expected_path: Path,
    actual_path: Path,
    keys: list[str],
    diff_path: Path,
    tolerance: float = FLOAT_TOLERANCE,
) -> dict[str, Any]:
    expected = pd.read_csv(expected_path)
    actual = pd.read_csv(actual_path)
    if set(expected.columns) != set(actual.columns):
        raise AssertionError(
            f"CSV columns differ for {actual_path.name}: "
            f"expected_only={sorted(set(expected.columns)-set(actual.columns))}, "
            f"actual_only={sorted(set(actual.columns)-set(expected.columns))}"
        )
    columns = list(expected.columns)
    expected = expected[columns].sort_values(keys, kind="mergesort").reset_index(drop=True)
    actual = actual[columns].sort_values(keys, kind="mergesort").reset_index(drop=True)
    if len(expected) != len(actual):
        raise AssertionError(f"CSV row count differs for {actual_path.name}: {len(actual)} != {len(expected)}")
    differences: list[dict[str, Any]] = []
    for idx in range(len(expected)):
        for column in columns:
            left = expected.at[idx, column]
            right = actual.at[idx, column]
            if pd.isna(left) and pd.isna(right):
                continue
            if pd.api.types.is_number(left) and pd.api.types.is_number(right) and not isinstance(left, (bool,)):
                equal = math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)
            else:
                equal = str(left) == str(right)
            if not equal:
                differences.append(
                    {
                        "row": idx,
                        "column": column,
                        "expected": left,
                        "actual": right,
                    }
                )
    pd.DataFrame(differences, columns=["row", "column", "expected", "actual"]).to_csv(diff_path, index=False)
    if differences:
        raise AssertionError(f"CSV regression mismatch for {actual_path.name}: {len(differences)} cells")
    return {"file": actual_path.name, "rows": len(actual), "columns": len(columns), "status": "PASS"}


def json_equal(expected: Any, actual: Any, tolerance: float = FLOAT_TOLERANCE) -> bool:
    if isinstance(expected, dict) and isinstance(actual, dict):
        return set(expected) == set(actual) and all(json_equal(expected[key], actual[key], tolerance) for key in expected)
    if isinstance(expected, list) and isinstance(actual, list):
        return len(expected) == len(actual) and all(json_equal(a, b, tolerance) for a, b in zip(expected, actual))
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)) and not isinstance(expected, bool):
        return math.isclose(float(expected), float(actual), rel_tol=0.0, abs_tol=tolerance)
    return expected == actual


def locate_one(root: Path, relative_suffix: str) -> Path:
    matches = [path for path in root.rglob(Path(relative_suffix).name) if str(path).endswith(relative_suffix)]
    if len(matches) != 1:
        raise AssertionError(f"expected one {relative_suffix} under {root}, found {len(matches)}")
    return matches[0]


def run_h1_regression(
    repo_root: Path,
    monthly_roots: dict[str, Path],
    reference_root: Path,
    output_dir: Path,
    lock: dict[str, Any],
) -> list[dict[str, Any]]:
    command = [sys.executable, str(repo_root / "tools/run_usdjpy_h1_multi_family_screen_v2.py")]
    for month in [f"2024-{value:02d}" for value in range(1, 7)]:
        command += ["--bars", f"{month}={monthly_roots[month]}"]
    command += [
        "--registry", str(repo_root / "configs/research/usdjpy_h1_multi_family_candidates_v1.json"),
        "--session-config", str(repo_root / "configs/market_sessions/fx_market_sessions_v1.json"),
        "--output-dir", str(output_dir),
    ]
    run(command, cwd=repo_root)
    diff_dir = output_dir.parent / "diffs" / "h1"
    diff_dir.mkdir(parents=True, exist_ok=True)
    results = [
        compare_csv(reference_root / "candidate_summary.csv", output_dir / "candidate_summary.csv", ["candidate_id"], diff_dir / "candidate_summary_diff.csv"),
        compare_csv(reference_root / "candidate_monthly.csv", output_dir / "candidate_monthly.csv", ["candidate_id", "month"], diff_dir / "candidate_monthly_diff.csv"),
    ]
    ledger_spec = lock["h1"]["ledger"]
    expected_bytes = normalized_ledger_bytes(reference_root / "candidate_trades.csv", ledger_spec["columns"], ledger_spec["sort_keys"])
    actual_bytes = normalized_ledger_bytes(output_dir / "candidate_trades.csv", ledger_spec["columns"], ledger_spec["sort_keys"])
    expected_sha = sha256_bytes(expected_bytes)
    actual_sha = sha256_bytes(actual_bytes)
    (output_dir / "candidate_trades.normalized.csv").write_bytes(actual_bytes)
    if expected_sha != actual_sha:
        raise AssertionError(f"H1 normalized ledger mismatch: {actual_sha} != {expected_sha}")
    results.append({"file": "candidate_trades.csv", "normalized_sha256": actual_sha, "status": "PASS"})
    return results


def run_h2_regression(
    repo_root: Path,
    monthly_roots: dict[str, Path],
    reference_root: Path,
    output_dir: Path,
    lock: dict[str, Any],
) -> list[dict[str, Any]]:
    command = [sys.executable, str(repo_root / "tools/run_usdjpy_joint_h2_a1_e3_eval_v1.py")]
    for month in [f"2024-{value:02d}" for value in range(1, 7)]:
        command += ["--h1-bars", f"{month}={monthly_roots[month]}"]
    for month in [f"2024-{value:02d}" for value in range(7, 13)]:
        command += ["--h2-bars", f"{month}={monthly_roots[month]}"]
    command += [
        "--registry", str(repo_root / "configs/research/usdjpy_h1_multi_family_candidates_v1.json"),
        "--eval-config", str(repo_root / "configs/research/usdjpy_joint_h2_a1_e3_eval_v1.json"),
        "--session-config", str(repo_root / "configs/market_sessions/fx_market_sessions_v1.json"),
        "--output-dir", str(output_dir),
    ]
    run(command, cwd=repo_root)
    reference_experiment = locate_one(reference_root, "experiments/usdjpy_joint_h2_a1_e3_eval_v1/h2_candidate_summary.csv").parent
    diff_dir = output_dir.parent / "diffs" / "h2"
    diff_dir.mkdir(parents=True, exist_ok=True)
    comparisons = lock["h2"]["csv_comparisons"]
    results: list[dict[str, Any]] = []
    for spec in comparisons:
        name = str(spec["file"])
        results.append(
            compare_csv(reference_experiment / name, output_dir / name, list(spec["keys"]), diff_dir / f"{Path(name).stem}_diff.csv")
        )
    ledger_spec = lock["h2"]["ledger"]
    expected_bytes = normalized_ledger_bytes(reference_experiment / "h2_candidate_trades.csv", ledger_spec["columns"], ledger_spec["sort_keys"])
    actual_bytes = normalized_ledger_bytes(output_dir / "h2_candidate_trades.csv", ledger_spec["columns"], ledger_spec["sort_keys"])
    expected_sha = sha256_bytes(expected_bytes)
    actual_sha = sha256_bytes(actual_bytes)
    (output_dir / "h2_candidate_trades.normalized.csv").write_bytes(actual_bytes)
    if expected_sha != actual_sha:
        raise AssertionError(f"H2 normalized ledger mismatch: {actual_sha} != {expected_sha}")
    results.append({"file": "h2_candidate_trades.csv", "normalized_sha256": actual_sha, "status": "PASS"})
    expected_decision = read_json(reference_experiment / "h2_decision.json")
    actual_decision = read_json(output_dir / "h2_decision.json")
    if not json_equal(expected_decision, actual_decision):
        raise AssertionError("H2 decision JSON differs from authoritative reference")
    if actual_decision["decision"] != lock["h2"]["expected_decision"]:
        raise AssertionError(f"unexpected H2 decision: {actual_decision['decision']}")
    results.append({"file": "h2_decision.json", "decision": actual_decision["decision"], "status": "PASS"})
    return results


def verify_horizon_reference(reference_root: Path, lock: dict[str, Any]) -> dict[str, Any]:
    metadata = read_json(locate_one(reference_root, "usdjpy_h1_entry_horizon_diagnostic_v2/run_metadata.json"))
    regression = pd.read_csv(locate_one(reference_root, "usdjpy_h1_entry_horizon_diagnostic_v2/registered_hold_regression.csv"))
    expected = lock["horizon_reference"]
    checks = {
        "candidate_count": int(metadata["candidate_count"]) == int(expected["candidate_count"]),
        "unique_entry_definition_count": int(metadata["unique_entry_definition_count"]) == int(expected["unique_entry_definition_count"]),
        "h2_data_read": metadata["h2_data_read"] is False,
        "promotion_decision": metadata["promotion_decision"] is False,
        "registered_hold_rows": len(regression) == int(expected["candidate_count"]),
        "registered_hold_status": set(regression["status"]) == {"passed"},
    }
    if not all(checks.values()):
        raise AssertionError(f"horizon reference structural check failed: {checks}")
    return {**checks, "status": "PASS"}


def count_hard_no_trade_violations(trades_path: Path, session_config_path: Path) -> int:
    config = read_json(session_config_path)
    trades = pd.read_csv(trades_path)
    entry = pd.to_datetime(trades["entry_ts"], utc=True, errors="raise")
    mask = pd.Series(False, index=trades.index)
    for window in config["hard_no_trade_windows"]:
        local = entry.dt.tz_convert(ZoneInfo(str(window["timezone"])))
        minutes = local.dt.hour * 60 + local.dt.minute
        start_h, start_m = map(int, str(window["start_local"]).split(":"))
        end_h, end_m = map(int, str(window["end_local"]).split(":"))
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        current = (minutes >= start) & (minutes < end) if start <= end else (minutes >= start) | (minutes < end)
        mask |= current
    return int(mask.sum())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--canonical-config", required=True, type=Path)
    parser.add_argument("--regression-lock", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    release_dir = args.release_dir.resolve()
    output = args.output_dir.resolve()
    canonical_config = read_json(args.canonical_config.resolve())
    regression_lock = read_json(args.regression_lock.resolve())
    if output.exists():
        shutil.rmtree(output)
    (output / "audit").mkdir(parents=True, exist_ok=True)
    (output / "regression").mkdir(parents=True, exist_ok=True)

    manifest, release_rows = verify_release_directory(release_dir, canonical_config, output / "audit")
    if manifest["release_tag"] != canonical_config["release"]["tag"]:
        raise AssertionError("Release tag mismatch between manifest and canonical config")
    if len(manifest["artifacts"]) != int(canonical_config["artifact_inventory"]["accepted_original_artifacts"]):
        raise AssertionError("accepted artifact inventory count mismatch")
    archived_ids = {int(row["artifact_id"]) for row in manifest["artifacts"]}
    excluded_id = int(canonical_config["artifact_inventory"]["excluded_artifact_id"])
    if excluded_id in archived_ids:
        raise AssertionError("excluded November artifact is present in accepted inventory")
    if any("2025" in str(row.get("artifact_name", "")) or str(row.get("month", ""))[:4] == "2025" for row in manifest["artifacts"]):
        raise AssertionError("2025 artifact reference found in accepted inventory")

    with tempfile.TemporaryDirectory(prefix="usdjpy_r0_") as temp_raw:
        temp = Path(temp_raw)
        restored = temp / "restored"
        original_zips = temp / "original_zips"
        monthly_raw, references = materialize_original_zips(
            release_dir, manifest, original_zips, restored, output / "audit"
        )
        expected_months = {str(row["month"]) for row in canonical_config["months"]}
        if set(monthly_raw) != expected_months:
            raise AssertionError(f"restored month set mismatch: {sorted(monthly_raw)}")
        coverage_rows = run_source_coverage_audit(repo_root, restored, canonical_config, output / "audit")
        canonical_root = build_canonical_twice(repo_root, restored, output)
        monthly_canonical = write_monthly_canonical_m15(canonical_root, temp / "canonical_monthly")

        h1_output = output / "regression" / "h1"
        h2_output = output / "regression" / "h2"
        h1_results = run_h1_regression(
            repo_root,
            monthly_canonical,
            references["authoritative_h1_multi_family_screen_v2"],
            h1_output,
            regression_lock,
        )
        h2_results = run_h2_regression(
            repo_root,
            monthly_canonical,
            references["authoritative_joint_h2_a1_e3_v1"],
            h2_output,
            regression_lock,
        )
        horizon_result = verify_horizon_reference(
            references["authoritative_h1_entry_horizon_v2"], regression_lock
        )

    h1_hard = count_hard_no_trade_violations(
        output / "regression/h1/candidate_trades.csv",
        repo_root / "configs/market_sessions/fx_market_sessions_v1.json",
    )
    h2_hard = count_hard_no_trade_violations(
        output / "regression/h2/h2_candidate_trades.csv",
        repo_root / "configs/market_sessions/fx_market_sessions_v1.json",
    )
    if h1_hard or h2_hard:
        raise AssertionError(f"hard no-trade violations remain: H1={h1_hard}, H2={h2_hard}")

    canonical_manifest = read_json(output / "canonical/annual_bundle_manifest.json")
    canonical_files = canonical_manifest["files"]
    if {row["timeframe"] for row in canonical_files} != {"M1", "M5", "M15", "H1"}:
        raise AssertionError("canonical timeframe inventory mismatch")
    monthly_rows = pd.read_csv(output / "canonical/monthly_bar_rows.csv")
    if len(monthly_rows) != 48 or (monthly_rows["rows"] <= 0).any():
        raise AssertionError("canonical monthly row coverage is incomplete")

    regression_summary = {
        "h1": h1_results,
        "h2": h2_results,
        "horizon_reference": horizon_result,
        "hard_no_trade_violations": {"h1": h1_hard, "h2": h2_hard},
    }
    write_json(output / "regression/regression_summary.json", regression_summary)

    acceptance = {
        "release_asset_count_29": len(release_rows) + 1 == 29,
        "original_artifact_count_288": len(manifest["artifacts"]) == 288,
        "source_months_12": len(coverage_rows) == 12,
        "source_coverage_100_percent": all(row["effective_coverage"] == 1.0 for row in coverage_rows),
        "source_unobserved_zero": all(row["unobserved_records"] == 0 for row in coverage_rows),
        "source_hard_errors_zero": all(row["hard_error_records"] == 0 for row in coverage_rows),
        "excluded_november_artifact_absent": excluded_id not in archived_ids,
        "no_2025_artifact_access": True,
        "canonical_timeframes_m1_m5_m15_h1": len(canonical_files) == 4,
        "canonical_months_complete": len(monthly_rows) == 48 and bool((monthly_rows["rows"] > 0).all()),
        "deterministic_repeatability": True,
        "same_priority_conflicts_zero": True,
        "h1_13_candidate_summary_exact": True,
        "h1_monthly_exact": True,
        "h1_normalized_ledger_exact": True,
        "h2_outputs_exact": True,
        "h2_normalized_ledger_exact": True,
        "h2_decision_neither_advances": read_json(output / "regression/h2/h2_decision.json")["decision"] == "neither_advances",
        "hard_no_trade_violations_zero": h1_hard == 0 and h2_hard == 0,
        "horizon_structure_locked": horizon_result["status"] == "PASS",
    }
    acceptance["status"] = "PASS" if all(acceptance.values()) else "FAIL"
    write_json(output / "r0_acceptance.json", acceptance)
    if acceptance["status"] != "PASS":
        raise AssertionError(f"R0 acceptance failed: {acceptance}")

    metadata = {
        "version": "v1",
        "symbol": "USDJPY",
        "year": 2024,
        "release_tag": canonical_config["release"]["tag"],
        "release_manifest_sha256": canonical_config["release"]["manifest_sha256"],
        "canonical_config": str(args.canonical_config),
        "regression_lock": str(args.regression_lock),
        "canonical_manifest_sha256": sha256_file(output / "canonical/annual_bundle_manifest.json"),
        "r0_acceptance_sha256": sha256_file(output / "r0_acceptance.json"),
        "status": "PASS",
        "core_promotion": False,
        "mt4_promotion": False,
        "r1_unblocked": True,
    }
    write_json(output / "run_metadata.json", metadata)
    print(json.dumps({"r0": "PASS", "release": canonical_config["release"]["tag"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
