# EURUSD 2024 Tick archive launch v1

The previous annual source Release is a bar-level authority and does not contain the complete 2024 Tick stream.

The corrective archive workflow is `.github/workflows/archive_eurusd_2024_tick_data_v1.yml`. It downloads all 2024 EURUSD calendar hours from the Dukascopy BI5 endpoint, preserves the exact vendor BI5 payload and a deterministic normalized UTC Bid/Ask Tick CSV.GZ representation, verifies that each month reproduces the accepted M1/M5/M15/H1 bars, and uploads twelve monthly packages to the durable GitHub Release `eurusd-2024-tick-data-archive-v1`.

The normalized Tick files are conversion inputs for MT4. A separate explicit conversion to FXT/HST or the selected MT4 Tick importer format remains required.
