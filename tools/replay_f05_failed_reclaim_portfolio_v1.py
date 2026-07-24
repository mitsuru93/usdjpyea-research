#!/usr/bin/env python3
"""Compatibility entrypoint for the frozen F05 failed-reclaim portfolio evaluator."""
from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).with_name("evaluate_f05_failed_reclaim_portfolio_v1.py")),
        run_name="__main__",
    )
