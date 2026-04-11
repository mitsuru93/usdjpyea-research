#!/usr/bin/env python3
"""Config-driven experiment runner for simulator v1 + feature snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from research.features import FEATURE_SET_VERSION, attach_features_to_candidates, build_feature_frame
from research.io.csv_loader import load_ohlc_csv
from research.policy import POLICY_SEMANTICS, apply_policy_to_candidates, parse_policy_config
from research.scoring.summary import summarize_outcomes
from research.simulator.candidate_engine import ASSUMPTION_VERSION, build_candidates
from research.simulator.envelope import DEVIATION_RATE, EMA_SPAN, add_envelope_columns
from research.simulator.outcome_engine import DEFAULT_MAX_HOLDING_BARS, PIP_SIZE, evaluate_candidates
from research.simulator.session import INPUT_TIMEZONE_MODES, add_session_columns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run config-driven pre-MT4 candidate experiment.")
    parser.add_argument("--config", required=True, help="Path to YAML experiment config.")
    return parser.parse_args()


def _load_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    required = ["input_csv", "output_dir", "input_timezone_mode", "max_holding_bars", "symbol", "timeframe"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Experiment config missing required fields: {missing}")

    tz_mode = str(cfg["input_timezone_mode"]).upper()
    if tz_mode not in INPUT_TIMEZONE_MODES:
        raise ValueError(f"Unsupported input_timezone_mode='{tz_mode}'. Allowed: {sorted(INPUT_TIMEZONE_MODES)}")
    cfg["input_timezone_mode"] = tz_mode
    cfg["policy"] = cfg.get("policy", {}) or {}
    return cfg


def main() -> None:
    args = parse_args()
    cfg = _load_config(args.config)

    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    ohlc_df = load_ohlc_csv(cfg["input_csv"])
    tagged_df = add_session_columns(ohlc_df, input_timezone_mode=cfg["input_timezone_mode"])
    env_df = add_envelope_columns(tagged_df)
    feature_df = build_feature_frame(env_df)

    base_candidates = build_candidates(env_df)
    candidate_feature_df = attach_features_to_candidates(base_candidates, feature_df)

    policy_cfg = parse_policy_config(cfg.get("policy"))
    policy_result = apply_policy_to_candidates(candidate_feature_df, policy_cfg)
    screened_candidates_df = policy_result["included_df"]
    candidates_audit_df = policy_result["audit_df"]

    outcomes_df = evaluate_candidates(env_df, screened_candidates_df, max_holding_bars=int(cfg["max_holding_bars"]))
    summaries = summarize_outcomes(outcomes_df)

    outcomes_df.to_csv(output_dir / "candidates.csv", index=False)
    candidates_audit_df.to_csv(output_dir / "candidates_policy_audit.csv", index=False)
    summaries["overall"].to_csv(output_dir / "summary_overall.csv", index=False)
    summaries["by_month"].to_csv(output_dir / "summary_by_month.csv", index=False)
    summaries["by_session"].to_csv(output_dir / "summary_by_session.csv", index=False)
    summaries["by_family"].to_csv(output_dir / "summary_by_family.csv", index=False)

    metadata = {
        "simulator_version": "v1",
        "feature_set_version": FEATURE_SET_VERSION,
        "assumption_version": ASSUMPTION_VERSION,
        "input_csv": str(Path(cfg["input_csv"]).resolve()),
        "symbol": str(cfg["symbol"]),
        "timeframe": str(cfg["timeframe"]),
        "pip_size": PIP_SIZE,
        "timeline_handling": {
            "raw_datetime_column": "datetime",
            "input_timezone_mode": cfg["input_timezone_mode"],
            "jst_derivation": "UTC mode => raw +9h; JST mode => raw used directly",
            "session_and_month_source": "jst_datetime",
        },
        "envelope": {
            "ema_span": EMA_SPAN,
            "deviation_rate": DEVIATION_RATE,
        },
        "assumption_notes": {
            "same_bar_ambiguity_rule": "SL-first conservative",
            "entry_evaluation_rule": "Evaluate from next bar after signal bar",
            "entry_price_definition": "Signal reference price from touch-bar close, not broker fill price",
            "mt4_parity": "Not MT4 parity; MT4 remains final source of truth",
        },
        "max_holding_bars": int(cfg["max_holding_bars"]),
        "policy": {
            "enabled": bool(policy_cfg.enabled),
            "name": str(policy_cfg.name) if policy_cfg.enabled else "",
            "semantics": policy_cfg.semantics if policy_cfg.enabled else POLICY_SEMANTICS,
            "rule_count": len(policy_cfg.rules),
            "matched_rule_events": int(policy_result["matched_rule_events"]),
            "base_candidate_count": int(len(candidate_feature_df)),
            "included_candidate_count": int(len(screened_candidates_df)),
            "excluded_candidate_count": int(len(candidates_audit_df) - len(screened_candidates_df)),
        },
        "notes": cfg.get("notes", ""),
    }
    with (output_dir / "run_metadata.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False)

    print(
        "Experiment run completed:",
        f"cand_base={len(candidate_feature_df)}",
        f"cand_included={len(screened_candidates_df)}",
        f"wins={(outcomes_df['outcome_status'] == 'win').sum() if not outcomes_df.empty else 0}",
        f"losses={(outcomes_df['outcome_status'] == 'loss').sum() if not outcomes_df.empty else 0}",
        f"timeouts={(outcomes_df['outcome_status'] == 'timeout').sum() if not outcomes_df.empty else 0}",
        f"tz_mode={cfg['input_timezone_mode']}",
        f"feature_set={FEATURE_SET_VERSION}",
        f"out={output_dir}",
    )


if __name__ == "__main__":
    main()
