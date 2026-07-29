#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usdjpy_hyp034_bi5_source_v1 import iter_tick_days, m15_bars, source_inventory, tick_day_audit

PROGRAM_ID = "USDJPY-CSOS-DUKASCOPY-NATIVE-REMAINING-FAMILY-ATLAS-V1"
TARGET_TOKENS = [
    "A_FALSE_BREAKOUT_REVERSAL",
    "B_BALANCE_MEAN_REVERSION",
    "C_SHOCK_CONTINUATION",
    "E_TOKYO_LONDON",
    "E_LONDON_NY",
    "E_NY_TOKYO",
    "G_TREND_EXHAUSTION",
    "H_COMPRESSION_BREAKOUT",
    "I_FAILED_TREND_CONTINUATION",
    "K_LONDON_OPENING_RANGE_BREAKOUT",
    "K_ROUND_NUMBER_REJECTION",
    "K_DAILY_TIME_SERIES_MOMENTUM",
]
FORBIDDEN = ("2019", "2020", "2021", "2022", "2025")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def read_tabular(path: Path) -> pd.DataFrame:
    if path.name.endswith(".csv.gz"):
        return pd.read_csv(path, compression="gzip")
    return pd.read_csv(path)


def archive_inventory(atlas_zip: Path, unpacked: Path, out: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    with zipfile.ZipFile(atlas_zip) as zf:
        zf.extractall(unpacked)
        rows = [
            {
                "path": info.filename,
                "byte_size": info.file_size,
                "compressed_size": info.compress_size,
                "crc": info.CRC,
                "is_dir": info.is_dir(),
            }
            for info in zf.infolist()
        ]
    files = sorted(p for p in unpacked.rglob("*") if p.is_file())
    enriched = []
    for path in files:
        rel = path.relative_to(unpacked).as_posix()
        record: dict[str, Any] = {
            "path": rel,
            "byte_size": path.stat().st_size,
            "sha256": sha256(path),
        }
        try:
            if path.name.endswith((".csv", ".csv.gz")):
                frame = read_tabular(path)
                record.update({"kind": "table", "rows": len(frame), "columns": list(frame.columns)})
            elif path.suffix.lower() == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                record.update({"kind": "json", "top_level_type": type(payload).__name__, "keys": sorted(payload) if isinstance(payload, dict) else None})
            else:
                record["kind"] = "other"
        except Exception as exc:
            record.update({"kind": "unreadable", "error": f"{type(exc).__name__}: {exc}"})
        enriched.append(record)
    write_json(out / "old_atlas_archive_inventory.json", {"archive": atlas_zip.name, "archive_sha256": sha256(atlas_zip), "zip_members": rows, "files": enriched})
    return enriched, files


def find_opportunity_ledger(files: list[Path]) -> Path:
    exact = [p for p in files if p.name == "strategy_opportunity_atlas.csv.gz"]
    if len(exact) == 1:
        return exact[0]
    candidates = []
    for p in files:
        if not p.name.endswith((".csv", ".csv.gz")):
            continue
        try:
            cols = set(read_tabular(p).columns)
        except Exception:
            continue
        if {"variant", "signal_utc", "entry_utc", "exit_utc"}.issubset(cols):
            candidates.append(p)
    if len(candidates) != 1:
        raise RuntimeError(f"cannot uniquely identify old Atlas opportunity ledger: {[str(p) for p in candidates]}")
    return candidates[0]


def old_atlas_summary(ledger_path: Path, out: Path) -> dict[str, Any]:
    df = read_tabular(ledger_path)
    for col in ["signal_utc", "entry_utc", "exit_utc"]:
        if col in df:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    variant_col = "variant" if "variant" in df else "variant_id"
    family_col = "family" if "family" in df else "family_id" if "family_id" in df else None
    pnl_col = next((c for c in ["normalized_pl_jpy", "pl_jpy", "net_jpy"] if c in df), None)
    rows = []
    for variant, group in df.groupby(variant_col, dropna=False):
        pnl = pd.to_numeric(group[pnl_col], errors="coerce") if pnl_col else pd.Series(dtype=float)
        gp = float(pnl[pnl > 0].sum()) if len(pnl) else None
        gl = float(-pnl[pnl < 0].sum()) if len(pnl) else None
        rows.append({
            "family_id": str(group[family_col].iloc[0]) if family_col else None,
            "variant_id": str(variant),
            "events": int(len(group)),
            "net_jpy": float(pnl.sum()) if len(pnl) else None,
            "profit_factor": (gp / gl if gl and gl > 0 else None),
            "long_events": int((pd.to_numeric(group.get("side"), errors="coerce") > 0).sum()) if "side" in group else None,
            "short_events": int((pd.to_numeric(group.get("side"), errors="coerce") < 0).sum()) if "side" in group else None,
            "first_signal": group["signal_utc"].min() if "signal_utc" in group else None,
            "last_signal": group["signal_utc"].max() if "signal_utc" in group else None,
        })
    summary = pd.DataFrame(rows).sort_values(["family_id", "variant_id"], na_position="last")
    summary.to_csv(out / "old_atlas_variant_summary.csv", index=False, lineterminator="\n")
    target = summary[summary.variant_id.astype(str).isin(TARGET_TOKENS)].copy()
    target.to_csv(out / "target_old_atlas_variant_summary.csv", index=False, lineterminator="\n")
    write_json(out / "old_atlas_ledger_schema.json", {"path": str(ledger_path), "rows": len(df), "columns": list(df.columns), "dtypes": {c: str(t) for c, t in df.dtypes.items()}, "pnl_column": pnl_col, "variant_column": variant_col, "family_column": family_col})
    return {"ledger_path": str(ledger_path), "rows": len(df), "variant_count": int(df[variant_col].nunique()), "target_token_matches": int(len(target))}


def tick_inventory(raw_dirs: list[Path], out: Path) -> dict[str, Any]:
    inv = source_inventory(raw_dirs)
    day_rows: list[dict[str, Any]] = []
    bar_parts: list[pd.DataFrame] = []
    for day in iter_tick_days(raw_dirs):
        day_rows.append(tick_day_audit(day))
        bars = m15_bars(day)
        if len(bars):
            bar_parts.append(bars)
    days = pd.DataFrame(day_rows)
    bars = pd.concat(bar_parts, ignore_index=True) if bar_parts else pd.DataFrame()
    if len(bars):
        bars["bar_start_utc"] = pd.to_datetime(bars["bar_start_utc"], utc=True)
        bars = bars[(bars.bar_start_utc >= "2023-01-01") & (bars.bar_start_utc < "2025-01-01")].sort_values("bar_start_utc", kind="mergesort").reset_index(drop=True)
    days.to_csv(out / "dukascopy_tick_day_audit.csv", index=False, lineterminator="\n")
    if len(bars):
        with gzip.GzipFile(filename="", mode="wb", fileobj=(out / "dukascopy_m15_bidask_2023_2024.csv.gz").open("wb"), compresslevel=9, mtime=0) as gz:
            gz.write(bars.to_csv(index=False, lineterminator="\n", float_format="%.10f").encode())
    gaps = bars.bar_start_utc.diff().dt.total_seconds().div(60) if len(bars) else pd.Series(dtype=float)
    result = {
        **inv,
        "day_rows": int(len(days)),
        "tick_count": int(days.tick_count.sum()) if len(days) else 0,
        "ask_bid_inversion_count": int(days.ask_bid_inversion_count.sum()) if len(days) else 0,
        "duplicate_timestamp_count": int(days.duplicate_timestamp_count.sum()) if len(days) else 0,
        "nonmonotonic_timestamp_count": int(days.nonmonotonic_timestamp_count.sum()) if len(days) else 0,
        "m15_bar_count": int(len(bars)),
        "duplicate_m15_bar_count": int(bars.bar_start_utc.duplicated().sum()) if len(bars) else 0,
        "missing_interval_count_gt_15m": int((gaps > 15.000001).sum()) if len(gaps) else 0,
        "max_bar_gap_minutes": float(gaps.max()) if len(gaps) else None,
        "first_bar_utc": bars.bar_start_utc.min() if len(bars) else None,
        "last_bar_utc": bars.bar_start_utc.max() if len(bars) else None,
    }
    write_json(out / "dukascopy_source_inventory.json", clean(result))
    return clean(result)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas-zip", type=Path, required=True)
    ap.add_argument("--atlas-unpacked", type=Path, required=True)
    ap.add_argument("--raw-2023", type=Path, required=True)
    ap.add_argument("--raw-2024", type=Path, required=True)
    ap.add_argument("--baseline-trades", type=Path, required=True)
    ap.add_argument("--prior-study-search", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    inventory, files = archive_inventory(args.atlas_zip, args.atlas_unpacked, out)
    ledger = find_opportunity_ledger(files)
    atlas = old_atlas_summary(ledger, out)
    source = tick_inventory([args.raw_2023, args.raw_2024], out)
    baseline = pd.read_csv(args.baseline_trades)
    baseline_record = {"path": str(args.baseline_trades), "sha256": sha256(args.baseline_trades), "rows": len(baseline), "columns": list(baseline.columns)}
    write_json(out / "canonical_baseline_inventory.json", baseline_record)
    prior = json.loads(args.prior_study_search.read_text(encoding="utf-8"))
    write_json(out / "duplicate_prior_study_audit.json", prior)
    all_names = [p.name for p in [args.atlas_zip, args.baseline_trades, *args.raw_2023.glob("*"), *args.raw_2024.glob("*")]]
    protected_hits = sorted({token for token in FORBIDDEN for name in all_names if token in name})
    final = {
        "schema_version": "usdjpy_csos_dukascopy_native_remaining_family_atlas_inventory_result_v1",
        "program_id": PROGRAM_ID,
        "status": "PASS_SOURCE_AND_OLD_ATLAS_INVENTORY" if source["archive_count"] == 24 and source["ask_bid_inversion_count"] == 0 and source["nonmonotonic_timestamp_count"] == 0 and source["duplicate_m15_bar_count"] == 0 and not protected_hits else "TECHNICAL_NO_RESULT_SOURCE_AUTHORITY",
        "old_atlas": atlas,
        "old_atlas_file_count": len(inventory),
        "source": source,
        "baseline": baseline_record,
        "protected_filename_hits": protected_hits,
        "protected_2020_2022_accessed": False,
        "protected_2025_accessed": False,
        "candidate_outcomes_computed": False,
        "core_modified": False,
        "mt4_executed": False,
        "candidate_freeze": False,
        "production_authorized": False,
        "live_authorized": False,
    }
    write_json(out / "inventory_result.json", clean(final))
    if not str(final["status"]).startswith("PASS"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
