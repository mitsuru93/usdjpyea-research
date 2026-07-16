#!/usr/bin/env python3
"""Confirm the M15 impulse condition on the original Dukascopy source bars.

The tool never regenerates P&L. It labels the canonical M15 breakout trade rows
with range[t] > range[t-1] computed from the same Dukascopy M15 bar artifacts.
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

PRIMARY_HOURS_UTC = {13, 14, 15, 16}
BASE_SPREAD_PIPS = 0.5
PARAMS = json.dumps({"lookback_bars": 3}, sort_keys=True, separators=(",", ":"))


def parse_labeled_path(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("expected MONTH=PATH")
    label, value = raw.split("=", 1)
    path = Path(value).expanduser().resolve()
    if not label.strip() or not path.exists():
        raise argparse.ArgumentTypeError(f"invalid input: {raw}")
    return label.strip(), path


def normalized_params(value: object) -> str:
    if isinstance(value, str):
        value = json.loads(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def materialize(path: Path, scratch: Path, label: str) -> Path:
    if path.suffix.lower() != ".zip":
        return path
    root = scratch / label
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as zf:
        zf.extractall(root)
    return root


def find_one_trades(root: Path) -> Path:
    matches = [p for p in root.rglob("trades.csv") if "experiments" in p.parts]
    if len(matches) != 1:
        raise ValueError(
            f"expected one experiment trades.csv under {root}; got {matches}"
        )
    return matches[0]


def load_breakout_trades(month: str, root: Path) -> pd.DataFrame:
    df = pd.read_csv(find_one_trades(root))
    df["params_norm"] = df["params_json"].map(normalized_params)
    selected = df[
        (df["timeframe"] == "M15")
        & (df["family"] == "breakout_close_followthrough")
        & (df["params_norm"] == PARAMS)
        & (df["hold_bars"] == 6)
        & (df["entry_hour_utc"].isin(PRIMARY_HOURS_UTC))
    ].copy()
    for col in ["timestamp_utc", "entry_ts", "exit_ts"]:
        selected[col] = pd.to_datetime(selected[col], utc=True)
    selected["month"] = month
    selected["date_utc"] = selected["entry_ts"].dt.strftime("%Y-%m-%d")
    selected["default_cost_pips"] = selected[
        "entry_public_spread_pips"
    ].clip(lower=BASE_SPREAD_PIPS)
    selected["default_net_pips"] = (
        selected["gross_pips"] - selected["default_cost_pips"]
    )
    selected["severe_cost_pips"] = (
        selected["entry_public_spread_pips"].clip(lower=BASE_SPREAD_PIPS)
        * 3.0
        + 1.0
    )
    selected["severe_net_pips"] = (
        selected["gross_pips"] - selected["severe_cost_pips"]
    )
    return selected


def load_m15_bars(root: Path) -> pd.DataFrame:
    paths = sorted(root.rglob("M15/USDJPY_M15.csv.gz"))
    if not paths:
        raise FileNotFoundError(
            f"no M15/USDJPY_M15.csv.gz files under {root}"
        )
    frames = []
    for path in paths:
        frame = pd.read_csv(
            path,
            usecols=[
                "timestamp_utc",
                "mid_high",
                "mid_low",
                "source_build_id",
            ],
        )
        frame["_path"] = str(path)
        frames.append(frame)
    bars = pd.concat(frames, ignore_index=True)
    bars["timestamp_utc"] = pd.to_datetime(bars["timestamp_utc"], utc=True)
    bars["mid_high"] = pd.to_numeric(bars["mid_high"], errors="coerce")
    bars["mid_low"] = pd.to_numeric(bars["mid_low"], errors="coerce")
    bars = bars.dropna(subset=["timestamp_utc", "mid_high", "mid_low"])
    bars = bars.drop_duplicates(subset=["timestamp_utc"], keep="last")
    bars = bars.sort_values("timestamp_utc").reset_index(drop=True)
    bars["signal_range_pips"] = (
        bars["mid_high"] - bars["mid_low"]
    ) / 0.01
    bars["previous_bar_range_pips"] = bars["signal_range_pips"].shift(1)
    bars["impulse_confirmed"] = (
        bars["signal_range_pips"] > bars["previous_bar_range_pips"]
    )
    return bars


def summarize(
    group: pd.DataFrame, net_col: str = "default_net_pips"
) -> dict[str, float | int]:
    net = group[net_col]
    return {
        "trades": int(len(group)),
        "win_rate": float((net > 0).mean()) if len(group) else 0.0,
        "avg_net_pips": float(net.mean()) if len(group) else 0.0,
        "total_net_pips": float(net.sum()) if len(group) else 0.0,
        "profit_factor": profit_factor(net),
    }


def grouped(
    df: pd.DataFrame,
    keys: list[str],
    net_col: str = "default_net_pips",
) -> pd.DataFrame:
    rows = []
    for key, group in df.groupby(keys, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(keys, key))
        row.update(summarize(group, net_col))
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline", action="append", required=True, type=parse_labeled_path
    )
    parser.add_argument(
        "--bars", action="append", required=True, type=parse_labeled_path
    )
    parser.add_argument("--event-date", action="append", default=[])
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    baseline_map = dict(args.baseline)
    bars_map = dict(args.bars)
    if set(baseline_map) != set(bars_map):
        raise ValueError("baseline and bars month labels must match")

    frames = []
    coverage_rows = []
    with tempfile.TemporaryDirectory(
        prefix="dukascopy_impulse_"
    ) as temp:
        scratch = Path(temp)
        for month in sorted(baseline_map):
            baseline_root = materialize(
                baseline_map[month], scratch, f"baseline-{month}"
            )
            bars_root = materialize(
                bars_map[month], scratch, f"bars-{month}"
            )
            trades = load_breakout_trades(month, baseline_root)
            bars = load_m15_bars(bars_root)
            labels = bars[
                [
                    "timestamp_utc",
                    "signal_range_pips",
                    "previous_bar_range_pips",
                    "impulse_confirmed",
                ]
            ]
            joined = trades.merge(
                labels,
                on="timestamp_utc",
                how="left",
                validate="many_to_one",
            )
            coverage_rows.append(
                {
                    "month": month,
                    "breakout_trades": int(len(joined)),
                    "matched_signal_bars": int(
                        joined["impulse_confirmed"].notna().sum()
                    ),
                    "missing_signal_bars": int(
                        joined["impulse_confirmed"].isna().sum()
                    ),
                    "m15_bar_rows": int(len(bars)),
                    "m15_bar_files": int(
                        len(
                            list(
                                bars_root.rglob(
                                    "M15/USDJPY_M15.csv.gz"
                                )
                            )
                        )
                    ),
                }
            )
            frames.append(joined)

    all_trades = pd.concat(frames, ignore_index=True)
    if all_trades["impulse_confirmed"].isna().any():
        missing = all_trades[
            all_trades["impulse_confirmed"].isna()
        ][["month", "timestamp_utc"]]
        raise ValueError(
            "missing source bars for breakout signals:\n"
            + missing.to_string(index=False)
        )

    impulse = all_trades[all_trades["impulse_confirmed"]].copy()
    complement = all_trades[~all_trades["impulse_confirmed"]].copy()
    event_dates = set(args.event_date)
    no_events = impulse[~impulse["date_utc"].isin(event_dates)]
    daily = impulse.groupby("date_utc")["default_net_pips"].sum().sort_values(
        ascending=False
    )

    monthly = grouped(impulse, ["month"])
    monthly_severe = grouped(impulse, ["month"], "severe_net_pips")
    side = grouped(impulse, ["month", "side"])
    comparison_rows = []
    for label, group in [
        ("impulse_confirmed", impulse),
        ("not_impulse_confirmed", complement),
    ]:
        row = {"population": label}
        row.update(summarize(group))
        row["positive_months"] = int(
            (
                group.groupby("month")["default_net_pips"].mean()
                > 0
            ).sum()
        )
        row["q1_avg_net_pips"] = float(
            group[
                group["month"].isin(
                    ["2024-01", "2024-02", "2024-03"]
                )
            ]["default_net_pips"].mean()
        )
        row["q2_avg_net_pips"] = float(
            group[
                group["month"].isin(
                    ["2024-04", "2024-05", "2024-06"]
                )
            ]["default_net_pips"].mean()
        )
        row["severe_avg_net_pips"] = float(
            group["severe_net_pips"].mean()
        )
        row["severe_profit_factor"] = profit_factor(
            group["severe_net_pips"]
        )
        comparison_rows.append(row)

    summary = {
        "candidate": {
            "timeframe": "M15",
            "family": "breakout_close_followthrough",
            "lookback_bars": 3,
            "hold_bars": 6,
            "entry_hours_utc": sorted(PRIMARY_HOURS_UTC),
            "impulse_rule": (
                "signal_bar_range > previous_completed_bar_range"
            ),
        },
        "all_breakout": summarize(all_trades),
        "impulse_confirmed": summarize(impulse),
        "impulse_severe": summarize(impulse, "severe_net_pips"),
        "positive_months": int((monthly["avg_net_pips"] > 0).sum()),
        "event_dates": sorted(event_dates),
        "event_excluded": summarize(no_events),
        "best_two_days": daily.head(2).to_dict(),
        "total_net_excluding_best_two_days": float(
            impulse["default_net_pips"].sum() - daily.head(2).sum()
        ),
        "source_bar_coverage_complete": bool(
            all_trades["impulse_confirmed"].notna().all()
        ),
    }

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    all_trades.to_csv(out / "labeled_breakout_trades.csv", index=False)
    impulse.to_csv(out / "impulse_confirmed_trades.csv", index=False)
    monthly.to_csv(out / "impulse_monthly.csv", index=False)
    monthly_severe.to_csv(out / "impulse_monthly_severe.csv", index=False)
    side.to_csv(out / "impulse_side.csv", index=False)
    pd.DataFrame(coverage_rows).to_csv(
        out / "source_bar_coverage.csv", index=False
    )
    pd.DataFrame(comparison_rows).to_csv(
        out / "population_comparison.csv", index=False
    )
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(monthly.to_string(index=False))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
