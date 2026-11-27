# Setup audit — 2026-11-27

Auditor: coordinator (Gold Council assistant), cloud Claude Code session.
Scope: verify configuration and agents, review spec, find the milestone, inventory knowledge.

## 1. Configuration and agent verification (actual findings)

| Item | Expected (README) | Found in repo | Status |
|---|---|---|---|
| GOLD_COUNCIL_SPEC.md | master guide | present (757 lines) | OK |
| CLAUDE.md | project rules | present | OK |
| STATE.md / DECISIONS.md | registers | present (minimal) | OK |
| knowledge/catalog.csv | source register | header only, 0 rows | EMPTY |
| knowledge/requests.md | missing-source queue | instructions only, 0 requests | EMPTY |
| `.claude/agents/gold-council-assistant.md` | primary assistant | **missing** | MISSING |
| 18 specialist agent files | `.claude/agents/*.md` | **missing** (no `.claude/` dir) | MISSING |
| 1 workflow skill | `.claude/skills/*/SKILL.md` | **missing** | MISSING |
| pyproject.toml, src/, tests/, config.yaml, .gitignore | M0 scaffold | **missing** | NOT STARTED |
| knowledge/raw, processed, strategies | folders | missing | NOT STARTED |

Probable cause: the upload ("Add files via upload", commit 5309efb) dropped hidden folders, so `.claude/` never reached the repository. Your original starter zip on your Mac likely still holds the 18 agents and the skill.

Action taken: created `.claude/agents/research-librarian.md` (research-only, no write/download tools) so knowledge acquisition can proceed. The other 17 specialists and the assistant definition were **not** recreated, because their original contents are unknown and re-inventing them could conflict with your versions. See backlog item D-01.

Environment: Linux cloud container, Python 3.12/3.13 available. No MT5, no Mac, no broker, no market data. No API key used or required. No `.gitignore` exists yet, so nothing copyrighted or secret may be added before D-02.

## 2. Spec review summary

The spec defines milestones M0–M9 (§13). Important for the current phase: CLAUDE.md overrides the spec's API, scheduling and execution steps (Steps 15–17, 22–24 unattended parts). The present mode is interactive on a subscription, with no API key, daemons, paid APIs or real-account execution.

Spec items that conflict with the current mode and are deferred:
- Step 15/16 Anthropic API adapter → replace with mock adapter + interactive Claude Code council (Step 14) for now.
- Step 22 Telegram bot, Step 23 scheduled paper service → deferred (would be unattended background services).
- Step 24 demo EA → late, demo-only; real accounts prohibited in V1.

## 3. Current milestone

**M0: project scaffold and config. Not started.** STATE.md described M0 as "foundation and verification". Verification is now done (this report), but none of the M0 deliverables exist: pyproject, `gold-council` CLI, config.yaml with `allow_real_account: false`, mock fixtures, tests, .gitignore. Nothing in M1–M9 is implemented.

## 4. Knowledge library inventory

- Local books/papers/transcripts: **0 files**. `knowledge/` contains only the two empty registers.
- Retrieval pipeline (Step 6): not implemented, so nothing can be INDEXED.
- Strategy definitions: none. All S01–S22 remain unresolved/disabled by rule.

## 5. Missing materials (all of it, prioritised)

P1 books (needed for M1): Grimes; Raschke & Connors; Dalton (Mind Over Markets); Shannon (AVWAP); Chan; Aronson; López de Prado (AFML); Villahermosa (Wyckoff 2.0); Murphy (Intermarket Analysis); Tharp.
P2 (8) and P3 (6) books: listed in catalog.csv.
Free research (Step 5): PBO, Deflated Sharpe, Pseudo-Mathematics, TSMOM + data, Century of Trend-Following, WGC, CFTC COT, FRED DFII10/DGS10, intraday TSMOM paper.
Primary strategy education: ICT core content/mentorships (official channels); **MSNR and Alchemist original materials. Only you can supply these, and they block S04–S06.**
Market data: multi-year XAUUSD/XAGUSD broker history (M3), contract specs and costs. Only you can supply these from your MT5.

Librarian findings: see `reports/2026-11-27_librarian_sources.md` (written once the Librarian finishes).
