#!/usr/bin/env python3
"""Review control/current/distilled RV/TR runs side by side."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.rvtr_ml import load_run_rows, sanitize_label


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review RV/TR ML runs side by side.")
    parser.add_argument("--control-run-dir", required=True, help="Run directory for bin_env_v1 control.")
    parser.add_argument("--current-run-dir", required=True, help="Run directory for total_score_rvtr_v1.")
    parser.add_argument("--distilled-run-dir", required=True, help="Run directory for total_score_rvtr_v2_ml.")
    parser.add_argument("--coef-csv", required=False, default=None, help="Optional coefficient CSV for sign sanity.")
    parser.add_argument("--distilled-yaml", required=False, default=None, help="Optional distilled YAML for sign sanity.")
    parser.add_argument("--output-dir", required=True, help="Directory to write review artifacts into.")
    return parser.parse_args()


def _read_yaml(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    return payload if isinstance(payload, dict) else {}


def _load_run_frame(run_dir: Path) -> pd.DataFrame:
    frame = load_run_rows(run_dir)
    if frame.empty:
        raise FileNotFoundError(f"No candidate artifact found in {run_dir}")
    return frame


def _normalize_band_token(df: pd.DataFrame, run_dir: Path) -> pd.Series:
    if "band_token" in df.columns:
        token = df["band_token"].astype(str).replace("nan", "").fillna("")
        return token
    band_cfg = _read_yaml(run_dir / "effective_band_config.yaml")
    token = str(band_cfg.get("band_token", "")).strip()
    if not token:
        band_model = str(band_cfg.get("band_model", "")).strip().lower()
        if band_model == "atr":
            token = f"ATR{int(round(float(band_cfg.get('band_atr_k', 0.0)) * 10)):02d}_P{int(round(float(band_cfg.get('band_atr_period', 0)))):02d}"
        elif band_model == "parkinson":
            token = f"PARK{int(round(float(band_cfg.get('band_vol_k', 0.0)) * 10)):02d}_P{int(round(float(band_cfg.get('band_vol_period', 0)))):02d}"
        elif band_model == "fixed_pips":
            token = f"PIP{int(round(float(band_cfg.get('band_pips', 0.0)))):02d}"
        else:
            token = sanitize_label(band_model).upper()
    return pd.Series([token] * len(df), index=df.index)


def _selected_rows(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "selected_by_decision_policy" in work.columns:
        mask = work["selected_by_decision_policy"].fillna(False).astype(bool)
    elif "decision_policy_outcome" in work.columns:
        mask = work["decision_policy_outcome"].astype(str).eq("include")
    elif "final_decision" in work.columns:
        mask = work["final_decision"].astype(str).ne("no_entry")
    else:
        mask = pd.Series(True, index=work.index)
    return work.loc[mask].copy()


def _decision_group_id(df: pd.DataFrame) -> pd.Series:
    if "decision_group_id" in df.columns:
        return df["decision_group_id"].astype(str)
    if "decision_group_id_v1" in df.columns:
        return df["decision_group_id_v1"].astype(str)
    if "timestamp" in df.columns and "touch_side" in df.columns:
        return df["timestamp"].astype(str) + "|" + df["touch_side"].astype(str)
    return df.index.astype(str)


def _group_choice(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["decision_group_id", "candidate_family", "pnl_pips"])
    work = df.copy()
    work["decision_group_id"] = _decision_group_id(work)
    if "candidate_family" not in work.columns:
        work["candidate_family"] = "unknown"
    if "pnl_pips" not in work.columns:
        work["pnl_pips"] = 0.0
    work["pnl_pips"] = pd.to_numeric(work["pnl_pips"], errors="coerce").fillna(0.0)
    sort_cols = ["decision_group_id", "pnl_pips", "candidate_family"]
    if "candidate_id" in work.columns:
        sort_cols.append("candidate_id")
    ascending = [True, False, True] + [True] * (len(sort_cols) - 3)
    top = work.sort_values(sort_cols, ascending=ascending, kind="mergesort").drop_duplicates("decision_group_id", keep="first")
    keep_cols = [c for c in ["decision_group_id", "candidate_family", "pnl_pips", "month", "session", "band_token"] if c in top.columns]
    return top.loc[:, keep_cols].copy()


def _summary_frame(df: pd.DataFrame, label: str, run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    work = df.copy()
    work["band_token"] = _normalize_band_token(work, run_dir)
    if "month" not in work.columns:
        work["month"] = "unknown"
    if "session" not in work.columns:
        work["session"] = "unknown"
    if "candidate_family" not in work.columns:
        work["candidate_family"] = "unknown"
    if "decision_group_id" not in work.columns:
        work["decision_group_id"] = _decision_group_id(work)

    selected = _selected_rows(work)
    selected["pnl_pips"] = pd.to_numeric(selected.get("pnl_pips", 0.0), errors="coerce").fillna(0.0)
    chosen = _group_choice(work)

    overall = {
        "label": label,
        "run_dir": str(run_dir),
        "selected_trade_count": int(len(selected)),
        "kept_trade_count": int(len(selected)),
        "kept_total_pnl_pips": float(selected["pnl_pips"].sum()) if not selected.empty else 0.0,
        "kept_avg_pnl_pips": float(selected["pnl_pips"].mean()) if not selected.empty else 0.0,
        "rv_share": float((selected["candidate_family"].astype(str) == "rev").mean()) if not selected.empty else 0.0,
        "tr_share": float((selected["candidate_family"].astype(str) == "trend").mean()) if not selected.empty else 0.0,
        "unique_groups": int(chosen["decision_group_id"].nunique()) if not chosen.empty else 0,
    }
    return selected, chosen, pd.DataFrame([overall]), overall


def _metrics_by_group(selected: pd.DataFrame, label: str, group_cols: list[str], control_choice: pd.DataFrame | None = None) -> pd.DataFrame:
    if selected.empty:
        cols = ["label"] + group_cols + ["kept_trade_count", "kept_total_pnl_pips", "kept_avg_pnl_pips", "rv_share", "tr_share", "decision_flip_rate_vs_control"]
        return pd.DataFrame(columns=cols)

    work = selected.copy()
    for col in group_cols:
        if col not in work.columns:
            work[col] = "unknown"
    work["pnl_pips"] = pd.to_numeric(work.get("pnl_pips", 0.0), errors="coerce").fillna(0.0)
    work["is_rv"] = work["candidate_family"].astype(str).eq("rev")
    work["is_tr"] = work["candidate_family"].astype(str).eq("trend")

    if control_choice is not None and not control_choice.empty:
        control_map = control_choice.loc[:, ["decision_group_id", "candidate_family"]].drop_duplicates("decision_group_id").rename(
            columns={"candidate_family": "candidate_family_control"}
        )
        choice_map = _group_choice(work)
        choice_map = choice_map.merge(control_map, on="decision_group_id", how="inner")
        choice_map["flip"] = choice_map["candidate_family"].astype(str) != choice_map["candidate_family_control"].astype(str)
        flip_rate = (
            choice_map.groupby(group_cols, dropna=False)["flip"].mean().reset_index(name="decision_flip_rate_vs_control")
            if not choice_map.empty
            else pd.DataFrame(columns=group_cols + ["decision_flip_rate_vs_control"])
        )
    else:
        flip_rate = pd.DataFrame(columns=group_cols + ["decision_flip_rate_vs_control"])

    agg = (
        work.groupby(group_cols, dropna=False)
        .agg(
            kept_trade_count=("pnl_pips", "size"),
            kept_total_pnl_pips=("pnl_pips", "sum"),
            kept_avg_pnl_pips=("pnl_pips", "mean"),
            rv_share=("is_rv", "mean"),
            tr_share=("is_tr", "mean"),
        )
        .reset_index()
    )
    agg["label"] = label
    if not flip_rate.empty:
        agg = agg.merge(flip_rate, on=group_cols, how="left")
    else:
        agg["decision_flip_rate_vs_control"] = 0.0
    agg["decision_flip_rate_vs_control"] = agg["decision_flip_rate_vs_control"].fillna(0.0)
    return agg


def _sign_sanity(coef_csv: Path | None) -> dict[str, Any]:
    if coef_csv is None or not coef_csv.exists():
        return {"available": False}
    df = pd.read_csv(coef_csv)
    if df.empty:
        return {"available": False}
    work = df.copy()
    work["coef_original"] = pd.to_numeric(work.get("coef_original", 0.0), errors="coerce").fillna(0.0)
    work["abs_coef_original"] = work["coef_original"].abs()
    work = work[work["feature"].astype(str).str.lower() != "intercept"].copy()
    work["preferred_label"] = work["coef_original"].map(lambda x: "rv" if x >= 0.0 else "tr")
    top = work.sort_values("abs_coef_original", ascending=False, kind="mergesort").head(10)
    return {
        "available": True,
        "top_positive_count": int((work["coef_original"] > 0).sum()),
        "top_negative_count": int((work["coef_original"] < 0).sum()),
        "top_features": [
            {
                "feature": str(row.feature),
                "coef_original": float(row.coef_original),
                "preferred_label": str(row.preferred_label),
            }
            for row in top.itertuples(index=False)
        ],
    }


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    runs = {
        "bin_env_v1": Path(args.control_run_dir).resolve(),
        "total_score_rvtr_v1": Path(args.current_run_dir).resolve(),
        "total_score_rvtr_v2_ml": Path(args.distilled_run_dir).resolve(),
    }

    selected_frames: dict[str, pd.DataFrame] = {}
    group_choices: dict[str, pd.DataFrame] = {}
    overall_rows: list[pd.DataFrame] = []
    for label, run_dir in runs.items():
        frame = _load_run_frame(run_dir)
        selected, group_choice, overall, _ = _summary_frame(frame, label, run_dir)
        selected_frames[label] = selected
        group_choices[label] = group_choice
        overall_rows.append(overall)

    control_choice = group_choices["bin_env_v1"]
    overall_compare = pd.concat(overall_rows, ignore_index=True)

    for label in ["total_score_rvtr_v1", "total_score_rvtr_v2_ml"]:
        chosen = group_choices[label]
        if control_choice.empty or chosen.empty:
            flip_rate = 0.0
        else:
            merged = chosen.merge(
                control_choice.loc[:, ["decision_group_id", "candidate_family"]].drop_duplicates("decision_group_id", keep="first"),
                on="decision_group_id",
                how="inner",
                suffixes=("_variant", "_control"),
            )
            flip_rate = float((merged["candidate_family_variant"].astype(str) != merged["candidate_family_control"].astype(str)).mean()) if not merged.empty else 0.0
        overall_compare.loc[overall_compare["label"] == label, "decision_flip_rate_vs_control"] = flip_rate

    by_month = pd.concat(
        [_metrics_by_group(selected_frames[label], label, ["month"], control_choice=control_choice) for label in runs],
        ignore_index=True,
    )
    by_session = pd.concat(
        [_metrics_by_group(selected_frames[label], label, ["session"], control_choice=control_choice) for label in runs],
        ignore_index=True,
    )
    by_band = pd.concat(
        [_metrics_by_group(selected_frames[label], label, ["band_token"], control_choice=control_choice) for label in runs],
        ignore_index=True,
    )

    overall_compare.to_csv(output_dir / "rvtr_ml_compare.csv", index=False)
    by_month.to_csv(output_dir / "rvtr_ml_by_month.csv", index=False)
    by_session.to_csv(output_dir / "rvtr_ml_by_session.csv", index=False)
    by_band.to_csv(output_dir / "rvtr_ml_by_band.csv", index=False)

    sign_sanity = _sign_sanity(Path(args.coef_csv).resolve() if args.coef_csv else None)
    distilled_payload = _read_yaml(Path(args.distilled_yaml).resolve() if args.distilled_yaml else None)

    md_lines = [
        "# RV/TR ML Review",
        "",
        f"- output_dir: `{output_dir}`",
        f"- control: `bin_env_v1` -> `{runs['bin_env_v1']}`",
        f"- current: `total_score_rvtr_v1` -> `{runs['total_score_rvtr_v1']}`",
        f"- distilled: `total_score_rvtr_v2_ml` -> `{runs['total_score_rvtr_v2_ml']}`",
        "",
        "## Overall compare",
        "",
    ]
    for _, row in overall_compare.iterrows():
        md_lines.append(
            f"- {row['label']}: kept_total_pnl={row['kept_total_pnl_pips']:.3f}, "
            f"kept_avg_pnl={row['kept_avg_pnl_pips']:.3f}, kept_trade_count={int(row['kept_trade_count'])}, "
            f"rv_share={row['rv_share']:.3f}, tr_share={row['tr_share']:.3f}, "
            f"flip_rate_vs_control={row['decision_flip_rate_vs_control']:.3f}"
        )
    md_lines.extend(["", "## Sign sanity", ""])
    if sign_sanity.get("available"):
        md_lines.append(
            f"- top_positive_count={sign_sanity['top_positive_count']}, top_negative_count={sign_sanity['top_negative_count']}"
        )
        for item in sign_sanity["top_features"][:8]:
            md_lines.append(
                f"- {item['feature']}: coef={item['coef_original']:.6f}, preferred_label={item['preferred_label']}"
            )
    else:
        md_lines.append("- coefficient CSV unavailable.")
    md_lines.extend(["", "## Distilled payload", ""])
    if distilled_payload:
        md_lines.append(
            f"- policy_family={distilled_payload.get('decision_policy_family', 'n/a')}, "
            f"entry_threshold={distilled_payload.get('entry_threshold', 'n/a')}, "
            f"margin_threshold={distilled_payload.get('margin_threshold', 'n/a')}"
        )
    else:
        md_lines.append("- distilled YAML unavailable.")

    (output_dir / "rvtr_ml_review.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("RV/TR ML review completed:", f"compare_rows={len(overall_compare)}", f"out={output_dir}")


if __name__ == "__main__":
    main()
