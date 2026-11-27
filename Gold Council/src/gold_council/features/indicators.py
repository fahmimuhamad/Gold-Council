"""Point-in-time indicators. Value at row t uses only rows <= t (completed bars)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(),
                    (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    tr.iloc[0] = df["high"].iloc[0] - df["low"].iloc[0]
    return tr


def wilder(series: pd.Series, n: int) -> pd.Series:
    """Wilder smoothing seeded by the first n-value simple mean (NaN before)."""
    out = pd.Series(np.nan, index=series.index, dtype=float)
    vals = series.to_numpy(dtype=float)
    if len(vals) < n:
        return out
    acc = np.nanmean(vals[:n])
    res = np.full(len(vals), np.nan)
    res[n - 1] = acc
    for i in range(n, len(vals)):
        acc = (acc * (n - 1) + vals[i]) / n
        res[i] = acc
    out[:] = res
    return out


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return wilder(true_range(df), n)


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    plus_dm.iloc[0] = minus_dm.iloc[0] = np.nan
    tr = true_range(df)
    tr.iloc[0] = np.nan
    atr_ = wilder(tr.iloc[1:], n).reindex(df.index)
    pdi = 100 * wilder(plus_dm.iloc[1:], n).reindex(df.index) / atr_
    mdi = 100 * wilder(minus_dm.iloc[1:], n).reindex(df.index) / atr_
    dx = (100 * (pdi - mdi).abs() / (pdi + mdi)).replace([np.inf, -np.inf], np.nan)
    first = dx.first_valid_index()
    if first is None:
        return pd.Series(np.nan, index=df.index)
    pos = df.index.get_loc(first)
    return wilder(dx.iloc[pos:], n).reindex(df.index)


def efficiency_ratio(close: pd.Series, n: int = 20) -> pd.Series:
    change = (close - close.shift(n)).abs()
    vol = close.diff().abs().rolling(n).sum()
    return (change / vol).where(vol > 0)


def ema(close: pd.Series, n: int) -> pd.Series:
    return close.ewm(span=n, adjust=False, min_periods=n).mean()


def rolling_percentile(series: pd.Series, lookback: int) -> pd.Series:
    """Fraction of the previous `lookback` values (inclusive of t) that are <= value at t."""
    def pct(w: np.ndarray) -> float:
        return float(np.mean(w <= w[-1]))
    return series.rolling(lookback, min_periods=lookback).apply(pct, raw=True)


def zscore(close: pd.Series, n: int = 20) -> pd.Series:
    m = close.rolling(n).mean()
    s = close.rolling(n).std(ddof=0)
    return ((close - m) / s).where(s > 0)
