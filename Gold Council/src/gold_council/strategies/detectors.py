"""Deterministic geometric detectors. These are *observations*, not trading signals.

Input: DataFrame with columns time (bar open, tz-aware UTC), open, high, low, close,
and a bar duration. Each event's `available_at` is the close time of the bar that
completes the pattern; nothing may act on it earlier.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time as dtime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from gold_council.features.indicators import atr, rolling_percentile, zscore


@dataclass(frozen=True)
class Event:
    detector: str
    direction: str          # BULL | BEAR | NEUTRAL
    bar_index: int
    available_at: pd.Timestamp
    levels: dict


def _close_time(df: pd.DataFrame, i: int, bar: timedelta) -> pd.Timestamp:
    return df["time"].iloc[i] + bar


def fvg(df: pd.DataFrame, bar: timedelta) -> list[Event]:
    """Three-candle gap. Bullish: low[t] > high[t-2], bounds [high[t-2], low[t]]."""
    ev = []
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    for t in range(2, len(df)):
        if l[t] > h[t - 2]:
            lo, hi = h[t - 2], l[t]
            ev.append(Event("fvg", "BULL", t, _close_time(df, t, bar),
                            {"lower": lo, "upper": hi, "mid": (lo + hi) / 2}))
        elif h[t] < l[t - 2]:
            lo, hi = h[t], l[t - 2]
            ev.append(Event("fvg", "BEAR", t, _close_time(df, t, bar),
                            {"lower": lo, "upper": hi, "mid": (lo + hi) / 2}))
    return ev


def donchian_breakout(df: pd.DataFrame, bar: timedelta, n: int = 20) -> list[Event]:
    """Close beyond the highest high / lowest low of the previous n completed bars (excl. t)."""
    upper = df["high"].rolling(n).max().shift(1)
    lower = df["low"].rolling(n).min().shift(1)
    ev = []
    for t in range(n, len(df)):
        c = df["close"].iloc[t]
        if c > upper.iloc[t]:
            ev.append(Event("donchian", "BULL", t, _close_time(df, t, bar), {"channel": float(upper.iloc[t])}))
        elif c < lower.iloc[t]:
            ev.append(Event("donchian", "BEAR", t, _close_time(df, t, bar), {"channel": float(lower.iloc[t])}))
    return ev


def nr7(df: pd.DataFrame, bar: timedelta, n: int = 7) -> list[Event]:
    rng = df["high"] - df["low"]
    ev = []
    for t in range(n - 1, len(df)):
        w = rng.iloc[t - n + 1: t + 1].to_numpy()
        if w[-1] < w[:-1].min():  # strictly narrowest; ties are not NR7
            ev.append(Event("nr7", "NEUTRAL", t, _close_time(df, t, bar),
                            {"high": float(df["high"].iloc[t]), "low": float(df["low"].iloc[t])}))
    return ev


def atr_compression(df: pd.DataFrame, bar: timedelta, n: int = 14, lookback: int = 100,
                    pct_max: float = 0.10) -> list[Event]:
    pct = rolling_percentile(atr(df, n), lookback)
    return [Event("atr_compression", "NEUTRAL", t, _close_time(df, t, bar), {"atr_pct": float(pct.iloc[t])})
            for t in range(len(df)) if not np.isnan(pct.iloc[t]) and pct.iloc[t] <= pct_max]


def zscore_extreme(df: pd.DataFrame, bar: timedelta, n: int = 20, threshold: float = 2.0) -> list[Event]:
    z = zscore(df["close"], n)
    ev = []
    for t in range(len(df)):
        v = z.iloc[t]
        if np.isnan(v):
            continue
        if v >= threshold:
            ev.append(Event("zscore", "BEAR", t, _close_time(df, t, bar), {"z": float(v)}))
        elif v <= -threshold:
            ev.append(Event("zscore", "BULL", t, _close_time(df, t, bar), {"z": float(v)}))
    return ev


def opening_range(df: pd.DataFrame, bar: timedelta, tz: str = "Europe/London",
                  open_local: dtime = dtime(8, 0), minutes: int = 30) -> list[Event]:
    """Opening range per local session day (DST-aware via IANA tz), then first close outside it.

    The range is available only after its last bar closes. Breakout events need a full,
    gap-free range window; partial windows are skipped.
    """
    zone = ZoneInfo(tz)
    local = df["time"].dt.tz_convert(zone)
    need = int(timedelta(minutes=minutes) / bar)
    ev = []
    for day, idx in df.groupby(local.dt.date).groups.items():
        rows = sorted(df.index.get_indexer(idx))
        start = pd.Timestamp.combine(day, open_local).tz_localize(zone)
        end = start + timedelta(minutes=minutes)
        win = [i for i in rows if start <= local.iloc[i] < end]
        if len(win) != need:
            continue
        hi = float(df["high"].iloc[win].max())
        lo = float(df["low"].iloc[win].min())
        for i in rows:
            if local.iloc[i] < end:
                continue
            c = df["close"].iloc[i]
            if c > hi or c < lo:
                ev.append(Event("orb", "BULL" if c > hi else "BEAR", i, _close_time(df, i, bar),
                                {"range_high": hi, "range_low": lo, "session_tz": tz}))
                break  # first breakout only
    return ev


DETECTORS = {
    "fvg": fvg,
    "donchian": donchian_breakout,
    "nr7": nr7,
    "atr_compression": atr_compression,
    "zscore": zscore_extreme,
    "orb": opening_range,
}
