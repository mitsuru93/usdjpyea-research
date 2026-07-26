# USDJPY B02/F05 Portfolio Loss-Cluster Study Phase 1 — Canonical Result

Updated: 2026-07-26

## Decision

Status: `PHASE1_COMPLETE_ONE_PHASE2_RESEARCH_CANDIDATE_NO_IMPLEMENTATION`

Phase 1 found **one narrow research candidate**:

- `SESSION_LOSS_CAP_2`
- prospective rule: do not admit a new B02/F05 entry after two realized losses have already occurred in the same UTC session key
- authorization: **Phase 2 confirmation only**
- MT4 implementation, 2025H1 access and production use: **not authorized**

No broad exposure cap is supported. Concurrent positions, same-direction overlap and B02/F05 overlap are not generally defective; in the canonical population they are associated with most of the profitable portfolio exposure.

## Source authority and lineage

- Research main at study start: `57dded3efa003c1644e4bae49a239d7a21b21429`
- Core main at study start: `aca45ab891d9a6da272b5111a99142d99e874929`
- successful scientific execution SHA: `dcb8837c68abce39fbf70411d356878d871741d4`
- canonical trade ledger SHA-256: `98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca`
- canonical state ledger SHA-256: `2caddc38cdb16ce7504fe1e3b625f8425ccc6f7d579d02590f9ee92bbf013eda`
- source folds: 2023H1, 2023H2, 2024H1, 2024H2
- 2025H1/H2 accessed by this study: false
- new MT4 execution: false

The 2023 source was transformed to the immutable historical-2024 clock contract. The 2024 authority was not rewritten. Timestamps are UTC. Lot size is fixed at 0.01 in the source contract and normalized exposure is 1.0 per trade.

MFE/MAE and portfolio mark-to-market are common-M15 observations. They are not represented as raw-tick extrema for 2023. The shock state is likewise a causal completed/open-M15 proxy, not raw-tick shock authority.

## Identity audit

| Dimension | Count |
|---|---:|
| Total trades | 1,882 |
| B02 | 429 |
| F05 | 1,453 |
| 2023H1 | 488 |
| 2023H2 | 472 |
| 2024H1 | 428 |
| 2024H2 | 494 |
| Long | 1,166 |
| Short | 716 |
| Winners | 966 |
| Losers | 916 |
| Duplicate trade IDs | 0 |
| Identity mismatches | 0 |
| Entries with an already-open position | 1,400 |
| Entries with B02/F05 cross-strategy overlap | 1,039 |

Baseline:

- gross profit: ¥426,515
- gross loss: ¥374,888
- net: ¥51,627
- PF: 1.1377
- maximum realized DD: ¥40,487
- maximum M15-snapshot DD: ¥42,660

## Portfolio event contract

The primary portfolio event joins trades when the next entry begins before the current event has ended plus a fixed 60-minute gap. Sensitivity windows are 15, 30 and 60 minutes.

The event ledger separately identifies:

- standalone entries
- concurrent exposure
- same-direction, opposite-direction and mixed overlap
- B02/F05 overlap
- entry clusters
- loss clusters
- drawdown additions
- session loss chains
- shock/post-shock adjacency
- recovery interference

The 60-minute definition produced 435 events; 245 contained at least two losing trades.

## Main finding: concentration is real, but overlap is not generally harmful

Loss-cluster events contain ¥325,386 of gross loss, or 86.8% of all gross loss. However, they also contain ¥242,288 of gross profit. Their net is -¥83,098. The perfect-loss-cluster avoidance value of +¥113,792 is therefore an **oracle upper bound**, not a deployable rule.

The high loss coverage is stable to event-window definition:

| Gap | Events | Events with 2+ losses | Gross loss in those events |
|---:|---:|---:|---:|
| 15m | 462 | 248 | ¥318,325 |
| 30m | 452 | 247 | ¥321,952 |
| 60m | 435 | 245 | ¥325,386 |

Trade-level comparisons contradict a blanket de-clustering policy:

| Entry state | Trades | Net | PF |
|---|---:|---:|---:|
| Standalone within 60m | 325 | -¥25,117 | 0.717 |
| Non-standalone | 1,557 | ¥76,744 | 1.268 |
| Position count after entry = 1 | 482 | -¥9,052 | 0.922 |
| Position count after entry = 2 | 502 | ¥19,136 | 1.185 |
| Position count after entry >= 3 | 898 | ¥41,543 | 1.267 |

After stratifying by fold, strategy and side, the clustered-minus-standalone loss-rate difference was -6.25 percentage points; permutation p=0.0385. This is descriptive association, not proof that adding positions causes profit, but it rejects “clustered exposure is generally bad.”

## Same-direction and B02/F05 overlap

| Exposure state at entry | Trades | Net | PF |
|---|---:|---:|---:|
| No overlap | 482 | -¥9,052 | 0.922 |
| Same-direction only | 1,154 | ¥53,360 | 1.253 |
| Opposite-direction only | 133 | ¥3,936 | 1.124 |
| Mixed same/opposite | 113 | ¥3,383 | 1.208 |
| B02/F05 overlap | 1,039 | ¥38,831 | 1.216 |
| No cross-strategy overlap | 843 | ¥12,796 | 1.066 |

Same-direction overlap was negative in 2023H1 but positive in the other three folds. This regime asymmetry means a universal same-direction cap is not portable. B02/F05 exclusivity reduces DD but removes too much profitable exposure.

B02/F05 events also depend on sequence:

- B02-leading cross-strategy events: -¥13,063
- F05-leading cross-strategy events: +¥68,868
- simultaneous first entries: +¥27,560

This sequence result is descriptive and was not used to introduce a new routing threshold in Phase 1.

## Drawdown additions

Most entries occurred below the historical realized-equity peak: 1,829 of 1,882 entries. This makes “entry during any drawdown” too broad to be informative.

The preregistered drawdown block families reduced DD only by eliminating nearly all exposure:

- `DRAWDOWN_BLOCK_500JPY`: M15 DD reduction ¥40,455
- net improvement: -¥53,355
- winner retention: 0.2%

Therefore drawdown-aware blocking is rejected in its tested broad form. Drawdown state alone is not an admissible candidate.

Recovery interference was identified only once under the fixed M15 definition, so no inference or rule is permitted from that cell.

## Session loss chains

The decisive prospective state is the number of **already realized losses in the same session** at a new entry:

| Prior same-session realized losses | Entries | Net | PF |
|---:|---:|---:|---:|
| 0 | 1,706 | ¥58,167 | 1.177 |
| 1 | 149 | -¥955 | 0.975 |
| 2+ | 27 | -¥5,585 | 0.352 |

The 27 entries after two prior session losses earned only ¥3,032 gross profit and lost ¥8,617. This is distinct from labeling final losing chains after outcomes; it is available prospectively at entry time.

## Shock adjacency

The common-M15 volatility state did not justify a shock exposure cap:

| State | Trades | Net | PF |
|---|---:|---:|---:|
| Contraction | 26 | -¥624 | 0.858 |
| Normal | 414 | ¥19,250 | 1.273 |
| Expansion | 776 | -¥117 | 0.999 |
| Shock | 491 | ¥33,359 | 1.304 |
| Post-shock | 175 | -¥241 | 0.994 |

`SHOCK_COOLDOWN_60M` lost ¥33,118, retained only 57.1% of winner profit and was positive in one fold. Shock/post-shock exposure control is rejected under this M15 contract. Raw-tick shock research would require a separately declared year-complete authority.

## Counterfactual results

### Phase 2 research candidate: SESSION_LOSS_CAP_2

- removed trades: 27
- avoided gross loss: ¥8,617
- lost gross profit: ¥3,032
- net improvement: ¥5,585
- candidate net: ¥57,212
- candidate PF: 1.1562
- realized DD reduction: ¥3,717
- M15-snapshot DD reduction: ¥3,717
- winner retention: 99.29%
- top-20 winner loss: ¥0
- positive net folds: 3/4
- DD-positive folds: 3/4
- positive-effect months: 9
- negative-effect months: 4
- largest positive month share: 20.6%
- event-bootstrap 95% interval: -¥249 to ¥12,066
- bootstrap probability of non-positive effect: 3.5%

Fold results:

| Fold | Net improvement | DD reduction | Winner retention |
|---|---:|---:|---:|
| 2023H1 | ¥1,476 | ¥1,023 | 99.84% |
| 2023H2 | ¥2,672 | ¥2,241 | 99.40% |
| 2024H1 | -¥907 | ¥213 | 98.65% |
| 2024H2 | ¥2,344 | ¥0 | 99.20% |

Strategy breadth is positive:

- B02 delta: +¥1,311
- F05 delta: +¥4,274

Side breadth is not yet sufficient:

- Long delta: -¥1,570
- Short delta: +¥7,155

Session effects:

- Tokyo: +¥2,872
- London: +¥2,295
- London/NY overlap: +¥418
- New York: ¥0

Therefore the candidate is not implementation-ready. Phase 2 must confirm that the effect is not a sparse Short-side/session artifact.

### Secondary diagnostic only: LOSS_COOLDOWN_60M

- net improvement: +¥2,016
- M15 DD reduction: ¥3,914
- winner retention: 97.18%
- positive folds: 2/4
- event-bootstrap probability non-positive: 32.7%

It does not advance.

### DD-only trade-offs, not candidates

Formal ranking places some broad controls above others because they reduce DD, but they are economically rejected:

| Family | Representative | Net delta | M15 DD reduction | Winner retention |
|---|---|---:|---:|---:|
| B02/F05 exclusivity | `B02_F05_EXCLUSIVE` | -¥12,422 | ¥11,837 | 68.7% |
| Adaptive sizing | `HALF_SIZE_DD_1000` | -¥27,912 | ¥21,039 | 53.2% |
| Same-direction cap | `SAME_DIRECTION_CAP_3` | -¥11,541 | ¥6,273 | 81.5% |
| Max concurrent | `MAX_CONCURRENT_1` | -¥52,713 | ¥17,438 | 34.2% |
| Broad DD block | `DRAWDOWN_BLOCK_500JPY` | -¥53,355 | ¥40,455 | 0.2% |
| Entry cooldown | `ENTRY_COOLDOWN_60M` | -¥23,377 | ¥2,058 | 76.6% |
| Shock cooldown | `SHOCK_COOLDOWN_60M` | -¥33,118 | ¥5,283 | 57.1% |

## Candidate family ranking

The raw formal ranking is retained in the artifact. Scientific interpretation is:

1. `session_loss_cap` — advance `SESSION_LOSS_CAP_2` to Phase 2 confirmation only.
2. `loss_cooldown` — diagnostic sensitivity only; not portable enough.
3. all other families — reject or retain only as DD-versus-profit trade-off references.

There are not three implementation candidates. Reporting the formal second and third rows as recommendations would ignore their negative net and severe winner damage.

## Impact Atlas relation

Impact Atlas Phase 1 ranked portfolio exposure control below entry establishment, market-state routing and profit lifecycle despite its large oracle loss coverage. This Phase 1 study explains why:

- portfolio loss clusters cover a large share of gross loss;
- the same clusters also carry much of the portfolio's gross profit;
- broad exposure controls reduce DD by destroying winners;
- only the narrow prospective session-loss state shows an acceptable preliminary trade-off.

Thus this study complements rather than replaces Impact Atlas. It does not alter Entry, Exit, SL, TP, failed reclaim, structural SL or market-state routing research.

## Expected 2025H1 impact

2025 was not accessed or used for candidate selection. The development estimate is modest: +¥5,585 net and -¥3,717 M15 DD from only 27 entries.

Against the known adverse 2025H1 gate context, this magnitude should be treated as loss compression, not as evidence that the gate will pass. It may not be sufficient by itself. The only valid path is:

1. freeze an exact Phase 2 protocol on 2023/2024;
2. confirm `SESSION_LOSS_CAP_2` unchanged;
3. prove Research-to-MT4 parity;
4. then execute one unchanged 2025H1 binding test.

## Failures and recurrence prevention

### Run 30203423794

Classification: `TECHNICAL_INCOMPLETE_NO_RESULT`.

- source verification and 1,882-trade materialization passed;
- evaluator failed after candidate computation because `session_loss_chain_size` was merged twice and renamed to suffixed columns;
- no result package or artifact was created;
- repair reused the existing grouping column, asserted equality across ledgers and added a synthetic regression preflight.

The unchanged repaired run was executed once.

### Evidence package v1

All scientific files matched their individual hashes, but `PACKAGE_SHA256SUMS` included itself and its self-row could not match after write completion.

The immutable original is retained. Release `usdjpy-portfolio-loss-cluster-phase1-v1-r1` preserves scientific files and regenerates the checksum list without self-reference. Full `sha256sum -c` readback passed.

## Evidence

- preregistration PR: #296
- preregistration merge: `a56c53dad75d083b9f2665faa01ebcfb3481fa35`
- failed scientific Run: `30203423794`
- technical repair PR: #301
- repair merge / successful execution SHA: `dcb8837c68abce39fbf70411d356878d871741d4`
- successful scientific Run: `30204173630`
- source artifact: `8632649725`
- source artifact digest: `sha256:eb9e30b2e3cee27dddfaa354bdc5d460ed8e9e8845943dc3086d7daf575b8934`
- result receipt Issue: #304
- evidence repair PR: #305
- evidence repair merge: `249e38dd5e7ff3a536955eff772eacbab6b03009`
- evidence repair Run: `30204835214`
- corrected artifact: `8632740782`
- corrected artifact digest: `sha256:22bda1a44494a57a9a236a9900e2ddf3da7900dfb7b4e6b8fa06b86a5df828c1`
- corrected Release: `usdjpy-portfolio-loss-cluster-phase1-v1-r1`
- corrected Release asset SHA-256: `32ae25199256ca83e10a6a5da2cb9236f90ce0f41ebd797a3bd205b5b299bada`
- archive receipt Issue: #306

## Next action

Preregister Phase 2 confirmation of `SESSION_LOSS_CAP_2` only. Keep the exact session definition and threshold unchanged. Require:

- net improvement and DD reduction in at least 3/4 folds;
- winner retention >=99%;
- no top-winner loss;
- event-level bootstrap support;
- side, strategy, session and month breadth;
- unchanged 2025/MT4 firewall.

No production EA implementation is authorized in Phase 1.
