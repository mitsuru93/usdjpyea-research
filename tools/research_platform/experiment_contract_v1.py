#!/usr/bin/env python3
"""Machine-readable experiment contract and lineage checks."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "usdjpy_b02_f05_experiment_contract_v1"


@dataclass(frozen=True, slots=True)
class ExperimentContract:
    experiment_id: str
    hypothesis_id: str
    strategies: tuple[str, ...]
    periods: tuple[str, ...]
    dataset_sha256: str
    code_sha: str
    event_schema_version: str
    analysis_family: str
    parameters: dict[str, Any]
    expected_mechanism: str
    primary_endpoint: str
    falsification_rule: str

    @classmethod
    def from_json(cls, path: str | Path) -> "ExperimentContract":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if raw.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported experiment schema")
        contract = cls(
            experiment_id=raw["experiment_id"],
            hypothesis_id=raw["hypothesis_id"],
            strategies=tuple(raw["strategies"]),
            periods=tuple(raw["periods"]),
            dataset_sha256=raw["dataset_sha256"],
            code_sha=raw["code_sha"],
            event_schema_version=raw["event_schema_version"],
            analysis_family=raw["analysis_family"],
            parameters=dict(raw.get("parameters", {})),
            expected_mechanism=raw["expected_mechanism"],
            primary_endpoint=raw["primary_endpoint"],
            falsification_rule=raw["falsification_rule"],
        )
        contract.validate()
        return contract

    def validate(self) -> None:
        required_text = {
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "code_sha": self.code_sha,
            "event_schema_version": self.event_schema_version,
            "analysis_family": self.analysis_family,
            "expected_mechanism": self.expected_mechanism,
            "primary_endpoint": self.primary_endpoint,
            "falsification_rule": self.falsification_rule,
        }
        for name, value in required_text.items():
            if not value.strip():
                raise ValueError(f"{name} is required")
        if not self.strategies or not set(self.strategies) <= {"B02", "F05"}:
            raise ValueError("strategies must contain only B02/F05")
        if not self.periods or not set(self.periods) <= {"2023H1", "2023H2", "2024H1", "2024H2"}:
            raise ValueError("periods are invalid")
        digest = self.dataset_sha256.removeprefix("sha256:")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
            raise ValueError("dataset_sha256 must be a SHA-256 digest")

    def contract_sha256(self) -> str:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "strategies": list(self.strategies),
            "periods": list(self.periods),
            "dataset_sha256": self.dataset_sha256,
            "code_sha": self.code_sha,
            "event_schema_version": self.event_schema_version,
            "analysis_family": self.analysis_family,
            "parameters": self.parameters,
            "expected_mechanism": self.expected_mechanism,
            "primary_endpoint": self.primary_endpoint,
            "falsification_rule": self.falsification_rule,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(canonical.encode("utf-8")).hexdigest()
