#!/usr/bin/env python3
"""Recover one EURUSD 2024 raw-tick month from a prior GitHub Actions run.

The script downloads every immutable day artifact for the requested month,
validates each packet, re-collects only invalid days with conservative retry
settings, and emits a deterministic validated monthly package.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import gzip
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

API_ROOT = "https://api.github.com"
USER_AGENT = "usdjpyea-research-eurusd-recovery-v1"
REDIRECT_CODES = {301, 302, 303, 307, 308}
SYMBOL = "EURUSD"
COUNT_FIELDS = (
    "resolved_hours",
    "downloaded_hours",
    "missing_404_hours",
    "no_tick_hours",
    "error_hours",
    "tick_rows",
    "negative_spread_rows",
    "source_bi5_bytes",
    "decoded_csv_bytes",
)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def api_request(url: str, token: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        },
    )


def storage_request(url: str) -> urllib.request.Request:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise RuntimeError(f"invalid signed artifact URL: {url!r}")
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def read_json(url: str, token: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(api_request(url, token), timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API HTTP {exc.code} for {url}: {body[:1000]}") from exc


def list_run_artifacts(repository: str, run_id: int, token: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for page in range(1, 101):
        payload = read_json(
            f"{API_ROOT}/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100&page={page}",
            token,
        )
        rows = payload.get("artifacts")
        if not isinstance(rows, list):
            raise RuntimeError(f"artifact response missing list on page {page}")
        artifacts.extend(rows)
        if len(rows) < 100:
            return artifacts
    raise RuntimeError("artifact pagination exceeded 100 pages")


def resolve_download_url(repository: str, artifact_id: int, token: str) -> str:
    url = f"{API_ROOT}/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(api_request(url, token), timeout=120) as response:
            location = response.headers.get("Location")
            if location:
                return location
            raise RuntimeError(f"artifact endpoint returned {response.status} without redirect: {artifact_id}")
    except urllib.error.HTTPError as exc:
        if exc.code in REDIRECT_CODES:
            location = exc.headers.get("Location")
            if location:
                return location
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"artifact redirect HTTP {exc.code} for {artifact_id}: {body[:1000]}") from exc


def safe_extract(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            relative = PurePosixPath(member.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError(f"unsafe artifact member: {member.filename!r}")
            if stat.S_ISLNK(member.external_attr >> 16):
                raise RuntimeError(f"artifact symbolic link rejected: {member.filename!r}")
            target = destination.joinpath(*relative.parts)
            resolved = target.resolve()
            if root != resolved and root not in resolved.parents:
                raise RuntimeError(f"artifact member escapes destination: {member.filename!r}")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)


def download_artifact(repository: str, artifact_id: int, token: str, target_zip: Path) -> None:
    signed_url = resolve_download_url(repository, artifact_id, token)
    try:
        with urllib.request.urlopen(storage_request(signed_url), timeout=300) as response, target_zip.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"signed artifact HTTP {exc.code} for {artifact_id}: {body[:1000]}") from exc
    if not target_zip.is_file() or target_zip.stat().st_size == 0 or not zipfile.is_zipfile(target_zip):
        raise RuntimeError(f"invalid artifact ZIP: {artifact_id}")


def verify_checksum_file(root: Path) -> list[str]:
    failures: list[str] = []
    checksum_path = root / "SHA256SUMS"
    if not checksum_path.is_file():
        return ["missing SHA256SUMS"]
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            digest, relative = line.split(maxsplit=1)
        except ValueError:
            failures.append(f"malformed checksum line: {line!r}")
            continue
        relative = relative.lstrip("* ")
        target = root / relative
        if not target.is_file():
            failures.append(f"checksum target missing: {relative}")
        elif sha256_file(target) != digest:
            failures.append(f"checksum mismatch: {relative}")
    return failures


def validate_day(root: Path, day: str) -> tuple[dict[str, int], dict[str, Any], list[str]]:
    failures = verify_checksum_file(root)
    manifest_path = root / "download_manifest.jsonl"
    summary_path = root / "day_summary.json"
    if not manifest_path.is_file() or not summary_path.is_file():
        return {}, {}, failures + [f"missing manifest or summary: {day}"]

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("symbol") != SYMBOL or summary.get("date") != day:
        failures.append(f"summary identity mismatch: {day}")
    if not summary.get("accepted"):
        failures.append(f"source day summary not accepted: {day}: {summary.get('failures')}")

    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 24:
        failures.append(f"terminal record count {len(rows)} != 24: {day}")

    computed = {key: 0 for key in COUNT_FIELDS}
    seen: set[str] = set()
    for row in rows:
        hour = str(row.get("hour_start_utc", ""))
        if hour in seen:
            failures.append(f"duplicate terminal record: {hour}")
        seen.add(hour)
        if row.get("symbol") != SYMBOL:
            failures.append(f"unexpected symbol at {hour}")
        status = str(row.get("status", "error"))
        if status == "downloaded":
            source = root / str(row.get("source_bi5_path", ""))
            decoded = root / str(row.get("decoded_csv_path", ""))
            if not source.is_file() or sha256_file(source) != row.get("source_bi5_sha256"):
                failures.append(f"BI5 verification failed: {hour}")
            if not decoded.is_file() or sha256_file(decoded) != row.get("decoded_csv_sha256"):
                failures.append(f"decoded CSV verification failed: {hour}")
            computed["downloaded_hours"] += 1
            computed["tick_rows"] += int(row.get("rows", 0))
            computed["negative_spread_rows"] += int(row.get("negative_spread_rows", 0))
            computed["source_bi5_bytes"] += int(row.get("source_bi5_bytes", 0))
            computed["decoded_csv_bytes"] += int(row.get("decoded_csv_bytes", 0))
        elif status == "missing_404":
            computed["missing_404_hours"] += 1
        elif status == "no_ticks":
            computed["no_tick_hours"] += 1
        else:
            computed["error_hours"] += 1
            failures.append(f"terminal error: {hour} {row.get('error_type')} {row.get('error')}")
    computed["resolved_hours"] = len(rows) - computed["error_hours"]
    for key in COUNT_FIELDS:
        if int(summary.get(key, -1)) != computed[key]:
            failures.append(f"summary mismatch {key}: recorded={summary.get(key)} computed={computed[key]}")
    if computed["negative_spread_rows"]:
        failures.append(f"negative spread rows: {computed['negative_spread_rows']}")
    if sha256_file(manifest_path) != summary.get("manifest_sha256"):
        failures.append("manifest digest mismatch")
    return computed, summary, failures


def write_checksums(root: Path) -> None:
    paths = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    with (root / "SHA256SUMS").open("w", encoding="utf-8", newline="\n") as fh:
        for path in paths:
            fh.write(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n")


def collect_day(repository_root: Path, day: str, root: Path) -> dict[str, Any]:
    if root.exists():
        shutil.rmtree(root)
    (root / "source_bi5").mkdir(parents=True)
    (root / "decoded_csv").mkdir(parents=True)
    next_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    attempts = root / "download_manifest.attempts.jsonl"
    command = [
        "python", str(repository_root / "tools/download_dukascopy_tick_archive_v1.py"),
        "--symbols", SYMBOL,
        "--start", f"{day}T00",
        "--end", f"{next_day}T00",
        "--bi5-output-root", str(root / "source_bi5"),
        "--tick-output-root", str(root / "decoded_csv"),
        "--manifest-out", str(attempts),
        "--retries", "8",
        "--sleep-seconds", "2.0",
        "--request-interval", "0.25",
        "--request-timeout", "60",
        "--max-errors", "24",
        "--error-retry-passes", "6",
        "--error-retry-sleep-seconds", "15",
        "--error-retry-request-timeout", "90",
        "--error-retry-retries", "8",
    ]
    completed = subprocess.run(command, cwd=repository_root, text=True)
    rows = []
    if attempts.is_file():
        rows = [json.loads(line) for line in attempts.read_text(encoding="utf-8").splitlines() if line.strip()]
    final: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        final[(str(row.get("symbol", "")), str(row.get("hour_start_utc", "")))] = row

    failures: list[str] = []
    normalized: list[dict[str, Any]] = []
    totals = {"expected_hours": 24, **{key: 0 for key in COUNT_FIELDS}}
    start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    for offset in range(24):
        hour = start + timedelta(hours=offset)
        key = (SYMBOL, hour.strftime("%Y-%m-%dT%H:%M:%SZ"))
        row = final.get(key)
        if row is None:
            totals["error_hours"] += 1
            failures.append(f"missing terminal record: {key[1]}")
            continue
        status = str(row.get("status", "error"))
        out: dict[str, Any] = {
            "symbol": SYMBOL,
            "hour_start_utc": key[1],
            "status": status,
            "rows": int(row.get("rows", 0)),
            "url": row.get("url"),
        }
        if status == "downloaded":
            source_rel = Path("source_bi5") / SYMBOL / hour.strftime("%Y/%m/%d") / f"{hour:%H}h_ticks.bi5"
            tick_rel = Path("decoded_csv") / SYMBOL / hour.strftime("%Y/%m/%d") / f"{hour:%H}.csv.gz"
            source = root / source_rel
            tick = root / tick_rel
            if not source.is_file() or not tick.is_file():
                failures.append(f"missing downloaded payload: {key[1]}")
                totals["error_hours"] += 1
                normalized.append(out)
                continue
            source_sha = sha256_file(source)
            tick_sha = sha256_file(tick)
            if source_sha != row.get("bi5_sha256"):
                failures.append(f"BI5 digest mismatch: {key[1]}")
            if tick_sha != row.get("tick_gzip_sha256"):
                failures.append(f"Tick digest mismatch: {key[1]}")
            tick_rows = 0
            negative = 0
            with gzip.open(tick, "rt", encoding="utf-8", newline="") as fh:
                for tick_row in csv.DictReader(fh):
                    tick_rows += 1
                    if tick_row.get("symbol") != SYMBOL:
                        failures.append(f"unexpected symbol: {key[1]}")
                        break
                    if Decimal(tick_row["ask"]) < Decimal(tick_row["bid"]):
                        negative += 1
            if tick_rows != int(row.get("rows", 0)):
                failures.append(f"Tick row mismatch: {key[1]} {tick_rows} != {row.get('rows')}")
            if negative:
                failures.append(f"negative spreads: {key[1]} rows={negative}")
            out.update({
                "source_bi5_path": source_rel.as_posix(),
                "source_bi5_sha256": source_sha,
                "source_bi5_bytes": source.stat().st_size,
                "decoded_csv_path": tick_rel.as_posix(),
                "decoded_csv_sha256": tick_sha,
                "decoded_csv_bytes": tick.stat().st_size,
                "negative_spread_rows": negative,
            })
            totals["resolved_hours"] += 1
            totals["downloaded_hours"] += 1
            totals["tick_rows"] += tick_rows
            totals["negative_spread_rows"] += negative
            totals["source_bi5_bytes"] += source.stat().st_size
            totals["decoded_csv_bytes"] += tick.stat().st_size
        elif status in {"missing_404", "no_ticks"}:
            totals["resolved_hours"] += 1
            totals["missing_404_hours" if status == "missing_404" else "no_tick_hours"] += 1
        else:
            totals["error_hours"] += 1
            failures.append(f"terminal error: {key[1]} {row.get('error_type')} {row.get('error')}")
            out.update(error_type=row.get("error_type"), error=row.get("error"))
        normalized.append(out)

    manifest = root / "download_manifest.jsonl"
    manifest.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in normalized), encoding="utf-8")
    accepted = (
        completed.returncode == 0
        and not failures
        and len(normalized) == 24
        and totals["resolved_hours"] == 24
        and totals["error_hours"] == 0
        and totals["negative_spread_rows"] == 0
    )
    summary = {
        "schema_version": "eurusd_raw_tick_day_v1",
        "symbol": SYMBOL,
        "date": day,
        **totals,
        "manifest_sha256": sha256_file(manifest),
        "failures": failures,
        "accepted": accepted,
        "recovered": True,
    }
    (root / "day_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_checksums(root)
    if not accepted:
        raise RuntimeError(f"recovery failed for {day}: {'; '.join(failures[:20])}")
    return summary


def build_tar(staging: Path, out_path: Path, days: list[str]) -> None:
    tar_command = [
        "tar", "--sort=name", "--mtime=UTC 1970-01-01", "--owner=0", "--group=0", "--numeric-owner",
        "-cf", "-", "-C", str(staging), *days,
    ]
    with out_path.open("wb") as output:
        tar_process = subprocess.Popen(tar_command, stdout=subprocess.PIPE)
        assert tar_process.stdout is not None
        gzip_process = subprocess.Popen(["gzip", "-n"], stdin=tar_process.stdout, stdout=output)
        tar_process.stdout.close()
        gzip_rc = gzip_process.wait()
        tar_rc = tar_process.wait()
    if tar_rc or gzip_rc:
        raise RuntimeError(f"deterministic tar failed: tar={tar_rc} gzip={gzip_rc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-run-id", required=True, type=int)
    parser.add_argument("--source-run-attempt", required=True, type=int)
    parser.add_argument("--month", required=True, type=int, choices=range(1, 13))
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--package-run-id", required=True, type=int)
    parser.add_argument("--package-run-attempt", required=True, type=int)
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"missing token environment: {args.token_env}")
    repository_root = Path(__file__).resolve().parents[1]
    args.staging.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    days = [date(2024, args.month, value).isoformat() for value in range(1, calendar.monthrange(2024, args.month)[1] + 1)]

    artifacts = list_run_artifacts(args.repository, args.source_run_id, token)
    by_name: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        by_name.setdefault(str(artifact.get("name")), []).append(artifact)

    receipts: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="eurusd-source-artifacts-") as temp:
        temp_root = Path(temp)
        for day in days:
            name = f"eurusd-raw-ticks-{day}-{args.source_run_id}-{args.source_run_attempt}"
            matches = by_name.get(name, [])
            if len(matches) != 1:
                raise RuntimeError(f"{name}: expected exactly one artifact, found {len(matches)}")
            artifact = matches[0]
            if bool(artifact.get("expired")):
                raise RuntimeError(f"expired source artifact: {name}")
            artifact_id = int(artifact["id"])
            zip_path = temp_root / f"{artifact_id}.zip"
            print(json.dumps({"event": "download_source_day", "date": day, "artifact_id": artifact_id, "name": name}))
            download_artifact(args.repository, artifact_id, token, zip_path)
            safe_extract(zip_path, args.staging)
            receipts.append({
                "date": day,
                "artifact_id": artifact_id,
                "artifact_name": name,
                "artifact_digest": artifact.get("digest"),
                "artifact_size_in_bytes": int(artifact.get("size_in_bytes", 0)),
                "created_at": artifact.get("created_at"),
            })

    original_failures: list[dict[str, Any]] = []
    recovered_dates: list[str] = []
    day_summaries: list[dict[str, Any]] = []
    totals = {
        "expected_days": len(days),
        "present_days": 0,
        "expected_hours": len(days) * 24,
        **{key: 0 for key in COUNT_FIELDS},
    }
    for day in days:
        root = args.staging / day
        computed, summary, failures = validate_day(root, day)
        if failures:
            original_failures.append({"date": day, "failures": failures, "recorded_summary": summary})
            print(json.dumps({"event": "recover_day", "date": day, "failure_count": len(failures)}))
            collect_day(repository_root, day, root)
            recovered_dates.append(day)
            computed, summary, failures = validate_day(root, day)
            if failures:
                raise RuntimeError(f"post-recovery validation failed for {day}: {'; '.join(failures[:20])}")
        totals["present_days"] += 1
        day_summaries.append(summary)
        for key in COUNT_FIELDS:
            totals[key] += int(computed[key])

    accepted = (
        totals["present_days"] == totals["expected_days"]
        and totals["resolved_hours"] == totals["expected_hours"]
        and totals["error_hours"] == 0
        and totals["negative_spread_rows"] == 0
    )
    manifest = {
        "schema_version": "eurusd_2024_raw_tick_month_recovered_v1",
        "symbol": SYMBOL,
        "month": f"2024-{args.month:02d}",
        "source": "Dukascopy BI5 public Bid/Ask ticks",
        "source_workflow_run_id": args.source_run_id,
        "source_workflow_run_attempt": args.source_run_attempt,
        "package_workflow_run_id": args.package_run_id,
        "package_workflow_run_attempt": args.package_run_attempt,
        "totals": totals,
        "original_failures": original_failures,
        "recovered_dates": recovered_dates,
        "day_summaries": day_summaries,
        "accepted": accepted,
    }
    manifest_path = args.out / f"eurusd-2024-{args.month:02d}-raw-ticks-v1.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_path = args.out / f"eurusd-2024-{args.month:02d}-source-artifacts.json"
    receipt_path.write_text(json.dumps({
        "schema_version": "eurusd_source_artifact_receipt_v1",
        "source_run_id": args.source_run_id,
        "source_run_attempt": args.source_run_attempt,
        "total_artifacts_enumerated": len(artifacts),
        "month": f"2024-{args.month:02d}",
        "artifacts": receipts,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not accepted:
        raise RuntimeError(f"month validation failed: {manifest['month']} {totals}")

    tar_path = args.out / f"eurusd-2024-{args.month:02d}-raw-ticks-v1.tar.gz"
    build_tar(args.staging, tar_path, days)
    checksum_path = args.out / f"eurusd-2024-{args.month:02d}-raw-ticks-v1.SHA256SUMS"
    files = sorted(path for path in args.out.iterdir() if path.is_file() and path != checksum_path)
    with checksum_path.open("w", encoding="utf-8", newline="\n") as fh:
        for path in files:
            fh.write(f"{sha256_file(path)}  {path.name}\n")
    print(json.dumps({"month": manifest["month"], "accepted": True, "recovered_dates": recovered_dates, **totals}, sort_keys=True))


if __name__ == "__main__":
    main()
