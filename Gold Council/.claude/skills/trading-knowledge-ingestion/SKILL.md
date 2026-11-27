---
name: trading-knowledge-ingestion
description: Use when adding, citing or reviewing sources in the knowledge library.
---
Check rights in knowledge/catalog.csv before ingesting. Place files in knowledge/raw/<topic>/ (never committed). Run `gold-council knowledge ingest --path <file>`, then `knowledge stats`. Record sha256 and local_path in the catalog. Flagged (scanned/blank) pages need manual review; never invent their content. Derived notes must cite chunk IDs and be labelled definition / empirical finding / author rule / interpretation / hypothesis.
