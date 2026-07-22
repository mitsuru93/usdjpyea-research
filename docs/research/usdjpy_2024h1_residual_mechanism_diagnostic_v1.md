# USDJPY 2024 H1 Residual Mechanism Diagnostic v1

## Status

This report completes the next Stage S1 analysis under `usdjpy_validation_operating_contract_v3`.

It uses only accepted 2024 H1 evidence for mechanism development. It does not access new 2024 H2 evidence, does not execute a candidate on 2025 H1, and does not authorize MT4 implementation or H2 execution.

The purpose is to identify which loss paths remain materially untreated after the closed SC70/C240, S1, S2, S3 and Family C specifications.

## Evidence identity

- accepted 2024 H1 source Run: `29787357305`;
- accepted 2024 H1 source artifact: `8479048161`;
- source artifact digest: `sha256:e078758343995c8254244dd36385c93a61a7124cb5037beb458afdf5d0e208e5`;
- Entry-State Atlas v2 Run: `29884556860`;
- Entry-State Atlas v2 artifact: `8516049893`;
- Entry-State Atlas v2 artifact digest: `sha256:ee54d2608c38750776366c27bde03e046a44c6bebec6964f33f1f04b4f115981`;
- combined Atlas CSV SHA-256: `a9f78991fbf23cb5fb0af96b6b36fc4c3f9185e499a9ca44bdd3d33fcaa40efd`.

Closed-candidate H1 evidence used only for overlap and coverage accounting:

- S1 H1 removed entries: 11;
- S2 H1 changed positions: 12;
- S3 H1 removed entries: 20;
- Family C H1 changed positions: 24.

## Baseline

| Metric | 2024 H1 |
|---|---:|
| Closed trades | 428 |
| Net JPY | 22,797 |
| PF | 1.377415 |
| B02 closed / net | 97 / 9,554 |
| F05 closed / net | 331 / 13,243 |
| Q1 net | 8,730 |
| Q2 net | 14,067 |

## What the previous candidate families actually covered

The union of S1, S2, S3 and Family C affected 55 unique 2024 H1 trades. Pairwise overlap was low.

| Candidate pair | Exact affected-trade overlap |
|---|---:|
| S1 × S2 | 3 |
| S1 × S3 | 3 |
| S1 × Family C | 1 |
| S2 × S3 | 3 |
| S2 × Family C | 4 |
| S3 × Family C | 3 |

This confirms that the four mechanisms were mostly distinct. Their combined coverage was nevertheless concentrated in F05 P1 giveback-to-loss.

### Loss-path coverage by the union of prior candidates

| Strategy / path | H1 losing trades | H1 loss JPY | Prior-candidate affected trades | Affected loss JPY | Count coverage | Loss coverage |
|---|---:|---:|---:|---:|---:|---:|
| B02 P1 giveback-to-loss | 16 | 4,546 | 0 | 0 | 0.0% | 0.0% |
| B02 P2 minor-favourable-then-loss | 18 | 7,139 | 1 | 1,717 | 5.6% | 24.1% |
| B02 P3 never-profitable | 6 | 1,375 | 0 | 0 | 0.0% | 0.0% |
| F05 P1 giveback-to-loss | 44 | 16,210 | 22 | 11,195 | 50.0% | 69.1% |
| F05 P2 minor-favourable-then-loss | 66 | 14,889 | 5 | 2,432 | 7.6% | 16.3% |
| F05 P3 never-profitable | 41 | 16,244 | 6 | 3,935 | 14.6% | 24.2% |

### Residual population

After excluding the 55 trades touched by any prior candidate, the untreated population still contains:

- 38 P1 losses, JPY `-9,561`;
- 78 P2 losses, JPY `-17,879`;
- 41 P3 losses, JPY `-13,684`;
- 216 winners, JPY `+76,422`.

The next mechanism should therefore not be another broad P1 protection rule. The largest untreated research target is F05 P2/P3 early failure.

## Marked-path diagnosis

All snapshot values below are executable marked P/L at fixed post-entry M15 boundaries. Long positions use Bid and short positions use Ask. One pip at fixed 0.01 lot corresponds to JPY 10 in the accepted audit.

### F05 at 30 minutes

| Marked P/L at 30m | Trades | Final net JPY | Final winner rate | P1 | P2 | P3 |
|---|---:|---:|---:|---:|---:|---:|
| <= -20 pips | 10 | -4,481 | 0.0% | 0 | 2 | 8 |
| (-20, -10] | 35 | -4,719 | 22.9% | 4 | 6 | 17 |
| (-10, 0] | 122 | +3,720 | 51.6% | 12 | 30 | 16 |
| (0, 10] | 115 | +8,204 | 59.1% | 19 | 28 | 0 |
| (10, 20] | 37 | +5,458 | 81.1% | 6 | 0 | 0 |
| > 20 pips | 12 | +5,061 | 75.0% | 3 | 0 | 0 |

The cleanest descriptive separation occurs at the deep adverse tail. Every F05 trade at or below -20 pips after 30 minutes finished as a loser. The ten trades were distributed over all six H1 months and nine entry dates.

This is not yet a candidate approval. Closing immediately at the 30-minute marked value would improve the ten-trade aggregate by JPY 1,732, but two months would worsen because some trades recovered before their eventual loss.

### Persistence from 30 to 60 minutes

A second diagnostic asks whether an adverse state persists instead of using a single delayed stop.

The following rows are exploratory H1 counterfactuals. They are disclosed because they were inspected before the formal family preregistration. Formal gates, ranking and finalist limits are frozen separately before the formal evaluator output.

| 30m condition | 60m condition | Changed | Dates | Trigger months | Final winners | P2 / P3 | Delta JPY | Benefit / harm JPY | Positive / negative effect months | Ex-best-two JPY | Leave-one-month-out min JPY | Prior-candidate overlap |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| <= -15 | <= -5 | 17 | 15 | 6 | 1 | 3 / 13 | +2,416 | 3,469 / 1,053 | 5 / 1 | +780 | +869 | 4 |
| <= -15 | <= -10 | 15 | 13 | 5 | 0 | 3 / 12 | +2,072 | 2,968 / 896 | 4 / 1 | +436 | +525 | 3 |
| <= -15 | <= -15 | 12 | 10 | 4 | 0 | 3 / 9 | +2,051 | 2,843 / 792 | 3 / 1 | +415 | +504 | 3 |
| <= -20 | <= -5 | 10 | 9 | 6 | 0 | 2 / 8 | +1,868 | 2,438 / 570 | 5 / 1 | +504 | +694 | 4 |

The persistent condition is structurally different from all closed candidates:

- it does not suppress a new Entry from pre-entry shock or extension;
- it does not use a fixed intrabar stop;
- it does not require a prior profitable excursion;
- it does not use breakout-origin re-entry after MFE;
- it waits for two post-entry observations before declaring early failure.

The strongest qualitative finding is not one exact threshold. It is that **persistent early adverse state isolates F05 P2/P3 losses with little overlap with prior mechanisms**.

## Exposure-state attribution of the persistent adverse population

For the representative diagnostic `30m <= -15` and `60m <= -10`, the 15 affected trades consist of:

| Exposure state | P2 | P3 | Total |
|---|---:|---:|---:|
| same-direction stack | 2 | 9 | 11 |
| simultaneous same-direction | 1 | 0 | 1 |
| opposite overlap | 0 | 1 | 1 |
| standalone | 0 | 2 | 2 |

The mechanism is not reducible to a stack filter. Four of the fifteen trades are outside same-direction stack, and the previous Family B conditional-overlap grid produced no eligible H1 specification.

## Why B02 is not included in the next family

Equivalent B02 marked-path diagnostics did not produce a stable early-adverse improvement.

Examples:

- B02 30m <= -10 pips: 13 trades, exploratory delta JPY `-526`;
- B02 60m <= -15 pips: 14 trades, exploratory delta JPY `-775`;
- B02 240m <= -30 pips: eight trades, exploratory delta only JPY `+135`, with three negative-effect months and negative ex-best-two residual.

Including B02 would broaden the family without H1 evidence and would repeat the S2 problem of improving F05 while damaging B02.

## Mechanism decision

The next finite family will target F05 only and test two related but distinct mechanisms:

1. a single deep-adverse decision at the exact 30-minute checkpoint;
2. persistent adverse confirmation using both the exact 30-minute and 60-minute checkpoints.

The family is named `D_EARLY_FAILURE_PERSISTENCE`.

No exact candidate is selected by this report.

## Relationship to the 2025 H1 problem

The mechanism has a direct readiness thesis for the already-known adverse regime without using candidate-specific 2025 H1 execution:

- 2025 H1 deterioration included materially deeper early adverse paths;
- F05 accounted for the larger share of gross-loss deterioration;
- F05 P2/P3 severity was a major untreated component;
- the proposed mechanism exits only after adverse persistence, rather than blocking profitable continuation before entry;
- B02 remains unchanged.

This is a thesis, not validation. Any finalist remains locked from candidate-specific 2025 H1 execution until the period-role decision and preceding gate are fixed.

## Whether 2024 H2 should become an analysis period

No period-role change is made in this report.

There is a legitimate reason to reconsider the role of H2: the current promising mechanism is sparse, with approximately 10 to 17 H1 triggers depending on the cell. Combining 2024 H1 and H2 would materially improve parameter identifiability and regime breadth.

There is also a cost: changing H2 into development removes the current intermediate binding block. In that design, 2025 H1 would be a known adverse stress gate rather than a pristine holdout, and 2025 H2 would become the only genuinely later final block.

The decision is deferred until the formal H1 family evaluation. H2 reclassification will be considered only if at least one of the following is observed:

1. no formal H1 cell passes;
2. an eligible cell has fewer than 20 changed positions;
3. adjacent parameter cells remain outcome-equivalent or ranking-unstable;
4. ex-best-two or leave-one-month-out residual is less than 25% of total H1 improvement;
5. the selected rule changes materially depending on the ranking metric.

Until that decision, the current period boundaries remain unchanged and no new H2 evidence is accessed.

## Next action

Run the preregistered 12-cell `D_EARLY_FAILURE_PERSISTENCE` H1 research evaluator against the immutable Entry-State Atlas v2 artifact. The formal evaluation must report parameter equivalence classes, prior-candidate overlap, path fidelity, concentration, month breadth and all standard H1 gates before any MT4 implementation.
