#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.research_platform.factor_analysis_v1 import (  # noqa: E402
    TradeObservation,
    aggregate_observations,
    analyze_categorical_factor,
    analyze_numeric_factor,
    deterministic_analysis_sha256,
)


def fixture() -> list[TradeObservation]:
    return [
        TradeObservation("T1", "2023H1", "B02", "BUY", "P1", -4.0, {"atr": 0.7, "session": "Tokyo"}),
        TradeObservation("T2", "2023H1", "B02", "BUY", "P1", 2.0, {"atr": 1.2, "session": "London"}),
        TradeObservation("T3", "2023H2", "B02", "SELL", "P2", -2.0, {"atr": 0.8, "session": "Tokyo"}),
        TradeObservation("T4", "2023H2", "B02", "SELL", "P2", 4.0, {"atr": 1.3, "session": "London"}),
        TradeObservation("T5", "2024H1", "F05", "BUY", "P3", -1.0, {"atr": 0.9, "session": "Tokyo"}),
        TradeObservation("T6", "2024H1", "F05", "BUY", "P3", 5.0, {"atr": 1.4, "session": "London"}),
        TradeObservation("T7", "2024H2", "F05", "SELL", "P3", -3.0, {"atr": 1.0, "session": "Tokyo"}),
        TradeObservation("T8", "2024H2", "F05", "SELL", "P3", 3.0, {"atr": 1.5, "session": "London"}),
    ]


def test_group_aggregation() -> None:
    summaries = aggregate_observations(fixture(), dimensions=("period", "strategy"))
    assert len(summaries) == 4
    assert sum(item.trade_count for item in summaries) == 8
    assert summaries[0].dimensions == {"period": "2023H1", "strategy": "B02"}


def test_numeric_factor() -> None:
    contrast = analyze_numeric_factor(fixture(), "atr", threshold=1.0, permutation_iterations=199, seed=7)
    assert contrast.low_count == 4
    assert contrast.high_count == 4
    assert contrast.mean_delta_pips > 0
    assert contrast.direction_consistent_folds == contrast.eligible_fold_count == 4
    assert contrast.permutation_p_value is not None
    assert 0 < contrast.permutation_p_value <= 1


def test_categorical_factor() -> None:
    levels = analyze_categorical_factor(fixture(), "session")
    by_level = {item.level: item for item in levels}
    assert set(by_level) == {"London", "Tokyo"}
    assert by_level["London"].mean_outcome_pips > by_level["Tokyo"].mean_outcome_pips


def test_deterministic_hash() -> None:
    payload = [asdict(item) for item in aggregate_observations(fixture(), dimensions=("strategy", "side"))]
    assert deterministic_analysis_sha256(payload) == deterministic_analysis_sha256(payload)
    assert len(deterministic_analysis_sha256(payload)) == 64


def main() -> None:
    test_group_aggregation()
    test_numeric_factor()
    test_categorical_factor()
    test_deterministic_hash()
    print("factor analysis v1 tests: PASS")


if __name__ == "__main__":
    main()
