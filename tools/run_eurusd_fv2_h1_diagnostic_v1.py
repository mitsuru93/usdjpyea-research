#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PIP = 0.0001
TRADE_COLUMNS = [
    "candidate_id", "family", "signal_ts", "entry_ts", "exit_time_utc",
    "side", "hold_bars", "exit_reason", "entry_mid", "exit_mid",
    "gross_pips", "spread_basis_pips", "net_pips", "severe_net_pips",
    "entry_date_utc", "entry_month",
]


def load_base(path: Path):
    spec = importlib.util.spec_from_file_location("eurusd_v2_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(json_safe(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses > 0:
        return gains / losses
    return math.inf if gains > 0 else 0.0


def grouped_metrics(frame: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(group_columns, dropna=False, observed=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = {column: value for column, value in zip(group_columns, key)}
        row.update(
            trades=int(len(group)),
            avg_net_pips=float(group.net_pips.mean()),
            total_net_pips=float(group.net_pips.sum()),
            profit_factor=profit_factor(group.net_pips),
            win_rate=float((group.net_pips > 0).mean()),
            severe_profit_factor=profit_factor(group.severe_net_pips),
            avg_MFE_pips=float(group.MFE_pips.mean()),
            avg_MAE_pips=float(group.MAE_pips.mean()),
            median_hold_bars=float(group.hold_bars.median()),
        )
        rows.append(row)
    return pd.DataFrame(rows)


def session_name(hour: int, buckets: dict[str, list[int]]) -> str:
    for name, bounds in buckets.items():
        if int(bounds[0]) <= hour < int(bounds[1]):
            return name
    raise ValueError(f"hour {hour} is not covered by session buckets")


def enrich_trades(bars: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=TRADE_COLUMNS + [
            "signal_index", "entry_index", "exit_index", "entry_abs_z",
            "entry_efficiency_ratio", "entry_utc_hour", "MFE_pips",
            "MAE_pips", "top_path_available_bars",
        ])
    index_by_ts = {timestamp: index for index, timestamp in enumerate(bars.timestamp_utc)}
    rows: list[dict[str, Any]] = []
    for item in trades.to_dict("records"):
        signal_ts = pd.Timestamp(item["signal_ts"])
        entry_ts = pd.Timestamp(item["entry_ts"])
        exit_bar_ts = pd.Timestamp(item["exit_time_utc"]) - pd.Timedelta(hours=1)
        signal_index = index_by_ts[signal_ts]
        entry_index = index_by_ts[entry_ts]
        exit_index = index_by_ts[exit_bar_ts]
        direction = int(item["side"])
        entry_mid = float(item["entry_mid"])
        window = bars.iloc[entry_index : exit_index + 1]
        if direction == 1:
            mfe = (float(window.mid_high.max()) - entry_mid) / PIP
            mae = (float(window.mid_low.min()) - entry_mid) / PIP
        else:
            mfe = (entry_mid - float(window.mid_low.min())) / PIP
            mae = (entry_mid - float(window.mid_high.max())) / PIP
        item.update(
            signal_index=signal_index,
            entry_index=entry_index,
            exit_index=exit_index,
            entry_abs_z=abs(float(bars.at[signal_index, "z72"])),
            entry_efficiency_ratio=float(bars.at[signal_index, "er24"]),
            entry_utc_hour=int(entry_ts.hour),
            MFE_pips=mfe,
            MAE_pips=mae,
            top_path_available_bars=min(12, len(bars) - signal_index - 1),
        )
        rows.append(item)
    return pd.DataFrame(rows)


def candidate_summary(frame: pd.DataFrame) -> dict[str, Any]:
    daily = frame.groupby("entry_date_utc").net_pips.sum().sort_values(ascending=False)
    monthly = frame.groupby("entry_month").net_pips.sum()
    equity = frame.sort_values("entry_ts").net_pips.cumsum()
    drawdown = equity - equity.cummax()
    total = float(frame.net_pips.sum())
    top1 = float(daily.head(1).sum())
    top2 = float(daily.head(2).sum())
    return {
        "candidate_id": str(frame.candidate_id.iloc[0]),
        "trades": int(len(frame)),
        "avg_net_pips": float(frame.net_pips.mean()),
        "total_net_pips": total,
        "profit_factor": profit_factor(frame.net_pips),
        "positive_months": int((monthly > 0).sum()),
        "severe_profit_factor": profit_factor(frame.severe_net_pips),
        "max_drawdown_pips": float(drawdown.min()),
        "total_excluding_best_two_days": total - top2,
        "best_day_net_pips": top1,
        "best_two_days_net_pips": top2,
        "best_two_days_share_of_positive_total": (top2 / total) if total > 0 else None,
        "avg_MFE_pips": float(frame.MFE_pips.mean()),
        "avg_MAE_pips": float(frame.MAE_pips.mean()),
        "median_MFE_pips": float(frame.MFE_pips.median()),
        "median_MAE_pips": float(frame.MAE_pips.median()),
        "mean_hold_bars": float(frame.hold_bars.mean()),
        "median_hold_bars": float(frame.hold_bars.median()),
        "long_trades": int((frame.side == 1).sum()),
        "short_trades": int((frame.side == -1).sum()),
    }


def average_path(bars: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candidate_id, group in trades.groupby("candidate_id"):
        for holding_bar in range(1, 13):
            values: list[float] = []
            for item in group.itertuples(index=False):
                path_index = int(item.signal_index) + holding_bar
                if path_index >= len(bars):
                    continue
                close_value = float(bars.at[path_index, "mid_close"])
                values.append(int(item.side) * (close_value - float(item.entry_mid)) / PIP)
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "holding_bar": holding_bar,
                    "observations": len(values),
                    "avg_gross_path_pips": float(np.mean(values)) if values else 0.0,
                    "median_gross_path_pips": float(np.median(values)) if values else 0.0,
                    "positive_fraction": float(np.mean(np.asarray(values) > 0)) if values else 0.0,
                }
            )
    return pd.DataFrame(rows)


def cost_grid(frame: pd.DataFrame, protocol: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grid = protocol["diagnostics"]["cost_grid"]
    for candidate_id, group in frame.groupby("candidate_id"):
        for multiplier in grid["spread_multipliers"]:
            for slippage in grid["slippage_pips_per_side"]:
                net = group.gross_pips - group.spread_basis_pips * float(multiplier) - 2.0 * float(slippage)
                rows.append(
                    {
                        "candidate_id": candidate_id,
                        "spread_multiplier": float(multiplier),
                        "slippage_pips_per_side": float(slippage),
                        "trades": int(len(group)),
                        "avg_net_pips": float(net.mean()),
                        "total_net_pips": float(net.sum()),
                        "profit_factor": profit_factor(net),
                    }
                )
    return pd.DataFrame(rows)


def entry_overlap(frame: pd.DataFrame, candidate_ids: list[str]) -> dict[str, Any]:
    first = frame.loc[frame.candidate_id == candidate_ids[0]]
    second = frame.loc[frame.candidate_id == candidate_ids[1]]
    key = lambda row: (pd.Timestamp(row.entry_ts).strftime("%Y-%m-%dT%H:%M:%SZ"), int(row.side))
    first_keys = {key(row) for row in first.itertuples(index=False)}
    second_keys = {key(row) for row in second.itertuples(index=False)}
    common = sorted(first_keys & second_keys)
    return {
        "candidate_1": candidate_ids[0],
        "candidate_2": candidate_ids[1],
        "candidate_1_entries": len(first_keys),
        "candidate_2_entries": len(second_keys),
        "common_entries": len(common),
        "candidate_1_only": len(first_keys - second_keys),
        "candidate_2_only": len(second_keys - first_keys),
        "jaccard": len(common) / len(first_keys | second_keys) if first_keys | second_keys else 0.0,
        "common_entry_keys": [{"entry_utc": ts, "side": side} for ts, side in common],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars", required=True, type=Path)
    parser.add_argument("--candidate-protocol", required=True, type=Path)
    parser.add_argument("--diagnostic-protocol", required=True, type=Path)
    parser.add_argument("--base-runner", default=Path("tools/run_eurusd_h1_h2_v2_validation.py"), type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    diagnostic = json.loads(args.diagnostic_protocol.read_text(encoding="utf-8"))
    candidate_protocol = json.loads(args.candidate_protocol.read_text(encoding="utf-8"))
    base = load_base(args.base_runner)
    bars = base.load_bars(args.bars)
    start = pd.Timestamp(diagnostic["period"]["start_utc"])
    end = pd.Timestamp(diagnostic["period"]["end_utc_exclusive"])
    if bars.timestamp_utc.min() < start or bars.timestamp_utc.max() >= end:
        raise RuntimeError("diagnostic input is not physically isolated to 2024 H1")
    if len(bars) != int(diagnostic["source"]["expected_H1_rows_after_slice"]):
        raise RuntimeError(f"unexpected H1 row count: {len(bars)}")

    definitions = {
        item["id"]: item
        for item in candidate_protocol["diagnostic_baselines"] + candidate_protocol["v2_candidates"]
    }
    candidate_ids = diagnostic["candidate_ids"]
    if set(candidate_ids) - set(definitions):
        raise RuntimeError("one or more diagnostic candidates are absent from the authoritative protocol")

    frames: list[pd.DataFrame] = []
    for candidate_id in candidate_ids:
        trades = base.trades(bars, definitions[candidate_id], candidate_protocol, start, end)
        if trades.empty:
            raise RuntimeError(f"candidate produced no H1 trades: {candidate_id}")
        frames.append(enrich_trades(bars, trades))
    all_trades = pd.concat(frames, ignore_index=True)
    all_trades["session"] = all_trades.entry_utc_hour.map(
        lambda hour: session_name(int(hour), diagnostic["diagnostics"]["session_bucket_utc"])
    )
    all_trades["side_name"] = all_trades.side.map({1: "long", -1: "short"})
    all_trades["zscore_bin"] = pd.cut(
        all_trades.entry_abs_z,
        bins=[1.5, 1.75, 2.0, 2.5, np.inf],
        right=False,
        labels=["1.50-1.75", "1.75-2.00", "2.00-2.50", "2.50+"],
    )
    all_trades["efficiency_bin"] = pd.cut(
        all_trades.entry_efficiency_ratio,
        bins=[0.0, 0.15, 0.25, 0.35 + 1e-12],
        right=False,
        labels=["0.00-0.15", "0.15-0.25", "0.25-0.35"],
    )

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    summaries = [candidate_summary(group) for _, group in all_trades.groupby("candidate_id")]
    summary_frame = pd.DataFrame(summaries)
    summary_frame.to_csv(out / "candidate_summary.csv", index=False)
    all_trades.to_csv(out / "trade_diagnostics.csv", index=False)
    grouped_metrics(all_trades, ["candidate_id", "entry_month"]).to_csv(out / "monthly_breakdown.csv", index=False)
    grouped_metrics(all_trades, ["candidate_id", "side_name"]).to_csv(out / "side_breakdown.csv", index=False)
    grouped_metrics(all_trades, ["candidate_id", "entry_utc_hour"]).to_csv(out / "hour_breakdown.csv", index=False)
    grouped_metrics(all_trades, ["candidate_id", "session"]).to_csv(out / "session_breakdown.csv", index=False)
    grouped_metrics(all_trades, ["candidate_id", "zscore_bin"]).to_csv(out / "zscore_breakdown.csv", index=False)
    grouped_metrics(all_trades, ["candidate_id", "efficiency_bin"]).to_csv(out / "efficiency_breakdown.csv", index=False)
    grouped_metrics(all_trades, ["candidate_id", "hold_bars"]).to_csv(out / "holding_breakdown.csv", index=False)
    grouped_metrics(all_trades, ["candidate_id", "exit_reason"]).to_csv(out / "exit_reason_breakdown.csv", index=False)
    cost_frame = cost_grid(all_trades, diagnostic)
    cost_frame.to_csv(out / "cost_grid.csv", index=False)
    path_frame = average_path(bars, all_trades)
    path_frame.to_csv(out / "average_path.csv", index=False)
    overlap = entry_overlap(all_trades, candidate_ids)
    write_json(out / "entry_overlap.json", overlap)

    result = {
        "schema_version": "eurusd_fv2_h1_diagnostic_result_v1",
        "period": diagnostic["period"],
        "candidate_ids": candidate_ids,
        "candidate_summary": summaries,
        "entry_overlap": {key: value for key, value in overlap.items() if key != "common_entry_keys"},
        "H2_accessed": False,
        "candidate_rules_changed": False,
        "revision_selected": False,
        "next_action": "interpret H1 diagnostics and preregister a bounded revision separately, or retain the frozen baseline if no structural revision is justified",
    }
    write_json(out / "diagnostic_result.json", result)
    source_receipt = {
        "schema_version": "eurusd_fv2_h1_diagnostic_source_receipt_v1",
        "bars_file": str(args.bars),
        "bars_file_sha256": f"sha256:{sha256_file(args.bars)}",
        "bars_frame_content_sha256": f"sha256:{base.frame_hash(bars)}",
        "bars_rows": int(len(bars)),
        "first_utc": bars.timestamp_utc.iloc[0],
        "last_utc": bars.timestamp_utc.iloc[-1],
        "candidate_protocol_sha256": f"sha256:{sha256_file(args.candidate_protocol)}",
        "diagnostic_protocol_sha256": f"sha256:{sha256_file(args.diagnostic_protocol)}",
        "authoritative_candidate_lock_sha256": diagnostic["authoritative_candidate_lock_sha256"],
    }
    write_json(out / "source_receipt.json", source_receipt)

    lines = [
        "# EURUSD F v2 2024 H1 diagnostic v1",
        "",
        "Only 2024 H1 was loaded. 2024 H2 was not accessed and no rule was changed.",
        "",
        summary_frame.to_markdown(index=False),
        "",
        f"Entry overlap: {overlap['common_entries']} common, {overlap['candidate_1_only']} target-0.5-only, {overlap['candidate_2_only']} target-0.25-only; Jaccard {overlap['jaccard']:.6f}.",
        "",
        "Interpretation and candidate creation are intentionally deferred to a separate preregistration step.",
    ]
    (out / "analysis_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    required = diagnostic["required_outputs"]
    missing = [name for name in required if not (out / name).exists() and name != "SHA256SUMS"]
    if missing:
        raise RuntimeError(f"missing required outputs: {missing}")
    checksum_lines = []
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            checksum_lines.append(f"{sha256_file(path)}  {path.name}")
    (out / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps(json_safe(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
