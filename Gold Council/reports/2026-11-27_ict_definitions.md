# ICT definitions: FVG, displacement, sweep, CISD — 2026-11-27

You have no ICT notes, so the Research Librarian searched for ICT's primary sources itself.
- **PRIMARY identified but not verified:** ICT teaches by video. The official videos were found by title: Core Content Month 04 "Fair Value Gaps" (FgacYSN9QEo), Month 04 "Liquidity Voids" (HTQgH11W37o), and 2022 Mentorship Episode 2 (tmeCWULSTHc). YouTube is not reachable from this environment. Even if it were, pulling video content into the library isn't cleared by the rights rules. So the actual content was not checked.
- **SECONDARY (used):** LuxAlgo, TradingView, Equiti, alphaexcapital, fxnx and tradingfinder explainers. They agree with each other. Catalog entry E05.

## Encoded definitions (`src/gold_council/strategies/ict.py`, all DRAFT)
| Concept | Rule as coded | Choices ICT doesn't quantify (parameters) |
|---|---|---|
| FVG | Candle-1 high to candle-3 low (bullish), wick-bounded; known at candle-3 close (existing `fvg`) | minimum size, timeframe |
| CE | 50% of the FVG | entry at CE vs edge |
| FVG lifecycle | ACTIVE → CE_REACHED → FILLED (wick through far edge) → INVERTED / IFVG (close beyond far edge) | `invalidate_on`: body close (default) or wick |
| Volume imbalance | Body gap with overlapping wicks, kept separate from FVG | — |
| Displacement | Body ≥ 1.5 × ATR(prior bar) and body/range ≥ 0.6 | **both thresholds are placeholders; ICT gives none** |
| Liquidity sweep | Wick through last confirmed swing, close back inside | swing size k (2) |
| CISD | Close through the open of the first candle of the latest opposite-direction run | single- vs multi-candle run |

Tests: `tests/test_ict.py` covers lifecycle states, threshold behaviour and sweep vs breakdown. It also runs no-lookahead checks on realistic-wick data for all 7 structure detectors and on the FVG lifecycle.

## Strategy registry
S01, S02 and S03 are now v0.2.0 with source references and narrowed unresolved lists. All remain **draft**: secondary sources aren't enough to approve.

## To make these PRIMARY (optional, only you can do it)
Watch the three videos above and note the timestamps where ICT defines each item. I'll then mark the definitions verified.
