from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

import yaml

sys.path.append(str(Path(__file__).resolve().parents[1]))

from research.orchestration.study_runner import run_study

REPO_ROOT = Path(__file__).resolve().parents[1]


def _all_string_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_all_string_values(item))
        return result
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_all_string_values(item))
        return result
    return []


def test_expand_batch_writes_repo_relative_paths_only() -> None:
    with TemporaryDirectory(dir=REPO_ROOT) as tmp:
        tmp_path = Path(tmp)
        spec_path = tmp_path / "batch_spec.yaml"
        runtime_dir = tmp_path / "runtime"
        spec_path.write_text(
            yaml.safe_dump(
                {
                    "batch_id": "cross_runner_path_smoke",
                    "dataset_registry": "configs/datasets.yaml",
                    "dataset_id": "usd-jpy-m1-sample",
                    "output_root": "research/reports/batches/cross_runner_path_smoke",
                    "shard_size": 1,
                    "blackout_windows_jst": [{"start_hhmmss": "000000", "end_hhmmss": "000500"}],
                    "spread_mode": "ignore",
                    "band_model_sweep": {
                        "variants": [
                            {"band_model_family": "percent", "band_model": "percent", "band_percent": 0.001, "band_token": "PCT001"}
                        ]
                    },
                    "timing_modes": ["baseline_touch"],
                    "compare_sections": ["overall"],
                    "ranking_profile": {},
                    "review_sink": {},
                    "notes": "cross-runner regression",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "expand_batch.py"),
                "--batch-spec",
                str(spec_path),
                "--runtime-dir",
                str(runtime_dir),
            ],
            check=True,
            cwd=REPO_ROOT,
        )

        manifest_path = runtime_dir / "cross_runner_path_smoke" / "batch_manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        shard_cfg_path = runtime_dir / "cross_runner_path_smoke" / "shards" / "shard_000" / "study_config.yaml"
        shard_cfg = yaml.safe_load(shard_cfg_path.read_text(encoding="utf-8"))

        assert not Path(str(manifest["output_root"])).is_absolute()
        assert not Path(str(shard_cfg["output_root"])).is_absolute()
        assert not Path(str(manifest["shards"][0]["study_config"])).is_absolute()
        assert not Path(str(manifest["shards"][0]["study_output"])).is_absolute()

        for text in _all_string_values(manifest) + _all_string_values(shard_cfg):
            assert "/actions-runner" not in text
            assert "/_work/" not in text


def test_run_study_resolves_repo_relative_output_on_current_runner(monkeypatch) -> None:
    output_relpath = "research/reports/batches/cross_runner_resolution_smoke"
    output_root = REPO_ROOT / output_relpath
    shutil.rmtree(output_root, ignore_errors=True)

    with TemporaryDirectory(dir=REPO_ROOT) as tmp:
        tmp_path = Path(tmp)
        cfg_path = tmp_path / "study_config.yaml"
        cfg_path.write_text(
            yaml.safe_dump(
                {
                    "study_name": "cross-runner-resolution-smoke",
                    "output_root": output_relpath,
                    "shared_defaults": {
                        "input_csv": "research/data_sample/usdjpy_m1_sample.csv",
                        "input_timezone_mode": "UTC",
                        "max_holding_bars": 5,
                        "symbol": "USDJPY",
                        "timeframe": "M1",
                        "analyze_after_run": False,
                    },
                    "runs": [{"label": "smoke"}],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        def _fake_run_cli(cli_path: Path, config_path: Path, repo_root: Path) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args=[str(cli_path), str(config_path)], returncode=0, stdout="ok", stderr="")

        monkeypatch.setattr("research.orchestration.study_runner._run_cli", _fake_run_cli)

        metadata = run_study(cfg_path)
        assert metadata["output_root"] == str(output_root.resolve())
        assert (output_root / "study_metadata.yaml").exists()
        assert (output_root / "runtime_configs").exists()
        assert (output_root / "runs" / "smoke" / "run_experiment.stdout.log").exists()

    shutil.rmtree(output_root, ignore_errors=True)
