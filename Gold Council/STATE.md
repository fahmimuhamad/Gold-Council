# Project state
Updated: 2026-11-27 (coordinator, cloud session)

Current milestone: **M0, project scaffold and config. NOT STARTED.**
Verification done: see reports/2026-11-27_setup_audit.md.

Facts:
- Implemented and tested features: **none**. No CLI, RAG, strategy engine, regime engine, market feed, risk engine, backtest, dashboard or EA exists.
- Agents: `.claude/agents/` was missing from the repo, so the 18 specialists, the assistant definition and the skill were not uploaded. Only `research-librarian.md` has been created (2026-11-27).
- Knowledge library: 0 local files. catalog.csv lists 24 books, 6 papers, 4 datasets and 3 education sources, all UNVERIFIED or NEEDS_USER_ACCESS.
- Trading: offline research only. No real-money or demo execution exists or is enabled.

Next actions (see ROADMAP.md):
1. User: locate the original `.claude/` folder (D-01/U-04) or approve regeneration.
2. Coordinator: .gitignore + M0 scaffold + real tests (D-02..D-04).
3. Librarian results → reports/2026-11-27_librarian_sources.md; user approves open-paper downloads (U-02).
