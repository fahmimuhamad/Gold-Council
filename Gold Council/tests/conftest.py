from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def root():
    return ROOT


def make_bars(closes, start="2026-01-05 00:00", minutes=15, spread=0.5):
    """Synthetic SYNTHETIC-ONLY bars. Not market data."""
    closes = np.asarray(closes, dtype=float)
    opens = np.r_[closes[0], closes[:-1]]
    t = pd.date_range(start, periods=len(closes), freq=f"{minutes}min", tz="UTC")
    return pd.DataFrame({"time": t, "open": opens, "high": np.maximum(opens, closes) + spread,
                         "low": np.minimum(opens, closes) - spread, "close": closes})


@pytest.fixture
def bars():
    return make_bars
