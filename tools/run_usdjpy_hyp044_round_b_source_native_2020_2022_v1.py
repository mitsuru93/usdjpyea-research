#!/usr/bin/env python3
from __future__ import annotations

import argparse
import heapq
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

import run_usdjpy_hyp044_source_native_2020_2022_v1 as base

CANDIDATE_ID = "B0_A2_EARLY_C3_PLUS_A4_SESSION_LOSS_CAP_2"
RULE_HASH = "d8878f92e0641b10c4926966a03a46f238e4074335312003b7a6c058f8843f94"


def cap_session(ts: pd.Timestamp) -> str:
    if ts.hour < 7:
        return "ASIA"
    if ts.hour < 13:
        return "LONDON"
    if ts.hour < 16:
        return "LONDON_NY_OVERLAP"
    return "NEW_YORK"


def cap_session_key(ts: pd.Timestamp) -> str:
    return f"{ts.date().isoformat()}|{cap_session(ts)}"


def apply_b02_a2(baseline: list[dict[str, Any]], c3: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source = {row["trade_id"]: row for row in baseline}
    out: list[dict[str, Any]] = []
    for row in c3:
        boundary = int(row["exit_bar_index"] - row["entry_bar_index"])
        if row.get("modified") and boundary <= 16:
            candidate = dict(row)
            candidate["c3_boundary"] = boundary
            candidate["reason"] = "A2_C3_EARLY_GIVEBACK_16BAR"
            out.append(candidate)
        else:
            candidate = dict(source[row["trade_id"]])
            candidate["c3_boundary"] = boundary if row.get("modified") else None
            candidate["reason"] = "A2_RETAIN_ORIGINAL_48BAR_EXIT"
            out.append(candidate)
    return out


def apply_session_cap(rows: list[dict[str, Any]], cap: int = 2) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: (row["entry_utc"], row["strategy"], row["trade_id"]))
    matured: list[tuple[int, str, dict[str, Any]]] = []
    current_key: str | None = None
    loss_count = 0
    accepted: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for row in ordered:
        entry_ns = int(row["entry_utc"].value)
        while matured and matured[0][0] <= entry_ns:
            _, _, closed = heapq.heappop(matured)
            close_key = cap_session_key(closed["close_utc"])
            if close_key != current_key:
                current_key = close_key
                loss_count = 0
            if float(closed["pnl_jpy"]) < 0:
                loss_count += 1
            elif float(closed["pnl_jpy"]) > 0:
                loss_count = 0
        entry_key = cap_session_key(row["entry_utc"])
        if entry_key != current_key:
            current_key = entry_key
            loss_count = 0
        blocked = loss_count >= cap
        decisions.append({
            "trade_id": row["trade_id"],
            "strategy": row["strategy"],
            "entry_utc": row["entry_utc"],
            "session_key": entry_key,
            "prior_session_loss_count": loss_count,
            "decision": "BLOCK" if blocked else "ACCEPT",
            "source_pnl_jpy": row["pnl_jpy"],
        })
        if not blocked:
            accepted.append(row)
            heapq.heappush(matured, (int(row["close_utc"].value), row["trade_id"], row))
    return accepted, decisions


def stability(monthly: pd.DataFrame) -> dict[str, Any]:
    x = monthly.sort_values("period").copy()
    values = x["net_jpy"].astype(float)
    periods = x["period"].astype(str).tolist()
    result: dict[str, Any] = {
        "positive_months": int((values > 0).sum()),
        "total_months": int(len(values)),
        "worst_month": {"period": periods[int(values.argmin())], "net_jpy": float(values.min())} if len(values) else None,
    }
    for window in (3, 6, 12):
        roll = values.rolling(window, min_periods=window).sum()
        if roll.notna().any():
            idx = int(roll.idxmin())
            result[f"rolling_{window}_month_minimum"] = {"end_period": str(x.loc[idx, "period"]), "net_jpy": float(roll.loc[idx])}
        else:
            result[f"rolling_{window}_month_minimum"] = None
    return result


def serialize_frame(frame: pd.DataFrame, path: Path) -> None:
    out = frame.copy()
    for column in out.columns:
        if len(out) and isinstance(out[column].iloc[0], pd.Timestamp):
            out[column] = out[column].map(lambda value: value.isoformat() if pd.notna(value) else "")
    out.to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--c2-summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    bars = base.add_features(base.load_bars(args.data_root))
    b02, f05 = base.generate_b02_f05(bars)
    b02_c3 = base.apply_b02_c3(b02, bars)
    b02_a2 = apply_b02_a2(b02, b02_c3)
    c2_summary = json.loads(args.c2_summary.read_text(encoding="utf-8"))
    thresholds = c2_summary["f05_c2"]["thresholds"]
    f05_c2 = base.assign_c2_tick_outcomes(f05, thresholds, args.data_root)
    sp39 = base.generate_sp(bars)

    p0 = [*b02, *f05]
    p4 = [*b02_c3, *f05_c2, *sp39]
    a2 = [*b02_a2, *f05_c2, *sp39]
    a4_parent, a4_decisions = apply_session_cap([*b02_c3, *f05_c2], 2)
    a4 = [*a4_parent, *sp39]
    b0_parent, b0_decisions = apply_session_cap([*b02_a2, *f05_c2], 2)
    b0 = [*b0_parent, *sp39]

    portfolios = {
        "P0_B02_BASELINE_F05_BASELINE": p0,
        "P4_B02_C3_F05_C2_SP39": p4,
        "A2_B02_EARLY_C3_F05_C2_SP39": a2,
        "A4_B02_C3_F05_C2_CAP2_SP39": a4,
        CANDIDATE_ID: b0,
    }
    period_tables = base.period_tables(portfolios)
    for name, frame in period_tables.items():
        frame.to_csv(args.out / f"{name}_metrics_round_b_2020_2022.csv", index=False)

    event_frame = pd.DataFrame(b0)
    serialize_frame(event_frame, args.out / "round_b_event_ledger_2020_2022.csv")
    decision_frame = pd.DataFrame(b0_decisions)
    serialize_frame(decision_frame, args.out / "round_b_decision_ledger_2020_2022.csv")

    portfolio_metrics = {key: base.trade_metrics(value) for key, value in portfolios.items()}
    full_equity_metrics = base.full_equity(portfolios, args.data_root)
    annual = period_tables["annual"]
    halfyear = period_tables["halfyear"]
    quarter = period_tables["quarterly"]
    monthly = period_tables["monthly"]
    candidate_annual = annual[annual.portfolio_id == CANDIDATE_ID].reset_index(drop=True)
    candidate_halfyear = halfyear[halfyear.portfolio_id == CANDIDATE_ID].reset_index(drop=True)
    candidate_quarter = quarter[quarter.portfolio_id == CANDIDATE_ID].reset_index(drop=True)
    candidate_monthly = monthly[monthly.portfolio_id == CANDIDATE_ID].reset_index(drop=True)

    strategy_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    side_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in b0:
        strategy_groups[row["strategy"]].append(row)
        side_groups["LONG" if row["side"] == 1 else "SHORT"].append(row)

    result = {
        "schema_version": "usdjpy_hyp044_round_b_source_native_2020_2022_v1",
        "hypothesis_id": "USDJPY-HYP-044",
        "candidate_id": CANDIDATE_ID,
        "rule_hash_sha256": RULE_HASH,
        "status": "PASS_ROUND_B_SOURCE_NATIVE_2020_2022_ANALYSIS",
        "authority": "USDJPY-DATA-2020-2022-TICK-AUTHORITY-001",
        "period_role": "ANALYSIS_PERIOD",
        "portfolio_metrics": portfolio_metrics,
        "candidate_metrics": portfolio_metrics[CANDIDATE_ID],
        "candidate_full_equity": full_equity_metrics[CANDIDATE_ID],
        "full_equity_metrics": full_equity_metrics,
        "annual": candidate_annual.to_dict(orient="records"),
        "halfyear": candidate_halfyear.to_dict(orient="records"),
        "quarterly": candidate_quarter.to_dict(orient="records"),
        "stability": {
            "positive_years": int((candidate_annual.net_jpy > 0).sum()),
            "total_years": int(len(candidate_annual)),
            "positive_halfyears": int((candidate_halfyear.net_jpy > 0).sum()),
            "total_halfyears": int(len(candidate_halfyear)),
            "positive_quarters": int((candidate_quarter.net_jpy > 0).sum()),
            "total_quarters": int(len(candidate_quarter)),
            "worst_year": candidate_annual.loc[candidate_annual.net_jpy.idxmin()].to_dict(),
            "worst_halfyear": candidate_halfyear.loc[candidate_halfyear.net_jpy.idxmin()].to_dict(),
            "worst_quarter": candidate_quarter.loc[candidate_quarter.net_jpy.idxmin()].to_dict(),
            **stability(candidate_monthly),
        },
        "strategy_attribution": {key: base.trade_metrics(value) for key, value in strategy_groups.items()},
        "side_attribution": {key: base.trade_metrics(value) for key, value in side_groups.items()},
        "session_control": {
            "blocked_trade_count": sum(row["decision"] == "BLOCK" for row in b0_decisions),
            "blocked_B02": sum(row["decision"] == "BLOCK" and row["strategy"] == "B02" for row in b0_decisions),
            "blocked_F05": sum(row["decision"] == "BLOCK" and row["strategy"] == "F05" for row in b0_decisions),
            "blocked_source_net_jpy": sum(float(row["source_pnl_jpy"]) for row in b0_decisions if row["decision"] == "BLOCK"),
        },
        "reference_A4_decision_count": len(a4_decisions),
        "tick_count": full_equity_metrics[CANDIDATE_ID]["tick_count"],
        "2025H2_accessed": False,
        "production_authorized": False,
        "live_authorized": False,
    }
    base.write_json(args.out / "round_b_source_native_result_2020_2022.json", result)
    with (args.out / "sha256sums.txt").open("w", encoding="utf-8") as stream:
        for path in sorted(args.out.iterdir()):
            if path.is_file() and path.name != "sha256sums.txt":
                stream.write(f"{base.sha256(path)}  {path.name}\n")
    print(json.dumps(base.clean(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
