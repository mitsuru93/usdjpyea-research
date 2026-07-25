#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.research_platform.event_model_v1 import (  # noqa: E402
    SCHEMA_VERSION as EVENT_SCHEMA,
    TradeEvent,
    TradeIdentity,
    deterministic_record_sha256,
    validate_event_stream,
)
from tools.research_platform.experiment_contract_v1 import (  # noqa: E402
    ExperimentContract,
    SCHEMA_VERSION as EXPERIMENT_SCHEMA,
)
from tools.research_platform.result_adapter_v1 import (  # noqa: E402
    load_lifecycle_candidate_summary,
    rank_candidates,
)
from tools.research_platform.source_inventory_v1 import (  # noqa: E402
    SCHEMA_VERSION as INVENTORY_SCHEMA,
    collection_required,
    deterministic_inventory_sha256,
    inspect_repository_file,
    load_inventory,
)
from tools.research_platform.transition_rules_v1 import (  # noqa: E402
    assess_f05_failed_reclaim,
)


def test_event_stream() -> None:
    identity = TradeIdentity("B02-001", "B02", "BUY", "2024H1", "2024-01-02T00:00:00Z", 140.0)
    events = [
        TradeEvent("B02-001", 0, "ENTRY", "2024-01-02T00:00:00Z", 0, 0.0, 0.0, 0.0, {}),
        TradeEvent("B02-001", 1, "INITIAL_ADVERSE", "2024-01-02T00:00:01Z", 1000, -0.2, 0.0, 0.2, {"spread_pips": 0.5}),
        TradeEvent("B02-001", 2, "BREAKOUT_ESTABLISHED", "2024-01-02T00:00:03Z", 3000, 1.0, 1.0, 0.2, {"outside_ms": 2000}),
    ]
    assert len(validate_event_stream(identity, events)) == 3
    assert deterministic_record_sha256(identity, events) == deterministic_record_sha256(identity, events)


def test_rejects_non_monotonic_event() -> None:
    identity = TradeIdentity("F05-001", "F05", "SELL", "2023H2", "2023-07-03T00:00:00Z", 145.0)
    events = [
        TradeEvent("F05-001", 0, "ENTRY", "2023-07-03T00:00:00Z", 0, 0.0, 0.0, 0.0, {}),
        TradeEvent("F05-001", 1, "BAD", "2023-07-02T23:59:59Z", 1, 0.0, 0.0, 0.0, {}),
    ]
    try:
        validate_event_stream(identity, events)
    except ValueError:
        return
    raise AssertionError("non-monotonic event was accepted")


def test_experiment_contract() -> None:
    payload = {
        "schema_version": EXPERIMENT_SCHEMA,
        "experiment_id": "EXP-PLATFORM-SMOKE-001",
        "hypothesis_id": "HYP-SMOKE-001",
        "strategies": ["B02", "F05"],
        "periods": ["2023H1", "2023H2", "2024H1", "2024H2"],
        "dataset_sha256": "0" * 64,
        "code_sha": "test",
        "event_schema_version": EVENT_SCHEMA,
        "analysis_family": "state_transition",
        "parameters": {"outside_ms": 2000},
        "expected_mechanism": "breakout establishment separates immediate failure paths",
        "primary_endpoint": "initial_loss_path_rate",
        "falsification_rule": "reject when effect direction is inconsistent across three or more folds"
    }
    with TemporaryDirectory() as directory:
        path = Path(directory) / "contract.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        contract = ExperimentContract.from_json(path)
        assert len(contract.contract_sha256()) == 64


def test_source_inventory() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        fixture = root / "fixture.csv"
        fixture.write_text("id,value\n1,a\n2,b\n", encoding="utf-8")
        payload = {
            "schema_version": INVENTORY_SCHEMA,
            "sources": [
                {
                    "source_id": "fixture",
                    "kind": "repository_file",
                    "state": "available",
                    "locator": "fixture.csv",
                    "rows": 2,
                    "notes": "test"
                },
                {
                    "source_id": "release",
                    "kind": "release",
                    "state": "declared",
                    "locator": "accepted-release",
                    "notes": "test"
                }
            ]
        }
        inventory_path = root / "inventory.json"
        inventory_path.write_text(json.dumps(payload), encoding="utf-8")
        records = load_inventory(inventory_path)
        assert len(deterministic_inventory_sha256(records)) == 64
        inspection = inspect_repository_file(root, records[0])
        assert inspection["exists"] is True
        assert inspection["data_rows"] == 2
        assert inspection["row_match"] is True
        assert collection_required(records) is False


def test_lifecycle_result_adapter() -> None:
    fieldnames = [
        "candidate_id", "stage", "fold_pass_count", "all_four_folds_pass",
        "pooled_default_delta_pips", "pooled_severe_delta_pips",
        "minimum_fold_default_delta_pips", "minimum_fold_severe_delta_pips",
        "minimum_top10_retention", "minimum_top5_retention", "passing_folds",
        "pooled_rank_within_stage"
    ]
    rows = [
        ["CANDIDATE_B", "B", 1, "False", 10.0, 8.0, -1.0, -2.0, 0.90, 0.80, "2023H1", 2],
        ["CANDIDATE_A", "A", 4, "True", 5.0, 4.0, 0.5, 0.2, 0.95, 0.85, "2023H1|2023H2|2024H1|2024H2", 1],
    ]
    with TemporaryDirectory() as directory:
        path = Path(directory) / "summary.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(fieldnames)
            writer.writerows(rows)
        records = load_lifecycle_candidate_summary(path)
        ranked = rank_candidates(records)
        assert ranked[0].candidate_id == "CANDIDATE_A"
        assert ranked[0].all_four_folds_pass is True


def test_failed_reclaim_transition_rules() -> None:
    trade_id = "F05-TRANSITION-001"
    events = [
        TradeEvent(trade_id, 0, "ENTRY", "2024-01-02T00:00:00Z", 0, 0.0, 0.0, 0.0, {}),
        TradeEvent(trade_id, 1, "INITIAL_FAILURE_ARMED", "2024-01-02T00:05:00Z", 300000, -1.0, 0.0, 1.0, {}),
        TradeEvent(trade_id, 2, "INITIAL_REENTRY", "2024-01-02T00:05:00Z", 300000, -2.1, 0.0, 2.1, {}),
        TradeEvent(trade_id, 3, "FIRST_RECLAIM", "2024-01-02T00:06:00Z", 360000, -0.1, 0.0, 2.1, {}),
        TradeEvent(trade_id, 4, "RECLAIM_FAILURE", "2024-01-02T00:10:00Z", 600000, -1.4, 0.0, 2.1, {}),
        TradeEvent(trade_id, 5, "CANDIDATE_EXIT", "2024-01-02T00:11:00Z", 660000, -1.5, 0.0, 2.1, {}),
    ]
    result = assess_f05_failed_reclaim(events)
    assert result.valid is True
    assert result.terminal_state == "CANDIDATE_EXIT"

    disarmed = events[:3] + [
        TradeEvent(trade_id, 3, "PROFIT_DISARM", "2024-01-02T00:06:00Z", 360000, 0.1, 0.1, 2.1, {})
    ]
    result = assess_f05_failed_reclaim(disarmed)
    assert result.valid is True
    assert result.terminal_state == "PROFIT_DISARMED"


def main() -> None:
    test_event_stream()
    test_rejects_non_monotonic_event()
    test_experiment_contract()
    test_source_inventory()
    test_lifecycle_result_adapter()
    test_failed_reclaim_transition_rules()
    print("research platform v1 tests: PASS")


if __name__ == "__main__":
    main()
