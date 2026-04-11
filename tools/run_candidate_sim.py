#!/usr/bin/env python3
"""Run simulator v1 candidate pipeline on OHLC CSV input."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from research.io.csv_loader import load_ohlc_csv
from research.scoring.summary import summarize_outcomes
from research.simulator.candidate_engine import ASSUMPTION_VERSION, build_candidates
from research.simulator.envelope import DEVIATION_RATE, EMA_SPAN, add_envelope_columns
from research.simulator.outcome_engine import DEFAULT_MAX_HOLDING_BARS, evaluate_candidates
from research.simulator.session import add_session_columns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pre-MT4 simulator v1 candidate engine.")
    parser.add_argument("--input-csv", required=True, help="Path to OHLC CSV input.")
    parser.add_argument("--output-dir", required=True, help="Directory for output CSV/YAML files.")
    parser.add_argument(
        "--max-holding-bars",
        type=int,
        default=DEFAULT_MAX_HOLDING_BARS,
        help=f"Maximum holding bars for outcome evaluation (default: {DEFAULT_MAX_HOLDING_BARS}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ohlc_df = load_ohlc_csv(args.input_csv)
    tagged_df = add_session_columns(ohlc_df)
    env_df = add_envelope_columns(tagged_df)
    candidates_df = build_candidates(env_df)
    outcomes_df = evaluate_candidates(env_df, candidates_df, max_holding_bars=args.max_holding_bars)
    summaries = summarize_outcomes(outcomes_df)

    candidates_df.to_csv(output_dir / "candidates.csv", index=False)
    summaries["overall"].to_csv(output_dir / "summary_overall.csv", index=False)
    summaries["by_month"].to_csv(output_dir / "summary_by_month.csv", index=False)
    summaries["by_session"].to_csv(output_dir / "summary_by_session.csv", index=False)
    summaries["by_family"].to_csv(output_dir / "summary_by_family.csv", index=False)

    metadata = {
        "simulator_version": "v1",
        "assumption_version": ASSUMPTION_VERSION,
        "input_csv": str(Path(args.input_csv).resolve()),
        "symbol_timeframe_baseline": "USDJPY_M1",
        "envelope": {
            "ema_span": EMA_SPAN,
            "deviation_rate": DEVIATION_RATE,
        },
        "tp_sl_defaults": {
            "rev": {"tp_pips": 10, "sl_pips": 30},
            "trend": {"tp_pips": 10, "sl_pips": 20},
        },
        "same_bar_ambiguity_rule": "SL-first conservative",
        "entry_evaluation_rule": "Evaluate from next bar after signal bar",
        "max_holding_bars": args.max_holding_bars,
        "notes": [
            "Candidate labeling engine only (not full MT4 backtester)",
            "No trend-environment gating implemented in v1",
            "No full position-lock/live execution semantics in v1",
        ],
    }
    with (output_dir / "run_metadata.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False)

    print(
        "Simulator v1 completed:",
        f"cand={len(candidates_df)}",
        f"wins={(outcomes_df['outcome_status'] == 'win').sum() if not outcomes_df.empty else 0}",
        f"losses={(outcomes_df['outcome_status'] == 'loss').sum() if not outcomes_df.empty else 0}",
        f"timeouts={(outcomes_df['outcome_status'] == 'timeout').sum() if not outcomes_df.empty else 0}",
        f"out={output_dir}",
    )


if __name__ == "__main__":
    main()
