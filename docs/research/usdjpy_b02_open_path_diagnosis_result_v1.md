# USDJPY B02 Cross-Year Open-Path Diagnosis v1

Decision: **preregister a finite B02 short weak-four-hour-alignment admission family**

## Reconciliation

A common no-lookahead B02 feature contract was rebuilt from historical-lineage M15 Bid bar opens.

- 2023: 230 / 230 B02 rows, missing signal/entry times 0 / 0, non-next-bar entries 0, net JPY -12,459
- 2024 H1: 97 / 97 rows, missing 0 / 0, non-next-bar 0, net JPY +9,554
- 2024 H2: 102 / 102 rows, missing 0 / 0, non-next-bar 0, net JPY +15,627

The 2024 source lineage was not modified and no 2025 evidence was accessed.

## Common feature contract

All features are available by the B02 signal close:

- side-aligned M15-open movement over 15m, 30m, 1h and 4h;
- prior one-hour movement and one-hour acceleration;
- path efficiency, aligned-step fraction, range and total path length;
- executable entry distance outside the B02 session range;
- side, entry hour and pre-entry exposure state.

## Recurring negative admission state

Only one fixed descriptive rule had negative baseline P/L in all three periods with at least five trades per period:

**B02 short and side-aligned four-hour M15-open move at most 20 pips**

- 2023: 62 trades, JPY -7,792
- 2024 H1: 22 trades, JPY -5,332
- 2024 H2: 17 trades, JPY -1,480
- pooled: 101 trades, JPY -14,604

Short direction alone was not stable because B02 shorts were positive in 2024 H2. Four-hour weakness alone was also not stable. The recurring loss state was their conjunction.

## Mechanism

A B02 short session-range breakout entered without an established side-aligned four-hour downward open path is a weak-trend or counter-regime admission. The descriptive 20-pip boundary is not yet a selected candidate threshold.

## Duplicate-research audit

This is not a new generic momentum strategy and does not reopen the old R1 candidate universe. The prior ATR directional-change family generated independent entry rules. Family I conditions the already accepted B02 short breakout using its pre-entry four-hour path under the current historical MT4 lineage.

It is also distinct from Families A-H, which targeted F05 admission, exposure state or exit behavior.

## Evidence identities

- diagnostic script: `c315f942c8f83ca36682aa1f5da1d4e36db0284a21a2afa761d536b1b309cf37`
- common features: `a75138402da4b2447c497bfa1254c411501c319ae6fd0933048b1897652cd88a`
- reconciliation: `8e6eebdd2ba0a74fdd64c8cee8a94db0bc184f3e39e2bc640ae28bb7d4cd6445`
- fixed subgroup table: `b236c901f58ae98ef7a04fee4d3194d38b855b0de6dc67d62445bb33e5a1651f`
- consistency table: `a5e0b5a0b177962d8fb74d66ce407ec554105ade3df83fa2ee4ae5ea033815f3`

## Next action

Freeze a three-cell threshold grid before computing candidate P/L. B02 longs and all F05 trades remain unchanged. No candidate-specific 2025 access is permitted.
