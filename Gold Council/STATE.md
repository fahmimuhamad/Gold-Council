# Project state
Updated: 2026-11-27 (coordinator)

Current milestone: **M0 DONE** (gate passed: CLI help + 85 tests pass, offline-only, no execution capability, rules + roadmap exist).
Partly built ahead of schedule (tested, but their milestone gates are NOT passed): knowledge library code (M1), detectors/regime/registry (M2), risk engine (M5).
Next milestone: **M1, the knowledge library.** Code works, but no books or papers are ingested yet.

Facts:
- Tests: 85 passed (`.venv/bin/python -m pytest -q`). Details: reports/2026-11-27_m0_build_and_review.md
- Agents: 18 regenerated from spec in .claude/agents (not your originals). Skills: 10 in .claude/skills. Restart Claude Code to load them.
- Library: 0 sources ingested. FRED DFII10/DGS10 downloaded to data/historical/macro (latest values, not vintages).
- Strategies: 14 drafts, 0 approved, 0 able to emit candidates.
- Trading: no order execution exists. allow_real_account is hard-locked false.
- Environment: this cloud session now uses the personal "gold-council" environment (allows eScholarship, AMS, SSRN, FRED/ALFRED, CFTC, AQR).

Not implemented: backtester, paper broker service, council orchestration, MT5 exporters, dashboard, alerts.

Next actions (coordinator, no user input needed):
1. D-12 backtest replay engine + baseline A on synthetic fixtures (no profitability claims).
2. D-11 MT5 read-only exporter source code (compiling it needs the user's Mac later).
3. CFTC COT + AQR dataset adapters.
Blocked on user (optional): book purchases, MSNR/Alchemist notes, MT5 history export, 3 paper PDFs via browser.
