# Strategy research for round 3 — 2026-11-27

Three research agents worked in parallel (strategy-discovery-researcher, macro+intermarket desks, momentum+mean-reversion desks). The independent-validation-reviewer then challenged the combined shortlist. Its verdict on the first draft was FAIL: "too many, too much overlap". It narrowed the list to at most 3 tests. The reviewer's data checks looked only at bar counts and spreads on DEV; no returns were computed.

## Shortlist after review
| # | Strategy | Evidence | Why it's new | Main risk |
|---|---|---|---|---|
| A | **Asian-session drift**: long 23:00→07:00 UTC, flat otherwise | MODERATE: Blose, Gondhalekar & Kort (2018, J. Econ. & Finance) find overnight gold returns positive and day returns negative; a CBS thesis finds the same "hat" pattern; WGC 2024 commentary | A different mechanism from breakouts (Asian physical demand vs Western selling) | Trades daily, so it needs gross drift above about 2.5 bp/day; Asian hours are quieter, so cost per unit of movement is about 40% worse. Must avoid the 20–21 UTC rollover spike |
| C | **RSI(2) mean reversion** (Connors): D1, long if close > 200SMA and RSI(2) < 5, exit on close > 5SMA | MODERATE on equity indices; untested on gold | Opposite of the failed trend tests | Gold isn't an equity index; may produce < 100 trades |
| W | **Weekend effect** (reinstated by reviewer) | WEAK: Blose & Gondhalekar (2013), findings unverified | Different mechanism (Sunday open gap); cheap to test on H1 | Only about 370 DEV weekends; calendar effects are prone to data mining |

## Parked (need data we don't have yet)
- **Intraday momentum** (Gao et al. 2018; Baltussen et al. 2021): needs minute data aligned to the 08:20 NY COMEX open. On hourly bars it would fail for measurement reasons.
- **COT positioning extremes**: needs a point-in-time CFTC dataset (Tuesday data, Friday release).
- **Pre-FOMC drift**: needs the historical FOMC calendar. Lucca & Moench found no drift outside equities.
- **News blackout filter / real-yield filter**: only as filters on a strategy that already passes.

## Dropped
- **Already failed or overlapping:** 12-month time-series momentum (about 74 DEV decisions, overlaps failed Donchian), Crabel/Williams volatility breakout (another range breakout), Asian-range fade (= CRT).
- **Effect gone or unconfirmed:** autumn effect (not replicated), London PM fix (the fix was replaced in 2015), gold/silver ratio (no out-of-sample evidence).

## Testing discipline for round 3
- Maximum 3 tests, one frozen parameter set each.
- Holm-Bonferroni within the round (strictest p < 0.0167).
- Deflated Sharpe Ratio reported with N = 11 cumulative trials.
- Pre-registered before any code or result.
