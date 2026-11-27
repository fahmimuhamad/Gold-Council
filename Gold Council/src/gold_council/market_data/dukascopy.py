"""Dukascopy public historical candles (research use; raw files stay local, never committed).

Format (.bi5): LZMA-compressed big-endian records of 24 bytes:
int32 seconds-from-period-start, int32 open, int32 close, int32 low, int32 high, float32 volume.
Prices are integers scaled by `price_scale` (XAUUSD: 1000). Timestamps are UTC.
Monthly hourly file: /datafeed/{SYM}/{YYYY}/{MM0}/{BID|ASK}_candles_hour_1.bi5  (MM0 = month - 1).
Closed-market hours appear as flat zero-volume bars; they are DROPPED, never filled.
These are Dukascopy's own quotes: they differ from any other broker's prices, spreads and server time.
"""
from __future__ import annotations

import hashlib
import lzma
import struct
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

BASE = "https://datafeed.dukascopy.com/datafeed"
REC = struct.Struct(">5if")


def decode(raw: bytes, period_start: datetime, price_scale: float) -> pd.DataFrame:
    data = lzma.decompress(raw) if raw else b""
    if len(data) % REC.size:
        raise ValueError("corrupt bi5 payload (length not a multiple of 24)")
    rows = []
    for i in range(0, len(data), REC.size):
        t, o, c, l, h, v = REC.unpack_from(data, i)
        rows.append((period_start + timedelta(seconds=t), o / price_scale, h / price_scale,
                     l / price_scale, c / price_scale, float(v)))
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])
    closed = (df["volume"] == 0) & (df["open"] == df["high"]) & (df["high"] == df["low"]) & (df["low"] == df["close"])
    return df[~closed].reset_index(drop=True)


def fetch_month(symbol: str, year: int, month: int, side: str, cache: Path, pause: float = 2.0,
                attempts: int = 10) -> bytes | None:
    """Download one monthly file (cached). The server throttles with 503s and resets; retry patiently.
    Returns None if the month could not be fetched (caller records the gap; nothing is invented)."""
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{symbol}_{year}_{month:02d}_{side}_hour.bi5"
    if f.exists():
        return f.read_bytes()
    url = f"{BASE}/{symbol}/{year}/{month - 1:02d}/{side}_candles_hour_1.bi5"
    req = urllib.request.Request(url, headers={"User-Agent": "gold-council-research/0.1"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            if raw:
                lzma.decompress(raw)          # verify it's a real data file before caching
            f.write_bytes(raw)
            time.sleep(pause)
            return raw
        except Exception:
            time.sleep(min(90, 5 * 2 ** attempt))
    return None


def build_hourly(symbol: str, start: tuple[int, int], end: tuple[int, int], cache: Path,
                 price_scale: float = 1000.0) -> tuple[pd.DataFrame, dict]:
    """Bid OHLC + ask close per completed month in [start, end]. Adds spread_close = ask_close - bid_close."""
    frames, files = [], {}
    y, m = start
    while (y, m) <= end:
        ps = datetime(y, m, 1, tzinfo=timezone.utc)
        bid_raw = fetch_month(symbol, y, m, "BID", cache)
        ask_raw = fetch_month(symbol, y, m, "ASK", cache)
        if bid_raw is None or ask_raw is None:
            files[f"{y}-{m:02d}"] = {"status": "MISSING (download failed after retries)"}
            print(f"MISSING {y}-{m:02d}", flush=True)
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
            continue
        print(f"ok {y}-{m:02d}", flush=True)
        files[f"{y}-{m:02d}"] = {"bid_sha256": hashlib.sha256(bid_raw).hexdigest()[:16],
                                 "ask_sha256": hashlib.sha256(ask_raw).hexdigest()[:16]}
        bid = decode(bid_raw, ps, price_scale)
        ask = decode(ask_raw, ps, price_scale)[["time", "close"]].rename(columns={"close": "ask_close"})
        mm = bid.merge(ask, on="time", how="left")
        frames.append(mm)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    df = pd.concat(frames, ignore_index=True).sort_values("time").reset_index(drop=True)
    df["spread_close"] = (df["ask_close"] - df["close"]).round(3)
    return df, files
