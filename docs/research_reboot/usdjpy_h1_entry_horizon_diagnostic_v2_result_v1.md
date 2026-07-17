# USDJPY H1 Entry-Horizon Diagnostic v2 Result

## Run

```text
workflow: Run USDJPY H1 Entry-Horizon Diagnostic v2
run_id: 29583719940
head_sha: e81fe4d1600a5c8d665c700d68218b6bf85299c3
artifact: usdjpy-h1-entry-horizon-diagnostic-v2-29583719940
artifact_digest: sha256:f95a0a450aa3b821dbcb20ea4f3410f345668606bf5f20a766a3e01d8a6e89e4
```

The run is accepted as the authoritative January-June entry-horizon diagnostic. All workflow steps completed successfully.

## Acceptance tests

The workflow passed all required checks:

- January-June bars were concatenated before signal generation.
- All 13 registered candidates matched the authoritative corrected H1 screen at their registered hold period.
- Trade count, win rate, average net pips, total net pips, profit factor, severe average and severe profit factor matched within the fixed tolerance.
- C1 and C2 mapped to one shared entry definition.
- Metadata reported 13 candidates and 12 unique entry definitions.
- Metadata reported `h2_data_read: false` and `promotion_decision: false`.

The invalid predecessor run `29582417411` remains excluded.

## A1 horizon surface

```text
bars   avg net pips   PF      positive months   severe PF
1      +0.165         1.027   3                 0.696
2      +1.033         1.167   4                 0.842
3      +0.925         1.145   4                 0.840
4      +1.057         1.174   3                 0.847
6      +2.016         1.281   4                 0.982
8      +1.703         1.212   4                 0.949
12     +1.317         1.141   4                 0.919
16     +1.383         1.148   4                 0.925
24     -0.233         0.980   3                 0.810
```

Interpretation:

- Six bars is the highest tested average for A1.
- The result is not an isolated point: horizons 2 through 16 are positive.
- The edge decays by 24 bars and becomes negative.
- A1 therefore appears to be a short-to-medium impulse effect rather than a full-day continuation effect.

## E3 horizon surface

```text
bars   avg net pips   PF      positive months   severe PF
1      -0.347         0.917   2                 0.516
2      -0.549         0.882   2                 0.552
3      -0.151         0.970   2                 0.642
4      +0.196         1.038   3                 0.693
6      +1.783         1.305   4                 0.950
8      +1.484         1.206   4                 0.922
12     +1.404         1.159   4                 0.926
16     +0.241         1.022   3                 0.844
24     +0.367         1.025   3                 0.886
```

Interpretation:

- E3 is negative at one to three bars and requires time to develop.
- Six, eight and twelve bars form a positive region rather than a single isolated peak.
- Six bars is the strongest tested point, but E3's path is slower than A1.

## Exit-sensitive candidates

The diagnostic confirms that the original six-bar screen did not rank entry definitions independently of exit horizon.

### C4 — Asia-range failed excursion

```text
bars   avg net pips   PF      positive months   severe PF
6      +0.848         1.151   4                 0.811
8      +1.115         1.169   4                 0.869
12     +1.817         1.230   3                 0.965
16     +2.932         1.323   4                 1.079
24     +4.198         1.376   4                 1.170
```

C4 strengthens as the horizon lengthens and is the clearest evidence that a candidate rejected under the original six-bar gate may represent a slower mechanism.

### C3 — 24-bar failed excursion

```text
bars   avg net pips   PF      positive months   severe PF
6      +0.295         1.041   4                 0.776
8      +0.918         1.118   4                 0.859
12     +1.606         1.180   4                 0.944
16     +1.325         1.126   3                 0.928
24     -0.931         0.935   1                 0.799
```

C3 has a broad positive region from eight to sixteen bars and reverses by 24 bars.

### E2 — eight-hour trend resumption

```text
bars   avg net pips   PF      positive months   severe PF
6      +0.031         1.005   3                 0.732
12     +0.759         1.085   4                 0.863
16     +0.479         1.045   3                 0.858
24     +3.607         1.290   5                 1.109
```

E2 shows a strong 24-bar result, but the preceding horizons are much weaker. This is a slower-horizon hypothesis requiring new validation, not a promoted strategy.

### B2 — Asia 00-07 breakout

```text
bars   avg net pips   PF      positive months   severe PF
6      -0.009         0.999   4                 0.703
12     +0.126         1.017   3                 0.764
16     +2.620         1.329   4                 1.053
24     +2.490         1.212   5                 1.027
```

B2 changes materially at 16 and 24 bars, but it has only 99 entries in H1 and remains sample-limited.

### B3 — prior-day breakout

B3 is positive only at six bars and negative at the neighboring tested horizons:

```text
4 bars:  -0.176
6 bars:  +2.378
8 bars:  -0.639
12 bars: -0.838
16 bars: -1.435
24 bars: -4.482
```

The six-bar result is an isolated horizon peak. B3 also remains below the predeclared 120-trade sample gate.

## Price-path timing

Descriptive 24-bar path statistics show different timing by mechanism:

```text
candidate   median bars to MFE   median gross MFE   median gross MAE
A1          7                    +17.1 pips         -15.1 pips
E3          11                   +19.6 pips         -19.5 pips
C4          13                   +20.9 pips         -14.1 pips
C3          11                   +20.0 pips         -16.6 pips
B2          13                   +18.8 pips         -20.1 pips
```

MFE and MAE are descriptive only. M15 OHLC does not reveal intrabar high-low ordering and these values are not executable exit results.

## Research decision

1. The active confirmatory H2 remains A1+hold6 and E3+hold6 only.
2. A1 and E3 are not merely isolated six-bar winners: each has a neighboring positive horizon region.
3. Exit horizon materially changes the assessment of C4, C3, E2 and B2.
4. No candidate is promoted from this development diagnostic.
5. The later exit-policy programme must be mechanism-based and must use a new pre-registration plus a later untouched validation block.
6. A full Cartesian sweep of hold, SL, TP, trailing, breakeven and partial-close parameters remains prohibited.
