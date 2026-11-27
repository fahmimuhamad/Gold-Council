"""Resample UTC bars into broker-style NY-close candles (broker clock = America/New_York + 7h).

4H candles open at broker 00/04/08/12/16/20 (NY 17/21/01/05/09/13); D1 = 17:00 NY -> 17:00 NY;
W1 starts Monday 00:00 broker (= Sunday 17:00 NY). Output `time` is the candle OPEN in UTC.
`n_src` = number of source bars aggregated (short sessions are kept, never padded).
"""
from __future__ import annotations

import pandas as pd

NY = "America/New_York"
BROKER_SHIFT = pd.Timedelta(hours=7)


def to_broker_clock(t_utc: pd.Series) -> pd.Series:
    return t_utc.dt.tz_convert(NY).dt.tz_localize(None) + BROKER_SHIFT


def from_broker_clock(t_broker: pd.Series) -> pd.Series:
    return (t_broker - BROKER_SHIFT).dt.tz_localize(NY, ambiguous="raise", nonexistent="raise").dt.tz_convert("UTC")


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """rule: '4h', '1D' or 'W' (weeks starting Monday, broker clock)."""
    b = to_broker_clock(df["time"])
    if rule == "W":
        key = b.dt.to_period("W-SUN").dt.start_time
    else:
        key = b.dt.floor(rule)
    g = df.assign(_k=key.values).groupby("_k", sort=True)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                        "close": g["close"].last(), "n_src": g["open"].size()})
    out = out.reset_index().rename(columns={"_k": "broker_open"})
    out["time"] = from_broker_clock(out["broker_open"])
    out["ny_open_hour"] = out["time"].dt.tz_convert(NY).dt.hour
    return out[["time", "broker_open", "ny_open_hour", "open", "high", "low", "close", "n_src"]]
