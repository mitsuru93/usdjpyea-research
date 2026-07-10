#!/usr/bin/env python3
"""Resample downloaded tick files listed in a JSONL download manifest.

This wrapper avoids manually enumerating hourly files after a Dukascopy BI5 download.
It filters successful/existing records from the manifest and delegates to
`tools/resample_fx_ticks.py`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def load_paths(manifest: Path, symbols: set[str] | None) -> list[str]:
    paths: list[str] = []
    for line_no, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on {manifest}:{line_no}: {exc}") from exc
        status = record.get("status")
        symbol = str(record.get("symbol", "")).upper()
        path = record.get("path")
        if symbols is not None and symbol not in symbols:
            continue
        if status not in {"downloaded", "exists"}:
            continue
        if not path:
            continue
        tick_path = Path(str(path))
        if not tick_path.exists():
            raise FileNotFoundError(f"manifest path does not exist: {tick_path}")
        paths.append(str(tick_path))
    return sorted(paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resample tick files from a download manifest.")
    parser.add_argument("--manifest", required=True, help="JSONL manifest from download_dukascopy_bi5_ticks.py")
    parser.add_argument("--output-dir", required=True, help="Output directory for bars.")
    parser.add_argument("--symbols", nargs="+", default=None, help="Optional symbol filter.")
    parser.add_argument("--timeframes", nargs="+", default=["M1", "M5", "M15"], help="Timeframes passed to resample_fx_ticks.py")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = Path(args.manifest)
    symbols = {s.upper() for s in args.symbols} if args.symbols else None
    paths = load_paths(manifest, symbols)
    if not paths:
        raise RuntimeError("no downloaded/existing tick paths found in manifest")
    script = Path(__file__).resolve().parent / "resample_fx_ticks.py"
    cmd = [sys.executable, str(script)]
    for path in paths:
        cmd.extend(["--input", path])
    cmd.extend(["--output-dir", args.output_dir, "--timeframes", *args.timeframes])
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
