#!/usr/bin/env python3
"""Measure forward-return horizons and 24-bar MFE/MAE for frozen USDJPY H1 entries.

This is a development-only diagnostic. It does not read H2 data, change the active
A1/E3 H2 pre-registration, optimize an exit, or promote a candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Callable

import pandas as pd

import run_usdjpy_h1_multi_family_screen as base
import run_usdjpy_h1_multi_family_screen_v2 as corrected


SignalFunction = Callable[[pd.DataFrame, dict], pd.Series]


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def summarize(group: pd.DataFrame, net_col: str) -> dict[str, float | int]:
    values = group[net_col]
    return {
        "trades": int(len(group)),
        "win_rate": float((values > 0).mean()) if len(group) else 0.0,
        "avg_net_pips": float(values.mean()) if len(group) else 0.0,
        "total_net_pips": float(values.sum()) if len(group) else 0.0,
        "profit_factor": profit_factor(values),
    }


def entry_definition_id(family: str, candidate: dict) -> str:
    payload = {
        key: value
        for key, value in candidate.items()
        if key not in {"id", "hold_bars"}
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:12]
    return f"{family}__{digest}"


def signal_function(family: str) -> SignalFunction:
    mapping: dict[str, SignalFunction] = {
        "m15_impulse_breakout": corrected.impulse_breakout,
        "session_range_breakout": base.session_breakout,
        "mean_reversion_failed_excursion": corrected.failed_excursion,
        "compression_expansion": corrected.compression_expansion,
        "higher_timeframe_trend_continuation": corrected.trend_continuation,
    }
    try:
        return mapping[family]
    except KeyError as exc:
        raise ValueError(f"unsupported family: {family}") from exc


def eligible_signal_mask(
    bars: pd.DataFrame,
    side: pd.Series,
    session_config: dict,
) -> pd.Series:
    entry_ts = bars["timestamp_utc"].shift(-1)
    entry_mid = bars["mid_open"].shift(-1)
    entry_spread = bars["spread_mean_pips"].shift(-1)
    excluded = corrected.base.hard_exclusion_mask(
        entry_ts, session_config, corrected.base.SYMBOL
    )
    return (
        side.isin([1, -1])
        & entry_ts.notna()
        & entry_mid.notna()
        & entry_spread.notna()
        & ~excluded
    )


def build_horizon_rows(
    bars: pd.DataFrame,
    side: pd.Series,
    eligible: pd.Series,
    family: str,
    candidate: dict,
    definition_id: str,
    horizons: list[int],
) -> pd.DataFrame:
    work = bars.copy()
    work["side"] = side.fillna(0).astype(int)
    work["signal_ts"] = work["timestamp_utc"]
    work["entry_ts"] = work["timestamp_utc"].shift(-1)
    work["entry_mid"] = work["mid_open"].shift(-1)
    work["entry_spread_pips"] = work["spread_mean_pips"].shift(-1)

    rows: list[pd.DataFrame] = []
    base_spread = float(candidate.get("base_spread_pips", 0.5))
    for horizon in horizons:
        exit_ts = work["timestamp_utc"].shift(-horizon)
        exit_mid = work["mid_close"].shift(-horizon)
        valid = eligible & exit_ts.notna() & exit_mid.notna()
        if not valid.any():
            continue
        current = work.loc[
            valid,
            [
                "signal_ts",
                "entry_ts",
                "entry_mid",
                "entry_spread_pips",
                "side",
            ],
        ].copy()
        current["exit_ts"] = exit_ts.loc[valid]
        current["exit_mid"] = exit_mid.loc[valid]
        current["candidate_id"] = candidate["id"]
        current["entry_definition_id"] = definition_id
        current["family"] = family
        current["registered_hold_bars"] = int(candidate["hold_bars"])
        current["horizon_bars"] = horizon
        current["entry_month"] = current["entry_ts"].dt.strftime("%Y-%m")
        current["entry_date_utc"] = current["entry_ts"].dt.strftime("%Y-%m-%d")
        current["gross_pips"] = (
            current["side"]
            * (current["exit_mid"] - current["entry_mid"])
            / base.PIP
        )
        spread = current["entry_spread_pips"].clip(lower=base_spread)
        current["default_cost_pips"] = spread
        current["severe_cost_pips"] = spread * 3.0 + 1.0
        current["default_net_pips"] = (
            current["gross_pips"] - current["default_cost_pips"]
        )
        current["severe_net_pips"] = (
            current["gross_pips"] - current["severe_cost_pips"]
        )
        rows.append(current)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def build_path_rows(
    bars: pd.DataFrame,
    side: pd.Series,
    eligible: pd.Series,
    family: str,
    candidate: dict,
    definition_id: str,
    path_window: int,
) -> pd.DataFrame:
    highs = bars["mid_high"].to_numpy(dtype=float)
    lows = bars["mid_low"].to_numpy(dtype=float)
    opens = bars["mid_open"].to_numpy(dtype=float)
    timestamps = bars["timestamp_utc"].tolist()
    spreads = bars["spread_mean_pips"].to_numpy(dtype=float)
    side_values = side.fillna(0).astype(int).to_numpy()
    eligible_values = eligible.to_numpy(dtype=bool)
    base_spread = float(candidate.get("base_spread_pips", 0.5))

    rows: list[dict[str, object]] = []
    for signal_idx in range(len(bars)):
        if not eligible_values[signal_idx]:
            continue
        last_idx = signal_idx + path_window
        entry_idx = signal_idx + 1
        if last_idx >= len(bars):
            continue
        direction = int(side_values[signal_idx])
        entry_mid = float(opens[entry_idx])
        path_highs = highs[entry_idx : last_idx + 1]
        path_lows = lows[entry_idx : last_idx + 1]
        if direction == 1:
            favorable = (path_highs - entry_mid) / base.PIP
            adverse = (path_lows - entry_mid) / base.PIP
        else:
            favorable = (entry_mid - path_lows) / base.PIP
            adverse = (entry_mid - path_highs) / base.PIP

        raw_mfe = float(favorable.max())
        raw_mae = float(adverse.min())
        gross_mfe = max(0.0, raw_mfe)
        gross_mae = min(0.0, raw_mae)
        bars_to_mfe = int(favorable.argmax()) + 1 if raw_mfe > 0 else 0
        bars_to_mae = int(adverse.argmin()) + 1 if raw_mae < 0 else 0
        spread = max(base_spread, float(spreads[entry_idx]))
        severe_cost = spread * 3.0 + 1.0
        entry_ts = timestamps[entry_idx]
        rows.append(
            {
                "candidate_id": candidate["id"],
                "entry_definition_id": definition_id,
                "family": family,
                "registered_hold_bars": int(candidate["hold_bars"]),
                "signal_ts": timestamps[signal_idx],
                "entry_ts": entry_ts,
                "entry_month": entry_ts.strftime("%Y-%m"),
                "entry_date_utc": entry_ts.strftime("%Y-%m-%d"),
                "side": direction,
                "entry_mid": entry_mid,
                "entry_spread_pips": float(spreads[entry_idx]),
                "path_window_bars": path_window,
                "gross_mfe_pips": gross_mfe,
                "gross_mae_pips": gross_mae,
                "default_mfe_net_pips": gross_mfe - spread,
                "default_mae_net_pips": gross_mae - spread,
                "severe_mfe_net_pips": gross_mfe - severe_cost,
                "severe_mae_net_pips": gross_mae - severe_cost,
                "bars_to_mfe": bars_to_mfe,
                "bars_to_mae": bars_to_mae,
            }
        )
    return pd.DataFrame(rows)


def build_horizon_summaries(
    horizon_trades: pd.DataFrame,
    horizons: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    monthly_rows: list[dict[str, object]] = []
    for keys, group in horizon_trades.groupby(
        ["candidate_id", "entry_definition_id", "family", "horizon_bars", "entry_month"],
        sort=True,
    ):
        candidate_id, definition_id, family, horizon, month = keys
        row: dict[str, object] = {
            "candidate_id": candidate_id,
            "entry_definition_id": definition_id,
            "family": family,
            "horizon_bars": int(horizon),
            "month": month,
        }
        default = summarize(group, "default_net_pips")
        severe = summarize(group, "severe_net_pips")
        row.update(default)
        row.update({f"severe_{key}": value for key, value in severe.items()})
        monthly_rows.append(row)
    monthly = pd.DataFrame(monthly_rows)

    summary_rows: list[dict[str, object]] = []
    for keys, group in horizon_trades.groupby(
        ["candidate_id", "entry_definition_id", "family", "horizon_bars"],
        sort=True,
    ):
        candidate_id, definition_id, family, horizon = keys
        default = summarize(group, "default_net_pips")
        severe = summarize(group, "severe_net_pips")
        month_slice = monthly[
            (monthly["candidate_id"] == candidate_id)
            & (monthly["horizon_bars"] == int(horizon))
        ]
        row = {
            "candidate_id": candidate_id,
            "entry_definition_id": definition_id,
            "family": family,
            "horizon_bars": int(horizon),
            **default,
            **{f"severe_{key}": value for key, value in severe.items()},
            "positive_months": int((month_slice["avg_net_pips"] > 0).sum()),
            "minimum_monthly_trades": int(month_slice["trades"].min()),
        }
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)

    stability_rows: list[dict[str, object]] = []
    for keys, group in summary.groupby(
        ["candidate_id", "entry_definition_id", "family"], sort=True
    ):
        candidate_id, definition_id, family = keys
        indexed = group.set_index("horizon_bars").reindex(horizons)
        values = indexed["avg_net_pips"]
        positive = values.gt(0).fillna(False).tolist()
        longest = 0
        current = 0
        for flag in positive:
            current = current + 1 if flag else 0
            longest = max(longest, current)
        valid_values = values.dropna()
        best_horizon = (
            int(valid_values.idxmax()) if not valid_values.empty else None
        )
        h6 = indexed.loc[6] if 6 in indexed.index else None
        stability_rows.append(
            {
                "candidate_id": candidate_id,
                "entry_definition_id": definition_id,
                "family": family,
                "reported_horizons": int(valid_values.shape[0]),
                "positive_horizon_count": int((valid_values > 0).sum()),
                "longest_positive_run_on_fixed_grid": int(longest),
                "minimum_avg_net_pips": float(valid_values.min()),
                "maximum_avg_net_pips": float(valid_values.max()),
                "diagnostic_best_horizon_bars": best_horizon,
                "hold6_avg_net_pips": (
                    float(h6["avg_net_pips"])
                    if h6 is not None and pd.notna(h6["avg_net_pips"])
                    else math.nan
                ),
                "hold6_profit_factor": (
                    float(h6["profit_factor"])
                    if h6 is not None and pd.notna(h6["profit_factor"])
                    else math.nan
                ),
            }
        )
    stability = pd.DataFrame(stability_rows)
    return summary, monthly, stability


def build_path_summary(path_trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metrics = [
        "gross_mfe_pips",
        "gross_mae_pips",
        "default_mfe_net_pips",
        "default_mae_net_pips",
        "severe_mfe_net_pips",
        "severe_mae_net_pips",
        "bars_to_mfe",
        "bars_to_mae",
    ]
    for keys, group in path_trades.groupby(
        ["candidate_id", "entry_definition_id", "family"], sort=True
    ):
        candidate_id, definition_id, family = keys
        row: dict[str, object] = {
            "candidate_id": candidate_id,
            "entry_definition_id": definition_id,
            "family": family,
            "path_trades": int(len(group)),
        }
        for metric in metrics:
            row[f"mean_{metric}"] = float(group[metric].mean())
            row[f"median_{metric}"] = float(group[metric].median())
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", action="append", required=True, type=base.parse_labeled_path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--horizon-config", required=True, type=Path)
    parser.add_argument("--session-config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    horizon_config = json.loads(args.horizon_config.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))
    horizons = [int(value) for value in horizon_config["horizon_bars"]]
    if horizons != sorted(set(horizons)) or 6 not in horizons:
        raise ValueError("horizon_bars must be unique, sorted and include 6")
    path_window = int(horizon_config["path_window_bars"])
    if path_window < max(horizons):
        raise ValueError("path_window_bars must be >= maximum horizon")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    loaded: dict[str, pd.DataFrame] = {}
    coverage_rows: list[dict[str, object]] = []
    for month, root in args.bars:
        bars, coverage = corrected.load_bars(month, root)
        loaded[month] = bars
        coverage_rows.append(coverage)

    horizon_frames: list[pd.DataFrame] = []
    path_frames: list[pd.DataFrame] = []
    definition_rows: list[dict[str, object]] = []
    for family_block in registry["families"]:
        family = str(family_block["family"])
        generator = signal_function(family)
        for candidate in family_block["candidates"]:
            definition_id = entry_definition_id(family, candidate)
            definition_rows.append(
                {
                    "candidate_id": candidate["id"],
                    "entry_definition_id": definition_id,
                    "family": family,
                    "registered_hold_bars": int(candidate["hold_bars"]),
                    "entry_parameters_json": json.dumps(
                        {
                            key: value
                            for key, value in candidate.items()
                            if key not in {"id", "hold_bars"}
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                }
            )
            for month in sorted(loaded):
                bars = loaded[month]
                side = generator(bars, candidate)
                eligible = eligible_signal_mask(bars, side, session_config)
                horizon_rows = build_horizon_rows(
                    bars,
                    side,
                    eligible,
                    family,
                    candidate,
                    definition_id,
                    horizons,
                )
                if not horizon_rows.empty:
                    horizon_frames.append(horizon_rows)
                path_rows = build_path_rows(
                    bars,
                    side,
                    eligible,
                    family,
                    candidate,
                    definition_id,
                    path_window,
                )
                if not path_rows.empty:
                    path_frames.append(path_rows)

    if not horizon_frames:
        raise RuntimeError("no horizon trades generated")
    if not path_frames:
        raise RuntimeError("no path trades generated")

    horizon_trades = pd.concat(horizon_frames, ignore_index=True)
    path_trades = pd.concat(path_frames, ignore_index=True)
    horizon_summary, horizon_monthly, stability = build_horizon_summaries(
        horizon_trades, horizons
    )
    path_summary = build_path_summary(path_trades)
    definition_map = pd.DataFrame(definition_rows).sort_values(
        ["family", "entry_definition_id", "candidate_id"]
    )

    horizon_trades.to_csv(output_dir / "horizon_trades.csv", index=False)
    horizon_summary.to_csv(output_dir / "horizon_summary.csv", index=False)
    horizon_monthly.to_csv(output_dir / "horizon_monthly.csv", index=False)
    path_trades.to_csv(output_dir / "entry_path_trades.csv", index=False)
    path_summary.to_csv(output_dir / "entry_path_summary.csv", index=False)
    stability.to_csv(output_dir / "horizon_stability.csv", index=False)
    definition_map.to_csv(output_dir / "entry_definition_map.csv", index=False)
    pd.DataFrame(coverage_rows).to_csv(
        output_dir / "source_bar_coverage.csv", index=False
    )

    metadata = {
        "version": "v1",
        "status": "development_diagnostic_only",
        "registry": str(args.registry),
        "horizon_config": str(args.horizon_config),
        "session_config": str(args.session_config),
        "months": sorted(loaded),
        "horizons": horizons,
        "path_window_bars": path_window,
        "candidate_count": int(definition_map["candidate_id"].nunique()),
        "unique_entry_definition_count": int(
            definition_map["entry_definition_id"].nunique()
        ),
        "h2_data_read": False,
        "promotion_decision": False,
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
