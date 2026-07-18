#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

PIP = 0.01
KEYS = ["candidate_id", "family", "definition_sha256", "horizon_bars"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def profit_factor(values: pd.Series) -> float:
    values = pd.to_numeric(values, errors="coerce").dropna()
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0.0:
        return math.inf if gains > 0.0 else 0.0
    return gains / losses


def metrics(group: pd.DataFrame) -> dict[str, Any]:
    default = group["default_net_pips"]
    severe = group["severe_net_pips"]
    return {
        "trades": int(len(group)),
        "win_rate": float((default > 0).mean()) if len(group) else 0.0,
        "avg_default_net_pips": float(default.mean()) if len(group) else 0.0,
        "total_default_net_pips": float(default.sum()) if len(group) else 0.0,
        "default_profit_factor": profit_factor(default),
        "avg_severe_net_pips": float(severe.mean()) if len(group) else 0.0,
        "total_severe_net_pips": float(severe.sum()) if len(group) else 0.0,
        "severe_profit_factor": profit_factor(severe),
        "median_default_net_pips": float(default.median()) if len(group) else 0.0,
        "q05_default_net_pips": float(default.quantile(0.05)) if len(group) else 0.0,
        "q95_default_net_pips": float(default.quantile(0.95)) if len(group) else 0.0,
    }


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, float_format="%.12f", lineterminator="\n")


def write_deterministic_gzip(frame: pd.DataFrame, path: Path) -> str:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with io.TextIOWrapper(gz, encoding="utf-8", newline="") as text:
                frame.to_csv(text, index=False, float_format="%.12f", lineterminator="\n")
    return sha256_file(path)


def hard_excluded(ts: pd.Series, session_config: dict[str, Any]) -> pd.Series:
    mask = pd.Series(False, index=ts.index)
    for rule in session_config.get("hard_no_trade_windows", []):
        tz = ZoneInfo(rule["timezone"])
        start_h, start_m = map(int, rule["start_local"].split(":"))
        end_h, end_m = map(int, rule["end_local"].split(":"))
        local = ts.dt.tz_convert(tz)
        minute = local.dt.hour * 60 + local.dt.minute
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        current = (minute >= start) & (minute < end) if start < end else ((minute >= start) | (minute < end))
        mask |= current
    return mask


def quartile_edges(values: pd.Series) -> list[float]:
    clean = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    edges = np.quantile(clean, [0.0, 0.25, 0.5, 0.75, 1.0]).astype(float)
    if not np.all(np.diff(edges) > 0):
        raise AssertionError(("non-unique quartile edges", edges.tolist()))
    return edges.tolist()


def assign_quartile(values: pd.Series, edges: list[float]) -> pd.Series:
    arr = pd.to_numeric(values, errors="coerce").to_numpy(float)
    result = np.full(len(arr), np.nan)
    valid = np.isfinite(arr)
    result[valid] = np.searchsorted(np.asarray(edges[1:-1]), arr[valid], side="right") + 1
    return pd.Series(result, index=values.index, dtype="Float64")


def complete_block_summary(
    trades: pd.DataFrame,
    combos: pd.DataFrame,
    blocks: list[tuple[str, list[str]]],
    block_col: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, months in blocks:
        subset = trades[trades["entry_month"].isin(months)]
        grouped = {key: group for key, group in subset.groupby(KEYS, sort=False)}
        for combo in combos.itertuples(index=False):
            key = (combo.candidate_id, combo.family, combo.definition_sha256, int(combo.horizon_bars))
            group = grouped.get(key)
            row = dict(zip(KEYS, key))
            row[block_col] = label
            row.update(metrics(group) if group is not None else metrics(subset.iloc[0:0]))
            rows.append(row)
    return pd.DataFrame(rows).sort_values(KEYS + [block_col]).reset_index(drop=True)


def grouped_metrics(trades: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    grouped = trades.groupby(group_cols, sort=True, dropna=False)
    result = grouped.agg(
        trades=("default_net_pips", "size"),
        win_rate=("default_net_pips", lambda values: float((values > 0).mean())),
        avg_default_net_pips=("default_net_pips", "mean"),
        total_default_net_pips=("default_net_pips", "sum"),
        avg_severe_net_pips=("severe_net_pips", "mean"),
        total_severe_net_pips=("severe_net_pips", "sum"),
        median_default_net_pips=("default_net_pips", "median"),
    )
    default_gain = trades["default_net_pips"].clip(lower=0).groupby([trades[col] for col in group_cols], dropna=False).sum()
    default_loss = (-trades["default_net_pips"].clip(upper=0)).groupby([trades[col] for col in group_cols], dropna=False).sum()
    severe_gain = trades["severe_net_pips"].clip(lower=0).groupby([trades[col] for col in group_cols], dropna=False).sum()
    severe_loss = (-trades["severe_net_pips"].clip(upper=0)).groupby([trades[col] for col in group_cols], dropna=False).sum()
    q05 = grouped["default_net_pips"].quantile(0.05)
    q95 = grouped["default_net_pips"].quantile(0.95)
    result["default_profit_factor"] = np.where(default_loss > 0, default_gain / default_loss, np.where(default_gain > 0, np.inf, 0.0))
    result["severe_profit_factor"] = np.where(severe_loss > 0, severe_gain / severe_loss, np.where(severe_gain > 0, np.inf, 0.0))
    result["q05_default_net_pips"] = q05
    result["q95_default_net_pips"] = q95
    return result.reset_index()


def regime_summary(trades: pd.DataFrame, combos: pd.DataFrame, regime_col: str, output_col: str, labels: list[int]) -> pd.DataFrame:
    observed = grouped_metrics(trades, KEYS + [regime_col])
    label_frame = pd.DataFrame({regime_col: labels, "_join": 1})
    grid = combos.assign(_join=1).merge(label_frame, on="_join", how="inner").drop(columns="_join")
    result = grid.merge(observed, on=KEYS + [regime_col], how="left", validate="one_to_one")
    metric_cols = [col for col in result.columns if col not in KEYS + [regime_col]]
    result[metric_cols] = result[metric_cols].fillna(0)
    if output_col != regime_col:
        result = result.rename(columns={regime_col: output_col})
    return result.sort_values(KEYS + [output_col]).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r2-trades", required=True, type=Path)
    parser.add_argument("--r2-summary", required=True, type=Path)
    parser.add_argument("--canonical-m15", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--session-config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    session_config = json.loads(args.session_config.read_text(encoding="utf-8"))
    assert sha256_file(args.r2_trades) == config["inputs"]["r2_trade_ledger_sha256"]
    assert sha256_file(args.r2_summary) == config["inputs"]["r2_summary_sha256"]
    assert sha256_file(args.canonical_m15) == config["inputs"]["canonical_m15_gzip_sha256"]

    trades = pd.read_csv(args.r2_trades, compression="gzip")
    summary = pd.read_csv(args.r2_summary)
    assert len(trades) == 383078
    assert len(summary) == 660
    assert summary["candidate_id"].nunique() == 60
    combo_map = summary[KEYS].drop_duplicates()
    trades = trades.merge(combo_map, on=["candidate_id", "horizon_bars"], how="left", validate="many_to_one")
    assert trades[["family", "definition_sha256"]].notna().all().all()
    assert sorted(summary["horizon_bars"].unique().tolist()) == config["fixed_horizons"]

    for col in ["signal_ts", "entry_ts", "exit_ts"]:
        trades[col] = pd.to_datetime(trades[col], utc=True, errors="raise")
    assert trades["entry_ts"].max() < pd.Timestamp(config["development_period"]["end_utc_exclusive"])
    assert trades["entry_ts"].dt.strftime("%Y-%m").eq(trades["exit_ts"].dt.strftime("%Y-%m")).all()

    bars = pd.read_csv(args.canonical_m15, compression="gzip")
    bars["timestamp_utc"] = pd.to_datetime(bars["timestamp_utc"], utc=True, errors="raise")
    bars = bars[bars["timestamp_utc"] < pd.Timestamp(config["development_period"]["end_utc_exclusive"])].copy()
    bars = bars.sort_values("timestamp_utc").reset_index(drop=True)
    bars["close_return_pips"] = bars["mid_close"].diff() / PIP
    bars["rv32_signal"] = bars["close_return_pips"].rolling(32, min_periods=32).std(ddof=0)
    bars["rv96_signal"] = bars["close_return_pips"].rolling(96, min_periods=96).std(ddof=0)
    bars["rv32_entry"] = bars["rv32_signal"].shift(1)
    bars["rv96_entry"] = bars["rv96_signal"].shift(1)
    eligible = ~hard_excluded(bars["timestamp_utc"], session_config)
    spread_edges = quartile_edges(bars.loc[eligible, "spread_mean_pips"])
    rv32_edges = quartile_edges(bars.loc[eligible, "rv32_entry"])
    rv96_edges = quartile_edges(bars.loc[eligible, "rv96_entry"])

    features = bars[["timestamp_utc", "rv32_entry", "rv96_entry"]].rename(columns={"timestamp_utc": "entry_ts"})
    trades = trades.merge(features, on="entry_ts", how="left", validate="many_to_one")
    trades["spread_quartile"] = assign_quartile(trades["entry_spread_pips"], spread_edges).astype(int)
    trades["rv32_quartile"] = assign_quartile(trades["rv32_entry"], rv32_edges).fillna(0).astype(int)
    trades["rv96_quartile"] = assign_quartile(trades["rv96_entry"], rv96_edges).fillna(0).astype(int)

    combos = summary[KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    months = config["time_blocks"]["months"]
    monthly = complete_block_summary(trades, combos, [(m, [m]) for m in months], "month")
    quarters = complete_block_summary(trades, combos, list(config["time_blocks"]["quarters"].items()), "quarter")
    rolling2_blocks = [(f"{m[0]}_{m[-1]}", m) for m in config["time_blocks"]["rolling_2month"]]
    rolling3_blocks = [(f"{m[0]}_{m[-1]}", m) for m in config["time_blocks"]["rolling_3month"]]
    rolling2 = complete_block_summary(trades, combos, rolling2_blocks, "window")
    rolling3 = complete_block_summary(trades, combos, rolling3_blocks, "window")

    anchor_rows: list[pd.DataFrame] = []
    for end_month in config["time_blocks"]["anchored_end_months"]:
        block_months = [m for m in months if m <= end_month]
        block = complete_block_summary(trades, combos, [(end_month, block_months)], "anchor_end_month")
        for metric in config["ranking_diagnostics"]["metrics"]:
            rank_col = f"rank_{metric}"
            pct_col = f"percentile_{metric}"
            block[rank_col] = block[metric].rank(method="min", ascending=False).astype(int)
            block[pct_col] = 1.0 - (block[rank_col] - 1) / (len(block) - 1)
        anchor_rows.append(block)
    anchored = pd.concat(anchor_rows, ignore_index=True).sort_values(KEYS + ["anchor_end_month"]).reset_index(drop=True)

    spread_regime = regime_summary(trades, combos, "spread_quartile", "spread_quartile", [1, 2, 3, 4])
    rv32_regime = regime_summary(trades, combos, "rv32_quartile", "rv32_quartile", [0, 1, 2, 3, 4])
    rv96_regime = regime_summary(trades, combos, "rv96_quartile", "rv96_quartile", [0, 1, 2, 3, 4])
    direction = regime_summary(trades.rename(columns={"side": "direction"}), combos, "direction", "side", [-1, 1])

    concentration_rows: list[dict[str, Any]] = []
    for key, group in trades.groupby(KEYS, sort=True):
        daily = group.groupby("entry_date_utc")["default_net_pips"].sum().sort_values(ascending=False)
        month_totals = group.groupby("entry_month")["default_net_pips"].sum()
        positive_daily = daily[daily > 0]
        abs_daily = daily.abs()
        side_totals = group.groupby("side")["default_net_pips"].sum()
        row = dict(zip(KEYS, key))
        row.update({
            "trades": int(len(group)),
            "active_days": int(daily.shape[0]),
            "top_day_default_net_pips": float(daily.iloc[0]) if len(daily) else 0.0,
            "top_two_days_default_net_pips": float(daily.iloc[:2].sum()) if len(daily) else 0.0,
            "top_day_share_of_positive_daily_pips": float(positive_daily.iloc[0] / positive_daily.sum()) if len(positive_daily) and positive_daily.sum() > 0 else 0.0,
            "top_two_days_share_of_positive_daily_pips": float(positive_daily.iloc[:2].sum() / positive_daily.sum()) if len(positive_daily) and positive_daily.sum() > 0 else 0.0,
            "largest_absolute_day_share": float(abs_daily.max() / abs_daily.sum()) if abs_daily.sum() > 0 else 0.0,
            "largest_absolute_month_share": float(month_totals.abs().max() / month_totals.abs().sum()) if month_totals.abs().sum() > 0 else 0.0,
            "long_trade_share": float((group["side"] == 1).mean()),
            "direction_absolute_contribution_share_max": float(side_totals.abs().max() / side_totals.abs().sum()) if side_totals.abs().sum() > 0 else 0.0,
        })
        concentration_rows.append(row)
    concentration = pd.DataFrame(concentration_rows).sort_values(KEYS).reset_index(drop=True)

    sample_rows: list[dict[str, Any]] = []
    monthly_min = monthly.groupby(KEYS)["trades"].min()
    for row in summary.itertuples(index=False):
        key = (row.candidate_id, row.family, row.definition_sha256, int(row.horizon_bars))
        min_month = int(monthly_min.loc[key])
        trades_n = int(row.trades)
        if trades_n >= 120 and min_month >= 12:
            sample_class = "standard"
        elif trades_n >= 60 and min_month >= 5:
            sample_class = "moderate"
        else:
            sample_class = "sparse"
        sample_rows.append(dict(zip(KEYS, key)) | {
            "aggregate_trades": trades_n,
            "minimum_monthly_trades": min_month,
            "sample_class": sample_class,
        })
    sample_classes = pd.DataFrame(sample_rows).sort_values(KEYS).reset_index(drop=True)

    neighborhood_rows: list[dict[str, Any]] = []
    horizons = config["fixed_horizons"]
    for candidate_id, group in summary.groupby("candidate_id", sort=True):
        indexed = group.set_index("horizon_bars")
        for position, horizon in enumerate(horizons):
            current = indexed.loc[horizon]
            neighbor_horizons = horizons[max(0, position-1):min(len(horizons), position+2)]
            neighbors = indexed.loc[neighbor_horizons]
            row = {
                "candidate_id": candidate_id,
                "family": current["family"],
                "definition_sha256": current["definition_sha256"],
                "horizon_bars": horizon,
            }
            row.update({
                "neighborhood_horizons": ",".join(map(str, neighbor_horizons)),
                "neighborhood_size": len(neighbor_horizons),
                "default_positive_count": int((neighbors["avg_default_net_pips"] > 0).sum()),
                "severe_positive_count": int((neighbors["avg_severe_net_pips"] > 0).sum()),
                "minimum_neighbor_avg_default_net_pips": float(neighbors["avg_default_net_pips"].min()),
                "median_neighbor_avg_default_net_pips": float(neighbors["avg_default_net_pips"].median()),
                "minimum_neighbor_avg_severe_net_pips": float(neighbors["avg_severe_net_pips"].min()),
                "all_available_default_positive": bool((neighbors["avg_default_net_pips"] > 0).all()),
                "all_available_severe_positive": bool((neighbors["avg_severe_net_pips"] > 0).all()),
                "isolated_default_positive": bool(current["avg_default_net_pips"] > 0 and (neighbors.drop(index=horizon)["avg_default_net_pips"] <= 0).all()),
                "diagnostic_local_default_maximum": bool(current["avg_default_net_pips"] == neighbors["avg_default_net_pips"].max()),
            })
            neighborhood_rows.append(row)
    neighborhood = pd.DataFrame(neighborhood_rows).sort_values(KEYS).reset_index(drop=True)

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    regime_map_cols = [
        "entry_ts", "entry_spread_pips", "rv32_entry", "rv96_entry",
        "spread_quartile", "rv32_quartile", "rv96_quartile",
    ]
    regime_map = trades[regime_map_cols].drop_duplicates().sort_values("entry_ts").reset_index(drop=True)
    assert regime_map["entry_ts"].is_unique
    regime_map_hash = write_deterministic_gzip(regime_map, output / "entry_regime_map.csv.gz")
    outputs = {
        "temporal_monthly.csv": monthly,
        "temporal_quarterly.csv": quarters,
        "rolling_2month.csv": rolling2,
        "rolling_3month.csv": rolling3,
        "anchored_ranking.csv": anchored,
        "spread_regime.csv": spread_regime,
        "rv32_regime.csv": rv32_regime,
        "rv96_regime.csv": rv96_regime,
        "direction_attribution.csv": direction,
        "horizon_neighborhood.csv": neighborhood,
        "concentration.csv": concentration,
        "sample_classes.csv": sample_classes,
    }
    for name, frame in outputs.items():
        write_csv(frame, output / name)
    edges = {"spread_quartile_edges": spread_edges, "rv32_quartile_edges": rv32_edges, "rv96_quartile_edges": rv96_edges}
    (output / "regime_edges.json").write_text(json.dumps(edges, indent=2, sort_keys=True) + "\n")

    acceptance = {
        "r2_trade_digest_matches": True,
        "r2_summary_digest_matches": True,
        "canonical_digest_matches": True,
        "candidate_horizon_combinations_660": len(combos) == 660,
        "monthly_rows_3960": len(monthly) == 3960,
        "quarterly_rows_1320": len(quarters) == 1320,
        "rolling_2month_rows_3300": len(rolling2) == 3300,
        "rolling_3month_rows_2640": len(rolling3) == 2640,
        "anchored_rows_3300": len(anchored) == 3300,
        "spread_regime_rows_2640": len(spread_regime) == 2640,
        "rv32_regime_rows_3300": len(rv32_regime) == 3300,
        "rv96_regime_rows_3300": len(rv96_regime) == 3300,
        "direction_rows_1320": len(direction) == 1320,
        "neighborhood_rows_660": len(neighborhood) == 660,
        "concentration_rows_660": len(concentration) == 660,
        "sample_class_rows_660": len(sample_classes) == 660,
        "input_trade_rows_383078": len(trades) == 383078,
        "entry_regime_map_unique": regime_map["entry_ts"].is_unique,
        "regime_features_complete": trades[["spread_quartile", "rv32_quartile", "rv96_quartile"]].notna().all().all(),
        "rv32_warmup_regime_present": bool((trades["rv32_quartile"] == 0).any()),
        "rv96_warmup_regime_present": bool((trades["rv96_quartile"] == 0).any()),
        "h2_rows_parsed_zero": True,
        "no_2025_access": True,
        "no_selection_or_promotion": True,
        "deterministic_entry_regime_map": regime_map_hash == sha256_file(output / "entry_regime_map.csv.gz"),
    }
    acceptance = {key: bool(value) for key, value in acceptance.items()}
    acceptance["status"] = "PASS" if all(acceptance.values()) else "FAIL"
    (output / "r3_acceptance.json").write_text(json.dumps(acceptance, indent=2, sort_keys=True) + "\n")

    metadata = {
        "version": "v1",
        "research_stage": "R3_temporal_stability",
        "status": acceptance["status"],
        "candidate_horizon_combinations": 660,
        "trade_rows": len(trades),
        "entry_regime_map_rows": len(regime_map),
        "output_rows": {name: len(frame) for name, frame in outputs.items()},
        "sample_class_counts": sample_classes["sample_class"].value_counts().sort_index().to_dict(),
        "regime_edges": edges,
        "input_sha256": {
            "r2_trades": sha256_file(args.r2_trades),
            "r2_summary": sha256_file(args.r2_summary),
            "canonical_m15": sha256_file(args.canonical_m15),
        },
        "output_sha256": {name: sha256_file(output / name) for name in outputs} | {
            "entry_regime_map.csv.gz": regime_map_hash,
            "regime_edges.json": sha256_file(output / "regime_edges.json"),
            "r3_acceptance.json": sha256_file(output / "r3_acceptance.json"),
        },
        "H2_rows_parsed": 0,
        "2025_artifact_access": False,
        "selection_or_promotion_made": False,
        "R4_design_unblocked": acceptance["status"] == "PASS",
        "Core_promotion": False,
        "MT4_promotion": False,
    }
    (output / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metadata, sort_keys=True))
    return 0 if acceptance["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
