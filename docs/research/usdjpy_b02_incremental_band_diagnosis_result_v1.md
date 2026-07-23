# USDJPY B02 Incremental 20–40 Pip Band Diagnosis v1

Decision: **close RQ-019; do not repair Family I and do not activate the current Family J WIP**

## Scope

The B02 short population with more than 20 and at most 40 pips of side-aligned four-hour movement was compared across 2023 and both historical 2024 halves.

- 2023: 27 trades, JPY -2,218
- 2024 H1: 5 trades, JPY +1,970
- 2024 H2: 12 trades, JPY +2,676

No 2025 evidence was accessed and historical 2024 was not modified.

## Fixed partitions tested

The band was partitioned using no-lookahead features with mechanism-based cut points:

- recent and prior one-hour direction and acceleration;
- one-hour and four-hour path efficiency and aligned-step fraction;
- entry breakout distance and UTC session;
- exposure state;
- ATR percentile and reference-range width;
- signal close outside distance, body, close location and counter-wick geometry;
- pre-entry directional path, portfolio support and US DST state.

No fixed partition with at least two trades per period was negative in all three development periods. The 20-to-40-pip reversal cannot be repaired by adding a stable Family I condition.

## Family J WIP audit

The original next question was whether B02 shorts at or below 20 pips should be replaced by opposite long mean-reversion trades. A later algebraic audit showed that the reversed payoff is deterministically derivable from the already opened Family I trade outcomes. The WIP therefore cannot be described as blind preregistration.

The 20-pip reversal would make all three full development periods positive, but its implied 2024 H2 effect months are 3 positive and 3 negative. The WIP protocol requires at least 4 positive and at most 2 negative H2 effect months. Its own frozen breadth gate is already false.

The unmerged Family J branch is classified as `NOT_CANONICAL` and must not be merged or evaluated under its current claims.

## Result

- Close RQ-019.
- Do not add Family I thresholds or local conditions.
- Do not activate the current Family J WIP.
- Move to exact cross-year portability of independent fixed strategies and broader multi-day regime diagnosis.

## Evidence identities

- open-path diagnostic: `eaca60feafaa13d2c2bd868c1660e7903ab225f1c577264119ccb817044024a2`
- Atlas diagnostic: `0827f4693b632fb71d9b2069851cfa4bf7c145304fbd9a6e35d3d2df696f4404`
- open-path consistency: `62961e3fd6c7e95e22807ae8d7caac6284eb7a0e418122105318ecdda38d30c2`
- Atlas consistency: `492081153b18d389f14d8c64827479d78285492d51ebb2ab0165bbe3f2442fd7`

## Next action

Restore the exact accepted 2023 legacy-2024 timestamp transformer and portability evaluator, reproduce 1,543 shifted M15 bars and accepted B02/F05 identities, and then evaluate the unchanged fixed five-strategy cohort before any new family is opened.
