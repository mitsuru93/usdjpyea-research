#!/usr/bin/env python3
"""Config-driven post-run analysis for feature-enriched candidate outputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.analysis import (
    DEFAULT_FEATURE_PAIRS,
    DEFAULT_FEATURES,
    DEFAULT_QUANTILE_BUCKET_COUNT,
    DEFAULT_SLICE_MODES,
    MIN_UNSTABLE_SAMPLE_SIZE,
    ensure_required_files,
    generate_bucket_reports,
    generate_joint_reports,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze completed experiment run outputs.")
    parser.add_argument("--config", required=True, help="Path to YAML analysis config.")
    return parser.parse_args()


def _normalize_feature_pairs(raw_pairs: list | None) -> list[tuple[str, str]]:
    if not raw_pairs:
        return DEFAULT_FEATURE_PAIRS

    pairs: list[tuple[str, str]] = []
    for pair in raw_pairs:
        if isinstance(pair, str):
            parts = [part.strip() for part in pair.split("|")]
            if len(parts) != 2:
                raise ValueError(f"Invalid feature pair string: {pair}")
            pairs.append((parts[0], parts[1]))
            continue

        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            pairs.append((str(pair[0]), str(pair[1])))
            continue

        raise ValueError(f"Unsupported feature pair format: {pair}")

    return pairs


def _load_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    required = ["run_dir", "output_dir"]
    missing = [key for key in required if key not in cfg]
    if missing:
        raise ValueError(f"Analysis config missing required fields: {missing}")

    cfg["quantile_bucket_count"] = int(cfg.get("quantile_bucket_count", DEFAULT_QUANTILE_BUCKET_COUNT))
    cfg["selected_features"] = list(cfg.get("selected_features", DEFAULT_FEATURES))
    cfg["selected_feature_pairs"] = _normalize_feature_pairs(cfg.get("selected_feature_pairs"))
    cfg["slice_modes"] = list(cfg.get("slice_modes", DEFAULT_SLICE_MODES))
    cfg["bucket_mode"] = str(cfg.get("bucket_mode", "quantile"))
    cfg["fixed_bins_by_feature"] = dict(cfg.get("fixed_bins_by_feature", {}))
    cfg["notes"] = str(cfg.get("notes", ""))

    return cfg


def _write_analysis_summary(output_dir: Path, selected_features: list[str]) -> Path:
    by_family_paths = sorted(output_dir.glob("bucket_by_family__*.csv"))
    lines = ["# Analysis Summary", "", "## Features analyzed", ""]
    lines.extend([f"- {feature}" for feature in selected_features])

    if by_family_paths:
        lines.extend(["", "## Family bucket extremes (avg_pnl_pips)", ""])
        for path in by_family_paths:
            df = pd.read_csv(path)
            if df.empty:
                continue

            feature_name = str(df["feature"].iloc[0]) if "feature" in df.columns else path.stem
            lines.append(f"### {feature_name}")
            for family, part in df.groupby("candidate_family", dropna=False):
                part_sorted = part.sort_values("avg_pnl_pips")
                lowest = part_sorted.iloc[0]
                highest = part_sorted.iloc[-1]
                lines.append(
                    f"- {family}: lowest={lowest['bucket']} ({lowest['avg_pnl_pips']:.4f}, n={int(lowest['trade_count'])}), "
                    f"highest={highest['bucket']} ({highest['avg_pnl_pips']:.4f}, n={int(highest['trade_count'])})"
                )

    unstable_paths = sorted(output_dir.glob("bucket_*.csv"))
    unstable_rows: list[str] = []
    for path in unstable_paths:
        df = pd.read_csv(path)
        if df.empty or "trade_count" not in df.columns:
            continue

        unstable = df[df["trade_count"] < MIN_UNSTABLE_SAMPLE_SIZE]
        for row in unstable.itertuples(index=False):
            feature = getattr(row, "feature", path.stem)
            bucket = getattr(row, "bucket", "")
            unstable_rows.append(
                f"- {path.name}: feature={feature}, bucket={bucket}, trade_count={int(row.trade_count)}"
            )

    lines.extend(["", "## Unstable low-sample buckets", ""])
    if unstable_rows:
        lines.extend(unstable_rows)
    else:
        lines.append(f"- None below trade_count < {MIN_UNSTABLE_SAMPLE_SIZE}.")

    out_path = output_dir / "analysis_summary.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    args = parse_args()
    cfg = _load_config(args.config)

    run_dir = Path(cfg["run_dir"])
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    required_paths = ensure_required_files(run_dir)
    candidates_df = pd.read_csv(required_paths["candidates"])

    bucket_paths = generate_bucket_reports(
        df=candidates_df,
        output_dir=output_dir,
        selected_features=cfg["selected_features"],
        quantile_bucket_count=cfg["quantile_bucket_count"],
        slice_modes=cfg["slice_modes"],
        bucket_mode=cfg["bucket_mode"],
        fixed_bins_by_feature=cfg["fixed_bins_by_feature"],
    )
    joint_paths = generate_joint_reports(
        df=candidates_df,
        output_dir=output_dir,
        selected_feature_pairs=cfg["selected_feature_pairs"],
        quantile_bucket_count=cfg["quantile_bucket_count"],
    )
    summary_path = _write_analysis_summary(output_dir, cfg["selected_features"])

    metadata = {
        "analysis_tool": "analyze_run.py",
        "run_dir": str(run_dir.resolve()),
        "output_dir": str(output_dir.resolve()),
        "quantile_bucket_count": int(cfg["quantile_bucket_count"]),
        "selected_features": cfg["selected_features"],
        "selected_feature_pairs": [list(pair) for pair in cfg["selected_feature_pairs"]],
        "slice_modes": cfg["slice_modes"],
        "bucket_mode": cfg["bucket_mode"],
        "fixed_bins_by_feature": cfg["fixed_bins_by_feature"],
        "required_summary_files": [path.name for path in required_paths["summaries"]],
        "generated_bucket_files": [path.name for path in bucket_paths],
        "generated_joint_files": [path.name for path in joint_paths],
        "analysis_summary": summary_path.name,
        "notes": cfg["notes"],
    }
    with (output_dir / "analysis_metadata.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False)

    print(
        "Post-run analysis completed:",
        f"features={len(cfg['selected_features'])}",
        f"pairs={len(cfg['selected_feature_pairs'])}",
        f"bucket_files={len(bucket_paths)}",
        f"joint_files={len(joint_paths)}",
        f"out={output_dir}",
    )


if __name__ == "__main__":
    main()
