# USDJPY Family E Exact 2024 Research-to-MT4 Parity Result v1

## Decision

**PASS**

`E2_ADAPTIVE_60_90__A15_B5_C15_R0` reproduced the frozen 2024 Research result on the Rakuten MT4 Strategy Tester.

This result proves the exact MT4 implementation and the frozen Research expectation agree for:

- unchanged baseline entries;
- unchanged B02 outcomes;
- the exact 37 Family E changed positions;
- dynamic entry-exposure state;
- 60-minute and 90-minute exit assignment;
- exit UTC;
- gross pips;
- H1 and H2 net profit and profit factor;
- zero order-send and order-close failures.

It does not constitute independent validation because 2024 H1 and H2 are development periods under period-role policy v4.

## Binding identities

| Item | Identity |
|---|---|
| Research freeze commit | `f23abdf24e757601a9ed0c35d81bfb688737c762` |
| Core final main commit | `2434df896f71cb67de279cae9d516569ebd5e187` |
| Binding Run | `29924434439`, attempt 1 |
| Job | `88937828542` |
| Runner | `onamae-mt4-ui-01` |
| Artifact | `8531451951` |
| Artifact digest | `sha256:cbac9ba7341fb7d9172e112b4050c33caa64fa32f4ad943e9d19f37dd91c2a01` |
| Receipt | Core issue `131` |
| Candidate EX4 SHA-256 | `a441141b5e51fb70de94cc3ca4829b95d669ff8ccefefd02bc471d110f4ac2c8` |

The Run used the self-hosted interactive Rakuten MT4 runner with USDJPY M15, model 0 and spread 5 MT4 points, equivalent to 0.5 pips.

## Result

| Period | Baseline net | Candidate net | Delta | Candidate PF | Changed positions |
|---|---:|---:|---:|---:|---:|
| 2024 H1 | JPY 22,797 | JPY 25,085 | **JPY +2,288** | 1.431644153833 | 11 |
| 2024 H2 complete | JPY 38,109 | JPY 43,879 | **JPY +5,770** | 1.428158816584 | 26 |
| 2024 full year | — | — | **JPY +8,058** | — | 37 |

All 32 frozen parity gates passed. The result contains no failed gate.

## Technical reconciliation

The first complete four-test Run reproduced both baselines exactly and reproduced the H1 candidate metrics, but exposed two technical mismatches:

1. MT4 audit timestamps used dotted dates while the frozen expected CSV used hyphenated dates. The evaluator now normalizes formatting before comparison.
2. One H2 trade had no exact 30-minute and 60-minute checkpoint bar. The original EA used elapsed bar count and substituted different timestamps. Research treated the checkpoint as missing. The repaired EA only evaluates Family E when the exact UTC 30-, 60- and 90-minute M15 checkpoint exists.

These repairs do not change the candidate thresholds, the state rule, the frozen 37 expected trades or the ranking. They align the MT4 implementation with the preregistered exact-checkpoint semantics.

The final Run then matched all 37 changed positions, states, exit timestamps and gross pips exactly.

## Evidence hashes

| Evidence | SHA-256 |
|---|---|
| H1 candidate audit | `1ca20456f820b43ba5aadc3e5a6e897fce77be61c6cee50ec9e1677a22ea052c` |
| H2 candidate audit | `56e4531865bb82580bca9a99d71954475ce1e63cf7d4bf7ace99ef1a041dcaf9` |
| Validation result JSON | `f1c7d41c6a50562dcec54c528d4f6bbf4a9945869396563bc1053a54a1421280` |
| Changed outcomes CSV | `1943e128b70e959f9cd5f23028e02152188dfb2a03ef2d1dfc25df05f2f64477` |
| Candidate base MQ4 | `95740f62f03a791613593d200e1cb2762a2f4cd223f417f7d4c242fd5815465b` |
| Candidate wrapper MQ4 | `d956f54dc7c61c9b22712c32ab10a768911fe8526cdab68d38fdd932a3fae29b` |
| Candidate EX4 | `a441141b5e51fb70de94cc3ca4829b95d669ff8ccefefd02bc471d110f4ac2c8` |

## Receipt metadata note

Core issue 131 inherited the original workflow-level builder and evaluator values. The uploaded artifact's `run_manifest.json` and `core_identity_verification.json` bind the actually executed repaired v2 builder and evaluator:

- builder blob: `bd82b9267b51a21065e4c1688ce4feb9feb94a5c`;
- evaluator blob: `bd296be5e3ed28f2ee8b23228a1386bb2a575ae5`.

The artifact is authoritative for executed code identity.

## Period and authorization state

- 2024 H1: development and mechanism analysis.
- 2024 H2: development and cross-regime analysis.
- 2025 H1: first binding Rakuten MT4 stress gate.
- 2025 H2: final binding validation, locked until 2025 H1 passes.

No candidate-specific 2025 H1 or H2 evidence was accessed by the parity Run. Live orders remain unauthorized.

## Next stage

The next authorized stage is:

`REUSABLE_2025_H1_WORKFLOW_PREFLIGHT`

This stage may build, identity-lock and dry-preflight the reusable 2025 H1 workflow. It must not execute the candidate on 2025 H1 data. Candidate-specific 2025 H1 execution requires a later atomic authorization after the preflight package is reviewed and frozen.
