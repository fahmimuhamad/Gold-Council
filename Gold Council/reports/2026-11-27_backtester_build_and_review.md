# Backtester (D-12, baseline A) — 2026-11-27

Built: `src/gold_council/backtesting/engine.py` (replay, metrics, block-bootstrap CI, chronological 60/20/20 split with embargo, sealed holdout) and `backtesting/plans.py` (draft plan builders: S16 Donchian with 2×ATR stop and 2R target; S23 CRT with stop beyond purge and target at 50% or opposite end). CLI: `gold-council backtest`. Each run saves a manifest (data sha256, code commit, costs, split, fill rules, data label) plus trades.csv under reports/backtests/<run_id>/ (gitignored). Every holdout access is appended to reports/holdout_access_log.md.

Conservative fill rules: entry at the next bar's open (plus latency), never the signal bar. If SL and TP are inside the same bar, the SL counts first. A gap through the SL exits at the open. A gap through the TP pays only the TP. Spread and slippage are adverse on both legs. If the fill bar opens already past the stop or target, there is no fill (mirrors the risk engine).

Independent review: first verdict FAIL. Fixed with regression tests:
- MAJOR: SNR freshness wasn't idempotent: a second call leaked later data, and one test passed only because of the bug. Now each walk restarts from the formation role.
- Entry-bar gaps past the stop/target are now an explicit NO_FILL_GAPPED (reported), consistent with the risk engine.
- The run ID now covers all settings (a silent overwrite was possible before).
- Holdout unseal needs a reason of 20 or more characters and is logged.
- A gap entirely over a level now counts as a break.
The reviewer found no lookahead in the plan builders, fills, BOS, swings or CRT. R, profit factor, drawdown, bootstrap and split boundaries were checked correct.

Tests: 116 passed.

Sanity run on SYNTHETIC random-walk H1 data (3,000 bars, dev segment, spread 0.30, slippage 0.05):
| strategy | trades | win rate | expectancy R | 95% CI (block bootstrap) |
|---|---|---|---|---|
| donchian | 49 | 34.7% | +0.01 | [−0.29, +0.38] |
| crt_mid | 449 | 36.3% | −0.50 | [−0.58, −0.42] |
This is what random data should produce: no edge, and costs hurt small-target strategies. **These numbers say nothing about XAUUSD.** Real broker history is required.

Limitations: OHLC only (no tick data), no swaps/commission schedule, fixed costs, no limit orders, single position.
