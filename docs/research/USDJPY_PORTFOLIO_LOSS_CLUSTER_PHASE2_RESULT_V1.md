# USDJPY-HYP-027 / SESSION_LOSS_CAP_2 Phase 2 Confirmation

## Final decision

`FAIL_PHASE2_SIDE_BREADTH_SHORT_DEPENDENT`

The unchanged Phase 1 candidate was reproduced exactly and improved pooled net, PF, and drawdown, but it failed the binding breadth contract. Long deteriorated by JPY 1,570, all positive side effect came from Short, and F05 explained 76.5264% of positive strategy effect.

## Authority and protocol

- Study: `USDJPY-PORTFOLIO-LOSS-CLUSTER-PHASE2-V1`
- Hypothesis: `USDJPY-HYP-027`
- Candidate: `SESSION_LOSS_CAP_2`
- Role: `INTERNAL_CONFIRMATION_AND_IMPLEMENTATION_CONTRACT_VALIDATION`
- Research start SHA: `bb4a9dcedec8390585b4c4611c9316bb4febb34c`
- Core start SHA: `dbffc656a0793a2efd9bd54394223f1239de2afa`
- Phase 2 protocol commit: `2e48531cbba7a64babdf48950104e19a0e5560a9`
- Phase 2 workflow Run: `30331667249`
- Actions artifact: `8677604809`
- Artifact digest: `sha256:192d3d8fa3967b8b36f1ab3cd238a39745fa92950aad7f6371a78371f54face6`

## Exact state semantics

- UTC session buckets: Tokyo 00:00–06:59, London 07:00–12:59, London/NY overlap 13:00–15:59, New York 16:00–19:59, transition 20:00–23:59.
- Session key: UTC calendar date plus session bucket.
- B02/F05 and Long/Short share one loss counter.
- Winners do not reset the counter.
- Accepted closes with `close_utc <= entry_utc` are applied before an Entry; close order is close timestamp then trade ID.
- Same-timestamp Entry order is strategy then trade ID.
- A loss is canonical accepted `realized_pl_jpy < 0`; zero is breakeven.
- Blocked trades never update future state.

## Phase 1 exact reproduction

- Trade identity: 1,882 / 1,882
- B02 / F05: 429 / 1,453
- Long / Short: 1,166 / 716
- Blocked identity: 27 / 27
- Missing / extra / duplicate: 0 / 0 / 0
- Decision / reason / timestamp mismatch: 0 / 0 / 0
- Future-information violations: 0

## Economics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| Net JPY | 51,627 | 57,212 | +5,585 |
| PF | 1.1377 | 1.1562 | +0.0185 |
| Realized DD JPY | 40,487 | 36,770 | -3,717 |
| M15 snapshot DD JPY | 42,660 | 38,943 | -3,717 |
| Gross loss JPY | 374,888 | 366,271 | -8,617 |
| Gross profit JPY | 426,515 | 423,483 | -3,032 |

Winner retention was 99.2891%; top-20 winner loss was JPY 0.

## Fold results

- 2023H1: +JPY 1,476
- 2023H2: +JPY 2,672
- 2024H1: -JPY 907
- 2024H2: +JPY 2,344

Positive-net folds: 3/4. DD-positive folds: 3/4.

## Breadth

- B02: +JPY 1,311
- F05: +JPY 4,274
- Long: -JPY 1,570
- Short: +JPY 7,155
- London: +JPY 2,295
- London/NY overlap: +JPY 418
- New York: JPY 0
- Tokyo: +JPY 2,872
- Positive / negative months: 9 / 4
- Largest positive month share: 20.5514%
- F05 positive-effect share: 76.5264% (binding limit 75%)
- Short positive-effect share: 100% (binding limit 75%)

## Resampling and concentration

- Event bootstrap 95% interval: -JPY 248.725 to +JPY 12,065.675
- Event bootstrap P(non-positive): 3.5%
- Date/session-aware bootstrap 95% interval: +JPY 396.975 to +JPY 10,806.3
- Date/session-aware P(non-positive): 1.7%
- Best affected event removed: +JPY 4,257 remains
- Top three affected-loss events removed: +JPY 1,780 remains

## Failed binding gates

1. `Long_delta_nonnegative`
2. `strategy_concentration_below_75pct`
3. `side_concentration_below_75pct`

## Stop-rule execution

No candidate freeze was created. Core implementation, Research/Core parity, Rakuten MT4 2023–2024, 2025H1, 2025H2, production, and live were not executed and are not authorized. This is a completed scientific failure, not a technical stop.
