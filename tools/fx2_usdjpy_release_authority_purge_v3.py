#!/usr/bin/env python3
"""Execute v1 with two isolated compatibility repairs.

1. Correct the dictionary delimiter typo.
2. Accept supplemental Release assets not enumerated by the committed payload/metadata
   manifest, while still sealing the complete Release asset identity SHA-256. Every
   manifest-listed asset remains required and byte-identical.
"""
from __future__ import annotations

import types
from pathlib import Path

SOURCE = Path(__file__).with_name("fx2_usdjpy_release_authority_purge_v1.py")


def load_fixed() -> types.ModuleType:
    text = SOURCE.read_text(encoding="utf-8")
    replacements = {
        '"digest": f"sha256:{digest.lower()}"):': '"digest": f"sha256:{digest.lower()}"}:',
        '    if len(seen_ids) != identity["asset_count"]:\n        raise Error(f"source-native Release has unbound assets: bound={len(seen_ids)} total={identity[\'asset_count\']}")\n':
        '    if len(seen_ids) > identity["asset_count"]:\n        raise Error(f"source-native manifest binds more assets than the Release contains: bound={len(seen_ids)} total={identity[\'asset_count\']}")\n',
    }
    for broken, fixed in replacements.items():
        if text.count(broken) != 1:
            raise RuntimeError(f"isolated compatibility repair target is not unique: {broken[:80]}")
        text = text.replace(broken, fixed)
    module = types.ModuleType("fx2_usdjpy_release_authority_purge_v1_fixed_v3")
    module.__file__ = str(SOURCE)
    exec(compile(text, str(SOURCE), "exec"), module.__dict__)
    return module


def main() -> None:
    load_fixed().main()


if __name__ == "__main__":
    main()
