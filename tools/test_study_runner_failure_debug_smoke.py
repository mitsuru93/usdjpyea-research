from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import sys

import yaml

sys.path.append(str(Path(__file__).resolve().parents[1]))

from research.orchestration.study_runner import run_study


def _base_study_config(output_root: Path, *, analyze_after_run: bool = False) -> dict:
    return {
        "study_name": "debug-smoke",
        "output_root": str(output_root),
        "shared_defaults": {
            "input_csv": "research/data_sample/usdjpy_m1_sample.csv",
            "input_timezone_mode": "utc",
            "max_holding_bars": 5,
            "symbol": "USDJPY",
            "timeframe": "M1",
            "analyze_after_run": analyze_after_run,
        },
        "runs": [{"label": "failing_run"}],
    }


def test_run_failure_logs_are_printed_and_saved(monkeypatch, capsys) -> None:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        output_root = tmp_path / "study_output"
        cfg_path = tmp_path / "study.yaml"
        cfg_path.write_text(yaml.safe_dump(_base_study_config(output_root)), encoding="utf-8")

        def _fake_run_cli(cli_path: Path, config_path: Path, repo_root: Path) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=[str(cli_path), str(config_path)],
                returncode=1,
                stdout="run stdout line",
                stderr="Traceback: run failed",
            )

        monkeypatch.setattr("research.orchestration.study_runner._run_cli", _fake_run_cli)

        metadata = run_study(cfg_path)
        run = metadata["runs"][0]
        run_dir = Path(run["run_dir"])

        assert run["status"] == "run_failed"
        assert (run_dir / "run_experiment.stdout.log").read_text(encoding="utf-8") == "run stdout line"
        assert (run_dir / "run_experiment.stderr.log").read_text(encoding="utf-8") == "Traceback: run failed"
        assert (run_dir / "analyze_run.stdout.log").exists()
        assert (run_dir / "analyze_run.stderr.log").exists()

        printed = capsys.readouterr().out
        assert "[run_experiment][stdout]" in printed
        assert "run stdout line" in printed
        assert "[run_experiment][stderr]" in printed
        assert "Traceback: run failed" in printed


def test_analysis_failure_logs_are_printed_and_saved(monkeypatch, capsys) -> None:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        output_root = tmp_path / "study_output"
        cfg_path = tmp_path / "study.yaml"
        cfg_path.write_text(yaml.safe_dump(_base_study_config(output_root, analyze_after_run=True)), encoding="utf-8")

        def _fake_run_cli(cli_path: Path, config_path: Path, repo_root: Path) -> subprocess.CompletedProcess[str]:
            tool_name = Path(cli_path).name
            if tool_name == "run_experiment.py":
                return subprocess.CompletedProcess(
                    args=[str(cli_path), str(config_path)],
                    returncode=0,
                    stdout="run ok",
                    stderr="",
                )
            if tool_name == "analyze_run.py":
                return subprocess.CompletedProcess(
                    args=[str(cli_path), str(config_path)],
                    returncode=1,
                    stdout="analyze stdout",
                    stderr="Traceback: analyze failed",
                )
            raise AssertionError(f"Unexpected CLI path: {cli_path}")

        monkeypatch.setattr("research.orchestration.study_runner._run_cli", _fake_run_cli)

        metadata = run_study(cfg_path)
        run = metadata["runs"][0]
        run_dir = Path(run["run_dir"])

        assert run["status"] == "analysis_failed"
        assert (run_dir / "run_experiment.stdout.log").read_text(encoding="utf-8") == "run ok"
        assert (run_dir / "run_experiment.stderr.log").read_text(encoding="utf-8") == ""
        assert (run_dir / "analyze_run.stdout.log").read_text(encoding="utf-8") == "analyze stdout"
        assert (run_dir / "analyze_run.stderr.log").read_text(encoding="utf-8") == "Traceback: analyze failed"

        printed = capsys.readouterr().out
        assert "[analyze_run][stdout]" in printed
        assert "analyze stdout" in printed
        assert "[analyze_run][stderr]" in printed
        assert "Traceback: analyze failed" in printed
