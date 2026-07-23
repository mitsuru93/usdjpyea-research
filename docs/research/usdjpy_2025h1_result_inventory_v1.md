# USDJPY 2025 H1 complete result inventory v1

## Correction

The 2025 H1 evidence is not limited to the later Family E binding gate. The complete scientifically interpretable result population currently retained by the project contains six distinct portfolio cases:

1. accepted B02/F05 baseline;
2. SC70/C240 exact-impact reconstruction;
3. S1 direct MT4 diagnostic;
4. S2 direct MT4 diagnostic;
5. S3 direct MT4 diagnostic;
6. Family E direct MT4 binding gate.

The project’s durable artifact destination is **GitHub Release**, not Google Drive.

## Common 2025 H1 contract

- Interval: 2025-01-01 inclusive through 2025-07-01 exclusive
- Source: pre-existing Rakuten MT4 cached HST
- M1 SHA-256: `db00b63e9e7ff2dd3f785563ad7f392a7e79ccef8a2c3e696f662b397b2b5af0`
- M15 SHA-256: `b22e9fb9a6d0f397b4186ba17f6e71cae9eb38aa59f214dfd1eb5173e4e7f165`
- MT4 model: 0
- Spread: 5 points
- Lots: B02 0.01 and F05 0.01

## All result cases

| Case | Evidence type | Trades | Net JPY | Delta | PF | Equity DD basis | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| Baseline | Direct Rakuten MT4 | 463 | -20,808 | — | 0.829408 | tick: 42,737 | Accepted reference |
| SC70/C240 | Exact-impact reconstruction | 416 | -12,976 | +7,832 | 0.873833 | M15 snapshot: 30,363 | Closed diagnostic fail |
| S1 `F05_SW70_R10_E90_A240_v1` | Direct Rakuten MT4 diagnostic | 455 | -17,543 | +3,265 | 0.852104 | tick: 40,306 | Diagnostic only |
| S2 `B02F05_DSHOCK60_R20_E90_EXIT_v1` | Direct Rakuten MT4 diagnostic | 463 | -21,195 | -387 | 0.825174 | tick: 42,328 | Worse than baseline |
| S3 `F05_EXTATR25_LOC80_F30_v1` | Direct Rakuten MT4 diagnostic | 434 | -12,959 | +7,849 | 0.882164 | tick: 34,492 | Diagnostic only |
| Family E `E2_ADAPTIVE_60_90__A15_B5_C15_R0` | Direct Rakuten MT4 binding gate | 463 | -15,866 | +4,942 | 0.863026 | tick: 39,246 | Binding FAIL; specification closed |

The balance-ladder baseline is not a seventh distinct result. It reproduced the fixed 0.01-lot result exactly because the balance never reached JPY 150,000.

## Baseline monthly profile

| Month | Net JPY |
|---|---:|
| 2025-01 | -14,627 |
| 2025-02 | +4,475 |
| 2025-03 | -18,485 |
| 2025-04 | -9,972 |
| 2025-05 | +15,313 |
| 2025-06 | +2,488 |

## Candidate summary

### SC70/C240

This is not a separate candidate Strategy Tester artifact. It deterministically removes the frozen 47 trade keys from the accepted baseline evidence and validates the method against the direct 2024 H2 MT4 result.

- B02: 98 trades, JPY -10,021
- F05: 318 trades, JPY -2,955
- 27 losing and 20 winning trades removed
- loss avoided: JPY 19,127
- profit sacrificed: JPY 11,295
- result remained negative and the specification stayed closed

### S1

- Eight F05 entries removed
- B02 remained JPY -6,964
- F05 improved to JPY -10,579
- monthly deltas: +1,415, +683, +333, 0, +834, 0
- result remained negative

### S2

- Entry keys were unchanged
- Twelve exits changed
- B02 worsened to JPY -7,400
- F05 changed to JPY -13,795
- net deteriorated by JPY 387

### S3

- Twenty-nine F05 entries removed
- B02 remained JPY -6,964
- F05 improved to JPY -5,995
- monthly deltas: +2,342, -474, 0, +7,122, -658, -483
- the largest diagnostic improvement remained negative and was not promoted

### Family E

- B02 remained exactly JPY -6,964
- F05 improved from JPY -13,844 to JPY -8,902
- 40 F05 outcomes changed
- maximum tick-equity drawdown improved by JPY 3,491
- failed gates: candidate net positive, PF at least 1, and January–March nonnegative
- candidate-specific 2025 H2 was not accessed

## Excluded records

The following are not scientific 2025 H1 outcomes:

- Run `29932286502`: stopped during build/compile before either tester run;
- Run `29933179966`: stopped at the EX4 reproducibility gate before either tester run;
- `F05_MFE20_BOR1_EXIT_v1`: failed binding 2024 H2 and never received 2025 H1 authorization;
- D family: closed during 2024 development;
- F family: closed after 2024 H1 robustness failure.

## Identity erratum

The historical SC70/C240 summary records the source artifact digest as:

`sha256:0867bbfd33375fe006de98f41ccb8d0824b00c3649cecd174811d39fbb95a72a`

The GitHub Actions artifact API and accepted baseline assessment both verify artifact `8477893216` as:

`sha256:0867bb4d8bfb0be9f96e61dd1e9c73aadd56b2b217b514532596e644dc95a72a`

This inventory records the latter as the verified identity and treats the former as a historical metadata transcription defect. The original result file is not silently rewritten.

## Durable GitHub Release archive

All three source Actions artifacts are now archived under Core Release:

`usdjpy-2025h1-evidence-archive-v1`

| Evidence | Release asset ID | SHA-256 readback |
|---|---:|---|
| Baseline Run 29783855056 | 487144599 | `0867bb4d8bfb0be9f96e61dd1e9c73aadd56b2b217b514532596e644dc95a72a` |
| S1–S3 Run 29880733653 | 487144600 | `0ceced6933b493bf6c65fe53311c53b33cdf310578d51036c51617f2157af416` |
| Family E Run 29934029169 | 487144601 | `79238df0ffaff1df6fdb8034b63e4dd191270b5364c1ab3e12c3f04f47acc4bc` |

Each Release asset was downloaded after publication and matched its source Actions ZIP byte-for-byte. The Core receipt is stored at:

`docs/research/artifact_archives/usdjpy_2025h1_evidence_v1/receipt.json`

## Research boundary

These results define the already observed 2025 H1 adverse-regime evidence. They may be used as a final fixed gate for a future candidate developed and frozen from 2023/2024 evidence. They may not be used to retune or reopen the closed specifications listed above.
