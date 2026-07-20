# USDJPY 2024 Raw Tick Repair Recovery Acceptance v1

The recovery is accepted only when all twelve monthly manifests report `accepted: true`, annual totals report 366 present days and 8,784 resolved UTC hours, terminal error hours are zero, and negative-spread rows are zero.

A GitHub Release is created only after those checks pass. Any missing, duplicate, expired, or ambiguously named source or repair artifact blocks packaging.
