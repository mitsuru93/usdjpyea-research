# USDJPY Market-State Router Candidate Freeze v1

## Frozen candidate

`S3_H4_ALIGNED`

The candidate is a permission overlay on the existing canonical B02/F05 entries. It does not define a new entry architecture.

An entry is permitted only when the latest completed exact-slot H4 EMA(6,24) state available at the entry timestamp equals the trade side.

## Frozen semantics

- H4 membership uses logical MT4 server four-hour buckets reconstructed from exact M15 slots.
- Partial H4 buckets do not update EMA or state.
- H4 close is the indicator price.
- EMA recursion is alpha `2/(span+1)`, equivalent to pandas `ewm(adjust=false, min_periods=slow)`.
- State is +1 for fast EMA above slow EMA, -1 below, and 0 before initialization or at exact equality.
- Only completed H4 information available at or before entry may be used.
- No strategy, period, direction, session or year exception is authorized.

## Required parity

Research generates two frozen ledgers:

1. every exact H4 state row, including information time and EMA values;
2. every one of the 1,882 canonical trade rows, including the joined H4 state and permission decision.

Core parity requires zero information-time, state and permission mismatches. EMA numeric comparison tolerance is `1e-10`.

## Locks

Until parity is proven:

- MT4 strategy testing is locked;
- 2025 access is locked;
- candidate parameters are locked;
- production authorization is false.
