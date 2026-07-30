# USDJPY 2020–2022 Rakuten MT4 Broker-History Provisional Baseline

Work ID: `USDJPY-MT4-2020-2022-PROVISIONAL-BASELINE-001`

Final classification: `FAIL_KNOWN_PERIOD_REPRODUCTION_NOT_COMPARABLE`

Evidence class: `ANALYSIS_ONLY_PROVISIONAL_BROKER_HISTORY_EVIDENCE`

## Scope and firewall

This work executed only:

- `B02_BASELINE_UNCHANGED`
- `F05_BASELINE_UNCHANGED`
- `B02_F05_BASELINE_UNCHANGED_PORTFOLIO`

It did not use B02 C3, HYP-039, HYP-040, HYP-041, HYP-042, HYP-043, an unselected candidate, or a source-portability correction. It performed no candidate selection, threshold selection, retuning, Entry/Exit change, side/session exclusion, production authorization, or live authorization. It did not access 2025H2.

2020–2022 remains `ANALYSIS_PERIOD`; 2023–2024 remains `RESEARCH_AND_CANDIDATE_CONSTRUCTION_PERIOD`; 2025H1 remains `VALIDATION_PERIOD`.

## Source and tester contract

- Source: Rakuten MT4 broker-history HST
- Raw Tick status: `RAKUTEN_BROKER_NATIVE_RAW_TICK_NOT_AVAILABLE`
- Source-native Tick authority: false
- Model: `MT4_MODEL0_FIXED_SPREAD_PROVISIONAL`
- Timeframe: M15
- Primary spread: 5 points / 0.5 pip fixed
- Stress: 10, 15 and 25 points
- Warm-up: 2019-10-01 through 2019-12-31, excluded from P/L
- Analysis: 2020-01-01 through 2022-12-31
- Missing months: none
- Potential M15 history gaps: 0
- M15 analysis records: 74,722
- M15 HST SHA-256: `b22e9fb9a6d0f397b4186ba17f6e71cae9eb38aa59f214dfd1eb5173e4e7f165`

## Execution identity

- Core SHA: `56cbf5da0b7f0dd0a6560a6d1c9cedd492a7fa70`
- Run: `30534882633`, attempt 1
- terminal SHA-256: `683d3638af3a14dc4e643f51d2fb27bf579b0c9c916f4b85444ccb156a3a1655`
- MetaEditor SHA-256: `92db0ef6a13e9fdb0eb2d7e6ad7719fc24b12e10ea394c714c76ddeab1b2dbba`
- MQ4 SHA-256: `34cc3a4978dffbe98887a676a2321db3f10daa1f64b75b99cf4f86243e6fc972`
- EX4 SHA-256: `af10c3877f1d16fb8c4a0541aae19fa01af0823cd9cfb240a3a6243d576e4a69`
- Compile: success, no errors reported
- Deterministic repeat: PASS

## 2020–2022 all-period result

| Variant | Trades | Net JPY | PF | Realized DD | Minimum realized equity |
|---|---:|---:|---:|---:|---:|
| B02 unchanged | 672 | +11,167 | 1.105023 | 17,627 | 99,700 |
| F05 unchanged | 2,109 | +17,470 | 1.065705 | 29,455 | 98,434 |
| B02 + F05 portfolio | 2,781 | +28,637 | 1.076937 | 40,622 | 98,246 |

Portfolio gross profit was ¥400,851, gross loss was ¥372,214, average trade was ¥10.2974, median trade was ¥0, win rate was 49.9461%, payoff ratio was 1.075386, maximum winner was ¥2,845, maximum loser was -¥5,870, maximum consecutive wins was 17 and maximum consecutive losses was 15.

The MT4 virtual Tick path recorded maximum equity drawdown ¥42,839, minimum equity ¥98,173, maximum 10 open orders, maximum 0.10 open lots, minimum free margin ¥62,929.18 and minimum margin level 250.292%. This is not source-native Tick full-equity DD. The tester-reported DD field remains separated from realized-ledger DD.

## Annual portfolio result

| Year | Trades | Net JPY | PF | Realized DD |
|---|---:|---:|---:|---:|
| 2020 | 922 | +20,197 | 1.218150 | 7,834 |
| 2021 | 958 | +3,445 | 1.038890 | 7,112 |
| 2022 | 901 | +4,995 | 1.026145 | 40,622 |

All three years were positive, but 2022 contained a large H2 loss and the full-period realized DD.

## Half-year portfolio result

| Half | Trades | Net JPY | PF |
|---|---:|---:|---:|
| 2020H1 | 435 | +19,614 | 1.403622 |
| 2020H2 | 487 | +583 | 1.013254 |
| 2021H1 | 445 | -2,340 | 0.943264 |
| 2021H2 | 513 | +5,785 | 1.122204 |
| 2022H1 | 439 | +32,362 | 1.624580 |
| 2022H2 | 462 | -27,367 | 0.803446 |

Four of six half-years were positive. The best half-year was 2022H1 and the worst was 2022H2.

## Monthly portfolio result

The complete 36-month machine-readable table is stored at `data/derived/usdjpy_mt4_2020_2022_provisional_baseline_monthly_portfolio_v1.csv`.

Nineteen of 36 months were positive. Best month was 2020-02 at +¥15,222; worst month was 2022-09 at -¥8,962. Worst day was 2022-10-21 at -¥13,968 and worst week was 2022-W42 at -¥13,140.

## Strategy, side and session contribution

- B02 contribution: +¥11,167
- F05 contribution: +¥17,470
- Long: +¥41,871
- Short: -¥13,234
- Asian: +¥14,307
- London Open: +¥29,194
- London/NY overlap: -¥11,720
- New York: -¥3,144

The provisional result therefore contains material side and session asymmetry. It must not be used to introduce a Short exclusion or session exclusion because this work is analysis-only and retuning is prohibited.

## Concentration and bootstrap

- Top 1 winner removed: +¥25,792
- Top 3 winners removed: +¥21,068
- Top 5 winners removed: +¥17,178
- Top winner decile removed: -¥118,001
- Trade bootstrap iterations: 10,000
- Probability of positive portfolio net: 88.28%
- Net p05 / median / p95: -¥11,606 / +¥28,694 / +¥68,556
- PF p05 / median / p95: 0.970797 / 1.077090 / 1.196302
- Tick path assumed by bootstrap: false

## Spread diagnostics

| Fixed spread | Trades | Net JPY | PF |
|---|---:|---:|---:|
| 1.0 pip | 2,781 | +14,732 | 1.038848 |
| 1.5 pips | 2,781 | +827 | 1.002141 |
| 2.5 pips | 1,901 | -14,809 | 0.927317 |

Stress runs are diagnostics and are not the primary baseline.

## Known-period reproduction failure

The same broker-history terminal, EX4, Model=0 and fixed 5-point spread did not reproduce the accepted known-period authority.

### 2023–2024

- Accepted authority: 1,882 portfolio trades, +¥51,627, PF 1.137713
- Broker-history reproduction: 257 trades, -¥28,552, PF 0.663484
- Difference: -1,625 trades and -¥80,179

### 2025H1

- Accepted authority: 463 portfolio trades, -¥20,808, PF 0.829408
- Broker-history reproduction: 160 trades, -¥19,332, PF 0.546591
- Difference: -303 trades and +¥1,476

Both periods are classified with trade-count mismatch, price mismatch, P/L mismatch, source event population difference, tester model difference and timestamp mismatch requiring trade-level reconciliation. The mismatch is large and unresolved. Therefore the 2020–2022 result cannot be certified as a comparable formal baseline even though the 2020–2022 history coverage and deterministic rerun passed.

## Final classification

`FAIL_KNOWN_PERIOD_REPRODUCTION_NOT_COMPARABLE`

This is not a formal FAIL for B02 or F05. It is a failure to certify the broker-history result as a comparable provisional baseline.

## Remote evidence

- Core Issue: `mitsuru93/usdjpyea-core#714`
- Core Release: `usdjpy-mt4-2020-2022-provisional-baseline-v1`
- Release ID: `362378690`
- Release archive asset ID: `495282368`
- Release archive SHA-256: `a50f723f9ba7dbd43ab0c783c4e352da058ee1ad04038bbcb90c69817504eea3`
- Release readback: `PASS_BYTE_IDENTICAL_RELEASE_READBACK`
- Actions Artifact: unavailable due to Actions storage/API; Release is the immutable authority
- Core small-evidence branch: `evidence/usdjpy-mt4-2020-2022-provisional-baseline-v1`

## Exact next action

Perform trade-level reconciliation against the certified `usdjpy-2020-2022-source-native-bidask-tick-authority-v1` Release using strategy, side, signal UTC, Entry UTC, Exit UTC, trading date, Entry/Exit prices, holding bars and sequence. Classify MT4-only, Tick-only and common events and their timestamp, price, holding and P/L differences. Do not retune, change any candidate rule, change any formal decision, or authorize production/live use.
