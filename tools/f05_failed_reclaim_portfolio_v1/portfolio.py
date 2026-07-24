"""Fixed-lot B02/F05 portfolio replay and risk metrics."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from usdjpy_structural_sl_v1.common import PIP, r1

INITIAL_BALANCE_JPY = 100000.0
LEVERAGE = 25.0
CONTRACT_UNITS = 1000.0  # 0.01 lot of a 100,000-unit FX contract
LOT_SIZE = 0.01
STOPOUT_LEVEL_PERCENT = 100.0


@dataclass
class Position:
    trade_id: str
    side: int
    entry_price: float
    entry_utc: pd.Timestamp
    exit_utc: pd.Timestamp
    realized_pips: float
    fold: str
    strategy: str


def _mark_price(m1_2023: pd.DataFrame, m1_2024: pd.DataFrame, ts: pd.Timestamp, side: int) -> float:
    bars = m1_2023 if ts.year == 2023 else m1_2024
    key = ts.floor("min")
    if key not in bars.index:
        prior = bars[bars.index <= key]
        if prior.empty:
            raise KeyError(f"no M1 mark at or before {ts}")
        row = prior.iloc[-1]
    else:
        row = bars.loc[key]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[-1]
    return float(row.bid_open if side == 1 else row.ask_open)


def _portfolio_state(
    balance: float,
    open_positions: dict[str, Position],
    ts: pd.Timestamp,
    m1_2023: pd.DataFrame,
    m1_2024: pd.DataFrame,
) -> tuple[float, float, float, float]:
    floating = 0.0
    margin = 0.0
    for position in open_positions.values():
        mark = _mark_price(m1_2023, m1_2024, ts, position.side)
        floating += position.side * (mark - position.entry_price) * CONTRACT_UNITS
        margin += CONTRACT_UNITS * mark / LEVERAGE
    equity = balance + floating
    free_margin = equity - margin
    margin_level = math.inf if margin <= 0.0 else equity / margin * 100.0
    return equity, margin, free_margin, margin_level


def _drawdown(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    peak = values[0]
    maximum = 0.0
    maximum_percent = 0.0
    for value in values:
        peak = max(peak, value)
        decline = peak - value
        maximum = max(maximum, decline)
        if peak > 0.0:
            maximum_percent = max(maximum_percent, decline / peak * 100.0)
    return maximum, maximum_percent


def _profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0.0].sum())
    losses = float(-values[values < 0.0].sum())
    if losses == 0.0:
        return math.inf if gains > 0.0 else 0.0
    return gains / losses


def apply_candidate(
    trades: pd.DataFrame,
    ledger: pd.DataFrame,
    *,
    extra_exit_cost_pips: float = 0.0,
) -> pd.DataFrame:
    result = trades.copy()
    result["trade_id"] = result.trade_id.astype(str)
    result["realized_exit_utc"] = pd.to_datetime(result.close_utc, utc=True)
    result["realized_pips"] = result.baseline_pips.astype(float)
    result["candidate_triggered"] = False
    if ledger.empty:
        return result
    by_id = ledger.set_index("trade_id")
    overlap = result.trade_id.isin(by_id.index)
    for index in result[overlap].index:
        trade_id = result.at[index, "trade_id"]
        event = by_id.loc[trade_id]
        if isinstance(event, pd.DataFrame):
            event = event.iloc[0]
        result.at[index, "realized_exit_utc"] = pd.Timestamp(event.candidate_exit_utc)
        result.at[index, "realized_pips"] = float(event.candidate_pips) - float(extra_exit_cost_pips)
        result.at[index, "candidate_triggered"] = True
    return result


def simulate(
    trades: pd.DataFrame,
    m1_2023: pd.DataFrame,
    m1_2024: pd.DataFrame,
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    frame = trades.copy().sort_values(["entry_utc", "trade_id"], kind="mergesort").reset_index(drop=True)
    events: list[dict[str, object]] = []
    for row in frame.itertuples(index=False):
        events.append({"time": pd.Timestamp(row.realized_exit_utc), "order": 0, "kind": "close", "row": row})
        events.append({"time": pd.Timestamp(row.entry_utc), "order": 1, "kind": "open", "row": row})
    events.sort(key=lambda item: (item["time"], item["order"], str(item["row"].trade_id)))

    balance = INITIAL_BALANCE_JPY
    open_positions: dict[str, Position] = {}
    admitted: set[str] = set()
    denied: set[str] = set()
    realized_rows: list[dict[str, object]] = []
    curve: list[dict[str, object]] = []
    balances = [balance]
    equities = [balance]
    min_free_margin = math.inf
    min_margin_level = math.inf
    max_open = 0
    max_lots = 0.0
    stopout_breached = False

    for item in events:
        ts = pd.Timestamp(item["time"])
        row = item["row"]
        trade_id = str(row.trade_id)
        if item["kind"] == "close":
            position = open_positions.pop(trade_id, None)
            if position is None:
                continue
            profit_jpy = float(position.realized_pips) * 10.0
            balance += profit_jpy
            realized_rows.append({
                "trade_id": trade_id,
                "fold": position.fold,
                "strategy": position.strategy,
                "side": position.side,
                "entry_utc": position.entry_utc,
                "exit_utc": ts,
                "realized_pips": float(position.realized_pips),
                "realized_pl_jpy": profit_jpy,
            })
            balances.append(balance)
        else:
            if trade_id in denied:
                continue
            equity, margin, free_margin, margin_level = _portfolio_state(
                balance, open_positions, ts, m1_2023, m1_2024
            )
            entry_price = float(row.entry_price)
            new_margin = CONTRACT_UNITS * entry_price / LEVERAGE
            if free_margin - new_margin <= 0.0:
                denied.add(trade_id)
            else:
                admitted.add(trade_id)
                open_positions[trade_id] = Position(
                    trade_id=trade_id,
                    side=int(row.side),
                    entry_price=entry_price,
                    entry_utc=ts,
                    exit_utc=pd.Timestamp(row.realized_exit_utc),
                    realized_pips=float(row.realized_pips),
                    fold=str(row.fold),
                    strategy=str(row.strategy),
                )

        equity, margin, free_margin, margin_level = _portfolio_state(
            balance, open_positions, ts, m1_2023, m1_2024
        )
        equities.append(equity)
        min_free_margin = min(min_free_margin, free_margin)
        if math.isfinite(margin_level):
            min_margin_level = min(min_margin_level, margin_level)
            stopout_breached = stopout_breached or margin_level <= STOPOUT_LEVEL_PERCENT
        max_open = max(max_open, len(open_positions))
        max_lots = max(max_lots, len(open_positions) * LOT_SIZE)
        curve.append({
            "timestamp_utc": ts,
            "event": item["kind"],
            "trade_id": trade_id,
            "balance_jpy": balance,
            "equity_jpy": equity,
            "margin_jpy": margin,
            "free_margin_jpy": free_margin,
            "margin_level_percent": None if not math.isfinite(margin_level) else margin_level,
            "open_positions": len(open_positions),
            "open_lots": len(open_positions) * LOT_SIZE,
        })

    realized = pd.DataFrame(realized_rows)
    balance_dd, balance_dd_percent = _drawdown(balances)
    equity_dd, equity_dd_percent = _drawdown(equities)
    values = realized.realized_pips if not realized.empty else pd.Series(dtype=float)
    metrics = {
        "accepted_signals": int(len(frame)),
        "admitted_trades": int(len(admitted)),
        "denied_trades": int(len(denied)),
        "closed_trades": int(len(realized)),
        "ending_balance_jpy": round(balance, 2),
        "net_pips": r1(values.sum()) if len(values) else 0.0,
        "profit_factor": _profit_factor(values),
        "realized_balance_max_drawdown_jpy": round(balance_dd, 2),
        "realized_balance_max_drawdown_percent": round(balance_dd_percent, 6),
        "event_equity_max_drawdown_jpy": round(equity_dd, 2),
        "event_equity_max_drawdown_percent": round(equity_dd_percent, 6),
        "minimum_free_margin_jpy": round(min_free_margin if math.isfinite(min_free_margin) else balance, 2),
        "minimum_margin_level_percent": None if not math.isfinite(min_margin_level) else round(min_margin_level, 6),
        "maximum_concurrent_positions": int(max_open),
        "maximum_open_lots": round(max_lots, 2),
        "stopout_breached": bool(stopout_breached),
    }
    return metrics, pd.DataFrame(curve), realized


def grouped_net(trades: pd.DataFrame, group: str) -> dict[str, float]:
    return {
        str(key): r1(value)
        for key, value in trades.groupby(group).realized_pips.sum().sort_index().items()
    }


def fold_replays(
    trades: pd.DataFrame,
    m1_2023: pd.DataFrame,
    m1_2024: pd.DataFrame,
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for fold, group in trades.groupby("fold", sort=True):
        metrics, _, _ = simulate(group.copy(), m1_2023, m1_2024)
        result[str(fold)] = metrics
    return result
