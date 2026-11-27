# Gold Council roadmap and prioritized backlog

Updated 2026-11-27 by the coordinator. Status words mean: NOT STARTED / IN PROGRESS / BLOCKED / DONE (DONE only when the gate has actually been tested).
Mode: interactive Claude subscription, offline research only. `allow_real_account: false` is permanent unless you explicitly ask otherwise.

## Milestones

| M | Deliverable | Status | Blocked by |
|---|---|---|---|
| M0 | Scaffold, config, CLI, mock fixtures, tests | **DONE** (85 tests pass) | — |
| M1 | 10 essential sources, local FTS5 library | IN PROGRESS: code done + tested; 0 sources ingested | books (U-01) |
| M2 | Strategy registry + regime engine | IN PROGRESS: registry, 6 detectors, draft regime engine tested | reviewed definitions; real data for thresholds |
| M3 | Read-only MT5 data bridge | NOT STARTED | your Mac + MT5 (cannot be done in this cloud container) |
| M4 | Manual Claude council on frozen snapshots | NOT STARTED | M2, M3 (or exported CSV) |
| M5 | Orchestration (mock adapter) + deterministic risk engine | IN PROGRESS: risk engine done + independently reviewed | orchestration not started |
| M6 | Replay/backtest + baselines | IN PROGRESS: engine built + reviewed; no real data yet | real XAUUSD history |
| M7 | Dashboard + journal (Telegram deferred) | NOT STARTED | M5, M6 |
| M8 | Forward paper trading (interactive, on demand) | NOT STARTED | M6 gates |
| M9 | MT5 demo-only executor | NOT STARTED | M8 gates; demo account |

## Development backlog (in order)

| ID | Pri | Task | Owner | Depends |
|---|---|---|---|---|
| D-01 ✅ | P0 | Restore original `.claude/agents/` (18 specialists + assistant) and skill from your starter zip, **or** approve me regenerating them from spec Step 13/25 | you → coordinator | — |
| D-02 ✅ | P0 | `.gitignore` protecting knowledge/raw, data/, *.db, .env, credentials | coordinator | — |
| D-03 ✅ | P0 | M0 scaffold: pyproject (`gold-council` CLI), src/gold_council packages, config.yaml (offline, risk defaults, `allow_real_account: false`), .env.example without keys | coordinator | D-02 |
| D-04 ✅ | P0 | M0 tests: CLI help, config validation, assert no execution permission; run pytest for real | coordinator + auditor | D-03 |
| D-05 ✅ | P1 | Knowledge ingestion + SQLite FTS5 search (Step 6), with tests using public-domain/own-authored fixtures | coordinator | D-03 |
| D-06 ⚠️ | P1 | Ingest first open-access papers (PBO, DSR, Pseudo-Math) once you approve downloads | librarian → coordinator | D-05, U-02 |
| D-07 ✅ | P1 | Deterministic risk engine + paper broker (Step 18) with adversarial tests | coordinator | D-03 |
| D-08 ✅ | P1 | Strategy registry YAML schema; simple detectors that need no disputed definitions: S16 Donchian, S17 ATR compression, S18 NR7, S21 z-score, S08/S09 ORB, 3-candle FVG geometry | coordinator | D-03 |
| D-09 ✅ | P1 | Regime engine (Step 10), point-in-time, UNKNOWN state | coordinator | D-08 |
| D-10 ✅ | P2 | CSV importer + validator for MT5 exports (works on files you upload) | coordinator | D-03 |
| D-11 ◐ | P2 | MT5 read-only exporters (.mq5). Code can be written here; compile/verification needs your Mac | coordinator → you | D-10 |
| D-12 ✅ | P2 | Backtest replay, A baseline (deterministic only), leakage tests | coordinator | D-08, D-10, data |
| D-13 | P3 | Manual council run (Step 14) as Claude Code subagents | coordinator | D-01, M2, M3 |
| D-14 | P3 | Dashboard (read-only) | coordinator | M5/M6 |
| — | Deferred | API adapter, Telegram, scheduled service, demo EA | — | your explicit go-ahead; CLAUDE.md mode |

## Research / knowledge backlog

| ID | Pri | Item | Owner | Status |
|---|---|---|---|---|
| R-01 | P0 | Verify lawful sources for 9 free papers/datasets | Research Librarian | PARTLY DONE: 6 found open, P02/DGS10/WGC unconfirmed |
| R-02 | P0 | Rights/edition check for 10 P1 books | Research Librarian | DONE: all paid; Street Smarts out of print |
| R-03 | P0 | MSNR + Alchemist definitions | you → coordinator | PARTLY DONE: E03 received + extracted; OCL/rejection/QML open |
| R-04 | P1 | ICT official definitions: FVG, displacement, CISD, liquidity sweep, Turtle Soup variants | Librarian → you (transcripts/notes) | OPEN |
| R-05 | P1 | Broker specifics: symbol suffix, server time/DST, tick value, commissions, swaps | **you** (from MT5) | OPEN |
| R-06 | P2 | P2 books (8) | Librarian | OPEN |
| R-07 | P2 | Macro data adapters: FRED/ALFRED, CFTC COT, WGC | Librarian → coordinator | OPEN |
| R-08 | P3 | P3 books (6) | Librarian | OPEN |

## Things only you can do (U-list)

- U-01 Buy or provide authorized copies of the P1 books (start with Aronson, López de Prado, Chan, Grimes) and place them locally in `knowledge/raw/`. They stay out of Git.
- U-02 Approve downloads of the open-access papers into this project.
- U-03 Provide MSNR/Alchemist original materials or your own notes.
- U-04 Find the original `.claude/` folder from the starter zip (D-01).
- U-05 Export multi-year XAUUSD/XAGUSD history from MT5 (later, M3).

## Progress log
- 2026-11-27: D-01 (agents regenerated from spec), D-02, D-03, D-04, D-05, D-07, D-08 (6 detectors), D-09 (draft), D-10 done and tested. D-06: the paper sites block automated downloads (bot check), so the papers need a browser. FRED yields downloaded. The independent review found 3 major risk defects; all are fixed with regression tests.
- 2026-11-27: Received E03 Alchemist + E04 TS&CRT. Ingested, vision-reviewed key diagrams, extracted definitions (reports/2026-11-27_msnr_crt_definitions.md). Added SNR/freshness, BOS, CRT, Turtle Soup detectors. 103 tests pass.
- 2026-11-27: D-12 backtester built; independent review FAIL -> 5 fixes; 116 tests pass. Synthetic sanity run shows no edge (as expected).
- 2026-11-27: D-11 read-only MT5 history export script written (not compiled - no MetaEditor here). Importer supports broker clocks like America/New_York+7. 118 tests pass.
