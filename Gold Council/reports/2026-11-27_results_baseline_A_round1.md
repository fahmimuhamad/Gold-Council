# Results — Baseline A, round 1 (as pre-registered)

Pre-registration: reports/2026-11-27_preregistration_baseline_A.md (committed before results, commit 96813cd).
- **Data:** Dukascopy XAUUSD H1 BID, UTC, 70,063 bars, Jan 2015 – Oct 2026. 142/142 months present, all 284 files verified. Validation: 0 duplicates, 0 bad OHLC, 2,931 gaps (weekends/holidays, not filled).
- **Segment:** DEV only, 2015-01-01 → 2022-02-04. Validation and holdout untouched.
- **Costs:** spread 0.44 (measured p75; median 0.338, p95 0.84), plus slippage 0.10 per fill.

| Hypothesis | Trades | Win rate | Avg win / loss (R) | Expectancy (R) | 95% CI (block bootstrap) | Max DD (R) | Verdict |
|---|---|---|---|---|---|---|---|
| S16 Donchian 20, 2×ATR stop, 2R target | 1,482 | 33.8% | +1.80 / −1.05 | **−0.088** | [−0.157, −0.021] | 142 | FAIL: no edge |
| S23a CRT 2-candle, target 50% | 8,133 | 32.1% | +0.40 / −1.02 | **−0.562** | [−0.580, −0.545] | 4,572 | FAIL: strongly negative |
| S23b CRT 2-candle, target opposite end | 8,967 | 37.4% | +0.80 / −1.17 | **−0.431** | [−0.455, −0.407] | 3,867 | FAIL: strongly negative |

None meets the pass criterion. Per the protocol, **nothing goes to validation and nothing is tuned.**

## Robustness diagnostics (not new tests; they only check whether the verdict is an artefact)
| | Ambiguous SL bars (SL and TP in the same hour, counted as loss) | Expectancy if ALL ambiguous bars were wins (impossible best case) | Expectancy with ZERO costs |
|---|---|---|---|
| Donchian | 4 (0.3%) | −0.080 | +0.013, CI [−0.059, +0.083] |
| CRT 50% | 1,233 (15.2%) | −0.284 | −0.152, CI [−0.172, −0.130] |
| CRT far | 505 (5.6%) | −0.303 | −0.027, CI [−0.060, +0.004] |

Interpretation:
- The losses are **not** caused by the pessimistic same-candle rule: even the impossible best case is negative.
- They are **not only** caused by costs: with zero costs the patterns show no gross edge either. CRT-50% is negative before costs.
- For CRT on H1, 43% of its stops are hit on the entry hour itself. The purge-based stop sits very close to the entry relative to normal hourly noise.

## What this does and does NOT mean
- It means: these **bare, mechanical** rules have no edge on hourly gold from 2015 to early 2022.
- It does **not** test the full CRT method as taught (E04): HTF bias, 1/5/9 am timing, 4H/Daily CRT with an LTF "Model 1" entry, killzones. Those filters are the method's claimed source of edge and are untested here.
- It does **not** test MSNR/Alchemist or ICT setups (entry/SL/TP still undefined in the sources).
- Three trials were run; no multiple-testing correction was needed, since none passed.

## Next candidates (each needs its own pre-registration before running)
1. CRT on **NY-close 4H / Daily** candles with the E04 time filter (1/5/9 am NY) and lower-TF entry, which is closer to the method as taught.
2. Regime-filtered variants (Donchian only in TREND regime), using regime thresholds estimated on dev.
3. Council demonstration (baseline C) on a sample of these real setups, once the council is built.
