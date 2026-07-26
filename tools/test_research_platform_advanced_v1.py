#!/usr/bin/env python3
from __future__ import annotations

from tools.research_platform.advanced_analysis_v1 import bootstrap_mean, interaction_analysis, matched_cohort
from tools.research_platform.event_model_v1 import TradeEvent, TradeIdentity
from tools.research_platform.factor_analysis_v1 import TradeObservation
from tools.research_platform.observation_builder_v1 import CanonicalTradeRecord, build_observation


def test_observation_builder() -> None:
    identity = TradeIdentity("T1", "F05", "BUY", "2024H1", "2024-01-01T00:00:00Z", 140.0)
    events = [
        TradeEvent("T1", 0, "ENTRY", "2024-01-01T00:00:00Z", 0, 0.0, 0.0, 0.0, {}),
        TradeEvent("T1", 1, "FIRST_RECLAIM", "2024-01-01T00:01:00Z", 60000, -0.1, 0.0, 1.0, {"distance_pips": 1.2}),
        TradeEvent("T1", 2, "BASELINE_EXIT", "2024-01-01T00:02:00Z", 120000, -2.0, 0.5, 2.0, {}),
    ]
    row = build_observation(CanonicalTradeRecord(identity, events))
    assert row.outcome_pips == -2.0
    assert row.factors["first_reclaim_distance_pips"] == 1.2


def fixture() -> list[TradeObservation]:
    rows = []
    for period in ("2023H1", "2023H2", "2024H1", "2024H2"):
        rows.extend([
            TradeObservation(period+"A", period, "F05", "BUY", "EXIT", 3.0, {"treated": True, "x": 2.0, "y": 2.0}),
            TradeObservation(period+"B", period, "F05", "BUY", "EXIT", 1.0, {"treated": False, "x": 0.0, "y": 2.0}),
            TradeObservation(period+"C", period, "F05", "SELL", "EXIT", -1.0, {"treated": True, "x": 2.0, "y": 0.0}),
            TradeObservation(period+"D", period, "F05", "SELL", "EXIT", -2.0, {"treated": False, "x": 0.0, "y": 0.0}),
        ])
    return rows


def main() -> None:
    test_observation_builder()
    interval = bootstrap_mean([1.0, 2.0, 3.0], iterations=200, seed=1)
    assert interval.lower <= interval.estimate <= interval.upper
    match = matched_cohort(fixture(), treatment_factor="treated", match_factors=("period", "strategy", "side", "state"))
    assert match.pair_count == 8
    interaction = interaction_analysis(fixture(), "x", "y", threshold_a=1.0, threshold_b=1.0)
    assert len(interaction.cells) == 4
    print("advanced research platform tests: PASS")


if __name__ == "__main__":
    main()
