# USDJPY 2024 Timezone Conversion Research Audit v1

## Decision

**BEHAVIORAL IMPACT CONFIRMED in exact Python reconstruction.**

The accepted B02/F05 baseline converts Rakuten MT4 server timestamps with US
DST boundaries. The accepted 2023 HST normalization established that Rakuten
MT4's server clock itself follows GMT+2/GMT+3 on the Europe/EET-EEST boundary,
while the trading-hours schedule follows US DST.

This is not only a display-label issue. `ServerToUtc` is used by B02's Asian
session reference and signal window and by F05's entry-hour filter. Therefore
the conversion rule can change the signal stream.

No candidate was evaluated. No 2024 H2 or 2025 evidence was accessed.

## Frozen evidence

- Accepted 2024 H1 MT4 Run: `29787357305`
- Artifact ID: `8479048161`
- Artifact ZIP SHA-256:
  `e078758343995c8254244dd36385c93a61a7124cb5037beb458afdf5d0e208e5`
- Accepted Core head: `8a6ad1ac1ac357e85ceaa1f9e62549105ae555d8`
- Base EA blob:
  `ceaca2c0e3a259451a879a90deb7929a1941dd7e`
- Wrapper blob:
  `fe7e96b0d4ae22e585b09074959cb3b734994b22`
- 2024 M1 HST SHA-256:
  `eb8bee2a61bd54a23ef03fa36d96421fc5c354348b992aaad9fdc08df8513b90`
- 2024 M15 HST SHA-256:
  `7a20a337e3b002eb55b2440d2be4f00ff770845aeb76d85f67550bc98a8a5ef7`

The exact MT4 execution expectations were frozen before corrected MT4
execution in
`configs/research/usdjpy_2024_timezone_conversion_audit_prereg_v1.json`.

## Reconciliation of the accepted implementation

The audit reconstructed the EA directly from the accepted M15 bars and then
compared it with the accepted MT4 audit and trade ledger.

| Gate | Result |
|---|---:|
| Accepted opened signal keys reproduced | 429 / 429 |
| Accepted B02 opened | 98 |
| Accepted F05 opened | 331 |
| Accepted closed trades reproduced | 428 / 428 |
| Maximum closed-trade gross-pips difference | 0.0 |
| Accepted net JPY reproduced | 22,797 |
| Accepted PF reproduced | 1.3774150290548484 |

This exact reconciliation is important: the corrected expectation is not
coming from a different strategy simulator. It is the accepted strategy with
only the server-clock offset-selection boundary changed.

## Corrected clock rule

Current implementation:

- derive a GMT+2 UTC candidate;
- select GMT+3 when that candidate lies inside US DST.

Audited server-clock implementation:

- GMT+2 outside Europe/EET-EEST DST;
- GMT+3 from the last Sunday in March at 01:00 UTC through the last Sunday in
  October at 01:00 UTC;
- fail if a local server timestamp is ambiguous or nonexistent.

For the 2024 H1 source, 1,400 M15 rows move by one hour. The affected corrected
UTC interval starts at `2024-03-11T01:00:00Z` and ends at
`2024-03-29T21:45:00Z`. There were no ambiguous or nonexistent source rows.

## Frozen corrected expectation

| Metric | Accepted current | Corrected expected | Delta |
|---|---:|---:|---:|
| Opened positions | 429 | 427 | -2 |
| B02 opened | 98 | 96 | -2 |
| F05 opened | 331 | 331 | 0 |
| Closed positions | 428 | 426 | -2 |
| Net JPY | 22,797 | 22,730 | -67 |
| Profit factor | 1.3774150290548484 | 1.373965548444415 | -0.0034494806104332643 |
| Gross profit JPY | 83,200 | 83,511 | +311 |
| Gross loss JPY | 60,403 | 60,781 | +378 |

Signal-set relation on the same MT4 server bars:

- common: 422;
- accepted-current only: 7;
- corrected only: 5.

All differences are B02. F05 is unchanged in this H1 sample.

## Changed B02 signals

Accepted-current only:

| Server signal bar | Current UTC | Corrected UTC | Side | Pips |
|---|---|---|---:|---:|
| 2024-03-12 15:45 | 12:45 | 13:45 | buy | -28.6 |
| 2024-03-13 11:45 | 08:45 | 09:45 | buy | -13.0 |
| 2024-03-19 12:15 | 09:15 | 10:15 | buy | +25.9 |
| 2024-03-21 10:45 | 07:45 | 08:45 | buy | +45.8 |
| 2024-03-22 15:15 | 12:15 | 13:15 | sell | -11.7 |
| 2024-03-26 15:30 | 12:30 | 13:30 | buy | +4.6 |
| 2024-03-28 15:45 | 12:45 | 13:45 | sell | -10.9 |

Corrected only:

| Server signal bar | Current UTC | Corrected UTC | Side | Pips |
|---|---|---|---:|---:|
| 2024-03-13 09:30 | 06:30 | 07:30 | buy | -4.3 |
| 2024-03-15 09:45 | 06:45 | 07:45 | sell | -82.8 |
| 2024-03-19 09:30 | 06:30 | 07:30 | buy | +45.0 |
| 2024-03-21 09:30 | 06:30 | 07:30 | buy | +62.4 |
| 2024-03-22 09:45 | 06:45 | 07:45 | sell | -14.9 |

These rows are recorded to explain the frozen aggregate expectation, not to
create exceptions or tune session boundaries.

## Scope of the corrected MT4 audit

The corrected MT4 run may change only `ServerToUtc` offset selection. It must
leave unchanged:

- B02 session and signal hours;
- F05 breakout and entry-hour rules;
- the separate US-DST trading-hours exclusion schedule;
- B02/F05 time exits;
- lots, spread, model and account contract;
- order of portfolio processing;
- audit schema.

The corrected MT4 run must reproduce 427 opened positions, 96 B02, 331 F05,
426 closed positions, JPY 22,730 and PF 1.373965548444415, with zero order
failures. It must also reproduce the frozen 7 current-only and 5 corrected-only
server-bar signal relation.

## Consequence for the development sequence

2023 baseline reconstruction cannot be frozen against the known-wrong US-DST
server-clock conversion. First, Rakuten MT4 must reproduce the corrected 2024
expectation. If it does, the canonical baseline clock implementation and all
UTC-derived 2024 session/trade-key fields will be corrected before the 2023
baseline and cross-year architecture atlas are built.

This finding does not reopen closed candidate specifications. It corrects a
shared foundational time conversion before creating any new candidate.
