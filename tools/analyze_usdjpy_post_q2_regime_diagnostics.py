#!/usr/bin/env python3
"""Diagnose the verified Jan-Jun USDJPY baseline families without retuning them.

P&L remains sourced from the canonical baseline trades.csv files. The canonical
public M1 series is used only for pre-entry/post-entry descriptive market-state
features after entry-price reconciliation against the Dukascopy baseline rows.
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

PIP = 0.01
PRIMARY_HOURS_UTC = {13, 14, 15, 16}
BASE_SPREAD_PIPS = 0.5
SERVER_TIMEZONE = "Europe/Helsinki"

CANDIDATES = {
    "m5_pullback_strict": {
        "timeframe": "M5",
        "family": "pullback_continuation",
        "params": {
            "pullback_min_pips": 2.0,
            "trend_lookback_bars": 12,
            "trend_min_pips": 10.0,
        },
        "hold_bars": 6,
    },
    "m15_breakout_lb3": {
        "timeframe": "M15",
        "family": "breakout_close_followthrough",
        "params": {"lookback_bars": 3},
        "hold_bars": 6,
    },
}


def parse_labeled_path(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("expected LABEL=PATH")
    label, value = raw.split("=", 1)
    path = Path(value).expanduser().resolve()
    if not label.strip() or not path.exists():
        raise argparse.ArgumentTypeError(f"invalid input: {raw}")
    return label.strip(), path


def normalized_params(value: object) -> str:
    if isinstance(value, str):
        value = json.loads(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def profit_factor(values: Iterable[float]) -> float:
    series = pd.Series(list(values), dtype=float)
    gains = float(series[series > 0].sum())
    losses = float(-series[series < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def find_trades(path: Path, scratch: Path) -> Path:
    root = path
    if path.suffix.lower() == ".zip":
        root = scratch / path.stem
        root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as zf:
            zf.extractall(root)
    matches = [p for p in root.rglob("trades.csv") if "experiments" in p.parts]
    if len(matches) != 1:
        raise ValueError(f"expected one experiment trades.csv under {path}; got {matches}")
    return matches[0]


def load_fixed_trades(inputs: list[tuple[str, Path]], scratch: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for month, path in inputs:
        df = pd.read_csv(find_trades(path, scratch))
        df["params_norm"] = df["params_json"].map(normalized_params)
        for col in ["timestamp_utc", "entry_ts", "exit_ts"]:
            df[col] = pd.to_datetime(df[col], utc=True)
        df["month"] = month
        df["date_utc"] = df["entry_ts"].dt.strftime("%Y-%m-%d")
        df["default_cost_pips"] = df["entry_public_spread_pips"].clip(lower=BASE_SPREAD_PIPS)
        df["default_net_pips"] = df["gross_pips"] - df["default_cost_pips"]
        df["severe_cost_pips"] = (df["entry_public_spread_pips"].clip(lower=BASE_SPREAD_PIPS) * 3.0) + 1.0
        df["severe_net_pips"] = df["gross_pips"] - df["severe_cost_pips"]
        for name, spec in CANDIDATES.items():
            selected = df[
                (df["timeframe"] == spec["timeframe"])
                & (df["family"] == spec["family"])
                & (df["params_norm"] == normalized_params(spec["params"]))
                & (df["hold_bars"] == spec["hold_bars"])
                & (df["entry_hour_utc"].isin(PRIMARY_HOURS_UTC))
            ].copy()
            selected["candidate"] = name
            frames.append(selected)
    result = pd.concat(frames, ignore_index=True)
    result["quarter"] = np.where(
        result["month"].isin(["2024-01", "2024-02", "2024-03"]), "Q1", "Q2"
    )
    return result


def load_public_m1(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=["DT", "Open", "High", "Low", "Close"])
    local = pd.to_datetime(df.pop("DT"), errors="raise")
    utc = local.dt.tz_localize(
        SERVER_TIMEZONE, ambiguous="infer", nonexistent="shift_forward"
    ).dt.tz_convert("UTC")
    df.index = pd.DatetimeIndex(utc)
    return df.sort_index()


def window(m1: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return m1.loc[(m1.index >= start) & (m1.index < end)]


def enrich_market_state(trades: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    lower = trades["entry_ts"].min() - pd.Timedelta(days=2)
    upper = trades["exit_ts"].max() + pd.Timedelta(hours=1)
    m1 = m1.loc[(m1.index >= lower) & (m1.index <= upper)].copy()

    entries = pd.DatetimeIndex(trades["entry_ts"])
    feature_frame = pd.DataFrame(index=entries)
    previous_close = m1["Close"].shift(1)
    absolute_path = m1["Close"].diff().abs()

    for minutes in [60, 180, 360, 720, 1440]:
        win = f"{minutes}min"
        high = m1["High"].rolling(win, closed="left", min_periods=1).max()
        low = m1["Low"].rolling(win, closed="left", min_periods=1).min()
        path = absolute_path.rolling(win, closed="left", min_periods=1).sum()
        feature_frame[f"prior_range_{minutes}m_pips"] = (
            (high - low).reindex(entries).to_numpy() / PIP
        )
        last_close = previous_close.reindex(entries).to_numpy()
        start_open = m1["Open"].reindex(
            entries - pd.Timedelta(minutes=minutes)
        ).to_numpy()
        feature_frame[f"prior_return_{minutes}m_pips"] = (
            last_close - start_open
        ) / PIP
        denominator = path.reindex(entries).to_numpy()
        feature_frame[f"prior_eff_{minutes}m"] = np.where(
            denominator > 0,
            np.abs(last_close - start_open) / denominator,
            np.nan,
        )

    public_open = m1["Open"].reindex(entries).to_numpy()
    feature_frame["entry_price_abs_diff_pips"] = (
        np.abs(public_open - trades["entry_mid"].to_numpy()) / PIP
    )

    for tf_minutes in [5, 15]:
        win = f"{tf_minutes}min"
        high = m1["High"].rolling(win, closed="left", min_periods=1).max()
        low = m1["Low"].rolling(win, closed="left", min_periods=1).min()
        current_range = (high - low).reindex(entries).to_numpy() / PIP
        previous_range = (high - low).reindex(
            entries - pd.Timedelta(minutes=tf_minutes)
        ).to_numpy() / PIP
        current_body = (
            previous_close.reindex(entries).to_numpy()
            - m1["Open"].reindex(
                entries - pd.Timedelta(minutes=tf_minutes)
            ).to_numpy()
        ) / PIP
        previous_body = (
            previous_close.reindex(
                entries - pd.Timedelta(minutes=tf_minutes)
            ).to_numpy()
            - m1["Open"].reindex(
                entries - pd.Timedelta(minutes=2 * tf_minutes)
            ).to_numpy()
        ) / PIP
        mask = trades["timeframe"].eq(f"M{tf_minutes}").to_numpy()
        feature_frame.loc[mask, "signal_range_pips"] = current_range[mask]
        feature_frame.loc[mask, "previous_bar_range_pips"] = previous_range[mask]
        feature_frame.loc[mask, "signal_body_pips"] = current_body[mask]
        feature_frame.loc[mask, "previous_bar_body_pips"] = previous_body[mask]

    minute = m1.reset_index().rename(
        columns={m1.index.name or "index": "timestamp_utc"}
    )
    minute["date_utc"] = minute["timestamp_utc"].dt.strftime("%Y-%m-%d")
    minute["hour_utc"] = minute["timestamp_utc"].dt.hour
    session_maps: dict[str, pd.DataFrame] = {}
    for name, hours in {
        "preprimary": range(0, 13),
        "primary_full": range(13, 17),
    }.items():
        part = minute[minute["hour_utc"].isin(hours)]
        grouped = part.groupby("date_utc").agg(
            range_high=("High", "max"),
            range_low=("Low", "min"),
            open_first=("Open", "first"),
            close_last=("Close", "last"),
        )
        grouped[f"{name}_range_pips"] = (
            grouped["range_high"] - grouped["range_low"]
        ) / PIP
        grouped[f"{name}_return_pips"] = (
            grouped["close_last"] - grouped["open_first"]
        ) / PIP
        session_maps[name] = grouped

    rows: list[dict[str, float]] = []
    for trade in trades.itertuples(index=False):
        entry = trade.entry_ts
        tf_minutes = 5 if trade.timeframe == "M5" else 15
        out: dict[str, float] = {}
        day_key = entry.strftime("%Y-%m-%d")
        for name in ["preprimary", "primary_full"]:
            grouped = session_maps[name]
            out[f"{name}_range_pips"] = (
                float(grouped.at[day_key, f"{name}_range_pips"])
                if day_key in grouped.index
                else float("nan")
            )
            out[f"{name}_return_pips"] = (
                float(grouped.at[day_key, f"{name}_return_pips"])
                if day_key in grouped.index
                else float("nan")
            )
        primary_start = entry.normalize() + pd.Timedelta(hours=13)
        primary_so_far = window(m1, primary_start, entry)
        if primary_so_far.empty:
            out["primary_sofar_range_pips"] = float("nan")
            out["primary_sofar_return_pips"] = float("nan")
        else:
            out["primary_sofar_range_pips"] = float(
                primary_so_far["High"].max() - primary_so_far["Low"].min()
            ) / PIP
            out["primary_sofar_return_pips"] = float(
                primary_so_far["Close"].iloc[-1]
                - primary_so_far["Open"].iloc[0]
            ) / PIP
        hold_end = trade.exit_ts + pd.Timedelta(minutes=tf_minutes)
        holding = window(m1, entry, hold_end)
        if holding.empty:
            out["mfe_pips"] = float("nan")
            out["mae_pips"] = float("nan")
            out["holding_range_pips"] = float("nan")
        elif trade.side == 1:
            out["mfe_pips"] = float(
                holding["High"].max() - trade.entry_mid
            ) / PIP
            out["mae_pips"] = float(
                holding["Low"].min() - trade.entry_mid
            ) / PIP
            out["holding_range_pips"] = float(
                holding["High"].max() - holding["Low"].min()
            ) / PIP
        else:
            out["mfe_pips"] = float(
                trade.entry_mid - holding["Low"].min()
            ) / PIP
            out["mae_pips"] = float(
                trade.entry_mid - holding["High"].max()
            ) / PIP
            out["holding_range_pips"] = float(
                holding["High"].max() - holding["Low"].min()
            ) / PIP
        rows.append(out)

    enriched = pd.concat(
        [
            trades.reset_index(drop=True),
            feature_frame.reset_index(drop=True),
            pd.DataFrame(rows),
        ],
        axis=1,
    )
    enriched["align_12h"] = (
        enriched["side"] * enriched["prior_return_720m_pips"] > 0
    )
    enriched["align_24h"] = (
        enriched["side"] * enriched["prior_return_1440m_pips"] > 0
    )
    enriched["signal_range_expands_previous"] = (
        enriched["signal_range_pips"]
        > enriched["previous_bar_range_pips"]
    )
    enriched["recent_volatility_accelerates"] = (
        enriched["prior_range_60m_pips"]
        > enriched["prior_range_180m_pips"] / 3.0
    )
    return enriched


def summarize(
    group: pd.DataFrame, net_col: str = "default_net_pips"
) -> dict[str, float | int]:
    net = group[net_col]
    return {
        "trades": int(len(group)),
        "win_rate": float((net > 0).mean()),
        "avg_net_pips": float(net.mean()),
        "total_net_pips": float(net.sum()),
        "profit_factor": profit_factor(net),
    }


def grouped_summary(
    df: pd.DataFrame, keys: list[str], net_col: str = "default_net_pips"
) -> pd.DataFrame:
    rows = []
    for key, group in df.groupby(keys, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(keys, key))
        row.update(summarize(group, net_col))
        rows.append(row)
    return pd.DataFrame(rows)


def daily_concentration(df: pd.DataFrame) -> pd.DataFrame:
    daily = df.groupby(
        ["candidate", "month", "date_utc"], as_index=False
    )["default_net_pips"].sum()
    rows = []
    for (candidate, month), group in daily.groupby(
        ["candidate", "month"], sort=True
    ):
        ordered = group.sort_values("default_net_pips", ascending=False)
        total = float(group["default_net_pips"].sum())
        rows.append(
            {
                "candidate": candidate,
                "month": month,
                "active_days": int(len(group)),
                "positive_days": int(
                    (group["default_net_pips"] > 0).sum()
                ),
                "negative_days": int(
                    (group["default_net_pips"] < 0).sum()
                ),
                "total_net_pips": total,
                "best_day": str(ordered.iloc[0]["date_utc"]),
                "best_day_net_pips": float(
                    ordered.iloc[0]["default_net_pips"]
                ),
                "worst_day": str(ordered.iloc[-1]["date_utc"]),
                "worst_day_net_pips": float(
                    ordered.iloc[-1]["default_net_pips"]
                ),
                "total_excluding_best_day": total
                - float(ordered.iloc[0]["default_net_pips"]),
                "total_excluding_best_two_days": total
                - float(ordered.head(2)["default_net_pips"].sum()),
            }
        )
    return pd.DataFrame(rows)


def mechanism_comparison(
    df: pd.DataFrame, event_dates: set[str]
) -> pd.DataFrame:
    breakout = df[df["candidate"] == "m15_breakout_lb3"]
    mechanisms = {
        "signal_range_expands_previous": "signal_range_expands_previous",
        "align_12h": "align_12h",
        "align_24h": "align_24h",
        "recent_volatility_accelerates": "recent_volatility_accelerates",
    }
    rows = []
    for label, column in mechanisms.items():
        group = breakout[breakout[column]]
        monthly = group.groupby("month")["default_net_pips"].agg(
            ["size", "mean"]
        )
        daily = group.groupby("date_utc")["default_net_pips"].sum().sort_values(
            ascending=False
        )
        no_events = group[~group["date_utc"].isin(event_dates)]
        row = {"mechanism": label}
        row.update(summarize(group))
        row["positive_months"] = int((monthly["mean"] > 0).sum())
        row["minimum_month_trades"] = int(monthly["size"].min())
        row["q1_avg_net_pips"] = float(
            group[group["quarter"] == "Q1"]["default_net_pips"].mean()
        )
        row["q2_avg_net_pips"] = float(
            group[group["quarter"] == "Q2"]["default_net_pips"].mean()
        )
        row["severe_avg_net_pips"] = float(
            group["severe_net_pips"].mean()
        )
        row["severe_profit_factor"] = profit_factor(
            group["severe_net_pips"]
        )
        row["event_excluded_avg_net_pips"] = float(
            no_events["default_net_pips"].mean()
        )
        row["event_excluded_profit_factor"] = profit_factor(
            no_events["default_net_pips"]
        )
        row["total_excluding_best_two_days"] = float(
            group["default_net_pips"].sum() - daily.head(2).sum()
        )
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", action="append", required=True, type=parse_labeled_path
    )
    parser.add_argument("--m1", required=True, type=Path)
    parser.add_argument("--event-date", action="append", default=[])
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="usdjpy_post_q2_") as tmp:
        trades = load_fixed_trades(args.input, Path(tmp))
    m1 = load_public_m1(args.m1)
    enriched = enrich_market_state(trades, m1)

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    grouped_summary(enriched, ["candidate", "month"]).to_csv(
        out / "fixed_monthly.csv", index=False
    )
    grouped_summary(enriched, ["candidate", "month", "side"]).to_csv(
        out / "side_monthly.csv", index=False
    )
    daily_concentration(enriched).to_csv(
        out / "daily_concentration.csv", index=False
    )

    state_columns = [
        "prior_range_60m_pips",
        "prior_range_180m_pips",
        "prior_eff_60m",
        "signal_range_pips",
        "preprimary_range_pips",
        "primary_sofar_range_pips",
        "primary_full_range_pips",
        "mfe_pips",
        "mae_pips",
        "holding_range_pips",
    ]
    quarter_state = enriched.groupby(["candidate", "quarter"])[
        state_columns
    ].median().reset_index()
    quarter_state.to_csv(
        out / "quarter_market_state_medians.csv", index=False
    )
    mechanism_comparison(enriched, set(args.event_date)).to_csv(
        out / "m15_mechanism_comparison.csv", index=False
    )

    reconciliation = {
        "candidate_trade_rows": int(len(enriched)),
        "median_entry_price_abs_diff_pips": float(
            enriched["entry_price_abs_diff_pips"].median()
        ),
        "p90_entry_price_abs_diff_pips": float(
            enriched["entry_price_abs_diff_pips"].quantile(0.90)
        ),
        "p99_entry_price_abs_diff_pips": float(
            enriched["entry_price_abs_diff_pips"].quantile(0.99)
        ),
        "share_within_2_pips": float(
            (enriched["entry_price_abs_diff_pips"] <= 2.0).mean()
        ),
        "pnl_source": "canonical Dukascopy baseline trades.csv",
        "market_state_source": str(args.m1),
        "market_state_server_timezone": SERVER_TIMEZONE,
        "event_dates": sorted(set(args.event_date)),
        "candidate_definitions": CANDIDATES,
    }
    (out / "data_reconciliation.json").write_text(
        json.dumps(reconciliation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    enriched.to_csv(out / "enriched_fixed_trades.csv", index=False)
    print(json.dumps(reconciliation, indent=2, sort_keys=True))
    print(
        mechanism_comparison(enriched, set(args.event_date)).to_string(
            index=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
