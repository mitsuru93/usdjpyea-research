#!/usr/bin/env python3
"""Adapters for existing B02/F05 result summaries.

These adapters preserve existing outputs and expose a stable normalized shape for
cross-experiment comparison. They do not reinterpret or recompute scientific results.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class CandidateResult:
    candidate_id: str
    stage: str
    fold_pass_count: int
    all_four_folds_pass: bool
    pooled_default_delta_pips: float
    pooled_severe_delta_pips: float
    minimum_fold_default_delta_pips: float
    minimum_fold_severe_delta_pips: float
    minimum_top10_retention: float
    minimum_top5_retention: float
    passing_folds: tuple[str, ...]
    pooled_rank_within_stage: int

    def validate(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id is required")
        if not self.stage.strip():
            raise ValueError("stage is required")
        if self.fold_pass_count < 0 or self.fold_pass_count > 4:
            raise ValueError("fold_pass_count must be between zero and four")
        if self.all_four_folds_pass != (self.fold_pass_count == 4):
            raise ValueError("all_four_folds_pass disagrees with fold_pass_count")
        if len(self.passing_folds) != self.fold_pass_count:
            raise ValueError("passing_folds disagrees with fold_pass_count")
        if not 0.0 <= self.minimum_top10_retention <= 1.0:
            raise ValueError("minimum_top10_retention must be in [0,1]")
        if not 0.0 <= self.minimum_top5_retention <= 1.0:
            raise ValueError("minimum_top5_retention must be in [0,1]")
        if self.pooled_rank_within_stage < 1:
            raise ValueError("pooled_rank_within_stage must be positive")

    def as_record(self) -> dict[str, object]:
        record = asdict(self)
        record["passing_folds"] = list(self.passing_folds)
        return record


def _as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"invalid boolean: {value}")


def load_lifecycle_candidate_summary(path: str | Path) -> list[CandidateResult]:
    records: list[CandidateResult] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            passing = tuple(part for part in row["passing_folds"].split("|") if part)
            record = CandidateResult(
                candidate_id=row["candidate_id"],
                stage=row["stage"],
                fold_pass_count=int(row["fold_pass_count"]),
                all_four_folds_pass=_as_bool(row["all_four_folds_pass"]),
                pooled_default_delta_pips=float(row["pooled_default_delta_pips"]),
                pooled_severe_delta_pips=float(row["pooled_severe_delta_pips"]),
                minimum_fold_default_delta_pips=float(row["minimum_fold_default_delta_pips"]),
                minimum_fold_severe_delta_pips=float(row["minimum_fold_severe_delta_pips"]),
                minimum_top10_retention=float(row["minimum_top10_retention"]),
                minimum_top5_retention=float(row["minimum_top5_retention"]),
                passing_folds=passing,
                pooled_rank_within_stage=int(row["pooled_rank_within_stage"]),
            )
            record.validate()
            records.append(record)
    if not records:
        raise ValueError("candidate summary is empty")
    ids = [record.candidate_id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate summary contains duplicate candidate_id")
    return records


def rank_candidates(records: Iterable[CandidateResult]) -> list[CandidateResult]:
    """Deterministic diagnostic ranking; never an adoption decision."""
    validated = list(records)
    for record in validated:
        record.validate()
    return sorted(
        validated,
        key=lambda r: (
            -r.fold_pass_count,
            -r.pooled_default_delta_pips,
            -r.pooled_severe_delta_pips,
            -r.minimum_top10_retention,
            r.candidate_id,
        ),
    )
