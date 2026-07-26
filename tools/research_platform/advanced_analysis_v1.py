#!/usr/bin/env python3
"""Advanced dependency-free diagnostics for USDJPY research observations."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
import random
from statistics import fmean
from typing import Iterable, Sequence

from tools.research_platform.factor_analysis_v1 import TradeObservation

SCHEMA_VERSION = "usdjpy_b02_f05_advanced_analysis_v1"


@dataclass(frozen=True, slots=True)
class BootstrapInterval:
    estimate: float
    lower: float
    upper: float
    confidence: float
    iterations: int


@dataclass(frozen=True, slots=True)
class MatchedCohortResult:
    treated_count: int
    control_count: int
    pair_count: int
    mean_treated_pips: float
    mean_control_pips: float
    mean_pair_delta_pips: float
    bootstrap: BootstrapInterval


@dataclass(frozen=True, slots=True)
class InteractionCell:
    factor_a_high: bool
    factor_b_high: bool
    trade_count: int
    mean_outcome_pips: float
    total_pips: float


@dataclass(frozen=True, slots=True)
class InteractionResult:
    factor_a: str
    factor_b: str
    threshold_a: float
    threshold_b: float
    cells: tuple[InteractionCell, ...]
    difference_in_differences_pips: float | None


def bootstrap_mean(values: Sequence[float], *, iterations: int = 2000, confidence: float = 0.95, seed: int = 0) -> BootstrapInterval:
    if not values:
        raise ValueError("bootstrap requires at least one value")
    if iterations < 100:
        raise ValueError("iterations must be at least 100")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    rng = random.Random(seed)
    sample = [float(value) for value in values]
    estimates = []
    for _ in range(iterations):
        estimates.append(fmean(rng.choice(sample) for _ in sample))
    estimates.sort()
    alpha = (1.0 - confidence) / 2.0
    lo = estimates[max(0, min(iterations - 1, int(alpha * iterations)))]
    hi = estimates[max(0, min(iterations - 1, int((1.0 - alpha) * iterations) - 1))]
    return BootstrapInterval(fmean(sample), lo, hi, confidence, iterations)


def matched_cohort(
    observations: Iterable[TradeObservation],
    *,
    treatment_factor: str,
    match_factors: Sequence[str] = ("period", "strategy", "side", "state"),
    seed: int = 0,
) -> MatchedCohortResult:
    treated: list[TradeObservation] = []
    controls: list[TradeObservation] = []
    for row in observations:
        row.validate()
        flag = row.factors.get(treatment_factor)
        if flag is True:
            treated.append(row)
        elif flag is False:
            controls.append(row)
    if not treated or not controls:
        raise ValueError("matched cohort requires treated and control observations")

    def key(row: TradeObservation) -> tuple[str, ...]:
        values = []
        for name in match_factors:
            if hasattr(row, name):
                values.append(str(getattr(row, name)))
            else:
                values.append(str(row.factors.get(name)))
        return tuple(values)

    control_buckets: dict[tuple[str, ...], list[TradeObservation]] = {}
    for row in controls:
        control_buckets.setdefault(key(row), []).append(row)
    for bucket in control_buckets.values():
        bucket.sort(key=lambda row: row.trade_id)

    deltas: list[float] = []
    matched_treated: list[float] = []
    matched_controls: list[float] = []
    for row in sorted(treated, key=lambda item: item.trade_id):
        bucket = control_buckets.get(key(row))
        if not bucket:
            continue
        control = min(bucket, key=lambda item: (abs(item.outcome_pips - row.outcome_pips), item.trade_id))
        bucket.remove(control)
        matched_treated.append(float(row.outcome_pips))
        matched_controls.append(float(control.outcome_pips))
        deltas.append(float(row.outcome_pips) - float(control.outcome_pips))
    if not deltas:
        raise ValueError("no matched pairs found")
    stable_seed = int(sha256(f"{treatment_factor}|{seed}".encode()).hexdigest()[:16], 16)
    return MatchedCohortResult(
        treated_count=len(treated),
        control_count=len(controls),
        pair_count=len(deltas),
        mean_treated_pips=fmean(matched_treated),
        mean_control_pips=fmean(matched_controls),
        mean_pair_delta_pips=fmean(deltas),
        bootstrap=bootstrap_mean(deltas, seed=stable_seed),
    )


def interaction_analysis(
    observations: Iterable[TradeObservation],
    factor_a: str,
    factor_b: str,
    *,
    threshold_a: float,
    threshold_b: float,
) -> InteractionResult:
    buckets: dict[tuple[bool, bool], list[float]] = {(a, b): [] for a in (False, True) for b in (False, True)}
    for row in observations:
        row.validate()
        raw_a = row.factors.get(factor_a)
        raw_b = row.factors.get(factor_b)
        if isinstance(raw_a, bool) or isinstance(raw_b, bool) or raw_a is None or raw_b is None:
            continue
        try:
            value_a = float(raw_a)
            value_b = float(raw_b)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value_a) or not math.isfinite(value_b):
            continue
        buckets[(value_a > threshold_a, value_b > threshold_b)].append(float(row.outcome_pips))
    cells = []
    for key in sorted(buckets):
        values = buckets[key]
        cells.append(InteractionCell(key[0], key[1], len(values), fmean(values) if values else math.nan, sum(values)))
    means = {key: (fmean(values) if values else None) for key, values in buckets.items()}
    did = None
    if all(value is not None for value in means.values()):
        did = (means[(True, True)] - means[(True, False)]) - (means[(False, True)] - means[(False, False)])
    return InteractionResult(factor_a, factor_b, float(threshold_a), float(threshold_b), tuple(cells), did)
