# F05 failed reclaim exploration source

This directory stores the exact exploration bundle used for `F05_FAILED_RECLAIM_BASIC_V1` research preparation.

## Restore the original ZIP

```bash
base64 -d F05_structural_SL_event_sequence_bundle_v1.zip.b64 > F05_structural_SL_event_sequence_bundle_v1.zip
sha256sum F05_structural_SL_event_sequence_bundle_v1.zip
```

Expected SHA-256:

`463850652d08f7c3d6b170a345ba92a1f7228c9efb24eb0f89f90b13a59b686d`

The human-readable report is stored at:

`docs/research/F05_structural_SL_event_sequence_v1.md`

Execution scope must come from direct user instruction or a frozen protocol, not from Notion tasks.
