# USDJPY Full Frozen Architecture Census Preflight Result v1

Decision: **PASS — unlock Stage 2 only after this atomic change is merged**

## Authority

The preflight used the accepted R2 Release `usdjpy-r2-horizon-surface-v1`:

- Run ID: `29646040010`
- artifact ID: `8430064217`
- artifact ZIP SHA-256: `84a495b7c7cddf1c719bb4c8ce78bfef2c990b355649d362c18481836d953426`

The fixed input identities were:

- canonical 2024 M15: `1566b9d0497f3a2aa156868144d31b89721fca48329feaf82035826ada7ee25c`
- R1 v2 signal ledger: `99c2e2d19bd76b2438c1cec6c777228f82cdca16eeb1b471257bd389d6b7dc9e`
- R1 v2 registry snapshot: `3bb43eeb1234ec6d175e37df3b1bbdb385364857351938bd088247ab14567549`

## Exact reproduction

All frozen 60 Entry definitions and eleven horizons were regenerated with the accepted R2 execution semantics. Every output matched the accepted R2 artifact both by row/numeric comparison and SHA-256:

| Output | Rows | SHA-256 exact |
|---|---:|---|
| trade ledger gzip | 383,078 | PASS |
| combination summary | 660 | PASS |
| monthly grid | 3,960 | PASS |
| direction grid | 1,320 | PASS |
| Entry surface | 60 | PASS |
| trade-ledger hash grid | 660 | PASS |

This proves exact reproduction of:

- next-M15 entry at mid open;
- exit at `entry index + horizon - 1` mid close;
- same-UTC-month retention;
- observed spread with a 0.5-pip default floor;
- severe cost `3 × default + 1 pip`;
- entry-through-exit MFE/MAE windows;
- all combination and trade-ledger hashes.

## Protected boundaries

No exact-2023 or 2024H2 census outcome was calculated in this stage. No single combination was ranked or selected. MT4 and 2025 remained locked.

## Stage 2

After this protocol/evaluator/preflight package is merged with both CI checks passing, the same frozen 660 combinations may be evaluated on 2023H1, 2023H2, 2024H1 and 2024H2.

The census will report cell robustness, contiguous horizon neighbourhoods and family-level breadth. It will not adopt the largest cell. A family region requires at least two distinct Entry definitions with three-horizon core-pass neighbourhoods and at least one full-gate cell per Entry. Any passing region only authorizes a separate finite preregistration.
