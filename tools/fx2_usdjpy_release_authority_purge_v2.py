#!/usr/bin/env python3
"""Execute v1 after correcting its isolated dictionary delimiter typo."""
from __future__ import annotations

import sys
import types
from pathlib import Path

SOURCE = Path(__file__).with_name("fx2_usdjpy_release_authority_purge_v1.py")


def load_fixed() -> types.ModuleType:
    text = SOURCE.read_text(encoding="utf-8")
    broken = '"digest": f"sha256:{digest.lower()}"):'
    fixed = '"digest": f"sha256:{digest.lower()}"}:'
    if text.count(broken) != 1:
        raise RuntimeError("isolated v1 syntax repair target is not unique")
    text = text.replace(broken, fixed)
    module = types.ModuleType("fx2_usdjpy_release_authority_purge_v1_fixed")
    module.__file__ = str(SOURCE)
    exec(compile(text, str(SOURCE), "exec"), module.__dict__)
    return module


def main() -> None:
    module = load_fixed()
    module.main()


if __name__ == "__main__":
    main()
