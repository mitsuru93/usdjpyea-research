from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from run_usdjpy_r1_entry_registry_v2 import SIGNAL_FUNCTIONS
from usdjpy_fixed5_portability_lib_v1 import hard_excl, norm_def, sha, canon_json

PIP = 0.01
HORIZONS = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48]
FOLDS = {
    "2023H1": (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2023-07-01", tz="UTC")),
    "2023H2": (pd.Timestamp("2023-07-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC")),
    "2024H1": (pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2024-07-01", tz="UTC")),
    "2024H2": (pd.Timestamp("2024-07-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
}
EXPECTED = {
    "m15_2023": "4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78",
    "m15_2024": "1566b9d0497f3a2aa156868144d31b89721fca48329feaf82035826ada7ee25c",
    "r1_signals": "99c2e2d19bd76b2438c1cec6c777228f82cdca16eeb1b471257bd389d6b7dc9e",
    "r1_registry": "3bb43eeb1234ec6d175e37df3b1bbdb385364857351938bd088247ab14567549",
    "r2_summary": "fa46a5db3e73c4d25b8e8c97ef4727c39d737cc8823080b23d21b0419d9e44f6",
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def profit_factor(values: pd.Series) -> float:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def load_candidates(path: Path) -> list[dict[str, Any]]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for family_block in registry["families"]:
        family = str(family_block["family"])
        for raw in family_block["candidates"]:
            candidate = dict(raw)
            candidate["family"] = family
            rows.append(
                {
                    "candidate_id": str(candidate["id"]),
                    "family": family,
                    "definition_sha256": sha(canon_json(norm_def(candidate))),
                    "candidate": candidate,
                }
            )
    rows.sort(key=lambda row: row["candidate_id"])
    if len(rows) != 60 or len({row["candidate_id"] for row in rows}) != 60:
        raise RuntimeError("R1-v2 candidate universe is not exactly 60 unique entries")
    return rows


def build_all_signals(
    bars: pd.DataFrame,
    candidates: list[dict[str, Any]],
    start: pd.Timestamp,
    end: pd.Timestamp,
    fold: str,
) -> pd.DataFrame:
    prepared = bars.copy()
    if "bar_range" not in prepared:
        prepared["bar_range"] = prepared["mid_high"] - prepared["mid_low"]
    frames: list[pd.DataFrame] = []
    for row in candidates:
        candidate = row["candidate"]
        side = SIGNAL_FUNCTIONS[candidate["family"]](prepared, candidate)
        work = pd.DataFrame({
            "signal_dt": prepared["timestamp_utc"],
            "entry_dt": prepared["timestamp_utc"].shift(-1),
            "side": side,
        })
        work = work[work["side"].isin([1, -1]) & work["entry_dt"].notna()].copy()
        work = work[(work["entry_dt"] >= start) & (work["entry_dt"] < end)].copy()
        work = work[~hard_excl(work["entry_dt"])].copy()
        work["candidate_id"] = candidate["id"]
        work["family"] = candidate["family"]
        work["definition_sha256"] = sha(canon_json(norm_def(candidate)))
        work["signal_ts"] = work["signal_dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        work["entry_ts"] = work["entry_dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        work["signal_month"] = work["signal_dt"].dt.strftime("%Y-%m")
        work["signal_hour_utc"] = work["signal_dt"].dt.hour.astype(int)
        work["entry_month"] = work["entry_dt"].dt.strftime("%Y-%m")
        work["entry_hour_utc"] = work["entry_dt"].dt.hour.astype(int)
        frames.append(work[[
            "candidate_id", "family", "definition_sha256", "signal_ts", "entry_ts", "side",
            "signal_month", "signal_hour_utc", "entry_month", "entry_hour_utc",
        ]])
    out = pd.concat(frames, ignore_index=True)
    out["fold"] = fold
    return out.sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True)


def regress_h1_signals(actual: pd.DataFrame, accepted_path: Path) -> dict[str, Any]:
    accepted = pd.read_csv(accepted_path)
    columns = [
        "candidate_id", "family", "definition_sha256", "signal_ts", "entry_ts", "side",
        "signal_month", "signal_hour_utc", "entry_month", "entry_hour_utc",
    ]
    expected = accepted[columns].sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True)
    observed = actual[columns].sort_values(["candidate_id", "signal_ts", "side"]).reset_index(drop=True)
    for frame in (expected, observed):
        frame[["side", "signal_hour_utc", "entry_hour_utc"]] = frame[["side", "signal_hour_utc", "entry_hour_utc"]].astype("int64")
    return {"accepted_rows": len(expected), "actual_rows": len(observed), "exact": bool(expected.equals(observed))}


def build_trades(
    bars: pd.DataFrame,
    signals: pd.DataFrame,
    fold: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    index_map = pd.Series(bars.index.to_numpy(), index=bars["timestamp_utc"]).to_dict()
    opens = bars["mid_open"].to_numpy(float)
    closes = bars["mid_close"].to_numpy(float)
    spreads = bars["spread_mean_pips"].to_numpy(float)
    timestamps = bars["timestamp_utc"].tolist()
    months = bars["month_utc"].to_numpy(str)
    dates = bars["date_utc"].to_numpy(str)

    work = signals.copy()
    work["entry_dt"] = pd.to_datetime(work["entry_ts"], utc=True)
    work["entry_index"] = work["entry_dt"].map(index_map)
    if work["entry_index"].isna().any():
        raise RuntimeError(f"missing entry bar in {fold}")
    entry_indices = work["entry_index"].astype(int).to_numpy()
    sides = work["side"].astype(int).to_numpy()
    cids = work["candidate_id"].to_numpy(str)
    families = work["family"].to_numpy(str)
    definitions = work["definition_sha256"].to_numpy(str)
    signal_ts = work["signal_ts"].to_numpy(str)
    entry_ts = work["entry_ts"].to_numpy(str)

    frames: list[pd.DataFrame] = []
    for horizon in HORIZONS:
        exit_indices = entry_indices + horizon - 1
        positions = np.where(exit_indices < len(bars))[0]
        if not len(positions):
            continue
        ei = entry_indices[positions]
        xi = exit_indices[positions]
        valid = (months[ei] == months[xi]) & np.array([timestamps[i] < end for i in xi]) & np.array([timestamps[i] >= start for i in ei])
        positions = positions[valid]
        if not len(positions):
            continue
        ei = entry_indices[positions]
        xi = exit_indices[positions]
        side = sides[positions]
        entry_mid = opens[ei]
        exit_mid = closes[xi]
        default_cost = np.maximum(0.5, spreads[ei])
        severe_cost = default_cost * 3.0 + 1.0
        gross = side * (exit_mid - entry_mid) / PIP
        frames.append(
            pd.DataFrame(
                {
                    "fold": fold,
                    "candidate_id": cids[positions],
                    "family": families[positions],
                    "definition_sha256": definitions[positions],
                    "horizon_bars": horizon,
                    "signal_ts": signal_ts[positions],
                    "entry_ts": entry_ts[positions],
                    "exit_ts": [timestamps[i].strftime("%Y-%m-%dT%H:%M:%SZ") for i in xi],
                    "entry_month": months[ei],
                    "entry_date_utc": dates[ei],
                    "side": side,
                    "gross_pips": gross,
                    "default_net_pips": gross - default_cost,
                    "severe_net_pips": gross - severe_cost,
                }
            )
        )
    return pd.concat(frames, ignore_index=True).sort_values(["candidate_id", "horizon_bars", "entry_ts", "side"]).reset_index(drop=True)


def aggregate_cell_fold(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["candidate_id", "family", "definition_sha256", "horizon_bars", "fold"]
    for key, group in trades.groupby(keys, sort=True):
        monthly = group.groupby("entry_month", sort=True).agg(default=("default_net_pips", "sum"), trades=("default_net_pips", "size"))
        daily = group.groupby("entry_date_utc", sort=True)["default_net_pips"].sum().sort_values(ascending=False)
        default = group["default_net_pips"]
        severe = group["severe_net_pips"]
        rows.append(
            {
                **dict(zip(keys, key)),
                "trades": int(len(group)),
                "default_net_pips": float(default.sum()),
                "default_pf": float(profit_factor(default)),
                "severe_net_pips": float(severe.sum()),
                "severe_pf": float(profit_factor(severe)),
                "positive_months": int(((monthly["trades"] > 0) & (monthly["default"] > 0)).sum()),
                "negative_months": int(((monthly["trades"] > 0) & (monthly["default"] < 0)).sum()),
                "ex_best_two_dates_default_pips": float(default.sum() - daily.head(2).sum()),
                "long_default_net_pips": float(group.loc[group["side"] == 1, "default_net_pips"].sum()),
                "short_default_net_pips": float(group.loc[group["side"] == -1, "default_net_pips"].sum()),
                "long_severe_net_pips": float(group.loc[group["side"] == 1, "severe_net_pips"].sum()),
                "short_severe_net_pips": float(group.loc[group["side"] == -1, "severe_net_pips"].sum()),
            }
        )
    return pd.DataFrame(rows)


