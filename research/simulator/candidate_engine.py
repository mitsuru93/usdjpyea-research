"""Candidate generation from envelope touch events.

This module intentionally labels candidates conservatively and does NOT
attempt to reproduce full MT4 entry gating/position semantics.

`entry_price` is a signal reference price (touch-bar close), not a broker fill.
"""

from __future__ import annotations

import hashlib
import pandas as pd

ASSUMPTION_VERSION = "sim_v1_conservative"
TIMING_MODES = {"baseline_touch", "rv_close_confirm", "all_close"}
DEFAULT_TIMING_MODE = "baseline_touch"
TP_SL_BY_FAMILY = {
    "rev": {"tp_pips": 10, "sl_pips": 30},
    "trend": {"tp_pips": 10, "sl_pips": 20},
}


def build_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Generate candidate rows from touch events.

    Mapping:
    - upper touch => rev sell, trend buy
    - lower touch => rev buy, trend sell
    """
    candidate_rows: list[dict] = []

    for row in df.itertuples(index=False):
        if row.touch_upper:
            candidate_rows.extend(
                [
                    _make_candidate(row, touch_side="upper", family="rev", direction="sell"),
                    _make_candidate(row, touch_side="upper", family="trend", direction="buy"),
                ]
            )
        if row.touch_lower:
            candidate_rows.extend(
                [
                    _make_candidate(row, touch_side="lower", family="rev", direction="buy"),
                    _make_candidate(row, touch_side="lower", family="trend", direction="sell"),
                ]
            )

    return pd.DataFrame(candidate_rows)


def apply_timing_mode(
    candidates_df: pd.DataFrame,
    env_df: pd.DataFrame,
    timing_mode: str = DEFAULT_TIMING_MODE,
) -> dict[str, pd.DataFrame]:
    """Apply experiment timing mode and return entry rows + full timing audit.

    Semantics:
    - baseline_touch:
      - all touch candidates enter immediately from touch evidence.
    - rv_close_confirm:
      - RV candidates are *created* from intrabar touch evidence, then final entry
        decision is made at bar close.
      - close decision does NOT require still-touch-at-close.
      - trend-family timing remains baseline-equivalent (touch-entered).
    - all_close:
      - research comparison mode only; all families use close-time decision.

    Conservative close decision in this research approximation:
    - reject close-time candidates when both upper/lower were touched in the same
      source bar (ambiguous intrabar path).
    - otherwise confirm only if close is back inside the touched envelope side:
      - upper-touch candidate => close < upper_env
      - lower-touch candidate => close > lower_env
      - else reject with close_not_back_inside_band
    """
    mode = str(timing_mode).strip().lower()
    if mode not in TIMING_MODES:
        raise ValueError(f"Unsupported timing_mode='{timing_mode}'. Allowed: {sorted(TIMING_MODES)}")

    if candidates_df.empty:
        return {
            "timing_audit_df": candidates_df.copy(),
            "entered_df": candidates_df.copy(),
        }

    source = env_df[["datetime", "touch_upper", "touch_lower", "upper_env", "lower_env", "close"]].copy()
    source = source.rename(
        columns={
            "datetime": "timestamp",
            "close": "bar_close_price",
        }
    )
    source["close_decision_reject_ambiguous_touch"] = source["touch_upper"] & source["touch_lower"]

    merged = candidates_df.merge(source, on="timestamp", how="left", validate="many_to_one")
    missing_src = merged["bar_close_price"].isna()
    if bool(missing_src.any()):
        raise ValueError("Timing mode application failed: candidate timestamp missing from envelope frame.")

    merged["timing_mode"] = mode
    merged["timing_candidate_created"] = True
    merged["timing_decision_event"] = "touch_entered_immediately"
    merged["timing_entered"] = True
    merged["timing_close_confirmed"] = False
    merged["timing_close_rejected"] = False
    merged["timing_close_reject_reason"] = ""
    merged["timing_still_touch_at_close"] = _compute_still_touch_at_close(merged)

    close_mask = _build_close_decision_mask(merged, mode)
    if bool(close_mask.any()):
        ambiguous_reject_mask = close_mask & merged["close_decision_reject_ambiguous_touch"]
        close_not_inside_reject_mask = close_mask & ~merged["close_decision_reject_ambiguous_touch"] & ~_is_back_inside_band(merged)
        reject_mask = ambiguous_reject_mask | close_not_inside_reject_mask
        confirm_mask = close_mask & ~reject_mask

        merged.loc[close_mask, "timing_decision_event"] = "close_confirmed"
        merged.loc[confirm_mask, "timing_close_confirmed"] = True
        merged.loc[reject_mask, "timing_decision_event"] = "close_rejected"
        merged.loc[reject_mask, "timing_close_rejected"] = True
        merged.loc[reject_mask, "timing_entered"] = False
        merged.loc[ambiguous_reject_mask, "timing_close_reject_reason"] = "ambiguous_dual_touch_same_bar"
        merged.loc[close_not_inside_reject_mask, "timing_close_reject_reason"] = "close_not_back_inside_band"

    audit_cols_to_drop = [
        "touch_upper",
        "touch_lower",
        "upper_env",
        "lower_env",
        "bar_close_price",
        "close_decision_reject_ambiguous_touch",
    ]
    timing_audit_df = merged.drop(columns=audit_cols_to_drop)
    entered_df = timing_audit_df[timing_audit_df["timing_entered"]].copy()

    return {
        "timing_audit_df": timing_audit_df,
        "entered_df": entered_df,
    }


def _build_close_decision_mask(df: pd.DataFrame, mode: str) -> pd.Series:
    if mode == "all_close":
        return pd.Series(True, index=df.index)
    if mode == "rv_close_confirm":
        return df["candidate_family"] == "rev"
    return pd.Series(False, index=df.index)


def _compute_still_touch_at_close(df: pd.DataFrame) -> pd.Series:
    upper_still_touch = (df["touch_side"] == "upper") & (df["bar_close_price"] >= df["upper_env"])
    lower_still_touch = (df["touch_side"] == "lower") & (df["bar_close_price"] <= df["lower_env"])
    return upper_still_touch | lower_still_touch


def _is_back_inside_band(df: pd.DataFrame) -> pd.Series:
    upper_back_inside = (df["touch_side"] == "upper") & (df["bar_close_price"] < df["upper_env"])
    lower_back_inside = (df["touch_side"] == "lower") & (df["bar_close_price"] > df["lower_env"])
    return upper_back_inside | lower_back_inside


def _make_candidate(row: object, touch_side: str, family: str, direction: str) -> dict:
    levels = TP_SL_BY_FAMILY[family]
    timestamp = row.datetime
    entry_price = float(row.close)
    tp_pips = levels["tp_pips"]
    sl_pips = levels["sl_pips"]
    deterministic_key = "|".join(
        [
            str(timestamp),
            str(touch_side),
            str(family),
            str(direction),
            f"{entry_price:.10f}",
            str(tp_pips),
            str(sl_pips),
            ASSUMPTION_VERSION,
        ]
    )
    candidate_id = hashlib.sha256(deterministic_key.encode("utf-8")).hexdigest()
    return {
        "candidate_id": candidate_id,
        "timestamp": timestamp,
        "session": row.session,
        "month": row.month,
        "touch_side": touch_side,
        "candidate_family": family,
        "direction": direction,
        "entry_price": entry_price,
        "entry_price_type": "signal_reference_price",
        "tp_pips": tp_pips,
        "sl_pips": sl_pips,
        "assumption_version": ASSUMPTION_VERSION,
    }
