#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from usdjpy_integration_001_context import build_context
from usdjpy_integration_001_matrices import build_matrices
from usdjpy_integration_001_artifacts import write_artifacts

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--historical-trades", type=Path, required=True)
    ap.add_argument("--historical-states", type=Path, required=True)
    ap.add_argument("--mt4-2025-events", type=Path, required=True)
    ap.add_argument("--mt4-2025-summary", type=Path, required=True)
    ap.add_argument("--schema", type=Path, required=True)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    ctx = build_context(args, out)
    matrices = build_matrices(out, ctx)
    return write_artifacts(args, out, ctx, matrices)

if __name__ == "__main__":
    raise SystemExit(main())
