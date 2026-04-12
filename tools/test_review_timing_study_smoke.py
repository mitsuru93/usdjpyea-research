from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys

import pandas as pd
import yaml

sys.path.append(str(Path(__file__).resolve().parents[1]))
from tools.review_timing_study import build_review


def test_timing_review_reads_current_compare_schema() -> None:
    with TemporaryDirectory() as tmp:
        compare_dir = Path(tmp)
        (compare_dir / "compare_metadata.yaml").write_text(
            yaml.safe_dump(
                {
                    "baseline_label": "baseline_touch",
                    "runs": [{"label": "baseline_touch"}, {"label": "rv_close_confirm"}],
                }
            ),
            encoding="utf-8",
        )
        pd.DataFrame(
            [
                {
                    "baseline_touch_trade_count": 10,
                    "rv_close_confirm_trade_count": 8,
                    "delta_rv_close_confirm_trade_count_vs_baseline": -2,
                    "baseline_touch_avg_pnl_pips": 0.1,
                    "rv_close_confirm_avg_pnl_pips": 0.2,
                    "delta_rv_close_confirm_avg_pnl_pips_vs_baseline": 0.1,
                    "baseline_touch_total_pnl_pips": 1.0,
                    "rv_close_confirm_total_pnl_pips": 1.6,
                    "delta_rv_close_confirm_total_pnl_pips_vs_baseline": 0.6,
                }
            ]
        ).to_csv(compare_dir / "compare_overall.csv", index=False)

        pd.DataFrame(
            [{"candidate_family": "rv", "delta_rv_close_confirm_total_pnl_pips_vs_baseline": 0.6}]
        ).to_csv(compare_dir / "compare_by_family.csv", index=False)

        pd.DataFrame(
            [
                {"timing_decision_event": "('close_confirmed',)", "rv_close_confirm_candidate_count": 3},
                {"timing_decision_event": "('close_rejected',)", "rv_close_confirm_candidate_count": 2},
                {"timing_decision_event": "('touch_entered_immediately',)", "rv_close_confirm_candidate_count": 1},
            ]
        ).to_csv(compare_dir / "compare_timing_by_decision_event.csv", index=False)

        pd.DataFrame(
            [
                {
                    "timing_close_reject_reason": "('close_not_back_inside_band',)",
                    "rv_close_confirm_candidate_count": 2,
                }
            ]
        ).to_csv(compare_dir / "compare_timing_by_reject_reason.csv", index=False)

        pd.DataFrame(
            [
                {
                    "candidate_family": "rv",
                    "timing_close_reject_reason": "('close_not_back_inside_band',)",
                    "delta_rv_close_confirm_candidate_count_vs_baseline": 2,
                }
            ]
        ).to_csv(compare_dir / "compare_timing_by_family_reject_reason.csv", index=False)

        pd.DataFrame(
            [
                {
                    "timing_still_touch_status": "('still_touch_true',)",
                    "delta_rv_close_confirm_candidate_count_vs_baseline": 1,
                },
                {
                    "timing_still_touch_status": "('still_touch_false',)",
                    "delta_rv_close_confirm_candidate_count_vs_baseline": -1,
                },
            ]
        ).to_csv(compare_dir / "compare_timing_by_still_touch_status.csv", index=False)

        review_text, _ = build_review(compare_dir)
        assert "timing decision-event columns unavailable" not in review_text
        assert "reject-reason columns unavailable" not in review_text
        assert "close_not_back_inside_band" in review_text
        assert "still_touch_true" in review_text
