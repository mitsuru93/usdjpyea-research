# USDJPY F05 Long Post-Entry Lifecycle Authority — Completed Record

## Registration

- Work ID: `USDJPY-F05-LONG-POST-ENTRY-LIFECYCLE-AUTHORITY-001`
- Diagnostic ID: `USDJPY-DIAG-F05-LONG-POST-ENTRY-LIFECYCLE-001`
- Type: read-only authority completion
- New `USDJPY-HYP-*`: not assigned
- Final decision: `PASS_F05_LONG_LIFECYCLE_AUTHORITY_COMPLETED`

## Parent finding

The completed Persistent Residual-Loss Atlas ranked:

`strategy_side_path:F05|LONG|LONG_DURATION_STAGNATION`

as the highest-priority residual mechanism family, but MFE, MAE, time-to-excursion and valid decision-time winner exposure were unavailable. The Atlas therefore did not define an Exit, lifecycle rule or threshold.

HYP-046 subsequently closed with:

`KEEP_HYP045_A3_NO_SUPERIOR_COMBINATION`

The frozen HYP-045 A3 architecture remains the parent authority.

## Fixed observability contract

The study observed accepted HYP-045 A3 F05 Long events at the following preregistered horizons only:

- 60 seconds
- 300 seconds
- 900 seconds
- 1,800 seconds
- 3,600 seconds
- 7,200 seconds
- 14,400 seconds

The zero-pips boundary was descriptive, not searched. The authority recorded full-path and horizon-state MFE, MAE, time to MFE/MAE, first favorable/adverse excursion, longest non-positive duration and exposed winner population.

## Period firewall

- 2020–2024: lifecycle authority construction and descriptive observability comparison
- 2025H1: recurrence confirmation only
- 2025H2: prohibited and not accessed

## Prohibitions preserved

- no new Entry
- no new Exit
- no new permission
- no threshold search
- no strategy-rule change
- no alternative candidate outcome
- no MetaEditor compile
- no MT4 execution
- no production or live authorization

## Exact execution and publication

- Controller repository: `mitsuru93/usdjpyea-core`
- Implementation PR: `#1026`
- Runtime repair PR: `#1028`
- Equivalent month-cache performance route PR: `#1032`
- Core result binding PR: `#1035`
- Exact source SHA: `aefa05b4e59c102c1ecc0cdc130886659d2c75f6`
- Controller Run: `30875068408`, attempt `1`, success
- Publisher Run: `30876492532`, attempt `1`, success
- Release: `usdjpy-f05-long-post-entry-lifecycle-authority-v1`
- Archive SHA-256: `b3dde2925528ed6c93c956f339b195a82b734743a4b2adfa91937550ec0608ce`
- Remote readback: `PASS_RELEASE_REMOTE_READBACK`
- Core result merge SHA: `c949fc967cda42476657bf7f6a0d87c292b15dfe`

The earlier exact-SHA Run `30869905489` was cancelled as the technical class `PERFORMANCE_STALL_REPEATED_GZIP_RESCAN`. No partial scientific result from that Run was bound. The replacement altered raw Tick I/O only and passed cross-hour/cross-month equivalence plus Controller contract validation.

## Authority completion

- F05 Long events: **2,214**
- Tick-covered events: **2,214**
- Missing Tick events: **0**
- Tick coverage ratio: **100%**
- Analysis events, 2020–2024: **2,057**
- Recurrence-confirmation events, 2025H1: **157**
- Long-duration stagnation events: **1,067**
- Decision-state rows: **15,494**
- MFE/MAE authority: complete
- Time-to-excursion authority: complete
- Winner exposure at valid decision times: complete

## Top observable mechanism state

The highest-ranked preregistered state was:

`14400s | GIVEBACK_TO_NONPOSITIVE`

For 2020–2024:

- events in state: **928**
- loser events: **710**
- exposed winner population: **215**
- gross loss population: **-¥213,861**
- exposed winner profit: **¥37,882**
- winner contamination ratio: **23.17%**
- observed in every year from 2020 through 2024

For 2025H1 recurrence confirmation:

- recurrence: `true`
- loser events: **64**
- exposed winner population: **18**

The ¥213,861 value is a theoretical ex-post loss-population upper bound. It is not an achievable candidate result, alternative Exit outcome or authorization to close trades at four hours.

## Interpretation

The completed authority confirms that the F05 Long residual problem is not primarily an unobservable post-hoc label. A substantial, cross-year population is already non-positive four hours after having produced favorable excursion, and the same state recurs in 2025H1. However, **215 development winners also occupy the state**, so a simple unconditional four-hour exit would have material winner contamination. Any control study must therefore remain finite and explicitly quantify the trade-off; the authority itself does not define that control.

## Exact next action

`PREREGISTER_A_SEPARATE_FINITE_F05_LONG_LIFECYCLE_CONTROL_STUDY_USING_ONLY_THIS_FIXED_DECISION_TIME_AUTHORITY_WITHOUT_REOPENING_HYP045_OR_USING_2025H1_FOR_SELECTION`
