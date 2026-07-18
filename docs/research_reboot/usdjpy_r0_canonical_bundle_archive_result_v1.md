# USDJPY R0 Canonical Bundle Archive Result v1

## Decision

```text
archive: PASS
accepted R0 run: 29639548804
accepted Actions artifact_id: 8428199309
release_tag: usdjpy-r0-canonical-2024-v1
```

The accepted R0 canonical bundle is preserved independently of GitHub Actions artifact expiry.

## Archive run

```text
archive_run_id: 29639999593
archive_audit_artifact_id: 8428311106
archive_audit_artifact_digest: sha256:3e98b0970aaf970143585e67cce956358c992300964cb311e4b4f4fcb310ee71
```

## Release assets

```text
usdjpy-r0-canonical-2024-v1-run-29639548804-artifact-8428199309.zip
  sha256:d67db9b051a03050ddedb720d407b73cb48c5eacf7a441b1b8ff98dd77dc2015

usdjpy-r0-canonical-2024-v1-manifest.json
  sha256:8d70ddf794222fc5546be3b082fa7ff77bb07344e92c140bc4d8c791042bb521

SHA256SUMS
  sha256:5b3852407e43ff294ff2c661369894e2b81326fceab75f4f114b5b64ecb29417
```

All three assets are uploaded, the Release is neither draft nor prerelease, and the accepted Actions artifact ZIP digest is unchanged.

## Receipt

```text
docs/research_reboot/artifact_archives/usdjpy_r0_canonical_2024_v1/
  artifact_manifest.json
  release_receipt.json
  SHA256SUMS
```

The manifest records:

- R0 status `PASS`;
- twenty acceptance checks;
- accepted head `2d88fb846bbe77e256ee37abdf1dcbb462e3ebe4`;
- canonical M1/M5/M15/H1 gzip hashes;
- H1 and H2 normalized ledger hashes;
- H2 decision `neither_advances`;
- R1 unblocked;
- Core promotion false;
- MT4 promotion false;
- 2025 artifact access false.

The one-time archive workflow was removed after the receipt was committed.
