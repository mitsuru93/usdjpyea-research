from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from usdjpy_common_portfolio.framework import (
    COMMON_INITIAL_CAPITAL_JPY,
    COMMON_TRADE_FIELDS,
    CHRONOLOGY,
    drawdown_details,
    profit_factor,
    recovery_classification,
    requested_combinations,
    validate_common_ledger,
)


def test_common_schema_and_contract_are_fixed() -> None:
    schema = json.loads((ROOT / "schemas/usdjpy_common_trade_ledger_v1.schema.json").read_text())
    contract = json.loads((ROOT / "configs/integration/usdjpy_ea_integration_001_contract_v1.json").read_text())
    assert schema["title"] == "USDJPY Common Trade Ledger v1"
    assert set(schema["required"]).issubset(set(COMMON_TRADE_FIELDS))
    assert contract["period_roles"]["2025H1"] == "VALIDATION_RESULT_INTEGRATION_COMPARISON"
    assert contract["common_accounting"]["comparison_initial_capital_jpy"] == COMMON_INITIAL_CAPITAL_JPY
    assert contract["common_accounting"]["missing_value_policy"] == "EXPLICIT_NULL_AND_STOP_DEPENDENT_GATE"
    assert contract["chronology"] == CHRONOLOGY
    assert contract["scientific_decision_authority"] is False


def test_baseline_result_and_candidate_pending_matrix() -> None:
    result = json.loads((ROOT / "configs/integration/usdjpy_ea_integration_001_result_v1.json").read_text())
    h = result["baseline_exact_reproduction"]["2023_2024"]
    v = result["baseline_exact_reproduction"]["2025H1"]
    assert h["trades"] == 1882
    assert h["net_jpy"] == 51627
    assert abs(h["profit_factor"] - 1.1377131303215893) < 1e-12
    assert h["full_equity_drawdown_jpy"] == 42660
    assert h["maximum_concurrent_positions"] == 9
    assert h["maximum_concurrent_lots"] == 0.09
    assert v["trades"] == 463
    assert v["net_jpy"] == -20808
    assert abs(v["profit_factor"] - 0.8294076655052265) < 1e-12
    assert v["authority_tick_equity_drawdown_jpy"] == 42737
    assert v["authority_minimum_equity_jpy"] == 57328
    assert v["B02"]["net_jpy"] == -6964
    assert v["F05"]["net_jpy"] == -13844
    assert v["classification"] == "NO_RECOVERY"
    assert {r["slot"] for r in result["candidate_availability"]} == {"N1", "N2", "F", "B"}
    assert all(r["availability"] == "PENDING_CANDIDATE_EVIDENCE" for r in result["candidate_availability"])
    assert result["candidate_rules_changed"] is False
    assert result["lot_allocation_changed"] is False


def test_numeric_primitives_and_recovery_labels() -> None:
    assert abs(profit_factor([10, 20, -5]) - 6.0) < 1e-12
    dd = drawdown_details([100000, 105000, 90000, 106000])
    assert dd["maximum_drawdown_jpy"] == 15000
    assert dd["minimum_equity_jpy"] == 90000
    base = {
        "net_jpy": -1000,
        "full_equity_drawdown": {"maximum_drawdown_jpy": 10000, "minimum_equity_jpy": 90000},
        "worst_20_business_days_jpy": -5000,
    }
    h23 = {"net_jpy": 1000, "profit_factor": 1.1}
    full = {
        "net_jpy": 100,
        "profit_factor": 1.01,
        "full_equity_drawdown": {"maximum_drawdown_jpy": 9000, "minimum_equity_jpy": 91000},
        "worst_20_business_days_jpy": -4000,
    }
    tradeoff = {
        "net_jpy": 100,
        "profit_factor": 1.01,
        "full_equity_drawdown": {"maximum_drawdown_jpy": 11000, "minimum_equity_jpy": 89000},
        "worst_20_business_days_jpy": -6000,
    }
    partial = {
        "net_jpy": -500,
        "profit_factor": 0.9,
        "full_equity_drawdown": {"maximum_drawdown_jpy": 9500, "minimum_equity_jpy": 90500},
        "worst_20_business_days_jpy": -4500,
    }
    assert recovery_classification(base, h23, full, True, True) == "FULL_RECOVERY"
    assert recovery_classification(base, h23, tradeoff, True, True) == "RETURN_RECOVERY_WITH_RISK_TRADEOFF"
    assert recovery_classification(base, h23, partial, True, True) == "PARTIAL_RECOVERY"
    assert recovery_classification(base, h23, partial, False, True) == "NO_RECOVERY"


def test_combination_list_and_null_gate() -> None:
    combos = requested_combinations()
    assert len(combos) == 15
    assert combos[0] == ("BASELINE", ["B02", "F05"])
    assert combos[-1] == ("BV2_FV2_N1_N2", ["B", "F", "N1", "N2"])
    row = {field: None for field in COMMON_TRADE_FIELDS}
    row.update({
        "source_trade_id": "X",
        "side": "LONG",
        "entry_utc": "2025-01-01T00:00:00Z",
        "exit_utc": "2025-01-01T01:00:00Z",
    })
    ledger = pd.DataFrame([row], columns=COMMON_TRADE_FIELDS)
    gate = validate_common_ledger(ledger)
    assert gate["missing_columns"] == []
    assert gate["decision_chronology_gate"] == "STOP_NULL_DECISION_UTC"
    assert gate["commission_swap_gate"] == "STOP_NULL_COST_COMPONENTS"
    assert gate["negative_holding_period_rows"] == 0
