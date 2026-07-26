#!/usr/bin/env python3
"""Dependency-free factor analysis primitives for canonical USDJPY trade records.

The module provides descriptive and contrast statistics only. It does not infer
causality, select candidates, or mutate frozen research decisions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from hashlib import sha256
import json
import math
import random
from statistics import fmean, median
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "usdjpy_b02_f05_factor_analysis_v1"
DEFAULT_DIMENSIONS = ("period", "strategy", "side", "state")


@dataclass(frozen=True, slots=True)
class TradeObservation:
    trade_id: str
    period: str
    strategy: str
    side: str
    state: str
    outcome_pips: float
    factors: Mapping[str, float | int | bool | str | None]

    def validate(self) -> None:
        if not self.trade_id.strip():
            raise ValueError("trade_id is required")
        if not self.period.strip() or not self.strategy.strip() or not self.side.strip() or not self.state.strip():
            raise ValueError("period, strategy, side and state are required")
        if not math.isfinite(float(self.outcome_pips)):
            raise ValueError("outcome_pips must be finite")


@dataclass(frozen=True, slots=True)
class GroupSummary:
    dimensions: Mapping[str, str]
    trade_count: int
    winner_count: int
    loser_count: int
    win_rate: float
    total_pips: float
    mean_pips: float
    median_pips: float
    minimum_pips: float
    maximum_pips: float


@dataclass(frozen=True, slots=True)
class NumericFactorContrast:
    factor: str
    threshold: float
    low_count: int
    high_count: int
    low_mean_outcome_pips: float
    high_mean_outcome_pips: float
    mean_delta_pips: float
    standardized_mean_difference: float | None
    permutation_p_value: float | None
    direction_consistent_folds: int
    eligible_fold_count: int


@dataclass(frozen=True, slots=True)
class CategoricalFactorLevel:
    factor: str
    level: str
    trade_count: int
    mean_outcome_pips: float
    win_rate: float
    total_pips: float


def _dimension_value(row: TradeObservation, name: str) -> str:
    if name not in DEFAULT_DIMENSIONS:
        raise ValueError(f"unsupported dimension: {name}")
    return str(getattr(row, name))


def aggregate_observations(
    observations: Iterable[TradeObservation],
    dimensions: Sequence[str] = DEFAULT_DIMENSIONS,
) -> list[GroupSummary]:
    rows = list(observations)
    if not dimensions:
        raise ValueError("at least one dimension is required")
    buckets: dict[tuple[str, ...], list[TradeObservation]] = {}
    for row in rows:
        row.validate()
        key = tuple(_dimension_value(row, dimension) for dimension in dimensions)
        buckets.setdefault(key, []).append(row)
    output: list[GroupSummary] = []
    for key in sorted(buckets):
        bucket = buckets[key]
        outcomes = [float(row.outcome_pips) for row in bucket]
        winners = sum(value > 0 for value in outcomes)
        losers = sum(value < 0 for value in outcomes)
        output.append(GroupSummary(
            dimensions=dict(zip(dimensions, key)),
            trade_count=len(bucket),
            winner_count=winners,
            loser_count=losers,
            win_rate=winners / len(bucket),
            total_pips=sum(outcomes),
            mean_pips=fmean(outcomes),
            median_pips=median(outcomes),
            minimum_pips=min(outcomes),
            maximum_pips=max(outcomes),
        ))
    return output


def _numeric_values(observations: Iterable[TradeObservation], factor: str) -> list[tuple[TradeObservation, float]]:
    result: list[tuple[TradeObservation, float]] = []
    for row in observations:
        row.validate()
        raw = row.factors.get(factor)
        if raw is None or isinstance(raw, bool) or isinstance(raw, str):
            continue
        value = float(raw)
        if math.isfinite(value):
            result.append((row, value))
    return result


def _sample_variance(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    mean_value = fmean(values)
    return sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)


def _standardized_mean_difference(low: Sequence[float], high: Sequence[float]) -> float | None:
    low_var = _sample_variance(low)
    high_var = _sample_variance(high)
    if low_var is None or high_var is None:
        return None
    denominator_df = len(low) + len(high) - 2
    if denominator_df <= 0:
        return None
    pooled = ((len(low) - 1) * low_var + (len(high) - 1) * high_var) / denominator_df
    if pooled <= 0:
        return 0.0 if fmean(high) == fmean(low) else None
    return (fmean(high) - fmean(low)) / math.sqrt(pooled)


def _permutation_p_value(
    low: Sequence[float], high: Sequence[float], *, iterations: int, seed: int
) -> float | None:
    if not low or not high or iterations <= 0:
        return None
    observed = abs(fmean(high) - fmean(low))
    pooled = list(low) + list(high)
    rng = random.Random(seed)
    exceedances = 0
    for _ in range(iterations):
        rng.shuffle(pooled)
        candidate_low = pooled[:len(low)]
        candidate_high = pooled[len(low):]
        if abs(fmean(candidate_high) - fmean(candidate_low)) >= observed - 1e-12:
            exceedances += 1
    return (exceedances + 1) / (iterations + 1)


def analyze_numeric_factor(
    observations: Iterable[TradeObservation],
    factor: str,
    *,
    threshold: float | None = None,
    permutation_iterations: int = 999,
    seed: int = 0,
) -> NumericFactorContrast:
    pairs = _numeric_values(observations, factor)
    if len(pairs) < 2:
        raise ValueError(f"factor {factor!r} has fewer than two numeric observations")
    values = [value for _, value in pairs]
    split = float(median(values) if threshold is None else threshold)
    low_rows = [row for row, value in pairs if value <= split]
    high_rows = [row for row, value in pairs if value > split]
    if not low_rows or not high_rows:
        raise ValueError(f"factor {factor!r} does not produce two non-empty groups at threshold {split}")
    low = [float(row.outcome_pips) for row in low_rows]
    high = [float(row.outcome_pips) for row in high_rows]
    pooled_delta = fmean(high) - fmean(low)
    fold_directions: list[bool] = []
    periods = sorted({row.period for row, _ in pairs})
    for period in periods:
        period_low = [float(row.outcome_pips) for row in low_rows if row.period == period]
        period_high = [float(row.outcome_pips) for row in high_rows if row.period == period]
        if period_low and period_high:
            delta = fmean(period_high) - fmean(period_low)
            fold_directions.append(delta == 0 or (delta > 0) == (pooled_delta > 0))
    stable_seed = int(sha256(f"{factor}|{split}|{seed}".encode()).hexdigest()[:16], 16)
    return NumericFactorContrast(
        factor=factor,
        threshold=split,
        low_count=len(low),
        high_count=len(high),
        low_mean_outcome_pips=fmean(low),
        high_mean_outcome_pips=fmean(high),
        mean_delta_pips=pooled_delta,
        standardized_mean_difference=_standardized_mean_difference(low, high),
        permutation_p_value=_permutation_p_value(low, high, iterations=permutation_iterations, seed=stable_seed),
        direction_consistent_folds=sum(fold_directions),
        eligible_fold_count=len(fold_directions),
    )


def analyze_categorical_factor(
    observations: Iterable[TradeObservation], factor: str
) -> list[CategoricalFactorLevel]:
    buckets: dict[str, list[float]] = {}
    for row in observations:
        row.validate()
        raw = row.factors.get(factor)
        if raw is None:
            continue
        level = str(raw)
        buckets.setdefault(level, []).append(float(row.outcome_pips))
    if not buckets:
        raise ValueError(f"factor {factor!r} has no categorical observations")
    result = []
    for level in sorted(buckets):
        outcomes = buckets[level]
        result.append(CategoricalFactorLevel(
            factor=factor,
            level=level,
            trade_count=len(outcomes),
            mean_outcome_pips=fmean(outcomes),
            win_rate=sum(value > 0 for value in outcomes) / len(outcomes),
            total_pips=sum(outcomes),
        ))
    return result


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f"unsupported analysis payload type: {type(value).__name__}")


def deterministic_analysis_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_json_default).encode("utf-8")
    return sha256(encoded).hexdigest()
