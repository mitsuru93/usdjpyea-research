# USDJPY R1 Entry Registry Result v2

## Decision

```text
R1 v2: PASS
R1 v1: EXCLUDED
R2 fixed-horizon surface: unblocked but not started
H2 rows parsed: 0
2025 access: none
outcomes opened: false
Core promotion: false
MT4 promotion: false
```

R1 v2 freezes sixty unique M15 Entry definitions across twelve mechanism families and reproduces every historical registered-hold Entry ledger exactly. It calculates no Entry price, Exit, horizon, cost, PnL, profit factor, expectancy or promotion result.

## Accepted run

```text
workflow: Run Corrected USDJPY R1 Entry Registry v2
run_id: 29642282221
head_sha: 9393e4ac9ec7d712f85c29e9ef7f44025de25403
artifact_id: 8428977454
artifact: usdjpy-r1-entry-registry-v2-29642282221
artifact_digest: sha256:0e0de71ccc56409a919d48d61e4dcb12502cefdb3944374b9163eda76d222d74
```

## Durable archive

```text
release_tag: usdjpy-r1-entry-registry-v2
release_asset: usdjpy-r1-entry-registry-v2-run-29642282221-artifact-8428977454.zip
release_asset_digest: sha256:0e0de71ccc56409a919d48d61e4dcb12502cefdb3944374b9163eda76d222d74
archive_run_id: 29642345597
receipt: docs/research_reboot/artifact_archives/usdjpy_r1_entry_registry_v2/
```

The corrected R1 ledger is preserved independently of GitHub Actions artifact expiry.

## Timing-semantics correction

The excluded v1 runner evaluated `entry_hours_utc` on the signal-bar timestamp. V2 evaluates it on the actual next-M15-bar Entry timestamp, matching the authoritative corrected H1 implementation.

```text
candidate changes from v1: 0
parameter changes from v1: 0
threshold changes from v1: 0
outcome information used: false
```

Session candidates whose `entry_start_hour` and `entry_end_hour_inclusive` define signal-close windows remain unchanged.

## Frozen Entry universe

```text
families: 12
unique Entry definitions: 60
legacy unique Entries: 12
new Entries: 48
functional-definition duplicates: 0
exact signal-equivalent groups: 0
```

| Family | Candidates | Mechanism |
|---|---:|---|
| Impulse breakout | 5 | completed-channel break plus range expansion |
| Session range breakout | 5 | Asian, London and prior-day range breaks |
| Failed excursion reversion | 6 | failed rolling/session/prior-day breakouts |
| Compression expansion | 5 | range contraction followed by expansion break |
| Trend pullback resumption | 5 | multi-hour trend, pullback and resumption |
| Donchian channel breakout | 5 | completed rolling-channel cross |
| EMA trend cross | 5 | fast/slow EMA crossing |
| Volatility-adjusted momentum | 5 | realized-volatility-normalized return threshold |
| Bollinger re-entry reversion | 5 | statistical-band excursion and re-entry |
| Return-shock reversal | 5 | ATR-normalized shock followed by reversal |
| Session handoff | 4 | Asia-to-London and London-to-New York continuation/reversal |
| ATR filter directional change | 5 | stateful ATR-normalized filter-rule reversal |

## Signal structure

```text
H1 rows parsed: 12,112
first timestamp: 2024-01-02T00:00:00Z
last timestamp: 2024-06-28T20:45:00Z
first unparsed H2 timestamp: 2024-07-01T00:00:00Z
H2 rows parsed: 0
Entry signal rows: 34,955
candidate_signals.csv.gz sha256: 99c2e2d19bd76b2438c1cec6c777228f82cdca16eeb1b471257bd389d6b7dc9e
```

All sixty candidates generated signals. Signal count is a sample-structure measurement and is not used as an edge or promotion score.

Family signal counts:

| Family | Signals |
|---|---:|
| ATR filter directional change | 7,571 |
| Bollinger re-entry reversion | 3,719 |
| Compression expansion | 2,261 |
| Donchian channel breakout | 3,590 |
| EMA trend cross | 1,709 |
| Failed excursion reversion | 3,579 |
| Impulse breakout | 4,144 |
| Return-shock reversal | 3,256 |
| Session handoff | 102 |
| Session range breakout | 551 |
| Trend pullback resumption | 2,873 |
| Volatility-adjusted momentum | 1,600 |

## Historical Entry regression

All thirteen registered-hold historical candidate ledgers matched exactly by signal timestamp and direction after applying their registered hold-availability boundary.

| Historical candidate | Expected | Projected | Missing | Extra | Result |
|---|---:|---:|---:|---:|---|
| A1 impulse breakout hold6 | 391 | 391 | 0 | 0 | PASS |
| B1 Asia 00–06 breakout hold6 | 309 | 309 | 0 | 0 | PASS |
| B2 Asia 00–07 breakout hold6 | 320 | 320 | 0 | 0 | PASS |
| B3 prior UTC day breakout hold6 | 106 | 106 | 0 | 0 | PASS |
| C1 failed 12-bar hold3 | 149 | 149 | 0 | 0 | PASS |
| C2 failed 12-bar hold6 | 149 | 149 | 0 | 0 | PASS |
| C3 failed 24-bar hold6 | 110 | 110 | 0 | 0 | PASS |
| C4 failed Asia 00–06 hold6 | 505 | 505 | 0 | 0 | PASS |
| D1 compression 4v4 hold6 | 293 | 293 | 0 | 0 | PASS |
| D2 compression 8v8 hold6 | 207 | 207 | 0 | 0 | PASS |
| E1 trend 4h resumption hold6 | 396 | 396 | 0 | 0 | PASS |
| E2 trend 8h resumption hold6 | 387 | 387 | 0 | 0 | PASS |
| E3 trend 24h resumption hold6 | 361 | 361 | 0 | 0 | PASS |

```text
legacy_registered_hold_regression.csv sha256:
2936af74567bb89440f1a18027beac714321869e1e96b00eb218f8b25a459992
```

## Acceptance

The twenty original Entry-registry checks passed, plus:

```text
actual next-bar Entry-hour semantics: PASS
thirteen historical registered-hold regressions: PASS
```

`r1_v2_acceptance.json` SHA-256:

```text
a49d194cc52253207744894d23458ecf9228c3f205ef5438c707a3d27de6e20f
```

## Next step

R2 may evaluate the complete fixed-horizon surface on canonical 2024 H1 only:

```text
60 Entries × 11 horizons = 660 combinations
horizons: 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 M15 bars
```

No Entry definition may be added, removed or altered. No H2 or 2025 data may be read.
