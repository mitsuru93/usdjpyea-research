#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PIP = 0.01
JPY_PER_PIP_001 = 10.0
INITIAL_EQUITY = 100000.0
LEVERAGE = 25.0
CONTRACT_SIZE = 100000.0
LOT = 0.01
STOPOUT_LEVEL = 100.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_files(root: Path) -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    for path in root.rglob("USDJPY_DUKASCOPY_NORMALIZED_TICKS_*.csv.gz"):
        match = re.search(r"(\d{4})_(\d{2})\.csv\.gz$", path.name)
        if match:
            ym = f"{match.group(1)}-{match.group(2)}"
            if "2020-01" <= ym <= "2022-12":
                rows.append((ym, path))
    rows.sort()
    if len(rows) != 36:
        raise RuntimeError(f"expected 36 normalized monthly files, got {len(rows)}")
    return rows


def load_ledger(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {
        "variant_id", "trade_id", "strategy", "entry_utc", "close_utc", "side",
        "entry_price", "pnl_jpy", "lots",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"ledger missing columns: {missing}")
    frame["entry_utc"] = pd.to_datetime(frame["entry_utc"], utc=True)
    frame["close_utc"] = pd.to_datetime(frame["close_utc"], utc=True)
    frame["side"] = pd.to_numeric(frame["side"], errors="raise").astype(int)
    frame["entry_price"] = pd.to_numeric(frame["entry_price"], errors="raise")
    frame["pnl_jpy"] = pd.to_numeric(frame["pnl_jpy"], errors="raise")
    frame["lots"] = pd.to_numeric(frame["lots"], errors="raise")
    return frame


def portfolio_frames(ledger: pd.DataFrame) -> dict[str, pd.DataFrame]:
    variants = {name: group.copy() for name, group in ledger.groupby("variant_id", sort=False)}
    required = {"B02_BASELINE", "B02_C3", "F05_BASELINE", "F05_C2", "SP39_UNCHANGED"}
    if set(variants) != required:
        raise RuntimeError(f"unexpected variant set: {sorted(variants)}")
    return {
        "P0_B02_BASELINE_F05_BASELINE": pd.concat([variants["B02_BASELINE"], variants["F05_BASELINE"]], ignore_index=True),
        "P1_B02_BASELINE_F05_C2": pd.concat([variants["B02_BASELINE"], variants["F05_C2"]], ignore_index=True),
        "P2_B02_C3_F05_BASELINE": pd.concat([variants["B02_C3"], variants["F05_BASELINE"]], ignore_index=True),
        "P3_B02_C3_F05_C2": pd.concat([variants["B02_C3"], variants["F05_C2"]], ignore_index=True),
        "P4_B02_C3_F05_C2_SP39": pd.concat([variants["B02_C3"], variants["F05_C2"], variants["SP39_UNCHANGED"]], ignore_index=True),
    }


def replay(portfolios: dict[str, pd.DataFrame], tick_root: Path) -> dict[str, dict[str, Any]]:
    state: dict[str, dict[str, Any]] = {}
    for portfolio_id in portfolios:
        state[portfolio_id] = {
            "balance": INITIAL_EQUITY,
            "peak_equity": INITIAL_EQUITY,
            "full_equity_drawdown_jpy": 0.0,
            "minimum_equity_jpy": INITIAL_EQUITY,
            "minimum_free_margin_jpy": INITIAL_EQUITY,
            "minimum_margin_level_pct": None,
            "maximum_concurrency": 0,
            "maximum_same_direction_concurrency": 0,
            "maximum_opposite_direction_concurrency": 0,
            "stopout_breached": False,
            "tick_count": 0,
        }

    for ym, tick_path in normalized_files(tick_root):
        ticks = pd.read_csv(tick_path, compression="gzip", usecols=["timestamp_utc", "bid", "ask"])
        times = pd.to_datetime(ticks["timestamp_utc"], utc=True)
        # Force nanosecond units. Pandas 3 may preserve microsecond storage, while
        # Timestamp.value is always nanoseconds; mixing units silently pushes every
        # search boundary to len(ticks), which was the v1 zero-risk defect.
        time_ns = times.to_numpy(dtype="datetime64[ns]").astype("int64")
        bid = ticks["bid"].to_numpy(dtype=float)
        ask = ticks["ask"].to_numpy(dtype=float)
        count_ticks = len(ticks)
        month_start = times.iloc[0]
        month_end = times.iloc[-1]

        for portfolio_id, trades in portfolios.items():
            s = state[portfolio_id]
            realized_delta = np.zeros(count_ticks + 1, dtype=float)
            floating = np.zeros(count_ticks, dtype=float)
            long_delta = np.zeros(count_ticks + 1, dtype=np.int32)
            short_delta = np.zeros(count_ticks + 1, dtype=np.int32)

            overlap = trades[(trades["close_utc"] >= month_start) & (trades["entry_utc"] <= month_end)]
            for row in overlap.itertuples(index=False):
                entry_ns = int(pd.Timestamp(row.entry_utc).value)
                close_ns = int(pd.Timestamp(row.close_utc).value)
                lo = int(np.searchsorted(time_ns, entry_ns, side="left"))
                hi = int(np.searchsorted(time_ns, close_ns, side="left"))
                lo = max(0, min(count_ticks, lo))
                hi = max(0, min(count_ticks, hi))

                if month_start <= row.close_utc <= month_end and hi < count_ticks:
                    realized_delta[hi] += float(row.pnl_jpy)

                if hi > lo:
                    pip_value = JPY_PER_PIP_001 * (float(row.lots) / LOT)
                    if int(row.side) == 1:
                        floating[lo:hi] += (bid[lo:hi] - float(row.entry_price)) / PIP * pip_value
                        long_delta[lo] += 1
                        long_delta[hi] -= 1
                    else:
                        floating[lo:hi] += (float(row.entry_price) - ask[lo:hi]) / PIP * pip_value
                        short_delta[lo] += 1
                        short_delta[hi] -= 1

            realized = float(s["balance"]) + np.cumsum(realized_delta[:-1])
            equity = realized + floating
            longs = np.cumsum(long_delta[:-1])
            shorts = np.cumsum(short_delta[:-1])
            concurrency = longs + shorts
            reference_price = (bid + ask) / 2.0
            margin = concurrency * reference_price * (CONTRACT_SIZE * LOT / LEVERAGE)
            free_margin = equity - margin
            margin_level = np.where(margin > 0, equity / margin * 100.0, np.inf)

            prior_peak = float(s["peak_equity"])
            running_peak = np.maximum.accumulate(np.r_[prior_peak, equity])[1:]
            drawdown = running_peak - equity
            s["peak_equity"] = max(prior_peak, float(np.max(equity)))
            s["full_equity_drawdown_jpy"] = max(float(s["full_equity_drawdown_jpy"]), float(np.max(drawdown)))
            s["minimum_equity_jpy"] = min(float(s["minimum_equity_jpy"]), float(np.min(equity)))
            s["minimum_free_margin_jpy"] = min(float(s["minimum_free_margin_jpy"]), float(np.min(free_margin)))
            finite_levels = margin_level[np.isfinite(margin_level)]
            if finite_levels.size:
                current = float(np.min(finite_levels))
                previous = s["minimum_margin_level_pct"]
                s["minimum_margin_level_pct"] = current if previous is None else min(float(previous), current)
            s["maximum_concurrency"] = max(int(s["maximum_concurrency"]), int(np.max(concurrency)))
            s["maximum_same_direction_concurrency"] = max(int(s["maximum_same_direction_concurrency"]), int(np.max(np.maximum(longs, shorts))))
            s["maximum_opposite_direction_concurrency"] = max(int(s["maximum_opposite_direction_concurrency"]), int(np.max(np.minimum(longs, shorts))))
            s["stopout_breached"] = bool(s["stopout_breached"] or np.any((margin > 0) & (margin_level < STOPOUT_LEVEL)))
            s["tick_count"] = int(s["tick_count"]) + count_ticks
            s["balance"] = float(realized[-1])

    result: dict[str, dict[str, Any]] = {}
    for portfolio_id, s in state.items():
        result[portfolio_id] = {
            "ending_balance_jpy": s["balance"],
            "net_jpy": float(s["balance"]) - INITIAL_EQUITY,
            "full_equity_drawdown_jpy": s["full_equity_drawdown_jpy"],
            "minimum_equity_jpy": s["minimum_equity_jpy"],
            "minimum_free_margin_jpy": s["minimum_free_margin_jpy"],
            "minimum_margin_level_pct": s["minimum_margin_level_pct"],
            "maximum_concurrency": s["maximum_concurrency"],
            "maximum_same_direction_concurrency": s["maximum_same_direction_concurrency"],
            "maximum_opposite_direction_concurrency": s["maximum_opposite_direction_concurrency"],
            "stopout_breached": s["stopout_breached"],
            "tick_count": s["tick_count"],
            "virtual_initial_equity_jpy": INITIAL_EQUITY,
            "virtual_leverage": LEVERAGE,
            "virtual_stopout_level_pct": STOPOUT_LEVEL,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--tick-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    ledger = load_ledger(args.ledger)
    portfolios = portfolio_frames(ledger)
    metrics = replay(portfolios, args.tick_root)
    expected_net = {portfolio_id: float(frame["pnl_jpy"].sum()) for portfolio_id, frame in portfolios.items()}
    tieout = {
        portfolio_id: {
            "expected_ledger_net_jpy": expected_net[portfolio_id],
            "replayed_net_jpy": metrics[portfolio_id]["net_jpy"],
            "difference_jpy": metrics[portfolio_id]["net_jpy"] - expected_net[portfolio_id],
            "pass": abs(metrics[portfolio_id]["net_jpy"] - expected_net[portfolio_id]) < 0.01,
        }
        for portfolio_id in portfolios
    }
    if not all(row["pass"] for row in tieout.values()):
        raise RuntimeError(f"realized balance tieout failed: {tieout}")
    if not all(metrics[p]["maximum_concurrency"] > 0 for p in metrics):
        raise RuntimeError("full-equity replay produced zero concurrency")

    payload = {
        "schema_version": "usdjpy_hyp044_source_native_full_equity_v2",
        "hypothesis_id": "USDJPY-HYP-044",
        "status": "PASS_CORRECTED_TICK_FULL_EQUITY_REPLAY",
        "authority": "USDJPY-DATA-2020-2022-TICK-AUTHORITY-001",
        "defect_corrected": "Pandas datetime unit mismatch in v1 searchsorted boundary conversion",
        "ledger": {"path": str(args.ledger), "sha256": sha256(args.ledger), "rows": len(ledger)},
        "metrics": metrics,
        "realized_balance_tieout": tieout,
        "2025H2_accessed": False,
    }
    output = args.out / "full_equity_metrics_2020_2022_v2.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "sha256sums.txt").write_text(f"{sha256(output)}  {output.name}\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
