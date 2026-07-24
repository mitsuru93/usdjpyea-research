#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path
_PARTS = ['evaluate_usdjpy_b02_f05_lifecycle_abc_v1.part01.pyfrag', 'evaluate_usdjpy_b02_f05_lifecycle_abc_v1.part02.pyfrag', 'evaluate_usdjpy_b02_f05_lifecycle_abc_v1.part03.pyfrag', 'evaluate_usdjpy_b02_f05_lifecycle_abc_v1.part04.pyfrag', 'evaluate_usdjpy_b02_f05_lifecycle_abc_v1.part05.pyfrag', 'evaluate_usdjpy_b02_f05_lifecycle_abc_v1.part06.pyfrag']
_SOURCE_SHA256 = 'e769943b736e1318bf63928fe80903fead355dd5590b8f6a3f28d27e5d889561'
_root = Path(__file__).resolve().parent
_source = ''.join((_root / p).read_text(encoding='utf-8') for p in _PARTS)
_actual = hashlib.sha256(_source.encode('utf-8')).hexdigest()
if _actual != _SOURCE_SHA256:
    raise RuntimeError(f'evaluator source bundle SHA mismatch: {_actual} != {_SOURCE_SHA256}')
exec(compile(_source, str(Path(__file__).with_suffix('.materialized.py')), 'exec'), globals(), globals())
