# USDJPY B02/F05 Impact Atlas Phase 1 — result v1

Updated: 2026-07-26

## Status

`PHASE1_DIAGNOSIS_COMPLETE_NO_CANDIDATE_AUTHORIZATION`

Phase 1 has completed on the canonical 2023H1, 2023H2, 2024H1 and 2024H2 B02/F05 population. No 2025 outcome, MT4 execution, candidate selection, EA implementation or production authorization was used.

## Source authority and lineage

- canonical trade ledger: `usdjpy_b02_f05_source_trade_ledger_v2.csv`
- trade ledger SHA-256: `98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca`
- canonical path/state ledger: `usdjpy_b02_f05_entry_exit_state_ledger_v2.csv.gz`
- state ledger SHA-256: `2caddc38cdb16ce7504fe1e3b625f8425ccc6f7d579d02590f9ee92bbf013eda`
- state rows: 68,955
- source authorities were rematerialized from the accepted historical Release package and verified against frozen SHA-256 identities.

## Population

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

## Main loss structure

The largest directly observed admission-side population is the Entry-establishment failure population. Its perfect-avoidance upper bound is ¥218,465, covering 58.3% of total gross loss. This is an outcome-defined upper bound, not a deployable filter; winner damage is not zero for a future decision-time rule merely because the diagnostic cohort contains losers.

Market-state variation remains economically important. Both B02 and F05 are weak in 2023H1 and improve later, which is inconsistent with a permanently bad strategy side or a single local Entry variable. However, the canonical path ledger does not contain complete native H1/H4 swing-state episodes. The Phase 1 market-state table therefore uses entry-time M15 state proxies and cannot authorize a router.

Profit lifecycle and portfolio exposure have larger gross-loss coverage, but both intersect substantial winner profit. Their oracle upper bounds cannot justify blanket termination, stack-count suppression or concurrency bans.

## Fold and side breadth

2023H1 is the common weak fold:

- B02 total: -¥14,381
- F05 total: -¥11,671
- B02 Short: -¥14,021
- F05 Long: -¥143
- F05 Short: -¥11,528

Later-fold behavior is materially different. In 2024H2 every strategy/side cell is positive. A fixed side exclusion is therefore not portable. The evidence is more consistent with state-dependent permission and post-Entry establishment quality.

## Raw diagnostic bounds

| Program | Impact upper bound | Gross-loss coverage | Winner-damage upper bound | Net upper bound | Key limitation |
|---|---:|---:|---:|---:|---|
| Entry establishment | ¥218,465 | 58.3% | not yet measurable for a prospective rule | ¥218,465 diagnostic only | cohort is outcome-defined |
| Market-state routing | ¥206,188 | 55.0% | ¥93,833 | ¥112,355 | native H1/H4 episodes missing |
| Profit lifecycle | ¥279,001 | 74.4% | ¥174,445 | ¥104,556 | high winner exposure |
| Portfolio exposure | ¥325,386 | 86.8% | ¥242,288 | ¥83,098 | simple suppression would damage winners |
| Complementary strategies | ¥112,466 | 30.0% | unknown | oracle only | no counter-strategy fills |
| Local structural exit | ¥156,423 | 41.7% | ¥85,303 | ¥71,120 | broad atlas already closed |

## Final research-resource ranking

The workflow also records the preregistered formula index. That index is not controlling because an unmeasured winner-damage denominator artificially favors outcome-defined or opportunity-only programs. Considering raw impact, fold breadth, causal clarity, data authority, implementability and winner damage, the final Phase 1 research-resource ranking is:

1. **Entry establishment**
2. **Market-state strategy routing**
3. **Profit lifecycle**
4. **Portfolio exposure control**
5. **Complementary strategies**
6. **Local structural exit**

## Next concrete hypothesis

`ENTRY_ESTABLISHMENT_PHASE2_V1`

Freeze a small mechanism-led set of decision-time observables that distinguish:

- immediate follow-through;
- delayed establishment;
- failed establishment;
- false breakout / non-expansion;
- adverse-first recovery;
- signal expiration.

Evaluate the unchanged definitions independently across all four folds, B02/F05 and Long/Short. The primary endpoint is avoidable loss after actual winner damage, not diagnostic oracle coverage. Market-state routing proceeds in parallel only as source enrichment for native H1/H4 episodes; it must not be combined with Entry changes in the same candidate.

## Relative position of local SL research

Local structural Exit is sixth. Broad structural-SL families remain closed. `F05_FAILED_RECLAIM_BASIC_V1` remains a narrow supporting candidate with historical Research/raw-Tick support, pending unchanged evaluation on accepted 2025 raw Bid/Ask Tick data. It does not determine the Impact Atlas priority.

## 2025H1 gate implication

Phase 1 does not estimate a reliable realized 2025H1 delta. The largest historical diagnostic capacity lies above local SL—in establishment and state permission—but the reported values are upper bounds. A credible expected gate contribution can only be estimated after a prospective Phase 2 rule demonstrates four-fold portability and measured winner retention. No 2025 information was used to select this direction.

## Limitations and unresolved items

- native H1/H4 market-state episodes are not yet joined to the canonical trade ledger;
- shock and announcement context is incomplete in this population;
- portfolio-event proximity uses a deterministic 60-minute grouping and needs sensitivity analysis;
- complementary strategies were not simulated;
- prospective early-detection bounds remain to be measured;
- no EA or MT4 implementation is authorized.

## Execution evidence

- PR: `#286`
- successful Phase 1 run: `30199879517`
- successful Research CI run: `30199879513`
- Actions artifact ID: `8631307172`
- Actions artifact digest: `sha256:858f750534f772f25f1cf4f34d3fc72307fe9ce1a7906241f3386d91e6c95d21`
- artifact expiry: 2026-10-24
- artifact contains the trade-level diagnostic ledger, portfolio-event ledger, cohort summaries, robustness table, ranking, manifest, receipt and reproduction command.
