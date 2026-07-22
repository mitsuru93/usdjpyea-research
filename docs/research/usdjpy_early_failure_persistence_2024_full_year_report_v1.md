# USDJPY D Early-Failure Persistence — 2024 Full-Year Result v1

## Formal decision

**CLOSED — no full-year eligible specification.**

The preregistered 12-cell family was evaluated without expanding the grid after 2024 H2 access. None of the 12 specifications passed the separate H1, H2 and full-year development requirements.

No exact D-family candidate is frozen. The family does not proceed to MT4 implementation or either 2025 gate.

## Why H2 was changed to analysis

The H1 leading cell passed every H1 gate but changed only 17 positions. That was insufficient to identify the exact `-15 pips at 30m / -5 pips at 60m` threshold.

After period policy v4 reclassified H2 as development, the same unchanged 12-cell grid was evaluated over the second half of 2024. This produced a decisive result that a one-shot H2 test of only the H1 leader would not provide: **all 12 early-adverse specifications had negative H2 deltas**.

## H2 Atlas reconciliation

The accepted H2 baseline audit was reproduced as:

- opened positions: 494;
- closed positions: 493;
- complete marked net: 38,109円;
- B02: 102 positions / 15,627円;
- F05: 392 positions / 22,482円.

The portfolio-snapshot method was first checked against all 428 H1 trades. It reproduced every H1 `pips_30m` and `pips_60m` value with only floating-point error below `3.2e-12`.

Two H2 entries had no exact 30-minute or 60-minute snapshot because the source audit skipped those bar times. They were retained in the Atlas with null checkpoint values and could not trigger an exact-checkpoint rule.

## Result of the H1 leading cell in H2

Rule:

> F05 only; at 60 minutes close if the 30-minute result was at or below −15 pips and the 60-minute result remains at or below −5 pips.

| Period | Changed | Delta | Ex-best-two | Leave-one-month-out minimum |
|---|---:|---:|---:|---:|
| 2024 H1 | 17 | **+2,416円** | +780円 | +869円 |
| 2024 H2 | 46 | **−751円** | −2,883円 | −3,756円 |
| Full 2024 | 63 | +1,665円 | — | — |

The full-year aggregate remained positive only because H1 was strong. The rule did not generalize to H2 and failed the preregistered cross-half requirements.

## What happened in H2

Among the 46 H2 positions triggered by the H1 leading rule:

- 38 ultimately lost;
- 8 ultimately won;
- 26 were P3 never-profitable;
- 9 were P1 giveback-to-loss;
- 3 were P2 minor-favourable-then-loss.

### Effect by final path

| Final path | Changed | Effect |
|---|---:|---:|
| P1 giveback-to-loss | 9 | +1,579円 |
| P2 minor-favourable-then-loss | 3 | +678円 |
| P3 never-profitable | 26 | **+7,123円** |
| Winner | 8 | **−10,131円** |

The original H1 mechanism was real: it continued to reduce P3 losses. The failure was that H2 contained a new competing path—positions that were materially adverse throughout the first hour but later recovered strongly and finished profitable.

The saved losses totalled 10,768円, while the sacrificed later recovery totalled 11,519円.

### Monthly effect

| Month | Effect |
|---|---:|
| July | +1,572円 |
| August | **−6,183円** |
| September | +3,005円 |
| October | +40円 |
| November | −232円 |
| December | +1,047円 |

The largest damage occurred on entry dates August 2 and August 5, totalling −8,127円. These were not ordinary small recoveries; several initially adverse short positions later reached very large favourable excursions and closed as substantial winners.

## All 12 specifications

Every cell had a negative H2 delta.

- best H2 delta: −751円;
- worst H2 delta: −5,736円;
- full-year eligible cells: zero;
- parameter-equivalent cells: zero;
- grid expansion after H2: none.

Tightening the 30-minute adverse threshold or requiring a deeper 60-minute loss reduced the number of trades but did not solve the late-recovery winner problem. Therefore this is not a threshold-selection issue inside the D family.

## Research conclusion

The statement

> “F05 is still materially adverse after one hour”

is not sufficient to distinguish permanent entry failure from temporary adverse movement.

The next research question is narrower:

> **Which entry-state or post-entry recovery features distinguish persistent P3 failure from first-hour adverse positions that later recover strongly?**

Potential diagnostic dimensions include:

- recovery slope after the 60-minute checkpoint;
- position relative to the breakout origin at later checkpoints;
- pre-entry extension and path efficiency;
- same-direction stack versus simultaneous entry state;
- whether adverse movement is isolated or part of a high-volatility repricing episode.

These are diagnostic questions only. No new candidate grid is authorized until the full-year mechanism analysis is completed and compared with all closed candidate families.
