# USDJPY 2023 Rakuten MT4 HST Data Acceptance v1

## Decision

**PASS — the accepted Rakuten MT4 USDJPY 2023 M1 Bid-bar HST extraction has
been normalized to canonical UTC and is authorized for unchanged baseline
reconstruction and the 2023 architecture atlas.**

Candidate signal generation, candidate outcome evaluation, parameter selection,
2024 H2 access and all 2025 access remain prohibited.

## Source identity

- Core Run: `29987402745`
- Core Job: `89142247552`
- Core artifact ID: `8555630385`
- Core artifact ZIP SHA-256:
  `e944ceb6c0c0423b3a65814ea880d8d8f951532350485c423ff427999ea6eaf4`
- Core receipt: `mitsuru93/usdjpyea-core#173`
- Selected HST: `RakutenSecurities-Live\USDJPY1.hst`
- Selected HST SHA-256:
  `db00b63e9e7ff2dd3f785563ad7f392a7e79ccef8a2c3e696f662b397b2b5af0`
- HST version: `401`
- Symbol / period: `USDJPY / M1`
- Price side: Bid bars

## Why the prior source contract is not reused unchanged

The frozen acquisition preregistration expected Dukascopy UTC M1 Bid bars.
The actually accepted source is a native Rakuten MT4 HST file whose timestamp
field is an MT4-server local clock encoded as an epoch value. It is therefore
not valid to relabel the extracted timestamps as UTC.

This acceptance adds a source-specific normalization contract while preserving
the original prohibition on candidate analysis before data acceptance.

## Official Rakuten clock facts

Rakuten's MT4 FAQ states that the server clock is GMT+2 in standard time and
GMT+3 in summer time. Rakuten's 2023 notices separately state that FX trading
hours moved to the US summer schedule from the 13 March 2023 trading day and
returned to the standard schedule from the 6 November 2023 trading day.

Those two facts do not by themselves identify the server-clock transition
week. The HST maintenance boundaries do.

## HST transition audit

Representative source rows around the 2023 transitions are:

| Evidence window | MT4 server | Frozen offset | UTC | Japan time |
|---|---|---:|---|---|
| Before US DST | 2023-03-09 23:54 | +2 | 2023-03-09 21:54 | 2023-03-10 06:54 |
| US DST active, before Europe DST | 2023-03-13 22:54 | +2 | 2023-03-13 20:54 | 2023-03-14 05:54 |
| Europe DST active | 2023-03-27 23:54 | +3 | 2023-03-27 20:54 | 2023-03-28 05:54 |
| Europe DST ended, US DST still active | 2023-11-03 22:58 | +2 | 2023-11-03 20:58 | 2023-11-04 05:58 |
| US DST ended | 2023-11-10 23:58 | +2 | 2023-11-10 21:58 | 2023-11-11 06:58 |

The daily close/maintenance boundary shifts one hour when US trading hours
change, while the server offset itself changes at the Europe/EET-EEST
boundaries. The accepted conversion is therefore:

- UTC+2 outside Europe DST;
- UTC+3 from the last Sunday in March at 01:00 UTC through the last Sunday in
  October at 01:00 UTC;
- fail if a local server timestamp is ambiguous or nonexistent.

For 2023 the frozen interval is
`2023-03-26T01:00:00Z` to `2023-10-29T01:00:00Z`.

No ambiguous or nonexistent source rows were observed.

## Accepted normalized output

| Metric | Result |
|---|---:|
| First UTC M1 | 2023-01-02T05:00:00Z |
| Last UTC M1 | 2023-12-29T21:46:00Z |
| M1 rows | 371,128 |
| M15 rows | 24,825 |
| Incomplete M15 rows retained and flagged | 360 |
| Gap records | 445 |
| Maximum missing minutes | 2,997 |
| UTC duplicate timestamps | 0 |
| Nonascending UTC timestamps | 0 |
| Invalid OHLC rows | 0 |
| UTC+2 source rows | 148,845 |
| UTC+3 source rows | 222,283 |

File identities:

- M1:
  `167509bde6553a468ffe48b082ed79de183cc57991f668cf4b3e7341350d307e`
- M15:
  `4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78`
- Gap inventory:
  `7f437e02f79a2297ebb8dd450101fb482870c8d429c0d2e3485f878b3bb48ebc`
- Normalized package:
  `4d75f3f67f6c81fe97a2b540846723162c17482430b4cc201b577ab4e00b68e8`

The package was uploaded to Google Drive as
`usdjpy-2023-rakuten-mt4-hst-utc-normalized-v1.zip`, file ID
`1AlL9eRBn4F-bGQsb6-L19-2Iese8knao`, downloaded again, and matched the local
package SHA-256.

## M15 construction

M15 uses UTC quarter-hour floors:

- open: first source M1 open;
- high: maximum source M1 high;
- low: minimum source M1 low;
- close: last source M1 close;
- volume: sum of source M1 tick volume;
- missing M1 bars: not synthesized;
- each M15 row records source count and incomplete status.

## Important 2024 audit consequence

Some existing 2024 helper code converts MT4 server timestamps with US DST
boundaries. The 2023 HST evidence demonstrates that this is not the accepted
server-clock rule for Rakuten MT4. That code would shift timestamps by one hour
during the US/Europe DST mismatch windows.

This does not change native MT4 Strategy Tester P/L, because MT4 consumes its
own server-time history. It can affect Python-side UTC session labels,
cross-period time-of-day analysis and any trade-key construction that converts
server time to UTC.

Before the 2023/2024 architecture-atlas comparison, the 2024 normalization and
trade-key UTC conversion must therefore be audited against the same rule.
Existing P/L results are not reopened solely by this finding; only
timestamp-dependent derived evidence is in scope for the audit.

## Authorization

Authorized now:

1. reconstruct the unchanged B02/F05 2023 baseline;
2. establish exact research/MT4 trade-key parity;
3. build the 2023 architecture atlas;
4. audit 2024 UTC-derived session and trade-key fields before cross-year
   comparison.

Still prohibited:

- new candidate signal generation;
- candidate outcome evaluation;
- parameter search or selection;
- 2024 H2 access;
- any 2025 access;
- live orders.
