"""Conservative candidate outcome evaluator for simulator v1."""

from __future__ import annotations

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
    candidate_values = candidates.to_numpy(copy=False)

    col_idx = {name: idx for idx, name in enumerate(candidate_columns)}
    timestamp_idx = col_idx["timestamp"]
    entry_price_idx = col_idx["entry_price"]
    tp_pips_idx = col_idx["tp_pips"]
    sl_pips_idx = col_idx["sl_pips"]
    direction_idx = col_idx["direction"]

    evaluated_rows = []
    bar_count = len(bar_high)

    for row_values in candidate_values:
        timestamp = row_values[timestamp_idx]
        entry_idx = time_to_idx.get(timestamp)
        if entry_idx is None:
            raise ValueError(f"Candidate timestamp not found in OHLC series: {timestamp}")

        start_idx = entry_idx + 1

        entry = float(row_values[entry_price_idx])
        tp_move = row_values[tp_pips_idx] * PIP_SIZE
        sl_move = row_values[sl_pips_idx] * PIP_SIZE
        direction = row_values[direction_idx]

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

        if direction == "buy":
            pnl_pips = (exit_price - entry) / PIP_SIZE
        else:
            pnl_pips = (entry - exit_price) / PIP_SIZE

        result = {column: row_values[idx] for idx, column in enumerate(candidate_columns)}
        result.update(
            {
                "outcome_status": status,
                "exit_price": float(exit_price),
                "bars_held": int(bars_held),
                "pnl_pips": float(pnl_pips),
            }
        )
        evaluated_rows.append(result)

    return pd.DataFrame(evaluated_rows)
