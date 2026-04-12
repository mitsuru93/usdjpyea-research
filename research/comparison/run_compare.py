"""Config-driven multi-run comparison for completed research artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from research.comparison.compare_utils import (
    build_missing_message,
    compute_direction_summary,
    load_csv_if_exists,
    merge_bucket_frames,
    merge_section_frames,
    safe_label,
)

SECTION_TO_FILE = {
    "overall": "summary_overall.csv",
    "by_month": "summary_by_month.csv",
    "by_session": "summary_by_session.csv",
    "by_family": "summary_by_family.csv",
    "timing_overall": "summary_timing_overall.csv",
    "timing_by_month": "summary_timing_by_month.csv",
    "timing_by_session": "summary_timing_by_session.csv",
    "timing_by_family": "summary_timing_by_family.csv",
    "timing_by_decision_event": "summary_timing_by_decision_event.csv",
    "timing_by_reject_reason": "summary_timing_by_reject_reason.csv",
    "timing_by_family_decision_event": "summary_timing_by_family_decision_event.csv",
    "timing_by_family_reject_reason": "summary_timing_by_family_reject_reason.csv",
    "timing_by_still_touch_status": "summary_timing_by_still_touch_status.csv",
}

SECTION_KEYS = {
    "overall": [],
    "by_month": ["month"],
    "by_session": ["session"],
    "by_family": ["candidate_family"],
    "by_direction": ["direction"],
    "timing_overall": [],
    "timing_by_month": ["month"],
    "timing_by_session": ["session"],
    "timing_by_family": ["candidate_family"],
    "timing_by_decision_event": ["timing_decision_event"],
    "timing_by_reject_reason": ["timing_close_reject_reason"],
    "timing_by_family_decision_event": ["candidate_family", "timing_decision_event"],
    "timing_by_family_reject_reason": ["candidate_family", "timing_close_reject_reason"],
    "timing_by_still_touch_status": ["timing_still_touch_status"],
}

DEFAULT_COMPARE_SECTIONS = ["overall", "by_month", "by_session", "by_family", "by_direction"]



def compare_runs_from_config(cfg: dict) -> dict:
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    runs = list(cfg.get("runs", []))
    if not runs:
        raise ValueError("compare config requires at least one run in 'runs'")

    baseline_label = str(runs[0]["label"])
    compare_sections = list(cfg.get("compare_sections", DEFAULT_COMPARE_SECTIONS))
    selected_bucket_features = list(cfg.get("selected_bucket_features", []))

    warnings: list[str] = []
    generated_files: list[str] = []

    section_outputs: dict[str, Path] = {}
    for section in compare_sections:
        if section not in SECTION_KEYS:
            warnings.append(f"[config] unsupported compare section skipped: {section}")
            continue

        run_frames: list[tuple[str, pd.DataFrame]] = []
        for run in runs:
            label = str(run["label"])
            run_dir = Path(run["run_dir"])

            if section == "by_direction":
                candidates_path = run_dir / "candidates.csv"
                cand_df = load_csv_if_exists(candidates_path)
                if cand_df is None:
                    warnings.append(build_missing_message(section, label, candidates_path))
                    continue
                frame = compute_direction_summary(cand_df)
            else:
                source_path = run_dir / SECTION_TO_FILE[section]
                frame = load_csv_if_exists(source_path)
                if frame is None:
                    warnings.append(build_missing_message(section, label, source_path))
                    continue

            run_frames.append((label, frame))

        if not run_frames:
            warnings.append(f"[{section}] skipped because no run had a loadable artifact")
            continue

        key_cols = SECTION_KEYS[section]
        if section in {"overall", "timing_overall"}:
            for idx, (label, frame) in enumerate(run_frames):
                if frame.empty:
                    run_frames[idx] = (label, pd.DataFrame([{}]))
                else:
                    run_frames[idx] = (label, frame.head(1).copy())

        merged = merge_section_frames(run_frames=run_frames, key_cols=key_cols, baseline_label=baseline_label)
        out_path = output_dir / f"compare_{section}.csv"
        merged.to_csv(out_path, index=False)
        section_outputs[section] = out_path
        generated_files.append(out_path.name)

    bucket_outputs: dict[str, list[Path]] = {"bucket_overall": [], "bucket_by_family": []}
    if selected_bucket_features:
        for feature in selected_bucket_features:
            feature_token = safe_label(str(feature))
            for bucket_section, key_cols, source_name in [
                ("bucket_overall", ["feature", "bucket"], f"bucket_overall__{feature_token}.csv"),
                (
                    "bucket_by_family",
                    ["feature", "candidate_family", "bucket"],
                    f"bucket_by_family__{feature_token}.csv",
                ),
            ]:
                run_frames = []
                for run in runs:
                    label = str(run["label"])
                    analysis_dir_raw = run.get("analysis_dir")
                    if not analysis_dir_raw:
                        warnings.append(f"[{bucket_section}] missing analysis_dir for run '{label}'")
                        continue

                    analysis_path = Path(analysis_dir_raw) / source_name
                    frame = load_csv_if_exists(analysis_path)
                    if frame is None:
                        warnings.append(build_missing_message(bucket_section, label, analysis_path))
                        continue
                    run_frames.append((label, frame))

                if not run_frames:
                    continue

                merged = merge_bucket_frames(run_frames, key_cols=key_cols, baseline_label=baseline_label)
                out_path = output_dir / f"compare_{bucket_section}__{feature_token}.csv"
                merged.to_csv(out_path, index=False)
                bucket_outputs[bucket_section].append(out_path)
                generated_files.append(out_path.name)

    metadata = {
        "compare_tool": "compare_runs.py",
        "output_dir": str(output_dir.resolve()),
        "baseline_label": baseline_label,
        "runs": [
            {
                "label": str(run.get("label", "")),
                "run_dir": str(Path(run.get("run_dir", "")).resolve()) if run.get("run_dir") else "",
                "analysis_dir": (
                    str(Path(run.get("analysis_dir", "")).resolve()) if run.get("analysis_dir") else None
                ),
            }
            for run in runs
        ],
        "compare_sections": compare_sections,
        "selected_bucket_features": selected_bucket_features,
        "generated_files": generated_files,
        "warnings": warnings,
        "notes": str(cfg.get("notes", "")),
    }
    metadata_path = output_dir / "compare_metadata.yaml"
    with metadata_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f, sort_keys=False)

    summary_path = output_dir / "compare_summary.md"
    summary_path.write_text(
        build_compare_summary(
            runs=runs,
            baseline_label=baseline_label,
            section_outputs=section_outputs,
            bucket_outputs=bucket_outputs,
            warnings=warnings,
        ),
        encoding="utf-8",
    )
    generated_files.extend([metadata_path.name, summary_path.name])

    return {
        "baseline_label": baseline_label,
        "generated_files": generated_files,
        "warnings": warnings,
        "output_dir": output_dir,
    }


def _top_delta_rows(df: pd.DataFrame, delta_cols: list[str]) -> list[str]:
    rows: list[str] = []
    for col in delta_cols:
        if col not in df.columns or df.empty:
            continue
        top_pos = df.sort_values(col, ascending=False).head(1)
        top_neg = df.sort_values(col, ascending=True).head(1)
        if not top_pos.empty:
            rows.append(f"- best {col}: {top_pos.iloc[0][col]:.6g}")
        if not top_neg.empty:
            rows.append(f"- worst {col}: {top_neg.iloc[0][col]:.6g}")
    return rows


def build_compare_summary(
    runs: list[dict],
    baseline_label: str,
    section_outputs: dict[str, Path],
    bucket_outputs: dict[str, list[Path]],
    warnings: list[str],
) -> str:
    labels = [str(run["label"]) for run in runs]
    lines = ["# Compare Summary", "", "## Runs", ""]
    lines.extend([f"- {label}" for label in labels])
    lines.extend(["", f"- baseline: {baseline_label}", "", "## Sections generated", ""])

    generated_sections = sorted(section_outputs.keys())
    if generated_sections:
        lines.extend([f"- {name}" for name in generated_sections])
    else:
        lines.append("- None")

    lines.extend(["", "## Top delta snapshots (total_pnl_pips)", ""])
    for section in generated_sections:
        path = section_outputs[section]
        df = pd.read_csv(path)
        delta_cols = [col for col in df.columns if col.startswith("delta_") and col.endswith("_total_pnl_pips_vs_baseline")]
        lines.append(f"### {section}")
        top_rows = _top_delta_rows(df, delta_cols)
        if top_rows:
            lines.extend(top_rows)
        else:
            lines.append("- No total_pnl_pips delta columns available.")

    lines.extend(["", "## Bucket comparisons", ""])
    for bucket_key in ["bucket_overall", "bucket_by_family"]:
        files = sorted(bucket_outputs.get(bucket_key, []))
        if files:
            lines.append(f"- {bucket_key}: {', '.join(path.name for path in files)}")
        else:
            lines.append(f"- {bucket_key}: none")

    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend([f"- {warning}" for warning in warnings])
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"
