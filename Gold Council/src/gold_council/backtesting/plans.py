"""Baseline plan builders: deterministic, DRAFT research hypotheses with preregistered default params.
They turn detector events into TradePlans. They are NOT approved strategies."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from gold_council.backtesting.engine import TradePlan
from gold_council.features.indicators import atr
from gold_council.strategies.detectors import donchian_breakout
from gold_council.strategies.msnr import crt


def donchian_plans(df: pd.DataFrame, bar: timedelta, n: int = 20, atr_n: int = 14,
                   stop_atr: float = 2.0, rr: float = 2.0) -> list[TradePlan]:
    a = atr(df, atr_n)
    out = []
    for e in donchian_breakout(df, bar, n):
        v = a.iloc[e.bar_index]
        if pd.isna(v) or v <= 0:
            continue
        c = df["close"].iloc[e.bar_index]
        side = "LONG" if e.direction == "BULL" else "SHORT"
        stop = c - stop_atr * v if side == "LONG" else c + stop_atr * v
        target = c + rr * stop_atr * v if side == "LONG" else c - rr * stop_atr * v
        out.append(TradePlan(f"donchian_{e.bar_index}", e.bar_index, side, stop, target, 1, "S16"))
    return out


def crt_plans(df: pd.DataFrame, bar: timedelta, target: str = "mid") -> list[TradePlan]:
    """S23: stop beyond the purge extreme; target = 50% of candle-1 range ('mid') or opposite end ('far')."""
    out = []
    for e in crt(df, bar):
        L = e.levels
        side = "LONG" if e.direction == "BULL" else "SHORT"
        if target == "mid":
            tgt = L["mid"]
        else:
            tgt = L["range_high"] if side == "LONG" else L["range_low"]
        out.append(TradePlan(f"crt_{e.bar_index}", e.bar_index, side, L["purge_extreme"], tgt, 1, "S23"))
    return out


BUILDERS = {"donchian": donchian_plans, "crt_mid": lambda d, b: crt_plans(d, b, "mid"),
            "crt_far": lambda d, b: crt_plans(d, b, "far")}


# ------------------------------------------------------------------ round 2 builders

def donchian_channel_plans(df: pd.DataFrame, bar: timedelta, n: int = 20, exit_n: int = 10,
                           atr_n: int = 14, stop_atr: float = 2.0, regime=None) -> list[TradePlan]:
    """Turtle-style: 20-bar breakout, 2xATR protective stop, exit on opposite `exit_n` channel, no target.
    `regime`: optional RegimeConfig -> only signals with ADX >= adx_trend_min and ER >= er_trend_min."""
    import math
    from gold_council.features.indicators import adx, efficiency_ratio
    a = atr(df, atr_n)
    ok = None
    if regime is not None:
        ok = (adx(df, regime.adx_period) >= regime.adx_trend_min) & \
             (efficiency_ratio(df["close"], regime.er_period) >= regime.er_trend_min)
    out = []
    for e in donchian_breakout(df, bar, n):
        v = a.iloc[e.bar_index]
        if pd.isna(v) or v <= 0 or (ok is not None and not bool(ok.iloc[e.bar_index])):
            continue
        c = df["close"].iloc[e.bar_index]
        side = "LONG" if e.direction == "BULL" else "SHORT"
        stop = c - stop_atr * v if side == "LONG" else c + stop_atr * v
        target = math.inf if side == "LONG" else -math.inf
        out.append(TradePlan(f"dch_{e.bar_index}", e.bar_index, side, stop, target, 1, "S16", exit_channel=exit_n))
    return out


def weekly_bias(weekly: pd.DataFrame) -> pd.Series:
    """E04 p18 HTF order flow, for each COMPLETED week i vs week i-1:
    close > prev high -> BULL; close < prev low -> BEAR; wick above but close <= prev high -> BEAR;
    wick below but close >= prev low -> BULL; both or neither -> NEUTRAL."""
    ph, pl = weekly["high"].shift(1), weekly["low"].shift(1)
    out = []
    for i in range(len(weekly)):
        if i == 0:
            out.append("NEUTRAL"); continue
        h, l, c = weekly["high"].iloc[i], weekly["low"].iloc[i], weekly["close"].iloc[i]
        if c > ph.iloc[i]:
            out.append("BULL")
        elif c < pl.iloc[i]:
            out.append("BEAR")
        else:
            above, below = h > ph.iloc[i], l < pl.iloc[i]
            out.append("BEAR" if above and not below else "BULL" if below and not above else "NEUTRAL")
    return pd.Series(out, index=weekly.index)


def crt_atr_plans(df: pd.DataFrame, bar: timedelta, atr_n: int = 14, buffer_atr: float = 0.5,
                  ny_hours: set[int] | None = None, bias_at_bar: pd.Series | None = None) -> list[TradePlan]:
    """CRT (E04) with stop = purge extreme +/- buffer_atr x ATR, target = opposite end of candle 1.
    `ny_hours`: candle 2 must OPEN at one of these New York hours (needs `ny_open_hour` column).
    `bias_at_bar`: per-bar 'BULL'/'BEAR'/'NEUTRAL' known at that bar's close; trade only with the bias."""
    a = atr(df, atr_n)
    out = []
    for e in crt(df, bar):
        t = e.bar_index
        v = a.iloc[t]
        if pd.isna(v) or v <= 0:
            continue
        if ny_hours is not None and int(df["ny_open_hour"].iloc[t]) not in ny_hours:
            continue
        side = "LONG" if e.direction == "BULL" else "SHORT"
        if bias_at_bar is not None and bias_at_bar.iloc[t] != ("BULL" if side == "LONG" else "BEAR"):
            continue
        L = e.levels
        stop = L["purge_extreme"] - buffer_atr * v if side == "LONG" else L["purge_extreme"] + buffer_atr * v
        tgt = L["range_high"] if side == "LONG" else L["range_low"]
        out.append(TradePlan(f"crt2_{t}", t, side, stop, tgt, 1, "S23"))
    return out


def bias_for_daily(daily: pd.DataFrame, weekly: pd.DataFrame) -> pd.Series:
    """Bias usable at each daily bar = bias of the most recent week that ENDED at or before that day's close.
    Week end = next week's open; a week still in progress is never used (no lookahead)."""
    wb = weekly_bias(weekly)
    week_end = weekly["time"].shift(-1)          # last week has no known end -> never usable
    day_close = daily["time"] + pd.Timedelta(days=1)
    out = []
    j = -1
    for dc in day_close:
        while j + 1 < len(weekly) and pd.notna(week_end.iloc[j + 1]) and week_end.iloc[j + 1] <= dc:
            j += 1
        out.append(wb.iloc[j] if j >= 0 else "NEUTRAL")
    return pd.Series(out, index=daily.index)
