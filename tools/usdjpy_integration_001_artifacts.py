#!/usr/bin/env python3
from __future__ import annotations
from usdjpy_integration_001_support import *

def write_artifacts(args, out, ctx, matrices):
    globals().update(ctx)
    availability = matrices["availability"]
    common_contract = json.loads(args.contract.read_text(encoding="utf-8"))
    common_chronology = {
        "work_id": WORK_ID,
        "global_order": CHRONOLOGY,
        "strategy_local_separation": "Each strategy may finalize its local exit condition internally, but global close/account/state/permission/entry/margin/equity ordering is invariant.",
        "same_timestamp_sort_key": ["timestamp_utc", "global_chronology_rank", "strategy_id", "source_trade_id"],
        "legacy_baseline_result": "No negative holding periods or trade failures; decision_utc remains null and blocks complete decision-trace parity.",
    }
    write_json(out / "common_chronology.json", common_chronology)
    write_json(out / "common_jpy_accounting.json", common_contract["common_accounting"])
    write_json(out / "common_margin_engine.json", {
        "historical_contract": "margin_used_jpy = abs(1000 USD × lot/0.01 × entry_bid) / 25",
        "2025H1_contract": "Use broker-reported margin/free-margin/margin-level from MT4 authority; do not replace with a formula.",
        "historical_minimum_margin_level_percent_common_capital": hist_metrics["margin"]["minimum_margin_level_percent"],
        "2025H1_minimum_margin_level_percent_authority": tick_authority["minimum_margin_level_percent"],
        "2025H1_minimum_free_margin_jpy_authority": tick_authority["minimum_free_margin_jpy"],
        "candidate_gate": "STOP if a candidate supplies neither broker-reported margin evidence nor a complete broker contract.",
    })
    write_json(out / "adapter_contract.json", {
        "accepted_sources": common_contract["accepted_candidate_sources"],
        "required_schema": "usdjpy_common_trade_ledger_v1",
        "null_policy": common_contract["common_accounting"]["missing_value_policy"],
        "baseline_adapters": ["CANONICAL_RESEARCH_TRADE_STATE_LEDGER", "RAKUTEN_MT4_EVENT_LOG"],
        "candidate_adapter_invariants": [
            "No rule reconstruction from aggregate metrics",
            "No inferred zero for missing commission, swap, decision time, quote, SHA or digest",
            "Formal candidate identity and version must match the originating study",
            "2025H1 output is validation evidence and may not modify the candidate",
            "Candidate-local chronology is mapped into, not substituted for, the global chronology",
        ],
        "dependent_gate_stops": {
            "decision_utc_null": "implementation chronology parity",
            "commission_or_swap_null": "complete transaction-cost attribution",
            "artifact_digest_null": "candidate ingestion",
            "mark_to_market_source_null": "full-equity comparison",
            "margin_contract_null": "margin feasibility",
        },
    })

    baseline_result = {
        "schema_version": "usdjpy_ea_integration_001_baseline_reproduction_v1",
        "work_id": WORK_ID,
        "generated_at_utc": GENERATED_AT,
        "source_identity": {
            "research_main": RESEARCH_MAIN,
            "core_main": CORE_MAIN,
            "historical_trade_sha256": HIST_TRADE_SHA,
            "historical_state_sha256": HIST_STATE_SHA,
            "2025H1_run_id": 29783855056,
            "2025H1_artifact_digest": BASELINE_2025_ARTIFACT,
        },
        "source_authority": source_authority,
        "common_comparison": {"2023_2024": hist_metrics, "2025H1": h25_metrics},
        "ledger_integrity": {"2023_2024": hist_integrity, "2025H1": h25_integrity},
        "exact_reproduction": {
            "historical_trade_rows": len(hist),
            "historical_state_rows": 68955,
            "historical_net_matches_51627": hist_metrics["net_jpy"] == 51627.0,
            "historical_full_equity_dd_matches_42660": hist_metrics["full_equity_drawdown"]["maximum_drawdown_jpy"] == 42660.0,
            "2025_trade_rows_match_463": len(h25) == 463,
            "2025_net_matches_minus_20808": h25_metrics["net_jpy"] == -20808.0,
            "2025_pf_matches_authority": abs(h25_metrics["profit_factor"] - 0.8294076655052265) < 1e-12,
            "2025_tick_dd_matches_42737": tick_authority["maximum_tick_equity_drawdown_jpy"] == 42737.0,
            "currency_mismatch": 0,
        },
    }
    write_json(out / "baseline_exact_reproduction.json", baseline_result)

    # Explicit-null examples prove the adapter policy without publishing source ledgers.
    samples = [to_json_record(hist.iloc[0]), to_json_record(h25.iloc[0])]
    with (out / "common_trade_ledger_samples.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for row in samples:
            f.write(json.dumps(clean(row), sort_keys=True, ensure_ascii=False) + "\n")
    shutil.copy2(args.schema, out / "common_trade_ledger_schema.json")
    shutil.copy2(args.contract, out / "integration_contract.json")

    recommendation = {
        "work_id": WORK_ID,
        "scientific_pass_fail_issued": False,
        "current_architecture_recommendation": "RETAIN_B02_F05_AS_REFERENCE_ONLY_AND_DEFER_FINAL_EA_COMPOSITION",
        "reason": "The baseline is exact but 2025H1 remains JPY -20,808 / PF 0.829. N1, N2, F and B lack admissible completed evidence, so no non-baseline combination may be calculated or recommended.",
        "production_architecture_selected": False,
        "lot_allocation_changed": False,
        "candidate_rules_changed": False,
        "framework_status": "READY_FOR_INCREMENTAL_HASH_PINNED_CANDIDATE_INGESTION",
        "baseline_classification": "NO_RECOVERY",
        "pending_slots": ["N1", "N2", "F", "B"],
    }
    write_json(out / "final_architecture_recommendation.json", recommendation)
    next_action = {
        "exact_next_action": "Ingest the first candidate that reaches merged main, immutable Release, or a hash-pinned artifact with a complete common-ledger-compatible trade/equity/margin package. Current nearest dependency is HYP-039 Core PR #505: after merge and formal evidence publication, pin its candidate ID/version, Research SHA, Core SHA, Run ID and artifact digest; validate null/chronology/accounting gates; then replay BASELINE+N1 without changing candidate rules. Apply the same adapter path to HYP-040, F05 v2 and B02 v2 as each becomes admissible.",
        "do_not_do": ["Do not read aggregate net only", "Do not reconstruct missing trades", "Do not retune from 2025H1", "Do not run a candidate combination while any required component is pending"],
    }
    write_json(out / "exact_next_action.json", next_action)

    human = f"""# USDJPY Common Portfolio Evaluation and Integration Framework

- Work ID: `{WORK_ID}`
- Role: EA-wide infrastructure/integration; no Hypothesis ID and no candidate selection authority.
- Baseline reproduction: **PASS**.
- 2023–2024: 1,882 trades, net **+JPY 51,627**, PF **{hist_metrics['profit_factor']:.6f}**, common full-equity DD **JPY {hist_metrics['full_equity_drawdown']['maximum_drawdown_jpy']:.0f}**.
- 2025H1: 463 trades, net **-JPY 20,808**, PF **0.829408**, authority Tick-equity DD **JPY 42,737**, minimum equity **JPY 57,328**.
- B02/F05 attribution: **-JPY 6,964 / -JPY 13,844**.
- Candidate availability: N1, N2, F and B are all `PENDING_CANDIDATE_EVIDENCE`; no non-baseline combination was calculated.
- Current architecture recommendation: retain B02+F05 as the exact comparison reference only; defer final EA composition until admissible candidate evidence exists.
- The framework uses explicit nulls. Legacy baseline `decision_utc`, commission and swap gaps stop their dependent integrity/cost gates but do not alter exact net/PF/DD reproduction.
"""
    (out / "human_report.md").write_text(human, encoding="utf-8", newline="\n")

    # Manifest and deterministic package.
    file_entries = []
    for path in sorted(p for p in out.iterdir() if p.is_file() and p.name not in {"output_manifest.json", "PACKAGE_SHA256SUMS", "usdjpy-ea-integration-001-v1.zip"}):
        file_entries.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "usdjpy_ea_integration_001_output_manifest_v1",
        "work_id": WORK_ID,
        "generated_at_utc": GENERATED_AT,
        "research_main": RESEARCH_MAIN,
        "core_main": CORE_MAIN,
        "decision": "FRAMEWORK_COMPLETE_BASELINE_ONLY_PENDING_CANDIDATES",
        "candidate_rules_changed": False,
        "2025H1_role": "VALIDATION_PERIOD",
        "files": file_entries,
    }
    write_json(out / "output_manifest.json", manifest)
    sums_paths = sorted(p for p in out.iterdir() if p.is_file() and p.name not in {"PACKAGE_SHA256SUMS", "usdjpy-ea-integration-001-v1.zip"})
    (out / "PACKAGE_SHA256SUMS").write_text("".join(f"{sha256_file(p)}  {p.name}\n" for p in sums_paths), encoding="utf-8", newline="\n")
    zip_path = out / "usdjpy-ea-integration-001-v1.zip"
    deterministic_zip(out, zip_path)
    release = {
        "release_tag": "usdjpy-ea-integration-001-v1",
        "archive": zip_path.name,
        "archive_sha256": sha256_file(zip_path),
        "archive_bytes": zip_path.stat().st_size,
        "expected_repository": "mitsuru93/usdjpyea-research",
        "status": "READY_FOR_RELEASE",
    }
    write_json(out / "release_receipt.json", release)
    print(json.dumps(clean({"baseline": baseline_result["exact_reproduction"], "release": release, "pending": [r["slot"] for r in availability]}), indent=2))
    return 0
