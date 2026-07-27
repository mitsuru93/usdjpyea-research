#!/usr/bin/env python3
# Deterministic bootstrap for the audited Shock Failure 2025 postmortem evaluator.
from __future__ import annotations
import base64
import hashlib
from pathlib import Path
import zlib

EXPECTED_SOURCE_SHA256 = "cc6cd2c9885acd25769fea709ecfa246f1338a3aebda28bf4ae62b9b6f553bbc"
PART_DIR = Path(__file__).with_name("postmortem_payload_v1")
parts = sorted(PART_DIR.glob("part_*.txt"))
if len(parts) != 4:
    raise RuntimeError(f"postmortem payload part count={len(parts)} expected=4")
payload = "".join(p.read_text(encoding="ascii").strip() for p in parts)
source = zlib.decompress(base64.b64decode(payload, validate=True))
actual = hashlib.sha256(source).hexdigest()
if actual != EXPECTED_SOURCE_SHA256:
    raise RuntimeError(f"decoded evaluator SHA-256 mismatch: {actual}")
decoded = Path(__file__).with_suffix(".decoded.py")
decoded.write_bytes(source)
exec(compile(source, str(decoded), "exec"), {"__name__": "__main__", "__file__": str(decoded)})
