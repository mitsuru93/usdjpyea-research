# EURUSD H1-derived v2 / reusable fixed 2024 H2 — local reproduction v1

Created: 2026-07-20 JST

## Scope

This result was generated with the committed v2 candidate protocol and runner against the byte-verified canonical EURUSD 2024 annual source ZIP.

- Development and modification source: 2024-01-01 through 2024-06-30.
- Permanent fixed validation: 2024-07-01 through 2024-12-31.
- H2 is reusable across iterations and has no consumed or retired state.
- Candidate definitions were selected from H1 and frozen before H2 evaluation.
- The formal GitHub Actions run remains the independent execution receipt and must reproduce these rows.

## H1 candidate lock

The H1 gate retained five v2 candidates:

1. `F_v2_z72_1p5_mean_target_0p5_max12`
2. `F_v2_z72_1p5_mean_target_0p25_max12`
3. `F_v2_z72_1p5_mean_target_0p0_max12`
4. `H_v2_hier_48x12_24x6_fixed`
5. `H_v2_hier_48x12_24x6_midpoint`

A staged-exit variants did not pass the H1 development gate. The z=2.0 plus RSI-confirmation variants generated only 17 H1 trades and failed the registered minimum-trade gate. The 25% re-entry-depth H candidate did not pass the H1 gate.

## Fixed H2 result

### Final pass: z-score exit at |z| = 0.5

Candidate: `F_v2_z72_1p5_mean_target_0p5_max12`

- Entry: completed H1 z-score over 72 closes reaches ±1.5, with ER(24) <= 0.35; enter next H1 open in the mean-reversion direction.
- Exit: first completed H1 close that returns to z >= -0.5 for a long or z <= +0.5 for a short; maximum 12 H1 bars.
- H1: 90 trades, average +3.676027 pips, PF 1.510002, five positive months, severe-cost PF 1.180314.
- H2: 114 trades, average +1.834211 pips, total +209.100000 pips, PF 1.185323, three positive months.
- Full 2024: 204 trades, average +2.646776 pips, total +539.942396 pips, PF 1.303849, eight positive months, severe-cost PF 1.045614.
- Decision: pass.

### Final pass: z-score exit at |z| = 0.25

Candidate: `F_v2_z72_1p5_mean_target_0p25_max12`

- Entry: same as the 0.5 candidate.
- Exit: first completed H1 close that returns to z >= -0.25 for a long or z <= +0.25 for a short; maximum 12 H1 bars.
- H1: 90 trades, average +5.018249 pips, PF 1.696219, six positive months, severe-cost PF 1.344661.
- H2: 112 trades, average +1.485714 pips, total +166.400000 pips, PF 1.146757, three positive months.
- Full 2024: 202 trades, average +3.059616 pips, total +618.042396 pips, PF 1.346717, nine positive months, severe-cost PF 1.086775.
- Decision: pass.

### Rejected after H2

- `F_v2_z72_1p5_mean_target_0p0_max12`: H2 PF 1.095034 but only two positive H2 months; fail.
- `H_v2_hier_48x12_24x6_fixed`: H2 average -4.409960 pips and PF 0.625812; fail.
- `H_v2_hier_48x12_24x6_midpoint`: H2 average -2.890211 pips and PF 0.746705; fail.

## MT4 handoff

The two passing F candidates are handed to `mitsuru93/usdjpyea-core` with the same candidate IDs. The MT4 diagnostic uses:

- dedicated EURUSD 2024 HST files derived from canonical public Bid OHLC;
- Rakuten server time GMT+2/GMT+3 with the 2024 U.S. DST rule;
- EURUSD H1, model 0;
- fixed spread 6 points = 0.6 pips;
- MetaEditor compilation and Strategy Tester execution on `onamae-mt4-ui-01`;
- audit CSV comparison against the Research H2 trade counts and metrics.

MT4 platform P/L is reported separately because the Research evaluation uses canonical mid bars and `max(0.6 pips, public entry spread)` while MT4 uses Bid HST and a fixed 6-point spread.
