# USDJPY Market-State Router — S3_H4_ALIGNED MT4 Pre-Implementation Audit v1

## Decision

`PASS_RESEARCH_CORE_PARITY_AND_MT4_PREIMPLEMENTATION_AUDIT`

`S3_H4_ALIGNED` reproduces the frozen Research permission rule in Core/MT4 across the preregistered 2023H1–2024H2 evidence boundary. The candidate is eligible for the next controlled integration stage.

This decision does not authorize production or live orders.

## Frozen candidate rule

- Candidate: `S3_H4_ALIGNED`
- H4 state: EMA(6) versus EMA(24)
- H4 bar: exactly 16 complete M15 slots
- Price side: Bid
- USDJPY precision: 3 digits
- Permission: allow only when `H4 state == trade side`
- Strategy exceptions: none
- Side exceptions: none
- Session exceptions: none
- Parameter changes: none

The exact implementation contract remains the authority:

- Research commit: `2ade5c61ebc16e389da569d24fe678b081a56419`
- Contract: `configs/research/usdjpy_market_state_router_exact_implementation_contract_v1.json`

## H4 state parity

Binding Core Run: `30237882923`

- Core SHA: `227a514fd2df6b18274867d1782ccb18b614ef1f`
- Artifact ID: `8642244150`
- Artifact digest: `b5724d09aecb8e2b2228acf6f461f36e106bad3c8aa82768803ed5ff0d4433a8`
- H4 rows: 3,055
- Bucket-time mismatches: 0
- Information-time mismatches: 0
- Bid-close mismatches: 0
- EMA mismatches above `1e-10`: 0
- H4-state mismatches: 0
- Permission truth-table mismatches: 0

Maximum EMA absolute error was approximately `5.12e-13`.

## Binding historical reference-trade parity

The binding population is the exact frozen 1,882 Research reference trades. A dedicated MT4 replay EA passed each entry timestamp and side through the shared Core router without sending orders.

Source MT4 Run: `30238471176`

- Core SHA: `149c43caf573ab9cf5767d010183928f6a8b35fa`
- Source artifact ID: `8642446637`
- Source artifact digest: `7a8ab34a9c0d1827d64bc4c139303bb47643cff1c4592569bedc16e56df89339`

Evaluator receipt repair Run: `30238772493`

- Repaired artifact ID: `8642512253`
- Repaired artifact digest: `ebcd0ebc629b97e40562003a01746d944f65cb56bbd23d602a4baa36ed42f94e`
- Schedule rows: 1,882
- MT4 decision rows: 1,882
- Missed entry bars: 0
- Router data errors: 0
- Mismatch rows: 0
- Blocked: 671
- Allowed: 1,211
- Permission mismatches: 0
- Orders sent: 0

The evaluator repair did not rerun MT4 or change evaluation logic. It only made NumPy scalar booleans JSON serializable after the unchanged evaluator had already produced an empty mismatch ledger.

## Reference correction

The frozen exact implementation contract required Bid OHLC with USDJPY digits=3. The legacy 2024 reference generator nevertheless selected Mid OHLC.

- Legacy Mid canonical SHA-256: `c1aebc9eb33f8c4b41f639eb180ddb5e26ea99acee9510b5a7a259bd3b64842a`
- Corrected Bid canonical SHA-256: `8a7aeb6c193c93038e7ed36edc4586fd05032e8dc8ac7ff76e6fca0c703a11ac`
- MT4 canonical SHA-256: `8a7aeb6c193c93038e7ed36edc4586fd05032e8dc8ac7ff76e6fca0c703a11ac`

This was an evidence/reference correction only. Candidate selection, parameters, permission semantics, and period boundaries did not change.

## Integrated warm-up repair

The initial integrated candidate did not preload available closed M15 history before its first entry decision. Four early shared-trade decisions therefore remained neutral one H4 bucket too long.

- Repair commit: `4e7900872f69db586f1c1b3d16cdb7afd77d4581`
- Repair: process all available closed M15 bars from the frozen authority start in ascending order before the first decision
- Candidate-definition change: false
- Parameter change: false

The repaired implementation passed both H4 state parity and the exact 1,882-trade historical replay.

## Auxiliary native B02/F05 regeneration

Core Run `30237456639` regenerated the full B02/F05 baseline natively and emitted 1,898 decisions versus the preregistered 1,882-trade Research population.

- Reference trades missing from native regeneration: 9
- Extra native trades: 25
- Order-send failures: 0
- Order-close failures: 0

This is retained as a non-binding diagnostic of B02/F05 baseline trade-universe drift. It does not replace the exact frozen 1,882-trade binding population.

## Immutable Core evidence

Core Release:

`usdjpy-market-state-router-s3-mt4-preaudit-v1`

- Release target SHA: `55bc21b00e5af07bb695fd16cf99d67051e4b9c5`
- Release readback: verified
- Final Core cleanup SHA: `1c02971b44594b2341b0db6756c8025527056488`
- Core final receipt: `docs/research/market_state_router_s3_h4_aligned_mt4_preimplementation_audit_v1/final_receipt.json`
- Core final report: `docs/research/market_state_router_s3_h4_aligned_mt4_preimplementation_audit_v1/README.md`
- Core final Issue: `#328`

## Boundary and authorization

- Validated: 2023H1, 2023H2, 2024H1, 2024H2
- 2025H1 accessed: false
- 2025H2 accessed: false
- Production authorized: false
- Live orders authorized: false

## Next stage

The candidate may proceed to the next controlled integration stage using the frozen rule and the corrected Bid-contract evidence. The native B02/F05 trade-universe drift must remain separately tracked and must not be used to redefine the binding 1,882-trade parity population retroactively.
