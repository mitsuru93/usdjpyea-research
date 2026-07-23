# USDJPY Post-Invalidation Recovery-Capacity Diagnosis v1

Decision: **preregister a finite persistent-structural-invalidation family**

## Scope and lineage

This is descriptive mechanism diagnosis only. It uses:

- 2023 rebuilt under the unchanged historical 2024 time/trade-key contract;
- historical 2024 H1;
- historical 2024 H2.

The 2024 source lineage was not modified. No candidate replacement P/L, threshold selection from 2025, or 2025 access occurred.

## Why Family G failed

Family G closed an F05 position after a single return inside its original breakout reference level. That trigger removed real losses, but its winner sacrifice was approximately equal to the benefit and its effect reversed by development period.

The unresolved distinction was not the depth of one invalidation observation. It was whether the position **remained structurally invalidated without reaccepting the breakout level**.

## Structural-persistence population

For trades that were inside the original breakout level at two checkpoints and never reaccepted above the level between them, baseline outcomes were negative in every development period.

### 30 to 60 minutes, no reacceptance above 0 pips

- 2023: 171 trades, JPY -34,090
- 2024 H1: 67 trades, JPY -6,969
- 2024 H2: 74 trades, JPY -17,012

### 30 to 90 minutes, no reacceptance above 0 pips

- 2023: 142 trades, JPY -32,072
- 2024 H1: 61 trades, JPY -6,642
- 2024 H2: 59 trades, JPY -19,303

### 60 to 90 minutes, no reacceptance above 0 pips

- 2023: 199 trades, JPY -44,547
- 2024 H1: 96 trades, JPY -8,593
- 2024 H2: 95 trades, JPY -26,994

These are descriptive baseline populations, not candidate results. Replacement exit P/L remains uncomputed until preregistration is merged.

## Rejected mechanism: shadow strategy health

Trailing virtual B02/F05 performance was compared using the last 20, 40 and 60 closed trades and the preceding 30, 60 and 90 days. Its relation to the next trade outcome changed sign across 2023, 2024 H1 and 2024 H2 for both strategies.

Shadow strategy health is therefore rejected as the successor mechanism. It is not used as a Family H feature, filter or threshold.

## New observable

`post_entry_structural_persistence_without_reacceptance`

An F05 trade is structurally invalidated when:

1. executable price is inside its original breakout reference level at a first frozen checkpoint;
2. executable price is still inside at a second frozen checkpoint; and
3. executable price has not reaccepted above a frozen level between the checkpoints.

This is not a nearby Family G threshold. It is a two-state time sequence with an intervening-path condition.

## Distinction from closed work

- Family G: one structural checkpoint; no persistence or intervening reacceptance path.
- Family D: absolute adverse P/L persistence, not the original breakout level.
- Family E: exposure support and recovery timing, not structural reacceptance.
- Family F: pre-entry event confirmation, not post-entry invalidation persistence.

## Evidence identities

- diagnosis script SHA-256: `8ff66500ec149c640483902c730135513846c9d8699b8bb1ad5ae06667f55622`
- feature table: `21164436b87b8aeb2210e4de4a78225a9bd6e85ae3ada986fe4f90452b1427fd`
- persistence summary: `da8f0c11548ee89e5b71a87ba9179c490fd472446acb4dc37e38d67f3608193a`
- shadow-health summary: `2dc233c04cf48cd0e5e92123e49d2357c5861d91e125cfa8d222c8ff536f0d89`
- shadow-health consistency: `79d17871bcf2233fc1c616938bafb6e3fa97fe915ebbe7f7b8ede16f9001ccd0`

## Next action

Freeze a six-cell Family H grid before computing any candidate replacement outcome. Evaluate it separately on 2023, 2024 H1 and 2024 H2. Do not expand the grid after seeing the result.
