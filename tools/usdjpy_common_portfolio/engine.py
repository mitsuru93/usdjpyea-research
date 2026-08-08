#!/usr/bin/env python3
from __future__ import annotations
from .base import *

def historical_full_equity(trades: pd.DataFrame, states_path: Path, initial_capital: float) -> pd.DataFrame:
    states = pd.read_csv(states_path)
    states["observation_utc"] = parse_utc(states.observation_utc)
    t = trades.copy()
    t["entry_utc"] = parse_utc(t.entry_utc)
    t["exit_utc"] = parse_utc(t.exit_utc)
    close_map = t.set_index("source_trade_id")["exit_utc"]
    # Canonical state trade_id equals adapted source_trade_id.
    states["close_utc"] = states.trade_id.map(close_map)
    if states.close_utc.isna().any():
        raise ValueError("unresolved close timestamp in historical state ledger")
    grid = pd.DatetimeIndex(sorted(states.observation_utc.unique()))
    open_mask = states.observation_utc < states.close_utc
    floating = states[open_mask].groupby("observation_utc").executable_pips.sum().mul(JPY_PER_PIP_001_LOT).reindex(grid, fill_value=0.0)
    closes = t.groupby("exit_utc").realized_pl_jpy.sum().sort_index().cumsum()
    realized = closes.reindex(grid, method="ffill").fillna(0.0)
    open_count = states[open_mask].groupby("observation_utc").trade_id.nunique().reindex(grid, fill_value=0)
    out = pd.DataFrame({
        "timestamp_utc": grid,
        "realized_balance_jpy": initial_capital + realized.to_numpy(float),
        "floating_pl_jpy": floating.to_numpy(float),
        "equity_jpy": initial_capital + realized.to_numpy(float) + floating.to_numpy(float),
        "open_positions": open_count.to_numpy(int),
    })
    return out


def margin_series_from_trades(trades: pd.DataFrame, grid: pd.DatetimeIndex, leverage: float = DEFAULT_LEVERAGE) -> pd.DataFrame:
    margin = np.zeros(len(grid), dtype=float)
    lots = np.zeros(len(grid), dtype=float)
    grid_ns = grid.view("i8")
    for r in trades.itertuples(index=False):
        lo = int(np.searchsorted(grid_ns, pd.Timestamp(r.entry_utc).value, side="left"))
        hi = int(np.searchsorted(grid_ns, pd.Timestamp(r.exit_utc).value, side="left"))
        lot = float(r.lot)
        entry_bid = float(r.entry_bid)
        used = abs(CONTRACT_UNITS_001_LOT * (lot / DEFAULT_LOT) * entry_bid) / leverage
        margin[lo:hi] += used
        lots[lo:hi] += lot
    return pd.DataFrame({"timestamp_utc": grid, "margin_used_jpy": margin, "open_lots": lots})


def overlap_buckets(trades: pd.DataFrame) -> pd.DataFrame:
    t = trades.sort_values(["entry_utc", "source_trade_id"], kind="mergesort").reset_index(drop=True).copy()
    buckets = []
    for i, r in t.iterrows():
        overlap = t[(t.index != i) & (t.entry_utc < r.exit_utc) & (t.exit_utc > r.entry_utc)]
        same = bool((overlap.side == r.side).any())
        opposite = bool((overlap.side != r.side).any())
        bucket = "MIXED_SAME_AND_OPPOSITE" if same and opposite else "SAME_DIRECTION_ONLY" if same else "OPPOSITE_DIRECTION_ONLY" if opposite else "NO_OVERLAP"
        buckets.append(bucket)
    t["exposure_bucket"] = buckets
    return t


def period_metrics(
    trades: pd.DataFrame,
    full_equity: pd.DataFrame,
    initial_capital: float,
    observed_tick_authority: dict[str, Any] | None = None,
    observed_margin: pd.DataFrame | None = None,
) -> dict[str, Any]:
    t = trades.copy()
    t["entry_utc"] = parse_utc(t.entry_utc)
    t["exit_utc"] = parse_utc(t.exit_utc)
    values = t.realized_pl_jpy.astype(float)
    realized = realized_equity(t, initial_capital)
    realized_dd = drawdown_details(realized.realized_equity_jpy, realized.timestamp_utc)
    full_dd = drawdown_details(full_equity.equity_jpy, full_equity.timestamp_utc)
    daily = t.groupby(t.exit_utc.dt.strftime("%Y-%m-%d")).realized_pl_jpy.sum().sort_index()
    monthly = t.groupby(t.exit_utc.dt.strftime("%Y-%m")).realized_pl_jpy.sum().sort_index()
    by_strategy = {}
    for k, g in t.groupby("strategy_id", sort=True):
        by_strategy[str(k)] = {"trades": len(g), "net_jpy": float(g.realized_pl_jpy.sum()), "profit_factor": profit_factor(g.realized_pl_jpy)}
    by_quarter = t.groupby(t.exit_utc.dt.to_period("Q").astype(str)).realized_pl_jpy.sum().to_dict()
    overlap = overlap_buckets(t)
    exposure = overlap.groupby("exposure_bucket").realized_pl_jpy.agg(["count", "sum"]).reset_index().rename(columns={"count": "trades", "sum": "net_jpy"})
    result = {
        "trades": int(len(t)),
        "net_jpy": float(values.sum()),
        "gross_profit_jpy": float(values[values > 0].sum()),
        "gross_loss_jpy": float(-values[values < 0].sum()),
        "profit_factor": profit_factor(values),
        "initial_capital_jpy": initial_capital,
        "final_realized_balance_jpy": float(initial_capital + values.sum()),
        "realized_drawdown": realized_dd,
        "full_equity_drawdown": full_dd,
        "maximum_concurrent_positions": int(full_equity.open_positions.max()),
        "maximum_concurrent_lots": float(full_equity.open_positions.max() * DEFAULT_LOT),
        "worst_1_business_day_jpy": float(daily.min()),
        "worst_5_business_days_jpy": business_window_min(daily, 5),
        "worst_20_business_days_jpy": business_window_min(daily, 20),
        "worst_calendar_month_jpy": float(monthly.min()),
        "by_strategy": by_strategy,
        "by_month": {str(k): float(v) for k, v in monthly.items()},
        "by_quarter": {str(k): float(v) for k, v in by_quarter.items()},
        "exposure_buckets": exposure.to_dict("records"),
        "chronology_negative_holding_periods": int((t.exit_utc < t.entry_utc).sum()),
    }
    if observed_tick_authority is not None:
        result["tick_equity_authority"] = observed_tick_authority
    if observed_margin is not None and not observed_margin.empty:
        valid = observed_margin.margin_used_jpy > 0
        result["margin"] = {
            "maximum_margin_used_jpy": float(observed_margin.margin_used_jpy.max()),
            "minimum_free_margin_jpy": float(observed_margin.free_margin_jpy.min()) if "free_margin_jpy" in observed_margin else None,
            "minimum_margin_level_percent": float(observed_margin.loc[valid, "margin_level_percent"].min()) if valid.any() and "margin_level_percent" in observed_margin else None,
            "margin_breach_count": int((observed_margin.free_margin_jpy < 0).sum()) if "free_margin_jpy" in observed_margin else None,
        }
    return result


def recovery_classification(base_2025: dict[str, Any], current_2023: dict[str, Any], current_2025: dict[str, Any], integrity_pass: bool, margin_pass: bool) -> str:
    if not integrity_pass or not margin_pass:
        return "NO_RECOVERY"
    h23_ok = current_2023["net_jpy"] > 0 and (current_2023["profit_factor"] or 0) > 1
    h25_ok = current_2025["net_jpy"] > 0 and (current_2025["profit_factor"] or 0) > 1
    if h23_ok and h25_ok:
        risk_worse = (
            current_2025["full_equity_drawdown"]["maximum_drawdown_jpy"] > base_2025["full_equity_drawdown"]["maximum_drawdown_jpy"] + TOL
            or current_2025["full_equity_drawdown"]["minimum_equity_jpy"] < base_2025["full_equity_drawdown"]["minimum_equity_jpy"] - TOL
            or current_2025["worst_20_business_days_jpy"] < base_2025["worst_20_business_days_jpy"] - TOL
        )
        return "RETURN_RECOVERY_WITH_RISK_TRADEOFF" if risk_worse else "FULL_RECOVERY"
    if current_2025["net_jpy"] > base_2025["net_jpy"] + TOL:
        return "PARTIAL_RECOVERY"
    return "NO_RECOVERY"


def requested_combinations() -> list[tuple[str, list[str]]]:
    return [
        ("BASELINE", ["B02", "F05"]),
        ("B02_F05_N1", ["B02", "F05", "N1"]),
        ("B02_F05_N2", ["B02", "F05", "N2"]),
        ("B02_F05_N1_N2", ["B02", "F05", "N1", "N2"]),
        ("B02_FV2", ["B02", "F"]),
        ("B02_FV2_N1", ["B02", "F", "N1"]),
        ("B02_FV2_N2", ["B02", "F", "N2"]),
        ("B02_FV2_N1_N2", ["B02", "F", "N1", "N2"]),
        ("BV2_F05", ["B", "F05"]),
        ("BV2_F05_N1", ["B", "F05", "N1"]),
        ("BV2_F05_N2", ["B", "F05", "N2"]),
        ("BV2_FV2", ["B", "F"]),
        ("BV2_FV2_N1", ["B", "F", "N1"]),
        ("BV2_FV2_N2", ["B", "F", "N2"]),
        ("BV2_FV2_N1_N2", ["B", "F", "N1", "N2"]),
    ]
