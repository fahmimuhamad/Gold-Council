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
