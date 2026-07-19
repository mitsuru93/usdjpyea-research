#!/usr/bin/env python3
"""CLI phases for EURUSD 2024 H1-development / H2-validation screen."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from eurusd_h1_h2_data_v1 import *
from eurusd_h1_h2_eval_v1 import *


def development_phase(args: argparse.Namespace) -> int:
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))
    bars = load_bars(args.bars)
    dev_start = pd.Timestamp(protocol["periods"]["development"]["start_utc"])
    dev_end = pd.Timestamp(protocol["periods"]["development"]["end_utc_exclusive"])
    if (bars["timestamp_utc"] >= dev_end).any():
        raise ValueError("development input contains H2 timestamps; H2 must remain unread until development_lock.json exists")
    if (bars["timestamp_utc"] < dev_start).any():
        raise ValueError("development input contains timestamps before the registered development period")
    specs = expand_registry(registry)
    summary, monthly, trades, costs = run_period(bars, specs, registry, session_config, protocol, "development")
    passes, failures = [], []
    for _, row in summary.iterrows():
        passed, failed = candidate_development_pass(row, protocol)
        passes.append(passed)
        failures.append(failed)
    summary["development_gate_pass"] = passes
    summary["development_failed_checks"] = failures
    positive = summary["avg_net_pips"] > 0
    group_positive = summary.assign(_positive=positive).groupby(["family_id", "robustness_group"])["_positive"].sum().to_dict()
    summary["positive_variants_in_robustness_group"] = [int(group_positive[(r.family_id, r.robustness_group)]) for r in summary.itertuples()]
    min_variants = int(protocol["family_nomination_gate"]["positive_registered_variants_gte"])
    summary["robustness_support_pass"] = summary["positive_variants_in_robustness_group"] >= min_variants
    summary["development_representative_eligible"] = summary["development_gate_pass"] & summary["robustness_support_pass"]

    family_rows = []
    representatives: list[str] = []
    nominated_families: list[str] = []
    max_reps = int(protocol["family_nomination_gate"]["max_representatives_per_family"])
    for fid, group in summary.groupby("family_id", sort=True):
        eligible = group[group["development_representative_eligible"]].copy()
        eligible = eligible.sort_values(["profit_factor", "avg_net_pips", "positive_months", "total_excluding_best_two_days"], ascending=False)
        reps = eligible.head(max_reps)["candidate_id"].tolist()
        nominated = len(reps) > 0
        if nominated:
            nominated_families.append(fid)
            representatives.extend(reps)
        family_rows.append({
            "family_id": fid,
            "family": str(group["family"].iloc[0]),
            "registered_candidates": int(len(group)),
            "positive_candidates": int((group["avg_net_pips"] > 0).sum()),
            "development_gate_pass_candidates": int(group["development_gate_pass"].sum()),
            "robustness_supported_candidates": int(group["robustness_support_pass"].sum()),
            "nominated": nominated,
            "representatives": ",".join(reps),
        })
    family_summary = pd.DataFrame(family_rows)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    summary.sort_values(["family_id", "development_representative_eligible", "profit_factor", "avg_net_pips"], ascending=[True, False, False, False]).to_csv(out / "h1_candidate_summary.csv", index=False)
    family_summary.to_csv(out / "h1_family_summary.csv", index=False)
    monthly.to_csv(out / "h1_candidate_monthly.csv", index=False)
    trades.to_csv(out / "h1_candidate_trades.csv", index=False)
    costs.to_csv(out / "h1_cost_grid_summary.csv", index=False)
    json_dump(out / "expanded_candidate_registry.json", {"count": len(specs), "candidates": specs})
    lock = {
        "version": "v1",
        "created_by": "run_eurusd_h1_h2_screen_v1.py development",
        "source": {
            "development_frame_content_sha256": frame_content_sha256(bars),
            "canonical_source_artifact_digest": protocol["source_contract"]["annual_release_asset_sha256"],
            "registry_sha256": sha256_file(args.registry),
            "protocol_sha256": sha256_file(args.protocol),
            "session_config_sha256": sha256_file(args.session_config),
        },
        "development_period": protocol["periods"]["development"],
        "validation_period_locked_unread_for_nomination": protocol["periods"]["validation"],
        "nominated_family_ids": nominated_families,
        "development_representative_candidate_ids": representatives,
        "candidate_count": len(specs),
        "rule": "H2 may validate only the H1-nominated families and may not alter candidate definitions or representatives.",
    }
    json_dump(out / "development_lock.json", lock)
    print(json.dumps(lock, indent=2, sort_keys=True))
    return 0


def validation_phase(args: argparse.Namespace) -> int:
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))
    lock = json.loads(args.development_lock.read_text(encoding="utf-8"))
    if lock["source"]["registry_sha256"] != sha256_file(args.registry):
        raise ValueError("development lock registry hash mismatch")
    if lock["source"]["protocol_sha256"] != sha256_file(args.protocol):
        raise ValueError("development lock protocol hash mismatch")
    if lock["source"]["session_config_sha256"] != sha256_file(args.session_config):
        raise ValueError("development lock session config hash mismatch")
    if lock["source"]["canonical_source_artifact_digest"] != protocol["source_contract"]["annual_release_asset_sha256"]:
        raise ValueError("development lock canonical source digest mismatch")
    bars = load_bars(args.bars)
    dev_start = pd.Timestamp(protocol["periods"]["development"]["start_utc"])
    dev_end = pd.Timestamp(protocol["periods"]["development"]["end_utc_exclusive"])
    dev_slice = bars[(bars["timestamp_utc"] >= dev_start) & (bars["timestamp_utc"] < dev_end)].copy()
    if lock["source"]["development_frame_content_sha256"] != frame_content_sha256(dev_slice):
        raise ValueError("development lock H1 frame content mismatch")
    all_specs = expand_registry(registry)
    nominated = set(lock["nominated_family_ids"])
    specs = [s for s in all_specs if s["family_id"] in nominated]
    summary, monthly, trades, costs = run_period(bars, specs, registry, session_config, protocol, "validation")
    passes, failures = [], []
    for _, row in summary.iterrows():
        passed, failed = candidate_validation_pass(row, protocol)
        passes.append(passed)
        failures.append(failed)
    if not summary.empty:
        summary["validation_gate_pass"] = passes
        summary["validation_failed_checks"] = failures
    representatives = set(lock["development_representative_candidate_ids"])
    if not summary.empty:
        summary["development_representative"] = summary["candidate_id"].isin(representatives)
        group_positive = summary.assign(_positive=summary["avg_net_pips"] > 0).groupby(["family_id", "robustness_group"])["_positive"].sum().to_dict()
        summary["positive_variants_in_h2_robustness_group"] = [int(group_positive[(r.family_id, r.robustness_group)]) for r in summary.itertuples()]

    dev_summary = pd.read_csv(args.development_summary)
    dev_trades = pd.read_csv(args.development_trades, parse_dates=["signal_ts", "entry_ts", "exit_bar_ts", "exit_time_utc"])
    default_col = protocol["cost_cases"]["default"]["net_column"]
    severe_col = protocol["cost_cases"]["severe"]["net_column"]
    final_candidate_rows = []
    for cid in sorted(representatives):
        drow = dev_summary[dev_summary["candidate_id"] == cid]
        hrow = summary[summary["candidate_id"] == cid] if not summary.empty else pd.DataFrame()
        dtr = dev_trades[dev_trades["candidate_id"] == cid]
        htr = trades[trades["candidate_id"] == cid] if not trades.empty else pd.DataFrame()
        both = pd.concat([dtr, htr], ignore_index=True) if not htr.empty else dtr.copy()
        aggregate = metric_summary(both, default_col)
        severe = metric_summary(both, severe_col)
        monthly_all = both.groupby("entry_month")[default_col].mean() if not both.empty else pd.Series(dtype=float)
        daily = both.groupby("entry_date_utc")[default_col].sum().sort_values(ascending=False) if not both.empty else pd.Series(dtype=float)
        h2_pass = bool(hrow["validation_gate_pass"].iloc[0]) if not hrow.empty else False
        full_gate = protocol["full_year_candidate_gate"]
        checks = {
            "h2_validation": h2_pass,
            "aggregate_pf": float(aggregate["profit_factor"]) >= float(full_gate["profit_factor_gte"]),
            "positive_months": int((monthly_all > 0).sum()) >= int(full_gate["positive_months_gte"]),
            "trades": int(aggregate["trades"]) >= int(full_gate["trades_gte"]),
            "ex_best_two": float(aggregate["total_net_pips"] - daily.head(2).sum()) > float(full_gate["total_excluding_best_two_days_gt"]),
            "severe_pf": float(severe["profit_factor"]) >= float(full_gate["severe_profit_factor_gte"]),
        }
        final_candidate_rows.append({
            "candidate_id": cid,
            "family_id": str(drow["family_id"].iloc[0]),
            "family": str(drow["family"].iloc[0]),
            "h1_avg_net_pips": float(drow["avg_net_pips"].iloc[0]),
            "h1_profit_factor": float(drow["profit_factor"].iloc[0]),
            "h2_avg_net_pips": float(hrow["avg_net_pips"].iloc[0]) if not hrow.empty else 0.0,
            "h2_profit_factor": float(hrow["profit_factor"].iloc[0]) if not hrow.empty else 0.0,
            "h2_validation_gate_pass": h2_pass,
            "full_year_trades": aggregate["trades"],
            "full_year_avg_net_pips": aggregate["avg_net_pips"],
            "full_year_total_net_pips": aggregate["total_net_pips"],
            "full_year_profit_factor": aggregate["profit_factor"],
            "full_year_positive_months": int((monthly_all > 0).sum()),
            "full_year_total_excluding_best_two_days": float(aggregate["total_net_pips"] - daily.head(2).sum()),
            "full_year_severe_profit_factor": severe["profit_factor"],
            "final_candidate_pass": all(checks.values()),
            "failed_checks": ",".join(k for k, v in checks.items() if not v),
        })
    final_candidates = pd.DataFrame(final_candidate_rows)
    family_rows = []
    min_h2_variants = int(protocol["family_final_gate"]["positive_h2_registered_variants_gte"])
    for fid in sorted(nominated):
        hgroup = summary[summary["family_id"] == fid] if not summary.empty else pd.DataFrame()
        cgroup = final_candidates[final_candidates["family_id"] == fid] if not final_candidates.empty else pd.DataFrame()
        h2_positive = int((hgroup["avg_net_pips"] > 0).sum()) if not hgroup.empty else 0
        final_pass_count = int(cgroup["final_candidate_pass"].sum()) if not cgroup.empty else 0
        family_rows.append({
            "family_id": fid,
            "family": str(hgroup["family"].iloc[0]) if not hgroup.empty else "",
            "h1_nominated": True,
            "h2_evaluated_candidates": int(len(hgroup)),
            "h2_positive_candidates": h2_positive,
            "development_representatives": int(len(cgroup)),
            "final_candidate_pass_count": final_pass_count,
            "family_final_pass": h2_positive >= min_h2_variants and final_pass_count >= 1,
            "family_failed_checks": ",".join([x for x, ok in [("h2_variant_support", h2_positive >= min_h2_variants), ("representative_survival", final_pass_count >= 1)] if not ok]),
        })
    final_families = pd.DataFrame(family_rows)

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "h2_candidate_summary.csv", index=False)
    monthly.to_csv(out / "h2_candidate_monthly.csv", index=False)
    trades.to_csv(out / "h2_candidate_trades.csv", index=False)
    costs.to_csv(out / "h2_cost_grid_summary.csv", index=False)
    final_candidates.to_csv(out / "final_candidate_decisions.csv", index=False)
    final_families.to_csv(out / "final_family_decisions.csv", index=False)
    result = {
        "version": "v1",
        "development_lock_sha256": sha256_file(args.development_lock),
        "nominated_family_ids": sorted(nominated),
        "final_pass_family_ids": final_families.loc[final_families["family_final_pass"], "family_id"].tolist() if not final_families.empty else [],
        "final_pass_candidate_ids": final_candidates.loc[final_candidates["final_candidate_pass"], "candidate_id"].tolist() if not final_candidates.empty else [],
        "h2_policy": "H2 was used only after the development lock and did not nominate families or alter parameters.",
    }
    json_dump(out / "validation_result.json", result)
    lines = [
        "# EURUSD 2024 H1 development / H2 validation result v1",
        "",
        "H1 means January-June 2024 and H2 means July-December 2024. Market bars are one-hour bars.",
        "",
        f"- H1-nominated families: {', '.join(sorted(nominated)) if nominated else 'none'}",
        f"- Final passing families: {', '.join(result['final_pass_family_ids']) if result['final_pass_family_ids'] else 'none'}",
        f"- Final passing candidates: {', '.join(result['final_pass_candidate_ids']) if result['final_pass_candidate_ids'] else 'none'}",
        "",
        "H2 was evaluated only after development_lock.json was written. H2 did not nominate families or alter parameters.",
        "",
        "## Final family decisions",
        "",
        final_families.to_markdown(index=False) if not final_families.empty else "No H1 family was nominated.",
        "",
        "## Development representatives",
        "",
        final_candidates.to_markdown(index=False) if not final_candidates.empty else "No development representative was nominated.",
    ]
    (out / "analysis_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["development", "validation"], required=True)
    p.add_argument("--bars", type=Path, required=True)
    p.add_argument("--registry", type=Path, required=True)
    p.add_argument("--session-config", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--development-lock", type=Path)
    p.add_argument("--development-summary", type=Path)
    p.add_argument("--development-trades", type=Path)
    args = p.parse_args()
    if args.phase == "validation" and not all([args.development_lock, args.development_summary, args.development_trades]):
        p.error("validation requires --development-lock --development-summary --development-trades")
    return args


def main() -> int:
    args = parse_args()
    return development_phase(args) if args.phase == "development" else validation_phase(args)


if __name__ == "__main__":
    raise SystemExit(main())
