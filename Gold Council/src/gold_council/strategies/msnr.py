"""MSNR / Alchemist and CRT detectors, from user-supplied sources (see reports/2026-11-27_msnr_crt_definitions.md).

Source IDs: E03 = "The Alchemist: MSNR x SMC x ICT" (F.Y. Emmanuel); E04 = "Mastering TS & CRT" (@Sir_Crt).
These are DRAFT encodings. Where the source is ambiguous, the chosen interpretation is named
and the alternative is selectable via a parameter. Nothing here is a trading signal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np
import pandas as pd

from gold_council.strategies.detectors import Event, _close_time


# ---------------------------------------------------------------- SNR levels (E03 p8-9, p12)

@dataclass
class SnrLevel:
    level_id: str
    kind: str              # CLASSIC_A | CLASSIC_V | GAP_BULL | GAP_BEAR
    role: str              # RESISTANCE | SUPPORT (current role; flips on breakout)
    price: float
    alt_price: float       # the other body edge (open of 2nd candle vs close of 1st)
    formed_index: int      # index of the 2nd candle; level known at its close
    available_at: pd.Timestamp
    status: str = "FRESH"  # FRESH | UNFRESH | FLIPPED_FRESH
    history: list = field(default_factory=list)   # (bar_index, event)


def _bull(o, c):
    return c > o


def _bear(o, c):
    return c < o


def snr_levels(df: pd.DataFrame, bar: timedelta, price_from: str = "close_first") -> list[SnrLevel]:
    """Detect body-based SNR levels between consecutive candles t-1, t (wicks ignored).

    E03 p8: A (resistance) = bullish close -> next bearish open. V (support) = bearish close -> next bullish open.
    E03 p9 (diagram): GAP bullish = two consecutive bullish candles (support at the junction),
    GAP bearish = two consecutive bearish candles (resistance at the junction).
    `price_from`: 'close_first' (close of t-1) or 'open_second' (open of t). On continuous markets these are
    nearly equal; the source treats them as one line. Both are stored.
    Doji (open == close) candles never form levels (unresolved in source).
    """
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    out = []
    for t in range(1, len(df)):
        a, b = (o[t - 1], c[t - 1]), (o[t], c[t])
        if _bull(*a) and _bear(*b):
            kind, role = "CLASSIC_A", "RESISTANCE"
        elif _bear(*a) and _bull(*b):
            kind, role = "CLASSIC_V", "SUPPORT"
        elif _bull(*a) and _bull(*b):
            kind, role = "GAP_BULL", "SUPPORT"
        elif _bear(*a) and _bear(*b):
            kind, role = "GAP_BEAR", "RESISTANCE"
        else:
            continue
        p1, p2 = float(c[t - 1]), float(o[t])
        price, alt = (p1, p2) if price_from == "close_first" else (p2, p1)
        out.append(SnrLevel(f"snr_{t}", kind, role, price, alt, t, _close_time(df, t, bar)))
    return out


def update_freshness(df: pd.DataFrame, lvl: SnrLevel, upto: int | None = None) -> SnrLevel:
    """Walk bars after formation (point-in-time: only bars <= upto) and update status.

    E03 p14: touched by wick or body => UNFRESH.
    E03 p15: a candle BODY closing through the level => flip (SBR/RBS), new role.
    Interpretation (flagged): after a flip the level is FLIPPED_FRESH; its first subsequent touch that does
    not close through again is recorded as 'flip_retest' and the level becomes UNFRESH afterwards.
    """
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    end = len(df) - 1 if upto is None else min(upto, len(df) - 1)
    lvl.status, lvl.history = "FRESH", []
    role = lvl.role
    for j in range(lvl.formed_index + 1, end + 1):
        touched = l[j] <= lvl.price <= h[j]
        if not touched:
            continue
        broke = c[j] > lvl.price if role == "RESISTANCE" else c[j] < lvl.price
        if broke:
            role = "SUPPORT" if role == "RESISTANCE" else "RESISTANCE"
            lvl.status = "FLIPPED_FRESH"
            lvl.history.append((j, "flip"))
        elif lvl.status == "FLIPPED_FRESH":
            lvl.history.append((j, "flip_retest"))
            lvl.status = "UNFRESH"
        else:
            if lvl.status == "FRESH":
                lvl.history.append((j, "first_touch"))
            lvl.status = "UNFRESH"
    lvl.role = role
    return lvl


# ---------------------------------------------------------------- swings & BOS (E03 p36-37)

def swing_points(df: pd.DataFrame, k: int = 2) -> list[tuple[int, str, float, int]]:
    """Fractal pivots: high[i] strictly greater than k bars each side (lows mirrored).

    Returns (pivot_index, 'HIGH'|'LOW', price, confirmed_index=i+k). A pivot is only usable after the
    close of bar i+k (right-side bars) - no lookahead. k is NOT given by the source (unresolved).
    """
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    out = []
    for i in range(k, len(df) - k):
        if h[i] > max(np.r_[h[i - k:i], h[i + 1:i + k + 1]]):
            out.append((i, "HIGH", float(h[i]), i + k))
        if l[i] < min(np.r_[l[i - k:i], l[i + 1:i + k + 1]]):
            out.append((i, "LOW", float(l[i]), i + k))
    return out


def bos(df: pd.DataFrame, bar: timedelta, k: int = 2) -> list[Event]:
    """Break of structure: a candle BODY CLOSE beyond the most recent confirmed swing (E03 p37:
    a wick through is NOT a BOS). Each swing can be broken once."""
    c = df["close"].to_numpy()
    swings = swing_points(df, k)
    ev, used = [], set()
    for t in range(len(df)):
        known = [s for s in swings if s[3] < t]      # confirmed strictly before bar t
        last_h = next((s for s in reversed(known) if s[1] == "HIGH"), None)
        last_l = next((s for s in reversed(known) if s[1] == "LOW"), None)
        if last_h and last_h[0] not in used and c[t] > last_h[2]:
            used.add(last_h[0])
            ev.append(Event("bos", "BULL", t, _close_time(df, t, bar), {"swing_index": last_h[0], "level": last_h[2]}))
        if last_l and last_l[0] not in used and c[t] < last_l[2]:
            used.add(last_l[0])
            ev.append(Event("bos", "BEAR", t, _close_time(df, t, bar), {"swing_index": last_l[0], "level": last_l[2]}))
    return ev


# ---------------------------------------------------------------- CRT & Turtle Soup (E04)

def crt(df: pd.DataFrame, bar: timedelta) -> list[Event]:
    """Candle Range Theory, 2-candle form (E04 p32-33, p40).

    Candle 1 (t-1) = range. Candle 2 (t) purges one side with a wick and CLOSES back inside the range.
    Bullish: low[t] < low[t-1] and low[t-1] <= close[t] <= high[t-1]. Bearish mirrored.
    Levels: range high/low, 50% (target 1), opposite end (target 2), purge extreme (stop reference).
    If candle 2 purges both sides it is skipped (ambiguous; 'double purge' is a separate variant in E04 p35).
    """
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    ev = []
    for t in range(1, len(df)):
        rh, rl = h[t - 1], l[t - 1]
        inside = rl <= c[t] <= rh
        below, above = l[t] < rl, h[t] > rh
        if not inside or below == above:
            continue
        mid = (rh + rl) / 2
        if below:
            ev.append(Event("crt", "BULL", t, _close_time(df, t, bar),
                            {"range_high": rh, "range_low": rl, "mid": mid, "purge_extreme": float(l[t]),
                             "candle1_bearish": bool(c[t - 1] < o[t - 1])}))
        else:
            ev.append(Event("crt", "BEAR", t, _close_time(df, t, bar),
                            {"range_high": rh, "range_low": rl, "mid": mid, "purge_extreme": float(h[t]),
                             "candle1_bullish": bool(c[t - 1] > o[t - 1])}))
    return ev


def turtle_soup_wick(df: pd.DataFrame, bar: timedelta, lookback: int = 20) -> list[Event]:
    """Turtle Soup, E04 p4 variant: wick beyond the prior `lookback`-bar high/low with NO close beyond it.

    This is NOT the Raschke/Connors (Street Smarts) rule set; that variant needs source B02.
    `lookback` is not specified by E04 (unresolved)."""
    hh = df["high"].rolling(lookback).max().shift(1)
    ll = df["low"].rolling(lookback).min().shift(1)
    ev = []
    for t in range(lookback, len(df)):
        h, l, c = df["high"].iloc[t], df["low"].iloc[t], df["close"].iloc[t]
        if l < ll.iloc[t] and c >= ll.iloc[t] and not h > hh.iloc[t]:
            ev.append(Event("turtle_soup_wick", "BULL", t, _close_time(df, t, bar),
                            {"old_low": float(ll.iloc[t]), "sweep_low": float(l)}))
        elif h > hh.iloc[t] and c <= hh.iloc[t] and not l < ll.iloc[t]:
            ev.append(Event("turtle_soup_wick", "BEAR", t, _close_time(df, t, bar),
                            {"old_high": float(hh.iloc[t]), "sweep_high": float(h)}))
    return ev


def snr_events(df: pd.DataFrame, bar: timedelta) -> list[Event]:
    """Adapter: SNR level formations as Events (for registry/no-lookahead tests)."""
    return [Event("snr", "BEAR" if s.role == "RESISTANCE" else "BULL", s.formed_index, s.available_at,
                  {"kind": s.kind, "price": s.price}) for s in snr_levels(df, bar)]
