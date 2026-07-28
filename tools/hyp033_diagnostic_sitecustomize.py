"""HYP-033 technical diagnostic hook.

Captures an uncaught Python exception into the already-declared --out-dir.
It does not alter source data, candidate logic, periods, thresholds, gates, or outcomes.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _output_directory() -> Path | None:
    try:
        i = sys.argv.index("--out-dir")
        return Path(sys.argv[i + 1])
    except (ValueError, IndexError):
        return None


def _capture(exc_type, exc_value, exc_traceback) -> None:
    out = _output_directory()
    if out is not None:
        try:
            out.mkdir(parents=True, exist_ok=True)
            with (out / "technical_exception.log").open("w", encoding="utf-8") as f:
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        except Exception:
            pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = _capture
