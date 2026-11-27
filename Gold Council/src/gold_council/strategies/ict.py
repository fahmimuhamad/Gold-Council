"""ICT concept detectors - SECONDARY-tier DRAFT encodings.

ICT (M. J. Huddleston) teaches by video; primary content could not be verified from this environment.
Definitions follow consistent secondary explainers (catalog E05). Every choice ICT does not quantify is a
parameter with a named default; defaults are research placeholders, not ICT rules.
See reports/2026-11-27_ict_definitions.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np
import pandas as pd

from gold_council.features.indicators import atr
from gold_council.strategies.detectors import Event, _close_time, fvg
from gold_council.strategies.msnr import swing_points


# ---------------------------------------------------------------- FVG lifecycle

@dataclass
class FvgState:
    event: Event
    status: str = "ACTIVE"     # ACTIVE | CE_REACHED | FILLED | INVERTED (IFVG)
    history: list = field(default_factory=list)


def fvg_lifecycle(df: pd.DataFrame, bar: timedelta, upto: int | None = None,
                  invalidate_on: str = "body_close_far_edge") -> list[FvgState]:
    """Track each FVG after formation using only bars <= upto.

    Consequent encroachment (CE) = midpoint. FILLED = price traded through the far edge without a close
    beyond it. INVERTED = a candle CLOSE beyond the far edge (SECONDARY: becomes an inversion FVG).
    `invalidate_on`: 'body_close_far_edge' (default) or 'wick_far_edge' (stricter variant).
    """
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    end = len(df) - 1 if upto is None else min(upto, len(df) - 1)
    out = []
    for e in fvg(df, bar):
        if e.bar_index > end:
            continue
        s = FvgState(e)
        lo, hi, mid = e.levels["lower"], e.levels["upper"], e.levels["mid"]
        bull = e.direction == "BULL"
        for j in range(e.bar_index + 1, end + 1):
            far_wick = l[j] < lo if bull else h[j] > hi
            far_close = c[j] < lo if bull else c[j] > hi
            if (far_close if invalidate_on == "body_close_far_edge" else far_wick):
                s.status = "INVERTED"; s.history.append((j, "inverted")); break
            if far_wick and s.status != "FILLED":
                s.status = "FILLED"; s.history.append((j, "filled"))
            elif s.status == "ACTIVE" and ((l[j] <= mid) if bull else (h[j] >= mid)):
                s.status = "CE_REACHED"; s.history.append((j, "ce"))
        out.append(s)
    return out


# ---------------------------------------------------------------- displacement

def displacement(df: pd.DataFrame, bar: timedelta, atr_n: int = 14, body_atr_mult: float = 1.5,
                 min_body_ratio: float = 0.6) -> list[Event]:
    """Large one-sided candle. ICT gives NO numeric threshold; defaults are placeholders:
    body >= body_atr_mult x ATR(prior bar) and body/range >= min_body_ratio.
    ATR is taken from bar t-1 so the candle being judged does not inflate its own yardstick."""
    a = atr(df, atr_n).shift(1)
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    ev = []
    for t in range(len(df)):
        v = a.iloc[t]
        rng = h[t] - l[t]
        if pd.isna(v) or v <= 0 or rng <= 0:
            continue
        body = abs(c[t] - o[t])
        if body >= body_atr_mult * v and body / rng >= min_body_ratio:
            ev.append(Event("displacement", "BULL" if c[t] > o[t] else "BEAR", t, _close_time(df, t, bar),
                            {"body_atr": float(body / v), "body_ratio": float(body / rng)}))
    return ev


# ---------------------------------------------------------------- liquidity sweep

def liquidity_sweep(df: pd.DataFrame, bar: timedelta, k: int = 2) -> list[Event]:
    """Wick through the most recent CONFIRMED swing high/low and close back on the original side.
    Swing pivots (k bars each side) are usable only after confirmation (no lookahead)."""
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    swings = swing_points(df, k)
    ev, used = [], set()
    for t in range(len(df)):
        known = [s for s in swings if s[3] < t]
        sh = next((s for s in reversed(known) if s[1] == "HIGH"), None)
        sl = next((s for s in reversed(known) if s[1] == "LOW"), None)
        if sl and sl[0] not in used and l[t] < sl[2] <= c[t]:
            used.add(sl[0])
            ev.append(Event("sweep", "BULL", t, _close_time(df, t, bar), {"swept": sl[2], "swing_index": sl[0],
                                                                         "extreme": float(l[t])}))
        if sh and sh[0] not in used and h[t] > sh[2] >= c[t]:
            used.add(sh[0])
            ev.append(Event("sweep", "BEAR", t, _close_time(df, t, bar), {"swept": sh[2], "swing_index": sh[0],
                                                                         "extreme": float(h[t])}))
    return ev


# ---------------------------------------------------------------- CISD

def cisd(df: pd.DataFrame, bar: timedelta) -> list[Event]:
    """Change in State of Delivery (SECONDARY): a CLOSE through the OPEN of the first candle of the most
    recent run of consecutive opposite-direction candles (bodies/opens only, wicks ignored).
    Bullish: after a run of bearish candles, a close above that run's first open."""
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    ev = []
    run_dir, run_open, fired = 0, None, False
    for t in range(len(df)):
        d = 1 if c[t] > o[t] else -1 if c[t] < o[t] else 0
        if run_dir and run_open is not None and not fired:
            if run_dir == -1 and c[t] > run_open:
                ev.append(Event("cisd", "BULL", t, _close_time(df, t, bar), {"reference_open": float(run_open)}))
                fired = True
            elif run_dir == 1 and c[t] < run_open:
                ev.append(Event("cisd", "BEAR", t, _close_time(df, t, bar), {"reference_open": float(run_open)}))
                fired = True
        if d != 0 and d != run_dir:
            run_dir, run_open, fired = d, o[t], False
    return ev


def volume_imbalance(df: pd.DataFrame, bar: timedelta) -> list[Event]:
    """Body gap between consecutive candles whose wicks still overlap (kept separate from FVG)."""
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    ev = []
    for t in range(1, len(df)):
        top_prev, bot_prev = max(o[t - 1], c[t - 1]), min(o[t - 1], c[t - 1])
        top, bot = max(o[t], c[t]), min(o[t], c[t])
        wick_overlap = l[t] <= h[t - 1] and h[t] >= l[t - 1]
        if wick_overlap and bot > top_prev:
            ev.append(Event("volume_imbalance", "BULL", t, _close_time(df, t, bar), {"lower": top_prev, "upper": bot}))
        elif wick_overlap and top < bot_prev:
            ev.append(Event("volume_imbalance", "BEAR", t, _close_time(df, t, bar), {"lower": top, "upper": bot_prev}))
    return ev
