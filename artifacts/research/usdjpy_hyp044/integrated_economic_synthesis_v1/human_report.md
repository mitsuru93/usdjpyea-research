# USDJPY-HYP-044 Integrated Profitability Stabilization — Final Report

## Final decision

`PASS_PRODUCTION_CONFIGURATION_SELECTION_WITH_LIMITATIONS_AND_LIVE_AUTHORIZATION_WITHHELD`

Selected production configuration:

`B0_A2_EARLY_C3_PLUS_A4_SESSION_LOSS_CAP_2_WITHOUT_ASIAN_RANGE_SWEEP`

This configuration consists of:

- B02 A2 localized early C3 giveback handling within the first 16 completed M15 bars
- F05 C2 localized exact-60-second loss recovery
- unchanged HYP-039 Short Pullback
- parent B02/F05 session consecutive realized-loss cap 2
- no Asian Range Sweep constituent

The EA software configuration is selected and authorized for deterministic Release. Real-money production/live authorization is withheld.

## Binding economics

| Period | Authority | Trades | Net | PF | Full-equity DD |
|---|---|---:|---:|---:|---:|
| 2020–2022 | source-native Bid/Ask Tick | 3,625 | +JPY 22,699 | 1.058167 | JPY 39,650 |
| 2023–2024 | Rakuten MT4 | 2,386 | +JPY 70,455 | 1.204625 | JPY 27,206 |
| 2025H1 | Rakuten MT4 | 609 | +JPY 609 | 1.005668 | JPY 26,756 |
| 2020–2025H1 pooled | mixed binding authorities | 6,620 | +JPY 93,763 | 1.111357 | — |

2025H1 therefore satisfies the preregistered conditions `net > 0` and `PF > 1`. The margin is narrow rather than strong.

## 2025H1 strategy attribution

| Strategy | Trades | Net | PF |
|---|---:|---:|---:|
| B02 A2 | 101 | +JPY 4,648 | 1.329225 |
| F05 C2 | 336 | -JPY 7,522 | 0.885555 |
| unchanged SP39 | 172 | +JPY 3,483 | 1.126155 |

Direction attribution:

- LONG: 203 trades, -JPY 7,155, PF 0.844497
- SHORT: 406 trades, +JPY 7,764, PF 1.126365

The remaining weakness is concentrated in F05 and the long side. The configuration is profitable because B02 and SP39 offset that residual loss.

## Core / MT4 / Rakuten qualification

- MetaEditor: 0 errors / 0 warnings
- EX4 SHA-256: `4ed7fecc0349cbe36db5b2884b0e470018bd141c52d078f6251e285718c0a493`
- Rakuten qualification Run: `30588133058`, attempt 3
- Runner: `onamae-mt4-ui-01`
- Timeframe/model/spread: M15 / Model 0 / 5 points
- Runtime errors: 0
- Duplicate open tickets: 0
- Duplicate close tickets: 0
- Stopout: no breach
- F05 C2 exact-60-second execution: 148/148 in 2023–2024 and 56/56 in 2025H1

For 2025H1, expected and actual economics are identical at 609 trades and +JPY 609. B02 has 101 exact rows and F05 has 336 exact rows. SP39 has 171 exact rows plus one order whose expected entry timestamp is 22:30 UTC and MT4 first executable tick is 22:31 UTC; close time, exit identity, and -JPY 126 P/L are identical. This is classified as an explained executable-tick timestamp difference, not a candidate-rule mismatch.

For 2023–2024, actual Rakuten MT4 is +JPY 70,455 versus +JPY 62,097 in the event replay. Full source-row parity is not achieved. The source-population, price, and information-time divergence remains an explicit limitation and does not retroactively change HYP-039 through HYP-043 decisions.

## Full-equity and margin

2025H1 selected B0:

- maximum full-equity DD: JPY 26,756
- minimum equity: JPY 73,309
- minimum free margin: JPY 39,506.54
- minimum margin level: 197.9012%
- maximum open orders: 7
- maximum open lots: 0.07
- stopout breach: false

2023–2024 selected B0:

- maximum full-equity DD: JPY 27,206
- minimum equity: JPY 78,171
- minimum free margin: JPY 36,978.16
- minimum margin level: 177.6985%
- maximum open orders: 9
- maximum open lots: 0.09
- stopout breach: false

## Asian Range Sweep DD hedge comparison

The additive path reconstruction reproduced the immutable HYP-040 combined audit across 12,259 common timestamps with zero balance/equity difference.

Adding unchanged ARS40 to selected B0 produced:

- net: +JPY 586 versus +JPY 609 without ARS40
- PF: 1.004568 versus 1.005668
- full-equity DD: JPY 21,946 versus JPY 26,756
- DD improvement: JPY 4,810 / 17.98%
- minimum free margin: JPY 38,471.52
- minimum margin level: 183.3863%
- maximum open orders: 8
- maximum open lots: 0.08
- daily close-P/L correlation: -0.1625
- weekly close-P/L correlation: -0.4995

ARS40 clearly provides diversification and DD reduction. It is nevertheless rejected because it reduces net by JPY 23, has standalone PF below 1, and is not an authorized Common Portfolio constituent after its formal Rakuten portability failure. Its DD benefit is retained as mechanism evidence only.

## Residual limitations

- 2025H1 is a known-outcome validation reassessment, not untouched external validation.
- 2025H1 profitability is only +JPY 609 / PF 1.005668.
- F05 and LONG remain negative in 2025H1.
- 2021 remains -JPY 1,190 in source-native analysis.
- 2023–2024 full source-row parity is not achieved, despite stronger actual Rakuten economics.
- 2025H2 was not accessed.

## Authorization

- software release authorized: **yes**
- production configuration selected: **yes**
- real-money production authorization: **no**
- live authorization: **no**

Independent unseen forward/Rakuten evidence and explicit capital-risk approval are required before live deployment.

## Immutable Releases

### Core / MT4 / Rakuten

- tag: `usdjpy-hyp044-integrated-profitability-stabilization-v1`
- Release ID: `362800814`
- asset ID: `496075894`
- asset bytes: `2,981,655`
- SHA-256: `39e3da6e8a8513d106c80113ac28d43f98a58465593e58d7d8b9a8a822ca3089`
- local/remote readback: identical / PASS

### Research closure

- tag: `usdjpy-hyp044-integrated-profitability-stabilization-research-v1`
- Release ID: `362805909`
- asset ID: `496089104`
- asset bytes: `430,650`
- SHA-256: `9314416b4bae4bde628de5b8d5c356dc5ae47fc608d6e73bd745e5993b75e935`
- local/remote readback: identical / PASS

The economic, implementation, parity, full-equity, ARS-disposition, deterministic archive, and remote readback work is complete.
