# USDJPY 2024 Raw Tick Repair Run 29707697472 — Failure Classification v1

## Result

The 28 affected UTC days were recollected successfully. The run failed during monthly reconstruction because the source collection run contains more than 100 artifacts and the original download step did not enumerate all artifact pages.

Example: the January monthly artifact contained only `2024-01-08`, `2024-01-11`, and `2024-01-28`, then reported the other 28 calendar dates as missing day directories. The repaired January days themselves had 24 resolved hours and zero terminal errors.

## Recovery decision

Do not rerun the Dukascopy downloads and do not rerun failed jobs from run `29707697472`.

A dedicated recovery workflow reuses:

- original day packets from source run `29689427642`, attempt 1;
- repaired day packets from run `29707697472`, attempt 1;
- exact expected artifact names for every calendar date;
- paginated GitHub REST artifact enumeration.

The recovery workflow rebuilds all twelve months and publishes the durable release only after all 366 days and 8,784 UTC hours pass validation.
