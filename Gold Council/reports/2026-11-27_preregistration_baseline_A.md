# Pre-registration — Baseline A, round 1 (written BEFORE any real-data result)

Date: 2026-11-27. Author: coordinator. This file is not to be edited after results exist; any later change is a new round.

## Data
- Dukascopy XAUUSD hourly BID candles, UTC, Jan 2015 – Oct 2026. Closed-market hours dropped; ask close kept for spread.
- This is NOT the user's broker. Results show only whether a rule has any edge on gold *in general*; broker-specific costs come later.

## Split (fixed)
Chronological 60 / 20 / 20 (dev / validation / holdout) with a 24-bar embargo between segments (engine default).
- **This round runs on DEV only.**
- Validation is used only for configurations that pass the dev criterion below, unchanged.
- The holdout stays sealed.

## Costs (fixed before results)
- Spread = the **75th percentile** of measured hourly ask − bid closes over the whole file. This is a conservative single number, chosen before looking at strategy results.
- Slippage = 0.10 USD per fill. Commission is not modelled (Dukascopy spreads are all-in; this will be revisited with broker data).

## Hypotheses and fixed parameters (no tuning in this round)
| ID | Rule | Parameters |
|---|---|---|
| H1-S16 | Donchian breakout, next-bar-open entry | n=20, stop 2×ATR(14), target 2R |
| H1-S23a | CRT 2-candle, target 50% of candle-1 range | stop at purge extreme |
| H1-S23b | CRT 2-candle, target opposite end | stop at purge extreme |
All on H1. Three trials in total. That count matters when reading the results (multiple testing).

## Pass criterion for moving to validation
Dev net expectancy > 0 **and** the lower bound of the 95% block-bootstrap CI > 0 **and** ≥ 100 trades. Anything else is reported as "no evidence of edge" and is not tuned to look better.

## What would NOT be concluded
- A pass on dev is not evidence of profitability. It only earns a single validation run.
- A fail does not prove the idea is useless; it says these exact rules show no edge after costs on this data.
