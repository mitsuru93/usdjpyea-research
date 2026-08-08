#!/usr/bin/env python3
from __future__ import annotations
from .base import *

def adapt_historical_baseline(
    trades_path: Path,
    research_sha: str,
    period_core_sha: dict[str, str | None],
    period_run_id: dict[str, int],
    period_artifact_digest: dict[str, str],
) -> pd.DataFrame:
    src = pd.read_csv(trades_path)
    for c in ["signal_utc", "entry_utc", "close_utc"]:
        src[c] = parse_utc(src[c])
    rows: list[dict[str, Any]] = []
    for i, r in enumerate(src.itertuples(index=False), start=1):
        side = int(r.side)
        entry_bid = float(r.entry_bid)
        # Fixed five-point MT4 execution contract: long opens at Ask, short opens at Bid.
        entry_ask = entry_bid + DEFAULT_SPREAD_POINTS * POINT
        entry_price = entry_ask if side > 0 else entry_bid
        # Historical source ledger stores exit time and realized P/L, but not exit quote.
        # It is deliberately left null rather than reconstructed from P/L.
        period = str(r.fold)
        sid = f"{period}|{r.strategy}|{pd.Timestamp(r.entry_utc)}|{side}"
        rows.append(commonize_row({
            "study_id": "B02_F05_BASELINE",
            "hypothesis_id": None,
            "candidate_id": "UNCHANGED_B02_F05_BASELINE",
            "candidate_version": "CANONICAL_V2",
            "strategy_id": str(r.strategy),
            "source": "Rakuten MT4 historical authority / deterministic 2023 lineage",
            "broker": "Rakuten Securities",
            "symbol": SYMBOL,
            "lot": DEFAULT_LOT,
            "side": "LONG" if side > 0 else "SHORT",
            "signal_utc": r.signal_utc,
            "decision_utc": None,
            "entry_utc": r.entry_utc,
            "entry_bid": entry_bid,
            "entry_ask": entry_ask,
            "entry_price": entry_price,
            "exit_utc": r.close_utc,
            "exit_bid": None,
            "exit_ask": None,
            "exit_price": None,
            "realized_pl_jpy": float(r.realized_pl_jpy),
            "spread_points": DEFAULT_SPREAD_POINTS,
            "commission": None,
            "swap": None,
            "exit_reason": "FIXED_TIME_CAP_48_BARS" if str(r.strategy) == "B02" else "FIXED_TIME_CAP_32_BARS",
            "position_id": sid,
            "source_trade_id": sid,
            "candidate_visibility": "BASELINE_AUTHORITY",
            "validation_run_id": str(period_run_id[period]),
            "research_sha": research_sha,
            "core_sha": period_core_sha.get(period),
            "artifact_digest": period_artifact_digest[period],
        }))
    out = pd.DataFrame(rows, columns=COMMON_TRADE_FIELDS)
    return out


def adapt_mt4_event_log(
    event_path: Path,
    run_id: int,
    core_sha: str,
    artifact_digest: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(event_path)
    raw["utc"] = parse_utc(raw.utc_time, mt4=True)
    opens = raw[raw.event.eq("order_opened")].copy()
    closes = raw[raw.event.eq("order_closed")].copy()
    merged = opens.merge(
        closes[["ticket", "utc", "price", "gross_pips", "detail"]],
        on="ticket", how="left", suffixes=("_open", "_close"), validate="one_to_one",
    )
    rows: list[dict[str, Any]] = []
    for r in merged.itertuples(index=False):
        side = int(r.side)
        ep = float(r.price_open)
        xp = float(r.price_close)
        if side > 0:
            ebid, eask, xbid, xask = ep - DEFAULT_SPREAD_POINTS * POINT, ep, xp, xp + DEFAULT_SPREAD_POINTS * POINT
        else:
            ebid, eask, xbid, xask = ep, ep + DEFAULT_SPREAD_POINTS * POINT, xp - DEFAULT_SPREAD_POINTS * POINT, xp
        source_id = f"MT4:{int(r.ticket)}"
        rows.append(commonize_row({
            "study_id": "B02_F05_BASELINE",
            "hypothesis_id": None,
            "candidate_id": "UNCHANGED_B02_F05_BASELINE",
            "candidate_version": "MT4_2025H1_V1",
            "strategy_id": str(r.strategy),
            "source": "pre-existing Rakuten MT4 cached HST",
            "broker": "Rakuten Securities",
            "symbol": SYMBOL,
            "lot": float(r.lots),
            "side": "LONG" if side > 0 else "SHORT",
            "signal_utc": pd.to_datetime(r.signal_utc, format="%Y.%m.%d %H:%M:%S", utc=True),
            "decision_utc": None,
            "entry_utc": pd.to_datetime(r.entry_utc, format="%Y.%m.%d %H:%M:%S", utc=True),
            "entry_bid": round(ebid, 3),
            "entry_ask": round(eask, 3),
            "entry_price": ep,
            "exit_utc": r.utc_close,
            "exit_bid": round(xbid, 3),
            "exit_ask": round(xask, 3),
            "exit_price": xp,
            "realized_pl_jpy": float(r.gross_pips_close) * JPY_PER_PIP_001_LOT,
            "spread_points": DEFAULT_SPREAD_POINTS,
            "commission": None,
            "swap": None,
            "exit_reason": str(r.detail_close),
            "position_id": source_id,
            "source_trade_id": source_id,
            "candidate_visibility": "VALIDATION_PERIOD_BASELINE_AUTHORITY",
            "validation_run_id": str(run_id),
            "research_sha": None,
            "core_sha": core_sha,
            "artifact_digest": artifact_digest,
        }))
    ledger = pd.DataFrame(rows, columns=COMMON_TRADE_FIELDS)
    snapshots = raw[raw.event.eq("portfolio_snapshot")].copy()
    snapshots = snapshots.rename(columns={"utc": "timestamp_utc"})
    return ledger, snapshots


def validate_common_ledger(ledger: pd.DataFrame) -> dict[str, Any]:
    missing_columns = [c for c in COMMON_TRADE_FIELDS if c not in ledger.columns]
    duplicated = int(ledger.source_trade_id.dropna().duplicated().sum()) if "source_trade_id" in ledger else None
    invalid_side = int((~ledger.side.isin(["LONG", "SHORT"])).sum()) if "side" in ledger else None
    chronology_negative = None
    if "entry_utc" in ledger and "exit_utc" in ledger:
        chronology_negative = int((pd.to_datetime(ledger.exit_utc, utc=True) < pd.to_datetime(ledger.entry_utc, utc=True)).sum())
    critical_nulls = {
        c: int(ledger[c].isna().sum())
        for c in ["decision_utc", "commission", "swap", "research_sha", "core_sha", "artifact_digest"]
        if c in ledger
    }
    return {
        "missing_columns": missing_columns,
        "duplicate_source_trade_ids": duplicated,
        "invalid_side_rows": invalid_side,
        "negative_holding_period_rows": chronology_negative,
        "critical_null_counts": critical_nulls,
        "chronology_mismatch": 0 if chronology_negative == 0 else chronology_negative,
        "decision_chronology_gate": "STOP_NULL_DECISION_UTC" if critical_nulls.get("decision_utc", 0) else "PASS",
        "commission_swap_gate": "STOP_NULL_COST_COMPONENTS" if critical_nulls.get("commission", 0) or critical_nulls.get("swap", 0) else "PASS",
    }
