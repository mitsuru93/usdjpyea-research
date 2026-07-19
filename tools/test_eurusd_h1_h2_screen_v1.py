#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

import pandas as pd

MODULE_PATH = Path(__file__).with_name("eurusd_h1_h2_eval_v1.py")
spec = importlib.util.spec_from_file_location("screen", MODULE_PATH)
screen = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(screen)


def synthetic_bars(n: int = 30) -> pd.DataFrame:
    ts = pd.date_range("2024-01-02T00:00:00Z", periods=n, freq="1h")
    close = pd.Series([1.10 + i * 0.0001 for i in range(n)])
    return pd.DataFrame({
        "timestamp_utc": ts,
        "symbol": "EURUSD",
        "mid_open": close - 0.00002,
        "mid_high": close + 0.00005,
        "mid_low": close - 0.00005,
        "mid_close": close,
        "spread_mean_pips": 0.4,
        "tick_count": 100,
        "date_utc": ts.strftime("%Y-%m-%d"),
        "hour_utc": ts.hour,
    })


class ScreenTests(unittest.TestCase):
    def test_registry_expands_to_46_candidates(self) -> None:
        registry = json.loads(Path("configs/research/eurusd_h1_prior_literature_candidates_v1.json").read_text())
        expanded = screen.expand_registry(registry)
        self.assertEqual(len(expanded), 46)
        self.assertEqual(len({row["id"] for row in expanded}), 46)

    def test_next_bar_entry_and_no_overlap(self) -> None:
        bars = synthetic_bars()
        candidate = {
            "id": "test",
            "family_id": "B",
            "family": "return_sign_time_series_momentum",
            "evidence_class": "test",
            "lookback_bars": 1,
            "hold_bars": 4,
            "robustness_group": "test",
        }
        costs = {"base_spread_pips": 0.6, "spread_multipliers": [1.0, 3.0], "slippage_pips_per_side": [0.0, 0.5]}
        trades = screen.build_trades(
            bars,
            candidate,
            {"hard_no_trade_windows": []},
            costs,
            pd.Timestamp("2024-01-02T00:00:00Z"),
            pd.Timestamp("2024-01-04T00:00:00Z"),
        )
        self.assertGreater(len(trades), 1)
        first = trades.iloc[0]
        self.assertEqual(first["entry_ts"], first["signal_ts"] + pd.Timedelta(hours=1))
        for previous, current in zip(trades.iloc[:-1].itertuples(), trades.iloc[1:].itertuples()):
            self.assertGreater(current.entry_ts, previous.exit_bar_ts)

    def test_cross_boundary_trade_is_excluded(self) -> None:
        bars = synthetic_bars(10)
        candidate = {
            "id": "test",
            "family_id": "B",
            "family": "return_sign_time_series_momentum",
            "evidence_class": "test",
            "lookback_bars": 1,
            "hold_bars": 4,
            "robustness_group": "test",
        }
        costs = {"base_spread_pips": 0.6, "spread_multipliers": [1.0, 3.0], "slippage_pips_per_side": [0.0, 0.5]}
        end = pd.Timestamp("2024-01-02T05:00:00Z")
        trades = screen.build_trades(bars, candidate, {"hard_no_trade_windows": []}, costs, bars.timestamp_utc.min(), end)
        self.assertTrue(trades.empty or (trades["exit_time_utc"] <= end).all())

    def test_frame_hash_is_stable_across_copy(self) -> None:
        bars = synthetic_bars()
        self.assertEqual(screen.frame_content_sha256(bars), screen.frame_content_sha256(bars.copy()))


if __name__ == "__main__":
    unittest.main()
