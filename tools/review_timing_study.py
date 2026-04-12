#!/usr/bin/env python3
"""Generate a compact post-run markdown review for timing-study compare outputs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read completed timing-study compare outputs and generate a compact markdown review "
            "(convenience layer only; pre-MT4 research context)."
        )
    )
    parser.add_argument("--study-dir", help="Study output root containing compare/", default=None)
    parser.add_argument("--compare-dir", help="Compare output directory", default=None)
    args = parser.parse_args()

    if bool(args.study_dir) == bool(args.compare_dir):
        parser.error("Provide exactly one of --study-dir or --compare-dir")
    return args


def safe_label(label: str) -> str:
    return label.strip().replace(" ", "_").replace("/", "_")


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _fmt_intlike(value: float | None) -> str:
    if value is None:
        return "n/a"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.3f}"


TUPLE_LIKE_SINGLETON_RE = re.compile(r"""^\(\s*['"]([^'"]+)['"]\s*,\s*\)$""")


def _normalize_tuple_like_label(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    match = TUPLE_LIKE_SINGLETON_RE.match(text)
    if match:
        return match.group(1)
    return text


def _pick_prefixed_metric_col(df: pd.DataFrame, token: str, metric_candidates: list[str]) -> str | None:
    for metric in metric_candidates:
        prefixed = f"{token}_{metric}"
        if prefixed in df.columns:
            return prefixed
    return None


def _pick_delta_metric_col(df: pd.DataFrame, token: str, metric_candidates: list[str]) -> str | None:
    for metric in metric_candidates:
        prefixed = f"delta_{token}_{metric}_vs_baseline"
        if prefixed in df.columns:
            return prefixed
        generic = f"delta_{metric}_vs_baseline"
        if generic in df.columns:
            return generic
    return None


def resolve_compare_dir(study_dir: str | None, compare_dir: str | None) -> Path:
    if compare_dir:
        path = Path(compare_dir).resolve()
    else:
        study_path = Path(study_dir).resolve()
        compare_candidate = study_path / "compare"
        if compare_candidate.exists() and compare_candidate.is_dir():
            path = compare_candidate
        else:
            path = study_path

    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Compare directory not found: {path}")
    return path


def load_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def load_metadata(compare_dir: Path) -> dict[str, Any]:
    metadata_path = compare_dir / "compare_metadata.yaml"
    if not metadata_path.exists():
        return {}
    with metadata_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def detect_run_labels(metadata: dict[str, Any], compare_overall: pd.DataFrame | None) -> list[str]:
    runs = metadata.get("runs", []) if isinstance(metadata, dict) else []
    labels = [str(run.get("label", "")).strip() for run in runs if str(run.get("label", "")).strip()]
    if labels:
        return labels

    if compare_overall is None:
        return []

    labels_from_cols: set[str] = set()
    for col in compare_overall.columns:
        if col.endswith("_trade_count"):
            labels_from_cols.add(col[: -len("_trade_count")])
    return sorted(labels_from_cols)


def build_variant_metric_snapshot(row: pd.Series, baseline_label: str, variant_label: str) -> list[str]:
    baseline_token = safe_label(baseline_label)
    variant_token = safe_label(variant_label)

    notes: list[str] = []
    for metric, digits, formatter in [
        ("trade_count", 3, _fmt_intlike),
        ("avg_pnl_pips", 3, _fmt),
        ("total_pnl_pips", 3, _fmt),
    ]:
        baseline_col = f"{baseline_token}_{metric}"
        variant_col = f"{variant_token}_{metric}"
        delta_col = f"delta_{variant_token}_{metric}_vs_baseline"

        baseline_val = _to_float(row.get(baseline_col))
        variant_val = _to_float(row.get(variant_col))
        delta_val = _to_float(row.get(delta_col))
        if delta_val is None and baseline_val is not None and variant_val is not None:
            delta_val = variant_val - baseline_val

        notes.append(
            f"- {variant_label} {metric}: {formatter(variant_val)} "
            f"(baseline {formatter(baseline_val)}, delta {formatter(delta_val)})"
        )
    return notes


def dominant_delta_row(df: pd.DataFrame, key_col: str, delta_col: str) -> tuple[str, float] | None:
    if key_col not in df.columns or delta_col not in df.columns or df.empty:
        return None

    work = df.copy()
    work[delta_col] = pd.to_numeric(work[delta_col], errors="coerce").fillna(0.0)
    if work.empty:
        return None

    best_idx = work[delta_col].abs().idxmax()
    row = work.loc[best_idx]
    key = str(row.get(key_col, ""))
    value = float(row.get(delta_col, 0.0))
    return key, value


def summarize_decision_events(df: pd.DataFrame, variant_label: str) -> list[str]:
    token = safe_label(variant_label)
    count_col = _pick_prefixed_metric_col(
        df,
        token,
        ["candidate_count", "candidate_created_count", "close_confirmed_count", "close_rejected_count", "trade_count"],
    )
    if "timing_decision_event" not in df.columns or count_col is None:
        return [f"- {variant_label}: timing decision-event columns unavailable."]

    work = df.copy()
    work["timing_decision_event"] = work["timing_decision_event"].map(_normalize_tuple_like_label)
    work[count_col] = pd.to_numeric(work[count_col], errors="coerce").fillna(0.0)

    def count_for(event: str) -> float:
        mask = work["timing_decision_event"].str.lower() == event
        return float(work.loc[mask, count_col].sum())

    confirmed = count_for("close_confirmed")
    rejected = count_for("close_rejected")
    touch_now = count_for("touch_entered_immediately")
    return [
        f"- {variant_label}: close_confirmed={_fmt_intlike(confirmed)}, "
        f"close_rejected={_fmt_intlike(rejected)}, "
        f"touch_entered_immediately={_fmt_intlike(touch_now)}"
    ]


def summarize_reject_reasons(df: pd.DataFrame, variant_label: str) -> list[str]:
    token = safe_label(variant_label)
    count_col = _pick_prefixed_metric_col(df, token, ["candidate_count", "close_rejected_count", "trade_count"])
    if "timing_close_reject_reason" not in df.columns or count_col is None:
        return [f"- {variant_label}: reject-reason columns unavailable."]

    work = df.copy()
    work["timing_close_reject_reason"] = work["timing_close_reject_reason"].map(_normalize_tuple_like_label)
    work[count_col] = pd.to_numeric(work[count_col], errors="coerce").fillna(0.0)
    work = work[work["timing_close_reject_reason"].str.len() > 0]
    if work.empty:
        return [f"- {variant_label}: no reject-reason rows."]

    top = work.sort_values(count_col, ascending=False).head(3)
    lines = []
    for _, row in top.iterrows():
        lines.append(f"- {variant_label}: {row['timing_close_reject_reason']}={_fmt_intlike(float(row[count_col]))}")
    return lines


def build_review(compare_dir: Path) -> tuple[str, Path]:
    metadata = load_metadata(compare_dir)

    file_map = {
        "overall": compare_dir / "compare_overall.csv",
        "by_family": compare_dir / "compare_by_family.csv",
        "timing_decision": compare_dir / "compare_timing_by_decision_event.csv",
        "timing_reject": compare_dir / "compare_timing_by_reject_reason.csv",
        "timing_family_reject": compare_dir / "compare_timing_by_family_reject_reason.csv",
        "timing_still_touch": compare_dir / "compare_timing_by_still_touch_status.csv",
    }
    frames = {name: load_csv_if_exists(path) for name, path in file_map.items()}

    run_labels = detect_run_labels(metadata, frames["overall"])
    baseline_label = str(metadata.get("baseline_label", run_labels[0] if run_labels else "baseline_touch"))
    variant_labels = [label for label in run_labels if label != baseline_label]

    lines: list[str] = [
        "# Timing Study Review (Post-Run Convenience)",
        "",
        "This is a compact, deterministic convenience readout from compare CSVs.",
        "It is pre-MT4 research-only and not a production or MT4-parity validation.",
        "",
        f"- compare_dir: `{compare_dir}`",
    ]

    if run_labels:
        lines.append(f"- detected run labels: {', '.join(run_labels)}")
    else:
        lines.append("- detected run labels: unavailable")

    lines.append(f"- baseline label: {baseline_label}")

    missing = [name for name, frame in frames.items() if frame is None]
    if missing:
        lines.append(f"- unavailable compare inputs: {', '.join(missing)}")
    else:
        lines.append("- unavailable compare inputs: none")

    lines.extend(["", "## Top-line notes (`compare_overall.csv`)", ""])
    overall = frames["overall"]
    if overall is None or overall.empty:
        lines.append("- compare_overall.csv unavailable or empty.")
    else:
        row = overall.iloc[0]
        for variant in variant_labels:
            lines.extend(build_variant_metric_snapshot(row, baseline_label, variant))

    lines.extend(["", "## Family-level notes (`compare_by_family.csv`)", ""])
    by_family = frames["by_family"]
    if by_family is None or by_family.empty:
        lines.append("- compare_by_family.csv unavailable or empty.")
    else:
        key_col = "candidate_family"
        if key_col not in by_family.columns:
            lines.append("- candidate_family column unavailable.")
        else:
            lines.append(
                "- Focus check: whether RV rows carry most of the change vs baseline (using absolute delta_total_pnl_pips where available)."
            )
            for variant in variant_labels:
                delta_col = f"delta_{safe_label(variant)}_total_pnl_pips_vs_baseline"
                if delta_col not in by_family.columns:
                    delta_col = "delta_total_pnl_pips_vs_baseline"
                hit = dominant_delta_row(by_family, key_col=key_col, delta_col=delta_col)
                if hit is None:
                    lines.append(f"- {variant}: family delta columns unavailable.")
                else:
                    fam, val = hit
                    lines.append(f"- {variant}: largest |family total pnl delta| = {fam} ({_fmt(val)} pips).")

    lines.extend(["", "## Timing decision-event summary (`compare_timing_by_decision_event.csv`)", ""])
    timing_decision = frames["timing_decision"]
    if timing_decision is None or timing_decision.empty:
        lines.append("- compare_timing_by_decision_event.csv unavailable or empty.")
    else:
        targets = variant_labels if variant_labels else run_labels
        for label in targets:
            lines.extend(summarize_decision_events(timing_decision, label))

    lines.extend(["", "## Timing reject-reason summary (`compare_timing_by_reject_reason.csv`)", ""])
    timing_reject = frames["timing_reject"]
    if timing_reject is None or timing_reject.empty:
        lines.append("- compare_timing_by_reject_reason.csv unavailable or empty.")
    else:
        targets = variant_labels if variant_labels else run_labels
        for label in targets:
            lines.extend(summarize_reject_reasons(timing_reject, label))

    lines.extend(["", "## Family reject-reason summary (`compare_timing_by_family_reject_reason.csv`)", ""])
    timing_family_reject = frames["timing_family_reject"]
    if timing_family_reject is None or timing_family_reject.empty:
        lines.append("- compare_timing_by_family_reject_reason.csv unavailable or empty.")
    else:
        for variant in variant_labels:
            delta_col = _pick_delta_metric_col(
                timing_family_reject, safe_label(variant), ["candidate_count", "close_rejected_count", "trade_count"]
            )
            timing_family_reject = timing_family_reject.copy()
            if "timing_close_reject_reason" in timing_family_reject.columns:
                timing_family_reject["timing_close_reject_reason"] = timing_family_reject["timing_close_reject_reason"].map(
                    _normalize_tuple_like_label
                )
            hit = dominant_delta_row(timing_family_reject, key_col="timing_close_reject_reason", delta_col=delta_col)
            if hit is None:
                lines.append(f"- {variant}: unable to derive dominant family reject reason delta.")
            else:
                reason, val = hit
                lines.append(f"- {variant}: dominant family reject-reason delta appears to be {reason} ({_fmt(val)} trades).")

    lines.extend(["", "## Still-touch-status summary (`compare_timing_by_still_touch_status.csv`)", ""])
    still_touch = frames["timing_still_touch"]
    if still_touch is None or still_touch.empty:
        lines.append("- compare_timing_by_still_touch_status.csv unavailable or empty.")
    else:
        key_col = "timing_still_touch_status"
        if key_col not in still_touch.columns:
            lines.append("- timing_still_touch_status column unavailable.")
        else:
            still_touch = still_touch.copy()
            still_touch[key_col] = still_touch[key_col].map(_normalize_tuple_like_label)
            for variant in variant_labels:
                delta_col = _pick_delta_metric_col(
                    still_touch,
                    safe_label(variant),
                    ["candidate_count", "still_touch_at_close_true_count", "still_touch_at_close_false_count", "trade_count"],
                )
                hit = dominant_delta_row(still_touch, key_col=key_col, delta_col=delta_col)
                if hit is None:
                    lines.append(f"- {variant}: still-touch delta unavailable.")
                else:
                    status, val = hit
                    lines.append(f"- {variant}: largest still-touch trade-count delta = {status} ({_fmt(val)}).")

    lines.extend(["", "## Interpretation (transparent first pass)", ""])
    rv_label = next((label for label in run_labels if label.lower() == "rv_close_confirm"), None)
    all_close_label = next((label for label in run_labels if label.lower() == "all_close"), None)
    interpretation_count = 0

    if rv_label and overall is not None and not overall.empty:
        row = overall.iloc[0]
        rv_token = safe_label(rv_label)
        delta_trade = _to_float(row.get(f"delta_{rv_token}_trade_count_vs_baseline"))
        delta_avg = _to_float(row.get(f"delta_{rv_token}_avg_pnl_pips_vs_baseline"))
        direction_trade = "reduced" if (delta_trade or 0.0) < 0 else "increased"
        direction_avg = "improving" if (delta_avg or 0.0) > 0 else "worsening"
        lines.append(
            f"- `{rv_label}` {direction_trade} trade count by {_fmt_intlike(delta_trade)} and was {direction_avg} avg pnl by {_fmt(delta_avg)} pips versus `{baseline_label}`."
        )
        interpretation_count += 1
    elif rv_label:
        lines.append(f"- `{rv_label}` interpretation unavailable because compare_overall.csv is missing.")
        interpretation_count += 1

    if rv_label and timing_reject is not None and not timing_reject.empty:
        token = safe_label(rv_label)
        count_col = _pick_prefixed_metric_col(timing_reject, token, ["candidate_count", "close_rejected_count", "trade_count"])
        if count_col and "timing_close_reject_reason" in timing_reject.columns:
            work = timing_reject.copy()
            work[count_col] = pd.to_numeric(work[count_col], errors="coerce").fillna(0.0)
            work["timing_close_reject_reason"] = work["timing_close_reject_reason"].map(_normalize_tuple_like_label)
            work = work[work["timing_close_reject_reason"].str.len() > 0]
            if not work.empty:
                top = work.sort_values(count_col, ascending=False).iloc[0]
                lines.append(
                    f"- `{rv_label}` rejects were mainly `{top['timing_close_reject_reason']}` ({_fmt_intlike(float(top[count_col]))})."
                )
                interpretation_count += 1

    if all_close_label:
        lines.append(
            f"- `{all_close_label}` acts as a broader timing perturbation and should be treated as a comparison reference, not a default target mode."
        )
        interpretation_count += 1

    if interpretation_count == 0:
        lines.append("- No mode-specific interpretation available from the current compare artifacts.")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This helper only reads existing compare outputs and writes this additional markdown file.",
            "- Existing run/analysis/compare runtime behavior and CSV outputs are unchanged.",
            "- Use this as a quick first read, then inspect raw compare CSVs directly.",
        ]
    )

    out_path = compare_dir / "timing_study_review.md"
    return "\n".join(lines) + "\n", out_path


def main() -> None:
    args = parse_args()
    compare_dir = resolve_compare_dir(args.study_dir, args.compare_dir)
    text, out_path = build_review(compare_dir)
    out_path.write_text(text, encoding="utf-8")
    print(f"Timing study review written: {out_path}")


if __name__ == "__main__":
    main()
