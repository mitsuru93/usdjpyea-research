#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd

import replay_usdjpy_hyp044_source_native_full_equity_v2 as base


def load_ledger(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {
        "variant_id", "trade_id", "strategy", "entry_utc", "close_utc", "side",
        "entry_price", "pnl_jpy", "lots",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"ledger missing columns: {missing}")
    frame["entry_utc"] = pd.to_datetime(frame["entry_utc"], utc=True, format="mixed")
    frame["close_utc"] = pd.to_datetime(frame["close_utc"], utc=True, format="mixed")
    frame["side"] = pd.to_numeric(frame["side"], errors="raise").astype(int)
    frame["entry_price"] = pd.to_numeric(frame["entry_price"], errors="raise")
    frame["pnl_jpy"] = pd.to_numeric(frame["pnl_jpy"], errors="raise")
    frame["lots"] = pd.to_numeric(frame["lots"], errors="raise")
    return frame


if __name__ == "__main__":
    base.load_ledger = load_ledger
    base.main()
