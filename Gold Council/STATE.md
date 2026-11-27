# Project state
Updated: 2026-11-27 (coordinator)

Current milestone: **M0 DONE** (gate passed: CLI help + 85 tests pass, offline-only, no execution capability, rules + roadmap exist).
Partly built ahead of schedule (tested, but their milestone gates are NOT passed): knowledge library code (M1), detectors/regime/registry (M2), risk engine (M5).
Next milestone: **M1, the knowledge library.** Code works, but no books or papers are ingested yet.

Facts:
- Tests: 147 passed (`.venv/bin/python -m pytest -q`). Details: reports/2026-11-27_m0_build_and_review.md
- Agents: 18 regenerated from spec in .claude/agents (not your originals). Skills: 10 in .claude/skills. Restart Claude Code to load them.
- Library: 2 sources INDEXED (E03 Alchemist, E04 TS&CRT; 24 chunks; search verified). FRED DFII10/DGS10 downloaded to data/historical/macro (latest values, not vintages).
- Strategies: 16 drafts (S04-S07 now source-backed, new S23 CRT, F01 BOS), 0 approved, 0 able to emit candidates.
- Detectors: 14 (+ FVG lifecycle/CE/IFVG, displacement, liquidity sweep, CISD, volume imbalance - ICT secondary-tier drafts).
- OCL = Open-Close (Gap) level (user decision).
- Trading: no order execution exists. allow_real_account is hard-locked false.
- Environment: this cloud session now uses the personal "gold-council" environment (allows eScholarship, AMS, SSRN, FRED/ALFRED, CFTC, AQR).

Real data: Dukascopy XAUUSD H1 2015-01..2026-10 (70,063 bars, local only, gitignored).
Round 1 results (DEV 2015-2022): Donchian, CRT-50%, CRT-far all FAIL, no edge after costs (reports/2026-11-27_results_baseline_A_round1.md).
Round 2 (NY-close H4/D1, trend exits, CRT time/bias filters): 3 FAIL, 2 INSUFFICIENT SAMPLE; best = Donchian H4 +0.083R with CI incl. 0 (reports/2026-11-27_results_round2.md). 8 trials total, 0 passes.
Round 3 (Asian drift, RSI2, weekend): 0 passes; 11 trials total. Asian drift has a real GROSS effect (+3.55bp/day, t=4.1) but costs ~4.6bp kill it (reports/2026-11-27_results_round3.md). Next: broker all-in cost needed.
Backtester: baseline A (OHLC, conservative fills, sealed holdout) built + reviewed; sanity-checked on SYNTHETIC data only (reports/2026-11-27_backtester_build_and_review.md).

Not implemented: paper broker service, council orchestration, MT5 exporters, dashboard, alerts.

Next actions (coordinator, no user input needed):
1. CFTC COT + AQR dataset adapters.
2. Real XAUUSD history: mt5/GoldCouncilHistoryExport.mq5 is written (NOT compiled); user runs it per mt5/README.md -> first real baseline runs on the dev segment.
Blocked on user (optional): book purchases, MSNR/Alchemist notes, MT5 history export, 3 paper PDFs via browser.
