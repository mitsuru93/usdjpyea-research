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
    - evaluation starts from the NEXT bar to avoid same-bar lookahead.
    """
    if candidates_df.empty:
        return candidates_df.copy()

    bars = ohlc_df.reset_index(drop=True).copy()
    time_to_idx = {ts: i for i, ts in enumerate(bars["datetime"]) }

    evaluated_rows = []
    for row in candidates_df.itertuples(index=False):
        entry_idx = time_to_idx.get(row.timestamp)
        if entry_idx is None:
            raise ValueError(f"Candidate timestamp not found in OHLC series: {row.timestamp}")
        start_idx = entry_idx + 1
        result = _evaluate_single(row, bars, start_idx, max_holding_bars)
        evaluated_rows.append(result)

    return pd.DataFrame(evaluated_rows)


def _evaluate_single(row: object, bars: pd.DataFrame, start_idx: int, max_holding_bars: int) -> dict:
    entry = float(row.entry_price)
    tp_move = row.tp_pips * PIP_SIZE
    sl_move = row.sl_pips * PIP_SIZE

    if row.direction == "buy":
        tp_price = entry + tp_move
        sl_price = entry - sl_move
    elif row.direction == "sell":
        tp_price = entry - tp_move
        sl_price = entry + sl_move
    else:
        raise ValueError(f"Unknown direction: {row.direction}")

    end_idx = min(start_idx + max_holding_bars, len(bars))
    status = "timeout"
    exit_price = entry
    bars_held = max(0, end_idx - start_idx)

    for idx in range(start_idx, end_idx):
        bar = bars.iloc[idx]
        bar_high = float(bar["high"])
        bar_low = float(bar["low"])

        if row.direction == "buy":
            tp_hit = bar_high >= tp_price
            sl_hit = bar_low <= sl_price
        else:
            tp_hit = bar_low <= tp_price
            sl_hit = bar_high >= sl_price

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

    if row.direction == "buy":
        pnl_pips = (exit_price - entry) / PIP_SIZE
    else:
        pnl_pips = (entry - exit_price) / PIP_SIZE

    result = row._asdict()
    result.update(
        {
            "outcome_status": status,
            "exit_price": float(exit_price),
            "bars_held": int(bars_held),
            "pnl_pips": float(pnl_pips),
        }
    )
    return result
