#!/usr/bin/env python3
"""Audit Rakuten MT4 server-time conversion used by the accepted 2024 H1 baseline."""

from __future__ import annotations

import argparse
import calendar
import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_ARTIFACT_SHA256 = "e078758343995c8254244dd36385c93a61a7124cb5037beb458afdf5d0e208e5"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nth_sunday_utc(year: int, month: int, nth: int, hour: int) -> pd.Timestamp:
    value = pd.Timestamp(year=year, month=month, day=1, hour=hour, tz="UTC")
    return value + pd.Timedelta(days=(6 - value.weekday()) % 7 + 7 * (nth - 1))


def last_sunday_utc(year: int, month: int, hour: int = 1) -> pd.Timestamp:
    value = pd.Timestamp(
        year=year,
        month=month,
        day=calendar.monthrange(year, month)[1],
        hour=hour,
        tz="UTC",
    )
    while value.weekday() != 6:
        value -= pd.Timedelta(days=1)
    return value


def load_source(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with zipfile.ZipFile(path) as archive:
        required = {
            "m15_utc_2024h1.csv",
            "trade_ledger_2024h1.csv",
            "tester/fx2_usdjpy_2024h1_event_audit_fixed_001_each_v1.csv",
        }
        missing = sorted(required - set(archive.namelist()))
        if missing:
            raise RuntimeError(f"artifact missing: {missing}")
        bars = pd.read_csv(io.BytesIO(archive.read("m15_utc_2024h1.csv")))
        ledger = pd.read_csv(io.BytesIO(archive.read("trade_ledger_2024h1.csv")))
        raw_audit = archive.read(
            "tester/fx2_usdjpy_2024h1_event_audit_fixed_001_each_v1.csv"
        )
    audit = None
    for encoding in ("utf-8-sig", "cp932", "cp1252", "latin-1"):
        try:
            audit = pd.read_csv(io.BytesIO(raw_audit), encoding=encoding)
            break
        except UnicodeDecodeError:
            pass
    if audit is None:
        raise RuntimeError("audit decoding failed")
    return bars, ledger, audit


def reconstruct_server_and_corrected_utc(
    old_utc: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    year = int(old_utc.iloc[0].year)
    us_start = nth_sunday_utc(year, 3, 2, 7)
    us_end = nth_sunday_utc(year, 11, 1, 6)
    us_summer = (old_utc >= us_start) & (old_utc < us_end)
    server = old_utc + pd.to_timedelta(np.where(us_summer, 3, 2), unit="h")
    server_naive = server.dt.tz_localize(None)

    eu_start = last_sunday_utc(year, 3, 1)
    eu_end = last_sunday_utc(year, 10, 1)
    standard_utc = (server_naive - pd.Timedelta(hours=2)).dt.tz_localize("UTC")
    summer_utc = (server_naive - pd.Timedelta(hours=3)).dt.tz_localize("UTC")
    summer_valid = (summer_utc >= eu_start) & (summer_utc < eu_end)
    standard_valid = ~((standard_utc >= eu_start) & (standard_utc < eu_end))
    ambiguous = summer_valid & standard_valid
    nonexistent = ~summer_valid & ~standard_valid
    if bool(ambiguous.any()) or bool(nonexistent.any()):
        raise RuntimeError(
            f"DST ambiguity: ambiguous={int(ambiguous.sum())}, "
            f"nonexistent={int(nonexistent.sum())}"
        )
    corrected_ns = standard_utc.astype("int64")
    corrected_ns.loc[summer_valid] = summer_utc.loc[summer_valid].astype("int64")
    corrected = pd.to_datetime(corrected_ns, utc=True)
    return server_naive, corrected, corrected - old_utc


def simulate_signals(times: pd.Series, bars: pd.DataFrame) -> pd.DataFrame:
    rows: list[tuple] = []
    last_long_day = 0
    last_short_day = 0
    for entry_index in range(1, len(times)):
        if entry_index >= 100:
            signal_time = times.iloc[entry_index - 1]
            entry_time = times.iloc[entry_index]
            if 7 <= signal_time.hour <= 12:
                signal_day = signal_time.date()
                ref_high = -1.0e100
                ref_low = 1.0e100
                found = False
                for shift in range(1, min(entry_index, 400) + 1):
                    index = entry_index - shift
                    value = times.iloc[index]
                    if value.date() != signal_day:
                        if found:
                            break
                        continue
                    if 0 <= value.hour < 7:
                        ref_high = max(ref_high, float(bars.iloc[index]["high"]))
                        ref_low = min(ref_low, float(bars.iloc[index]["low"]))
                        found = True
                if found:
                    close = float(bars.iloc[entry_index - 1]["close"])
                    side = 1 if close > ref_high else -1 if close < ref_low else 0
                    day_number = (
                        signal_time.year * 10000
                        + signal_time.month * 100
                        + signal_time.day
                    )
                    if side == 1 and last_long_day == day_number:
                        side = 0
                    if side == -1 and last_short_day == day_number:
                        side = 0
                    if side:
                        if side == 1:
                            last_long_day = day_number
                        else:
                            last_short_day = day_number
                        rows.append(
                            (
                                "B02",
                                entry_index - 1,
                                entry_index,
                                signal_time,
                                entry_time,
                                side,
                            )
                        )

        if entry_index >= 120:
            signal_time = times.iloc[entry_index - 1]
            entry_time = times.iloc[entry_index]
            if 0 <= entry_time.hour <= 19:
                current = bars.iloc[entry_index - 97 : entry_index - 1]
                previous = bars.iloc[entry_index - 98 : entry_index - 2]
                signal_close = float(bars.iloc[entry_index - 1]["close"])
                previous_close = float(bars.iloc[entry_index - 2]["close"])
                side = 0
                if (
                    signal_close > current["high"].max()
                    and previous_close <= previous["high"].max()
                ):
                    side = 1
                elif (
                    signal_close < current["low"].min()
                    and previous_close >= previous["low"].min()
                ):
                    side = -1
                if side:
                    rows.append(
                        (
                            "F05",
                            entry_index - 1,
                            entry_index,
                            signal_time,
                            entry_time,
                            side,
                        )
                    )
    return pd.DataFrame(
        rows,
        columns=[
            "strategy",
            "signal_index",
            "entry_index",
            "signal_time",
            "entry_time",
            "side",
        ],
    )


def attach_trade_results(signals: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    result = signals.copy()
    pips = []
    for _, row in result.iterrows():
        entry_index = int(row["entry_index"])
        cap = 48 if row["strategy"] == "B02" else 32
        close_index = entry_index + cap
        if close_index >= len(bars):
            pips.append(np.nan)
            continue
        side = int(row["side"])
        spread = 5 * 0.001
        entry_bid = float(bars.iloc[entry_index]["open"])
        close_bid = float(bars.iloc[close_index]["open"])
        entry_price = entry_bid + spread if side == 1 else entry_bid
        close_price = close_bid if side == 1 else close_bid + spread
        pips.append(round(side * (close_price - entry_price) / 0.01, 6))
    result["gross_pips"] = pips
    result["closed"] = result["gross_pips"].notna()
    result["realized_pl_jpy"] = result["gross_pips"] * 10.0
    return result


def metric_block(frame: pd.DataFrame) -> dict:
    closed = frame.loc[frame["closed"]].copy()
    gross_profit = float(closed.loc[closed["realized_pl_jpy"] > 0, "realized_pl_jpy"].sum())
    gross_loss = float(-closed.loc[closed["realized_pl_jpy"] < 0, "realized_pl_jpy"].sum())
    return {
        "opened_trades": int(len(frame)),
        "closed_trades": int(len(closed)),
        "B02_opened": int((frame["strategy"] == "B02").sum()),
        "F05_opened": int((frame["strategy"] == "F05").sum()),
        "net_jpy": float(closed["realized_pl_jpy"].sum()),
        "gross_profit_jpy": gross_profit,
        "gross_loss_jpy": gross_loss,
        "profit_factor": gross_profit / gross_loss,
        "wins": int((closed["realized_pl_jpy"] > 0).sum()),
        "losses": int((closed["realized_pl_jpy"] < 0).sum()),
        "flat": int((closed["realized_pl_jpy"] == 0).sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-zip", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    actual_sha = sha256_file(args.artifact_zip)
    if actual_sha != EXPECTED_ARTIFACT_SHA256:
        raise RuntimeError(f"artifact SHA {actual_sha} != {EXPECTED_ARTIFACT_SHA256}")

    bars, ledger, audit = load_source(args.artifact_zip)
    old_utc = pd.to_datetime(
        bars["utc_time"], format="%Y-%m-%d %H:%M:%S", utc=True
    )
    server, corrected_utc, delta = reconstruct_server_and_corrected_utc(old_utc)

    old = attach_trade_results(simulate_signals(old_utc, bars), bars)
    corrected = attach_trade_results(simulate_signals(corrected_utc, bars), bars)

    old["signal_text"] = old["signal_time"].dt.strftime("%Y.%m.%d %H:%M:%S")
    accepted_keys = set(
        map(
            tuple,
            audit.loc[audit["event"] == "order_opened", ["strategy", "signal_utc", "side"]]
            .astype(str)
            .to_numpy(),
        )
    )
    simulated_keys = set(
        map(
            tuple,
            old[["strategy", "signal_text", "side"]].astype(str).to_numpy(),
        )
    )
    if accepted_keys != simulated_keys:
        raise RuntimeError(
            f"old implementation signal parity failed: "
            f"missing={len(accepted_keys - simulated_keys)}, "
            f"unexpected={len(simulated_keys - accepted_keys)}"
        )

    closed_old = old.loc[old["closed"]].copy()
    closed_old["signal_text"] = closed_old["signal_time"].dt.strftime(
        "%Y.%m.%d %H:%M:%S"
    )
    comparison = closed_old.merge(
        ledger[["strategy", "signal_utc", "side", "gross_pips"]],
        left_on=["strategy", "signal_text", "side"],
        right_on=["strategy", "signal_utc", "side"],
        how="left",
    )
    if comparison["gross_pips_y"].isna().any():
        raise RuntimeError("old implementation closed-trade reconciliation failed")
    max_pip_diff = float(
        (comparison["gross_pips_x"] - comparison["gross_pips_y"]).abs().max()
    )
    if max_pip_diff != 0.0:
        raise RuntimeError(f"old implementation P/L parity failed: {max_pip_diff}")

    old_key = set(
        map(
            tuple,
            old[["strategy", "signal_index", "entry_index", "side"]].to_numpy(),
        )
    )
    corrected_key = set(
        map(
            tuple,
            corrected[
                ["strategy", "signal_index", "entry_index", "side"]
            ].to_numpy(),
        )
    )

    def describe_difference(frame: pd.DataFrame, selected: set[tuple]) -> list[dict]:
        rows = []
        for _, row in frame.iterrows():
            key = (
                row["strategy"],
                row["signal_index"],
                row["entry_index"],
                row["side"],
            )
            if key not in selected:
                continue
            index = int(row["signal_index"])
            rows.append(
                {
                    "strategy": row["strategy"],
                    "side": int(row["side"]),
                    "signal_mt4_server": server.iloc[index].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "old_signal_utc": old_utc.iloc[index].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "corrected_signal_utc": corrected_utc.iloc[index].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "gross_pips": (
                        None
                        if pd.isna(row["gross_pips"])
                        else float(row["gross_pips"])
                    ),
                    "realized_pl_jpy": (
                        None
                        if pd.isna(row["realized_pl_jpy"])
                        else float(row["realized_pl_jpy"])
                    ),
                }
            )
        return rows

    old_metrics = metric_block(old)
    corrected_metrics = metric_block(corrected)
    old_only = describe_difference(old, old_key - corrected_key)
    corrected_only = describe_difference(corrected, corrected_key - old_key)

    result = {
        "schema_version": "usdjpy_2024_timezone_conversion_research_audit_v1",
        "status": "BEHAVIORAL_IMPACT_CONFIRMED",
        "source": {
            "run_id": 29787357305,
            "artifact_id": 8479048161,
            "artifact_sha256": actual_sha,
        },
        "conversion": {
            "current_implementation": "GMT+2/GMT+3 selected by US DST boundaries",
            "corrected_implementation": "GMT+2/GMT+3 selected by Europe/EET-EEST boundaries",
            "m15_rows_shifted_by_one_hour": int((delta.dt.total_seconds() != 0).sum()),
            "first_shifted_corrected_utc": corrected_utc[delta.dt.total_seconds() != 0]
            .iloc[0]
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_shifted_corrected_utc": corrected_utc[delta.dt.total_seconds() != 0]
            .iloc[-1]
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ambiguous_rows": 0,
            "nonexistent_rows": 0,
        },
        "reconciliation": {
            "current_signal_set_exact_match": True,
            "current_closed_trade_pips_exact_match": True,
            "maximum_current_pip_difference": max_pip_diff,
        },
        "current_metrics": old_metrics,
        "corrected_expected_metrics": corrected_metrics,
        "delta": {
            "opened_trades": corrected_metrics["opened_trades"]
            - old_metrics["opened_trades"],
            "closed_trades": corrected_metrics["closed_trades"]
            - old_metrics["closed_trades"],
            "B02_opened": corrected_metrics["B02_opened"]
            - old_metrics["B02_opened"],
            "F05_opened": corrected_metrics["F05_opened"]
            - old_metrics["F05_opened"],
            "net_jpy": corrected_metrics["net_jpy"] - old_metrics["net_jpy"],
            "profit_factor": corrected_metrics["profit_factor"]
            - old_metrics["profit_factor"],
            "old_only_server_bar_signals": len(old_key - corrected_key),
            "corrected_only_server_bar_signals": len(corrected_key - old_key),
            "common_server_bar_signals": len(old_key & corrected_key),
        },
        "old_only_signals": old_only,
        "corrected_only_signals": corrected_only,
        "boundaries": {
            "candidate_evaluated": False,
            "2024_H2_accessed": False,
            "2025_accessed": False,
            "live_orders": False,
        },
        "next_action": "require exact Rakuten MT4 reproduction of corrected expected metrics before choosing the canonical baseline clock implementation",
    }
    output = args.output_dir / "usdjpy_2024_timezone_conversion_research_audit_v1.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
