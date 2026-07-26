# F05 Failed Reclaim Extended Grid Stage 1 Result v1

## Scope

- Analysis periods: 2023H1, 2023H2, 2024H1, 2024H2 only.
- 2025H1 and 2025H2 were not accessed or used for selection.
- Source evidence: `f05-failed-reclaim-validation-v1-30104463746-1` artifact and its `exploration_reproduction_ledger_v1.csv`.
- This stage is exploratory parameter sensitivity. It does not replace the frozen binding candidate.

## Previously confirmed natural-family result

The strongest previously evaluated natural-family candidate was:

- `max_cons = 2`
- `max_time = 60 minutes`
- `close_buf = 0.0 pips`
- no maximum reclaim-width restriction

Result:

| Metric | Basic | Refined candidate |
|---|---:|---:|
| Total delta | +202.1 pips | **+248.3 pips** |
| Stopped trades | 14 | 11 |
| Winner damage | -84.9 pips | **-36.6 pips** |
| Loser benefit | +287.0 pips | +284.9 pips |
| Positive folds | 4/4 | **4/4** |

Fold deltas for the refined candidate:

- 2023H1: +68.7 pips
- 2023H2: +50.7 pips
- 2024H1: +122.4 pips
- 2024H2: +6.5 pips

## Stage 1 extended sensitivity

A finer monitoring-time grid was applied to the exact exploration event ledger. The provisional `max_mfe` dimension means the maximum favorable excursion through the trigger must be no greater than the specified value. This is a sensitivity proxy only; it is not yet the final executable profit-disarm definition.

### Monitoring-time plateau

With `max_mfe = 0.0 pips`, the best time-only result is constant from 55 through 90 minutes:

| Max monitoring time | Total delta | Winner damage | Loser benefit | Positive folds |
|---:|---:|---:|---:|---:|
| 45 min | +161.4 | -73.2 | +234.6 | 4/4 |
| **55 min** | **+213.8** | -73.2 | +287.0 | 4/4 |
| **60 min** | **+213.8** | -73.2 | +287.0 | 4/4 |
| **90 min** | **+213.8** | -73.2 | +287.0 | 4/4 |
| 120 min | +202.1 | -84.9 | +287.0 | 4/4 |
| unlimited | +202.1 | -84.9 | +287.0 | 4/4 |

Interpretation: the gain from the time restriction is caused by excluding a late harmful event beyond 90 minutes. The evidence does not identify 60 minutes as a uniquely optimal point; instead it supports a broad 55–90 minute plateau. Sixty minutes remains the most natural operational representative.

### Profit-disarm sensitivity proxy

Tightening the event set to `max_mfe <= -0.2 pips` reduced total delta to +207.3 pips and removed the only 2024H2 event, leaving 3/4 positive folds. Tightening to `max_mfe <= -0.5 pips` reduced the result to +66.5 pips with only 2/4 positive folds.

Therefore a more severe never-profitable threshold is not supported by this proxy. The final profit-disarm test must be performed from raw ordered ticks, distinguishing a transient executable profit from sustained or meaningful profit.

## Current research judgment

1. Preserve `max_cons = 2`, `close_buf = 0`, and no reclaim-width cap as the lead structural family.
2. Treat 55–90 minutes as a stability plateau; retain 60 minutes as the representative parameter rather than claiming a sharp optimum.
3. Do not add a negative MFE severity gate based on the current proxy.
4. Continue to an exact raw-tick extended grid for profit-disarm threshold, persistence, failure timing, and exit delay.
5. Keep all selection restricted to 2023–2024.

## Next exact grid

The next evaluator run must include:

- monitoring time: 45, 55, 60, 75, 90 minutes;
- maximum reclaim/failure sequence count: 1, 2, 3, unlimited;
- close buffer: 0.0, 0.25, 0.5 pips;
- profit-disarm threshold: 0.0, 0.2, 0.5, 1.0 executable pips;
- profit persistence: 1 tick, 2 consecutive ticks, 5 seconds, 15 seconds;
- failure confirmation: next completed M5, M1 early confirmation, two-M1 confirmation;
- exit delay: first executable tick, 1 second, 3 seconds, 5 seconds;
- reporting by fold, side, winner/loser damage, month, and leave-one-fold-out stability.

No candidate is authorized for production from Stage 1 alone.
