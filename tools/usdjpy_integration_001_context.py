#!/usr/bin/env python3
from __future__ import annotations
from usdjpy_integration_001_support import *

def build_context(args, out):
    if sha256_file(args.historical_trades) != HIST_TRADE_SHA:
        raise ValueError("historical trade authority SHA mismatch")
    if sha256_file(args.historical_states) != HIST_STATE_SHA:
        raise ValueError("historical state authority SHA mismatch")

    period_core_sha = {
        "2023H1": None,
        "2023H2": None,
        "2024H1": "8a6ad1ac1ac357e85ceaa1f9e62549105ae555d8",
        "2024H2": "e1100e91f5f587f17932bb7b04b982bbdf1de078",
    }
    period_run_id = {"2023H1": 29997167048, "2023H2": 29997167048, "2024H1": 29787357305, "2024H2": 29873856877}
    period_digest = {
        "2023H1": "sha256:22d66bf76c60362b78e9badff2113bc196b80e3657f5083ae470d1d62df70c01",
        "2023H2": "sha256:22d66bf76c60362b78e9badff2113bc196b80e3657f5083ae470d1d62df70c01",
        "2024H1": "sha256:e078758343995c8254244dd36385c93a61a7124cb5037beb458afdf5d0e208e5",
        "2024H2": "sha256:9c5846e8b6e47b4b981a3ceeec856391311d3864a8cd7c2bef7caf7d21e6375b",
    }
    hist = adapt_historical_baseline(args.historical_trades, HIST_RESEARCH_SHA, period_core_sha, period_run_id, period_digest)
    h25, snapshots = adapt_mt4_event_log(args.mt4_2025_events, 29783855056, "973d0c31bec66a6cf9cca913835b4d7cc6013dca", BASELINE_2025_ARTIFACT)

    hist_integrity = validate_common_ledger(hist)
    h25_integrity = validate_common_ledger(h25)

    hist_eq = historical_full_equity(hist, args.historical_states, COMMON_INITIAL_CAPITAL_JPY)
    hist_margin = margin_series_from_trades(hist, pd.DatetimeIndex(hist_eq.timestamp_utc))
    hist_margin = hist_margin.merge(hist_eq[["timestamp_utc", "equity_jpy"]], on="timestamp_utc", how="left")
    hist_margin["free_margin_jpy"] = hist_margin.equity_jpy - hist_margin.margin_used_jpy
    hist_margin["margin_level_percent"] = np.where(hist_margin.margin_used_jpy > 0, hist_margin.equity_jpy / hist_margin.margin_used_jpy * 100.0, np.nan)

    snapshots = snapshots.sort_values("timestamp_utc", kind="mergesort")
    h25_eq = pd.DataFrame({
        "timestamp_utc": snapshots.timestamp_utc,
        "realized_balance_jpy": snapshots.balance.astype(float),
        "floating_pl_jpy": snapshots.equity.astype(float) - snapshots.balance.astype(float),
        "equity_jpy": snapshots.equity.astype(float),
        "open_positions": snapshots.open_orders.astype(int),
    })
    h25_margin = pd.DataFrame({
        "timestamp_utc": snapshots.timestamp_utc,
        "margin_used_jpy": snapshots.margin.astype(float),
        "free_margin_jpy": snapshots.free_margin.astype(float),
        "margin_level_percent": snapshots.margin_level.astype(float),
        "open_lots": snapshots.open_lots.astype(float),
    })

    summary = json.loads(args.mt4_2025_summary.read_text(encoding="utf-8-sig"))
    case = next(c for c in summary["cases"] if c["id"] == "JPY100K_FIXED_001_EACH")
    tick_authority = {
        "source": "DIRECT_RAKUTEN_MT4_STRATEGY_TESTER",
        "maximum_tick_equity_drawdown_jpy": case["maximum_tick_equity_drawdown_jpy"],
        "minimum_equity_jpy": case["minimum_equity_jpy"],
        "minimum_free_margin_jpy": case["minimum_free_margin_jpy"],
        "minimum_margin_level_percent": case["minimum_margin_level_percent"],
        "maximum_open_orders": case["maximum_open_orders"],
        "maximum_open_lots": case["maximum_open_lots"],
        "stopout_breached": case["stopout_breached"],
    }

    hist_metrics = period_metrics(hist, hist_eq, COMMON_INITIAL_CAPITAL_JPY, observed_margin=hist_margin)
    h25_metrics = period_metrics(h25, h25_eq, COMMON_INITIAL_CAPITAL_JPY, observed_tick_authority=tick_authority, observed_margin=h25_margin)
    h25_metrics["maximum_concurrent_lots"] = float(case["maximum_open_lots"])
    h25_metrics["maximum_concurrent_positions"] = int(case["maximum_open_orders"])

    # Fixed authority assertions. Values are not replaced by a second accounting result.
    assert len(hist) == 1882 and abs(hist.realized_pl_jpy.sum() - 51627) < 1e-9
    assert len(h25) == 463 and abs(h25.realized_pl_jpy.sum() + 20808) < 1e-9
    assert abs((profit_factor(h25.realized_pl_jpy) or 0) - 0.8294076655052265) < 1e-12
    assert hist_metrics["full_equity_drawdown"]["maximum_drawdown_jpy"] == 42660.0
    assert hist_metrics["maximum_concurrent_positions"] == 9
    assert case["maximum_tick_equity_drawdown_jpy"] == 42737.0

    source_authority = {
        "2023_2024": {
            "source_initial_capital_jpy": 1_000_000.0,
            "net_jpy": 51627.0,
            "realized_drawdown_jpy": 40487.0,
            "full_equity_drawdown_jpy": 42660.0,
            "minimum_realized_equity_jpy": 959513.0,
            "minimum_full_equity_jpy": 959118.0,
            "maximum_concurrent_positions": 9,
            "normalization_note": "The common comparison rebases the same P/L and equity deltas to JPY 100,000 without replacing source-authority values. Drawdown is unchanged; minimum equity shifts by exactly JPY -900,000.",
        },
        "2025H1": {
            "source_initial_capital_jpy": 100000.0,
            "trades": 463,
            "net_jpy": -20808.0,
            "profit_factor": 0.8294076655052265,
            "B02_net_jpy": -6964.0,
            "F05_net_jpy": -13844.0,
            "maximum_tick_equity_drawdown_jpy": 42737.0,
            "minimum_equity_jpy": 57328.0,
        },
    }
    return {k: v for k, v in locals().items() if k not in {"args", "out"}}
