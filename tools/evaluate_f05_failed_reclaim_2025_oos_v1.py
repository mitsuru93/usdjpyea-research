#!/usr/bin/env python3
from __future__ import annotations
import argparse, gzip, hashlib, io, json, re, tarfile
from pathlib import Path
import pandas as pd

PIP = 0.01
PERIODS = ["2025H1", "2025H2"]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

class TickStore:
    def __init__(self, root: Path):
        self.idx = {}
        self.cache = {}
        archives = sorted(root.rglob("usdjpy-2025-??-raw-ticks-v1.tar.gz"))
        if len(archives) != 12:
            raise RuntimeError(("expected_12_2025_archives", len(archives)))
        for archive in archives:
            with tarfile.open(archive, "r:gz") as tf:
                for member in tf.getmembers():
                    if member.isfile() and member.name.endswith(".csv.gz") and "decoded_csv/USDJPY/" in member.name:
                        key = member.name.split("decoded_csv/USDJPY/", 1)[1]
                        self.idx[key] = (archive, member.name)

    def hour(self, hour: pd.Timestamp) -> pd.DataFrame:
        key = hour.tz_convert("UTC").strftime("%Y/%m/%d/%H.csv.gz")
        if key in self.cache:
            return self.cache[key]
        if key not in self.idx:
            out = pd.DataFrame(columns=["timestamp_utc", "bid", "ask"])
            self.cache[key] = out
            return out
        archive, member_name = self.idx[key]
        with tarfile.open(archive, "r:gz") as tf:
            extracted = tf.extractfile(member_name)
            if extracted is None:
                raise RuntimeError(("missing_member", key))
            raw = gzip.decompress(extracted.read())
        out = pd.read_csv(io.BytesIO(raw), usecols=["timestamp_utc", "bid", "ask"])
        out["timestamp_utc"] = pd.to_datetime(out["timestamp_utc"], utc=True)
        out["bid"] = out["bid"].astype(float)
        out["ask"] = out["ask"].astype(float)
        if (out.ask < out.bid).any():
            raise RuntimeError(("negative_spread", key))
        out = out.sort_values("timestamp_utc").drop_duplicates("timestamp_utc", keep="last")
        self.cache[key] = out
        return out

    def window(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        frames = [self.hour(h) for h in pd.date_range(start.floor("h"), end.floor("h"), freq="h")]
        out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if out.empty:
            return out
        return out[(out.timestamp_utc >= start) & (out.timestamp_utc <= end)].sort_values("timestamp_utc")

def parse_level(detail: str, side: int) -> float:
    key = "current_high" if side == 1 else "current_low"
    match = re.search(rf"(?:^|;){key}=([0-9.]+)", str(detail))
    if not match:
        raise RuntimeError(("missing_breakout_level", key, detail))
    return float(match.group(1))

def load_trades(path: Path, period: str) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8-sig")
    raw["utc_time"] = pd.to_datetime(raw.utc_time, utc=True)
    opened = raw[(raw.event == "order_opened") & (raw.strategy == "F05")].copy()
    closed = raw[(raw.event == "order_closed") & (raw.strategy == "F05")].copy()
    close_by_ticket = closed.sort_values("utc_time").drop_duplicates("ticket", keep="last").set_index("ticket")
    rows = []
    for row in opened.itertuples(index=False):
        if row.ticket not in close_by_ticket.index:
            continue
        close = close_by_ticket.loc[row.ticket]
        side = int(row.side)
        rows.append({
            "period": period,
            "trade_key": f"F05|{pd.Timestamp(row.signal_utc, tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ')}|{side}",
            "ticket": int(row.ticket),
            "signal_utc": pd.to_datetime(row.signal_utc, utc=True),
            "entry_utc": pd.to_datetime(row.entry_utc, utc=True),
            "baseline_exit_utc": pd.Timestamp(close.utc_time),
            "side": side,
            "logged_entry_price": float(row.price),
            "baseline_pips": float(close.gross_pips),
            "breakout_level": parse_level(row.detail, side),
        })
    out = pd.DataFrame(rows).sort_values(["entry_utc", "ticket"]).reset_index(drop=True)
    if out.empty:
        raise RuntimeError(("no_f05_trades", str(path)))
    return out

def executable_price(frame: pd.DataFrame, side: int) -> pd.Series:
    return frame.bid if side == 1 else frame.ask

def favorable_pips(frame: pd.DataFrame, entry: float, side: int) -> pd.Series:
    return (executable_price(frame, side) - entry) * side / PIP

def inside(price: float, level: float, side: int, buffer_pips: float) -> bool:
    return price <= level + buffer_pips * PIP if side == 1 else price >= level - buffer_pips * PIP

def outside(price: float, level: float, side: int) -> bool:
    return price > level if side == 1 else price < level

def close_bars(ticks: pd.DataFrame, freq: str) -> pd.DataFrame:
    return ticks.set_index("timestamp_utc")[["bid", "ask"]].resample(freq, label="right", closed="right").last().dropna().reset_index()

def five_second_disarmed(ticks: pd.DataFrame, entry: float, side: int, end: pd.Timestamp) -> bool:
    sample = ticks[ticks.timestamp_utc <= end]
    if sample.empty:
        return False
    good = favorable_pips(sample, entry, side) >= -1e-12
    start = None
    for ts, flag in zip(sample.timestamp_utc, good):
        if flag and start is None:
            start = ts
        elif not flag:
            start = None
        if start is not None and (ts - start).total_seconds() >= 5:
            return True
    return False

def evaluate_trade(store: TickStore, tr) -> dict | None:
    ticks = store.window(tr.entry_utc, tr.baseline_exit_utc)
    if ticks.empty:
        raise RuntimeError(("missing_ticks", tr.trade_key))
    entry_ticks = ticks[ticks.timestamp_utc >= tr.entry_utc]
    if entry_ticks.empty:
        return None
    entry_tick = entry_ticks.iloc[0]
    entry = float(entry_tick.ask if tr.side == 1 else entry_tick.bid)
    first_m5 = tr.entry_utc.floor("5min") + pd.Timedelta(minutes=5)
    if first_m5 >= tr.baseline_exit_utc:
        return None
    initial = ticks[(ticks.timestamp_utc >= tr.entry_utc) & (ticks.timestamp_utc <= first_m5)]
    if initial.empty:
        return None
    first_bars = close_bars(initial, "5min")
    first_rows = first_bars[first_bars.timestamp_utc >= first_m5]
    if first_rows.empty:
        return None
    first = first_rows.iloc[0]
    first_close = float(first.bid if tr.side == 1 else first.ask)
    if not inside(first_close, tr.breakout_level, tr.side, 0.0):
        return None

    monitor_end = min(tr.baseline_exit_utc, tr.entry_utc + pd.Timedelta(minutes=60))
    post = ticks[(ticks.timestamp_utc > first_m5) & (ticks.timestamp_utc < monitor_end)]
    if post.empty:
        return None
    m1 = close_bars(post, "1min")
    reclaim = None
    for row in m1.itertuples(index=False):
        px = float(row.bid if tr.side == 1 else row.ask)
        if outside(px, tr.breakout_level, tr.side):
            reclaim = pd.Timestamp(row.timestamp_utc)
            break
    if reclaim is None:
        return None

    after = ticks[(ticks.timestamp_utc >= reclaim) & (ticks.timestamp_utc < tr.baseline_exit_utc)]
    m1_after = close_bars(after, "1min")
    run = 0
    max_run = 0
    for row in m1_after.itertuples(index=False):
        px = float(row.bid if tr.side == 1 else row.ask)
        if outside(px, tr.breakout_level, tr.side):
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
        if max_run > 2:
            return None

    m5_after = close_bars(after, "5min")
    trigger = None
    for row in m5_after[m5_after.timestamp_utc > reclaim].itertuples(index=False):
        px = float(row.bid if tr.side == 1 else row.ask)
        if inside(px, tr.breakout_level, tr.side, 0.0):
            trigger = pd.Timestamp(row.timestamp_utc)
            break
    if trigger is None or trigger >= tr.baseline_exit_utc:
        return None
    if five_second_disarmed(ticks, entry, tr.side, trigger):
        return None

    target = trigger + pd.Timedelta(seconds=5)
    exits = ticks[ticks.timestamp_utc >= target]
    if exits.empty:
        return None
    exit_tick = exits.iloc[0]
    exit_utc = pd.Timestamp(exit_tick.timestamp_utc)
    if exit_utc >= tr.baseline_exit_utc:
        return None
    exit_price = float(exit_tick.bid if tr.side == 1 else exit_tick.ask)
    candidate_pips = (exit_price - entry) * tr.side / PIP
    delta = candidate_pips - tr.baseline_pips
    return {
        "period": tr.period,
        "trade_key": tr.trade_key,
        "ticket": tr.ticket,
        "side": tr.side,
        "entry_utc": tr.entry_utc.isoformat(),
        "baseline_exit_utc": tr.baseline_exit_utc.isoformat(),
        "breakout_level": tr.breakout_level,
        "reclaim_utc": reclaim.isoformat(),
        "trigger_utc": trigger.isoformat(),
        "candidate_exit_utc": exit_utc.isoformat(),
        "baseline_pips": round(float(tr.baseline_pips), 4),
        "candidate_pips": round(float(candidate_pips), 4),
        "delta_pips": round(float(delta), 4),
        "baseline_winner": bool(tr.baseline_pips > 0),
        "maximum_consecutive_outside_m1_closes": int(max_run),
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--raw-tick-dir", required=True)
    ap.add_argument("--h1-log", required=True)
    ap.add_argument("--h2-log", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    prereg_path = Path(args.prereg)
    prereg = json.loads(prereg_path.read_text())
    assert prereg["status"] == "FROZEN_BEFORE_2025_ORDERED_TICK_OUTCOME_EXECUTION"
    assert prereg["validation_periods"] == PERIODS
    assert prereg["reoptimization_allowed"] is False
    assert prereg["proxy_substitution_allowed"] is False
    fixed = prereg["fixed_candidate"]
    assert fixed == {
        "maximum_sequence_count": 2,
        "monitoring_horizon_minutes": 60,
        "close_buffer_pips": 0.0,
        "profit_disarm_threshold_executable_pips": 0.0,
        "profit_persistence": "five_seconds",
        "failure_confirmation": "next_m5",
        "exit_delay_seconds": 5,
    }

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    store = TickStore(Path(args.raw_tick_dir))
    trades = pd.concat([
        load_trades(Path(args.h1_log), "2025H1"),
        load_trades(Path(args.h2_log), "2025H2"),
    ], ignore_index=True)
    ledger = []
    for tr in trades.itertuples(index=False):
        row = evaluate_trade(store, tr)
        if row is not None:
            ledger.append(row)
    changed = pd.DataFrame(ledger)
    if changed.empty:
        changed = pd.DataFrame(columns=["period","trade_key","ticket","side","entry_utc","baseline_exit_utc","breakout_level","reclaim_utc","trigger_utc","candidate_exit_utc","baseline_pips","candidate_pips","delta_pips","baseline_winner","maximum_consecutive_outside_m1_closes"])
    changed.to_csv(out / "changed_trade_ledger.csv", index=False)

    period_rows = []
    for period in PERIODS:
        population = trades[trades.period == period]
        group = changed[changed.period == period]
        winners = group[group.baseline_winner == True]
        losers = group[group.baseline_winner == False]
        period_rows.append({
            "period": period,
            "population_f05_trades": int(len(population)),
            "stopped": int(len(group)),
            "winner_stopped": int(len(winners)),
            "loser_stopped": int(len(losers)),
            "winner_damage_pips": round(float(winners.delta_pips.sum()), 4) if len(winners) else 0.0,
            "loser_benefit_pips": round(float(losers.delta_pips.sum()), 4) if len(losers) else 0.0,
            "total_delta_pips": round(float(group.delta_pips.sum()), 4) if len(group) else 0.0,
        })
    period_metrics = pd.DataFrame(period_rows)
    period_metrics.to_csv(out / "period_metrics.csv", index=False)

    if len(changed):
        changed["month"] = pd.to_datetime(changed.entry_utc, utc=True).dt.strftime("%Y-%m")
        monthly = changed.groupby(["period", "month"], as_index=False).agg(stopped=("trade_key", "count"), delta_pips=("delta_pips", "sum"))
        direction = changed.groupby(["period", "side"], as_index=False).agg(stopped=("trade_key", "count"), delta_pips=("delta_pips", "sum"))
    else:
        monthly = pd.DataFrame(columns=["period", "month", "stopped", "delta_pips"])
        direction = pd.DataFrame(columns=["period", "side", "stopped", "delta_pips"])
    monthly.to_csv(out / "monthly_metrics.csv", index=False)
    direction.to_csv(out / "direction_metrics.csv", index=False)

    total = round(float(changed.delta_pips.sum()), 4) if len(changed) else 0.0
    winner_damage = round(float(changed.loc[changed.baseline_winner == True, "delta_pips"].sum()), 4) if len(changed) else 0.0
    loser_benefit = round(float(changed.loc[changed.baseline_winner == False, "delta_pips"].sum()), 4) if len(changed) else 0.0
    result = {
        "schema_version": "f05_failed_reclaim_2025_oos_result_v1",
        "status": "PASS_2025_ORDERED_TICK_OOS_VALIDATION",
        "candidate_id": prereg["selection_source"]["candidate_id"],
        "candidate_frozen_before_2025_outcome_execution": True,
        "validation_periods": PERIODS,
        "reoptimization_performed": False,
        "proxy_substitution_used": False,
        "population_f05_trades": int(len(trades)),
        "stopped_trades": int(len(changed)),
        "winner_damage_pips": winner_damage,
        "loser_benefit_pips": loser_benefit,
        "total_delta_pips": total,
        "period_metrics": period_rows,
        "production_authorization": False,
    }
    (out / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    manifest = {
        "evaluator_sha256": sha256(Path(__file__)),
        "prereg_sha256": sha256(prereg_path),
        "h1_log_sha256": sha256(Path(args.h1_log)),
        "h2_log_sha256": sha256(Path(args.h2_log)),
        "result_sha256": sha256(out / "result.json"),
        "tick_archive_count": 12,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
