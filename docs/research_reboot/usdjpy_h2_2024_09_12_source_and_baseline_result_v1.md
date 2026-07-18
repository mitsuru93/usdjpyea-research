# USDJPY H2 2024-09 to 2024-12 Source and Baseline Result v1

## Run

```text
workflow: Run USDJPY H2 2024-09 to 2024-12 Collect and Baseline
run_id: 29569149852
head_sha: ba7dc2a448bf626d6282e69397d91e00c05ec12c
```

The rerun completed the missing November day, December collection and all four monthly baselines. No A1/E3 candidate result was opened while verifying these data blocks.

## Acceptance method

The frozen workflow used `expected_records_mode: observed`. Each accepted monthly terminal manifest was therefore independently compared against the fixed set of all Monday-Friday UTC hours in that calendar month.

Acceptance required:

```text
unique terminal hours == fixed weekday hours
missing fixed weekday hours == 0
extra hours == 0
terminal hard errors == 0
effective coverage == 1.0
bar validation status == ok
monthly baseline output and trade files present
hard no-trade filtering enabled
base spread == 0.5 pips
cost mode == max_base_public
```

Explicit `no_ticks` records count as observed terminal states. They are not unobserved gaps.

## 2024-09

```text
fixed weekday hours: 504
unique terminal hours: 504
missing: 0
extra: 0
downloaded: 492
no_ticks: 12
hard errors: 0
effective coverage: 1.0
validation files: 88
validation status: ok
aggregate repair records: 1

source artifact_id: 8404664185
source artifact: public-fx-data-pilot-2024-09-USDJPY-aggregate-29569149852
source digest: sha256:c319547fdc00f1f77dd8c1574f0823a6ae5eab26837b9c8edfbc8ab4cddd8718

baseline artifact_id: 8423361030
baseline artifact: fx-session-baseline-2024-09-USDJPY-29569149852
baseline digest: sha256:1975d70dbbe40db942495fef8903078de73cf29af4cee65db176a18be6b45b31
baseline input files: 44 = 42 day M5/M15 files + 2 consolidated repair files
baseline summary rows: 10080
baseline trade rows: 135946
```

## 2024-10

```text
fixed weekday hours: 552
unique terminal hours: 552
missing: 0
extra: 0
downloaded: 540
no_ticks: 12
hard errors: 0
effective coverage: 1.0
validation files: 96
validation status: ok
aggregate repair records: 4

source artifact_id: 8408558801
source artifact: public-fx-data-pilot-2024-10-USDJPY-aggregate-29569149852
source digest: sha256:e65c8c3941ee417db58a0692abcf40d08cb69b0833571d2a49768d51080fa52c

baseline artifact_id: 8423402213
baseline artifact: fx-session-baseline-2024-10-USDJPY-29569149852
baseline digest: sha256:fbae37c01ef7d342fd524b738116563cc99206850f7e200c7dd42e7fdb7ce57d
baseline input files: 48 = 46 day M5/M15 files + 2 consolidated repair files
baseline summary rows: 10080
baseline trade rows: 124812
```

## 2024-11

The first-attempt aggregate is excluded:

```text
excluded artifact_id: 8412658745
excluded digest: sha256:8629b80f7196fe0fade05c0e31e2b1242e7b704edcb4229bc1bf74b0900e547e
reason: complete 2024-11-22 day artifact absent
```

The rerun recovered that day and produced the accepted source block:

```text
fixed weekday hours: 504
unique terminal hours: 504
missing: 0
extra: 0
downloaded: 493
no_ticks: 11
hard errors: 0
effective coverage: 1.0
validation files: 84
validation status: ok

recovered d16 artifact_id: 8421751697
recovered d16 digest: sha256:9f34820a3a01c9ee48928c5a205738224bde5a270364f40d7bad3f3b4cf2c1bc

accepted source artifact_id: 8421758330
accepted source artifact: public-fx-data-pilot-2024-11-USDJPY-aggregate-29569149852
accepted source digest: sha256:5c4f3e17100a63ff0f370d4810fb8f4ebca22ceb5192120ebfb8d58a788b12f4

baseline artifact_id: 8423419800
baseline artifact: fx-session-baseline-2024-11-USDJPY-29569149852
baseline digest: sha256:d83599f9080ed603fd5fc36cd0742a6281c26af4672bdf8e5216fcaf39779507
baseline input files: 44 = 42 day M5/M15 files + 2 consolidated repair files
baseline repair manifest records: 8
baseline summary rows: 8064
baseline trade rows: 127863
```

Artifact ID and digest are authoritative for November because the first attempt and rerun use the same display name.

## 2024-12

```text
fixed weekday hours: 528
unique terminal hours: 528
missing: 0
extra: 0
downloaded: 504
no_ticks: 24
hard errors: 0
effective coverage: 1.0
validation files: 92
validation status: ok
aggregate repair records: 7

source artifact_id: 8423343357
source artifact: public-fx-data-pilot-2024-12-USDJPY-aggregate-29569149852
source digest: sha256:6778b097f3345a677d4a726e3d81156faf89dbeffbfeded24c3dd8a7fa347dfa

baseline artifact_id: 8423376366
baseline artifact: fx-session-baseline-2024-12-USDJPY-29569149852
baseline digest: sha256:49e4748b6cd197e406ad14c59a37f873c96592bae4da1ba548ca11a0fad454f5
baseline input files: 46 = 44 day M5/M15 files + 2 consolidated repair files
baseline summary rows: 8064
baseline trade rows: 113770
```

## Common baseline configuration

All four accepted baseline artifacts report:

```text
symbol: USDJPY
timeframes: M5 and M15
base spread: 0.5 pips
cost spread mode: max_base_public
hard no-trade windows enabled: true
experiment summary present: true
trade output present: true
source hard errors after repair: 0
```

The generic session-baseline metrics are diagnostic and must not change A1/E3 definitions or the preregistered H2 gate.

## Decision

The 2024-09 through 2024-12 H2 source and monthly baseline blocks are accepted.

Together with the previously accepted 2024-07 and 2024-08 blocks, all six untouched H2 months are now ready for one joint evaluation of:

```text
A1_impulse_breakout_lb3_hold6
E3_trend_24h_resumption_hold6
```

The next operation is the preregistered full-block A1/E3 H2 evaluator. Monthly candidate results must not be used for parameter changes.
