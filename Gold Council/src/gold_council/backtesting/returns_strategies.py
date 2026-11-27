"""Round-3 strategies without stops: trades measured as net return in basis points.

Cost model (long only): entry = bid + spread/2 + slippage; exit = bid - spread/2 - slippage.
Financing: annual rate x calendar days held / 365, only if the position crosses the daily rollover.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from gold_council.features.indicators import wilder


@dataclass(frozen=True)
class RetTrade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    exit: float
    net_bp: float


def _net_bp(entry_bid, exit_bid, spread, slip, fin_rate=0.0, days=0.0):
    e = entry_bid + spread / 2 + slip
    x = exit_bid - spread / 2 - slip
    return e, x, (x - e) / e * 1e4 - fin_rate * days / 365 * 1e4


def asian_drift(h1: pd.DataFrame, spread: float, slip: float, entry_hour: int = 23, exit_hour: int = 7) -> list[RetTrade]:
    """Buy the open of the entry_hour UTC bar, sell the open of the exit_hour UTC bar (next UTC day)."""
    idx = {t: i for i, t in enumerate(h1["time"])}
    o = h1["open"].to_numpy()
    out = []
    for i, t in enumerate(h1["time"]):
        if t.hour != entry_hour:
            continue
        t_exit = t + pd.Timedelta(hours=(exit_hour - entry_hour) % 24)
        j = idx.get(t_exit)
        if j is None:
            continue
        e, x, bp = _net_bp(o[i], o[j], spread, slip)
        out.append(RetTrade(t, t_exit, e, x, bp))
    return out


def rsi(close: pd.Series, n: int = 2) -> pd.Series:
    d = close.diff()
    gain = wilder(d.clip(lower=0).iloc[1:], n).reindex(close.index)
    loss = wilder((-d).clip(lower=0).iloc[1:], n).reindex(close.index)
    rs = gain / loss
    out = 100 - 100 / (1 + rs)
    return out.where(loss > 0, 100.0).where(gain.notna())


def rsi2_reversion(d1: pd.DataFrame, spread: float, slip: float, fin_rate: float,
                   sma_long: int = 200, sma_exit: int = 5, rsi_max: float = 5.0) -> list[RetTrade]:
    c, o = d1["close"], d1["open"].to_numpy()
    s200, s5, r2 = c.rolling(sma_long).mean(), c.rolling(sma_exit).mean(), rsi(c, 2)
    t = d1["time"]
    out, i, n = [], 0, len(d1)
    while i < n - 1:
        if pd.notna(s200.iloc[i]) and c.iloc[i] > s200.iloc[i] and pd.notna(r2.iloc[i]) and r2.iloc[i] < rsi_max:
            ent = i + 1
            ex = None
            for j in range(ent, n):
                if c.iloc[j] > s5.iloc[j]:
                    ex = j + 1
                    break
            if ex is None or ex >= n:          # still open at end of data: mark at last close
                exit_px, exit_t = c.iloc[-1], t.iloc[-1] + pd.Timedelta(days=1)
                nxt = n
            else:
                exit_px, exit_t = o[ex], t.iloc[ex]
                nxt = ex
            days = (exit_t - t.iloc[ent]).total_seconds() / 86400
            e, x, bp = _net_bp(o[ent], exit_px, spread, slip, fin_rate, days)
            out.append(RetTrade(t.iloc[ent], exit_t, e, x, bp))
            i = nxt
            continue
        i += 1
    return out


def weekend_long(d1: pd.DataFrame, spread: float, slip: float, fin_rate: float, sma_long: int = 200) -> list[RetTrade]:
    """Friday NY-close daily candle close -> following Monday candle close, only if Friday close > SMA200."""
    c = d1["close"]
    s = c.rolling(sma_long).mean()
    wd = d1["broker_open"].dt.weekday
    out = []
    for i in range(len(d1) - 1):
        if wd.iloc[i] != 4 or wd.iloc[i + 1] != 0:
            continue
        if not (pd.notna(s.iloc[i]) and c.iloc[i] > s.iloc[i]):
            continue
        t_in = d1["time"].iloc[i] + pd.Timedelta(days=1)       # Friday close time
        t_out = d1["time"].iloc[i + 1] + pd.Timedelta(days=1)  # Monday close time
        days = (t_out - t_in).total_seconds() / 86400
        e, x, bp = _net_bp(c.iloc[i], c.iloc[i + 1], spread, slip, fin_rate, days)
        out.append(RetTrade(t_in, t_out, e, x, bp))
    return out
