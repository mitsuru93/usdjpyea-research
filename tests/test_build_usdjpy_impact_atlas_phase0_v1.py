from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "build_usdjpy_impact_atlas_phase0_v1.py"
spec = importlib.util.spec_from_file_location("impact_phase0", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_identify_reports_existing_and_missing(tmp_path: Path) -> None:
    existing = tmp_path / "a.txt"
    existing.write_text("atlas\n", encoding="utf-8")
    rows = module.identify(tmp_path, ["a.txt", "missing.txt"])
    assert rows[0].exists is True
    assert rows[0].size_bytes == 6
    assert len(rows[0].sha256) == 64
    assert rows[1].exists is False
    assert rows[1].sha256 is None


def test_constants_lock_2025_from_selection() -> None:
    assert module.HISTORICAL_FOLDS == ("2023H1", "2023H2", "2024H1", "2024H2")
    assert module.EXCLUDED_SELECTION_PERIODS == ("2025H1", "2025H2")
