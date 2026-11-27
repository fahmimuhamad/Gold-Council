# Missing-source queue
Add one request per missing concept: request ID, requesting agent, exact concept, suggested source, reason, priority, status and next action. Allowed statuses: OPEN, SEARCHING, FOUND_OPEN, NEEDS_USER_ACCESS, UNAVAILABLE, VERIFIED_LOCAL, INDEXED. Never mark INDEXED without checking the actual retrieval pipeline.

| ID | Requested by | Concept | Suggested source | Reason | Pri | Status | Next action |
|---|---|---|---|---|---|---|---|
| RQ-001 | coordinator | Backtest overfitting (PBO), Deflated Sharpe, multiple testing | P01-P03 (catalog) | M6 evaluation integrity | P0 | FOUND_OPEN | Sites block automated download (bot check); optional 1-minute browser download into knowledge/raw/16_papers/ |
| RQ-002 | coordinator | Statistical validation of TA rules | B06 Aronson | M1/M6 | P0 | NEEDS_USER_ACCESS | User acquires authorized ebook |
| RQ-003 | coordinator | Leakage, purged CV, labeling | B07 López de Prado | M6 | P0 | NEEDS_USER_ACCESS | User acquires authorized ebook |
| RQ-004 | coordinator | ICT FVG, displacement, CISD, liquidity sweep, Turtle Soup variants | E01 ICT official | S01-S03, S07 definitions | P1 | SEARCHING | Librarian lists official playlists; user supplies notes/transcripts |
| RQ-005 | coordinator | MSNR Classic A/V, OCL, freshness, confirmation | E02 user materials | S04, S05 blocked | P0 | NEEDS_USER_ACCESS | User provides originals or own notes |
| RQ-006 | coordinator | Alchemist entry model | E03 user materials | S06 blocked | P0 | NEEDS_USER_ACCESS | User provides originals or own notes |
| RQ-007 | coordinator | Real/nominal yields as-released | D02 FRED/ALFRED | M3 macro context | P2 | VERIFIED_LOCAL (latest values only) | ALFRED vintages need a free FRED API key; deferred |
| RQ-008 | coordinator | Remaining P1 books (B01-B05, B08-B10) | catalog | M1 library | P1 | NEEDS_USER_ACCESS | Rights check by Librarian, then user purchase |
