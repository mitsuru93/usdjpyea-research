# USDJPY R2 Fixed-Horizon Surface Preregistration v1

## Decision

R2 evaluates the complete frozen R1 v2 Entry universe on canonical 2024 H1 only.

```text
Entry definitions: 60
fixed horizons: 11
surface combinations: 660
horizons: 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 M15 bars
candidate selection in R2: prohibited
H2 access: prohibited
2025 access: prohibited
Core promotion: false
MT4 promotion: false
```

Authoritative configuration:

```text
configs/research/usdjpy_r2_horizon_surface_v1.json
```

Authoritative evaluator:

```text
tools/run_usdjpy_r2_horizon_surface_v1.py
```

## Inputs

R2 accepts only:

1. canonical M15 bars from Release `usdjpy-r0-canonical-2024-v1`;
2. corrected R1 v2 signal ledger and registry snapshot from Release `usdjpy-r1-entry-registry-v2`;
3. the fixed market-session configuration;
4. the accepted H1 horizon diagnostic for implementation regression only.

The historical implementation reference is pinned as:

```text
run_id: 29583719940
artifact_id: 8408094591
artifact: usdjpy-h1-entry-horizon-diagnostic-v2-29583719940
artifact_digest: sha256:f95a0a450aa3b821dbcb20ea4f3410f345668606bf5f20a766a3e01d8a6e89e4
```

The corrected accepted R1 registry snapshot digest is:

```text
sha256:3bb43eeb1234ec6d175e37df3b1bbdb385364857351938bd088247ab14567549
```

The previously recorded `113f6f...` value was not the digest of the accepted artifact file and is excluded as an input-lock transcription error. No Entry definition or parameter changed.

R1 v1 run `29641805182` and artifact `8428842719` are excluded and may not be read.

## Horizon semantics

For a signal on M15 bar index `i`:

```text
Entry timestamp: bar i+1
Entry price: mid_open of bar i+1
h-bar Exit timestamp: bar i+h
Exit price: mid_close of bar i+h
```

Therefore horizon 1 enters at the next bar open and exits at that same bar close. This is a diagnostic fixed-horizon return, not a proposed operational Exit.

Entry and Exit must remain within the same UTC calendar month. A signal without a complete same-month path for a horizon is omitted from that horizon only.

## Cost semantics

Default cost:

```text
max(0.5 pips, actual Entry bar spread_mean_pips)
```

Severe cost:

```text
3 × max(0.5 pips, actual Entry bar spread_mean_pips) + 1.0 pip
```

The additional 1.0 pip represents 0.5-pip slippage on each side.

## Price-path semantics

For each Entry/horizon trade, R2 calculates path extrema from the Entry bar through the Exit bar inclusive:

- long MFE: maximum `mid_high - entry_mid`;
- long MAE: minimum `mid_low - entry_mid`;
- short MFE: maximum `entry_mid - mid_low`;
- short MAE: minimum `entry_mid - mid_high`;
- bars to MFE and MAE use the first occurrence.

Intrabar ordering is unknown. MFE and MAE are descriptive path extrema and must not be interpreted as simultaneously executable stop and target outcomes.

## Complete reporting

Every one of the 660 Entry/horizon combinations remains in the summary, including zero-trade definitions.

Required outputs include:

- normalized trade ledger;
- 660-row candidate/horizon summary;
- 3,960-row monthly grid;
- 1,320-row direction grid;
- sixty-row surface-shape summary;
- 660 deterministic ledger hashes;
- default and severe costs;
- MFE, MAE and timing-to-extrema;
- total excluding the best one and best two UTC Entry dates;
- implementation regression against the accepted legacy horizon diagnostic;
- acceptance and run metadata.

## Interpretation rule

R2 does not select a winner. The diagnostic maximum of one horizon is reported only to describe surface shape.

The following are not promotion evidence by themselves:

- one profitable horizon;
- the single highest average return;
- one profitable month;
- high signal count;
- low signal count;
- a neighbouring candidate with similar signals.

R3 and R4 will evaluate temporal stability, neighbouring-horizon support, concentration and family-level redundancy before selecting at most two representatives per family and eight overall.

## Historical implementation regression

The accepted H1 horizon diagnostic contains thirteen historical candidate projections across nine horizons:

```text
1, 2, 3, 4, 6, 8, 12, 16, 24
```

Its legacy output predates the R2 same-month rule and contains five trades whose Entry is in May and Exit is in June. Before comparison, the reference ledger is projected onto the already registered R2 domain:

```text
keep only rows where Entry UTC month equals Exit UTC month
expected excluded reference rows: 5
```

This projection changes neither the new R2 ledger nor any Entry, horizon, cost or performance rule. It prevents a legacy diagnostic with cross-month paths from being incorrectly treated as the R2 target.

R2 must reproduce all 117 candidate/horizon projected ledgers exactly by Entry timestamp and direction and within absolute tolerance `1e-9` for:

- Exit timestamp;
- gross pips;
- default cost and net pips;
- severe cost and net pips.

C1 and C2 remain separate historical projections of the shared Entry definition.

## Acceptance

R2 passes only if:

1. accepted R0 and R1 Release asset digests and the historical horizon artifact digest match;
2. canonical M15, R1 signal and R1 registry-snapshot digests match;
3. only 2024 H1 bars are parsed;
4. H2 rows parsed equals zero;
5. 2025 access equals false;
6. sixty registered candidates are present;
7. eleven horizons are present;
8. all 660 summary combinations are present;
9. all 3,960 monthly rows are present;
10. all 1,320 direction rows are present;
11. zero-trade candidates remain represented when present;
12. Entry and Exit remain in the same UTC month;
13. every Entry is the actual next M15 bar;
14. hard no-trade violations equal zero;
15. default cost is exact;
16. severe cost is exact;
17. MFE and MAE fields are complete;
18. trade-ledger gzip is byte deterministic;
19. the legacy artifact contains exactly five cross-month rows and all 117 projected historical horizon ledgers reproduce;
20. no selection or promotion decision is emitted;
21. Core and MT4 promotion remain false.

## Next stage

A passing R2 unblocks R3 temporal-stability diagnostics. R2 output may not be used to modify the sixty Entry definitions or the eleven fixed horizons.
