"""Frozen M1/M5 event adapters for F05 failed-reclaim validation."""
from __future__ import annotations

from typing import Iterable

import pandas as pd

from usdjpy_structural_sl_v1.common import (
    PIP,
    executable_price,
    inside,
    max_exec,
    min_exec,
    next_exit,
    outside,
    pnl,
    r1,
)


def trade_key(tr: object) -> str:
    signal = pd.Timestamp(tr.signal_utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{tr.strategy}|{signal}|{int(tr.side)}"


def _consecutive_outside(
    m1: pd.DataFrame,
    start_completion: pd.Timestamp,
    end_completion: pd.Timestamp,
    side: int,
    level: float,
) -> int:
    window = m1[
        ((m1.index + pd.Timedelta(minutes=1)) >= start_completion)
        & ((m1.index + pd.Timedelta(minutes=1)) <= end_completion)
    ]
    longest = 0
    run = 0
    for _, bar in window.iterrows():
        if outside(executable_price(bar, side, "close"), level, side):
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return int(longest)


def failed_reclaim_event(
    tr: object,
    m1: pd.DataFrame,
    m5: pd.DataFrame,
    *,
    allow_same_time_m5: bool,
) -> dict[str, object] | None:
    """Return one deterministic event or None.

    The exploration adapter sets ``allow_same_time_m5=True`` only for the
    byte-identified historical reproduction gate.  The binding adapter sets it
    to False, so the failure M5 completion must be strictly later than the
    reclaim M1 completion.
    """
    if str(tr.strategy) != "F05":
        return None
    side = int(tr.side)
    entry = pd.Timestamp(tr.entry_utc)
    baseline_close = pd.Timestamp(tr.close_utc)
    level = float(tr.breakout_level)
    entry_price = float(tr.entry_price)

    first_start = entry.floor("5min")
    if first_start not in m5.index:
        return None
    first_bar = m5.loc[first_start]
    if isinstance(first_bar, pd.DataFrame):
        first_bar = first_bar.iloc[0]
    first_completion = pd.Timestamp(first_bar.completion)
    if first_completion >= baseline_close:
        return None

    first_mfe = max_exec(m1, entry, first_completion, entry_price, side)
    if pd.isna(first_mfe) or first_mfe > 1.0e-9:
        return None
    first_close = executable_price(first_bar, side, "close")
    if not inside(first_close, level, side, 0.02):
        return None

    reclaim: pd.Timestamp | None = None
    reclaim_window = m1[
        ((m1.index + pd.Timedelta(minutes=1)) > first_completion)
        & ((m1.index + pd.Timedelta(minutes=1)) < baseline_close)
    ]
    for t, bar in reclaim_window.iterrows():
        completion = pd.Timestamp(t) + pd.Timedelta(minutes=1)
        if outside(executable_price(bar, side, "close"), level, side):
            reclaim = completion
            break
    if reclaim is None:
        return None

    if allow_same_time_m5:
        later = m5[(m5.completion >= reclaim) & (m5.completion < baseline_close)]
    else:
        later = m5[(m5.completion > reclaim) & (m5.completion < baseline_close)]
    if later.empty:
        return None
    failure_bar = later.iloc[0]
    failure = pd.Timestamp(failure_bar.completion)
    failure_close = executable_price(failure_bar, side, "close")
    if not inside(failure_close, level, side):
        return None

    mfe = max_exec(m1, entry, failure, entry_price, side)
    mae = min_exec(m1, entry, failure, entry_price, side)
    if pd.isna(mfe) or mfe > 1.0e-9:
        return None
    exit_pair = next_exit(m1, failure, baseline_close)
    if exit_pair is None:
        return None
    exit_time, exit_bar = exit_pair
    exit_price = executable_price(exit_bar, side, "open")
    baseline = float(tr.baseline_pips)
    candidate = pnl(exit_price, entry_price, side)
    reclaim_minutes = int((reclaim - entry).total_seconds() // 60)
    max_outside = _consecutive_outside(m1, reclaim, failure, side, level)

    return {
        "trade_id": trade_key(tr),
        "fold": str(tr.fold),
        "strategy": "F05",
        "side": side,
        "signal_utc": pd.Timestamp(tr.signal_utc),
        "entry_utc": entry,
        "baseline_exit_utc": baseline_close,
        "trigger_utc": failure,
        "candidate_exit_utc": pd.Timestamp(exit_time),
        "reclaim_utc": reclaim,
        "first_m5_completion_utc": first_completion,
        "breakout_level": level,
        "entry_price": entry_price,
        "baseline_pips": r1(baseline),
        "candidate_pips": r1(candidate),
        "delta_pips": r1(candidate - baseline),
        "mfe_through_trigger_pips": r1(mfe),
        "mae_through_trigger_pips": r1(mae),
        "reclaim_minutes": reclaim_minutes,
        "max_consecutive_outside_m1_closes": max_outside,
        "weak_quick_eligible": bool(reclaim_minutes <= 60 and max_outside <= 2),
        "same_time_m5_allowed": bool(allow_same_time_m5),
        "source_layer": "M1_M5_DERIVED",
    }


def derive_event_ledger(
    trades: pd.DataFrame,
    m1_2023: pd.DataFrame,
    m1_2024: pd.DataFrame,
    m5_2023: pd.DataFrame,
    m5_2024: pd.DataFrame,
    *,
    allow_same_time_m5: bool,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for tr in trades.itertuples(index=False):
        if str(tr.strategy) != "F05":
            continue
        year = pd.Timestamp(tr.entry_utc).year
        row = failed_reclaim_event(
            tr,
            m1_2023 if year == 2023 else m1_2024,
            m5_2023 if year == 2023 else m5_2024,
            allow_same_time_m5=allow_same_time_m5,
        )
        if row is not None:
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["entry_utc", "side", "trade_id"], kind="mergesort"
    ).reset_index(drop=True)


def summarize_reproduction(ledger: pd.DataFrame) -> dict[str, object]:
    if ledger.empty:
        return {
            "stopped_trades": 0,
            "total_delta_pips": 0.0,
            "long_delta_pips": 0.0,
            "short_delta_pips": 0.0,
            "fold_delta_pips": {},
        }
    fold = ledger.groupby("fold").delta_pips.sum().sort_index()
    direction = ledger.groupby("side").delta_pips.sum()
    return {
        "stopped_trades": int(len(ledger)),
        "total_delta_pips": r1(ledger.delta_pips.sum()),
        "long_delta_pips": r1(direction.get(1, 0.0)),
        "short_delta_pips": r1(direction.get(-1, 0.0)),
        "fold_delta_pips": {str(k): r1(v) for k, v in fold.items()},
    }


def weak_quick_subset(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return ledger.copy()
    return ledger[ledger.weak_quick_eligible.astype(bool)].copy().reset_index(drop=True)


def stringify_times(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column in result.columns:
            result[column] = pd.to_datetime(result[column], utc=True).dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
    return result
