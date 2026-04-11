"""Candidate generation from envelope touch events.

This module intentionally labels candidates conservatively and does NOT
attempt to reproduce full MT4 entry gating/position semantics.
"""

from __future__ import annotations

import pandas as pd

ASSUMPTION_VERSION = "sim_v1_conservative"
TP_SL_BY_FAMILY = {
    "rev": {"tp_pips": 10, "sl_pips": 30},
    "trend": {"tp_pips": 10, "sl_pips": 20},
}


def build_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Generate candidate rows from touch events.

    Mapping:
    - upper touch => rev sell, trend buy
    - lower touch => rev buy, trend sell
    """
    candidate_rows: list[dict] = []

    for row in df.itertuples(index=False):
        if row.touch_upper:
            candidate_rows.extend(
                [
                    _make_candidate(row, touch_side="upper", family="rev", direction="sell"),
                    _make_candidate(row, touch_side="upper", family="trend", direction="buy"),
                ]
            )
        if row.touch_lower:
            candidate_rows.extend(
                [
                    _make_candidate(row, touch_side="lower", family="rev", direction="buy"),
                    _make_candidate(row, touch_side="lower", family="trend", direction="sell"),
                ]
            )

    return pd.DataFrame(candidate_rows)


def _make_candidate(row: object, touch_side: str, family: str, direction: str) -> dict:
    levels = TP_SL_BY_FAMILY[family]
    return {
        "timestamp": row.datetime,
        "session": row.session,
        "month": row.month,
        "touch_side": touch_side,
        "candidate_family": family,
        "direction": direction,
        "entry_price": float(row.close),
        "tp_pips": levels["tp_pips"],
        "sl_pips": levels["sl_pips"],
        "assumption_version": ASSUMPTION_VERSION,
    }
