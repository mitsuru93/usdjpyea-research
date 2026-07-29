# USDJPY Common Portfolio Evaluation and Integration Framework

## 1. Identity and scope

- Work ID: `USDJPY-EA-INTEGRATION-001`
- Repository role: EA-wide portfolio accounting and integration infrastructure
- Hypothesis ID: none
- Scientific PASS/FAIL authority: none
- Candidate-rule modification authority: none

This work compares and incrementally integrates completed outputs from:

- N1: `USDJPY-HYP-039` unchanged Short Pullback
- N2: `USDJPY-HYP-040` unchanged Asian Range Sweep successor
- F: F05 v2 or a formal no-change decision
- B: B02 v2 or a formal no-change decision

It does not alter Entry, Exit, permission, candidate version, formal decision, or period role in any originating study.

## 2. Period firewall

| Period | Fixed role in this framework |
|---|---|
| 2020–2022 | Optional historical reference only |
| 2023–2024 | Research/candidate-result integration and comparison |
| 2025H1 | Validation-result integration and comparison |

Repeated access to 2025H1 results does not convert the period into an analysis, research, development, diagnostic, or retuning period.

## 3. Exact B02/F05 baseline reproduction

### 2023–2024

- Trades: **1,882**
- Net: **+¥51,627**
- Profit factor: **1.1377131303215893**
- Realized-equity drawdown: **¥40,487**
- Full-equity drawdown: **¥42,660**
- Maximum concurrent positions: **9**
- Maximum concurrent lots: **0.09**
- Common ¥100,000 comparison basis minimum full equity: **¥59,118**

The historical source authority uses ¥1,000,000 initial capital and reports minimum full equity of ¥959,118. The common framework rebases the same P/L and equity deltas to ¥100,000. Drawdown is invariant; minimum equity shifts by exactly ¥900,000.

### 2025H1

- Trades: **463**
- Net: **-¥20,808**
- Profit factor: **0.8294076655052265**
- Authority Tick-equity drawdown: **¥42,737**
- Authority minimum equity: **¥57,328**
- Maximum concurrent positions: **8**
- Maximum concurrent lots: **0.08**
- Minimum margin level: **156.0535%**
- B02: **105 trades / -¥6,964**
- F05: **358 trades / -¥13,844**

Baseline classification: `NO_RECOVERY`.

## 4. Common accounting contract

- Reporting currency: JPY
- Comparison initial capital: ¥100,000
- Default lot per strategy: 0.01
- USDJPY pip size: 0.01
- Point size: 0.001
- Baseline spread: 5 points = 0.5 pip
- Value at 0.01 lot: ¥10 per pip
- Missing values: explicit `null`; never infer zero
- Realized equity: initial capital plus chronologically applied realized P/L
- Full equity: realized balance plus source-native open-position mark-to-market
- Drawdown: running peak equity minus current equity
- Margin: broker-reported authority where available; otherwise a complete broker contract is mandatory

## 5. Common same-timestamp chronology

1. Executable market tick
2. Strategy-local exit condition finalized
3. Close execution
4. Realized P/L applied
5. State and loss counters updated
6. Entry permission evaluated
7. Entry execution
8. Margin updated
9. Equity snapshot

Strategy-local logic is mapped into this chronology; it does not replace the global accounting order.

## 6. Explicit-null integrity policy

The baseline authorities exactly reproduce trades, net, PF and drawdown, but legacy evidence has known nulls:

- `decision_utc`: null
- commission: null
- swap: null
- some historical exit Bid/Ask quotes: null
- some historical Core SHA fields: null where the source authority does not provide them

These nulls stop only their dependent gates:

- null `decision_utc` stops complete decision-trace chronology parity
- null commission/swap stops component-complete transaction-cost attribution
- absent source-native mark-to-market stops full-equity candidate comparison
- absent margin contract stops margin feasibility
- absent artifact digest stops candidate ingestion

They do not change exact baseline net/PF/DD reproduction.

## 7. Candidate availability

| Slot | Study | Formal availability |
|---|---|---|
| N1 | HYP-039 unchanged Short Pullback | `PENDING_CANDIDATE_EVIDENCE` |
| N2 | HYP-040 unchanged Asian Range Sweep successor | `PENDING_CANDIDATE_EVIDENCE` |
| F | F05 v2 or no-change | `PENDING_CANDIDATE_EVIDENCE` |
| B | B02 v2 or no-change | `PENDING_CANDIDATE_EVIDENCE` |

HYP-038 is not imported. Its formal result does not provide a deployable rule and cannot substitute for HYP-039.

No aggregate-only result, reconstructed trade stream, or placeholder is admitted. A candidate must be available through merged main, an immutable Release, or a hash-pinned Actions artifact and must provide candidate identity/version, complete trade/equity/margin evidence, Research SHA, Core SHA, Run ID, artifact digest, and formal decision.

## 8. Combination matrix status

The only calculated combination is the exact baseline:

- `B02 + F05`: `CALCULATED`, classification `NO_RECOVERY`

All combinations containing N1, N2, F or B are:

`NOT_CALCULATED_PENDING_CANDIDATE_EVIDENCE`

This is an evidence gate, not an adverse scientific decision on those candidates.

## 9. Residual 2025H1 loss decomposition

- Remaining portfolio loss: **-¥20,808**
- B02 attribution: **-¥6,964**
- F05 attribution: **-¥13,844**
- Required portfolio improvement to reach zero: **¥20,808**
- Fixed-spread component under the baseline contract: **-¥2,315**
- Commission: null
- Swap: null
- Margin-blocked entries: 0
- Stop-out breach: false
- Negative holding-period rows: 0
- Trade execution failures: 0

Strategy attribution and exclusive exposure-bucket attribution are separate internally additive decompositions. They must not be summed together.

## 10. Architecture recommendation

`RETAIN_B02_F05_AS_REFERENCE_ONLY_AND_DEFER_FINAL_EA_COMPOSITION`

B02+F05 remains the exact comparison reference. It is not endorsed as the final production portfolio because 2025H1 remains -¥20,808 with PF 0.829408. A final composition and lot allocation cannot be selected until admissible evidence is available for the candidate slots.

No candidate rules or lot allocation were changed.

## 11. Exact next action

Ingest the first candidate that reaches merged main, an immutable Release, or a hash-pinned artifact with a complete common-ledger-compatible trade/equity/margin package. The nearest current dependency is HYP-039 Core PR #505. After its merge and formal evidence publication:

1. Pin candidate ID/version, Research SHA, Core SHA, Run ID and artifact digest.
2. Validate explicit-null, chronology, accounting, mark-to-market and margin gates.
3. Replay `BASELINE + N1` without changing candidate rules.
4. Apply the same adapter path to HYP-040, F05 v2 and B02 v2 as each becomes admissible.

## 12. Verification

- `pytest -q tests/test_usdjpy_ea_integration_001.py`: **4 passed**
- Python compilation: passed
- Candidate-rule changes: false
- Currency mismatch: 0
- Deterministic Release archive contract: configured
