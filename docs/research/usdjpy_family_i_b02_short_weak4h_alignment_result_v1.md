# USDJPY Family I B02 Short Weak-Four-Hour Alignment Result v1

Decision: **CLOSED — no eligible specification**

## What was tested

The exact three preregistered thresholds blocked only accepted B02 short trades whose side-aligned four-hour M15-open movement was at most 0, 20 or 40 pips. B02 longs and all F05 trades remained unchanged. No 2025 evidence was accessed.

## Results

### `I_B02_SHORT_M4LE20`

This rule improved every development period:

- 2023: JPY -1,487, delta +7,792, PF 0.991953
- 2024 H1: JPY 28,129, delta +5,332
- 2024 H2: JPY 39,838, delta +1,480

Pooled delta was JPY +14,604, ex-best-two remained JPY +9,061 and leave-one-month-out minimum was JPY +10,859. However, the 2023 portfolio remained negative and PF stayed below 1. It also produced 17 positive and 7 negative effect months versus the preregistered 18 / 4 gate.

### `I_B02_SHORT_M4LE40`

This was the first tested rule to make the 2023 portfolio positive:

- 2023: JPY +731, delta +10,010, PF 1.004099
- 2024 H1: JPY 26,159, delta +3,362
- 2024 H2: JPY 37,162, delta -1,196

The rule failed because the additional B02 shorts in the 20-to-40-pip alignment band were profitable in 2024 H2. Loss avoided was below profit sacrificed in that period.

## Interpretation

Family I establishes a useful boundary but not a candidate.

- Blocking short B02 entries below 20 pips is directionally beneficial across all periods but insufficient for the 2023 positive-net gate.
- Extending the block to 40 pips solves 2023 but crosses into a regime-dependent band that contains profitable 2024 trades.

The next question is not another threshold. It is what no-lookahead state distinguishes the 20-to-40-pip band in 2023 from the same band in 2024.

## Invariance

- B02 longs: exact
- F05 trades and P/L: exact
- historical 2024 source: unchanged
- 2025 access: none

## Prohibited reuse

- Do not add another Family I threshold.
- Do not promote the 40-pip cell while ignoring its 2024 H2 reversal.
- Do not use 2025 to split the 20-to-40-pip band.
- Do not combine Family I with closed F05 candidates from their development results.

## Evidence identities

- evaluator: `31a9bb17dc364955d35293b369cbe6c1e377747d628eb77fa27fb147d7016f41`
- candidate summary: `9ecdb83b1ceda95170e1cf2f0105745fea19d1b2ebd8512e4061f0c2fe92801f`
- period metrics: `76fc56517ed33008569abda3dd3c6b58486c1d7f54f6dc46890cc5428cf3c73f`
- blocked effects: `ea6a2ec00f569c4bbb87188f8320974309bd1c667d85808c16763889fdfc3a29`
- equivalence classes: `de0319d8273187ae7d18c4765744d726a6d96bccce49b428b884d754c90c921a`

## Next action

Describe the incremental 20-to-40-pip B02 short population across 2023 and both 2024 halves using only pre-entry features. No successor family is authorized by this result alone.
