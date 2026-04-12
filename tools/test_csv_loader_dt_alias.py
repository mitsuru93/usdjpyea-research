from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from research.io.csv_loader import load_ohlc_csv


def test_load_ohlc_csv_accepts_dt_datetime_alias() -> None:
    with TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "dt_schema.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "DT,Open,High,Low,Close,TickVol,Spread,RealVol",
                    "2025-01-01 00:01:00,100.0,101.0,99.0,100.5,12,10,14",
                    "2025-01-01 00:00:00,99.0,100.0,98.5,99.5,11,9,13",
                ]
            ),
            encoding="utf-8",
        )

        loaded = load_ohlc_csv(csv_path)

        assert list(loaded.columns) == ["datetime", "open", "high", "low", "close"]
        assert loaded["datetime"].iloc[0].isoformat() == "2025-01-01T00:00:00"
        assert loaded["datetime"].iloc[1].isoformat() == "2025-01-01T00:01:00"
        assert loaded[["open", "high", "low", "close"]].iloc[0].to_dict() == {
            "open": 99.0,
            "high": 100.0,
            "low": 98.5,
            "close": 99.5,
        }
