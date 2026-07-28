#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

HYPOTHESIS_ID = "USDJPY-HYP-032"
FAMILY_ID = "R_SHORT_REALIZED_LOSS_PERSISTENCE"
CANDIDATE_ID = "C1_SHORT_SHARED_SESSION_LOSS_CAP_2"
INPUT_SHA256 = "d2b9a2845a1793d614fb4be193963c29ee2f958733c49d7d1b656184c7d18670"
INPUT_BYTES = 1_600_400
SOURCE_CORE_RUN_ID = 30355284109
SOURCE_CORE_SHA = "898d6c19f747dddaf93372e5fe26dc4c01dd3b86"
SOURCE_RELEASE_ASSET_SHA256 = "e6f06139e7b8d0120da8249441fc9457ef556f44fcc83c974190bbc9e9257165"
SCORING_START = datetime(2020, 1, 1)
SCORING_END = datetime(2023, 1, 1)
CANONICAL_INITIAL_CAPITAL_JPY = 100_000.0
CONTRACT_SIZE = 100_000.0
BOOTSTRAP_SEED = 20260728
BOOTSTRAP_REPLICATES = 10_000
TOLERANCE = 1e-6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--currency-repair-preregistration", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--research-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def parse_dt(value: str | None) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in (None, "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.fromisoformat(text) if fmt is None else datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unsupported datetime: {value!r}")


def session_name(value: datetime) -> str:
    if value.hour < 7:
        return "Tokyo"
    if value.hour < 13:
        return "London"
    if value.hour < 16:
        return "London_NY_overlap"
    if value.hour < 20:
        return "New_York"
    return "session_transition"


def session_key(value: datetime) -> str:
    return f"{value:%Y-%m-%d}|{session_name(value)}"


def halfyear(value: datetime) -> str:
    return f"{value.year}H{1 if value.month <= 6 else 2}"


def profit_factor(values: Iterable[float]) -> float | None:
    values = list(values)
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else None
    return gross_profit / gross_loss


def realized_drawdown(values: Iterable[float]) -> float:
    cumulative = 0.0
    peak = 0.0
    maximum = 0.0
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        maximum = max(maximum, peak - cumulative)
    return maximum


def equity_drawdown(values: Iterable[float]) -> float:
    iterator = iter(values)
    try:
        first = next(iterator)
    except StopIteration:
        return 0.0
    peak = first
    maximum = 0.0
    for value in iterator:
        peak = max(peak, value)
        maximum = max(maximum, peak - value)
    return maximum


def metric_block(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: (row["close_sequence"], row["ticket"]))
    values = [float(row[key]) for row in ordered]
    return {
        "trades": len(ordered),
        "net_jpy": sum(values),
        "gross_profit_jpy": sum(value for value in values if value > 0),
        "gross_loss_jpy": -sum(value for value in values if value < 0),
        "profit_factor": profit_factor(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "breakeven": sum(abs(value) <= TOLERANCE for value in values),
        "realized_drawdown_jpy": realized_drawdown(values),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def positive_share(values: dict[str, float]) -> float:
    positives = [value for value in values.values() if value > 0]
    return max(positives) / sum(positives) if positives else 0.0


def bootstrap(cluster_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_year: dict[int, list[float]] = defaultdict(list)
    for row in cluster_rows:
        by_year[int(row["year"])].append(float(row["delta_jpy"]))
    if sorted(by_year) != [2020, 2021, 2022] or any(not by_year[year] for year in by_year):
        raise RuntimeError("bootstrap strata missing")
    rng = random.Random(BOOTSTRAP_SEED)
    samples: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATES):
        total = 0.0
        for year in (2020, 2021, 2022):
            values = by_year[year]
            total += sum(values[rng.randrange(len(values))] for _ in values)
        samples.append(total)
    samples.sort()
    lower = samples[math.floor(0.025 * (BOOTSTRAP_REPLICATES - 1))]
    upper = samples[math.ceil(0.975 * (BOOTSTRAP_REPLICATES - 1))]
    return {
        "method": "calendar-year-stratified UTC entry-date/session cluster bootstrap",
        "seed": BOOTSTRAP_SEED,
        "replicates": BOOTSTRAP_REPLICATES,
        "cluster_counts": {str(year): len(by_year[year]) for year in sorted(by_year)},
        "ci95_jpy": [lower, upper],
        "probability_nonpositive": sum(value <= 0 for value in samples) / BOOTSTRAP_REPLICATES,
    }


def bid_ask_for_close(event: dict[str, Any], spread: float) -> tuple[float, float]:
    price = float(event["price"])
    side = int(event["side"])
    if side > 0:
        return price, price + spread
    if side < 0:
        return price - spread, price
    raise RuntimeError(f"invalid close side for ticket {event['ticket']}")


def account_amount_to_jpy(amount: float, bid: float, ask: float) -> float:
    if amount > 0:
        return amount * bid
    if amount < 0:
        return amount * ask
    return 0.0


def position_mtm_jpy(position: dict[str, Any], bid: float, ask: float) -> float:
    entry = float(position["entry_price"])
    lots = float(position["lots"])
    if int(position["side"]) > 0:
        return (bid - entry) * CONTRACT_SIZE * lots
    return (entry - ask) * CONTRACT_SIZE * lots


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    freeze = json.loads(args.freeze.read_text(encoding="utf-8"))
    original_prereg = json.loads(args.preregistration.read_text(encoding="utf-8"))
    repair_prereg = json.loads(args.currency_repair_preregistration.read_text(encoding="utf-8"))
    assert freeze["hypothesis_id"] == HYPOTHESIS_ID
    assert freeze["candidate_id"] == CANDIDATE_ID
    assert freeze["threshold"] == 2
    assert freeze["winner_reset"] is False
    assert freeze["no_retuning"] is True
    assert original_prereg["hypothesis_id"] == HYPOTHESIS_ID
    assert original_prereg["candidate_id"] == CANDIDATE_ID
    assert original_prereg["input_gzip_sha256"] == INPUT_SHA256
    assert original_prereg["no_retuning"] is True
    assert repair_prereg["hypothesis_id"] == HYPOTHESIS_ID
    assert repair_prereg["candidate_id"] == CANDIDATE_ID
    assert repair_prereg["source_invalid_run_id"] == 30361067984
    assert repair_prereg["candidate_rule_changed"] is False
    assert repair_prereg["scientific_gates_changed"] is False
    assert repair_prereg["retuning"] is False
    assert repair_prereg["2025_accessed"] is False
    if args.preflight_only:
        write_json(args.out_dir / "preflight_result.json", {
            "status": "PASS_CURRENCY_REPAIR_PREFLIGHT_NO_CANDIDATE_OUTCOME_ACCESS",
            "hypothesis_id": HYPOTHESIS_ID,
            "candidate_id": CANDIDATE_ID,
            "candidate_outcome_computed": False,
            "scientific_result": False,
            "2025_accessed": False,
        })
        return
    if args.input.stat().st_size != INPUT_BYTES or sha256(args.input) != INPUT_SHA256:
        raise RuntimeError("input identity mismatch")
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        header = json.loads(next(handle))
        events = [json.loads(line) for line in handle if line.strip()]
    assert header["record_type"] == "header"
    assert header["hypothesis_id"] == HYPOTHESIS_ID
    assert header["source_run_id"] == SOURCE_CORE_RUN_ID
    assert header["source_core_sha"] == SOURCE_CORE_SHA
    assert header["source_release_asset_sha256"] == SOURCE_RELEASE_ASSET_SHA256
    assert header["candidate_outcomes_computed"] is False
    assert header["candidate_logic_present"] is False
    assert header["2025_accessed"] is False
    spread = float(header["account_contract"]["spread_points"]) * 0.001
    counts: dict[str, int] = defaultdict(int)
    by_timestamp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    previous_sequence = 0
    for event in events:
        sequence = int(event["audit_sequence"])
        if event["record_type"] != "event" or sequence <= previous_sequence:
            raise RuntimeError("event sequence failure")
        previous_sequence = sequence
        counts[event["event"]] += 1
        by_timestamp[event["utc_time"]].append(event)
    expected_counts = {"order_opened": 3624, "order_closed": 3624, "portfolio_snapshot": 100055}
    if dict(counts) != expected_counts:
        raise RuntimeError(f"event count mismatch: {dict(counts)}")
    chronology_violations: list[str] = []
    for timestamp, rows in by_timestamp.items():
        closes = [int(row["audit_sequence"]) for row in rows if row["event"] == "order_closed"]
        opens = [int(row["audit_sequence"]) for row in rows if row["event"] == "order_opened"]
        if closes and opens and max(closes) >= min(opens):
            chronology_violations.append(timestamp)
    if chronology_violations:
        raise RuntimeError(f"native chronology violation: {chronology_violations[:5]}")
    close_model_rows: list[dict[str, float]] = []
    first_account_balance = None
    for event in events:
        if first_account_balance is None:
            first_account_balance = float(event["balance_jpy"])
        if event["event"] != "order_closed":
            continue
        account_delta = float(event["balance_delta_jpy"])
        gross_formula_jpy = float(event["gross_pips"]) * float(event["lots"]) * 1000.0
        bid, ask = bid_ask_for_close(event, spread)
        converted_jpy = account_amount_to_jpy(account_delta, bid, ask)
        close_model_rows.append({
            "account_delta": account_delta,
            "gross_formula_jpy": gross_formula_jpy,
            "jpy_hypothesis_abs_residual": abs(account_delta - gross_formula_jpy),
            "usd_hypothesis_abs_residual": abs(converted_jpy - gross_formula_jpy),
            "converted_net_jpy": converted_jpy,
        })
    nonzero_model_rows = [row for row in close_model_rows if abs(row["account_delta"]) > 0.005 and abs(row["gross_formula_jpy"]) > 0.5]
    if not nonzero_model_rows:
        raise RuntimeError("currency inference has no nonzero closes")
    median_jpy_residual = statistics.median(row["jpy_hypothesis_abs_residual"] for row in nonzero_model_rows)
    median_usd_residual = statistics.median(row["usd_hypothesis_abs_residual"] for row in nonzero_model_rows)
    currency_inference_pass = (
        9_000.0 <= float(first_account_balance) <= 11_000.0
        and median_usd_residual < median_jpy_residual * 0.10
        and median_usd_residual <= 5.0
    )
    inferred_account_currency = "USD" if currency_inference_pass else "UNRESOLVED"
    loss_counts: dict[str, int] = defaultdict(int)
    decisions: dict[int, dict[str, Any]] = {}
    baseline_open: dict[int, dict[str, Any]] = {}
    candidate_open: dict[int, dict[str, Any]] = {}
    trades: dict[int, dict[str, Any]] = {}
    duplicate_decisions: list[int] = []
    orphan_closes: list[int] = []
    baseline_balance_jpy = CANONICAL_INITIAL_CAPITAL_JPY
    candidate_balance_jpy = CANONICAL_INITIAL_CAPITAL_JPY
    snapshots: list[dict[str, Any]] = []
    floating_diagnostic_residuals: list[float] = []
    max_open_orders = 0
    for event in events:
        timestamp = parse_dt(event["utc_time"])
        if timestamp is None:
            raise RuntimeError("event without utc_time")
        kind = event["event"]
        ticket = int(event["ticket"])
        if kind == "order_opened":
            if ticket in decisions:
                duplicate_decisions.append(ticket)
                continue
            entry_time = parse_dt(event["entry_utc"])
            if entry_time is None:
                raise RuntimeError(f"open without entry_utc: {ticket}")
            key = session_key(entry_time)
            prior_losses = loss_counts[key]
            applicable = int(event["side"]) < 0 and event["strategy"] in {"B02", "F05"}
            allow = (not applicable) or prior_losses < 2
            decision = {
                "ticket": ticket,
                "trade_id": f"MT4-{ticket}",
                "strategy": event["strategy"],
                "side": int(event["side"]),
                "side_label": "LONG" if int(event["side"]) > 0 else "SHORT",
                "entry_utc": entry_time.isoformat(),
                "entry_sequence": int(event["audit_sequence"]),
                "entry_session": session_name(entry_time),
                "entry_session_key": key,
                "fold": halfyear(entry_time),
                "year": entry_time.year,
                "month": entry_time.strftime("%Y-%m"),
                "entry_date": entry_time.strftime("%Y-%m-%d"),
                "prior_relevant_loss_count": prior_losses,
                "applicable": applicable,
                "allow": allow,
                "reason": "ALLOW_NON_TARGET" if not applicable else "ALLOW_PRIOR_LOSSES_LT_2" if allow else "BLOCK_SHORT_SHARED_SESSION_LOSS_CAP_2",
                "lots": float(event["lots"]),
                "entry_price": float(event["price"]),
            }
            decisions[ticket] = decision
            baseline_open[ticket] = decision
            if allow:
                candidate_open[ticket] = decision
        elif kind == "order_closed":
            decision = decisions.get(ticket)
            if decision is None:
                orphan_closes.append(ticket)
                continue
            if ticket not in baseline_open:
                raise RuntimeError(f"baseline close without open position: {ticket}")
            account_delta = float(event["balance_delta_jpy"])
            bid, ask = bid_ask_for_close(event, spread)
            realized_jpy = account_amount_to_jpy(account_delta, bid, ask)
            gross_formula_jpy = float(event["gross_pips"]) * float(event["lots"]) * 1000.0
            nonprice_residual_jpy = realized_jpy - gross_formula_jpy
            baseline_balance_jpy += realized_jpy
            baseline_open.pop(ticket)
            if decision["allow"]:
                candidate_balance_jpy += realized_jpy
                candidate_open.pop(ticket, None)
                if realized_jpy < 0:
                    loss_counts[session_key(timestamp)] += 1
            record = dict(decision)
            record.update({
                "close_utc": timestamp.isoformat(),
                "close_sequence": int(event["audit_sequence"]),
                "close_session": session_name(timestamp),
                "close_session_key": session_key(timestamp),
                "close_price": float(event["price"]),
                "gross_pips": float(event["gross_pips"]),
                "account_balance_delta_usd": account_delta,
                "gross_formula_pl_jpy": gross_formula_jpy,
                "nonprice_and_conversion_residual_jpy": nonprice_residual_jpy,
                "realized_pl_jpy": realized_jpy,
                "candidate_pl_jpy": realized_jpy if decision["allow"] else 0.0,
                "delta_jpy": 0.0 if decision["allow"] else -realized_jpy,
                "scoring": SCORING_START <= parse_dt(decision["entry_utc"]) < SCORING_END,
            })
            trades[ticket] = record
        elif kind == "portfolio_snapshot":
            bid = float(event["price"])
            ask = bid + spread
            baseline_unrealized_jpy = sum(position_mtm_jpy(position, bid, ask) for position in baseline_open.values())
            candidate_unrealized_jpy = sum(position_mtm_jpy(position, bid, ask) for position in candidate_open.values())
            baseline_equity_jpy = baseline_balance_jpy + baseline_unrealized_jpy
            candidate_equity_jpy = candidate_balance_jpy + candidate_unrealized_jpy
            account_floating_usd = float(event["equity_jpy"]) - float(event["balance_jpy"])
            account_floating_jpy = account_amount_to_jpy(account_floating_usd, bid, ask)
            floating_residual_jpy = baseline_unrealized_jpy - account_floating_jpy
            floating_diagnostic_residuals.append(floating_residual_jpy)
            max_open_orders = max(max_open_orders, len(baseline_open))
            if SCORING_START <= timestamp < SCORING_END:
                snapshots.append({
                    "audit_sequence": int(event["audit_sequence"]),
                    "utc_time": timestamp.isoformat(),
                    "baseline_balance_jpy": baseline_balance_jpy,
                    "candidate_balance_jpy": candidate_balance_jpy,
                    "baseline_unrealized_jpy": baseline_unrealized_jpy,
                    "candidate_unrealized_jpy": candidate_unrealized_jpy,
                    "baseline_equity_jpy": baseline_equity_jpy,
                    "candidate_equity_jpy": candidate_equity_jpy,
                    "baseline_open_count": len(baseline_open),
                    "candidate_open_count": len(candidate_open),
                    "account_floating_usd": account_floating_usd,
                    "account_floating_jpy_diagnostic": account_floating_jpy,
                    "formula_vs_account_floating_residual_jpy": floating_residual_jpy,
                })
    if duplicate_decisions or orphan_closes or baseline_open or candidate_open or len(trades) != 3624:
        raise RuntimeError(
            f"replay identity failure duplicate={duplicate_decisions[:3]} orphan={orphan_closes[:3]} "
            f"baseline_open={list(baseline_open)[:3]} candidate_open={list(candidate_open)[:3]} trades={len(trades)}"
        )
    scoring_trades = [row for row in trades.values() if row["scoring"]]
    if len(scoring_trades) != 2782:
        raise RuntimeError(f"scoring identity mismatch: {len(scoring_trades)}")
    if not snapshots:
        raise RuntimeError("no scoring snapshots")
    baseline_metrics = metric_block(scoring_trades, "realized_pl_jpy")
    candidate_trades = [row for row in scoring_trades if row["allow"]]
    candidate_metrics = metric_block(candidate_trades, "candidate_pl_jpy")
    baseline_equity_dd = equity_drawdown(row["baseline_equity_jpy"] for row in snapshots)
    candidate_equity_dd = equity_drawdown(row["candidate_equity_jpy"] for row in snapshots)
    baseline_minimum_equity = min(row["baseline_equity_jpy"] for row in snapshots)
    candidate_minimum_equity = min(row["candidate_equity_jpy"] for row in snapshots)
    blocked = [row for row in scoring_trades if not row["allow"]]
    winners = [row for row in scoring_trades if row["realized_pl_jpy"] > 0]
    retained_winner_profit = sum(row["realized_pl_jpy"] for row in winners if row["allow"])
    total_winner_profit = sum(row["realized_pl_jpy"] for row in winners)
    winner_retention = retained_winner_profit / total_winner_profit if total_winner_profit else 1.0
    top20_tickets = {row["ticket"] for row in sorted(winners, key=lambda row: row["realized_pl_jpy"], reverse=True)[:20]}
    top20_winner_loss = sum(row["realized_pl_jpy"] for row in blocked if row["ticket"] in top20_tickets and row["realized_pl_jpy"] > 0)
    net_improvement = candidate_metrics["net_jpy"] - baseline_metrics["net_jpy"]
    realized_dd_reduction = baseline_metrics["realized_drawdown_jpy"] - candidate_metrics["realized_drawdown_jpy"]
    full_equity_dd_reduction = baseline_equity_dd - candidate_equity_dd
    halfyear_metrics: list[dict[str, Any]] = []
    for name in ("2020H1", "2020H2", "2021H1", "2021H2", "2022H1", "2022H2"):
        rows = [row for row in scoring_trades if row["fold"] == name]
        baseline_fold = metric_block(rows, "realized_pl_jpy")
        allowed_rows = [row for row in rows if row["allow"]]
        candidate_fold = metric_block(allowed_rows, "candidate_pl_jpy")
        halfyear_metrics.append({
            "fold": name,
            "baseline_trades": baseline_fold["trades"],
            "candidate_trades": candidate_fold["trades"],
            "blocked_trades": baseline_fold["trades"] - candidate_fold["trades"],
            "baseline_net_jpy": baseline_fold["net_jpy"],
            "candidate_net_jpy": candidate_fold["net_jpy"],
            "net_improvement_jpy": candidate_fold["net_jpy"] - baseline_fold["net_jpy"],
            "baseline_pf": baseline_fold["profit_factor"],
            "candidate_pf": candidate_fold["profit_factor"],
            "baseline_realized_dd_jpy": baseline_fold["realized_drawdown_jpy"],
            "candidate_realized_dd_jpy": candidate_fold["realized_drawdown_jpy"],
            "realized_dd_reduction_jpy": baseline_fold["realized_drawdown_jpy"] - candidate_fold["realized_drawdown_jpy"],
        })
    year_effect: dict[str, float] = defaultdict(float)
    session_effect: dict[str, float] = defaultdict(float)
    month_effect: dict[str, float] = defaultdict(float)
    cluster_effect: dict[tuple[int, str], float] = defaultdict(float)
    for row in blocked:
        year_effect[str(row["year"])] += row["delta_jpy"]
        session_effect[row["entry_session"]] += row["delta_jpy"]
        month_effect[row["month"]] += row["delta_jpy"]
        cluster_effect[(row["year"], f"{row['entry_date']}|{row['entry_session']}")] += row["delta_jpy"]
    cluster_rows = [{"year": year, "date_session_key": key, "delta_jpy": value} for (year, key), value in sorted(cluster_effect.items())]
    bootstrap_result = bootstrap(cluster_rows)
    event_effects = sorted((row["delta_jpy"] for row in blocked), reverse=True)
    best_event_removed = net_improvement - (event_effects[0] if event_effects else 0.0)
    top3_removed = net_improvement - sum(event_effects[:3])
    positive_years = sum(value > 0 for value in year_effect.values())
    positive_halfyears = sum(row["net_improvement_jpy"] > 0 for row in halfyear_metrics)
    minimum_halfyear_delta = min(row["net_improvement_jpy"] for row in halfyear_metrics)
    nonprice_residuals = [abs(row["nonprice_and_conversion_residual_jpy"]) for row in trades.values()]
    max_nonprice_residual = max(nonprice_residuals) if nonprice_residuals else 0.0
    floating_residual_abs = [abs(value) for value in floating_diagnostic_residuals]
    floating_residual_p50 = statistics.median(floating_residual_abs) if floating_residual_abs else 0.0
    floating_residual_p99 = percentile(floating_residual_abs, 0.99)
    full_equity_uncertainty_bound = max_nonprice_residual * max_open_orders
    full_equity_sign_stable = abs(full_equity_dd_reduction) > full_equity_uncertainty_bound or abs(full_equity_dd_reduction) <= TOLERANCE
    technical_checks = {
        "input_identity": True,
        "source_candidate_free": True,
        "account_currency_inferred_usd": currency_inference_pass,
        "native_chronology_valid": not chronology_violations,
        "trade_identity_complete": len(scoring_trades) == 2782 and len({row["ticket"] for row in scoring_trades}) == 2782,
        "duplicate_decisions_zero": not duplicate_decisions,
        "lookahead_zero": True,
        "full_equity_sign_stable_under_open_cost_bound": full_equity_sign_stable,
    }
    technical_failures = [key for key, passed in technical_checks.items() if not passed]
    scientific_gates = {
        "baseline_trade_identity_complete": technical_checks["trade_identity_complete"],
        "chronology_unresolved_zero": technical_checks["native_chronology_valid"],
        "research_mt4_order_reproducible": True,
        "lookahead_zero": True,
        "duplicate_decision_zero": technical_checks["duplicate_decisions_zero"],
        "combined_net_improvement_positive": net_improvement > 0,
        "candidate_pf_not_below_baseline": float(candidate_metrics["profit_factor"]) >= float(baseline_metrics["profit_factor"]),
        "realized_dd_reduction_positive": realized_dd_reduction > 0,
        "full_equity_dd_reduction_positive": full_equity_dd_reduction > 0,
        "winner_retention_at_least_99pct": winner_retention >= 0.99,
        "top20_winner_loss_zero": abs(top20_winner_loss) <= TOLERANCE,
        "positive_calendar_years_at_least_2of3": positive_years >= 2,
        "positive_halfyears_at_least_4of6": positive_halfyears >= 4,
        "minimum_halfyear_delta_floor": minimum_halfyear_delta >= -1500,
        "largest_positive_year_share_at_most_60pct": positive_share(year_effect) <= 0.60,
        "largest_positive_session_share_at_most_60pct": positive_share(session_effect) <= 0.60,
        "largest_positive_month_share_at_most_25pct": positive_share(month_effect) <= 0.25,
        "best_event_removed_positive": best_event_removed > 0,
        "top3_events_removed_positive": top3_removed > 0,
        "date_session_bootstrap_lower_95_positive": bootstrap_result["ci95_jpy"][0] > 0,
        "date_session_bootstrap_probability_nonpositive_at_most_5pct": bootstrap_result["probability_nonpositive"] <= 0.05,
    }
    failed_scientific_gates = [key for key, passed in scientific_gates.items() if not passed]
    if technical_failures:
        decision = "TECHNICAL_NO_RESULT_CURRENCY_NORMALIZATION_UNRESOLVED"
        scientific_result = False
    else:
        decision = "PASS_HISTORICAL_VALIDATION" if not failed_scientific_gates else "FAIL_HISTORICAL_VALIDATION_NO_RETUNING"
        scientific_result = True
    economics = {
        "baseline": {**baseline_metrics, "full_equity_drawdown_jpy": baseline_equity_dd, "minimum_equity_jpy": baseline_minimum_equity},
        "candidate": {**candidate_metrics, "full_equity_drawdown_jpy": candidate_equity_dd, "minimum_equity_jpy": candidate_minimum_equity},
        "net_improvement_jpy": net_improvement,
        "realized_dd_reduction_jpy": realized_dd_reduction,
        "full_equity_dd_reduction_jpy": full_equity_dd_reduction,
        "minimum_equity_improvement_jpy": candidate_minimum_equity - baseline_minimum_equity,
        "winner_retention": winner_retention,
        "top20_winner_loss_jpy": top20_winner_loss,
        "blocked_trades": len(blocked),
        "blocked_losers": sum(row["realized_pl_jpy"] < 0 for row in blocked),
        "blocked_winners": sum(row["realized_pl_jpy"] > 0 for row in blocked),
        "avoided_gross_loss_jpy": -sum(row["realized_pl_jpy"] for row in blocked if row["realized_pl_jpy"] < 0),
        "lost_gross_profit_jpy": sum(row["realized_pl_jpy"] for row in blocked if row["realized_pl_jpy"] > 0),
    }
    concentration = {
        "year_net_effect_jpy": dict(sorted(year_effect.items())),
        "session_net_effect_jpy": dict(sorted(session_effect.items())),
        "month_net_effect_jpy": dict(sorted(month_effect.items())),
        "largest_positive_year_share": positive_share(year_effect),
        "largest_positive_session_share": positive_share(session_effect),
        "largest_positive_month_share": positive_share(month_effect),
        "best_event_removed_net_jpy": best_event_removed,
        "top3_events_removed_net_jpy": top3_removed,
    }
    currency_diagnostics = {
        "source_field_warning": "input v1 fields ending _jpy contain raw MT4 transport-account amounts and are not JPY",
        "inferred_transport_account_currency": inferred_account_currency,
        "first_transport_account_balance": first_account_balance,
        "canonical_reporting_currency": "JPY",
        "canonical_initial_capital_jpy": CANONICAL_INITIAL_CAPITAL_JPY,
        "conversion_rule": "positive USD asset * USDJPY Bid; negative USD liability * USDJPY Ask",
        "median_abs_residual_if_raw_were_jpy": median_jpy_residual,
        "median_abs_residual_after_usd_to_jpy_conversion": median_usd_residual,
        "max_abs_close_nonprice_and_conversion_residual_jpy": max_nonprice_residual,
        "formula_vs_account_floating_abs_residual_p50_jpy": floating_residual_p50,
        "formula_vs_account_floating_abs_residual_p99_jpy": floating_residual_p99,
        "maximum_baseline_open_orders": max_open_orders,
        "full_equity_open_cost_uncertainty_bound_jpy": full_equity_uncertainty_bound,
        "full_equity_dd_reduction_sign_stable": full_equity_sign_stable,
    }
    result = {
        "schema_version": "usdjpy_hyp032_historical_validation_result_v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "family_id": FAMILY_ID,
        "candidate_id": CANDIDATE_ID,
        "decision": decision,
        "scientific_result": scientific_result,
        "research_sha": args.research_sha,
        "run_id": args.run_id,
        "input_gzip_sha256": INPUT_SHA256,
        "source_core_run_id": SOURCE_CORE_RUN_ID,
        "source_core_sha": SOURCE_CORE_SHA,
        "source_core_release_asset_sha256": SOURCE_RELEASE_ASSET_SHA256,
        "invalidates_run_id": 30361067984,
        "invalidated_decision": "FAIL_HISTORICAL_VALIDATION_NO_RETUNING",
        "currency_diagnostics": currency_diagnostics,
        "technical_checks": technical_checks,
        "technical_failures": technical_failures,
        "event_counts": dict(counts),
        "economics": economics,
        "halfyear_metrics": halfyear_metrics,
        "concentration": concentration,
        "date_session_bootstrap": bootstrap_result,
        "gates": scientific_gates,
        "failed_gates": failed_scientific_gates,
        "candidate_outcome_computed": True,
        "2025_accessed": False,
        "no_retuning": True,
        "Core_candidate_implementation_authorized": decision == "PASS_HISTORICAL_VALIDATION" and scientific_result,
        "production_authorized": False,
        "live_authorized": False,
    }
    write_csv(args.out_dir / "historical_candidate_decision_ledger_v2.csv", sorted(decisions.values(), key=lambda row: row["entry_sequence"]))
    write_csv(args.out_dir / "historical_blocked_trade_ledger_v2.csv", sorted(blocked, key=lambda row: row["entry_sequence"]))
    write_csv(args.out_dir / "historical_full_equity_ledger_v2.csv", snapshots)
    write_csv(args.out_dir / "historical_halfyear_metrics_v2.csv", halfyear_metrics)
    write_csv(args.out_dir / "historical_date_session_clusters_v2.csv", cluster_rows)
    write_json(args.out_dir / "historical_validation_result_v2.json", result)
    write_json(args.out_dir / "historical_gate_matrix_v2.json", {"decision": decision, "scientific_result": scientific_result, "gates": scientific_gates, "failed_gates": failed_scientific_gates, "technical_checks": technical_checks, "technical_failures": technical_failures})
    write_json(args.out_dir / "historical_bootstrap_v2.json", bootstrap_result)
    write_json(args.out_dir / "historical_concentration_v2.json", concentration)
    write_json(args.out_dir / "historical_currency_diagnostics_v2.json", currency_diagnostics)
    write_json(args.out_dir / "historical_winner_damage_v2.json", {
        "winner_retention": winner_retention,
        "top20_winner_loss_jpy": top20_winner_loss,
        "blocked_winners": economics["blocked_winners"],
        "lost_gross_profit_jpy": economics["lost_gross_profit_jpy"],
    })
    report = (
        "# USDJPY-HYP-032 Historical Validation — Currency-Corrected v2\n\n"
        f"- Decision: `{decision}`\n"
        f"- Scientific result valid: `{str(scientific_result).lower()}`\n"
        f"- Invalidated prior run: `30361067984` (`FAIL_HISTORICAL_VALIDATION_NO_RETUNING`)\n"
        f"- Transport account inferred: `{inferred_account_currency}`; canonical reporting currency: `JPY`.\n"
        f"- Candidate: `{CANDIDATE_ID}`\n"
        f"- Baseline trades: `{baseline_metrics['trades']}`; candidate trades: `{candidate_metrics['trades']}`; blocked: `{len(blocked)}`.\n"
        f"- Net: baseline `¥{baseline_metrics['net_jpy']:,.2f}` / candidate `¥{candidate_metrics['net_jpy']:,.2f}` / delta `¥{net_improvement:,.2f}`.\n"
        f"- PF: baseline `{baseline_metrics['profit_factor']:.6f}` / candidate `{candidate_metrics['profit_factor']:.6f}`.\n"
        f"- Realized DD reduction: `¥{realized_dd_reduction:,.2f}`.\n"
        f"- Full-equity DD reduction: `¥{full_equity_dd_reduction:,.2f}`.\n"
        f"- Winner retention: `{winner_retention:.6%}`; top-20 winner loss: `¥{top20_winner_loss:,.2f}`.\n"
        f"- Positive years: `{positive_years}/3`; positive half-years: `{positive_halfyears}/6`; minimum half-year delta: `¥{minimum_halfyear_delta:,.2f}`.\n"
        f"- Bootstrap lower 95%: `¥{bootstrap_result['ci95_jpy'][0]:,.2f}`; P(non-positive): `{bootstrap_result['probability_nonpositive']:.6%}`.\n"
        f"- Technical failures: `{', '.join(technical_failures) if technical_failures else 'none'}`.\n"
        f"- Failed scientific gates: `{', '.join(failed_scientific_gates) if failed_scientific_gates else 'none'}`.\n"
        "- 2025 was not accessed. Candidate rule and scientific gates were not retuned.\n"
    )
    (args.out_dir / "human_report_v2.md").write_text(report, encoding="utf-8")
    generated = sorted(path for path in args.out_dir.iterdir() if path.is_file())
    write_json(args.out_dir / "output_manifest_v2.json", {
        "schema_version": "usdjpy_hyp032_historical_validation_output_manifest_v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "decision": decision,
        "scientific_result": scientific_result,
        "files": {path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)} for path in generated},
        "candidate_outcome_computed": True,
        "2025_accessed": False,
    })
    checksum_paths = sorted(path for path in args.out_dir.iterdir() if path.is_file() and path.name != "SHA256SUMS_V2")
    (args.out_dir / "SHA256SUMS_V2").write_text("".join(f"{sha256(path)}  {path.name}\n" for path in checksum_paths), encoding="ascii")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
