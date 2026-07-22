# USDJPY F05 MFE20 BOR1 Exit — H1 freeze evidence correction v2

## Decision

`F05_MFE20_BOR1_EXIT_v1` remains the same exact candidate. Its rule, thresholds, target strategy, processing order, 2024 H1 metrics, and period boundaries are unchanged.

The only corrected field is `expected_changed_positions` in the freeze evidence.

## Root cause

The v1 freeze recorded the correct pre-MT4 result SHA-256 and changed-trades CSV SHA-256, but the 24 rows transcribed into `expected_changed_positions` did not match that hashed CSV and did not reconcile to the frozen net delta, benefit, or harm.

Authoritative pre-MT4 evidence:

- repository: `mitsuru93/usdjpyea-core`
- run: `29886163522`
- artifact: `8516578659`
- artifact digest: `sha256:ba436166bdbb367e02bf376879f2ae6dc2780c4f3fd55b45076d616cf38eb3be`
- changed-trades file SHA-256: `5e5f9faf29c6ae1bc761ad5cf833ba645b3d5b71ba67ed252dbe6d01ad980603`
- result file SHA-256: `8b8b111b7245b1f68e80e7d95ae38dbcb32b650ed56994ef4cc8a59da961a8be`

Those 24 pre-existing rows reconcile exactly to:

- changed positions: 24
- net delta: +3,322 JPY
- benefit: 5,472 JPY
- harm: 2,150 JPY
- Q1 delta: +1,342 JPY
- Q2 delta: +1,980 JPY

## MT4 forensic corroboration

Rakuten MT4 Strategy Tester run `29893008498`, artifact `8518973150`, reproduced the same 24 changed trade keys, close times, candidate P/L values, aggregate net, PF, benefit, harm, quarter effects, and drawdown-improvement direction as the authoritative pre-MT4 artifact.

The MT4 run reached both baseline and candidate tester completion. Its final evaluator failed only because it compared the valid MT4 audits against the incorrectly transcribed v1 list.

The MT4 evidence is corroboration only. The corrected rows in freeze v2 are sourced exclusively from the pre-MT4 artifact.

## Boundary

- 2024 H2 accessed: no
- 2025 H1 accessed: no
- candidate logic changed: no
- candidate selection changed: no
- parameter changed: no
- live order authorized: no

The existing MT4 audit files may be re-evaluated without rerunning MT4 because the correction changes only evidence transcription and not candidate logic, tester output, or frozen gates.
