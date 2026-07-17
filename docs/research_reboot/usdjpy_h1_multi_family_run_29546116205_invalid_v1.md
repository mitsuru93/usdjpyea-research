# USDJPY H1 Multi-Family Run 29546116205 — Invalid

## Run status

```text
workflow run: 29546116205
job conclusion: success
artifact: usdjpy-h1-multi-family-screen-29546116205
artifact digest: sha256:3014190badb48d2ffe0ecbe813b6b2a84f4ce3bdb506455cf2ac56ae604d66a4
head SHA: 94173935ab1a0b5eab8a3b4cb43a25c622fbe259
```

All workflow steps completed, but the candidate results are invalid for research decisions because the implementation did not match the registered entry-time and cost semantics.

## Defect 1: entry-hour offset

Candidates with `entry_hours_utc` were filtered using the signal M15 bar hour:

```text
bars["hour_utc"].isin(candidate["entry_hours_utc"])
```

The registered definition is next-bar entry time. For a next-bar-open entry, the allowed-hour condition must use:

```text
bars["timestamp_utc"].shift(-1).dt.hour
```

For A1 this defect:

```text
incorrectly removed: 16 canonical signals
incorrectly added:   13 signals
reported trades:     388
canonical trades:    391
```

A typical error was removing a 12:45 signal whose entry was 13:00 and adding a 16:45 signal whose entry was 17:00.

The same offset affected the rolling failed-excursion, compression-expansion and higher-timeframe trend candidates that use `entry_hours_utc`.

Session-range candidates retain their explicit signal-close windows; those windows are not converted to entry-hour windows.

## Defect 2: spread basis

The invalid screen used the entry bar's `spread_open_pips`.

The canonical monthly baseline implementation uses the entry bar's:

```text
spread_mean_pips
```

and applies:

```text
max(0.5-pip base spread, entry spread_mean_pips)
```

This caused P&L differences even where signal timestamp, side, entry mid and exit mid matched.

## Consequence

The following outputs from run 29546116205 must not be used:

```text
candidate_summary.csv
candidate_monthly.csv
family_ranking.csv
retained_candidates.json
candidate_trades.csv
```

In particular, its retained-candidate list is not the Step 3B decision.

## Correction

Corrected wrapper:

```text
tools/run_usdjpy_h1_multi_family_screen_v2.py
```

Corrected workflow:

```text
.github/workflows/run_usdjpy_h1_multi_family_screen.yml
```

The corrected workflow writes to a v2 output directory and includes a mandatory regression check against the exact-source-confirmed A1 canonical result:

```text
trades: 391
total net pips: 788.2165005892261
average net pips: 2.0158989784890693
profit factor: 1.2805773608918685
```

If any value fails to reproduce, the workflow fails before the multi-family result is accepted.

## Next action

Run a new workflow dispatch of:

```text
Run USDJPY H1 Multi-Family Screen
```

Do not rerun the old run attempt, because it checks out the old commit.
