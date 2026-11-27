# M0 build + early M1/M2/M5 components — 2026-11-27

## What was built (and tested)
| Component | Files | Tests |
|---|---|---|
| Config with hard safety locks (`allow_real_account`, martingale, grid are `Literal[False]`; unknown keys rejected; frozen) | src/gold_council/config.py, config.yaml | tests/test_config_safety.py |
| CLI `gold-council` (status, knowledge, strategies, data validate, regime) | src/gold_council/cli.py | tests/test_cli.py |
| Deterministic risk engine (vetoes, sizing rounded down, drawdown stops, dedupe, kill switch, fail-closed state) | src/gold_council/risk/engine.py | tests/test_risk.py |
| Knowledge ingestion (PDF/TXT/MD, hashing, dedupe, page citations, scan flags) + FTS5/BM25 search with synonyms | ingestion/ingest.py, retrieval/search.py | tests/test_knowledge.py |
| Point-in-time indicators + detectors (FVG geometry, Donchian, NR7, ATR compression, z-score, DST-aware ORB) | features/indicators.py, strategies/detectors.py | tests/test_detectors.py (incl. no-lookahead for every detector) |
| Regime engine (draft thresholds, UNKNOWN when data/calendar missing) | regime/engine.py | tests/test_regime_registry.py |
| Strategy registry: 14 draft YAMLs (S01–S09, S16–S19, S21); none can emit candidates | strategies/registry.py, knowledge/strategies/ | tests/test_regime_registry.py |
| CSV importer/validator (explicit broker timezone required) | market_data/csv_import.py | tests/test_csv_import.py |
| 18 agent definitions + 10 skills regenerated from spec Steps 13/20/25 | .claude/agents, .claude/skills | not executable code |

Real test run: `.venv/bin/python -m pytest -q` → **85 passed** (2026-11-27, Python 3.12.3, Linux cloud container).
Real CLI runs: `status`, `strategies list/validate` (14 valid, all draft, emits=False), `knowledge stats` (0 sources), `data validate` and `regime` on a SYNTHETIC CSV (regime → UNKNOWN because no news calendar exists, as designed).

## Independent review (independent-validation-reviewer role)
First verdict: **FAIL**, with 3 major and 5 minor findings. All of them are now fixed with regression tests:
1. MAJOR: quote not checked against the signal. Fixed: executable-price sizing, entry-deviation limit, already-crossed SL/TP rejection.
2. MAJOR: strategy approval trusted a string on the signal. Fixed: the engine looks strategies up in the registry and requires `can_emit_candidates()`.
3. MAJOR: deleting the state file reset the kill switch. Fixed: missing state now fails closed and needs an explicit `initialize()`.
4–6. Input validation added (negative counters, NaN/inf, bad side, zero spec values, future quotes). Unexpected errors return a REJECTED decision.
7. Regime CLI now validates data, drops forming bars, and returns UNKNOWN on shuffled or duplicate data.
8. Search limit is clamped to 1–50.
The reviewer confirmed clean: no lookahead (tests are non-vacuous), no real-account bypass, FTS5 robust to hostile queries, .gitignore keeps raw books/data/db/.venv out of Git.

## Not built / limitations (honest list)
- No backtester, paper broker service, council orchestration, MT5 exporters, dashboard or alerts.
- Regime thresholds are untested drafts. They must be estimated on real development data.
- Risk-engine contract values in the tests are illustrative. Real broker specs (tick value, commission, stops level) are unknown.
- FRED yields downloaded are latest-revised values, not as-released vintages.
- Open papers (PBO, DSR, Pseudo-Math) could not be downloaded automatically: the sites run bot checks, which I did not try to bypass.
- The 18 agents are regenerations from the spec, not your original starter files.
