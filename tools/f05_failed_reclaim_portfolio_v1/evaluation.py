"""Scientific evaluation orchestration for the frozen F05 candidate."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd

from usdjpy_structural_sl_v1.common import (
    EXPECTED_COUNTS,
    aggregate_bars,
    historical_2023_trades,
    load_2023_m15,
    load_m1,
    parse_event_trades,
    r1,
    sha256_file,
    write_json,
)
from f05_failed_reclaim_portfolio_v1.events import (
    derive_event_ledger,
    stringify_times,
    summarize_reproduction,
    trade_key,
    weak_quick_subset,
)
from f05_failed_reclaim_portfolio_v1.portfolio import (
    apply_candidate,
    fold_replays,
    grouped_net,
    simulate,
)
from f05_failed_reclaim_portfolio_v1.raw_ticks import audit_2024_events

REPORT_SHA = "489a2484be135209fd731951990e508b67d6ff11cd2aeff3a4fbac23dffdfad5"
BUNDLE_SHA = "463850652d08f7c3d6b170a345ba92a1f7228c9efb24eb0f89f90b13a59b686d"
MANIFEST_SHA = "648282bed25cb5cf93fed7c16a0878f55565146849adfb6e3d92d3e47ff0e668"
SOURCE_SHA = {
    "m15_2023": "4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78",
    "m1_2023": "167509bde6553a468ffe48b082ed79de183cc57991f668cf4b3e7341350d307e",
    "events_2024h1": "9560d6382e2457eaec83415316fb59d4989244d49c9977ce76cbdd717f32f09a",
    "events_2024h2": "a5a871d7105c6e68548e804c9ab517ee6bc0b08553474b158799f47ebd32edcd",
    "m1_2024": "f9f56be2daa39f07dc39cec197306fb87821ead01e4a640a73f17715bf27dde0",
}
FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]
DIRECT_ONLY_KEY = "F05|2023-06-08T15:45:00Z|-1"


def _json_sha(path: Path) -> str:
    value = json.loads(path.read_text(encoding="utf-8"))
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def verify_protocol(path: Path) -> dict[str, object]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    assert protocol["schema_version"] == "f05_failed_reclaim_portfolio_validation_protocol_v1"
    assert protocol["status"] == "FROZEN_BEFORE_OUTCOME_EXECUTION"
    assert protocol["binding_candidate"] == "F05_FAILED_RECLAIM_BASIC_V1"
    assert protocol["non_binding_sensitivity"] == "F05_FAILED_RECLAIM_WEAK_QUICK_V1"
    assert protocol["candidate_count"] == 2
    assert protocol["binding_candidate_count"] == 1
    boundaries = protocol["boundaries"]
    assert boundaries["mt4_accessed"] is False
    assert boundaries["2025H1_accessed"] is False
    assert boundaries["2025H2_accessed"] is False
    assert boundaries["notion_task_dependency"] is False
    return protocol


def verify_exact_source(report: Path, bundle: Path, manifest: Path) -> dict[str, object]:
    actual = {
        "report_sha256": sha256_file(report),
        "bundle_sha256": sha256_file(bundle),
        "manifest_canonical_sha256": _json_sha(manifest),
    }
    assert actual["report_sha256"] == REPORT_SHA, actual
    assert actual["bundle_sha256"] == BUNDLE_SHA, actual
    assert actual["manifest_canonical_sha256"] == MANIFEST_SHA, actual
    repository_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    with zipfile.ZipFile(bundle) as archive:
        archive.testzip()
        manifest_names = [name for name in archive.namelist() if name.endswith("manifest.json")]
        assert manifest_names, archive.namelist()
        embedded = json.loads(archive.read(manifest_names[0]).decode("utf-8"))
    assert embedded == repository_manifest
    actual["embedded_manifest_matches_repository_manifest"] = True
    return actual


def load_authorities(
    m15_2023: Path,
    m1_2023: Path,
    events_2024h1: Path,
    events_2024h2: Path,
    m1_2024: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    actual = {
        "m15_2023": sha256_file(m15_2023),
        "m1_2023": sha256_file(m1_2023),
        "events_2024h1": sha256_file(events_2024h1),
        "events_2024h2": sha256_file(events_2024h2),
        "m1_2024": sha256_file(m1_2024),
    }
    assert actual == SOURCE_SHA, (actual, SOURCE_SHA)
    trades = pd.concat(
        [
            historical_2023_trades(load_2023_m15(m15_2023)),
            parse_event_trades(events_2024h1, "2024H1", False),
            parse_event_trades(events_2024h2, "2024H2", True),
        ],
        ignore_index=True,
    ).sort_values(["fold", "entry_utc", "strategy"], kind="mergesort").reset_index(drop=True)
    counts = {
        fold: {strategy: int(n) for strategy, n in group.groupby("strategy").size().items()}
        for fold, group in trades.groupby("fold")
    }
    assert len(trades) == 1882 and counts == EXPECTED_COUNTS, (len(trades), counts)
    trades["trade_id"] = [trade_key(row) for row in trades.itertuples(index=False)]
    assert not trades.trade_id.duplicated().any()
    m23, m24 = load_m1(m1_2023, m1_2024)
    return trades, m23, m24


def _metric_compare(candidate: dict[str, object], baseline: dict[str, object]) -> bool:
    return bool(
        float(candidate["net_pips"]) >= float(baseline["net_pips"]) - 1.0e-9
        and float(candidate["realized_balance_max_drawdown_jpy"])
        <= float(baseline["realized_balance_max_drawdown_jpy"]) + 1.0e-9
    )


def _fold_gate(candidate: dict[str, dict[str, object]], baseline: dict[str, dict[str, object]]) -> tuple[bool, dict[str, bool]]:
    cells = {fold: _metric_compare(candidate[fold], baseline[fold]) for fold in FOLDS}
    return all(cells.values()), cells


def _serializable_metrics(metrics: dict[str, object]) -> dict[str, object]:
    result = dict(metrics)
    if result.get("profit_factor") == float("inf"):
        result["profit_factor"] = "Infinity"
    return result


def run_evaluation(
    *,
    protocol_path: Path,
    report: Path,
    bundle: Path,
    manifest: Path,
    m15_2023: Path,
    m1_2023: Path,
    events_2024h1: Path,
    events_2024h2: Path,
    m1_2024: Path,
    raw_tick_root: Path,
    out_dir: Path,
    research_commit: str,
    workflow_run_id: str,
    workflow_run_attempt: str,
) -> dict[str, object]:
    protocol = verify_protocol(protocol_path)
    source_identity = verify_exact_source(report, bundle, manifest)
    trades, m23, m24 = load_authorities(m15_2023, m1_2023, events_2024h1, events_2024h2, m1_2024)
    m5_2023 = aggregate_bars(m23, 5)
    m5_2024 = aggregate_bars(m24, 5)

    exploration = derive_event_ledger(
        trades, m23, m24, m5_2023, m5_2024, allow_same_time_m5=True
    )
    direct_pre_raw = derive_event_ledger(
        trades, m23, m24, m5_2023, m5_2024, allow_same_time_m5=False
    )
    exploration_summary = summarize_reproduction(exploration)
    direct_summary = summarize_reproduction(direct_pre_raw)
    reproduction_pass = bool(
        exploration_summary["stopped_trades"] == 14
        and exploration_summary["total_delta_pips"] == 202.1
        and exploration_summary["long_delta_pips"] == 65.2
        and exploration_summary["short_delta_pips"] == 136.9
    )
    direct_identity_pass = bool(
        direct_summary["stopped_trades"] == 15
        and direct_summary["total_delta_pips"] == 200.6
        and set(direct_pre_raw.trade_id).difference(set(exploration.trade_id)) == {DIRECT_ONLY_KEY}
    )
    if not reproduction_pass or not direct_identity_pass:
        raise RuntimeError(
            f"technical reproduction stop: exploration={exploration_summary}, direct={direct_summary}"
        )

    direct_2023 = direct_pre_raw[pd.to_datetime(direct_pre_raw.entry_utc, utc=True).dt.year == 2023].copy()
    direct_2024 = direct_pre_raw[pd.to_datetime(direct_pre_raw.entry_utc, utc=True).dt.year == 2024].copy()
    raw_armed, raw_audit = audit_2024_events(direct_2024, raw_tick_root)
    binding = pd.concat([direct_2023, raw_armed], ignore_index=True, sort=False).sort_values(
        ["entry_utc", "trade_id"], kind="mergesort"
    ).reset_index(drop=True)
    weak = weak_quick_subset(binding)
    raw_event_order_pass = bool(
        len(raw_audit) == len(direct_2024)
        and not raw_audit.empty
        and raw_audit.event_order_pass.astype(bool).all()
    )

    baseline_trades = apply_candidate(trades, pd.DataFrame())
    candidate_trades = apply_candidate(trades, binding)
    severe_trades = apply_candidate(trades, binding, extra_exit_cost_pips=1.0)
    weak_trades = apply_candidate(trades, weak)

    baseline_metrics, baseline_curve, baseline_realized = simulate(baseline_trades, m23, m24)
    candidate_metrics, candidate_curve, candidate_realized = simulate(candidate_trades, m23, m24)
    severe_metrics, severe_curve, severe_realized = simulate(severe_trades, m23, m24)
    weak_metrics, weak_curve, weak_realized = simulate(weak_trades, m23, m24)

    baseline_folds = fold_replays(baseline_trades, m23, m24)
    candidate_folds = fold_replays(candidate_trades, m23, m24)
    severe_folds = fold_replays(severe_trades, m23, m24)
    fold_pass, fold_cells = _fold_gate(candidate_folds, baseline_folds)
    severe_pass, severe_cells = _fold_gate(severe_folds, baseline_folds)

    baseline_direction = grouped_net(baseline_trades, "side")
    candidate_direction = grouped_net(candidate_trades, "side")
    direction_cells = {
        side: candidate_direction.get(side, 0.0) >= baseline_direction.get(side, 0.0) - 1.0e-9
        for side in ["-1", "1"]
    }
    direction_pass = all(direction_cells.values())

    winner_damage = r1(
        binding.loc[
            (binding.baseline_pips.astype(float) > 0.0) & (binding.delta_pips.astype(float) < 0.0),
            "delta_pips",
        ].sum()
    ) if not binding.empty else 0.0
    winner_damage_pass = bool(abs(min(winner_damage, 0.0)) <= 300.0)

    cell_delta = binding.groupby(["fold", "side"]).delta_pips.sum() if not binding.empty else pd.Series(dtype=float)
    positive_cells = int((cell_delta > 0.0).sum())
    fold_trigger_counts = binding.groupby("fold").size().reindex(FOLDS, fill_value=0) if not binding.empty else pd.Series(0, index=FOLDS)
    breadth_pass = bool(
        positive_cells >= 7
        and all(int(fold_trigger_counts[fold]) >= 3 for fold in FOLDS)
    )

    admission_pass = bool(
        baseline_metrics["admitted_trades"] == 1882
        and candidate_metrics["admitted_trades"] == 1882
        and candidate_metrics["denied_trades"] <= baseline_metrics["denied_trades"]
        and not (
            candidate_metrics["stopout_breached"]
            and not baseline_metrics["stopout_breached"]
        )
    )
    overall_pass = _metric_compare(candidate_metrics, baseline_metrics)
    gates = {
        "exploration_reproduction_gate": reproduction_pass,
        "direct_spec_identity_gate": direct_identity_pass,
        "raw_tick_event_order_gate": raw_event_order_pass,
        "portfolio_overall_no_worse_gate": overall_pass,
        "fold_no_worse_gate": fold_pass,
        "severe_cost_no_worse_gate": severe_pass,
        "direction_no_worse_gate": direction_pass,
        "winner_damage_gate": winner_damage_pass,
        "breadth_and_minimum_trigger_gate": breadth_pass,
        "admission_margin_stopout_gate": admission_pass,
    }
    scientific_pass = all(gates.values())

    out_dir.mkdir(parents=True, exist_ok=True)
    time_columns = [
        "signal_utc", "entry_utc", "close_utc", "baseline_exit_utc", "trigger_utc",
        "candidate_exit_utc", "reclaim_utc", "first_m5_completion_utc", "timestamp_utc",
        "exit_utc", "first_positive_tick_utc",
    ]
    source_out = trades.copy()
    for column in ["signal_utc", "entry_utc", "close_utc"]:
        source_out[column] = pd.to_datetime(source_out[column], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    source_out.to_csv(out_dir / "f05_failed_reclaim_source_trade_ledger_v1.csv", index=False, lineterminator="\n")
    stringify_times(exploration, time_columns).to_csv(out_dir / "f05_failed_reclaim_exploration_reproduction_ledger_v1.csv", index=False, lineterminator="\n")
    stringify_times(direct_pre_raw, time_columns).to_csv(out_dir / "f05_failed_reclaim_direct_spec_pre_raw_ledger_v1.csv", index=False, lineterminator="\n")
    stringify_times(raw_audit, time_columns).to_csv(out_dir / "f05_failed_reclaim_raw_tick_audit_v1.csv", index=False, lineterminator="\n")
    stringify_times(binding, time_columns).to_csv(out_dir / "f05_failed_reclaim_binding_ledger_v1.csv", index=False, lineterminator="\n")
    stringify_times(weak, time_columns).to_csv(out_dir / "f05_failed_reclaim_weak_quick_sensitivity_ledger_v1.csv", index=False, lineterminator="\n")
    stringify_times(baseline_curve, time_columns).to_csv(out_dir / "f05_failed_reclaim_baseline_portfolio_curve_v1.csv", index=False, lineterminator="\n")
    stringify_times(candidate_curve, time_columns).to_csv(out_dir / "f05_failed_reclaim_candidate_portfolio_curve_v1.csv", index=False, lineterminator="\n")
    stringify_times(severe_curve, time_columns).to_csv(out_dir / "f05_failed_reclaim_severe_portfolio_curve_v1.csv", index=False, lineterminator="\n")
    stringify_times(weak_curve, time_columns).to_csv(out_dir / "f05_failed_reclaim_weak_quick_portfolio_curve_v1.csv", index=False, lineterminator="\n")

    gate_rows = [{"gate": key, "pass": bool(value)} for key, value in gates.items()]
    pd.DataFrame(gate_rows).to_csv(out_dir / "f05_failed_reclaim_gate_matrix_v1.csv", index=False, lineterminator="\n")

    result = {
        "schema_version": "f05_failed_reclaim_portfolio_validation_result_v1",
        "status": "PASS" if scientific_pass else "FAIL",
        "binding_candidate": "F05_FAILED_RECLAIM_BASIC_V1",
        "non_binding_sensitivity": "F05_FAILED_RECLAIM_WEAK_QUICK_V1",
        "research_commit": research_commit,
        "workflow_run_id": int(workflow_run_id),
        "workflow_run_attempt": int(workflow_run_attempt),
        "source_identity": source_identity,
        "source_sha256": SOURCE_SHA,
        "population": {
            "accepted_signals": 1882,
            "counts": EXPECTED_COUNTS,
            "binding_trigger_count": int(len(binding)),
            "weak_quick_trigger_count": int(len(weak)),
            "raw_audit_count": int(len(raw_audit)),
            "raw_months_needed": sorted(set(raw_audit.month.astype(str))) if not raw_audit.empty else [],
        },
        "reproduction": {
            "exploration": exploration_summary,
            "direct_pre_raw": direct_summary,
            "direct_only_trade_key": DIRECT_ONLY_KEY,
        },
        "portfolio": {
            "baseline": _serializable_metrics(baseline_metrics),
            "candidate": _serializable_metrics(candidate_metrics),
            "severe_cost": _serializable_metrics(severe_metrics),
            "weak_quick_non_binding": _serializable_metrics(weak_metrics),
            "baseline_folds": {k: _serializable_metrics(v) for k, v in baseline_folds.items()},
            "candidate_folds": {k: _serializable_metrics(v) for k, v in candidate_folds.items()},
            "severe_folds": {k: _serializable_metrics(v) for k, v in severe_folds.items()},
            "baseline_direction_net_pips": baseline_direction,
            "candidate_direction_net_pips": candidate_direction,
        },
        "diagnostics": {
            "winner_damage_pips": winner_damage,
            "positive_fold_direction_cells": positive_cells,
            "fold_trigger_counts": {fold: int(fold_trigger_counts[fold]) for fold in FOLDS},
            "fold_gate_cells": fold_cells,
            "severe_gate_cells": severe_cells,
            "direction_gate_cells": direction_cells,
        },
        "gates": gates,
        "decision": {
            "research_finalist": "F05_FAILED_RECLAIM_BASIC_V1" if scientific_pass else None,
            "mt4_authorized": bool(scientific_pass),
            "2025H1_authorized": False,
            "weak_quick_can_promote": False,
        },
        "boundaries": {
            "portfolio_replay_computed": True,
            "mt4_accessed": False,
            "2025H1_accessed": False,
            "2025H2_accessed": False,
            "notion_used_as_task_source": False,
            "candidate_or_gate_changed_after_outcomes": False,
        },
    }
    result_path = out_dir / "f05_failed_reclaim_portfolio_validation_result_v1.json"
    write_json(result_path, result)
    manifest_out = {
        "schema_version": "f05_failed_reclaim_portfolio_output_manifest_v1",
        "files": {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sorted(out_dir.iterdir()) if path.is_file()
        },
    }
    write_json(out_dir / "f05_failed_reclaim_output_manifest_v1.json", manifest_out)
    return result
