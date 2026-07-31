# USDJPY-HYP-045 Economic Result v1

## Decision

`PARTIAL_B0_STABILITY_IMPROVEMENT_WITH_REMAINING_LOSS_PERIODS`

The primary B0 architecture is retained and extended only by the selected localized control:

`A3_B0_LOCALIZED_F05_LONG_SESSION_CLUSTER_CONTROL`

Rule hash:

`1425b4caf6c0a5e8c4f21be7efdf410442bbd6d24d329f87c9c4931eecbd4b7f`

## Selection firewall

- 2020–2024: cause decomposition, finite candidate construction, comparison and freeze.
- 2025H1: validation only after freeze.
- 2025H2: prohibited and not accessed.
- Production authorization: false.
- Live authorization: false.

## Economic comparison

| Metric | Current B0 | Selected A3 |
|---|---:|---:|
| 2020–2024 net JPY | 84,796 | 98,762 |
| 2020–2024 PF | 1.114410 | 1.137253 |
| Red quarters | 9 | 8 |
| Red months | 22 | 20 |
| Rolling 6m minimum JPY | -27,731 | -17,457 |
| Rolling 12m minimum JPY | -32,000 | -23,240 |
| Realized drawdown JPY | 50,884 | 39,562 |
| 2025H1 net JPY | 609 | 1,399 |
| 2025H1 PF | 1.005668 | 1.013116 |

A3 improved the long-horizon stability measures and remained positive in the validation period, while 2021, 2022H2 and 2025Q1 remained loss periods. The result is therefore a partial stability improvement, not complete residual-loss elimination.

## Mechanism

After the current A4 control, block only an additional F05 Long entry when one or more accepted F05 Long trades have already matured and closed at a loss in the same UTC day/session; reset the local count after an accepted F05 Long win. The rule is information-time valid and does not use a calendar label.

## Authority

- Core PR: `mitsuru93/usdjpyea-core#818`
- Core economic authority commit: `3c02162ac52c929396be12217d0d8a4f8dbbc353`
- Core authority and blocker receipt commit: `a0a434c4d5932cf9805534af765ad1eedad59a1a`
- Economic source archive SHA-256: `0c0de1ea945229524b8525e9199b9d9c5341a6cc2a00a611ebfa97e53d2d5ac4`
- The F05 1,464-vs-1,451 authority gap remains explicit; no synthetic rows were created.

## Current technical status

`BLOCKED_SERVICE_RUNNER_NOT_ACCEPTING_JOBS`

The stale service-runner holder was cancelled, but the replacement checkout-free job remained queued. This is an execution-environment stop, not a scientific failure and not a candidate decision change. The Rakuten Strategy Tester remains restricted to the interactive runner and must not run in Session 0.

## Remaining binding work

1. Restore the service and interactive runner listeners and verify pagefile/memory state.
2. Reconstruct the selected A3 implementation in Core.
3. Replay 2020–2022 over the certified 78,737,040 source-native ticks and bind full-equity, margin and concurrency evidence.
4. Run Rakuten MT4 qualification for 2023–2024 and 2025H1 without retuning.
5. Bind Research/Core parity, immutable Release/readback, final decision and cleanup receipts.
