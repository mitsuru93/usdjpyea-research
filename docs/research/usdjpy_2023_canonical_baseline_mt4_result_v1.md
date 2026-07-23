# USDJPY 2023 Canonical Baseline MT4 Result v1

## Decision

**PASS — the unchanged canonical-clock B02/F05 baseline reproduced exactly in Rakuten MT4 for 2023.**

The binding result authorizes construction of the 2023 Architecture Atlas. It does not authorize candidate generation, parameter search, 2024 H2 access or any 2025 access.

## Binding identity

- Core Run: `29998477805`
- Attempt: `1`
- Job: `89177724685`
- Head SHA: `1adf85cc49308268568e8356efacaa0dc933a957`
- Runner: `onamae-mt4-ui-01`
- Receipt: `mitsuru93/usdjpyea-core#187`
- Artifact ID: `8560057457`
- Artifact digest / downloaded ZIP SHA-256:
  `bf2cd6e94ba4a15f764e784f4a82b8d07edd3070ab198bbf9bc27112e931f63b`
- Permanent Drive file ID: `1DVE_Abq9278x03h8CI4Pd5jW-FJAskP1`
- Drive readback SHA-256: identical

The binding run completed every workflow step successfully: exact Core materialization, preparation-artifact verification, Research blob verification, isolated terminal construction, exact HST installation, compilation, Strategy Tester execution, full parity evaluation, evidence upload and receipt creation.

## Frozen result

| Metric | Research expectation | Rakuten MT4 | Gate |
|---|---:|---:|---|
| Opened trades | 964 | 964 | PASS |
| B02 opened | 232 | 232 | PASS |
| F05 opened | 732 | 732 | PASS |
| Closed trades | 963 | 963 | PASS |
| Period-end open trades | 1 | 1 | PASS |
| Realized net JPY | -9,904 | -9,904 | PASS |
| Gross profit JPY | 197,579 | 197,579 | PASS |
| Gross loss JPY | 207,483 | 207,483 | PASS |
| Profit factor | 0.9522659687781649 | 0.9522659687781649 | PASS |
| Wins | 469 | 469 | PASS |
| Losses | 493 | 493 | PASS |
| Flat | 1 | 1 | PASS |
| OrderSend failures | 0 | 0 | PASS |
| OrderClose failures | 0 | 0 | PASS |

## Trade-level parity

The evaluator compared every Research trade with the MT4 audit using the frozen trade key.

- expected opened keys: 964;
- actual opened keys: 964;
- expected closed keys: 963;
- actual closed keys: 963;
- missing opened keys: 0;
- unexpected opened keys: 0;
- missing closed keys: 0;
- unexpected closed keys: 0;
- duplicate opened keys: 0;
- duplicate closed keys: 0;
- closed-trade gross-pips mismatches: 0.

The sole period-end open position was exactly:

`F05|2023-12-29T16:30:00Z|-1`

with entry UTC `2023-12-29T16:45:00Z`.

The mismatch CSV contains only its header. Its SHA-256 is:

`cc43fc3fdadeead5483d61e6c50b10b232f6a7e100becc418077b18f39ef3d33`

The complete MT4 audit CSV SHA-256 is:

`a7349269db2072e24e694847e0c5517a90d10edd387aedb8baffa788caf008ff`

## Independent repeat execution

A separately dispatched repeat Run also passed:

- Run: `29998718769`
- Job: `89178633063`
- Receipt: `mitsuru93/usdjpyea-core#188`
- Artifact ID: `8560162845`
- Artifact digest:
  `sha256:b7a75ed5a1f5d20733f0b5e951876fef77e4b7ae45c943a1c5c6c9a6b5a85364`

The repeat produced the exact same:

- MT4 audit CSV SHA-256;
- empty mismatch-ledger SHA-256;
- expected-ledger SHA-256;
- trade keys;
- per-trade gross pips;
- realized JPY result;
- period-end open position and floating result.

The freshly compiled EX4 differed in byte hash and size between the two runs, while the source SHA, zero-error compile result and behavioral audit were identical. MetaEditor output is therefore not treated as byte-deterministic across fresh compilations. The binding implementation identity remains the exact source plus the compiled run receipt and resulting audit.

## Period-end mark

The frozen final market state was:

- final source M1 UTC: `2023-12-29T21:46:00Z`;
- final source M1 server time: `2023-12-29T23:46:00`;
- final Bid: `141.019`;
- fixed Ask: `141.024`;
- realized balance: JPY 90,096;
- equity: JPY 89,907;
- floating P/L: JPY -189;
- margin: JPY 5,640.86;
- free margin: JPY 84,266.14;
- margin level: 1,593.8527%;
- open orders/lots: 1 / 0.01.

The remaining short F05 position opened at `140.835`; marking it at Ask `141.024` gives exactly JPY -189.

## Deinitialization timestamp instrumentation defect

The outer timestamp columns on the final Deinit-related rows regressed after Strategy Tester completion:

- one final snapshot used `2021-06-04 10:33:59`;
- the period-end, risk-summary and runtime-deinit rows used `2019-02-10 17:54:06`.

This is a wrapper instrumentation defect: `TimeCurrent()` reverted to stale terminal server metadata after the simulated test interval, while the captured Bid/Ask, virtual account state and open-position state remained the correct final tested market mark.

Consequences:

- it does not affect any preregistered parity gate;
- it does not affect entries, exits, trade keys, pips or P/L;
- the regressed Deinit timestamps may not be used as Atlas features, period labels or cross-year keys;
- future instrumentation must capture a monotonic simulated tester timestamp or an explicit market-bar timestamp separately from terminal `TimeCurrent()`.

## Authorization

Authorized next:

1. build a 2023 closed-trade Architecture Atlas for the 963 reconciled trades;
2. use only entry-time information for explanatory feature columns;
3. keep outcome/path fields separate from entry features;
4. audit 2024 UTC-derived session and trade-key fields before any cross-year comparison.

Still prohibited:

- candidate signal generation;
- candidate outcome evaluation;
- parameter search or selection;
- 2024 H2 access;
- any 2025 access;
- live orders.
