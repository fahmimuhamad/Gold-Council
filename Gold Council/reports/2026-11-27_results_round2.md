# Results — Round 2 (as pre-registered)

- **Pre-registration:** reports/2026-11-27_preregistration_round2.md (commit d69857b, before code and results).
- **Pre-run independent review:** PASS (no leakage). One conservative financing fix was applied before the run (commit 9c9ac5e).
- **Data:** Dukascopy XAUUSD resampled to NY-close candles. DEV only, up to 2022-02-04.
- **Costs:** spread 0.44 + slippage 0.10 per fill, plus financing 4%/yr on longs and shorts.

| Test | Trades | Win rate | Expectancy (R) | 95% CI | Max DD (R) | Zero-cost expectancy | Verdict |
|---|---|---|---|---|---|---|---|
| R2-1 Donchian D1 20/10 | 58 | 25.9% | −0.224 | [−0.494, +0.145] | 13.5 | −0.066 | INSUFFICIENT SAMPLE |
| R2-2 Donchian H4 20/10 | 304 | 30.3% | **+0.083** | [−0.128, +0.287] | 18.6 | +0.208 | FAIL (CI includes 0) |
| R2-3 CRT H4, 1/5/9 am NY | 1,295 | 58.1% | −0.155 | [−0.199, −0.111] | 201.8 | −0.047 | FAIL |
| R2-4 CRT D1 + weekly bias | 189 | 59.8% | −0.052 | [−0.182, +0.075] | 19.3 | +0.017 | FAIL |
| R2-5 Donchian D1 + regime | 21 | 33.3% | −0.018 | [−0.597, +0.822] | 6.6 | +0.202 | INSUFFICIENT SAMPLE |

**Trials so far: 8** (3 in round 1, 5 in round 2). None passed, so nothing moves to validation.

## Reading the results honestly
- **CRT improved a lot with the method's own filters and a wider stop.** H4 went from −0.56R (round 1, H1) to −0.155R. Daily CRT with weekly bias is about −0.05R, and roughly break-even before costs (+0.017R). The win rate rose to about 59%. Still **no edge**: the gain per win is too small relative to the loss per stop.
- **Donchian H4 is the only positive result (+0.083R)**, but the confidence range is wide (−0.13 to +0.29). By the pre-registered rule this is **not evidence**, and with 8 trials one positive-looking result is expected by chance. Costs take about 0.12R per trade, mostly financing on multi-day holds.
- **Daily Donchian had too few trades** (58 and 21) in 7 years of DEV data with one position at a time. The test can't say yes or no. A daily system needs more history, not different settings.

## Candidate next steps (each needs its own pre-registration; NOT tuning of the above)
1. **More history**, so daily tests have enough trades. Dukascopy gold history may go back to about 2003; this would roughly double the DEV sample for D1 without changing any rule.
2. **Council demonstration** on a sample of real CRT/Donchian setups, to see whether agents filter out losers. This is spec baseline C vs A.
3. Retest on **broker data with real swaps** before any conclusion about costs.
