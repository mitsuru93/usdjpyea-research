#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

INITIAL_CAPITAL_JPY = 1_000_000.0


def profit_factor(values: Iterable[float]) -> float:
    array = np.asarray(list(values), dtype=float)
    gains = float(array[array > 0].sum())
    losses = float(-array[array < 0].sum())
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def realized_equity_metrics(trades: pd.DataFrame, pl_col: str = "pl_jpy", close_col: str = "exit_utc") -> dict[str, float]:
    if trades.empty:
        return {"net_jpy": 0.0, "profit_factor": 0.0, "mdd_jpy": 0.0, "minimum_equity_jpy": INITIAL_CAPITAL_JPY}
    ordered = trades.sort_values([close_col, "event_id"], kind="mergesort")
    values = ordered[pl_col].astype(float).to_numpy()
    equity = INITIAL_CAPITAL_JPY + np.cumsum(values)
    full = np.r_[INITIAL_CAPITAL_JPY, equity]
    peak = np.maximum.accumulate(full)
    drawdown = peak - full
    return {
        "net_jpy": float(values.sum()),
        "profit_factor": float(profit_factor(values)),
        "mdd_jpy": float(drawdown.max(initial=0.0)),
        "minimum_equity_jpy": float(full.min(initial=INITIAL_CAPITAL_JPY)),
    }


def trade_metrics(trades: pd.DataFrame, pl_col: str = "pl_jpy") -> dict[str, Any]:
    if trades.empty:
        return {
            "event_count": 0, "net_jpy": 0.0, "profit_factor": 0.0, "win_rate": 0.0,
            "median_pl_jpy": 0.0, "mae_pips_mean": None, "mfe_pips_mean": None,
            "mdd_jpy": 0.0, "minimum_equity_jpy": INITIAL_CAPITAL_JPY,
        }
    base = realized_equity_metrics(trades, pl_col=pl_col)
    values = trades[pl_col].astype(float)
    return {
        "event_count": int(len(trades)),
        **base,
        "win_rate": float((values > 0).mean()),
        "median_pl_jpy": float(values.median()),
        "mae_pips_mean": float(trades["mae_pips"].mean()) if "mae_pips" in trades and trades["mae_pips"].notna().any() else None,
        "mfe_pips_mean": float(trades["mfe_pips"].mean()) if "mfe_pips" in trades and trades["mfe_pips"].notna().any() else None,
    }


def grouped_metrics(trades: pd.DataFrame, group_columns: list[str], candidate_id: str, pl_col: str = "pl_jpy") -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, group in trades.groupby(group_columns, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {column: value for column, value in zip(group_columns, keys)}
        row.update({"candidate_id": candidate_id, **trade_metrics(group, pl_col=pl_col)})
        rows.append(row)
    return pd.DataFrame(rows)


def removal_metrics(trades: pd.DataFrame, pl_col: str = "pl_jpy") -> dict[str, float]:
    values = trades[pl_col].astype(float).sort_values(ascending=False).to_numpy()
    return {
        "best_event_removed_net_jpy": float(values[1:].sum()) if len(values) > 1 else 0.0,
        "top3_removed_net_jpy": float(values[3:].sum()) if len(values) > 3 else 0.0,
        "top5_removed_net_jpy": float(values[5:].sum()) if len(values) > 5 else 0.0,
    }


def positive_share(trades: pd.DataFrame, group_col: str, pl_col: str = "pl_jpy") -> float:
    totals = trades.groupby(group_col, sort=False)[pl_col].sum()
    positive = totals[totals > 0]
    denominator = float(positive.sum())
    if denominator <= 0:
        return 0.0
    return float(positive.max() / denominator)


def concentration_metrics(trades: pd.DataFrame, pl_col: str = "pl_jpy") -> dict[str, float]:
    result = removal_metrics(trades, pl_col=pl_col)
    result.update({
        "largest_positive_fold_share": positive_share(trades, "fold", pl_col),
        "largest_positive_session_share": positive_share(trades, "session", pl_col),
        "largest_positive_month_share": positive_share(trades, "month", pl_col),
    })
    return result


def bootstrap_values(values: np.ndarray, seed: int, iterations: int = 5000) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return {"iterations": iterations, "lower95_jpy": 0.0, "median_jpy": 0.0, "upper95_jpy": 0.0, "probability_nonpositive": 1.0}
    rng = np.random.default_rng(seed)
    chunk = 500
    totals: list[np.ndarray] = []
    for start in range(0, iterations, chunk):
        count = min(chunk, iterations - start)
        indexes = rng.integers(0, len(values), size=(count, len(values)))
        totals.append(values[indexes].sum(axis=1))
    sample = np.concatenate(totals)
    return {
        "iterations": int(iterations),
        "lower95_jpy": float(np.quantile(sample, 0.025)),
        "median_jpy": float(np.quantile(sample, 0.5)),
        "upper95_jpy": float(np.quantile(sample, 0.975)),
        "probability_nonpositive": float(np.mean(sample <= 0)),
    }


def bootstrap_metrics(trades: pd.DataFrame, seed: int = 3401, pl_col: str = "pl_jpy") -> dict[str, dict[str, float]]:
    event = bootstrap_values(trades[pl_col].astype(float).to_numpy(), seed=seed)
    blocks = trades.groupby(["entry_date", "session"], sort=True)[pl_col].sum().to_numpy(dtype=float)
    date_session = bootstrap_values(blocks, seed=seed + 1)
    dates = trades.groupby("entry_date", sort=True)[pl_col].sum().to_numpy(dtype=float)
    date = bootstrap_values(dates, seed=seed + 2)
    return {"event": event, "date_session": date_session, "date": date}


def cost_stress(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    stresses = {
        "OBSERVED_BIDASK": trades["pl_jpy"].astype(float),
        "SPREAD_PLUS_0_5_PIP": trades["pl_jpy"].astype(float) - 5.0,
        "SPREAD_PLUS_1_0_PIP": trades["pl_jpy"].astype(float) - 10.0,
        "SPREAD_PLUS_2_0_PIP": trades["pl_jpy"].astype(float) - 20.0,
        "ENTRY_DELAY_5S": trades["pl_delay_5s_jpy"].astype(float),
        "ENTRY_DELAY_10S": trades["pl_delay_10s_jpy"].astype(float),
        "ADVERSE_SLIPPAGE_0_5_PIP": trades["pl_jpy"].astype(float) - 5.0,
        "ADVERSE_SLIPPAGE_1_0_PIP": trades["pl_jpy"].astype(float) - 10.0,
    }
    for name, values in stresses.items():
        rows.append({
            "stress": name,
            "event_count": int(len(values)),
            "net_jpy": float(values.sum()),
            "profit_factor": float(profit_factor(values)),
        })
    return pd.DataFrame(rows)


def rule_mask(trades: pd.DataFrame, rule: dict[str, Any]) -> pd.Series:
    mask = pd.Series(True, index=trades.index)
    for condition in rule.get("conditions", []):
        feature = condition["feature"]
        threshold = float(condition["threshold"])
        operator = condition["operator"]
        values = pd.to_numeric(trades[feature], errors="coerce")
        if operator == ">=":
            mask &= values >= threshold
        elif operator == "<=":
            mask &= values <= threshold
        else:
            raise ValueError(f"unsupported operator {operator}")
    return mask.fillna(False)


def apply_active_suppression(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    kept: list[int] = []
    active_until = pd.Timestamp.min.tz_localize("UTC")
    for index, row in trades.sort_values(["entry_utc", "event_id"], kind="mergesort").iterrows():
        entry = pd.Timestamp(row["entry_utc"])
        if entry < active_until:
            continue
        kept.append(index)
        active_until = pd.Timestamp(row["exit_utc"])
    return trades.loc[kept].sort_values(["entry_utc", "event_id"], kind="mergesort").reset_index(drop=True)


def evaluate_rule(trades: pd.DataFrame, rule: dict[str, Any]) -> pd.DataFrame:
    selected = trades.loc[rule_mask(trades, rule)].copy()
    return apply_active_suppression(selected)


def daily_series(trades: pd.DataFrame, pl_col: str = "pl_jpy", date_col: str = "exit_date") -> pd.Series:
    if trades.empty:
        return pd.Series(dtype=float)
    return trades.groupby(date_col, sort=True)[pl_col].sum().astype(float)


def correlation(left: pd.Series, right: pd.Series) -> float | None:
    frame = pd.concat([left.rename("left"), right.rename("right")], axis=1).fillna(0.0)
    if len(frame) < 2 or frame.left.std(ddof=0) == 0 or frame.right.std(ddof=0) == 0:
        return None
    return float(frame.left.corr(frame.right))


def deterministic_csv(frame: pd.DataFrame, path: Path, gzip: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = frame.to_csv(index=False, lineterminator="\n", na_rep="", float_format="%.10f").encode("utf-8")
    if gzip:
        import gzip as gzip_module
        import io
        output = io.BytesIO()
        with gzip_module.GzipFile(filename="", mode="wb", fileobj=output, compresslevel=9, mtime=0) as handle:
            handle.write(data)
        payload = output.getvalue()
    else:
        payload = data
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def write_json(payload: dict[str, Any] | list[Any], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def package_manifest(output_dir: Path, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    files: list[dict[str, Any]] = []
    for path in sorted(item for item in output_dir.rglob("*") if item.is_file() and item.name not in exclude):
        data = path.read_bytes()
        files.append({"path": path.relative_to(output_dir).as_posix(), "byte_size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {"schema_version": "usdjpy_hyp034_output_manifest_v1", "files": files, "file_count": len(files)}
