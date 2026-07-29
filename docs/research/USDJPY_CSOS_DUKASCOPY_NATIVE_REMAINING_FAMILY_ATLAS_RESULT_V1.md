# CSOS Dukascopy-Native Remaining-Family Opportunity Atlas Study

Final decision: `ATLAS_COMPLETE_MECHANISM_RESEARCH_ONLY`

## Authority and boundaries

- Program ID: `USDJPY-CSOS-DUKASCOPY-NATIVE-REMAINING-FAMILY-ATLAS-V1`
- Research start SHA: `1841ed3fba757a9a44496faeb9a6c7e014efa9d6`
- Research execution SHA: `61249e52e9acb567eb24298f95ea6c7afd520be4`
- Core reference SHA: `f897b250b808207d960417b2306935dcb0655acf`
- Workflow Run: `30435884192`
- Atlas period: 2023-2024 only.
- 2020-2022 EA-wide role: analysis period; this Atlas did not require or access it and assigns no confirmation or external-validation credit.
- 2025 EA-wide role: the only binding unseen external-validation period; this Atlas did not access it.
- Shortlist meaning: research prioritization only. It is not candidate approval, Core/MT4 authorization, 2025 authorization, production authorization, or live authorization.
- Family contract, ranking metric, cost assumption and shortlist gates were frozen before new family outcome calculation and were unchanged by the period-role clarification.

## Source inventory

- Dukascopy monthly archives: 24
- Tick count: 84,428,370
- Reconstructed M15 bars: 49,894
- Ask < Bid: 0
- Nonmonotonic Tick timestamps: 0

## Variant comparison

|Track A rank|Track B rank|Variant|Trades|Net JPY|PF|Positive folds|Positive months|Top-5 removed|Spread +1 pip|Delay +5s|Corr B02|Corr F05|Negative-day contribution|Combined DD|A eligible|B eligible|
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
|11|9|A_FALSE_BREAKOUT_REVERSAL|1150|¥-36,694|0.787|1/4|6/24|¥-46,490|¥-48,194|¥-38,049|-0.289|-0.306|¥15,260|¥49,094|False|False|
|9|10|B_BALANCE_MEAN_REVERSION|349|¥-6,749|0.872|1/4|10/24|¥-12,146|¥-10,239|¥-7,083|-0.003|-0.021|¥1,486|¥41,709|False|False|
|2|3|C_SHOCK_CONTINUATION|650|¥6,092|1.079|2/4|16/24|¥-1,770|¥-408|¥6,790|-0.027|0.153|¥-5,026|¥40,488|False|False|
|5|7|E_LONDON_NY|141|¥68|1.004|2/4|14/24|¥-4,035|¥-1,342|¥239|0.292|0.259|¥-9,287|¥41,614|False|False|
|12|11|E_NY_TOKYO|93|¥-2,649|0.619|0/4|8/24|¥-4,666|¥-3,579|¥-2,717|-0.223|0.082|¥127|¥41,792|False|False|
|1|1|E_TOKYO_LONDON|121|¥1,466|1.144|2/4|14/24|¥-2,557|¥256|¥1,150|0.200|0.198|¥-2,647|¥37,620|False|False|
|6|2|G_TREND_EXHAUSTION|1239|¥-13,750|0.910|1/4|11/24|¥-25,891|¥-26,140|¥-14,289|-0.350|-0.548|¥46,678|¥39,123|False|False|
|7|8|H_COMPRESSION_BREAKOUT|355|¥-834|0.978|2/4|11/24|¥-5,983|¥-4,384|¥-731|0.117|0.132|¥-8,829|¥42,915|False|False|
|8|6|I_FAILED_TREND_CONTINUATION|63|¥-2,125|0.781|2/4|9/24|¥-6,774|¥-2,755|¥-2,741|-0.010|-0.010|¥422|¥40,943|False|False|
|4|4|K_DAILY_TIME_SERIES_MOMENTUM|446|¥2,173|1.027|2/4|13/24|¥-8,045|¥-2,287|¥1,890|0.009|0.225|¥-15,443|¥42,148|False|False|
|3|5|K_LONDON_OPENING_RANGE_BREAKOUT|607|¥2,343|1.044|2/4|12/24|¥-2,492|¥-3,727|¥1,382|0.165|0.129|¥-6,928|¥43,825|False|False|
|10|12|K_ROUND_NUMBER_REJECTION|1289|¥-17,786|0.898|1/4|9/24|¥-26,775|¥-30,676|¥-17,805|0.039|-0.002|¥-6,918|¥57,276|False|False|

## Family comparison

|Family|Variants|Trades|Net JPY|PF|Positive folds|Positive months|Corr B02|Corr F05|Negative-day contribution|Combined DD|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|A — False Breakout Reversal|1|1150|¥-36,694|0.787|1/4|6/24|-0.289|-0.306|¥15,260|¥49,094|
|B — Balance Mean Reversion|1|349|¥-6,749|0.872|1/4|10/24|-0.003|-0.021|¥1,486|¥41,709|
|C — Shock Continuation|1|650|¥6,092|1.079|2/4|16/24|-0.027|0.153|¥-5,026|¥40,488|
|E — Session Transition|3|355|¥-1,115|0.969|1/4|11/24|0.274|0.335|¥-11,807|¥40,052|
|G — Trend Exhaustion|1|1239|¥-13,750|0.910|1/4|11/24|-0.350|-0.548|¥46,678|¥39,123|
|H — Volatility Compression Breakout|1|355|¥-834|0.978|2/4|11/24|0.117|0.132|¥-8,829|¥42,915|
|I — Failed Trend Continuation|1|63|¥-2,125|0.781|2/4|9/24|-0.010|-0.010|¥422|¥40,943|
|K — Other Literature- and Practice-Led Families|3|1702|¥-19,145|0.915|1/4|8/24|0.061|0.173|¥-28,900|¥60,672|

## Old Atlas identity diagnostic

Old Atlas identity is diagnostic only and is not a shortlist gate.

|Variant|Old events|Dukascopy events|Common signal/side|Exact common|Old-only|Dukascopy-only|P/L mismatch|
|---|---:|---:|---:|---:|---:|---:|---:|
|A_FALSE_BREAKOUT_REVERSAL|1139|1150|1040|1036|99|110|895|
|B_BALANCE_MEAN_REVERSION|347|349|325|324|22|24|280|
|C_SHOCK_CONTINUATION|643|650|600|600|43|50|521|
|E_TOKYO_LONDON|119|121|117|117|2|4|104|
|E_LONDON_NY|139|141|137|137|2|4|116|
|E_NY_TOKYO|78|93|75|74|3|18|71|
|G_TREND_EXHAUSTION|1241|1239|1132|1130|109|107|976|
|H_COMPRESSION_BREAKOUT|347|355|308|305|39|47|266|
|I_FAILED_TREND_CONTINUATION|63|63|58|57|5|5|50|
|K_LONDON_OPENING_RANGE_BREAKOUT|607|607|586|585|21|21|497|
|K_ROUND_NUMBER_REJECTION|1286|1289|1163|1160|123|126|1010|
|K_DAILY_TIME_SERIES_MOMENTUM|445|446|444|443|1|2|387|

## Shortlist decision

- Track A: no variant passed all fixed gates.
- Track B: no variant passed all fixed gates.
- Mechanism-research-only: `B_BALANCE_MEAN_REVERSION`.

## Full-equity limitation

`NOT_AVAILABLE` — Canonical B02/F05 state ledger is M15 Bid-open path evidence from mixed historical lineages and does not provide common-source intrabar executable Bid/Ask equity at every Dukascopy Tick timestamp; combining it with Tick-level candidate floating P/L would not be exact.

## Correct next period design

Any shortlisted family must move to a separate Hypothesis. In that research, 2020-2022 may be used for mechanism analysis and candidate design, 2023-2024 remains the main research/candidate-construction period, and the candidate must be frozen before the only binding unseen external gate in 2025. No candidate freeze, Core/MT4, 2025, production or live authorization is granted by this Atlas.
