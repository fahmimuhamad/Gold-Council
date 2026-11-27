"""Import and validate OHLC CSV exports (e.g. from MT5). Never fills missing data."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

import pandas as pd

REQUIRED = ["time", "open", "high", "low", "close"]


@dataclass
class ValidationReport:
    rows: int
    duplicates: int = 0
    non_monotonic: int = 0
    bad_ohlc: int = 0
    gaps: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and self.duplicates == 0 and self.non_monotonic == 0 and self.bad_ohlc == 0


def load_csv(path: str | Path, source_tz: str | None) -> pd.DataFrame:
    """Load CSV. `source_tz` is the broker server timezone (IANA). None => refuse (fail closed)."""
    if source_tz is None:
        raise ValueError("broker timezone must be stated explicitly; broker time is not assumed to be UTC")
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().lstrip("<").rstrip(">") for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    t = pd.to_datetime(df["time"])
    df["time"] = t.dt.tz_localize(source_tz, ambiguous="raise", nonexistent="raise").dt.tz_convert("UTC")
    return df


def validate(df: pd.DataFrame, bar: timedelta) -> ValidationReport:
    rep = ValidationReport(rows=len(df))
    rep.duplicates = int(df["time"].duplicated().sum())
    rep.non_monotonic = int((df["time"].diff().dt.total_seconds() < 0).sum())
    bad = (df["high"] < df[["open", "close", "low"]].max(axis=1)) | (df["low"] > df[["open", "close", "high"]].min(axis=1))
    rep.bad_ohlc = int(bad.sum())
    diffs = df["time"].diff().dropna()
    rep.gaps = int((diffs > bar).sum())   # weekends/holidays included; reported, not filled
    if df[REQUIRED[1:]].isna().any().any():
        rep.errors.append("NaN prices present")
    return rep
