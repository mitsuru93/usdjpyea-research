#!/usr/bin/env python3
"""Build fixed-family diagnostics from extracted USDJPY session-baseline artifacts.

This is a diagnostic tool, not an optimizer. Candidate definitions are fixed to the
H1-2024 research decisions so reruns cannot silently retune parameters.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

PRIMARY_HOURS_UTC = {13, 14, 15, 16}
BASE_SPREAD_PIPS = 0.5

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


def parse_input(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("--input must be LABEL=PATH")
    label, value = raw.split("=", 1)
    label = label.strip()
    path = Path(value).expanduser().resolve()
    if not label:
        raise argparse.ArgumentTypeError("input label must not be empty")
    if not path.exists():
        raise argparse.ArgumentTypeError(f"input path does not exist: {path}")
    return label, path


def find_one(root: Path, filename: str) -> Path:
    matches = sorted(root.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"{filename} not found under {root}")
    experiment_matches = [p for p in matches if "experiments" in p.parts]
    if len(experiment_matches) == 1:
        return experiment_matches[0]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"multiple {filename} files under {root}: {matches}")


def normalized_params(value: object) -> str:
    if isinstance(value, str):
        value = json.loads(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def profit_factor(values: Iterable[float]) -> float:
    series = pd.Series(list(values), dtype=float)
    gains = float(series[series > 0].sum())
    losses = float(-series[series < 0].sum())
    if losses == 0:
        return float("inf") if gains > 0 else float("nan")
    return gains / losses


def load_candidate_trades(label: str, root: Path) -> pd.DataFrame:
    path = find_one(root, "trades.csv")
    df = pd.read_csv(path)
    required = {
        "entry_ts",
        "entry_public_spread_pips",
        "side",
        "timeframe",
        "family",
        "params_json",
        "hold_bars",
        "entry_hour_utc",
        "gross_pips",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")

    df["params_norm"] = df["params_json"].map(normalized_params)
    df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
    df["date_utc"] = df["entry_ts"].dt.date.astype(str)
    df["default_cost_pips"] = df["entry_public_spread_pips"].clip(lower=BASE_SPREAD_PIPS)
    df["net_pips"] = df["gross_pips"] - df["default_cost_pips"]

    parts: list[pd.DataFrame] = []
    for candidate_name, spec in CANDIDATES.items():
        selected = df[
            (df["timeframe"] == spec["timeframe"])
            & (df["family"] == spec["family"])
            & (df["params_norm"] == normalized_params(spec["params"]))
            & (df["hold_bars"] == spec["hold_bars"])
            & (df["entry_hour_utc"].isin(PRIMARY_HOURS_UTC))
        ].copy()
        selected["month"] = label
        selected["candidate"] = candidate_name
        parts.append(selected)

    if not parts:
        raise ValueError(f"no candidate trades found in {path}")
    return pd.concat(parts, ignore_index=True)


def summarize_group(group: pd.DataFrame) -> pd.Series:
    return pd.Series(
        {
            "trades": len(group),
            "win_rate": float((group["net_pips"] > 0).mean()) if len(group) else float("nan"),
            "avg_gross_pips": float(group["gross_pips"].mean()),
            "avg_cost_pips": float(group["default_cost_pips"].mean()),
            "avg_net_pips": float(group["net_pips"].mean()),
            "total_net_pips": float(group["net_pips"].sum()),
            "profit_factor": profit_factor(group["net_pips"]),
        }
    )


def grouped_summary(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for keys, group in df.groupby(columns, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(columns, keys))
        row.update(summarize_group(group).to_dict())
        rows.append(row)
    return pd.DataFrame(rows)


def build_event_sensitivity(trades: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    event_dates = set(events["official_date"].astype(str))

    # The second 2024 operation was officially dated May 1, while the associated
    # market shock appears around May 2 in UTC/JST price data. Keep both explicit
    # views rather than silently shifting every event.
    shock_dates = set(event_dates)
    if "2024-05-01" in event_dates:
        shock_dates.add("2024-05-02")

    for candidate, group in trades.groupby("candidate", sort=True):
        for label, excluded in (
            ("none", set()),
            ("exclude_exact_mof_dates", event_dates),
            ("exclude_mof_and_may2_utc_shock", shock_dates),
        ):
            kept = group[~group["date_utc"].isin(excluded)]
            result = summarize_group(kept).to_dict()
            result.update(
                {
                    "candidate": candidate,
                    "sensitivity": label,
                    "excluded_dates": ",".join(sorted(excluded)),
                }
            )
            rows.append(result)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True, type=parse_input)
    parser.add_argument("--event-csv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    frames = [load_candidate_trades(label, root) for label, root in args.input]
    all_trades = pd.concat(frames, ignore_index=True)

    events = pd.read_csv(args.event_csv)
    if "official_date" not in events.columns:
        raise ValueError("event CSV must contain official_date")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    monthly = grouped_summary(all_trades, ["candidate", "month"])
    daily = grouped_summary(all_trades, ["candidate", "month", "date_utc"])
    side = grouped_summary(all_trades, ["candidate", "month", "side"])
    event_sensitivity = build_event_sensitivity(all_trades, events)

    monthly.to_csv(output_dir / "monthly.csv", index=False)
    daily.to_csv(output_dir / "daily.csv", index=False)
    side.to_csv(output_dir / "side.csv", index=False)
    event_sensitivity.to_csv(output_dir / "event_sensitivity.csv", index=False)

    metadata = {
        "purpose": "fixed-family diagnostic; no parameter optimization",
        "base_spread_pips": BASE_SPREAD_PIPS,
        "primary_hours_utc": sorted(PRIMARY_HOURS_UTC),
        "candidates": CANDIDATES,
        "inputs": [{"label": label, "path": str(path)} for label, path in args.input],
        "event_csv": str(args.event_csv),
    }
    (output_dir / "config.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(monthly.to_string(index=False))
    print("\nEvent sensitivity")
    print(event_sensitivity.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
