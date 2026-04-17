#!/usr/bin/env python3
"""Config-driven experiment runner for simulator v1 + feature snapshots."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.features import FEATURE_SET_VERSION, attach_features_to_candidates, build_feature_frame
from research.io.csv_loader import load_ohlc_csv
from research.policy import (
    POLICY_SEMANTICS,
    apply_decision_policy_to_candidates,
    apply_policy_to_candidates,
    parse_decision_policy_config,
    parse_policy_config,
)
from research.scoring.summary import summarize_outcomes, summarize_timing_audit, summarize_timing_diagnostics
from research.simulator.candidate_engine import (
    ASSUMPTION_VERSION,
    DEFAULT_TIMING_MODE,
    TIMING_MODES,
    apply_timing_mode,
    build_candidates,
)
from research.simulator.envelope import (
    DEFAULT_ATR_PERIOD,
    DEFAULT_BAND_MODEL,
    DEFAULT_PIP_SIZE,
    DEFAULT_RANGE_PERIOD,
    DEFAULT_STD_PERIOD,
    DEFAULT_VOL_PERIOD,
    DEVIATION_RATE,
    EMA_SPAN,
    SUPPORTED_BAND_MODELS,
    add_envelope_columns,
)
from research.simulator.outcome_engine import DEFAULT_MAX_HOLDING_BARS, PIP_SIZE, evaluate_candidates
from research.simulator.session import INPUT_TIMEZONE_MODES, add_session_columns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run config-driven pre-MT4 candidate experiment.")
    parser.add_argument("--config", required=True, help="Path to YAML experiment config.")
    return parser.parse_args()


def _load_config(path: str | Path) -> dict:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    required = ["input_csv", "output_dir", "input_timezone_mode", "max_holding_bars", "symbol", "timeframe"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Experiment config missing required fields: {missing}")

    tz_mode = str(cfg["input_timezone_mode"]).upper()
    if tz_mode not in INPUT_TIMEZONE_MODES:
        raise ValueError(f"Unsupported input_timezone_mode='{tz_mode}'. Allowed: {sorted(INPUT_TIMEZONE_MODES)}")
    cfg["input_timezone_mode"] = tz_mode
    timing_mode = str(cfg.get("timing_mode", DEFAULT_TIMING_MODE)).strip().lower()
    if timing_mode not in TIMING_MODES:
        raise ValueError(f"Unsupported timing_mode='{timing_mode}'. Allowed: {sorted(TIMING_MODES)}")
    cfg["timing_mode"] = timing_mode

    has_inline_policy = "policy" in cfg and cfg.get("policy") not in (None, {})
    has_policy_file = "policy_file" in cfg and str(cfg.get("policy_file", "")).strip() != ""

    if has_inline_policy and has_policy_file:
        raise ValueError("Use either 'policy' or 'policy_file' in an experiment config, not both.")

    if has_policy_file:
        policy_file_path = _resolve_policy_file_path(
            raw_path=str(cfg["policy_file"]),
            config_dir=config_path.parent,
        )
        cfg["policy"] = _load_policy_preset(policy_file_path)
    else:
        cfg["policy"] = cfg.get("policy", {}) or {}

    return cfg


def _resolve_policy_file_path(*, raw_path: str, config_dir: Path) -> Path:
    policy_path = Path(raw_path)
    if policy_path.is_absolute():
        if not policy_path.exists():
            raise FileNotFoundError(f"Policy preset file not found: {policy_path}")
        return policy_path.resolve()

    candidate_from_config_dir = (config_dir / policy_path).resolve()
    if candidate_from_config_dir.exists():
        return candidate_from_config_dir

    candidate_from_repo_root = (REPO_ROOT / policy_path).resolve()
    if candidate_from_repo_root.exists():
        return candidate_from_repo_root

    raise FileNotFoundError(
        "Policy preset file not found. Tried config-relative and repo-root-relative paths: "
        f"'{candidate_from_config_dir}' and '{candidate_from_repo_root}'."
    )


def _load_policy_preset(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Policy preset must be a mapping-style YAML config: {path}")
    return payload


def _build_precompute_inputs(cfg: dict) -> tuple[dict[str, object], dict[str, object]]:
    band_model = str(cfg.get("band_model", DEFAULT_BAND_MODEL)).strip().lower()
    if band_model not in SUPPORTED_BAND_MODELS:
        raise ValueError(f"Unsupported band_model='{band_model}'. Allowed: {sorted(SUPPORTED_BAND_MODELS)}")

    def _read_value(key: str, default: object, cast: object) -> object:
        raw = cfg.get(key)
        value = default if raw is None or raw == "" else raw
        return cast(value) if callable(cast) else value

    params: dict[str, object] = {
        "band_model": band_model,
        "ema_period": _read_value("ema_period", EMA_SPAN, int),
        "band_percent": _read_value("band_percent", DEVIATION_RATE, float),
        "band_pips": _read_value("band_pips", 10.0, float),
        "band_atr_k": _read_value("band_atr_k", 1.0, float),
        "band_atr_period": _read_value("band_atr_period", DEFAULT_ATR_PERIOD, int),
        "band_std_k": _read_value("band_std_k", 1.0, float),
        "band_std_period": _read_value("band_std_period", DEFAULT_STD_PERIOD, int),
        "band_std_source": str(_read_value("band_std_source", "returns", str)).strip().lower(),
        "band_range_period": _read_value("band_range_period", DEFAULT_RANGE_PERIOD, int),
        "band_range_k": _read_value("band_range_k", 1.0, float),
        "band_range_percentile": _read_value("band_range_percentile", 0.75, float),
        "band_vol_period": _read_value("band_vol_period", DEFAULT_VOL_PERIOD, int),
        "band_vol_k": _read_value("band_vol_k", 1.0, float),
        "band_fixed_floor_pips": _read_value("band_fixed_floor_pips", 8.0, float),
        "band_fixed_cap_pips": _read_value("band_fixed_cap_pips", 15.0, float),
        "pip_size": _read_value("pip_size", DEFAULT_PIP_SIZE, float),
    }
    defaults_used: dict[str, bool] = {}
    for key in params:
        defaults_used[key] = key not in cfg or cfg.get(key) is None or cfg.get(key) == ""
    return params, defaults_used


def _compute_preprocessed_frames(cfg: dict, params: dict[str, object]) -> dict[str, pd.DataFrame]:
    ohlc_df = load_ohlc_csv(cfg["input_csv"])
    tagged_df = add_session_columns(ohlc_df, input_timezone_mode=cfg["input_timezone_mode"])
    env_df = add_envelope_columns(
        tagged_df,
        ema_span=int(params["ema_period"]),
        band_model=str(params["band_model"]),
        band_percent=float(params["band_percent"]),
        band_pips=float(params["band_pips"]),
        band_atr_k=float(params["band_atr_k"]),
        band_atr_period=int(params["band_atr_period"]),
        band_std_k=float(params["band_std_k"]),
        band_std_period=int(params["band_std_period"]),
        band_std_source=str(params["band_std_source"]),
        band_range_period=int(params["band_range_period"]),
        band_range_k=float(params["band_range_k"]),
        band_range_percentile=float(params["band_range_percentile"]),
        band_vol_period=int(params["band_vol_period"]),
        band_vol_k=float(params["band_vol_k"]),
        band_fixed_floor_pips=float(params["band_fixed_floor_pips"]),
        band_fixed_cap_pips=float(params["band_fixed_cap_pips"]),
        pip_size=float(params["pip_size"]),
    )
    feature_df = build_feature_frame(env_df)
    base_candidates = build_candidates(env_df)
    timing_result = apply_timing_mode(base_candidates, env_df, timing_mode=cfg["timing_mode"])
    timing_audit_df = timing_result["timing_audit_df"]
    timing_entered_df = timing_result["entered_df"]
    candidate_feature_df = attach_features_to_candidates(timing_entered_df, feature_df)
    return {
        "env_df": env_df,
        "feature_df": feature_df,
        "base_candidates": base_candidates,
        "timing_audit_df": timing_audit_df,
        "timing_entered_df": timing_entered_df,
        "candidate_feature_df": candidate_feature_df,
    }


def _resolve_shared_precompute(cfg: dict, params: dict[str, object]) -> tuple[dict[str, pd.DataFrame], dict[str, object]]:
    cache_dir_raw = str(cfg.get("shared_precompute_cache_dir", "")).strip()
    cache_key_raw = str(cfg.get("shared_precompute_cache_key", "")).strip()
    if not cache_dir_raw or not cache_key_raw:
        return _compute_preprocessed_frames(cfg, params), {"enabled": False, "cache_hit": False, "cache_key": ""}

    cache_dir = Path(cache_dir_raw).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_hash = hashlib.sha256(cache_key_raw.encode("utf-8")).hexdigest()
    cache_path = cache_dir / f"{cache_hash}.pkl"

    if cache_path.exists():
        cached = pd.read_pickle(cache_path)
        return cached, {"enabled": True, "cache_hit": True, "cache_key": cache_key_raw, "cache_path": str(cache_path)}

    preprocessed = _compute_preprocessed_frames(cfg, params)
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=cache_dir, prefix=f".{cache_hash}.", suffix=".tmp") as tmp:
        tmp_path = Path(tmp.name)
    pd.to_pickle(preprocessed, tmp_path)
    tmp_path.replace(cache_path)
    return preprocessed, {"enabled": True, "cache_hit": False, "cache_key": cache_key_raw, "cache_path": str(cache_path)}


def main() -> None:
    args = parse_args()
    cfg = _load_config(args.config)

    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    params, effective_defaults_used = _build_precompute_inputs(cfg)
    band_model = str(params["band_model"])
    ema_period = int(params["ema_period"])
    band_percent = float(params["band_percent"])
    band_pips = float(params["band_pips"])
    band_atr_k = float(params["band_atr_k"])
    band_atr_period = int(params["band_atr_period"])
    band_std_k = float(params["band_std_k"])
    band_std_period = int(params["band_std_period"])
    band_std_source = str(params["band_std_source"])
    band_range_period = int(params["band_range_period"])
    band_range_k = float(params["band_range_k"])
    band_range_percentile = float(params["band_range_percentile"])
    band_vol_period = int(params["band_vol_period"])
    band_vol_k = float(params["band_vol_k"])
    band_fixed_floor_pips = float(params["band_fixed_floor_pips"])
    band_fixed_cap_pips = float(params["band_fixed_cap_pips"])
    pip_size = float(params["pip_size"])

    precompute_result, precompute_stats = _resolve_shared_precompute(cfg, params)
    env_df = precompute_result["env_df"]
    base_candidates = precompute_result["base_candidates"]
    timing_audit_df = precompute_result["timing_audit_df"]
    timing_entered_df = precompute_result["timing_entered_df"]
    candidate_feature_df = precompute_result["candidate_feature_df"]

    decision_policy_cfg = parse_decision_policy_config(cfg.get("decision_policy"), cfg.get("score_bundle"))
    decision_policy_result = apply_decision_policy_to_candidates(candidate_feature_df, decision_policy_cfg)
    decision_candidates_df = decision_policy_result["included_df"]
    decision_policy_audit_df = decision_policy_result["audit_df"]
    decision_policy_summary = decision_policy_result["summary"]

    policy_cfg = parse_policy_config(cfg.get("policy"))
    policy_result = apply_policy_to_candidates(decision_candidates_df, policy_cfg)
    screened_candidates_df = policy_result["included_df"]
    candidates_audit_df = policy_result["audit_df"]

    outcomes_df = evaluate_candidates(env_df, screened_candidates_df, max_holding_bars=int(cfg["max_holding_bars"]))
    summaries = summarize_outcomes(outcomes_df)
    timing_summaries = summarize_timing_audit(timing_audit_df)
    timing_diagnostics = summarize_timing_diagnostics(timing_audit_df)

    def _count_timing_event(event_name: str) -> int:
        if "timing_decision_event" not in timing_audit_df.columns:
            return 0
        return int((timing_audit_df["timing_decision_event"] == event_name).sum())

    candidate_count = int(len(base_candidates))
    touched_upper_count = int(pd.to_numeric(env_df.get("touch_upper"), errors="coerce").fillna(False).astype(bool).sum())
    touched_lower_count = int(pd.to_numeric(env_df.get("touch_lower"), errors="coerce").fillna(False).astype(bool).sum())
    first_candidate_time = ""
    last_candidate_time = ""
    if candidate_count > 0 and "timestamp" in base_candidates.columns:
        ts = pd.to_datetime(base_candidates["timestamp"], errors="coerce", utc=True).dropna().sort_values()
        if not ts.empty:
            first_candidate_time = ts.iloc[0].isoformat()
            last_candidate_time = ts.iloc[-1].isoformat()

    outcomes_df.to_csv(output_dir / "candidates.csv", index=False)

    aggregate_cols = [col for col in ["timestamp", "pnl_pips"] if col in outcomes_df.columns]
    aggregate_candidates_df = outcomes_df.loc[:, aggregate_cols].copy() if aggregate_cols else pd.DataFrame(columns=["timestamp", "pnl_pips"])
    if "timestamp" not in aggregate_candidates_df.columns:
        aggregate_candidates_df["timestamp"] = pd.Series(dtype="object")
    if "pnl_pips" not in aggregate_candidates_df.columns:
        aggregate_candidates_df["pnl_pips"] = pd.Series(dtype="float64")
    aggregate_candidates_df = aggregate_candidates_df[["timestamp", "pnl_pips"]]
    aggregate_candidates_df.to_csv(output_dir / "candidates_aggregate.csv.gz", index=False, compression="gzip")

    timing_audit_df.to_csv(output_dir / "candidates_timing_audit.csv", index=False)
    decision_policy_audit_df.to_csv(output_dir / "candidates_decision_policy_audit.csv", index=False)
    candidates_audit_df.to_csv(output_dir / "candidates_policy_audit.csv", index=False)
    summaries["overall"].to_csv(output_dir / "summary_overall.csv", index=False)
    summaries["by_month"].to_csv(output_dir / "summary_by_month.csv", index=False)
    summaries["by_session"].to_csv(output_dir / "summary_by_session.csv", index=False)
    summaries["by_family"].to_csv(output_dir / "summary_by_family.csv", index=False)
    timing_summaries["overall"].to_csv(output_dir / "summary_timing_overall.csv", index=False)
    timing_summaries["by_month"].to_csv(output_dir / "summary_timing_by_month.csv", index=False)
    timing_summaries["by_session"].to_csv(output_dir / "summary_timing_by_session.csv", index=False)
    timing_summaries["by_family"].to_csv(output_dir / "summary_timing_by_family.csv", index=False)
    timing_diagnostics["timing_by_decision_event"].to_csv(output_dir / "summary_timing_by_decision_event.csv", index=False)
    timing_diagnostics["timing_by_reject_reason"].to_csv(output_dir / "summary_timing_by_reject_reason.csv", index=False)
    timing_diagnostics["timing_by_family_decision_event"].to_csv(
        output_dir / "summary_timing_by_family_decision_event.csv", index=False
    )
    timing_diagnostics["timing_by_family_reject_reason"].to_csv(
        output_dir / "summary_timing_by_family_reject_reason.csv", index=False
    )
    timing_diagnostics["timing_by_still_touch_status"].to_csv(
        output_dir / "summary_timing_by_still_touch_status.csv", index=False
    )
    pd.DataFrame(
        [
            {
                "candidate_count": candidate_count,
                "first_candidate_time": first_candidate_time,
                "last_candidate_time": last_candidate_time,
                "touched_upper_count": touched_upper_count,
                "touched_lower_count": touched_lower_count,
            }
        ]
    ).to_csv(output_dir / "candidate_summary.csv", index=False)
    effective_band_config = {
        "band_model": band_model,
        "band_percent": band_percent,
        "band_pips": band_pips,
        "band_atr_k": band_atr_k,
        "band_atr_period": band_atr_period,
        "band_std_k": band_std_k,
        "band_std_period": band_std_period,
        "band_std_source": band_std_source,
        "band_range_period": band_range_period,
        "band_range_k": band_range_k,
        "band_range_percentile": band_range_percentile,
        "band_vol_period": band_vol_period,
        "band_vol_k": band_vol_k,
        "band_fixed_floor_pips": band_fixed_floor_pips,
        "band_fixed_cap_pips": band_fixed_cap_pips,
        "band_percent_display": f"{band_percent * 100.0:.5f}%",
        "pip_size": pip_size,
        "ema_period": ema_period,
        "defaults_used": effective_defaults_used,
    }
    with (output_dir / "effective_band_config.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(effective_band_config, f, sort_keys=False)
    effective_decision_policy = {
        "decision_policy_family": decision_policy_cfg.family,
        "score_bundle": decision_policy_cfg.score_bundle,
        "decision_policy_version": decision_policy_cfg.version,
        "entry_threshold": decision_policy_cfg.entry_threshold,
        "margin_threshold": decision_policy_cfg.margin_threshold,
        "no_entry_threshold": decision_policy_cfg.no_entry_threshold,
        "rv_score_weights": decision_policy_cfg.rv_score_weights or {},
        "tr_score_weights": decision_policy_cfg.tr_score_weights or {},
        "notes": "Research-only RV/TR/no-entry selection. MT4 remains final source of truth.",
    }
    with (output_dir / "effective_decision_policy.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(effective_decision_policy, f, sort_keys=False)
    pd.DataFrame([decision_policy_summary]).to_csv(output_dir / "policy_candidate_summary.csv", index=False)

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
            "effective_ema_period": ema_period,
            "deviation_rate": DEVIATION_RATE,
            "band_model": band_model,
            "band_percent": band_percent,
            "band_pips": band_pips,
            "band_atr_k": band_atr_k,
            "band_atr_period": band_atr_period,
            "band_std_k": band_std_k,
            "band_std_period": band_std_period,
            "band_std_source": band_std_source,
            "band_range_period": band_range_period,
            "band_range_k": band_range_k,
            "band_range_percentile": band_range_percentile,
            "band_vol_period": band_vol_period,
            "band_vol_k": band_vol_k,
            "band_fixed_floor_pips": band_fixed_floor_pips,
            "band_fixed_cap_pips": band_fixed_cap_pips,
            "pip_size": pip_size,
        },
        "assumption_notes": {
            "same_bar_ambiguity_rule": "SL-first conservative",
            "entry_evaluation_rule": "Evaluate from next bar after signal bar",
            "entry_price_definition": "Signal reference price from touch-bar close, not broker fill price",
            "mt4_parity": "Not MT4 parity; MT4 remains final source of truth",
            "timing_mode": cfg["timing_mode"],
            "timing_mode_semantics": {
                "baseline_touch": "Touch evidence enters immediately (baseline behavior).",
                "rv_close_confirm": (
                    "RV uses touch-created candidate and close-time entry decision; "
                    "still-touch-at-close is not required."
                ),
                "all_close": "Research comparison mode only: all families use close-time decision.",
            },
        },
        "max_holding_bars": int(cfg["max_holding_bars"]),
        "timing_audit_counts": {
            "candidate_created_count": int(len(timing_audit_df)),
            "touch_entered_immediately_count": _count_timing_event("touch_entered_immediately"),
            "close_confirmed_count": _count_timing_event("close_confirmed"),
            "close_rejected_count": _count_timing_event("close_rejected"),
        },
        "decision_policy": {
            **effective_decision_policy,
            **decision_policy_summary,
        },
        "policy": {
            "enabled": bool(policy_cfg.enabled),
            "name": str(policy_cfg.name) if policy_cfg.enabled else "",
            "semantics": policy_cfg.semantics if policy_cfg.enabled else POLICY_SEMANTICS,
            "rule_count": len(policy_cfg.rules),
            "matched_rule_events": int(policy_result["matched_rule_events"]),
            "base_candidate_count": int(len(decision_candidates_df)),
            "included_candidate_count": int(len(screened_candidates_df)),
            "excluded_candidate_count": int(len(candidates_audit_df) - len(screened_candidates_df)),
        },
        "notes": cfg.get("notes", ""),
        "shared_precompute": precompute_stats,
    }
    with (output_dir / "run_metadata.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False)

    print(
        "Experiment run completed:",
        f"cand_base={len(candidate_feature_df)}",
        f"cand_decision={len(decision_candidates_df)}",
        f"cand_included={len(screened_candidates_df)}",
        f"decision_policy={decision_policy_cfg.family}",
        f"score_bundle={decision_policy_cfg.score_bundle}",
        f"timing_mode={cfg['timing_mode']}",
        f"wins={(outcomes_df['outcome_status'] == 'win').sum() if not outcomes_df.empty else 0}",
        f"losses={(outcomes_df['outcome_status'] == 'loss').sum() if not outcomes_df.empty else 0}",
        f"timeouts={(outcomes_df['outcome_status'] == 'timeout').sum() if not outcomes_df.empty else 0}",
        f"tz_mode={cfg['input_timezone_mode']}",
        f"feature_set={FEATURE_SET_VERSION}",
        f"shared_precompute={'hit' if precompute_stats.get('cache_hit', False) else ('miss' if precompute_stats.get('enabled', False) else 'disabled')}",
        f"out={output_dir}",
    )


if __name__ == "__main__":
    main()
