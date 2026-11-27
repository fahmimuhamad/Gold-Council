# Results — Round 3 (as pre-registered)

- **Pre-registration:** reports/2026-11-27_preregistration_round3.md (commit 8533aac, before code and results).
- **Pre-run review:** PASS, no defects. Two hardening checks were added before the run (commit after 3b4a28c).
- **Data:** Dukascopy XAUUSD, DEV only (2015-01 → 2022-02-04).
- **Costs:** spread 0.44 + slippage 0.10 per fill; financing 4%/yr where positions cross the rollover.
- **Cumulative trials: 11.**

| Test | Trades | Mean net/trade | 95% CI | NW t | p (one-sided) | Holm threshold | DSR | Verdict |
|---|---|---|---|---|---|---|---|---|
| R3-A Asian drift 23→07 UTC | 1,829 | **−1.10 bp** | [−2.84, +0.59] | −1.27 | 0.898 | 0.025 | 0.000 | FAIL |
| R3-C RSI(2) daily | 17 | +1.58 bp | [−80.6, +86.7] | 0.04 | 0.486 | 0.0167 | 0.090 | INSUFFICIENT SAMPLE |
| R3-W Weekend long (> SMA200) | 201 | −13.27 bp | [−23.3, −2.4] | −2.49 | 0.994 | 0.050 | 0.000 | FAIL (significantly negative) |

**Nothing passes; nothing goes to validation.**
RSI2 note: one position may be closed at the last DEV close (end-of-sample mark), per the reviewer's minor point 1.

## Diagnostic: gross returns (zero cost), NOT a test
| | Mean gross/trade | 95% CI | t |
|---|---|---|---|
| Asian drift | **+3.55 bp** | **[+1.81, +5.25]** | **4.10** |
| RSI(2) | +13.7 bp | [−66.9, +97.1] | 0.32 |
| Weekend | −5.55 bp | [−15.7, +5.4] | −1.04 |

Asian drift, gross mean by year (bp/day):

| 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|
| +5.9 | +7.6 | +2.3 | −0.9 | +1.0 | +2.9 | +6.4 |

## Interpretation
- **The Asian-session drift is a real, statistically strong *gross* effect in DEV**, consistent with Blose, Gondhalekar & Kort (2018). It is positive in 6 of 7 full years.
- **It is not tradeable at the assumed costs**: about 4.6 bp per round trip against about 3.6 bp of drift.
- This is now a **cost question, not a signal question.** The assumed cost is conservative: p75 bar-close spread plus 0.10 slippage on each side.
- The legitimate next step is a **new pre-registered test using a real broker's measured all-in cost** (raw spread + commission). Picking a lower cost now, after seeing the gross number, would be data snooping. The cost must come from the broker, not from the result.
- **RSI(2):** only 17 trades in 7 years; gold rarely meets the conditions. No conclusion possible.
- **Weekend long:** significantly negative even before the 3-day financing. Drop it.
