"""Frozen online event definitions and deterministic summaries for structural SL v1."""
from __future__ import annotations

import pandas as pd

from .common import EVENT_IDS, FOLDS, PIP, executable_price, inside, max_exec, min_exec, next_exit, outside, pnl, r1

def event_row(tr: object, event_id: str, trigger: pd.Timestamp, exit_time: pd.Timestamp,
              exit_price: float, mfe: float, mae: float, extra: dict[str, object] | None = None) -> dict[str, object]:
    side = int(tr.side)
    candidate = pnl(exit_price, float(tr.entry_price), side)
    baseline = float(tr.baseline_pips)
    row: dict[str, object] = {
        "event_id": event_id,
        "trade_id": f"{tr.fold}|{tr.strategy}|{pd.Timestamp(tr.entry_utc)}|{side}",
        "fold": tr.fold,
        "strategy": tr.strategy,
        "side": side,
        "signal_utc": tr.signal_utc,
        "entry_utc": tr.entry_utc,
        "baseline_exit_utc": tr.close_utc,
        "trigger_utc": trigger,
        "candidate_exit_utc": exit_time,
        "breakout_level": float(tr.breakout_level),
        "baseline_pips": r1(baseline),
        "candidate_pips": r1(candidate),
        "delta_pips": r1(candidate - baseline),
        "mfe_through_trigger_pips": r1(mfe),
        "mae_through_trigger_pips": r1(mae),
        "trigger_minutes": int((trigger - tr.entry_utc).total_seconds() / 60),
        "baseline_winner": bool(baseline > 0),
        "baseline_loser": bool(baseline <= 0),
    }
    if extra:
        row.update(extra)
    return row


def first_reentry(tr: object, m1: pd.DataFrame, bars: pd.DataFrame, minutes: int,
                  event_id: str, strategy_only: str | None = None) -> dict[str, object] | None:
    if strategy_only and tr.strategy != strategy_only:
        return None
    side, entry, close = int(tr.side), tr.entry_utc, tr.close_utc
    level, entry_price = float(tr.breakout_level), float(tr.entry_price)
    start = entry.floor(f"{minutes}min")
    if start not in bars.index:
        return None
    b = bars.loc[start]
    completion = start + pd.Timedelta(minutes=minutes)
    mfe = max_exec(m1, entry, completion, entry_price, side)
    mae = min_exec(m1, entry, completion, entry_price, side)
    if mfe > 1e-9 or not inside(executable_price(b, side, "close"), level, side, 0.02 if minutes == 5 else 0.0):
        return None
    ex = next_exit(m1, completion, close)
    if not ex:
        return None
    exit_time, exit_bar = ex
    return event_row(tr, event_id, completion, exit_time, executable_price(exit_bar, side, "open"), mfe, mae)


def no_reclaim_120(tr: object, m1: pd.DataFrame, bars: pd.DataFrame, minutes: int,
                   event_id: str, strategy_only: str | None = None) -> dict[str, object] | None:
    initial = first_reentry(tr, m1, bars, minutes, "_temporary", strategy_only)
    if not initial:
        return None
    side, close = int(tr.side), tr.close_utc
    level, entry_price = float(tr.breakout_level), float(tr.entry_price)
    completion = initial["trigger_utc"]
    deadline = completion + pd.Timedelta(minutes=120)
    if deadline >= close:
        return None
    w = m1[((m1.index + pd.Timedelta(minutes=1)) > completion) & ((m1.index + pd.Timedelta(minutes=1)) <= deadline)]
    if any(outside(executable_price(b, side, "close"), level, side) for _, b in w.iterrows()):
        return None
    mfe = max_exec(m1, tr.entry_utc, deadline, entry_price, side)
    mae = min_exec(m1, tr.entry_utc, deadline, entry_price, side)
    if mfe > 1e-9:
        return None
    ex = next_exit(m1, deadline, close)
    if not ex:
        return None
    exit_time, exit_bar = ex
    return event_row(tr, event_id, deadline, exit_time, executable_price(exit_bar, side, "open"), mfe, mae)


def failed_reclaim(tr: object, m1: pd.DataFrame, bars: pd.DataFrame, minutes: int,
                   event_id: str, strategy_only: str | None = None) -> dict[str, object] | None:
    initial = first_reentry(tr, m1, bars, minutes, "_temporary", strategy_only)
    if not initial:
        return None
    side, close = int(tr.side), tr.close_utc
    level, entry_price = float(tr.breakout_level), float(tr.entry_price)
    first_completion = initial["trigger_utc"]
    reclaim = None
    for t, b in m1[((m1.index + pd.Timedelta(minutes=1)) > first_completion) & ((m1.index + pd.Timedelta(minutes=1)) < close)].iterrows():
        completion = t + pd.Timedelta(minutes=1)
        if outside(executable_price(b, side, "close"), level, side):
            reclaim = completion
            break
    if reclaim is None:
        return None
    q = bars[(bars.completion > reclaim) & (bars.completion < close)]
    if q.empty:
        return None
    failure_bar = q.iloc[0]
    failure = failure_bar.completion
    if not inside(executable_price(failure_bar, side, "close"), level, side):
        return None
    mfe = max_exec(m1, tr.entry_utc, failure, entry_price, side)
    mae = min_exec(m1, tr.entry_utc, failure, entry_price, side)
    if mfe > 1e-9:
        return None
    ex = next_exit(m1, failure, close)
    if not ex:
        return None
    exit_time, exit_bar = ex
    return event_row(
        tr, event_id, failure, exit_time, executable_price(exit_bar, side, "open"), mfe, mae,
        {"reclaim_utc": reclaim},
    )


def profit_armed_range_failure(tr: object, m1: pd.DataFrame, m5: pd.DataFrame) -> dict[str, object] | None:
    side, entry, close = int(tr.side), tr.entry_utc, tr.close_utc
    level, entry_price = float(tr.breakout_level), float(tr.entry_price)
    arm = None
    for t, b in m1[(m1.index >= entry) & ((m1.index + pd.Timedelta(minutes=1)) < close)].iterrows():
        favorable = (float(b.bid_high) - entry_price) / PIP if side == 1 else (entry_price - float(b.ask_low)) / PIP
        if favorable > 1e-9:
            arm = t + pd.Timedelta(minutes=1)
            break
    if arm is None:
        return None
    for _, b in m5[(m5.completion > arm) & (m5.completion < close)].iterrows():
        trigger = b.completion
        close_price = executable_price(b, side, "close")
        if pnl(close_price, entry_price, side) <= 1e-9 and inside(close_price, level, side):
            mfe = max_exec(m1, entry, trigger, entry_price, side)
            mae = min_exec(m1, entry, trigger, entry_price, side)
            ex = next_exit(m1, trigger, close)
            if not ex:
                return None
            exit_time, exit_bar = ex
            return event_row(
                tr, "PROFIT_ARMED_M5_RANGE_FAILURE_V1", trigger, exit_time,
                executable_price(exit_bar, side, "open"), mfe, mae, {"profit_arm_utc": arm},
            )
    return None


def group_summary(g: pd.DataFrame, total_losers: int) -> dict[str, object]:
    losers = g[g.baseline_loser]
    winners = g[g.baseline_winner]
    folds = g.groupby("fold").delta_pips.sum().reindex(FOLDS, fill_value=0.0)
    direction = g.groupby("side").delta_pips.sum().reindex([1, -1], fill_value=0.0)
    cells = g.groupby(["fold", "strategy", "side"]).delta_pips.sum()
    dates = g.assign(date=pd.to_datetime(g.entry_utc, utc=True).dt.strftime("%Y-%m-%d")).groupby("date").delta_pips.sum().sort_values(ascending=False)
    total = float(g.delta_pips.sum())
    return {
        "triggers": int(len(g)),
        "losers_triggered": int(len(losers)),
        "winners_triggered": int(len(winners)),
        "loser_coverage": round(len(losers) / max(total_losers, 1), 6),
        "loser_benefit_pips": r1(losers.delta_pips.sum()),
        "winner_damage_pips": r1(winners.delta_pips.sum()),
        "total_delta_pips": r1(total),
        "median_trigger_minutes": float(g.trigger_minutes.median()),
        "fold_delta_pips": {f: r1(folds[f]) for f in FOLDS},
        "direction_delta_pips": {"long": r1(direction[1]), "short": r1(direction[-1])},
        "negative_fold_strategy_direction_cells": int((cells < 0).sum()),
        "observed_fold_strategy_direction_cells": int(len(cells)),
        "best_date_delta_pips": r1(dates.iloc[0]) if len(dates) else 0.0,
        "delta_after_best_date_removed_pips": r1(total - dates.iloc[0]) if len(dates) else 0.0,
    }


def summarize(ledger: pd.DataFrame, trades: pd.DataFrame) -> dict[str, object]:
    total_losers = int((trades.baseline_pips <= 0).sum())
    result: dict[str, object] = {}
    for event_id in EVENT_IDS:
        g = ledger[ledger.event_id == event_id]
        if g.empty:
            result[event_id] = {"overall": group_summary(g, total_losers), "by_strategy": {}}
            continue
        by_strategy = {
            strategy: group_summary(sg, int(((trades.strategy == strategy) & (trades.baseline_pips <= 0)).sum()))
            for strategy, sg in g.groupby("strategy")
        }
        result[event_id] = {"overall": group_summary(g, total_losers), "by_strategy": by_strategy}
    return result


def decide(summary: dict[str, object]) -> dict[str, object]:
    focal = summary["SHARED_FAILED_RECLAIM_STRICT_NO_PROFIT_V1"]["by_strategy"].get("F05", {})
    b02_candidates = [
        summary["B02_FIRST_M15_REENTRY_NO_PROFIT_V1"]["overall"],
        summary["B02_M15_FAILED_RECLAIM_NO_PROFIT_V1"]["overall"],
        summary["B02_M15_NO_RECLAIM_120_NO_PROFIT_V1"]["overall"],
    ]
    focal_fold_nonnegative = bool(focal) and all(v >= 0 for v in focal["fold_delta_pips"].values())
    focal_direction_nonnegative = bool(focal) and all(v >= 0 for v in focal["direction_delta_pips"].values())
    focal_cell_nonnegative = bool(focal) and focal["negative_fold_strategy_direction_cells"] == 0
    focal_promising = bool(focal) and focal["total_delta_pips"] > 0 and focal_fold_nonnegative
    b02_robust = any(
        x["total_delta_pips"] > 0
        and all(v >= 0 for v in x["fold_delta_pips"].values())
        and all(v >= 0 for v in x["direction_delta_pips"].values())
        and x["negative_fold_strategy_direction_cells"] == 0
        for x in b02_candidates
    )
    return {
        "overall_status": "DESCRIPTIVE_COMPLETE_NO_CANDIDATE_FROZEN",
        "f05_failed_reclaim": {
            "status": "PROMISING_EXPLORATORY_MECHANISM_NOT_CONFIRMATORY" if focal_promising else "REJECTED",
            "fold_nonnegative": focal_fold_nonnegative,
            "direction_total_nonnegative": focal_direction_nonnegative,
            "fold_direction_cell_nonnegative": focal_cell_nonnegative,
            "candidate_frozen": False,
            "reason": "F05 total and fold breadth may be positive, but any negative fold-direction cell or concentration prevents confirmatory promotion.",
        },
        "b02": {
            "status": "NO_ROBUST_STRUCTURAL_STOP_FOUND" if not b02_robust else "PROMISING_EXPLORATORY_MECHANISM_NOT_CONFIRMATORY",
            "candidate_frozen": False,
        },
        "shared_b02_f05_rule": {
            "status": "REJECT_SHARED_STOP_ARCHITECTURE",
            "reason": "A mechanism must not be promoted as shared when strategy-level effects diverge.",
        },
        "profit_armed_generic_termination": {
            "status": "REJECTED_AS_OVERBROAD",
            "candidate_frozen": False,
        },
        "implementation_authorized": False,
        "mt4_authorized": False,
        "2025_authorized": False,
    }
