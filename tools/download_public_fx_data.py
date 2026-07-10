#!/usr/bin/env python3
"""Download public FX research source files from an explicit manifest.

This tool intentionally does not scrape vendor websites. It downloads only URLs that
are explicitly recorded in a manifest so the research pipeline remains auditable and
reproducible. Raw bulk data should be stored as release assets or workflow artifacts,
not committed directly to git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    yaml = None


@dataclass(frozen=True)
class DownloadItem:
    source_id: str
    symbol: str
    url: str
    filename: str
    expected_sha256: str | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> list[DownloadItem]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to read the download manifest.")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"manifest must be a mapping: {path}")
    items = raw.get("downloads")
    if not isinstance(items, list):
        raise ValueError("manifest must contain a downloads: list")
    parsed: list[DownloadItem] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"downloads[{idx}] must be a mapping")
        for key in ("source_id", "symbol", "url", "filename"):
            if not item.get(key):
                raise ValueError(f"downloads[{idx}] missing required key: {key}")
        parsed.append(
            DownloadItem(
                source_id=str(item["source_id"]),
                symbol=str(item["symbol"]).upper(),
                url=str(item["url"]),
                filename=str(item["filename"]),
                expected_sha256=str(item["expected_sha256"]) if item.get("expected_sha256") else None,
            )
        )
    return parsed


def download_one(item: DownloadItem, output_root: Path, overwrite: bool) -> dict[str, Any]:
    symbol_dir = output_root / item.source_id / item.symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)
    out_path = symbol_dir / item.filename
    if out_path.exists() and not overwrite:
        status = "exists"
    else:
        status = "downloaded"
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
        with urllib.request.urlopen(item.url, timeout=120) as response, tmp_path.open("wb") as fh:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        tmp_path.replace(out_path)
    actual = sha256_file(out_path)
    verified = item.expected_sha256 is None or actual.lower() == item.expected_sha256.lower()
    if not verified:
        raise RuntimeError(
            f"sha256 mismatch for {out_path}: expected={item.expected_sha256} actual={actual}"
        )
    return {
        "source_id": item.source_id,
        "symbol": item.symbol,
        "url": item.url,
        "path": str(out_path),
        "filename": item.filename,
        "sha256": actual,
        "expected_sha256": item.expected_sha256,
        "status": status,
        "verified": verified,
        "bytes": out_path.stat().st_size,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download explicit public FX source files and write checksums.")
    parser.add_argument("--manifest", required=True, help="YAML manifest with a downloads: list.")
    parser.add_argument("--output-root", required=True, help="Directory for raw downloaded files.")
    parser.add_argument("--manifest-out", default=None, help="Optional JSONL output path for download records.")
    parser.add_argument("--overwrite", action="store_true", help="Re-download even when the target file exists.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    records = []
    for item in load_manifest(manifest_path):
        record = download_one(item, output_root, overwrite=args.overwrite)
        records.append(record)
        print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    manifest_out = Path(args.manifest_out) if args.manifest_out else output_root / "download_manifest.jsonl"
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records) + "\n", encoding="utf-8")
    print(f"wrote manifest: {manifest_out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
