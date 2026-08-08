# USDJPY 2020–2025H1 C2・C3・Short Pullback Integrated Long-Horizon Qualification

- Work ID: `USDJPY-INTEGRATED-LONG-HORIZON-QUALIFICATION-001`
- Final decision: `PARTIAL_LONG_HORIZON_RECOVERY_WITH_RESIDUAL_LOSS`
- Primary portfolio: `P4_B02_C3_F05_C2_SP39`
- Production authorization: **NO**
- 2025H2 accessed: **false**

## Economic conclusion

The frozen P4 configuration is profitable over 2020–2024 in pooled absolute terms (`+¥80,674`) but does not satisfy the primary 2025H1 requirement. 2025H1 is `-¥2,131`, with PF `0.980760`.

| Period | Net JPY | PF | Authority status |
|---|---:|---:|---|
| 2020 | +17,403 | 1.164201 | exact source-native |
| 2021 | -4,279 | 0.954460 | exact source-native |
| 2022 | +323 | 1.001679 | exact source-native |
| 2023 | +9,634 | 1.05123 diagnostic | exact frozen-component net; PF from row diagnostic |
| 2024 | +57,593 | 1.35768 diagnostic | exact frozen-component net; PF from row diagnostic |
| 2025H1 | -2,131 | 0.980760 | exact component authority composition |

2025Q1 is `-¥18,599`; 2025Q2 recovers `+¥16,468` but does not erase the first-quarter loss.

## Contribution

- B02 C3 2025H1: `+¥2,321`, improvement `+¥9,285`.
- F05 C2 2025H1: `-¥7,935`, improvement `+¥5,909`.
- unchanged Short Pullback 2025H1: `+¥3,483`.
- Combined P4 2025H1: `-¥2,131`.

## Long-horizon stability

- Positive years, 2020–2024: `4/5`.
- Positive half-years: `7/11`.
- Positive quarters: `12/22`.
- Positive months: `38/66`.
- Worst year: 2021, `-¥4,279`.
- Worst half-year: 2022H2, `-¥23,825`.
- Worst quarter: 2025Q1, `-¥18,599`.
- Rolling 6-month minimum (diagnostic monthly chronology): `-30,319` ending 2023-01.
- Rolling 12-month minimum (diagnostic monthly chronology): `-34,880` ending 2023-08.

## Technical qualification

The 2020–2022 source-native full-equity replay is certified: DD `¥38,609`, minimum equity `¥97,588`, minimum free margin `¥62,476`, minimum margin level `217.7766%`, max concurrency `10`, no stopout.

A single full-horizon latest-lineage P4 full-equity replay is not certified because HYP-043 C2’s historical decision ledger belongs to the 1,451-trade F05 authority generation while the latest binding F05 authority contains 1,464 trades. The 13-trade lineage difference is documented and not silently mixed. This limitation blocks PASS, but it does not prevent the economic PARTIAL decision because 2025H1 itself is already negative.

Rakuten HST/Model=0 remains diagnostic only. Historical raw-Tick exact T3 certification is not required; forward raw-Tick shadow qualification is required before any deployment.

## Exact next action

Do not deploy P4. Close this qualification as PARTIAL. Any residual-loss elimination must be a separate work item; after a frozen alternative exists, rerun this same 2020–2025H1 contract and complete Rakuten forward raw-Tick C2 qualification.
