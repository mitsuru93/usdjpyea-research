# USDJPY-HYP-045 Final Result v1

## Decision

`PARTIAL_B0_STABILITY_IMPROVEMENT_WITH_REMAINING_LOSS_PERIODS`

The primary B0 architecture is retained and extended only by the frozen localized control:

`A3_B0_LOCALIZED_F05_LONG_SESSION_CLUSTER_CONTROL`

Rule hash:

`1425b4caf6c0a5e8c4f21be7efdf410442bbd6d24d329f87c9c4931eecbd4b7f`

Primary reference rule hash:

`d8878f92e0641b10c4926966a03a46f238e4074335312003b7a6c058f8843f94`

## Selection firewall

- 2020–2024: cause decomposition, finite candidate construction, comparison and freeze.
- 2025H1: validation only after freeze.
- 2025H2: prohibited and not accessed.
- Candidate retuning after validation: false.
- Production authorization: false.
- Live authorization: false.

## Economic result

| Metric | Current B0 | Selected A3 |
|---|---:|---:|
| 2020–2024 net JPY | 84,796 | 98,762 |
| 2020–2024 PF | 1.114410 | 1.137253 |
| Red half-years | 3 | 3 |
| Red quarters | 9 | 8 |
| Red months | 22 | 20 |
| Rolling 6m minimum JPY | -27,731 | -17,457 |
| Rolling 12m minimum JPY | -32,000 | -23,240 |
| Realized drawdown JPY | 50,884 | 39,562 |
| 2025H1 net JPY | 609 | 1,399 |
| 2025H1 PF | 1.005668 | 1.013116 |

Selected A3 cumulative results:

- 2020–2024 net: `+¥98,762`
- Through 2025H1 net: `+¥100,161`
- Through 2025H1 PF: `1.121227`
- 2021: `-¥1,986`
- 2022H2: `-¥10,748`
- 2025Q1: `-¥15,339`
- 2025Q2: `+¥16,738`
- Controlled trades: `62` in development and `64` through 2025H1

A3 materially improved long-horizon stability and remained positive in validation, while recurring loss periods were not eliminated. This is a partial stability improvement, not complete residual-loss elimination.

## Mechanism

After the current A4 control, block only an additional F05 Long entry when one or more accepted F05 Long trades have already matured and closed at a loss in the same UTC day/session; reset the local count after an accepted F05 Long win. The rule is information-time valid and does not use a calendar label.

## Core implementation and source-native qualification

Core PR `mitsuru93/usdjpyea-core#818` was merged as:

`06901e91a448ecb2f1afb9112253fdbfa018ac29`

Implementation authority:

- Candidate compile: `0 errors / 0 warnings`
- Implementation SHA-256: `fc9aa82e9ecd74951a00c0d06f260bca5ec54f91358152268dfd993f4f4157d2`
- Core source SHA-256: `7bdcaa5eeed0b711edc44a155e3f485ee888c490d82eac951aaf2634e36f9089`
- EX4 SHA-256: `b5fba35009f3da131f3f3c12d49cc1a35338a6a0bf4bfa8fc0e0432b3c2fd09`

Source-native Run `30640088883`:

- Tick count: `78,737,040`
- Initial balance: `¥100,000`
- Final balance: `¥110,530`
- Net: `+¥10,530`
- Minimum full equity: `¥67,391`
- Full-equity drawdown: `¥48,739`
- Realized drawdown: `¥40,448`
- Minimum free margin: `¥24,837.08`
- Minimum margin level: `150.6512%`
- Maximum open positions: `10`
- Maximum same-direction positions: `6`
- Maximum opposite-direction positions: `6`
- Maximum lots: `0.10`
- Stop out: `false`
- Blocked F05 Long trades: `33`
- Improvement versus reference: `+¥10,274`
- Duplicate-order prevention: `PASS`

## Rakuten MT4 qualification

Run `30676863366` completed with:

`PASS_CORE_MT4_SAME_INPUT_AND_RAKUTEN_QUALIFICATION`

2023–2024:

- Baseline: `¥70,455`
- Candidate: `¥79,984`
- Improvement: `+¥9,529`
- Blocked trades: `29`
- Exact close deltas: `0`
- Minimum equity: `¥79,088`
- Drawdown: `¥24,881`
- Minimum free margin: `¥50,559.76`
- Minimum margin level: `275.812%`
- Maximum open positions: `7`

2025H1:

- Baseline: `+¥609`
- Candidate: `+¥1,399`
- Improvement: `+¥790`
- Trades: `607`
- PF: `1.013116075865117`
- Q1: `-¥15,339`
- Q2: `+¥16,738`
- Blocked trades: `2`
- Exact close deltas: `0`
- Minimum equity: `¥74,732`
- Drawdown: `¥25,986`
- Minimum free margin: `¥39,205.32`
- Minimum margin level: `179.0064%`
- Maximum open positions: `8`

Restart restoration has a deterministic receipt and passed static/state reconstruction checks. A separate Strategy Tester process restart with account-continuity comparison was not executed; this limitation remains explicit.

## Authority limitation

The latest F05 binding contains `1,464` trades while the retained row-certified authority contains `1,451` trades. The unresolved difference is `13`; no synthetic rows were created.

## Compressed authority recovery

The retained cross-regime matrix was recovered and gated against its original byte-level authority:

- CSV bytes: `45,569`
- CSV SHA-256: `b59a5d547a9f68d56360a4d074f4cbea7c7c4034215ab27ea7e57bcc277257e4`
- CRC32: `84a5f2f6`
- gzip bytes: `12,106`
- gzip SHA-256: `fb361b2bf9b6611c8890a929723669de1ed8570e5b130d4c701214788931a2ab`
- Repair commit: `dfeec7e27209845f0fb7e9773399c583d54f8c3e`

## Immutable Release and cleanup

Release:

`usdjpy-hyp045-b0-cross-regime-stability-improvement-v5`

- Release ID: `363909176`
- Archive: `usdjpy-b0-cross-regime-stability-improvement-001-v5.zip`
- Archive SHA-256: `aa54091ed2149b2c8d6ce5da1f11c739ee0d213eb2dda2928e7dfa1c5c153065`
- Deterministic archive members: `70`
- Initial archive remote readback: `PASS`
- All required final Release assets remote readback: `PASS`
- Placeholder Releases `v1–v4`: preserved
- Exact-owner VPS cleanup: `PASS`
- Cleanup runner: `onamae-mt4-01`
- Process termination: `false`
- Other research affected: `false`

## Authority

- Core merge commit: `06901e91a448ecb2f1afb9112253fdbfa018ac29`
- Core economic authority commit: `3c02162ac52c929396be12217d0d8a4f8dbbc353`
- Economic source archive SHA-256: `0c0de1ea945229524b8525e9199b9d9c5341a6cc2a00a611ebfa97e53d2d5ac4`
- Selected ledger semantic authority commit: `3612f88239a4934cc25a94be4a56622f7243e32c`
- Release v5 target commit: `b2c742ffd7d31fcc5576afebf79bfcb2bc8fcd99`
- Authority issue: `mitsuru93/usdjpyea-core#849`

## Final status and next action

`COMPLETE_RELEASED_REMOTE_READBACK_AND_CLEANUP_VERIFIED`

Production authorization remains `false`; live authorization remains `false`; 2025H2 was not accessed.

The exact next action is an independent A2A plus A3 study. It must not reopen or retune HYP-045:

`START_INDEPENDENT_A2A_HIGHVOL_EXTENSION4_PERMISSION_PLUS_A3_F05_LONG_SESSION_CLUSTER_CONTROL_STUDY_WITHOUT_REOPENING_OR_RETUNING_HYP045`
