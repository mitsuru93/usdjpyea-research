# USDJPY R1 Entry Registry Result v1

## Decision

```text
R1 Entry registry: PASS
R2 fixed-horizon surface: unblocked but not started
H2 opened for new candidates: false
2025 data access: none
Core promotion: false
MT4 promotion: false
```

R1 completed the pre-registered expansion of the USDJPY Entry universe. It did not calculate entry prices, exits, holding horizons, transaction-cost outcomes, expectancy, profit factor or promotion decisions.

## Accepted run

```text
workflow: Run USDJPY R1 Entry Registry v1
run_id: 29641805182
head_sha: 50411297d1743518371b06f0eceb039ab185bd89
artifact_id: 8428842719
artifact: usdjpy-r1-entry-registry-v1-29641805182
artifact_digest: sha256:a284e599c67910912d1e51c79d55ba4334e726ef423aba1b8ecb6a3e1ef9f27c
```

The downloaded Actions artifact ZIP was independently hashed after the run and matched the GitHub artifact digest exactly.

## Durable archive

```text
release_tag: usdjpy-r1-entry-registry-v1
release_assets: 3
release_asset: usdjpy-r1-entry-registry-v1-run-29641805182-artifact-8428842719.zip
release_asset_digest: sha256:a284e599c67910912d1e51c79d55ba4334e726ef423aba1b8ecb6a3e1ef9f27c
archive_run_id: 29641911300
archive_audit_artifact_id: 8428870489
archive_audit_artifact_digest: sha256:13a897ecf822f847fc607324d00c7375d637037261881770df85b9e0d4a557df
```

Receipt:

```text
docs/research_reboot/artifact_archives/usdjpy_r1_entry_registry_v1/
```

The accepted Entry ledger is therefore preserved independently of GitHub Actions artifact expiry.

## Frozen universe

```text
families: 12
unique Entry definitions: 60
legacy unique Entry definitions: 12
new Entry definitions: 48
functional definition duplicates: 0
exact signal-equivalent groups: 0
```

Family allocation:

| Family | Candidates | Mechanism class |
|---|---:|---|
| Impulse breakout | 5 | channel break plus range expansion |
| Session range breakout | 5 | Asian, London and prior-day range breaks |
| Failed excursion reversion | 6 | failed rolling/session/prior-day breakouts |
| Compression expansion | 5 | compressed range followed by expansion break |
| Trend pullback resumption | 5 | multi-hour trend, pullback and resumption |
| Donchian channel breakout | 5 | completed rolling-channel cross |
| EMA trend cross | 5 | fast/slow EMA directional cross |
| Volatility-adjusted momentum | 5 | realized-volatility-normalized return threshold |
| Bollinger re-entry reversion | 5 | statistical-band excursion and re-entry |
| Return-shock reversal | 5 | ATR-normalized shock followed by reversal bar |
| Session handoff | 4 | Asia-to-London and London-to-New York continuation/reversal |
| ATR filter directional change | 5 | stateful ATR-normalized directional-change filter |

The universe is grounded in established trend/momentum, technical-rule, volatility-seasonality, session-structure and intraday-reversal research. Literature grounding is recorded in:

```text
docs/research_reboot/usdjpy_r1_entry_universe_prereg_v1.md
```

## Signal-structure result

The accepted canonical M15 input produced:

```text
canonical H1 rows parsed: 12,112
first parsed timestamp: 2024-01-02T00:00:00Z
last parsed timestamp: 2024-06-28T20:45:00Z
first unparsed H2 timestamp: 2024-07-01T00:00:00Z
H2 rows parsed: 0
Entry signal rows: 34,636
candidate_signals.csv.gz sha256: facec1f6e89a3a4813dfdda0438a13ce68256fed8a8d761f670359260d6f7725
```

All sixty candidates generated at least one Entry signal. Fifty-nine candidates were active in all six H1 months. `R1K03_london_to_ny_cont` was active in five months and generated twenty-five signals. This is a sample-structure observation, not a performance decision.

Family signal counts:

| Family | Candidates | Total signals | Minimum per candidate | Maximum per candidate |
|---|---:|---:|---:|---:|
| ATR filter directional change | 5 | 7,571 | 861 | 2,515 |
| Bollinger re-entry reversion | 5 | 3,719 | 338 | 1,185 |
| Compression expansion | 5 | 2,261 | 318 | 553 |
| Donchian channel breakout | 5 | 3,590 | 345 | 1,259 |
| EMA trend cross | 5 | 1,709 | 129 | 739 |
| Failed excursion reversion | 6 | 3,579 | 443 | 814 |
| Impulse breakout | 5 | 4,114 | 388 | 1,548 |
| Return-shock reversal | 5 | 3,256 | 210 | 1,034 |
| Session handoff | 4 | 102 | 20 | 31 |
| Session range breakout | 5 | 551 | 94 | 140 |
| Trend pullback resumption | 5 | 2,568 | 361 | 751 |
| Volatility-adjusted momentum | 5 | 1,616 | 125 | 570 |

The complete pairwise matrix contains 1,770 candidate pairs. No two candidates produced identical signal ledgers. The largest exact-signal Jaccard overlap was:

```text
R1F04_donchian_64 versus R1F05_donchian_96
exact overlap: 337
union: 453
Jaccard: 0.743929359823
```

Other high-overlap neighbouring definitions remain in R2 because the roadmap explicitly requires evaluating coherent neighbouring horizon regions rather than selecting from Entry counts or overlap alone.

## Acceptance

All twenty R1 checks passed:

1. Canonical M15 digest exact.
2. H1-only rows parsed.
3. H2 rows parsed zero.
4. 2025 access false.
5. Family count twelve.
6. Candidate count sixty.
7. Family caps exact.
8. Candidate IDs unique.
9. Functional definitions unique.
10. No Exit or horizon parameter in R1.
11. All families supported by the runner.
12. All candidates reported.
13. Monthly grid complete: 360 rows.
14. Hourly grid complete: 1,440 rows.
15. Pairwise overlap complete: 1,770 rows.
16. Entries use the actual next M15 bar timestamp.
17. Hard no-trade violations zero.
18. No H2 Entry timestamp.
19. Outcome columns absent.
20. Deterministic signal-ledger gzip.

## Interpretation

R1 establishes breadth and non-duplication of the Entry universe. Signal frequency is not evidence of edge. High signal counts are not preferred, sparse candidates are not rejected, and no candidate is ranked using outcome information at this stage.

A1 and E3 remain closed as the previously tested Entry-plus-hold6 strategies. Their Entry definitions remain in the universe only as historical controls; R2 does not reinterpret their known H2 failure.

## Next step

R2 may now evaluate the pre-registered eleven fixed horizons on 2024 H1 only:

```text
1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 M15 bars
```

R2 must report default and severe cost, monthly stability, concentration and price path for all 660 Entry/horizon combinations. No candidate may be removed or added before the complete surface is produced. No H2 or 2025 data may be read.
