#!/usr/bin/env python3
"""Compare FX session baseline artifacts across months.

This tool consumes extracted GitHub Actions artifacts from
``run_fx_session_baseline_monthly.yml`` / ``run_fx_session_baseline_2024_01.yml``.
It is intentionally report-oriented: it summarizes family stability across months,
rather than optimizing parameters.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_SCENARIO = "spread_x1_slip_0"
SEVERE_SCENARIO = "spread_x3_slip_0.5"


def parse_month_input(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("--input must be MONTH=PATH, e.g. 2024-04=/tmp/artifact")
    month, path = raw.split("=", 1)
    month = month.strip()
    if not month:
        raise argparse.ArgumentTypeError("month label must not be empty")
    return month, Path(path)


def find_one(root: Path, filename: str) -> Path:
    matches = sorted(root.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"{filename} not found under {root}")
    if len(matches) > 1:
        # Prefer experiment-level files over source files when both exist.
        experiment_matches = [p for p in matches if "experiments" in p.parts]
        if len(experiment_matches) == 1:
            return experiment_matches[0]
        raise ValueError(f"multiple {filename} files found under {root}: {matches}")
    return matches[0]


def load_month(month: str, root: Path) -> pd.DataFrame:
    summary_path = find_one(root, "summary.csv")
    df = pd.read_csv(summary_path)
    required = {
        "symbol",
        "timeframe",
        "session",
        "family",
        "params_json",
        "hold_bars",
        "scenario",
        "trades",
        "win_rate",
        "avg_gross_pips",
        "avg_cost_pips",
        "avg_net_pips",
        "total_net_pips",
        "profit_factor",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{summary_path} missing columns: {sorted(missing)}")
    df["month"] = month
    df["artifact_root"] = str(root)
    return df


def normalize_key(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["params_json"] = out["params_json"].map(lambda x: json.dumps(json.loads(x), sort_keys=True))
    out["family_key"] = (
        out["symbol"].astype(str)
        + "|" + out["timeframe"].astype(str)
        + "|" + out["session"].astype(str)
        + "|" + out["family"].astype(str)
        + "|" + out["params_json"].astype(str)
        + "|hold=" + out["hold_bars"].astype(str)
    )
    return out


def summarize_stability(df: pd.DataFrame, *, scenario: str, min_trades: int) -> pd.DataFrame:
    d = df[(df["scenario"] == scenario) & (df["trades"] >= min_trades)].copy()
    if d.empty:
        return d
    grouped = []
    for key, g in d.groupby("family_key", sort=False):
        grouped.append(
            {
                "family_key": key,
                "symbol": g["symbol"].iloc[0],
                "timeframe": g["timeframe"].iloc[0],
                "session": g["session"].iloc[0],
                "family": g["family"].iloc[0],
                "params_json": g["params_json"].iloc[0],
                "hold_bars": int(g["hold_bars"].iloc[0]),
                "months": int(g["month"].nunique()),
                "positive_months": int((g["avg_net_pips"] > 0).sum()),
                "min_avg_net_pips": float(g["avg_net_pips"].min()),
                "mean_avg_net_pips": float(g["avg_net_pips"].mean()),
                "sum_total_net_pips": float(g["total_net_pips"].sum()),
                "min_profit_factor": float(g["profit_factor"].min()),
                "mean_profit_factor": float(g["profit_factor"].mean()),
                "total_trades": int(g["trades"].sum()),
            }
        )
    out = pd.DataFrame(grouped)
    return out.sort_values(
        ["positive_months", "min_avg_net_pips", "mean_avg_net_pips", "sum_total_net_pips"],
        ascending=[False, False, False, False],
    )


def markdown_table(df: pd.DataFrame, cols: list[str], max_rows: int = 20) -> str:
    if df.empty:
        return "_No rows._\n"
    view = df.loc[:, cols].head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: f"{x:.3f}")
    return view.to_markdown(index=False)


def write_report(
    *,
    df: pd.DataFrame,
    default_rank: pd.DataFrame,
    severe_rank: pd.DataFrame,
    output: Path,
    scenario: str,
    severe_scenario: str,
    min_trades: int,
) -> None:
    months = sorted(df["month"].unique())
    lines: list[str] = []
    lines.append("# FX Session Family Comparison")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("Months: " + ", ".join(months))
    lines.append("")
    lines.append(f"Default scenario: `{scenario}`")
    lines.append(f"Severe scenario: `{severe_scenario}`")
    lines.append(f"Minimum trades per month-row: `{min_trades}`")
    lines.append("")
    lines.append("## Default-cost family stability")
    lines.append("")
    lines.append(markdown_table(default_rank, [
        "timeframe", "session", "family", "params_json", "hold_bars",
        "months", "positive_months", "min_avg_net_pips", "mean_avg_net_pips",
        "sum_total_net_pips", "min_profit_factor", "total_trades",
    ]))
    lines.append("")
    lines.append("## Severe-stress family stability")
    lines.append("")
    lines.append(markdown_table(severe_rank, [
        "timeframe", "session", "family", "params_json", "hold_bars",
        "months", "positive_months", "min_avg_net_pips", "mean_avg_net_pips",
        "sum_total_net_pips", "min_profit_factor", "total_trades",
    ]))
    lines.append("")
    lines.append("## Monthly detail for top default families")
    lines.append("")
    top_keys = default_rank.head(10)["family_key"].tolist() if not default_rank.empty else []
    detail = df[(df["scenario"] == scenario) & (df["family_key"].isin(top_keys))].copy()
    if detail.empty:
        lines.append("_No detail rows._")
    else:
        detail = detail.sort_values(["family_key", "month"])
        lines.append(markdown_table(detail, [
            "month", "timeframe", "session", "family", "params_json", "hold_bars",
            "trades", "win_rate", "avg_net_pips", "total_net_pips", "profit_factor",
        ], max_rows=80))
    lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=parse_month_input, required=True, help="MONTH=EXTRACTED_ARTIFACT_DIR")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--default-scenario", default=DEFAULT_SCENARIO)
    parser.add_argument("--severe-scenario", default=SEVERE_SCENARIO)
    parser.add_argument("--min-trades", type=int, default=20)
    args = parser.parse_args()

    frames = [load_month(month, path) for month, path in args.input]
    df = normalize_key(pd.concat(frames, ignore_index=True))
    default_rank = summarize_stability(df, scenario=args.default_scenario, min_trades=args.min_trades)
    severe_rank = summarize_stability(df, scenario=args.severe_scenario, min_trades=args.min_trades)
    write_report(
        df=df,
        default_rank=default_rank,
        severe_rank=severe_rank,
        output=Path(args.output_md),
        scenario=args.default_scenario,
        severe_scenario=args.severe_scenario,
        min_trades=args.min_trades,
    )


if __name__ == "__main__":
    main()
