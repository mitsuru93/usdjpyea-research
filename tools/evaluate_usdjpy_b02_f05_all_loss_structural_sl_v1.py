#!/usr/bin/env python3
"""Run the frozen B02/F05 all-loss structural-SL descriptive evaluation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from usdjpy_structural_sl_v1.common import (
    EVENT_IDS, EXPECTED_COUNTS, EXPECTED_SHA, aggregate_bars, historical_2023_trades,
    load_2023_m15, load_m1, parse_event_trades, sha256_file, write_json,
)
from usdjpy_structural_sl_v1.events import (
    decide, failed_reclaim, first_reentry, no_reclaim_120, profit_armed_range_failure, summarize,
)

def verify_protocol(path: Path) -> dict[str, object]:
    p = json.loads(path.read_text())
    assert p["schema_version"] == "usdjpy_b02_f05_all_loss_structural_sl_protocol_v1"
    assert p["status"] == "FROZEN_BEFORE_OUTCOME_EXECUTION"
    assert p["population"]["trade_count"] == 1882
    assert p["event_family"]["event_ids"] == EVENT_IDS
    assert p["boundaries"]["fixed_pip_stop_evaluated"] is False
    assert p["boundaries"]["mt4_accessed"] is False
    assert p["boundaries"]["2025_accessed"] is False
    assert p["authorization"]["notion_task_dependency"] is False
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--m15-2023", type=Path)
    ap.add_argument("--m1-2023", type=Path)
    ap.add_argument("--events-2024h1", type=Path)
    ap.add_argument("--events-2024h2", type=Path)
    ap.add_argument("--m1-2024", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--research-commit", default="")
    ap.add_argument("--workflow-run-id", default="")
    ap.add_argument("--workflow-run-attempt", default="")
    args = ap.parse_args()

    verify_protocol(args.protocol)
    preflight = {
        "schema_version": "usdjpy_b02_f05_all_loss_structural_sl_preflight_v1",
        "status": "PASS_NO_OUTCOMES",
        "protocol_sha256": sha256_file(args.protocol),
        "evaluator_sha256": sha256_file(Path(__file__)),
        "event_ids": EVENT_IDS,
        "outcomes_computed": False,
        "mt4_accessed": False,
        "2025_accessed": False,
        "notion_task_dependency": False,
    }
    if args.preflight_only:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 0

    required = [args.m15_2023, args.m1_2023, args.events_2024h1, args.events_2024h2, args.m1_2024, args.out_dir]
    if any(x is None for x in required):
        raise SystemExit("full evaluation requires every source argument and --out-dir")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.out_dir / "preflight_result.json", preflight)

    actual_sha = {
        "m15_2023": sha256_file(args.m15_2023),
        "m1_2023": sha256_file(args.m1_2023),
        "events_2024h1": sha256_file(args.events_2024h1),
        "events_2024h2": sha256_file(args.events_2024h2),
        "m1_2024": sha256_file(args.m1_2024),
    }
    assert actual_sha == EXPECTED_SHA, (actual_sha, EXPECTED_SHA)

    trades = pd.concat([
        historical_2023_trades(load_2023_m15(args.m15_2023)),
        parse_event_trades(args.events_2024h1, "2024H1", False),
        parse_event_trades(args.events_2024h2, "2024H2", True),
    ], ignore_index=True).sort_values(["fold", "entry_utc", "strategy"], kind="mergesort").reset_index(drop=True)
    counts = {
        fold: {strategy: int(n) for strategy, n in g.groupby("strategy").size().items()}
        for fold, g in trades.groupby("fold")
    }
    assert len(trades) == 1882 and counts == EXPECTED_COUNTS, (len(trades), counts)

    m23, m24 = load_m1(args.m1_2023, args.m1_2024)
    bars = {
        "2023": {5: aggregate_bars(m23, 5), 15: aggregate_bars(m23, 15)},
        "2024": {5: aggregate_bars(m24, 5), 15: aggregate_bars(m24, 15)},
    }
    event_rows: list[dict[str, object]] = []
    for tr in trades.itertuples(index=False):
        year = "2023" if tr.fold.startswith("2023") else "2024"
        m1_all = m23 if year == "2023" else m24
        m1 = m1_all.loc[tr.entry_utc:tr.close_utc]
        m5 = bars[year][5].loc[tr.entry_utc.floor("5min"):tr.close_utc]
        m15 = bars[year][15].loc[tr.entry_utc.floor("15min"):tr.close_utc]
        candidates = [
            first_reentry(tr, m1, m5, 5, "SHARED_EARLY_M5_REENTRY_NO_PROFIT_V1"),
            no_reclaim_120(tr, m1, m5, 5, "SHARED_EARLY_REENTRY_NO_RECLAIM_120_V1"),
            failed_reclaim(tr, m1, m5, 5, "SHARED_FAILED_RECLAIM_STRICT_NO_PROFIT_V1"),
            first_reentry(tr, m1, m15, 15, "B02_FIRST_M15_REENTRY_NO_PROFIT_V1", "B02"),
            failed_reclaim(tr, m1, m15, 15, "B02_M15_FAILED_RECLAIM_NO_PROFIT_V1", "B02"),
            no_reclaim_120(tr, m1, m15, 15, "B02_M15_NO_RECLAIM_120_NO_PROFIT_V1", "B02"),
            profit_armed_range_failure(tr, m1, m5),
        ]
        event_rows.extend(x for x in candidates if x is not None)

    ledger = pd.DataFrame(event_rows).sort_values(["event_id", "fold", "entry_utc", "strategy"], kind="mergesort")
    summary = summarize(ledger, trades)
    decision = decide(summary)

    trades_out = trades.copy()
    for col in ["signal_utc", "entry_utc", "close_utc"]:
        trades_out[col] = pd.to_datetime(trades_out[col], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    ledger_out = ledger.copy()
    for col in ["signal_utc", "entry_utc", "baseline_exit_utc", "trigger_utc", "candidate_exit_utc", "reclaim_utc", "profit_arm_utc"]:
        if col in ledger_out.columns:
            ledger_out[col] = pd.to_datetime(ledger_out[col], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    trades_path = args.out_dir / "source_trade_ledger_v1.csv"
    ledger_path = args.out_dir / "event_counterfactual_ledger_v1.csv"
    trades_out.to_csv(trades_path, index=False, lineterminator="\n", float_format="%.6f")
    ledger_out.to_csv(ledger_path, index=False, lineterminator="\n", float_format="%.6f")

    result = {
        "schema_version": "usdjpy_b02_f05_all_loss_structural_sl_result_v1",
        "status": decision["overall_status"],
        "research_commit": args.research_commit,
        "workflow_run_id": int(args.workflow_run_id) if args.workflow_run_id else None,
        "workflow_run_attempt": int(args.workflow_run_attempt) if args.workflow_run_attempt else None,
        "source_sha256": actual_sha,
        "population": {
            "trade_count": int(len(trades)),
            "baseline_loser_count": int((trades.baseline_pips <= 0).sum()),
            "counts": counts,
        },
        "event_summary": summary,
        "decision": decision,
        "boundaries": {
            "fixed_pip_stop_evaluated": False,
            "portfolio_replay_computed": True,
            "mt4_accessed": False,
            "2025H1_accessed": False,
            "2025H2_accessed": False,
            "implementation_authorized": False,
            "candidate_frozen": False,
            "notion_used_as_task_source": False,
        },
    }
    result_path = args.out_dir / "result_v1.json"
    write_json(result_path, result)
    manifest = {
        "schema_version": "usdjpy_b02_f05_all_loss_structural_sl_output_manifest_v1",
        "files": {
            p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
            for p in sorted(args.out_dir.iterdir()) if p.is_file()
        },
    }
    write_json(args.out_dir / "output_manifest_v1.json", manifest)
    print(json.dumps({"status": result["status"], "trades": len(trades), "events": len(ledger)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
