---
name: mt5-engineering
description: Use when writing MT5 exporters or (later) the demo executor.
---
Exporters are read-only: CopyRates from position 1 (completed bars), FILE_COMMON, staging + ready marker, manifest with schema version. State the broker timezone explicitly. Never claim compilation without MetaEditor output from the user's machine. The executor (M9) is demo-only and must reject real/unknown accounts.
