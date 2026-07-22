# USDJPY 2024 Full-Year Recovery-Path Diagnostic v1

## Status

This report completes the `FULL_YEAR_RECOVERY_PATH_DIAGNOSIS` stage recorded in
`usdjpy_research_candidate_registry_v5`.

It uses only 2024 development evidence. It does not access candidate-specific
2025 H1 or 2025 H2 evidence and does not authorize MT4 execution.

The analysis is outcome-informed by design: 2024 H1 and H2 are development
periods under `usdjpy_period_role_policy_v4`. Exploratory counterfactuals were
inspected before the finite successor family was frozen. Therefore this report
does not claim independent validation. The first binding test remains 2025 H1.

## Evidence identity

- Research main before this report: `d50662fdfa0802d1ba30fa8cbc4d31b7f8f87f5b`.
- H1 Entry-State Atlas Run: `29884556860`.
- H1 artifact: `8516049893`.
- H1 artifact digest:
  `sha256:ee54d2608c38750776366c27bde03e046a44c6bebec6964f33f1f04b4f115981`.
- H1 Atlas CSV SHA-256:
  `a9f78991fbf23cb5fb0af96b6b36fc4c3f9185e499a9ca44bdd3d33fcaa40efd`.
- H2 source Rakuten MT4 Run: `29895387329`.
- H2 source artifact: `8519879009`.
- H2 artifact digest:
  `sha256:1341850d4530d9bb8ea6522aefaa796dd5ea70abc698913633cb523f55d51981`.
- H2 baseline audit SHA-256:
  `a5a871d7105c6e68548e804c9ab517ee6bc0b08553474b158799f47ebd32edcd`.
- Unified 2024 population rows: `922`.
- Unified population SHA-256: `792bd3efe830e4f22ce807c8dd7c640bb66f985d65b5ea3988d7c9abb83da380`.
- Recovery diagnostic rows: `63`.
- Recovery diagnostic SHA-256: `bef4bffd5660f9ab28ccb78e302c2fcde6689b8e6cf8430fbaffcc6caa4e6462`.

## Population under diagnosis

The closed D-family leading condition was used only as a diagnostic population:

- F05;
- 30-minute executable marked P/L at or below -15 pips;
- 60-minute executable marked P/L at or below -5 pips.

It identified 63 positions:

- H1: 17;
- H2: 46;
- P3 never profitable: 39;
- P1/P2 other final losses: 15;
- late-recovery non-loss positions: 9.

The question was not whether the D rule should be reopened. D remains closed.
The question was what observable state separated permanent failure from the
nine positions that were adverse for the first hour and later recovered.

## Recovery-path timing

Median executable marked P/L by final path:

| Final path | 30m | 60m | 90m | 120m | 240m |
|---|---:|---:|---:|---:|---:|
| P3 never profitable | -23.5 | -24.2 | -31.2 | -33.5 | -44.2 |
| Late-recovery non-loss | -23.2 | -17.2 | -12.9 | -15.7 | +9.2 |
| Other loss | -20.3 | -22.8 | -27.1 | -25.2 | -33.6 |

At 30 minutes the P3 and late-recovery groups were almost indistinguishable.
At 60 minutes there was still substantial overlap. Separation began between
60 and 90 minutes and became economically clear by 240 minutes.

This rejects another uniform 30- or 60-minute pip threshold. The additional
information is the portfolio state at entry and whether the position starts to
recover after the 60-minute checkpoint.

## Entry-exposure state is the primary separator

| Entry exposure state | P3 | Late recovery | Other loss |
|---|---:|---:|---:|
| standalone | 6 | 0 | 2 |
| opposite overlap | 3 | 0 | 1 |
| mixed overlap | 3 | 0 | 1 |
| same-direction stack | 27 | 7 | 10 |
| simultaneous same direction | 0 | 2 | 1 |

All nine late-recovery positions occurred with unopposed same-direction
support:

- seven in an existing same-direction stack;
- two in simultaneous same-direction exposure.

There were zero late-recovery positions among the 16 standalone,
opposite-overlap, or mixed-overlap cases.

If the original -15/-5 condition had closed only those 16 unsupported cases at
60 minutes, the 2024 exploratory effect would have been:

- total delta: +5,785 JPY;
- benefit: +6,163 JPY;
- harm: 378 JPY;
- final winners affected: zero.

By contrast, a uniform 60-minute close on the 47 same-direction-supported
positions produced -4,120 JPY because all nine late-recovery positions were in
that state.

## Mechanism interpretation

The data supports two different economic states.

### Unsupported or conflicted early failure

`standalone`, `opposite_overlap`, and `mixed_overlap` positions have no
unopposed same-direction campaign supporting the entry. When such a position
is deeply adverse at 30 minutes and remains adverse at 60 minutes, the observed
2024 sample contains only final losses.

### Same-direction-supported drawdown

`same_direction_stack` and `simultaneous_same_direction` positions are part of
a continuing directional campaign. An adverse first hour is not sufficient to
declare failure. These positions need a later checkpoint. The earliest useful
additional checkpoint in the available M15 evidence is 90 minutes.

The supported position is treated as failed only when:

- it remains materially adverse at 90 minutes; and
- it has not recovered from its 60-minute marked state.

This is not an entry filter, stack cap, or uniform stop. It is a
state-adaptive post-entry exit.

## Exploratory state-adaptive counterfactual

The strongest stable exploratory specification was:

1. Initial condition:
   - 30m P/L <= -15 pips;
   - 60m P/L <= -5 pips.
2. Unsupported state:
   - close at 60 minutes.
3. Same-direction-supported state:
   - wait until 90 minutes;
   - close when 90m P/L <= -15 pips;
   - and 90m P/L has not improved from 60m.

Exploratory 2024 result:

| Metric | H1 | H2 | Full 2024 |
|---|---:|---:|---:|
| Changed positions | 11 | 26 | 37 |
| Net delta | +2,288 JPY | +5,770 JPY | +8,058 JPY |
| Candidate PF | 1.431644 | 1.428159 | 1.429420 |
| Ex-best-two-date delta | +755 JPY | +3,643 JPY | +5,862 JPY |
| Leave-one-month-out minimum | +999 JPY | +3,527 JPY | +5,815 JPY |

Additional distribution:

- 36 entry dates;
- 11 active months;
- 10 positive-effect months;
- one negative-effect month;
- all four calendar quarters positive;
- benefit 10,045 JPY;
- harm 1,987 JPY;
- one final winner affected;
- winner harm 273 JPY;
- final-loser share 97.3%;
- P2/P3 share 83.8%;
- prior-candidate union overlap 35.1%;
- largest positive date share of benefit 11.7%;
- top-two positive date share of benefit 21.9%.

The single harmed winner is not used to add an exemption. Adding a
winner-specific shock, extension, or stack-ordinal exception after inspecting
that row is prohibited.

## Distinction from prior families

### Family B

Family B was a dynamic new-entry block. It suppressed F05 before opening based
on stale stacks, high stack ordinal, or opposite exposure.

Family E leaves every entry unchanged. It acts only after a position has
actually demonstrated 30-to-60-minute adverse persistence. Entry exposure
state changes the decision checkpoint, not entry acceptance.

### Family D

Family D used the same 30/60 pip condition uniformly. Family E explains the D
failure: the same-direction-supported subset contained all late-recovery
positions. Family E separates unsupported exits at 60 minutes from supported
positions deferred to 90 minutes.

### S1, S2, S3, and Family C

The successor does not use shock windows, degraded-shock repair, ATR extension,
MFE arming, or breakout-origin re-entry. Its changed-trade overlap with the
prior-candidate union is 35.1% for the leading exploratory specification.

## Decision

A new finite family is justified:

`E_STATE_ADAPTIVE_RECOVERY_EXIT`.

The canonical grid contains 63 specifications:

- nine unsupported-only 60-minute specifications;
- 54 adaptive 60/90-minute specifications.

The grid, gates, ranking, equivalence handling, and prohibition on 2025 access
are frozen in:

`configs/research/usdjpy_state_adaptive_recovery_exit_2024_prereg_v1.json`.

No exact candidate is authorized until all 63 cells are reproduced under that
contract. No direct MT4 execution or 2025 access is authorized by this report.
