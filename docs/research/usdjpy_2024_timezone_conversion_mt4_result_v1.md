# USDJPY 2024 Timezone Conversion MT4 Result v1

## Decision

**PASS — Rakuten MT4 confirmed the preregistered behavioral effect exactly.**

The canonical USDJPY server-time conversion is now:

- GMT+2 outside Europe/EET-EEST summer time;
- GMT+3 from the last Sunday in March at 01:00 UTC through the last Sunday in October at 01:00 UTC;
- ambiguous or nonexistent local server timestamps fail instead of being guessed.

The separate low-liquidity trading-hours exclusion continues to use the US DST schedule. Server-clock offset and broker trading schedule are distinct mechanisms.

No candidate was evaluated. No 2024 H2 or 2025 data was accessed.

## Binding execution identity

- Core Run: `29993711777`
- Attempt: `1`
- Job: `89162334758`
- Head SHA: `a0a28bde29ec07a5cfbdfa8cf57abcb7461af255`
- Runner: `onamae-mt4-ui-01`
- Rakuten MT4 build: `1470`
- Receipt: `mitsuru93/usdjpyea-core#180`
- Artifact ID: `8558119922`
- Artifact digest / independently downloaded ZIP SHA-256:
  `03aec8194ebdfadac5c0be73050ed9b94837de6030df89624ace9bf6b5e47fe6`
- Permanent Drive file ID: `1-Gg-P4dnqyEtKS2pDBf7C_A0yryNTZtE`
- Drive readback: byte-identical PASS

## Frozen result

| Metric | Preregistered | Rakuten MT4 | Gate |
|---|---:|---:|---|
| Opened positions | 427 | 427 | PASS |
| B02 opened | 96 | 96 | PASS |
| F05 opened | 331 | 331 | PASS |
| Closed positions | 426 | 426 | PASS |
| Net JPY | 22,730 | 22,730 | PASS |
| Profit factor | 1.373965548444415 | 1.373965548444415 | PASS |
| Order-send failures | 0 | 0 | PASS |
| Order-close failures | 0 | 0 | PASS |

Additional MT4 totals:

- gross profit: JPY 83,511;
- gross loss: JPY 60,781;
- wins: 234;
- losses: 190;
- flat closes: 2;
- one B02 position remained open at the period boundary, consistent with 427 opens and 426 closes.

## Signal-set relation to the legacy clock

The comparison was made on identical MT4 server bars, not approximate UTC labels.

- common signals: 422;
- legacy-US-DST-clock only: 7;
- canonical-Europe-clock only: 5.

All differences in this H1 sample were B02. F05 remained at 331 entries.

## Identity and scope gates

Every preregistered gate passed:

- exact accepted HST hashes;
- exact Research preregistration and research-result blobs;
- original base EA blob verified before patching;
- generated patch limited to `ServerToUtc` offset selection;
- the US-DST trading-hours function retained;
- MetaEditor compilation successful;
- corrected EX4 SHA-256:
  `e2b158cdb96bcdbbcffa407563e80461eaf703bfdf95a3fc7b00fff247e0f886`;
- corrected audit SHA-256:
  `cec287f4cd0870d04159cbc12f968718ce093c921977c44323d26261da25e848`;
- zero unexpected signal-relation or P/L differences;
- zero order failures.

The downloaded audit was independently parsed after the Run. It contained 12,644 audit rows and reproduced all reported counts, JPY P/L and PF.

## Canonical consequence

The legacy 2024 H1 Run `29787357305` remains preserved as historical native-MT4 evidence, but it is superseded for all new timestamp-dependent work.

For future research, the following must be rebuilt under the canonical clock before use:

- UTC signal and entry keys;
- session labels;
- weekday and time-of-day fields;
- entry-state and overlap joins that depend on UTC keys;
- 2023/2024 cross-year architecture comparisons.

Closed Family A–F specifications remain closed. This foundational correction does not reopen them or permit result-driven repairs. Their historical derived datasets may not be reused for new candidate selection without canonical-clock reconstruction.

## Next action

1. apply the accepted conversion to the Core baseline source;
2. freeze the resulting source and generated EX4 identities;
3. reconstruct unchanged B02/F05 baseline behavior on accepted 2023 data;
4. require exact research/MT4 trade-key and P/L parity;
5. only then build the 2023 architecture atlas.
