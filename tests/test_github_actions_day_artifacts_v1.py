from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "download_github_actions_day_artifacts_v1.py"
    spec = importlib.util.spec_from_file_location("download_github_actions_day_artifacts_v1", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_month_expected_dates_and_name() -> None:
    module = load_module()
    dates = module.expected_dates("source-month", 2, None)
    assert len(dates) == 29
    assert dates[0] == "2024-02-01"
    assert dates[-1] == "2024-02-29"
    assert module.expected_name("source-month", dates[0], 29689427642, 1) == (
        "usdjpy-raw-ticks-2024-02-01-29689427642-1"
    )


def test_repair_month_filters_locked_dates(tmp_path: Path) -> None:
    module = load_module()
    lock = tmp_path / "lock.json"
    lock.write_text(
        json.dumps({"repair_scope": {"affected_dates": ["2024-01-08", "2024-02-04", "2024-02-09"]}}),
        encoding="utf-8",
    )
    assert module.expected_dates("repair-month", 2, lock) == ["2024-02-04", "2024-02-09"]
    assert module.expected_name("repair-month", "2024-02-04", 29707697472, 1) == (
        "usdjpy-raw-ticks-repair-2024-02-04-29707697472-1"
    )


def test_signed_storage_request_never_contains_github_authorization() -> None:
    module = load_module()
    request = module.storage_request("https://example.blob.core.windows.net/container/file.zip?sig=abc")
    assert request.full_url.startswith("https://")
    assert "Authorization" not in request.headers
    assert "X-Github-Api-Version" not in request.headers


def test_signed_storage_request_rejects_non_https() -> None:
    module = load_module()
    with pytest.raises(RuntimeError, match="invalid signed artifact URL"):
        module.storage_request("http://example.com/file.zip")
