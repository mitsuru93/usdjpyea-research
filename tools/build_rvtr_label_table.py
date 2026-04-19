#!/usr/bin/env python3
"""Build RV/TR label tables from completed run-level label source artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.rvtr_ml import (
    SHORTLIST_BANDS,
    add_split_column,
    build_distribution_table,
    build_label_table,
    prepare_trainable_label_table,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RV/TR label tables from completed run artifacts.")
    parser.add_argument("--source-root", required=True, help="Root directory containing run outputs.")
    parser.add_argument("--output-dir", required=True, help="Directory to write label tables into.")
    return parser.parse_args()


def _write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip" if path.suffix == ".gz" else None)


def _write_summary(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    label_table = build_label_table(args.source_root)
    trainable = prepare_trainable_label_table(label_table)

    label_table_path = output_dir / "rvtr_label_table_v1.csv.gz"
    trainable_path = output_dir / "rvtr_label_table_trainable_v1.csv.gz"
    _write_csv(label_table_path, label_table)
    _write_csv(trainable_path, trainable)

    overall_dist = build_distribution_table(label_table, [])
    by_month = build_distribution_table(label_table, ["month"])
    by_session = build_distribution_table(label_table, ["session"])
    by_band = build_distribution_table(label_table, ["band_token"])

    _write_csv(output_dir / "label_distribution_overall.csv", overall_dist)
    _write_csv(output_dir / "label_distribution_by_month.csv", by_month)
    _write_csv(output_dir / "label_distribution_by_session.csv", by_session)
    _write_csv(output_dir / "label_distribution_by_band.csv", by_band)

    summary = {
        "source_root": str(Path(args.source_root).resolve()),
        "output_dir": str(output_dir),
        "shortlist_bands": sorted(SHORTLIST_BANDS),
        "label_table_rows": int(len(label_table)),
        "trainable_rows": int(len(trainable)),
        "label_counts": label_table["label_rvtr_v1"].value_counts(dropna=False).to_dict() if not label_table.empty else {},
        "trainable_label_counts": trainable["label_rvtr_v1"].value_counts(dropna=False).to_dict() if not trainable.empty else {},
        "split_counts": trainable["split"].value_counts(dropna=False).to_dict() if not trainable.empty else {},
        "unique_bands": sorted({str(x) for x in label_table.get("band_token", pd.Series(dtype=str)).dropna().astype(str).unique()}) if not label_table.empty else [],
        "unique_runs": int(label_table["source_run_dir"].nunique()) if not label_table.empty and "source_run_dir" in label_table.columns else 0,
        "trainable_rows_with_missing": int(trainable.isna().any(axis=1).sum()) if not trainable.empty else 0,
    }
    _write_summary(output_dir / "rvtr_label_table_v1.summary.json", summary)

    print(
        "RV/TR label table built:",
        f"rows={summary['label_table_rows']}",
        f"trainable={summary['trainable_rows']}",
        f"out={output_dir}",
    )


if __name__ == "__main__":
    main()
