# USDJPY B02 Incremental 20–40 Pip Band Diagnosis v1

Decision: **do not repair Family I; preregister a distinct reversal action**

## Scope

The B02 short population with more than 20 and at most 40 pips of side-aligned four-hour movement was compared across 2023 and both historical 2024 halves.

- 2023: 27 trades, JPY -2,218
- 2024 H1: 5 trades, JPY +1,970
- 2024 H2: 12 trades, JPY +2,676

No candidate outcome was calculated and no 2025 evidence was accessed.

## Fixed partitions tested

The band was partitioned using no-lookahead features with mechanism-based cut points:

- recent and prior one-hour direction and acceleration;
- one-hour and four-hour path efficiency and aligned-step fraction;
- entry breakout distance and UTC session;
- exposure state;
- ATR percentile and reference-range width;
- signal close outside distance, body, close location and counter-wick geometry;
- pre-entry directional path, portfolio support and US DST state.

No fixed partition with at least two trades per period was negative in all three development periods. The 20-to-40-pip reversal therefore cannot be repaired by adding a stable Family I condition.

## Action-level distinction

The B02 short population at or below 20 pips remains negative in every development period. Family I used the action “do not open the short.” That action improved every period but was not large enough to make 2023 positive.

A distinct causal interpretation is available: a downside session breakout without an established four-hour downtrend may be a false break. Instead of blocking the signal, the strategy can execute the opposite **long mean-reversion** trade at the same entry time and same fixed horizon.

This is a different action and payoff claim, not another Family I threshold.

## Prohibited reuse

- Do not add conditions or thresholds to the 20-to-40-pip Family I band.
- Do not use 2025 to find a band discriminator.
- Do not calculate reversal outcomes until the action and execution contract are preregistered.

## Evidence identities

- open-path diagnostic: `eaca60feafaa13d2c2bd868c1660e7903ab225f1c577264119ccb817044024a2`
- Atlas diagnostic: `0827f4693b632fb71d9b2069851cfa4bf7c145304fbd9a6e35d3d2df696f4404`
- open-path consistency: `62961e3fd6c7e95e22807ae8d7caac6284eb7a0e418122105318ecdda38d30c2`
- Atlas consistency: `492081153b18d389f14d8c64827479d78285492d51ebb2ab0165bbe3f2442fd7`

## Next action

Freeze Family J’s false-break reversal action before computing replacement P/L. Historical 2024 remains unchanged and 2025 stays locked.
