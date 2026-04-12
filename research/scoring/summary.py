"""Summary aggregation for simulator v1 outcomes."""

from __future__ import annotations

import pandas as pd


def summarize_outcomes(outcomes_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build overall and grouped summaries."""
    return {
        "overall": _summarize_group(outcomes_df, []),
        "by_month": _summarize_group(outcomes_df, ["month"]),
        "by_session": _summarize_group(outcomes_df, ["session"]),
        "by_family": _summarize_group(outcomes_df, ["candidate_family"]),
    }


def summarize_timing_audit(timing_audit_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build timing-event summaries for audit comparisons."""
    return {
        "overall": _summarize_timing_group(timing_audit_df, []),
        "by_month": _summarize_timing_group(timing_audit_df, ["month"]),
        "by_session": _summarize_timing_group(timing_audit_df, ["session"]),
        "by_family": _summarize_timing_group(timing_audit_df, ["candidate_family"]),
    }


def summarize_timing_diagnostics(timing_audit_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build compact timing-diagnostic summaries for interpretation."""
    return {
        "timing_by_decision_event": _summarize_timing_diagnostic_group(timing_audit_df, ["timing_decision_event"]),
        "timing_by_reject_reason": _summarize_timing_diagnostic_group(
            _close_rejected_only(timing_audit_df), ["timing_close_reject_reason"]
        ),
        "timing_by_family_decision_event": _summarize_timing_diagnostic_group(
            timing_audit_df, ["candidate_family", "timing_decision_event"]
        ),
        "timing_by_family_reject_reason": _summarize_timing_diagnostic_group(
            _close_rejected_only(timing_audit_df), ["candidate_family", "timing_close_reject_reason"]
        ),
        "timing_by_still_touch_status": _summarize_timing_diagnostic_group(
            _close_decision_only(timing_audit_df), ["timing_still_touch_status"]
        ),
    }


def _summarize_group(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        base_cols = group_cols + [
            "trade_count",
            "win_count",
            "loss_count",
            "timeout_count",
            "win_rate",
            "avg_pnl_pips",
            "total_pnl_pips",
        ]
        return pd.DataFrame(columns=base_cols)

    if group_cols:
        grouped = df.groupby(group_cols, dropna=False)
    else:
        grouped = [("overall", df)]

    rows = []
    for key, part in grouped:
        row = {}
        if group_cols:
            if len(group_cols) == 1:
                row[group_cols[0]] = key
            else:
                row.update(dict(zip(group_cols, key)))

        trade_count = len(part)
        win_count = int((part["outcome_status"] == "win").sum())
        loss_count = int((part["outcome_status"] == "loss").sum())
        timeout_count = int((part["outcome_status"] == "timeout").sum())

        row.update(
            {
                "trade_count": trade_count,
                "win_count": win_count,
                "loss_count": loss_count,
                "timeout_count": timeout_count,
                "win_rate": (win_count / trade_count) if trade_count else 0.0,
                "avg_pnl_pips": float(part["pnl_pips"].mean()) if trade_count else 0.0,
                "total_pnl_pips": float(part["pnl_pips"].sum()) if trade_count else 0.0,
            }
        )
        rows.append(row)

    return pd.DataFrame(rows)


def _summarize_timing_group(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    base_cols = group_cols + [
        "candidate_created_count",
        "touch_entered_immediately_count",
        "close_confirmed_count",
        "close_rejected_count",
        "still_touch_at_close_true_count",
        "still_touch_at_close_false_count",
    ]
    if df.empty:
        return pd.DataFrame(columns=base_cols)

    if group_cols:
        grouped = df.groupby(group_cols, dropna=False)
    else:
        grouped = [("overall", df)]

    rows = []
    for key, part in grouped:
        row: dict[str, object] = {}
        if group_cols:
            if len(group_cols) == 1:
                row[group_cols[0]] = key
            else:
                row.update(dict(zip(group_cols, key)))

        still_touch = part["timing_still_touch_at_close"].fillna(False).astype(bool)
        row.update(
            {
                "candidate_created_count": int(len(part)),
                "touch_entered_immediately_count": int((part["timing_decision_event"] == "touch_entered_immediately").sum()),
                "close_confirmed_count": int((part["timing_decision_event"] == "close_confirmed").sum()),
                "close_rejected_count": int((part["timing_decision_event"] == "close_rejected").sum()),
                "still_touch_at_close_true_count": int(still_touch.sum()),
                "still_touch_at_close_false_count": int((~still_touch).sum()),
            }
        )
        rows.append(row)

    return pd.DataFrame(rows)


def _close_decision_only(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    mask = df["timing_decision_event"].isin(["close_confirmed", "close_rejected"])
    close_df = df.loc[mask].copy()
    close_df["timing_still_touch_status"] = close_df["timing_still_touch_at_close"].fillna(False).map(
        {True: "still_touch_true", False: "still_touch_false"}
    )
    return close_df


def _close_rejected_only(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df.loc[df["timing_decision_event"] == "close_rejected"].copy()


def _summarize_timing_diagnostic_group(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    base_cols = group_cols + [
        "candidate_count",
        "close_confirmed_count",
        "close_rejected_count",
        "still_touch_at_close_true_count",
        "still_touch_at_close_false_count",
    ]
    if df.empty:
        return pd.DataFrame(columns=base_cols)

    grouped = df.groupby(group_cols, dropna=False)
    rows = []
    for key, part in grouped:
        row: dict[str, object] = {}
        if len(group_cols) == 1:
            row[group_cols[0]] = key
        else:
            row.update(dict(zip(group_cols, key)))

        still_touch = part["timing_still_touch_at_close"].fillna(False).astype(bool)
        row.update(
            {
                "candidate_count": int(len(part)),
                "close_confirmed_count": int((part["timing_decision_event"] == "close_confirmed").sum()),
                "close_rejected_count": int((part["timing_decision_event"] == "close_rejected").sum()),
                "still_touch_at_close_true_count": int(still_touch.sum()),
                "still_touch_at_close_false_count": int((~still_touch).sum()),
            }
        )
        rows.append(row)

    return pd.DataFrame(rows)
