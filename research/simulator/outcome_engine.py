"""Conservative candidate outcome evaluator for simulator v1."""

from __future__ import annotations

import numpy as np
import pandas as pd

PIP_SIZE = 0.01  # USDJPY pip size
DEFAULT_MAX_HOLDING_BARS = 30


def evaluate_candidates(
    ohlc_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    max_holding_bars: int = DEFAULT_MAX_HOLDING_BARS,
) -> pd.DataFrame:
    """Evaluate each candidate forward using OHLC bars.

    Conservative same-bar ambiguity rule:
    if both TP and SL are reachable in the same bar, resolve as SL first.

    Entry convention for v1:
    - candidate entry timestamp uses source signal bar timestamp.
    - candidate entry_price is a signal reference price (not broker fill).
    - evaluation starts from the NEXT bar to avoid same-bar lookahead.
    """
    if candidates_df.empty:
        return candidates_df.copy()

    bars = ohlc_df.reset_index(drop=True)
    bar_datetimes = bars["datetime"].tolist()
    bar_high = pd.to_numeric(bars["high"], errors="coerce").to_numpy(dtype=float, copy=False)
    bar_low = pd.to_numeric(bars["low"], errors="coerce").to_numpy(dtype=float, copy=False)
    time_to_idx = {ts: i for i, ts in enumerate(bar_datetimes)}

    candidates = candidates_df.reset_index(drop=True)
    candidate_columns = list(candidates.columns)
    ts_values = candidates["timestamp"].to_numpy(copy=False)
    entry_values = pd.to_numeric(candidates["entry_price"], errors="coerce").to_numpy(dtype=float, copy=False)
    tp_moves = pd.to_numeric(candidates["tp_pips"], errors="coerce").to_numpy(dtype=float, copy=False) * PIP_SIZE
    sl_moves = pd.to_numeric(candidates["sl_pips"], errors="coerce").to_numpy(dtype=float, copy=False) * PIP_SIZE
    direction_values = candidates["direction"].astype(str).to_numpy(copy=False)

    evaluated_rows = []
    bar_count = len(bar_high)

    status_values = np.full(len(candidates), "timeout", dtype=object)
    exit_values = entry_values.copy()
    bars_held_values = np.zeros(len(candidates), dtype=np.int64)

    for row_idx, timestamp in enumerate(ts_values):
        entry_idx = time_to_idx.get(timestamp)
        if entry_idx is None:
            raise ValueError(f"Candidate timestamp not found in OHLC series: {timestamp}")

        start_idx = entry_idx + 1

        entry = float(entry_values[row_idx])
        tp_move = float(tp_moves[row_idx])
        sl_move = float(sl_moves[row_idx])
        direction = direction_values[row_idx]

        if direction == "buy":
            tp_price = entry + tp_move
            sl_price = entry - sl_move
        elif direction == "sell":
            tp_price = entry - tp_move
            sl_price = entry + sl_move
        else:
            raise ValueError(f"Unknown direction: {direction}")

        end_idx = min(start_idx + max_holding_bars, bar_count)
        status = "timeout"
        exit_price = entry
        bars_held = max(0, end_idx - start_idx)

        for idx in range(start_idx, end_idx):
            high = bar_high[idx]
            low = bar_low[idx]

            if direction == "buy":
                tp_hit = high >= tp_price
                sl_hit = low <= sl_price
            else:
                tp_hit = low <= tp_price
                sl_hit = high >= sl_price

            if tp_hit and sl_hit:
                status = "loss"
                exit_price = sl_price
                bars_held = idx - start_idx + 1
                break
            if sl_hit:
                status = "loss"
                exit_price = sl_price
                bars_held = idx - start_idx + 1
                break
            if tp_hit:
                status = "win"
                exit_price = tp_price
                bars_held = idx - start_idx + 1
                break

        status_values[row_idx] = status
        exit_values[row_idx] = float(exit_price)
        bars_held_values[row_idx] = int(bars_held)

    evaluated = candidates.copy()
    evaluated["outcome_status"] = status_values
    evaluated["exit_price"] = exit_values.astype(float)
    evaluated["bars_held"] = bars_held_values.astype(int)
    buy_mask = pd.Series(direction_values).eq("buy").to_numpy()
    pnl = np.where(buy_mask, (exit_values - entry_values) / PIP_SIZE, (entry_values - exit_values) / PIP_SIZE)
    evaluated["pnl_pips"] = pnl.astype(float)
    return evaluated[candidate_columns + ["outcome_status", "exit_price", "bars_held", "pnl_pips"]]
