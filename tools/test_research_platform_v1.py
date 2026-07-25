#!/usr/bin/env python3
from __future__ import annotations

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


def main() -> None:
    test_event_stream()
    test_rejects_non_monotonic_event()
    test_experiment_contract()
    print("research platform v1 tests: PASS")


if __name__ == "__main__":
    main()
