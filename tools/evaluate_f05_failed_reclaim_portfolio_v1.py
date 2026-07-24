#!/usr/bin/env python3
"""Frozen binding evaluator for F05 failed reclaim with full portfolio replay.

The evaluator keeps three distinct layers:
1. byte-identified exploration reproduction (same-completion M5 adapter only);
2. binding direct instruction (failure M5 completion strictly later than reclaim close);
3. full accepted-signal-stream portfolio replay, including exact 2024 raw-tick audit.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import math
import tarfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from usdjpy_structural_sl_v1.common import (
    EXPECTED_COUNTS,
    EXPECTED_SHA,
    FOLDS,
    PIP,
    aggregate_bars,
    executable_price,
    historical_2023_trades,
    inside,
    load_2023_m15,
    load_m1,
    max_exec,
    min_exec,
    next_exit,
    outside,
    parse_event_trades,
    pnl,
    r1,
    sha256_file,
    write_json,
)
from usdjpy_structural_sl_v1.events import event_row, failed_reclaim

BINDING_ID = "F05_FAILED_RECLAIM_BASIC_V1"
SENSITIVITY_ID = "F05_FAILED_RECLAIM_WEAK_QUICK_V1"
EXPECTED_REPORT_SHA = "489a2484be135209fd731951990e508b67d6ff11cd2aeff3a4fbac23dffdfad5"
EXPECTED_BUNDLE_SHA = "463850652d08f7c3d6b170a345ba92a1f7228c9efb24eb0f89f90b13a59b686d"
EXPECTED_MANIFEST_SHA = "648282bed25cb5cf93fed7c16a0878f55565146849adfb6e3d92d3e47ff0e668"
EXPECTED_FIXTURE_SHA = {
    "exploration": "75312aba2ffd92c45ec52023b49ba906b6e216730c61f932927c8c239c5da837",
    "direct": "41f6bcda5515a40e283fde65e55cf8a1010ef26d31930e6fe8717238bf5ff6a9",
}
EXPECTED_EXPLORATION = {
    "stopped": 14,
    "delta": 202.1,
    "long": 65.2,
    "short": 136.9,
    "fold": {
        "2023H1": {"stopped": 4, "delta": 70.8},
        "2023H2": {"stopped": 4, "delta": 14.1},
        "2024H1": {"stopped": 5, "delta": 110.7},
        "2024H2": {"stopped": 1, "delta": 6.5},
    },
}
EXPECTED_DIRECT_PRE_RAW = {
    "stopped": 15,
    "delta": 200.6,
    "long": 65.2,
    "short": 135.4,
    "direct_only_trade_key": "F05|2023-06-08T15:45:00Z|-1",
}



def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iso(ts: object) -> str:
    return pd.Timestamp(ts).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def restore_bundle(bundle_b64: Path, output: Path) -> str:
    payload = base64.b64decode(b"".join(bundle_b64.read_bytes().split()), validate=True)
    output.write_bytes(payload)
    actual = hashlib.sha256(payload).hexdigest()
    assert actual == EXPECTED_BUNDLE_SHA, (actual, EXPECTED_BUNDLE_SHA)
    return actual


def verify_bundle(report: Path, bundle_b64: Path, repository_manifest: Path, work_dir: Path) -> dict:
    assert sha256_file(report) == EXPECTED_REPORT_SHA
    assert sha256_file(repository_manifest) == EXPECTED_MANIFEST_SHA
    restored = work_dir / "F05_structural_SL_event_sequence_bundle_v1.zip"
    bundle_sha = restore_bundle(bundle_b64, restored)
    repo_manifest = read_json(repository_manifest)
    with zipfile.ZipFile(restored) as zf:
        embedded_bytes = zf.read("manifest.json")
        embedded = json.loads(embedded_bytes)
        assert embedded == repo_manifest
        assert hashlib.sha256(embedded_bytes).hexdigest() == EXPECTED_MANIFEST_SHA
        members = []
        for item in embedded["files"]:
            payload = zf.read(item["name"])
            actual = {"name": item["name"], "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            assert actual["bytes"] == int(item["size_bytes"])
            assert actual["sha256"] == item["sha256"]
            members.append(actual)
        basic = pd.read_csv(io.BytesIO(zf.read("basic_failed_reclaim_fold_metrics.csv")))
    return {
        "report_sha256": EXPECTED_REPORT_SHA,
        "bundle_sha256": bundle_sha,
        "manifest_sha256": EXPECTED_MANIFEST_SHA,
        "member_count": len(members),
        "members": members,
        "basic_fold_metrics": basic.to_dict("records"),
    }


def verify_protocol(protocol_path: Path, semantic_path: Path) -> tuple[dict, dict]:
    p = read_json(protocol_path)
    s = read_json(semantic_path)
    assert p["schema_version"] == "f05_failed_reclaim_validation_protocol_v1"
    assert p["status"] == "FROZEN_BEFORE_OUTCOME_EXECUTION"
    assert p["candidates"]["count"] == 2 and p["candidates"]["binding_count"] == 1
    assert p["candidates"]["binding"]["candidate_id"] == BINDING_ID
    assert p["candidates"]["binding"]["reclaim_failure"]["same_timestamp_m5_forbidden"] is True
    assert p["candidates"]["non_binding_sensitivity"]["candidate_id"] == SENSITIVITY_ID
    assert p["candidates"]["non_binding_sensitivity"]["binding"] is False
    assert p["2025_lock"]["H2_access"] is False
    assert s["schema_version"] == "f05_failed_reclaim_semantic_resolution_v1"
    assert s["status"] == "FROZEN_BEFORE_SCIENTIFIC_OUTCOME_EXECUTION"
    assert s["exploration_reproduction_adapter"]["same_timestamp_m5_allowed"] is True
    assert s["binding_adapter"]["same_timestamp_m5_forbidden"] is True
    assert s["candidate_definition_changed"] is False
    return p, s


def make_trade_key(frame: pd.DataFrame) -> pd.Series:
    return (
        frame.strategy.astype(str)
        + "|"
        + pd.to_datetime(frame.signal_utc, utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        + "|"
        + frame.side.astype(int).astype(str)
    )


def load_population(m15_2023: Path, events_h1: Path, events_h2: Path) -> pd.DataFrame:
    trades = pd.concat(
        [
            historical_2023_trades(load_2023_m15(m15_2023)),
            parse_event_trades(events_h1, "2024H1", False),
            parse_event_trades(events_h2, "2024H2", True),
        ],
        ignore_index=True,
    ).sort_values(["fold", "entry_utc", "strategy"], kind="mergesort").reset_index(drop=True)
    counts = {
        fold: {strategy: int(n) for strategy, n in group.groupby("strategy").size().items()}
        for fold, group in trades.groupby("fold")
    }
    assert len(trades) == 1882 and counts == EXPECTED_COUNTS, (len(trades), counts)
    trades.insert(0, "trade_idx", np.arange(len(trades), dtype=int))
    trades["trade_key"] = make_trade_key(trades)
    assert trades.trade_key.is_unique
    return trades




def verify_2024_signal_admission(events_h1: Path, events_h2: Path) -> dict:
    expected = {
        "2024H1": {"B02": {"signals": 98, "opened": 98, "analysis_trades": 97}, "F05": {"signals": 331, "opened": 331, "analysis_trades": 331}},
        "2024H2": {"B02": {"signals": 102, "opened": 102, "analysis_trades": 102}, "F05": {"signals": 392, "opened": 392, "analysis_trades": 392}},
    }
    result: dict[str, object] = {}
    for fold, path in [("2024H1", events_h1), ("2024H2", events_h2)]:
        d = pd.read_csv(path, encoding="utf-8-sig")
        blocked = d[d.event.isin(["entry_blocked", "order_send_failed"])]
        deinit = d[d.event == "runtime_deinit"]
        assert len(deinit) == 1
        fields = dict(__import__("re").findall(r"(b02_signals|f05_signals|b02_opened|f05_opened|errors)=([0-9]+)", str(deinit.iloc[0].detail)))
        opened = d[d.event == "order_opened"].groupby("strategy").size().to_dict()
        period_open = d[d.event == "period_end_open_position"].groupby("strategy").size().to_dict()
        row: dict[str, object] = {
            "source_file": path.name,
            "entry_blocked_count": int(len(blocked)),
            "order_send_failed_count": int((d.event == "order_send_failed").sum()),
            "runtime_errors": int(fields["errors"]),
            "period_end_open_positions": {k: int(v) for k, v in period_open.items()},
            "strategies": {},
        }
        for strategy, prefix in [("B02", "b02"), ("F05", "f05")]:
            actual = {
                "signals": int(fields[f"{prefix}_signals"]),
                "opened": int(fields[f"{prefix}_opened"]),
                "order_opened_rows": int(opened.get(strategy, 0)),
                "analysis_trades": int(expected[fold][strategy]["analysis_trades"]),
            }
            assert actual["signals"] == expected[fold][strategy]["signals"]
            assert actual["opened"] == expected[fold][strategy]["opened"]
            assert actual["order_opened_rows"] == expected[fold][strategy]["opened"]
            assert actual["signals"] == actual["opened"]
            row["strategies"][strategy] = actual
        assert len(blocked) == 0 and int(fields["errors"]) == 0
        result[fold] = row
    result["all_detected_signals_opened"] = True
    result["admission_filters_beyond_hard_time_and_margin"] = False
    result["candidate_reopened_signal_count"] = 0
    result["reason"] = "The frozen EA signal functions do not depend on open positions, and both 2024 source logs show signals==opened with zero blocked or failed entries. Earlier exits can change exposure state but cannot reveal an unadmitted historical signal."
    return result


def failed_reclaim_exploration(tr: object, m1: pd.DataFrame, m5: pd.DataFrame) -> dict | None:
    """Byte-reproduction adapter: exploration selected completion >= reclaim."""
    if tr.strategy != "F05":
        return None
    side, entry, close = int(tr.side), tr.entry_utc, tr.close_utc
    level, entry_price = float(tr.breakout_level), float(tr.entry_price)
    start = entry.floor("5min")
    if start not in m5.index:
        return None
    first = m5.loc[start]
    first_completion = start + pd.Timedelta(minutes=5)
    mfe_first = max_exec(m1, entry, first_completion, entry_price, side)
    if mfe_first > 1e-9 or not inside(executable_price(first, side, "close"), level, side, 0.02):
        return None
    reclaim = None
    for t, bar in m1[((m1.index + pd.Timedelta(minutes=1)) > first_completion) & ((m1.index + pd.Timedelta(minutes=1)) < close)].iterrows():
        completion = t + pd.Timedelta(minutes=1)
        if outside(executable_price(bar, side, "close"), level, side):
            reclaim = completion
            break
    if reclaim is None:
        return None
    q = m5[(m5.completion >= reclaim) & (m5.completion < close)]
    if q.empty:
        return None
    failure_bar = q.iloc[0]
    failure = failure_bar.completion
    if not inside(executable_price(failure_bar, side, "close"), level, side):
        return None
    mfe = max_exec(m1, entry, failure, entry_price, side)
    mae = min_exec(m1, entry, failure, entry_price, side)
    if mfe > 1e-9:
        return None
    ex = next_exit(m1, failure, close)
    if not ex:
        return None
    exit_time, exit_bar = ex
    return event_row(
        tr,
        "F05_FAILED_RECLAIM_EXPLORATION_REPRODUCTION_V1",
        failure,
        exit_time,
        executable_price(exit_bar, side, "open"),
        mfe,
        mae,
        {"reclaim_utc": reclaim, "first_m5_completion_utc": first_completion},
    )


def add_trade_key(row: dict, tr: object) -> dict:
    row = dict(row)
    row["trade_key"] = f"{tr.strategy}|{iso(tr.signal_utc)}|{int(tr.side)}"
    row["candidate_id"] = BINDING_ID
    return row


def evaluate_events(trades: pd.DataFrame, m23: pd.DataFrame, m24: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bars = {"2023": aggregate_bars(m23, 5), "2024": aggregate_bars(m24, 5)}
    exploration: list[dict] = []
    direct: list[dict] = []
    weak: list[dict] = []
    for tr in trades.itertuples(index=False):
        if tr.strategy != "F05":
            continue
        year = "2023" if tr.fold.startswith("2023") else "2024"
        m1_all = m23 if year == "2023" else m24
        m1 = m1_all.loc[tr.entry_utc:tr.close_utc]
        m5 = bars[year].loc[tr.entry_utc.floor("5min"):tr.close_utc]
        old = failed_reclaim_exploration(tr, m1, m5)
        if old:
            exploration.append(add_trade_key(old, tr))
        new = failed_reclaim(tr, m1, m5, 5, BINDING_ID, "F05")
        if new:
            row = add_trade_key(new, tr)
            row["first_m5_completion_utc"] = tr.entry_utc.floor("5min") + pd.Timedelta(minutes=5)
            direct.append(row)
            reclaim = pd.Timestamp(row["reclaim_utc"])
            failure = pd.Timestamp(row["trigger_utc"])
            within_60 = reclaim <= tr.entry_utc + pd.Timedelta(minutes=60)
            closes = m1[((m1.index + pd.Timedelta(minutes=1)) >= reclaim) & ((m1.index + pd.Timedelta(minutes=1)) < failure)]
            run = 0
            max_run = 0
            for _, bar in closes.iterrows():
                if outside(executable_price(bar, int(tr.side), "close"), float(tr.breakout_level), int(tr.side)):
                    run += 1
                    max_run = max(max_run, run)
                else:
                    run = 0
            if within_60 and max_run <= 2:
                w = dict(row)
                w["candidate_id"] = SENSITIVITY_ID
                w["reclaim_within_60m"] = True
                w["maximum_consecutive_outside_m1_closes"] = int(max_run)
                weak.append(w)
    def frame(rows: list[dict]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        out = pd.DataFrame(rows).sort_values(["fold", "entry_utc", "trade_key"], kind="mergesort").reset_index(drop=True)
        return out
    return frame(exploration), frame(direct), frame(weak)


def event_summary(d: pd.DataFrame) -> dict:
    folds = {}
    for fold in FOLDS:
        g = d[d.fold == fold]
        folds[fold] = {
            "stopped": int(len(g)),
            "delta_pips": r1(g.delta_pips.sum()) if len(g) else 0.0,
            "long_delta_pips": r1(g.loc[g.side == 1, "delta_pips"].sum()) if len(g) else 0.0,
            "short_delta_pips": r1(g.loc[g.side == -1, "delta_pips"].sum()) if len(g) else 0.0,
        }
    return {
        "stopped_trades": int(len(d)),
        "total_delta_pips": r1(d.delta_pips.sum()) if len(d) else 0.0,
        "long_delta_pips": r1(d.loc[d.side == 1, "delta_pips"].sum()) if len(d) else 0.0,
        "short_delta_pips": r1(d.loc[d.side == -1, "delta_pips"].sum()) if len(d) else 0.0,
        "folds": folds,
    }


def verify_exploration(exploration: pd.DataFrame, bundle_basic: list[dict], fixture: Path) -> dict:
    assert sha256_file(fixture) == EXPECTED_FIXTURE_SHA["exploration"]
    expected_fixture = pd.read_csv(fixture)
    actual = exploration.copy()
    expected_keys = set(expected_fixture.trade_key.astype(str))
    actual_keys = set(actual.trade_key.astype(str))
    summary = event_summary(actual)
    checks = {
        "stopped": summary["stopped_trades"] == EXPECTED_EXPLORATION["stopped"],
        "total": math.isclose(summary["total_delta_pips"], EXPECTED_EXPLORATION["delta"], abs_tol=0.05),
        "long": math.isclose(summary["long_delta_pips"], EXPECTED_EXPLORATION["long"], abs_tol=0.05),
        "short": math.isclose(summary["short_delta_pips"], EXPECTED_EXPLORATION["short"], abs_tol=0.05),
        "identity": actual_keys == expected_keys,
    }
    for fold, expected in EXPECTED_EXPLORATION["fold"].items():
        checks[f"{fold}_stopped"] = summary["folds"][fold]["stopped"] == expected["stopped"]
        checks[f"{fold}_delta"] = math.isclose(summary["folds"][fold]["delta_pips"], expected["delta"], abs_tol=0.05)
    bundle_by_fold = {str(row["fold"]): row for row in bundle_basic}
    for fold in FOLDS:
        checks[f"{fold}_bundle_total"] = math.isclose(summary["folds"][fold]["delta_pips"], float(bundle_by_fold[fold]["total"]), abs_tol=0.05)
        checks[f"{fold}_bundle_stopped"] = summary["folds"][fold]["stopped"] == int(bundle_by_fold[fold]["stopped"])
    assert all(checks.values()), checks
    return {"status": "PASS_EXACT", "summary": summary, "checks": checks, "fixture_sha256": EXPECTED_FIXTURE_SHA["exploration"]}




def verify_direct_pre_raw(direct: pd.DataFrame, fixture: Path) -> dict:
    assert sha256_file(fixture) == EXPECTED_FIXTURE_SHA["direct"]
    expected = pd.read_csv(fixture)
    summary = event_summary(direct)
    checks = {
        "stopped": summary["stopped_trades"] == EXPECTED_DIRECT_PRE_RAW["stopped"],
        "total": math.isclose(summary["total_delta_pips"], EXPECTED_DIRECT_PRE_RAW["delta"], abs_tol=0.05),
        "long": math.isclose(summary["long_delta_pips"], EXPECTED_DIRECT_PRE_RAW["long"], abs_tol=0.05),
        "short": math.isclose(summary["short_delta_pips"], EXPECTED_DIRECT_PRE_RAW["short"], abs_tol=0.05),
        "identity": set(direct.trade_key.astype(str)) == set(expected.trade_key.astype(str)),
        "direct_only_present": EXPECTED_DIRECT_PRE_RAW["direct_only_trade_key"] in set(direct.trade_key.astype(str)),
    }
    actual_by = direct.set_index("trade_key")
    expected_by = expected.set_index("trade_key")
    for key in sorted(expected_by.index):
        a = actual_by.loc[key]
        e = expected_by.loc[key]
        for actual_col, expected_col in [
            ("entry_utc", "entry_utc"),
            ("reclaim_utc", "reclaim_m1_close_utc"),
            ("trigger_utc", "failure_m5_completion_utc"),
            ("candidate_exit_utc", "candidate_exit_utc"),
        ]:
            checks[f"{key}:{actual_col}"] = iso(a[actual_col]) == iso(e[expected_col])
        for col in ["baseline_pips", "candidate_pips", "delta_pips"]:
            checks[f"{key}:{col}"] = math.isclose(float(a[col]), float(e[col]), abs_tol=0.05)
    assert all(checks.values()), {k: v for k, v in checks.items() if not v}
    return {
        "status": "PASS_EXACT_DIRECT_PRE_RAW_IDENTITY",
        "summary": summary,
        "fixture_sha256": EXPECTED_FIXTURE_SHA["direct"],
        "checks_passed": len(checks),
    }


class RawTickArchives:
    def __init__(self, directory: Path):
        self.directory = directory
        self.archives = sorted(directory.glob("usdjpy-2024-??-raw-ticks-v1.tar.gz"))
        if not self.archives:
            raise AssertionError(f"no raw tick archives in {directory}")
        self.member_index: dict[str, tuple[Path, str]] = {}
        for archive_path in self.archives:
            with tarfile.open(archive_path, "r:gz") as tf:
                for member in tf.getmembers():
                    if member.isfile() and member.name.endswith(".csv.gz") and "/decoded_csv/USDJPY/" in "/" + member.name:
                        suffix = member.name.split("decoded_csv/USDJPY/", 1)[1]
                        self.member_index[suffix] = (archive_path, member.name)
        self.cache: dict[str, pd.DataFrame] = {}

    def hour(self, hour: pd.Timestamp) -> pd.DataFrame:
        key = hour.tz_convert("UTC").strftime("%Y/%m/%d/%H.csv.gz")
        if key in self.cache:
            return self.cache[key]
        if key not in self.member_index:
            self.cache[key] = pd.DataFrame(columns=["timestamp_utc", "bid", "ask"])
            return self.cache[key]
        archive_path, member_name = self.member_index[key]
        with tarfile.open(archive_path, "r:gz") as tf:
            extracted = tf.extractfile(member_name)
            assert extracted is not None
            compressed = extracted.read()
        raw = gzip.decompress(compressed)
        d = pd.read_csv(io.BytesIO(raw), usecols=["timestamp_utc", "bid", "ask"])
        d["timestamp_utc"] = pd.to_datetime(d.timestamp_utc, utc=True)
        d["bid"] = d.bid.astype(float)
        d["ask"] = d.ask.astype(float)
        assert not (d.ask < d.bid).any()
        d = d.sort_values("timestamp_utc").drop_duplicates("timestamp_utc", keep="last")
        self.cache[key] = d
        return d

    def window(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        hours = pd.date_range(start.floor("h"), end.floor("h"), freq="h")
        frames = [self.hour(h) for h in hours]
        d = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if d.empty:
            return d
        return d[(d.timestamp_utc >= start) & (d.timestamp_utc <= end)].sort_values("timestamp_utc")


def audit_2024_ticks(direct: pd.DataFrame, trades: pd.DataFrame, raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    archives = RawTickArchives(raw_dir)
    by_key = trades.set_index("trade_key")
    rows = []
    adjusted = direct.copy()
    for idx, ev in direct[direct.fold.str.startswith("2024")].iterrows():
        tr = by_key.loc[ev.trade_key]
        entry = pd.Timestamp(tr.entry_utc)
        first_completion = pd.Timestamp(ev.first_m5_completion_utc)
        failure = pd.Timestamp(ev.trigger_utc)
        baseline_close = pd.Timestamp(tr.close_utc)
        ticks = archives.window(entry, failure + pd.Timedelta(hours=1))
        if ticks.empty:
            raise AssertionError(("no_ticks", ev.trade_key, entry, failure))
        through_first = ticks[(ticks.timestamp_utc >= entry) & (ticks.timestamp_utc < first_completion)]
        through_trigger = ticks[(ticks.timestamp_utc >= entry) & (ticks.timestamp_utc < failure)]
        side = int(tr.side)
        entry_price = float(tr.entry_price)
        mfe_first = ((through_first.bid.max() - entry_price) / PIP) if side == 1 else ((entry_price - through_first.ask.min()) / PIP)
        mfe_trigger = ((through_trigger.bid.max() - entry_price) / PIP) if side == 1 else ((entry_price - through_trigger.ask.min()) / PIP)
        exit_ticks = ticks[ticks.timestamp_utc >= failure]
        if exit_ticks.empty:
            exit_ticks = archives.window(failure, failure + pd.Timedelta(hours=2))
            exit_ticks = exit_ticks[exit_ticks.timestamp_utc >= failure]
        if exit_ticks.empty or pd.Timestamp(exit_ticks.iloc[0].timestamp_utc) >= baseline_close:
            raise AssertionError(("no_candidate_exit_tick", ev.trade_key, failure, baseline_close))
        first_tick = exit_ticks.iloc[0]
        exit_time = pd.Timestamp(first_tick.timestamp_utc)
        exit_price = float(first_tick.bid if side == 1 else first_tick.ask)
        candidate_pips = r1(pnl(exit_price, entry_price, side))
        baseline_pips = float(tr.baseline_pips)
        valid = bool(mfe_first <= 1e-9 and mfe_trigger <= 1e-9)
        rows.append({
            "trade_key": ev.trade_key,
            "fold": tr.fold,
            "side": side,
            "entry_utc": iso(entry),
            "first_m5_completion_utc": iso(first_completion),
            "reclaim_utc": iso(ev.reclaim_utc),
            "failure_m5_completion_utc": iso(failure),
            "candidate_exit_tick_utc": iso(exit_time),
            "entry_price": entry_price,
            "candidate_exit_tick_price": exit_price,
            "raw_tick_mfe_through_first_m5_pips": r1(mfe_first),
            "raw_tick_mfe_through_trigger_pips": r1(mfe_trigger),
            "baseline_pips": r1(baseline_pips),
            "candidate_tick_pips": candidate_pips,
            "delta_tick_pips": r1(candidate_pips - baseline_pips),
            "chronology_valid": bool(entry < first_completion < pd.Timestamp(ev.reclaim_utc) < failure <= exit_time < baseline_close),
            "profit_disarm_clear": valid,
            "raw_tick_resolution": "RAW_CONFIRMED_CANDIDATE" if valid else "RAW_DISARMED_POSITIVE_PL",
        })
        if not valid:
            adjusted = adjusted[adjusted.trade_key != ev.trade_key].copy()
        else:
            adjusted.loc[idx, "candidate_exit_utc"] = exit_time
            adjusted.loc[idx, "candidate_pips"] = candidate_pips
            adjusted.loc[idx, "delta_pips"] = r1(candidate_pips - baseline_pips)
    audit = pd.DataFrame(rows).sort_values(["fold", "entry_utc", "trade_key"]).reset_index(drop=True)
    assert len(audit) == int((direct.fold.str.startswith("2024")).sum())
    assert audit.chronology_valid.all()
    return adjusted.sort_values(["fold", "entry_utc", "trade_key"]).reset_index(drop=True), audit


def profit_factor(values: pd.Series) -> float | None:
    gain = float(values[values > 0].sum())
    loss = float(-values[values < 0].sum())
    if loss == 0:
        return None if gain == 0 else math.inf
    return gain / loss


def realized_replay(trades: pd.DataFrame, exit_col: str, pips_col: str) -> tuple[pd.DataFrame, dict]:
    rows = []
    balance = 100000.0
    peak = balance
    max_dd = 0.0
    for tr in trades.sort_values([exit_col, "trade_key"], kind="mergesort").itertuples(index=False):
        pips = float(getattr(tr, pips_col))
        balance += pips * 10.0
        peak = max(peak, balance)
        dd = peak - balance
        max_dd = max(max_dd, dd)
        rows.append({
            "utc": iso(getattr(tr, exit_col)),
            "trade_key": tr.trade_key,
            "strategy": tr.strategy,
            "side": int(tr.side),
            "realized_pips": r1(pips),
            "balance_jpy": round(balance, 1),
            "realized_drawdown_jpy": round(dd, 1),
        })
    return pd.DataFrame(rows), {
        "starting_balance_jpy": 100000.0,
        "ending_balance_jpy": round(balance, 1),
        "net_jpy": round(balance - 100000.0, 1),
        "max_realized_drawdown_jpy": round(max_dd, 1),
        "profit_factor": profit_factor(trades[pips_col]),
    }


def exposure_replay(trades: pd.DataFrame, exit_col: str) -> tuple[pd.DataFrame, dict]:
    events = []
    for tr in trades.itertuples(index=False):
        events.append((pd.Timestamp(getattr(tr, exit_col)), 0, "exit", tr.trade_key, tr.strategy, int(tr.side)))
        events.append((pd.Timestamp(tr.entry_utc), 1, "entry", tr.trade_key, tr.strategy, int(tr.side)))
    events.sort(key=lambda x: (x[0], x[1], x[3]))
    open_positions: dict[str, dict[str, object]] = {}
    rows = []
    max_open = 0
    for ts, _, kind, key, strategy, side in events:
        if kind == "exit":
            assert key in open_positions, (key, ts)
            del open_positions[key]
            rows.append({"utc": iso(ts), "event": kind, "trade_key": key, "strategy": strategy, "side": side, "open_positions": len(open_positions)})
        else:
            same = sum(1 for p in open_positions.values() if int(p["side"]) == side)
            opposite = sum(1 for p in open_positions.values() if int(p["side"]) == -side)
            rows.append({
                "utc": iso(ts), "event": kind, "trade_key": key, "strategy": strategy, "side": side,
                "open_positions_before": len(open_positions), "same_direction_before": same,
                "opposite_direction_before": opposite, "stack_ordinal": same + 1,
                "open_positions": len(open_positions) + 1,
            })
            open_positions[key] = {"strategy": strategy, "side": side}
            max_open = max(max_open, len(open_positions))
    assert not open_positions
    frame = pd.DataFrame(rows)
    return frame, {"entry_count": int((frame.event == "entry").sum()), "exit_count": int((frame.event == "exit").sum()), "max_open_positions": int(max_open)}




def margin_admission_replay(trades: pd.DataFrame, exit_col: str, pips_col: str, m1: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    contract_size = 100000.0
    lots = 0.01
    leverage = 25.0
    events: list[tuple[pd.Timestamp, int, str, object]] = []
    for tr in trades.itertuples(index=False):
        events.append((pd.Timestamp(getattr(tr, exit_col)), 0, "exit", tr))
        events.append((pd.Timestamp(tr.entry_utc), 1, "entry", tr))
    events.sort(key=lambda item: (item[0], item[1], str(item[3].trade_key)))
    open_positions: dict[str, object] = {}
    balance = 100000.0
    rows: list[dict[str, object]] = []
    minimum_free_after = math.inf
    blocked = 0

    def market_row(ts: pd.Timestamp) -> pd.Series:
        if ts in m1.index:
            return m1.loc[ts]
        before = m1[m1.index <= ts]
        if before.empty:
            raise AssertionError(("missing_market_row", ts))
        return before.iloc[-1]

    for ts, _, kind, tr in events:
        key = str(tr.trade_key)
        if kind == "exit":
            assert key in open_positions, (key, ts)
            balance += float(getattr(tr, pips_col)) * 10.0
            del open_positions[key]
            continue
        bar = market_row(ts)
        bid = float(bar.bid_open)
        ask = float(bar.ask_open)
        mid = (bid + ask) * 0.5
        unrealized_jpy = 0.0
        for pos in open_positions.values():
            side = int(pos.side)
            mark = bid if side == 1 else ask
            unrealized_jpy += side * (mark - float(pos.entry_price)) / PIP * 10.0
        equity = balance + unrealized_jpy
        margin_before = len(open_positions) * contract_size * lots * mid / leverage
        additional_margin = contract_size * lots * mid / leverage
        free_after = equity - margin_before - additional_margin
        minimum_free_after = min(minimum_free_after, free_after)
        would_block = free_after <= 0.0
        blocked += int(would_block)
        rows.append({
            "utc": iso(ts),
            "trade_key": key,
            "strategy": tr.strategy,
            "side": int(tr.side),
            "balance_before_entry_jpy": round(balance, 2),
            "equity_before_entry_jpy": round(equity, 2),
            "open_positions_before": int(len(open_positions)),
            "margin_before_entry_jpy": round(margin_before, 2),
            "additional_margin_jpy": round(additional_margin, 2),
            "free_margin_after_entry_jpy": round(free_after, 2),
            "would_block": bool(would_block),
        })
        open_positions[key] = tr
    assert not open_positions
    frame = pd.DataFrame(rows)
    return frame, {
        "entry_count": int(len(frame)),
        "would_block_count": int(blocked),
        "minimum_free_margin_after_entry_jpy": round(minimum_free_after, 2),
        "fixed_lots": lots,
        "virtual_leverage": leverage,
        "contract_size": contract_size,
    }


def build_portfolio(trades: pd.DataFrame, direct: pd.DataFrame, m23: pd.DataFrame, m24: pd.DataFrame) -> tuple[pd.DataFrame, dict, dict[str, pd.DataFrame]]:
    changes = direct[["trade_key", "candidate_exit_utc", "candidate_pips", "delta_pips"]].copy()
    changes["candidate_exit_utc"] = pd.to_datetime(changes.candidate_exit_utc, utc=True)
    p = trades.merge(changes, on="trade_key", how="left", validate="one_to_one")
    p["changed"] = p.candidate_pips.notna()
    p["candidate_exit_utc_final"] = p.candidate_exit_utc.where(p.changed, p.close_utc)
    p["candidate_default_pips"] = p.candidate_pips.where(p.changed, p.baseline_pips)
    p["candidate_severe_pips"] = p.candidate_default_pips - np.where(p.changed, 2.0, 0.0)
    p["default_delta_pips"] = p.candidate_default_pips - p.baseline_pips
    p["severe_delta_pips"] = p.candidate_severe_pips - p.baseline_pips
    p["baseline_winner"] = p.baseline_pips > 0
    p["baseline_loser"] = ~p.baseline_winner
    p["final_candidate_loser"] = p.candidate_default_pips <= 0

    fold_rows = []
    curves: dict[str, pd.DataFrame] = {}
    baseline_exposure: dict[str, pd.DataFrame] = {}
    candidate_exposure: dict[str, pd.DataFrame] = {}
    for fold in FOLDS:
        g = p[p.fold == fold].copy()
        bcurve, bm = realized_replay(g, "close_utc", "baseline_pips")
        ccurve, cm = realized_replay(g, "candidate_exit_utc_final", "candidate_default_pips")
        scurve, sm = realized_replay(g, "candidate_exit_utc_final", "candidate_severe_pips")
        bexp, be = exposure_replay(g, "close_utc")
        cexp, ce = exposure_replay(g, "candidate_exit_utc_final")
        market = m23 if fold.startswith("2023") else m24
        bmargin_frame, bmargin = margin_admission_replay(g, "close_utc", "baseline_pips", market)
        cmargin_frame, cmargin = margin_admission_replay(g, "candidate_exit_utc_final", "candidate_default_pips", market)
        bentry = bexp[bexp.event == "entry"][["trade_key", "open_positions_before", "same_direction_before", "opposite_direction_before", "stack_ordinal"]]
        centry = cexp[cexp.event == "entry"][["trade_key", "open_positions_before", "same_direction_before", "opposite_direction_before", "stack_ordinal"]]
        state = bentry.merge(centry, on="trade_key", suffixes=("_baseline", "_candidate"), validate="one_to_one")
        exposure_changed = (
            (state.open_positions_before_baseline != state.open_positions_before_candidate)
            | (state.same_direction_before_baseline != state.same_direction_before_candidate)
            | (state.opposite_direction_before_baseline != state.opposite_direction_before_candidate)
        )
        fold_rows.append({
            "fold": fold,
            "trades": int(len(g)),
            "changed_trades": int(g.changed.sum()),
            "baseline_net_pips": r1(g.baseline_pips.sum()),
            "candidate_default_net_pips": r1(g.candidate_default_pips.sum()),
            "candidate_default_pf": profit_factor(g.candidate_default_pips),
            "default_delta_pips": r1(g.default_delta_pips.sum()),
            "candidate_severe_net_pips": r1(g.candidate_severe_pips.sum()),
            "candidate_severe_pf": profit_factor(g.candidate_severe_pips),
            "severe_delta_pips": r1(g.severe_delta_pips.sum()),
            "baseline_net_jpy": bm["net_jpy"],
            "candidate_default_net_jpy": cm["net_jpy"],
            "candidate_severe_net_jpy": sm["net_jpy"],
            "baseline_max_realized_drawdown_jpy": bm["max_realized_drawdown_jpy"],
            "candidate_default_max_realized_drawdown_jpy": cm["max_realized_drawdown_jpy"],
            "candidate_severe_max_realized_drawdown_jpy": sm["max_realized_drawdown_jpy"],
            "baseline_max_open_positions": be["max_open_positions"],
            "candidate_max_open_positions": ce["max_open_positions"],
            "entries_with_changed_exposure_state": int(exposure_changed.sum()),
            "candidate_entries_with_fewer_open_positions": int((state.open_positions_before_candidate < state.open_positions_before_baseline).sum()),
            "candidate_entries_with_more_open_positions": int((state.open_positions_before_candidate > state.open_positions_before_baseline).sum()),
            "admitted_entries_baseline": be["entry_count"],
            "admitted_entries_candidate": ce["entry_count"],
            "baseline_margin_blocked_entries": bmargin["would_block_count"],
            "candidate_margin_blocked_entries": cmargin["would_block_count"],
            "baseline_minimum_free_margin_after_entry_jpy": bmargin["minimum_free_margin_after_entry_jpy"],
            "candidate_minimum_free_margin_after_entry_jpy": cmargin["minimum_free_margin_after_entry_jpy"],
        })
        curves[f"baseline_{fold}"] = bcurve
        curves[f"candidate_default_{fold}"] = ccurve
        curves[f"candidate_severe_{fold}"] = scurve
        baseline_exposure[fold] = bexp
        candidate_exposure[fold] = cexp
        curves[f"baseline_margin_admission_{fold}"] = bmargin_frame
        curves[f"candidate_margin_admission_{fold}"] = cmargin_frame

    fold_metrics = pd.DataFrame(fold_rows)
    changed = p[p.changed].copy()
    loser_benefit = float(changed.loc[changed.baseline_loser, "default_delta_pips"].sum())
    winner_effect = float(changed.loc[changed.baseline_winner, "default_delta_pips"].sum())
    direction_rows = []
    for side, label in [(1, "Long"), (-1, "Short")]:
        g = changed[changed.side == side]
        fold_values = g.groupby("fold").default_delta_pips.sum().reindex(FOLDS, fill_value=0.0)
        direction_rows.append({
            "side": side, "direction": label, "default_delta_pips": r1(g.default_delta_pips.sum()),
            "severe_delta_pips": r1(g.severe_delta_pips.sum()),
            "nonnegative_folds": int((fold_values >= -1e-9).sum()),
            "fold_delta_pips": {f: r1(fold_values[f]) for f in FOLDS},
        })

    top_retention = {}
    for fold in FOLDS:
        winners = p[(p.fold == fold) & p.baseline_winner]
        threshold = float(winners.baseline_pips.quantile(0.9))
        top = winners[winners.baseline_pips >= threshold]
        base = float(top.baseline_pips.sum())
        cand = float(top.candidate_default_pips.sum())
        top_retention[fold] = {
            "threshold_pips": threshold,
            "trade_count": int(len(top)),
            "baseline_pips": r1(base),
            "candidate_pips": r1(cand),
            "retention": 1.0 if base <= 0 else cand / base,
        }
    top_base = sum(v["baseline_pips"] for v in top_retention.values())
    top_cand = sum(v["candidate_pips"] for v in top_retention.values())
    combined_retention = top_cand / top_base

    changed["date"] = pd.to_datetime(changed.entry_utc, utc=True).dt.strftime("%Y-%m-%d")
    changed["month"] = pd.to_datetime(changed.entry_utc, utc=True).dt.strftime("%Y-%m")
    daily = changed.groupby("date").default_delta_pips.sum().sort_values(ascending=False)
    monthly = changed.groupby("month").default_delta_pips.sum().sort_values(ascending=False)
    total = float(changed.default_delta_pips.sum())
    concentration = {
        "total_delta_pips": r1(total),
        "best_date_delta_pips": r1(daily.iloc[0]),
        "delta_excluding_best_date_pips": r1(total - daily.iloc[0]),
        "delta_excluding_best_two_dates_pips": r1(total - daily.iloc[:2].sum()),
        "largest_month_delta_pips": r1(monthly.iloc[0]),
        "largest_month_share_of_total_improvement": float(monthly.iloc[0] / total),
        "daily": {str(k): r1(v) for k, v in daily.items()},
        "monthly": {str(k): r1(v) for k, v in monthly.items()},
    }

    gates = {
        "fold_total": bool((fold_metrics.default_delta_pips > 0).all()),
        "severe": bool(fold_metrics.severe_delta_pips.sum() > 0 and int((fold_metrics.severe_delta_pips > 0).sum()) >= 3),
        "direction": bool(all(r["default_delta_pips"] > 0 and r["nonnegative_folds"] >= 3 for r in direction_rows)),
        "winner_damage": bool(loser_benefit > abs(winner_effect) and combined_retention >= 0.90 and all(v["retention"] >= 0.85 for v in top_retention.values())),
        "breadth": bool(concentration["delta_excluding_best_date_pips"] > 0 and concentration["delta_excluding_best_two_dates_pips"] > 0 and concentration["largest_month_share_of_total_improvement"] <= 0.50),
        "trigger_breadth": bool((fold_metrics.changed_trades >= 1).all() and int(changed.shape[0]) >= 10 and int(changed.final_candidate_loser.sum()) >= 5),
        "portfolio_admission_identity": bool(
            (fold_metrics.admitted_entries_baseline == fold_metrics.admitted_entries_candidate).all()
            and int(fold_metrics.candidate_entries_with_more_open_positions.sum()) == 0
            and int(fold_metrics.baseline_margin_blocked_entries.sum()) == 0
            and int(fold_metrics.candidate_margin_blocked_entries.sum()) == 0
            and float(fold_metrics.candidate_minimum_free_margin_after_entry_jpy.min()) > 0.0
        ),
    }
    summary = {
        "fold_metrics": fold_metrics.to_dict("records"),
        "directions": direction_rows,
        "loser_benefit_pips": r1(loser_benefit),
        "winner_effect_pips": r1(winner_effect),
        "top_decile_winner_retention": {"combined": combined_retention, "folds": top_retention},
        "breadth": concentration,
        "trigger_count": int(changed.shape[0]),
        "final_loser_count": int(changed.final_candidate_loser.sum()),
        "gates": gates,
    }
    curves["baseline_exposure_all"] = pd.concat([baseline_exposure[f].assign(fold=f) for f in FOLDS], ignore_index=True)
    curves["candidate_exposure_all"] = pd.concat([candidate_exposure[f].assign(fold=f) for f in FOLDS], ignore_index=True)
    return p, summary, curves


def serialize_times(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = pd.to_datetime(out[col], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            continue
        if col.endswith("_utc") or col in {"utc", "timestamp_utc"}:
            converted = pd.to_datetime(out[col], utc=True, errors="coerce")
            if converted.notna().any():
                out[col] = converted.dt.strftime("%Y-%m-%dT%H:%M:%SZ").where(converted.notna(), out[col])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--semantic-resolution", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--bundle-b64", type=Path, required=True)
    ap.add_argument("--repository-manifest", type=Path, required=True)
    ap.add_argument("--exploration-fixture", type=Path, required=True)
    ap.add_argument("--direct-fixture", type=Path, required=True)
    ap.add_argument("--m15-2023", type=Path)
    ap.add_argument("--m1-2023", type=Path)
    ap.add_argument("--events-2024h1", type=Path)
    ap.add_argument("--events-2024h2", type=Path)
    ap.add_argument("--m1-2024", type=Path)
    ap.add_argument("--m5-2024", type=Path)
    ap.add_argument("--raw-tick-dir", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--research-commit", default="")
    ap.add_argument("--workflow-run-id", default="")
    ap.add_argument("--workflow-run-attempt", default="")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    protocol, semantic = verify_protocol(args.protocol, args.semantic_resolution)
    bundle = verify_bundle(args.report, args.bundle_b64, args.repository_manifest, args.out_dir)
    assert sha256_file(args.exploration_fixture) == EXPECTED_FIXTURE_SHA["exploration"]
    assert sha256_file(args.direct_fixture) == EXPECTED_FIXTURE_SHA["direct"]
    preflight = {
        "schema_version": "f05_failed_reclaim_portfolio_preflight_v1",
        "status": "PASS_NO_OUTCOMES",
        "binding_candidate": BINDING_ID,
        "non_binding_sensitivity": SENSITIVITY_ID,
        "protocol_sha256": sha256_file(args.protocol),
        "semantic_resolution_sha256": sha256_file(args.semantic_resolution),
        "evaluator_sha256": sha256_file(Path(__file__)),
        "source": bundle,
        "outcomes_computed": False,
        "portfolio_replay_computed": False,
        "mt4_accessed": False,
        "2025H1_accessed": False,
        "2025H2_accessed": False,
        "notion_task_dependency": False,
    }
    write_json(args.out_dir / "preflight_result_v1.json", preflight)
    if args.preflight_only:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 0

    required = [args.m15_2023, args.m1_2023, args.events_2024h1, args.events_2024h2, args.m1_2024, args.m5_2024, args.raw_tick_dir]
    if any(x is None for x in required):
        raise SystemExit("full evaluation requires all historical and raw-tick source arguments")
    actual_sha = {
        "m15_2023": sha256_file(args.m15_2023), "m1_2023": sha256_file(args.m1_2023),
        "events_2024h1": sha256_file(args.events_2024h1), "events_2024h2": sha256_file(args.events_2024h2),
        "m1_2024": sha256_file(args.m1_2024), "m5_2024": sha256_file(args.m5_2024),
    }
    expected = {**EXPECTED_SHA, "m5_2024": "af04cf642171a1916abc11a77d0120e88a1f61382385e54c9a49d9107d5d7f36"}
    assert actual_sha == expected, (actual_sha, expected)

    trades = load_population(args.m15_2023, args.events_2024h1, args.events_2024h2)
    signal_admission = verify_2024_signal_admission(args.events_2024h1, args.events_2024h2)
    m23, m24 = load_m1(args.m1_2023, args.m1_2024)
    exploration, direct_derived, weak = evaluate_events(trades, m23, m24)
    reproduction = verify_exploration(exploration, bundle["basic_fold_metrics"], args.exploration_fixture)
    direct_identity = verify_direct_pre_raw(direct_derived, args.direct_fixture)

    direct, tick_audit = audit_2024_ticks(direct_derived, trades, args.raw_tick_dir)
    tick_gate = bool(
        len(tick_audit) == int((direct_derived.fold.str.startswith("2024")).sum())
        and tick_audit.chronology_valid.all()
        and tick_audit.raw_tick_resolution.isin(["RAW_CONFIRMED_CANDIDATE", "RAW_DISARMED_POSITIVE_PL"]).all()
        and int((direct.fold.str.startswith("2024")).sum()) == int(tick_audit.profit_disarm_clear.sum())
    )
    portfolio, portfolio_summary, curves = build_portfolio(trades, direct, m23, m24)
    gates = dict(portfolio_summary["gates"])
    gates["reproduction"] = reproduction["status"] == "PASS_EXACT"
    gates["tick_event_order"] = tick_gate
    gates["full_signal_admission"] = bool(signal_admission["all_detected_signals_opened"])
    historical_pass = all(gates.values())

    for name, frame in {
        "exploration_reproduction_ledger_v1.csv": exploration,
        "binding_direct_event_ledger_v1.csv": direct,
        "non_binding_weak_quick_event_ledger_v1.csv": weak,
        "raw_tick_event_order_audit_v1.csv": tick_audit,
        "portfolio_trade_ledger_v1.csv": portfolio,
    }.items():
        serialize_times(frame).to_csv(args.out_dir / name, index=False, lineterminator="\n", float_format="%.8f")
    for name, frame in curves.items():
        frame.to_csv(args.out_dir / f"{name}_v1.csv", index=False, lineterminator="\n")

    result = {
        "schema_version": "f05_failed_reclaim_portfolio_validation_result_v1",
        "status": "PASS_RESEARCH_HISTORICAL_GATES" if historical_pass else "FAIL_RESEARCH_HISTORICAL_GATES",
        "binding_candidate": BINDING_ID,
        "non_binding_sensitivity": {"candidate_id": SENSITIVITY_ID, "binding": False, "event_count": int(len(weak)), "finalist_eligible": False, "mt4_eligible": False, "2025_eligible": False},
        "research_commit": args.research_commit,
        "workflow_run_id": int(args.workflow_run_id) if args.workflow_run_id else None,
        "workflow_run_attempt": int(args.workflow_run_attempt) if args.workflow_run_attempt else None,
        "source_sha256": actual_sha,
        "exact_exploration_source": bundle,
        "exploration_reproduction": reproduction,
        "direct_pre_raw_identity": direct_identity,
        "binding_event_summary": event_summary(direct),
        "source_signal_admission": signal_admission,
        "portfolio": portfolio_summary,
        "historical_gates": gates,
        "decision": {
            "research_historical_pass": historical_pass,
            "mt4_authorized": historical_pass,
            "2025H1_authorized": False,
            "2025H2_authorized": False,
            "reason": "MT4 is authorized only when every Research historical gate passes; 2025H1 remains locked until MT4/TDS parity passes.",
        },
        "boundaries": {
            "portfolio_replay_computed": True,
            "accepted_signal_stream_replayed": True,
            "entry_logic_changed": False,
            "candidate_definition_changed": False,
            "non_binding_sensitivity_used_for_selection": False,
            "mt4_accessed": False,
            "2025H1_accessed": False,
            "2025H2_accessed": False,
            "notion_used_as_task_source": False,
        },
    }
    write_json(args.out_dir / "result_v1.json", result)
    manifest = {
        "schema_version": "f05_failed_reclaim_portfolio_output_manifest_v1",
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in sorted(args.out_dir.iterdir()) if p.is_file()},
    }
    write_json(args.out_dir / "output_manifest_v1.json", manifest)
    print(json.dumps({"status": result["status"], "trades": len(trades), "binding_events": len(direct), "gates": gates}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
