"""Raw Dukascopy Bid/Ask tick audit for 2024 F05 events."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from usdjpy_structural_sl_v1.common import PIP, inside, outside, r1

_HOUR_RE = re.compile(r"(?P<year>20\d{2})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<hour>\d{2})\.csv\.gz$")


class TickStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[pd.Timestamp, Path] = {}
        self.cache: dict[Path, pd.DataFrame] = {}
        for path in root.rglob("*.csv.gz"):
            normalized = path.as_posix()
            match = _HOUR_RE.search(normalized)
            if not match:
                continue
            hour = pd.Timestamp(
                f"{match.group('year')}-{match.group('month')}-{match.group('day')}T"
                f"{match.group('hour')}:00:00Z"
            )
            self.files[hour] = path
        if not self.files:
            raise FileNotFoundError(f"no hourly decoded raw tick CSV.GZ below {root}")

    def _read(self, path: Path) -> pd.DataFrame:
        if path not in self.cache:
            frame = pd.read_csv(path, compression="gzip")
            required = {"timestamp_utc", "bid", "ask"}
            missing = required.difference(frame.columns)
            if missing:
                raise ValueError(f"raw tick file {path} missing columns {sorted(missing)}")
            frame = frame[["timestamp_utc", "bid", "ask"]].copy()
            frame["timestamp_utc"] = pd.to_datetime(frame.timestamp_utc, utc=True)
            frame["bid"] = frame.bid.astype(float)
            frame["ask"] = frame.ask.astype(float)
            frame = frame.sort_values("timestamp_utc", kind="mergesort").drop_duplicates(
                "timestamp_utc", keep="last"
            )
            if bool((frame.ask < frame.bid).any()):
                raise ValueError(f"negative raw spread in {path}")
            self.cache[path] = frame.reset_index(drop=True)
        return self.cache[path]

    def between(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        start = pd.Timestamp(start)
        end = pd.Timestamp(end)
        if end <= start:
            return pd.DataFrame(columns=["timestamp_utc", "bid", "ask"])
        hours = pd.date_range(start.floor("h"), end.floor("h"), freq="h", tz="UTC")
        pieces: list[pd.DataFrame] = []
        for hour in hours:
            path = self.files.get(pd.Timestamp(hour))
            if path is None:
                continue
            pieces.append(self._read(path))
        if not pieces:
            return pd.DataFrame(columns=["timestamp_utc", "bid", "ask"])
        frame = pd.concat(pieces, ignore_index=True)
        return frame[
            (frame.timestamp_utc >= start) & (frame.timestamp_utc < end)
        ].copy().reset_index(drop=True)


def _exec_series(ticks: pd.DataFrame, side: int) -> pd.Series:
    return ticks.bid if side == 1 else ticks.ask


def _positive_mask(ticks: pd.DataFrame, side: int, entry_price: float) -> pd.Series:
    values = _exec_series(ticks, side)
    return values > entry_price + 1.0e-12 if side == 1 else values < entry_price - 1.0e-12


def _last_exec(ticks: pd.DataFrame, side: int, start: pd.Timestamp, end: pd.Timestamp) -> float | None:
    window = ticks[(ticks.timestamp_utc >= start) & (ticks.timestamp_utc < end)]
    if window.empty:
        return None
    row = window.iloc[-1]
    return float(row.bid if side == 1 else row.ask)


def _raw_failed_reclaim(
    trade: object,
    store: TickStore,
) -> dict[str, object]:
    side = int(trade.side)
    entry = pd.Timestamp(trade.entry_utc)
    baseline_close = pd.Timestamp(trade.baseline_exit_utc)
    level = float(trade.breakout_level)
    entry_price = float(trade.entry_price)
    first_start = entry.floor("5min")
    first_completion = first_start + pd.Timedelta(minutes=5)

    ticks = store.between(entry, baseline_close + pd.Timedelta(minutes=1))
    base = {
        "trade_id": str(trade.trade_id),
        "fold": str(trade.fold),
        "side": side,
        "entry_utc": entry,
        "baseline_exit_utc": baseline_close,
        "breakout_level": level,
        "entry_price": entry_price,
        "month": entry.strftime("%Y-%m"),
        "source_layer": "RAW_BID_ASK_TICKS",
    }
    if ticks.empty:
        return {**base, "status": "RAW_TICKS_MISSING", "armed": False, "event_order_pass": False}

    first_close = _last_exec(ticks, side, first_start, first_completion)
    if first_close is None:
        return {**base, "status": "FIRST_M5_EMPTY", "armed": False, "event_order_pass": False}
    if not inside(first_close, level, side, 0.02):
        return {**base, "status": "INITIAL_M5_NOT_INSIDE_2P", "armed": False, "event_order_pass": True}
    through_first = ticks[ticks.timestamp_utc < first_completion]
    if bool(_positive_mask(through_first, side, entry_price).any()):
        return {**base, "status": "PROFIT_DISARMED_BEFORE_INITIAL_M5", "armed": False, "event_order_pass": True}

    minute_starts = pd.date_range(first_completion, baseline_close, freq="min", tz="UTC")
    reclaim: pd.Timestamp | None = None
    for start in minute_starts:
        completion = pd.Timestamp(start) + pd.Timedelta(minutes=1)
        if completion >= baseline_close:
            break
        close_price = _last_exec(ticks, side, pd.Timestamp(start), completion)
        if close_price is not None and outside(close_price, level, side):
            reclaim = completion
            break
    if reclaim is None:
        return {**base, "status": "NO_RAW_RECLAIM", "armed": False, "event_order_pass": True}

    first_failure_completion = reclaim.floor("5min") + pd.Timedelta(minutes=5)
    if first_failure_completion <= reclaim:
        first_failure_completion += pd.Timedelta(minutes=5)
    failure_start = first_failure_completion - pd.Timedelta(minutes=5)
    failure_close = _last_exec(ticks, side, failure_start, first_failure_completion)
    if failure_close is None:
        return {**base, "status": "FAILURE_M5_EMPTY", "armed": False, "event_order_pass": False}
    if not inside(failure_close, level, side):
        return {**base, "status": "FIRST_LATER_M5_NOT_INSIDE", "armed": False, "event_order_pass": True}

    through_trigger = ticks[ticks.timestamp_utc <= first_failure_completion]
    positive = through_trigger[_positive_mask(through_trigger, side, entry_price)]
    if not positive.empty:
        return {
            **base,
            "status": "PROFIT_DISARMED_THROUGH_TRIGGER",
            "armed": False,
            "event_order_pass": True,
            "reclaim_utc": reclaim,
            "trigger_utc": first_failure_completion,
            "first_positive_tick_utc": pd.Timestamp(positive.iloc[0].timestamp_utc),
        }

    exit_ticks = ticks[ticks.timestamp_utc >= first_failure_completion]
    if exit_ticks.empty:
        return {**base, "status": "NO_EXECUTABLE_TICK_AFTER_TRIGGER", "armed": False, "event_order_pass": False}
    exit_tick = exit_ticks.iloc[0]
    exit_time = pd.Timestamp(exit_tick.timestamp_utc)
    if exit_time >= baseline_close:
        return {**base, "status": "BASELINE_EXIT_EARLIER", "armed": False, "event_order_pass": True}
    exit_price = float(exit_tick.bid if side == 1 else exit_tick.ask)
    candidate_pips = side * (exit_price - entry_price) / PIP
    baseline_pips = float(trade.baseline_pips)

    outside_flags: list[bool] = []
    for start in pd.date_range(reclaim - pd.Timedelta(minutes=1), first_failure_completion, freq="min", tz="UTC"):
        completion = pd.Timestamp(start) + pd.Timedelta(minutes=1)
        if completion > first_failure_completion:
            break
        close_price = _last_exec(ticks, side, pd.Timestamp(start), completion)
        if close_price is not None:
            outside_flags.append(outside(close_price, level, side))
    longest = run = 0
    for flag in outside_flags:
        run = run + 1 if flag else 0
        longest = max(longest, run)

    return {
        **base,
        "status": "RAW_EVENT_ARMED",
        "armed": True,
        "event_order_pass": bool(first_completion < reclaim < first_failure_completion < exit_time < baseline_close),
        "first_m5_completion_utc": first_completion,
        "reclaim_utc": reclaim,
        "trigger_utc": first_failure_completion,
        "candidate_exit_utc": exit_time,
        "exit_price": exit_price,
        "baseline_pips": r1(baseline_pips),
        "candidate_pips": r1(candidate_pips),
        "delta_pips": r1(candidate_pips - baseline_pips),
        "reclaim_minutes": int((reclaim - entry).total_seconds() // 60),
        "max_consecutive_outside_m1_closes": int(longest),
        "weak_quick_eligible": bool((reclaim - entry) <= pd.Timedelta(minutes=60) and longest <= 2),
    }


def audit_2024_events(pre_raw_ledger: pd.DataFrame, raw_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    if pre_raw_ledger.empty:
        return pre_raw_ledger.copy(), pd.DataFrame()
    store = TickStore(raw_root)
    audits = [_raw_failed_reclaim(row, store) for row in pre_raw_ledger.itertuples(index=False)]
    audit = pd.DataFrame(audits).sort_values(["entry_utc", "trade_id"], kind="mergesort").reset_index(drop=True)
    armed = audit[audit.armed.astype(bool)].copy()
    if armed.empty:
        return armed, audit
    columns = [
        "trade_id", "fold", "side", "entry_utc", "baseline_exit_utc", "trigger_utc",
        "candidate_exit_utc", "reclaim_utc", "first_m5_completion_utc", "breakout_level",
        "entry_price", "baseline_pips", "candidate_pips", "delta_pips", "reclaim_minutes",
        "max_consecutive_outside_m1_closes", "weak_quick_eligible", "source_layer",
    ]
    return armed[columns].copy(), audit
