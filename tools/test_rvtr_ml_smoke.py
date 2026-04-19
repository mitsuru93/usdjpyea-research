#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        source_root = temp_root / "source"
        output_root = temp_root / "rvtr_ml"
        run_dir = source_root / "atr04_p14_run"
        run_dir.mkdir(parents=True, exist_ok=True)
        output_root.mkdir(parents=True, exist_ok=True)

        audit_df = _build_synthetic_audit_rows()
        outcome_df = audit_df.loc[:, ["candidate_id", "pnl_pips"]].copy()

        audit_df.to_csv(run_dir / "candidates_decision_policy_audit.csv", index=False)
        outcome_df.to_csv(run_dir / "candidates_aggregate.csv.gz", index=False, compression="gzip")

        (run_dir / "run_metadata.yaml").write_text(
            yaml.safe_dump(
                {
                    "input_csv": str(temp_root / "synthetic_ohlc.csv"),
                    "symbol": "USDJPY",
                    "timeframe": "M1",
                    "feature_set_version": "feature_set_v1",
                    "assumption_version": "sim_v1_conservative",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (run_dir / "effective_band_config.yaml").write_text(
            yaml.safe_dump(
                {
                    "band_model": "atr",
                    "band_atr_k": 0.4,
                    "band_atr_period": 14,
                    "band_token": "ATR04_P14",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        ohlc_df = _build_synthetic_ohlc()
        ohlc_df.to_csv(temp_root / "synthetic_ohlc.csv", index=False)

        _run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "build_rvtr_label_table.py"),
                "--source-root",
                str(source_root),
                "--output-dir",
                str(output_root),
            ],
            cwd=REPO_ROOT,
        )

        trainable = output_root / "rvtr_label_table_trainable_v1.csv.gz"
        assert trainable.exists(), "missing trainable label table"

        _run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "train_rvtr_logit_v1.py"),
                "--label-table",
                str(trainable),
                "--output-dir",
                str(output_root),
            ],
            cwd=REPO_ROOT,
        )

        coef_csv = output_root / "rvtr_logit_v1_coef.csv"
        assert coef_csv.exists()

        _run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "distill_rvtr_score_v1.py"),
                "--coef-csv",
                str(coef_csv),
                "--output-dir",
                str(output_root),
            ],
            cwd=REPO_ROOT,
        )

        distilled_yaml = output_root / "distilled_total_score_rvtr_v2.yaml"
        review_dir = output_root / "review"
        _run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "review_rvtr_ml.py"),
                "--control-run-dir",
                str(run_dir),
                "--current-run-dir",
                str(run_dir),
                "--distilled-run-dir",
                str(run_dir),
                "--coef-csv",
                str(coef_csv),
                "--distilled-yaml",
                str(distilled_yaml),
                "--output-dir",
                str(review_dir),
            ],
            cwd=REPO_ROOT,
        )

        assert (review_dir / "rvtr_ml_review.md").exists()
        assert (review_dir / "rvtr_ml_compare.csv").exists()
        assert (review_dir / "rvtr_ml_by_month.csv").exists()
        assert (review_dir / "rvtr_ml_by_session.csv").exists()
        assert (review_dir / "rvtr_ml_by_band.csv").exists()
        print("rvtr ml smoke test passed")


def _build_synthetic_ohlc() -> pd.DataFrame:
    frames = []
    for start, base, drift in [("2024-01-01", 150.0, 0.02), ("2025-01-01", 160.0, -0.015), ("2025-11-01", 170.0, 0.01)]:
        ts = pd.date_range(start=start, periods=70, freq="D")
        idx = np.arange(len(ts), dtype=float)
        close = base + (idx * drift) + np.sin(idx / 4.0) * 0.35
        open_ = close + np.where(idx % 2 == 0, -0.08, 0.08)
        high = np.maximum(open_, close) + 0.25
        low = np.minimum(open_, close) - 0.25
        frames.append(pd.DataFrame({"datetime": ts, "open": open_, "high": high, "low": low, "close": close}))
    return pd.concat(frames, ignore_index=True)


def _build_synthetic_audit_rows() -> pd.DataFrame:
    rows = []
    scenarios = [
        ("2024-01-11", "ASIA", "upper", 1),
        ("2024-01-21", "LONDON", "upper", -1),
        ("2024-02-11", "ASIA", "lower", 1),
        ("2025-01-11", "LONDON", "lower", -1),
    ]
    for timestamp_text, session, touch_side, sign in scenarios:
        for family, direction, pnl in [
            ("rev", "buy" if touch_side == "lower" else "sell", 8.0 if sign > 0 else -7.0),
            ("trend", "sell" if touch_side == "lower" else "buy", 2.0 if sign > 0 else 11.0),
        ]:
            rows.append(
                {
                    "candidate_id": f"{timestamp_text}_{touch_side}_{family}",
                    "timestamp": timestamp_text,
                    "touch_side": touch_side,
                    "candidate_family": family,
                    "direction": direction,
                    "session": session.lower(),
                    "month": timestamp_text[:7],
                    "band_token": "ATR04_P14",
                    "band_model": "atr",
                    "band_model_family": "atr",
                    "selected_by_decision_policy": True,
                    "decision_policy_outcome": "include",
                    "final_decision": family,
                    "hard_gate_passed": True,
                    "group_status": "complete_unique_pair",
                    "label_gap_rv_minus_tr_pips": pnl,
                    "label_rvtr_v1": "rv" if pnl > 0 else "tr",
                    "pnl_pips": pnl,
                    "dist_from_ema_pips": 0.35,
                    "envelope_upper": 0.75,
                    "envelope_lower": -0.05,
                    "upper_env": 0.75,
                    "lower_env": -0.05,
                    "atr14_pips": 1.5,
                    "atr5_pips": 1.3,
                    "atr_ratio_5_14": 1.3 / 1.5,
                    "pre10_change_pips": 5.0 if sign > 0 else -4.0,
                    "pre30_change_pips": 7.5 if sign > 0 else -6.0,
                    "pre60_change_pips": 10.0 if sign > 0 else -8.0,
                    "net10_change_pips": 3.0 if sign > 0 else -2.4,
                    "rsi14": 48.0 if session == "ASIA" else 58.0,
                    "macd_hist": 0.03 if sign > 0 else -0.02,
                    "bb_width_ratio_to_close": 0.0015,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()
