#!/usr/bin/env python3
from __future__ import annotations

import argparse
import cProfile
import json
import pstats
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.policy.decision_policy import (  # noqa: E402
    DecisionPolicyConfig,
    DecisionPrepBundle,
    apply_prepared_decision_policy,
    prepare_decision_policy_inputs,
)
from research.simulator.candidate_engine import build_candidates  # noqa: E402
from research.simulator.outcome_engine import evaluate_candidates  # noqa: E402
from tools.run_experiment import (  # noqa: E402
    _build_precompute_inputs,
    _candidate_universe_identity,
    _compute_preprocessed_frames,
    _resolve_decision_score_prep_cache,
    _resolve_outcome_cache,
)


def _legacy_build_candidates(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in df.itertuples(index=False):
        if row.touch_upper:
            rows.extend([
                {
                    "timestamp": row.datetime,
                    "session": row.session,
                    "month": row.month,
                    "touch_side": "upper",
                    "candidate_family": "rev",
                    "direction": "sell",
                    "entry_price": float(row.close),
                    "entry_price_type": "signal_reference_price",
                    "tp_pips": 10,
                    "sl_pips": 30,
                    "assumption_version": "sim_v1_conservative",
                },
                {
                    "timestamp": row.datetime,
                    "session": row.session,
                    "month": row.month,
                    "touch_side": "upper",
                    "candidate_family": "trend",
                    "direction": "buy",
                    "entry_price": float(row.close),
                    "entry_price_type": "signal_reference_price",
                    "tp_pips": 10,
                    "sl_pips": 20,
                    "assumption_version": "sim_v1_conservative",
                },
            ])
        if row.touch_lower:
            rows.extend([
                {
                    "timestamp": row.datetime,
                    "session": row.session,
                    "month": row.month,
                    "touch_side": "lower",
                    "candidate_family": "rev",
                    "direction": "buy",
                    "entry_price": float(row.close),
                    "entry_price_type": "signal_reference_price",
                    "tp_pips": 10,
                    "sl_pips": 30,
                    "assumption_version": "sim_v1_conservative",
                },
                {
                    "timestamp": row.datetime,
                    "session": row.session,
                    "month": row.month,
                    "touch_side": "lower",
                    "candidate_family": "trend",
                    "direction": "sell",
                    "entry_price": float(row.close),
                    "entry_price_type": "signal_reference_price",
                    "tp_pips": 10,
                    "sl_pips": 20,
                    "assumption_version": "sim_v1_conservative",
                },
            ])
    return pd.DataFrame(rows)


def _legacy_prepare(df: pd.DataFrame, score_bundle: str) -> pd.DataFrame:
    # use current prep for score attachment, then overwrite with legacy group-loop ranking logic
    prep = prepare_decision_policy_inputs(df, score_bundle).prep_df.copy()
    for _, part in prep.groupby(["timestamp", "touch_side"], sort=False, dropna=False):
        group_id = f"{part.iloc[0]['timestamp']}|{part.iloc[0]['touch_side']}"
        prep.loc[part.index, "decision_group_id"] = group_id
        ranked = part.sort_values(["rvtr_score", "candidate_family"], ascending=[False, True])
        best_score = float(ranked.iloc[0]["rvtr_score"])
        second_score = float(ranked.iloc[1]["rvtr_score"]) if len(ranked) > 1 else 0.0
        prep.loc[part.index, "decision_best_score"] = best_score
        prep.loc[part.index, "decision_second_score"] = second_score
        prep.loc[part.index, "rvtr_score_margin"] = best_score - second_score
        prep.loc[part.index, "decision_group_count"] = int(len(ranked))
        for rank, idx in enumerate(ranked.index, start=1):
            prep.loc[idx, "decision_group_rank"] = rank
    return prep


def _legacy_apply(prep_df: pd.DataFrame, policy: DecisionPolicyConfig) -> pd.DataFrame:
    audit_df = prep_df.copy()
    audit_df["selected_by_decision_policy"] = False
    audit_df["decision_policy_outcome"] = "exclude"
    if policy.family == "bin_env_v1":
        audit_df["selected_by_decision_policy"] = True
        audit_df["decision_policy_outcome"] = "include"
        return audit_df
    for _, part in audit_df.groupby("decision_group_id", sort=False, dropna=False):
        best = part[part["decision_group_rank"] == 1]
        if best.empty:
            continue
        best_idx = best.index[0]
        margin = float(part["rvtr_score_margin"].iloc[0])
        best_score = float(part["decision_best_score"].iloc[0])
        if policy.family == "two_stage_margin_v1" and margin < policy.margin_threshold:
            audit_df.loc[part.index, "decision_policy_outcome"] = "no_entry_margin"
            continue
        if policy.family == "tri_score_rvtrno_v1":
            no_entry_score = policy.no_entry_threshold + max(0.0, policy.margin_threshold - margin)
            if no_entry_score >= best_score:
                audit_df.loc[part.index, "decision_policy_outcome"] = "no_entry_score"
                continue
        audit_df.loc[best_idx, "selected_by_decision_policy"] = True
        audit_df.loc[best_idx, "decision_policy_outcome"] = "include"
    return audit_df


def _legacy_evaluate(ohlc_df: pd.DataFrame, candidates_df: pd.DataFrame, max_holding_bars: int) -> pd.DataFrame:
    # faithful old double-loop baseline used for perf comparison
    if candidates_df.empty:
        return candidates_df.copy()
    bars = ohlc_df.reset_index(drop=True)
    highs = pd.to_numeric(bars["high"], errors="coerce").to_numpy(dtype=float, copy=False)
    lows = pd.to_numeric(bars["low"], errors="coerce").to_numpy(dtype=float, copy=False)
    idx_map = {ts: i for i, ts in enumerate(bars["datetime"].tolist())}
    rows = []
    for row in candidates_df.itertuples(index=False):
        entry_idx = idx_map[row.timestamp]
        start = entry_idx + 1
        end = min(start + max_holding_bars, len(highs))
        entry = float(row.entry_price)
        tp_move = float(row.tp_pips) * 0.01
        sl_move = float(row.sl_pips) * 0.01
        if row.direction == "buy":
            tp_price = entry + tp_move
            sl_price = entry - sl_move
        else:
            tp_price = entry - tp_move
            sl_price = entry + sl_move
        status = "timeout"
        exit_price = entry
        bars_held = max(0, end - start)
        for bi in range(start, end):
            high, low = highs[bi], lows[bi]
            if row.direction == "buy":
                tp_hit = high >= tp_price
                sl_hit = low <= sl_price
            else:
                tp_hit = low <= tp_price
                sl_hit = high >= sl_price
            if tp_hit and sl_hit:
                status = "loss"; exit_price = sl_price; bars_held = bi - start + 1; break
            if sl_hit:
                status = "loss"; exit_price = sl_price; bars_held = bi - start + 1; break
            if tp_hit:
                status = "win"; exit_price = tp_price; bars_held = bi - start + 1; break
        out = row._asdict()
        out["outcome_status"] = status
        out["exit_price"] = float(exit_price)
        out["bars_held"] = int(bars_held)
        out["pnl_pips"] = float((exit_price - entry) / 0.01 if row.direction == "buy" else (entry - exit_price) / 0.01)
        rows.append(out)
    return pd.DataFrame(rows)


def _bench(fn, loops: int = 5) -> dict[str, float]:
    samples = []
    for _ in range(loops):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return {
        "mean_sec": float(statistics.mean(samples)),
        "median_sec": float(statistics.median(samples)),
        "min_sec": float(min(samples)),
        "max_sec": float(max(samples)),
    }


def _run_experiment(config: Path, profile_out: Path | None = None) -> float:
    cmd = [sys.executable, str(REPO_ROOT / "tools" / "run_experiment.py"), "--config", str(config)]
    if profile_out is not None:
        cmd = [sys.executable, "-m", "cProfile", "-o", str(profile_out), str(REPO_ROOT / "tools" / "run_experiment.py"), "--config", str(config)]
    t0 = time.perf_counter()
    subprocess.run(cmd, cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return time.perf_counter() - t0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="docs/benchmarks/hotpath_profile")
    args = parser.parse_args()

    output_dir = (REPO_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        cache_dir = tmp / "cache"
        run1 = tmp / "run1"
        run2 = tmp / "run2"
        config = {
            "input_csv": "research/data_sample/usdjpy_m1_tiny_sample.csv",
            "output_dir": str(run1),
            "input_timezone_mode": "UTC",
            "max_holding_bars": 20,
            "symbol": "USDJPY",
            "timeframe": "M1",
            "timing_mode": "baseline_touch",
            "band_model": "fixed_pips",
            "band_pips": 10,
            "decision_policy": {"family": "two_stage_margin_v1", "margin_threshold": 0.75, "no_entry_threshold": 0.25},
            "score_bundle": "sf_ctx_base_v1",
            "policy": {},
            "shared_precompute_cache_dir": str(cache_dir),
            "shared_precompute_cache_key": "hotpath-profile-v1",
        }
        cfg1 = tmp / "run1.yaml"
        cfg2 = tmp / "run2.yaml"
        cfg1.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        config2 = dict(config); config2["output_dir"] = str(run2)
        cfg2.write_text(yaml.safe_dump(config2, sort_keys=False), encoding="utf-8")

        profile_file = tmp / "run1.prof"
        run1_wall = _run_experiment(cfg1, profile_out=profile_file)
        run2_wall = _run_experiment(cfg2, profile_out=None)

        md1 = yaml.safe_load((run1 / "run_metadata.yaml").read_text())
        md2 = yaml.safe_load((run2 / "run_metadata.yaml").read_text())

        params, _ = _build_precompute_inputs(config)
        pre = _compute_preprocessed_frames(config, params)
        env_df = pre["env_df"]
        cand_feat_df = pre["candidate_feature_df"]

        policy = DecisionPolicyConfig(family="two_stage_margin_v1", score_bundle="sf_ctx_base_v1", margin_threshold=0.75, no_entry_threshold=0.25)
        prep_new = _bench(lambda: prepare_decision_policy_inputs(cand_feat_df, policy.score_bundle))
        prep_old = _bench(lambda: _legacy_prepare(cand_feat_df, policy.score_bundle))

        bundle = prepare_decision_policy_inputs(cand_feat_df, policy.score_bundle)
        apply_new = _bench(lambda: apply_prepared_decision_policy(bundle, policy))
        apply_old = _bench(lambda: _legacy_apply(bundle.prep_df, policy))

        outcome_new = _bench(lambda: evaluate_candidates(env_df, cand_feat_df, max_holding_bars=20))
        outcome_old = _bench(lambda: _legacy_evaluate(env_df, cand_feat_df, max_holding_bars=20))

        build_new = _bench(lambda: build_candidates(env_df))
        build_old = _bench(lambda: _legacy_build_candidates(env_df))

        universe_id = _bench(lambda: _candidate_universe_identity(cand_feat_df))
        cache_rw = _bench(
            lambda: (
                _resolve_decision_score_prep_cache(
                    cfg=config,
                    candidate_feature_df=cand_feat_df,
                    score_bundle=policy.score_bundle,
                    decision_policy_version=policy.version,
                    universe_identity=_candidate_universe_identity(cand_feat_df),
                ),
                _resolve_outcome_cache(
                    cfg=config,
                    env_df=env_df,
                    candidate_feature_df=cand_feat_df,
                    max_holding_bars=20,
                    universe_identity=_candidate_universe_identity(cand_feat_df),
                ),
            )
        )

        ps = pstats.Stats(str(profile_file))
        ps.strip_dirs()
        target_funcs = [
            "evaluate_candidates",
            "prepare_decision_policy_inputs",
            "apply_prepared_decision_policy",
            "build_candidates",
            "_candidate_universe_identity",
            "_resolve_decision_score_prep_cache",
            "_resolve_outcome_cache",
        ]
        cprofile_hits: dict[str, dict[str, float]] = {}
        for fn, stat in ps.stats.items():
            _, _, name = fn
            if name in target_funcs:
                cc, nc, tt, ct, _ = stat
                cprofile_hits[name] = {
                    "call_count": float(nc),
                    "tottime_sec": float(tt),
                    "cumtime_sec": float(ct),
                }

        result = {
            "single_run": {
                "run1_cache_miss_wall_sec": run1_wall,
                "run2_cache_hit_wall_sec": run2_wall,
                "run1_stage_elapsed_sec": md1.get("telemetry", {}).get("stage_elapsed_sec", {}),
                "run2_stage_elapsed_sec": md2.get("telemetry", {}).get("stage_elapsed_sec", {}),
                "run1_cache": md1.get("cache", {}),
                "run2_cache": md2.get("cache", {}),
            },
            "microbench": {
                "prepare_decision_policy_inputs": {"new": prep_new, "legacy": prep_old},
                "apply_prepared_decision_policy": {"new": apply_new, "legacy": apply_old},
                "evaluate_candidates": {"new": outcome_new, "legacy": outcome_old},
                "build_candidates": {"new": build_new, "legacy": build_old},
                "candidate_universe_identity": universe_id,
                "cache_read_write": cache_rw,
            },
            "cprofile": cprofile_hits,
        }

        (output_dir / "hotpath_profile.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        lines = [
            "# Hotpath profile report",
            "",
            "## Single-run telemetry (cache miss/hit)",
            f"- miss wall sec: {run1_wall:.6f}",
            f"- hit wall sec: {run2_wall:.6f}",
            f"- miss decision_score_prep sec: {md1['telemetry']['stage_elapsed_sec'].get('decision_score_prep', 0):.6f}",
            f"- miss decision_threshold_apply sec: {md1['telemetry']['stage_elapsed_sec'].get('decision_threshold_apply', 0):.6f}",
            f"- miss outcome_resolve sec: {md1['telemetry']['stage_elapsed_sec'].get('outcome_resolve', 0):.6f}",
            "",
            "## Microbench (median sec, new vs legacy)",
        ]
        for key in ["prepare_decision_policy_inputs", "apply_prepared_decision_policy", "evaluate_candidates", "build_candidates"]:
            new_med = result["microbench"][key]["new"]["median_sec"]
            old_med = result["microbench"][key]["legacy"]["median_sec"]
            speedup = (old_med / new_med) if new_med > 0 else 0.0
            lines.append(f"- {key}: new={new_med:.6f}, legacy={old_med:.6f}, speedup={speedup:.2f}x")
        lines.extend([
            "",
            "## cProfile targets (cumtime sec)",
        ])
        for fn in target_funcs:
            if fn in cprofile_hits:
                lines.append(f"- {fn}: {cprofile_hits[fn]['cumtime_sec']:.6f}")
        (output_dir / "hotpath_profile.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote {output_dir / 'hotpath_profile.json'}")
    print(f"wrote {output_dir / 'hotpath_profile.md'}")


if __name__ == "__main__":
    main()
