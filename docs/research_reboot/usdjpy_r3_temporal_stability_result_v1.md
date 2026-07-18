# USDJPY R3 Temporal-Stability Result v1

## Decision

```text
R3 temporal-stability diagnostics: PASS
R4 common selection-rule design: unblocked but not started
candidate shortlist: none
H2 rows parsed: 0
2025 access: none
Core promotion: false
MT4 promotion: false
```

R3 applied the preregistered diagnostic framework to all 660 accepted R2 Entry/horizon combinations. It did not remove a combination, select a representative or define an operational Exit.

## Accepted run

```text
workflow: Run USDJPY R3 Temporal Stability v1
run_id: 29647304892
head_sha: 22a72f0cf1185e072d16afcdc64651502f2db83c
artifact_id: 8430424186
artifact: usdjpy-r3-temporal-stability-v1-29647304892
artifact_digest: sha256:bf906aa45e426146073d099ac2cf692067b4831256cd22de11e25f0e13b3e292
```

The downloaded artifact ZIP was independently hashed and matched the GitHub Actions artifact digest.

## Frozen execution

```text
runner_blob: e196b0f49479eb22331ede719f00f3bfc233bb29
runner_content_sha256: 90c4e74babcf0670b6f801dac30d04537f2a8efce0dfdb6adee2ccbf4d1c2807
lock_blob: d98de764d834fb26bb2c349de31bc2085ec19867
config_content_sha256: 9e11d313826fd001093d72c5dad3f53c66df76abb379becefcd50b3fd6841933
```

The evaluator and lock were committed before the accepted formal R3 run.

## Complete diagnostic shape

```text
input R2 trade rows: 383,078
candidate/horizon combinations: 660
unique Entry timestamps in regime map: 7,882

calendar-month rows: 3,960
quarter rows: 1,320
rolling two-month rows: 3,300
rolling three-month rows: 2,640
anchored-ranking rows: 3,300
spread-regime rows: 2,640
RV32-regime rows: 3,300
RV96-regime rows: 3,300
direction-attribution rows: 1,320
neighbouring-horizon rows: 660
concentration rows: 660
sample-class rows: 660
```

All twenty-five R3 acceptance checks passed.

## Sample classes

```text
standard: 572 combinations
moderate: 44 combinations
sparse: 44 combinations
```

The classification is descriptive. R3 did not delete the 44 sparse combinations. R4 must state explicitly whether and how each sample class can be selected before any candidate-specific selection result is opened.

## Fixed regime boundaries

### Entry spread in pips

```text
minimum: 0.266886227545
Q1:      0.502170460196
median:  0.566368216167
Q3:      0.628030520475
maximum: 3.917024189867
```

### RV32 in M15 close-to-close pips

```text
minimum: 1.494847106260
Q1:      3.803408407142
median:  5.263561121864
Q3:      7.480776616750
maximum: 54.587823067476
```

### RV96 in M15 close-to-close pips

```text
minimum: 2.010735550595
Q1:      4.489349342109
median:  5.901417569485
Q3:      8.109651612494
maximum: 34.623278100831
```

Initial Entries without the full RV32 or RV96 lookback were retained in regime `0 = warmup unavailable`. Both warmup regimes were present and passed acceptance.

## Diagnostics produced

R3 produced complete outputs for:

- all six calendar months;
- Q1 and Q2;
- five rolling two-month blocks;
- four rolling three-month blocks;
- five anchored development blocks and four metric ranks;
- four Entry-spread quartiles;
- warmup plus four RV32 quartiles;
- warmup plus four RV96 quartiles;
- long and short attribution;
- best-day, best-two-day, monthly and directional concentration;
- immediately neighbouring fixed horizons;
- fixed standard, moderate and sparse sample classes.

## Interpretation boundary

R3 output is internal development evidence, not independent validation. In particular:

- a high anchored rank is not a promotion decision;
- one profitable spread or volatility regime is not sufficient;
- a local horizon maximum is not an Exit;
- sparse combinations are not comparable to standard combinations without a separately frozen rule;
- the R3 artifact must not be used to revise the sixty Entry definitions or eleven horizons;
- H2 and 2025 remained unopened for the new candidates.

Candidate-specific R3 ranking and shortlist generation remain blocked until R4 common requirements, family caps, sample-class treatment, neighbouring-horizon rules and tie-breaking are committed.

## Principal hashes

```text
temporal_monthly.csv:
  64f0f4122e744d8f5e70e40a29f0939abfa14f4ea60f7e7201c3f21a56fc2a02
temporal_quarterly.csv:
  5c17f7cd24097f442bf6060bbbdad4de4f06cfcfab84b8ff474494e9403a298a
rolling_2month.csv:
  12f4652d477850b01cea04c180bf0d476c36b924bd243a307ec48a33407bf165
rolling_3month.csv:
  e9603b691a9e3fec444a05eee47e2768166f075fd2f6c7ad6de1a141ff976f60
anchored_ranking.csv:
  f6fe5b1043482892ee69d361cc89641c0f2f8c3a7338727c44067a573be16158
spread_regime.csv:
  8c63fe488b8a391eb256437810b130ff2c401157c9bcf1353c6ecf91e7d89fd8
rv32_regime.csv:
  135e4c40fed0dd5cd714e2369d1418ec1d30e1cab589c5eadeb05e16633d9251
rv96_regime.csv:
  a047c500c052c0906d7203cbe00d8ac3e3d34c77ee0687175ce4cb6b9242202a
direction_attribution.csv:
  b8fdb1380631e973f32a61c5b082ed9757fa1e716baf33b54f06147ecc601f7e
horizon_neighborhood.csv:
  504aed6f485264435c6a19c0e0a9f531713b7869647d2e10350d892cea278525
concentration.csv:
  c29d725705710fdec7e0451cead170c4a6eabbd9b43661bb4983404407737ab5
sample_classes.csv:
  f0218afd9c647c1ffc72261c134eb1ed54024c9da7bf090e4b419d5209155239
entry_regime_map.csv.gz:
  73d54b2194e21859c39a24a8e47d472b3d56eef552f593eda8fbc0a5bdceced2
regime_edges.json:
  adc57034894c9a2a25ac01119f02c9853d2f53f25cf9e00b596813557dd3f5cb
r3_acceptance.json:
  17ef172240b4f7ee071634e99562fee811696497c49ef331c215b688f9a79d15
```

## Next stage

The next operation is to preregister R4 selection rules. R4 may retain no more than two representatives per family and eight overall. No R3 candidate-specific shortlist is opened before that preregistration is committed.
