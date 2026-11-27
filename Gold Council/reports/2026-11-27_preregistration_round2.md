# Pre-registration — Round 2 (written BEFORE any round-2 code or result)

Date: 2026-11-27. Approved by user ("yes"). This file is frozen once committed; changes would be a new round.

## Data and candles
- Dukascopy XAUUSD H1 BID (UTC), the same file as round 1, resampled to **broker-style NY-close candles**: broker clock = New York local time + 7h. This is the common MT5 "GMT+2/+3 on US DST" convention.
  - 4H candles open at broker 00/04/08/12/16/20, which is 17/21/01/05/09/13 New York time.
  - Daily candles run 17:00 NY to 17:00 NY.
  - Weekly candles run Sunday 17:00 NY to Friday close.
- A candle's `available_at` is its nominal end (open + duration). This is conservative for short holiday sessions.
- **Split by date** for every timeframe: DEV = up to 2022-02-04 (the round-1 DEV end). Validation and holdout stay sealed. **This round runs on DEV only.**

## Costs (fixed)
- Spread 0.44 and slippage 0.10 per fill (same as round 1).
- **Financing (new, because trades now last days):** 4% per year of entry price, charged pro rata on calendar time held, for longs AND shorts. Dukascopy has no swap data, so this is an assumption to be replaced by broker swaps later.

## Hypotheses (5 trials; parameters fixed, no tuning)
| ID | Timeframe | Entry | Stop | Exit / target |
|---|---|---|---|---|
| R2-1 Donchian D1 | Daily | Close beyond prior 20-day high/low → next open | 2 × ATR(14) | Close beyond the opposite **10-day** channel → next open (no fixed target) |
| R2-2 Donchian H4 | 4H | Same with 20/10 bars | 2 × ATR(14) | Opposite 10-bar channel |
| R2-3 CRT H4 timed | 4H | 2-candle CRT (E04) where **candle 2 opens at 01:00, 05:00 or 09:00 NY** → candle-3 open | Purge extreme ± 0.5 × ATR(14) | Opposite end of candle-1 range |
| R2-4 CRT D1 + weekly bias | Daily | 2-candle CRT in the direction of the weekly bias → next open | Purge extreme ± 0.5 × ATR(14) | Opposite end of candle-1 range |
| R2-5 Donchian D1 + regime | Daily | As R2-1, but only when ADX(14) ≥ 25 **and** efficiency ratio(20) ≥ 0.30 at the signal bar (regime engine draft thresholds, unchanged) | as R2-1 | as R2-1 |

**Weekly bias (E04 p18 "HTF order flow")**, from the last fully completed week vs the week before it:
- Close above the prior high → BULL. Close below the prior low → BEAR.
- Wick above the prior high but close at or below it → BEAR. Wick below the prior low but close at or above it → BULL.
- Both wicks, or neither → NEUTRAL, which means no trade.

## Pass criterion (unchanged)
DEV net expectancy > 0, lower 95% block-bootstrap CI > 0, and ≥ 100 trades. Fewer than 100 trades = "insufficient sample", not a pass.
5 trials this round + 3 in round 1 = 8 trials so far. Any pass will be reported alongside this count.

## Known limits
- CRT entries are at the next candle's open. The lower-timeframe "Model 1" entry in E04 is not mechanically defined, so it is not tested.
- No news filter (no point-in-time calendar yet).
