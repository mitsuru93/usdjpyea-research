#!/usr/bin/env python3
"""Machine-readable registry for B02/F05 experiments and evidence lineage."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "usdjpy_b02_f05_experiment_registry_v1"
ALLOWED_STATUS = {"planned", "preregistered", "running", "completed", "rejected", "promoted", "closed"}
ALLOWED_DEPENDENCY = {"A", "B", "C", "D"}


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    experiment_id: str
    hypothesis_id: str
    title: str
    status: str
    strategies: tuple[str, ...]
    periods: tuple[str, ...]
    analysis_family: str
    contract_path: str
    result_paths: tuple[str, ...]
    code_paths: tuple[str, ...]
    dataset_sources: tuple[str, ...]
    dependency_tier: str
    mechanism: str
    primary_endpoint: str
    falsification_rule: str
    decision: str | None = None
    supersedes: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RegistryEntry":
        entry = cls(
            experiment_id=str(value["experiment_id"]),
            hypothesis_id=str(value["hypothesis_id"]),
            title=str(value["title"]),
            status=str(value["status"]),
            strategies=tuple(value["strategies"]),
            periods=tuple(value["periods"]),
            analysis_family=str(value["analysis_family"]),
            contract_path=str(value["contract_path"]),
            result_paths=tuple(value.get("result_paths", [])),
            code_paths=tuple(value.get("code_paths", [])),
            dataset_sources=tuple(value.get("dataset_sources", [])),
            dependency_tier=str(value["dependency_tier"]),
            mechanism=str(value["mechanism"]),
            primary_endpoint=str(value["primary_endpoint"]),
            falsification_rule=str(value["falsification_rule"]),
            decision=value.get("decision"),
            supersedes=value.get("supersedes"),
        )
        entry.validate()
        return entry

    def validate(self) -> None:
        if not self.experiment_id or not self.hypothesis_id or not self.title:
            raise ValueError("experiment_id, hypothesis_id and title are required")
        if self.status not in ALLOWED_STATUS:
            raise ValueError(f"unsupported status: {self.status}")
        if self.dependency_tier not in ALLOWED_DEPENDENCY:
            raise ValueError(f"unsupported dependency tier: {self.dependency_tier}")
        if not self.strategies or not self.periods:
            raise ValueError("strategies and periods are required")
        if not self.contract_path or not self.mechanism or not self.primary_endpoint or not self.falsification_rule:
            raise ValueError("contract, mechanism, endpoint and falsification are required")


def load_registry(path: Path) -> list[RegistryEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported registry schema")
    entries = [RegistryEntry.from_mapping(item) for item in payload.get("experiments", [])]
    ids = [item.experiment_id for item in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate experiment_id")
    return entries


def deterministic_registry_sha256(entries: Iterable[RegistryEntry]) -> str:
    document = [entry.__dict__ if hasattr(entry, "__dict__") else {
        "experiment_id": entry.experiment_id,
        "hypothesis_id": entry.hypothesis_id,
        "title": entry.title,
        "status": entry.status,
        "strategies": list(entry.strategies),
        "periods": list(entry.periods),
        "analysis_family": entry.analysis_family,
        "contract_path": entry.contract_path,
        "result_paths": list(entry.result_paths),
        "code_paths": list(entry.code_paths),
        "dataset_sources": list(entry.dataset_sources),
        "dependency_tier": entry.dependency_tier,
        "mechanism": entry.mechanism,
        "primary_endpoint": entry.primary_endpoint,
        "falsification_rule": entry.falsification_rule,
        "decision": entry.decision,
        "supersedes": entry.supersedes,
    } for entry in entries]
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def validate_registry_paths(root: Path, entries: Iterable[RegistryEntry]) -> list[str]:
    missing: list[str] = []
    for entry in entries:
        for relative in (entry.contract_path, *entry.result_paths, *entry.code_paths):
            if relative and not (root / relative).exists():
                missing.append(f"{entry.experiment_id}:{relative}")
    return missing
