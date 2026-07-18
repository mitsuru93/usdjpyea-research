# USDJPY R4 Selection Implementation Note v1

The R4 evaluator was implemented only after the common selection configuration and preregistration were committed.

```text
configuration commit: 3fce36e107300225428f3efa09cb6e4421fe56c8
preregistration commit: a6f48b5dd2f4992a8ce8178d9471f4197a501bb1
```

A local implementation preflight using the accepted R2 and R3 artifacts confirmed that the evaluator compiles, produces all required files and passes its internal acceptance contract. The local output is not authoritative. Only a successful frozen GitHub Actions run and independently verified artifact may be accepted as the R4 result.

No R4 rule, threshold, rank component, family cap or redundancy threshold may be changed in response to the local or formal output.
