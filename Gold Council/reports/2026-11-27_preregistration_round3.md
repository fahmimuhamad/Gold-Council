# Pre-registration — Round 3 (written BEFORE any round-3 code or result)

Date: 2026-11-27. Approved by user ("yes"). Frozen once committed.
Research basis: reports/2026-11-27_strategy_research_round3.md.

## Data, period, costs
- **Data:** Dukascopy XAUUSD H1 BID (UTC). Daily candles are NY-close (same resampler as round 2).
- **Period:** DEV only, up to 2022-02-04 (same boundary). Validation and holdout stay sealed.
- **Costs per round trip:** spread 0.44 + slippage 0.10 at entry and at exit (same as before). Financing 4%/yr pro rata for positions held across the daily rollover. Test A never crosses the rollover, so it pays no financing.
- None of these strategies has a stop in its source. Results are therefore measured as **net return per trade in basis points** (bp), not in R.

## Tests (3; one frozen parameter set each)
| ID | Rule |
|---|---|
| R3-A Asian drift | Every day where both bars exist: **buy at the open of the 23:00 UTC bar, sell at the open of the 07:00 UTC bar** (= close of the 06:00 bar). Long only, no stop. Skip a session if either bar is missing; never hold longer. |
| R3-C RSI(2) | NY-close daily candles. RSI(2) uses Wilder smoothing. Signal at a daily close when **close > SMA(200) and RSI(2) < 5** → buy at the next daily open. **Exit at the next open after a daily close > SMA(5).** Long only, no stop, one position at a time. |
| R3-W Weekend | NY-close daily candles. If the **Friday close > SMA(200)** (computed at that Friday's close): buy at the Friday close and sell at the following Monday close. Otherwise flat. Long only. |

## Statistics and pass criterion
For each test, from net per-trade returns:
1. **Mean net return > 0.**
2. **Lower bound of the 95% block-bootstrap CI > 0** (block = 5 trades).
3. **≥ 100 trades.**
4. **One-sided p-value from a Newey–West t-statistic (lag 5), Holm-Bonferroni across these 3 tests at α = 0.05.** The strictest threshold is p < 0.0167.

All four must hold to pass. A pass earns **one** run on the validation segment, unchanged.

Also reported (informational): the **Deflated Sharpe Ratio** (Bailey & López de Prado 2014), using N = 11 cumulative trials. Trial-Sharpe variance is estimated from all 11 per-trade Sharpe ratios, with rounds 1–2 recomputed on the same engine.

## Known limits
- Spread is the bar-close spread, not time-weighted. Test A's cost per unit of movement is about 40% worse in Asian hours (reviewer's feasibility check).
- 23:00 UTC is fixed in UTC and does not shift with DST. It is 18:00 NY in winter and 19:00 NY in summer, both after the daily rollover.
