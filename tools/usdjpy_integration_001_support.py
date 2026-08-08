#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from usdjpy_common_portfolio.framework import (
    WORK_ID, CHRONOLOGY, COMMON_INITIAL_CAPITAL_JPY, DEFAULT_LOT,
    adapt_historical_baseline, adapt_mt4_event_log, clean, drawdown_details,
    historical_full_equity, margin_series_from_trades, period_metrics,
    profit_factor, recovery_classification, requested_combinations, sha256_file,
    validate_common_ledger, write_json,
)

RESEARCH_MAIN = "4a6cb16768bbacc0c9bbeabfd5817bb26318c81a"
CORE_MAIN = "f897b250b808207d960417b2306935dcb0655acf"
HIST_RESEARCH_SHA = "e56c3dac189bf283b528253cee3ed718f4358fa8"
HIST_TRADE_SHA = "98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca"
HIST_STATE_SHA = "2caddc38cdb16ce7504fe1e3b625f8425ccc6f7d579d02590f9ee92bbf013eda"
BASELINE_2025_ARTIFACT = "sha256:0867bb4d8bfb0be9f96e61dd1e9c73aadd56b2b217b514532596e644dc95a72a"
GENERATED_AT = "2026-07-29T13:12:00Z"


def deterministic_zip(root: Path, zip_path: Path) -> None:
    files = sorted(p for p in root.rglob("*") if p.is_file() and p != zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def to_json_record(row: pd.Series) -> dict:
    out = {}
    for k, v in row.items():
        if pd.isna(v):
            out[k] = None
        elif isinstance(v, pd.Timestamp):
            out[k] = v.isoformat().replace("+00:00", "Z")
        else:
            out[k] = v.item() if hasattr(v, "item") else v
    return out
