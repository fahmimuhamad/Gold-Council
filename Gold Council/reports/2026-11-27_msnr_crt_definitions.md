# MSNR / Alchemist and CRT definition extraction — 2026-11-27

Sources (user-supplied, stored locally, NOT in Git):
- **E03** "The Alchemist: MSNR x SMC x ICT", F.Y. Emmanuel (Alchemy Traders Network), 51 pp. 13 image-only pages. Pages 9, 11–13 and 33 were vision-reviewed. Chart-illustration pages 23–30 were not transcribed.
- **E04** "Mastering TS & CRT", @Sir_Crt (credits @ROMEO), 48 pp. Free distribution, per its last page.

Both are practitioner guides from Telegram. Neither is canonical ICT, and E03 is one teacher's *variant* of Malaysian SNR. Performance claims in them (80–90% win rate, 1:21–1:26 RR examples) are unverified and have **no** evidential weight here.

## Spec Step 7 audit questions — answered only from local documents

| Question | Answer (paraphrased) | Citation | Status |
|---|---|---|---|
| How is a Classic A/V level formed? | Body-based, ignoring wicks. A (resistance) = close of a bullish candle joined to the open of the next bearish candle. V (support) = bearish close to the next bullish open. | E03 p8, p12 | Resolved (level price variant open/close stored) |
| What is a Gap (open-close) SNR? | Junction between two same-direction candles. It is a "hidden zone" on the HTF and becomes a breakout level on the LTF. | E03 p9 (diagram) | Resolved geometrically |
| When is an A/V level fresh? | Not yet touched by any wick or body. Any touch makes it unfresh. | E03 p14 | Resolved |
| Breakout / flip? | A body close through the level flips its role (SBR / RBS). After the flip the level is "fresh again" in its new role. | E03 p14–15 | **Ambiguous**: when freshness resets after a flip. Encoded interpretation is named in code |
| How is an OCL formed? | **Not defined in E03.** The term is used on p40 and p45 only. Working hypothesis: Open-Close Level = Gap SNR. | E03 p9, p40, p45 | **UNRESOLVED**: needs your confirmation or another source |
| What is a valid BOS? | Body close beyond a swing high/low. A wick through does not count. Wait for the retracement and trade in the BOS direction. | E03 p36–37 | Resolved, except swing length k |
| Confirmation timing (Alchemist)? | HTF fresh level is tapped with a wick rejection, then a breakout 2 TFs lower (W→H4, D→H1), then a pullback to the right shoulder / QML. | E03 p22 | Partly resolved (QML, rejection thresholds open) |
| Rejection candle? | Long wick plus a thicker body closing away from the level ("better than a pin bar"). | E03 p16–17 | **UNRESOLVED**: no numeric thresholds |
| Trendline entry? | Connect at least two SNRs. Enter only on a wick rejection at point 3, never point 2. Invalid if a candle closes through. Not usable on Gap SNR. | E03 p32–33 | Discretionary drawing; not automatable yet |
| Turtle Soup? | False breakout of an old high/low: a wick beyond with no close beyond. | E04 p4 | Resolved geometrically (lookback open) |
| CRT? | Candle 1 sets the range. Candle 2 purges one side and closes back inside. Target 1 is 50%, target 2 is the opposite end. Stop goes beyond the purge. | E04 p32–33, p40 | Resolved for the 2-candle form |
| Bullish FVG / displacement / liquidity sweep (ICT) | No ICT definition in the local library. FVG search returns the unrelated "Gap SNR" (a terminology clash). | — | **UNRESOLVED**: needs ICT source (E01) |

## What became code (all DRAFT, cannot emit signals)
`src/gold_council/strategies/msnr.py`, tests in `tests/test_msnr_crt.py`:
- `snr_levels` (A, V, GAP_BULL, GAP_BEAR) and `update_freshness` (FRESH / UNFRESH / FLIPPED_FRESH, point-in-time).
- `swing_points` and `bos`. A pivot is usable only after its k right-side bars close. Body close is required.
- `crt` (2-candle; double purge skipped) and `turtle_soup_wick` (E04 variant, kept separate from Raschke/Connors).
- All of them pass the no-lookahead test, checked non-vacuous.

Registry updates: S04 v0.2.0, S05 v0.2.0, S06 v0.2.0, S07 v0.2.0, new **S23 CRT** (registered explicitly, per spec Step 9), and new feature **F01 BOS**.

## Still needed to approve any of these
1. Human review of each encoding. Only you can set `research_approved`.
2. OCL meaning, rejection-candle thresholds, swing length k, killzone clock times.
3. Real XAUUSD history to measure anything. Nothing here is evidence of an edge.
