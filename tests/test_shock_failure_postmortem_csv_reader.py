from __future__ import annotations

import gzip
import importlib.util
import os
from pathlib import Path

import pandas as pd
import pandas.testing as pdt
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER_PATH = Path(
    os.environ.get(
        "SHOCK_POSTMORTEM_ANALYZER",
        REPO_ROOT / "tools" / "analyze_usdjpy_shock_failure_2025_postmortem_v3.py",
    )
)


def _load_analyzer():
    spec = importlib.util.spec_from_file_location("shock_postmortem_analyzer", ANALYZER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def analyzer():
    return _load_analyzer()


def test_plain_and_gzip_csv_are_identical(tmp_path: Path, analyzer) -> None:
    expected = pd.DataFrame(
        {
            "candidate_id": ["B_EXECUTABLE_T0_8BAR", "CONTROL"],
            "admitted": [True, False],
            "pnl_jpy": [12.5, -3.0],
            "note": ["UTF-8", "日本語"],
        }
    )
    plain = tmp_path / "synthetic.csv"
    compressed = tmp_path / "synthetic.csv.gz"
    expected.to_csv(plain, index=False, encoding="utf-8-sig")
    compressed.write_bytes(gzip.compress(plain.read_bytes(), mtime=0))

    plain_df = analyzer.read_csv_robust(plain)
    gzip_df = analyzer.read_csv_robust(compressed)
    pdt.assert_frame_equal(plain_df, gzip_df)
    pdt.assert_frame_equal(plain_df, expected)


def test_gzip_magic_is_honoured_without_gz_suffix(tmp_path: Path, analyzer) -> None:
    path = tmp_path / "magic.csv"
    path.write_bytes(gzip.compress(b"a,b\n1,2\n", mtime=0))
    actual = analyzer.read_csv_robust(path)
    pdt.assert_frame_equal(actual, pd.DataFrame({"a": [1], "b": [2]}))


def test_gz_suffix_without_gzip_magic_is_rejected(tmp_path: Path, analyzer) -> None:
    path = tmp_path / "not-compressed.csv.gz"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="gzip suffix without gzip magic"):
        analyzer.read_csv_robust(path)


def test_utf8_and_cp932_fallbacks(tmp_path: Path, analyzer) -> None:
    utf8 = tmp_path / "utf8.csv"
    cp932 = tmp_path / "cp932.csv"
    text = "key,value\n候補,失敗\n"
    utf8.write_bytes(text.encode("utf-8"))
    cp932.write_bytes(text.encode("cp932"))
    expected = [{"key": "候補", "value": "失敗"}]
    assert analyzer.read_csv_robust(utf8).to_dict("records") == expected
    assert analyzer.read_csv_robust(cp932).to_dict("records") == expected


def test_phase2_candidate_ledger_reads_114_events(analyzer) -> None:
    phase2_dir = os.environ.get("PHASE2_DIR")
    if not phase2_dir:
        pytest.skip("PHASE2_DIR is only set in the binding workflow")
    matches = list(Path(phase2_dir).rglob("candidate_trade_ledger.csv.gz"))
    assert len(matches) == 1
    ledger = analyzer.read_csv_robust(matches[0])
    candidate = ledger[
        (ledger["candidate_id"] == "B_EXECUTABLE_T0_8BAR")
        & ledger["admitted"].fillna(False)
    ]
    assert len(candidate) == 114
    assert set(candidate["fold"]) == {"2023H1", "2023H2", "2024H1", "2024H2"}
