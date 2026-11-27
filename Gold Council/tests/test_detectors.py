from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from gold_council.strategies.detectors import DETECTORS, donchian_breakout, fvg, nr7, opening_range, zscore_extreme
from tests.conftest import make_bars

BAR = timedelta(minutes=15)


def frame(rows, start="2026-01-05 00:00", minutes=15):
    t = pd.date_range(start, periods=len(rows), freq=f"{minutes}min", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"]).assign(time=t)


def test_bullish_fvg_bounds_and_availability():
    df = frame([(10, 11, 9, 10.5), (10.5, 14, 10.4, 13.8), (13.8, 15, 12, 14.5)])
    ev = fvg(df, BAR)
    assert len(ev) == 1 and ev[0].direction == "BULL"
    assert ev[0].levels == {"lower": 11, "upper": 12, "mid": 11.5}
    assert ev[0].available_at == df["time"].iloc[2] + BAR   # only at close of t


def test_touching_bars_are_not_fvg():
    df = frame([(10, 11, 9, 10.5), (10.5, 14, 10.4, 13.8), (13.8, 15, 11, 14.5)])  # low == high[t-2]
    assert fvg(df, BAR) == []


def test_bearish_fvg():
    df = frame([(10, 11, 9, 9.5), (9.5, 9.6, 6, 6.2), (6.2, 8, 5, 5.5)])
    ev = fvg(df, BAR)
    assert ev[0].direction == "BEAR" and ev[0].levels["lower"] == 8 and ev[0].levels["upper"] == 9


def test_donchian_excludes_current_bar():
    closes = [100] * 20 + [100.4]
    df = make_bars(closes, spread=0.5)   # prior highs 100.5 -> 100.4 close is NOT a breakout
    assert donchian_breakout(df, BAR, 20) == []
    df2 = make_bars([100] * 20 + [101.0], spread=0.5)
    assert [e.direction for e in donchian_breakout(df2, BAR, 20)] == ["BULL"]


def test_nr7_strict():
    rows = [(10, 10 + r, 10 - r, 10) for r in [3, 2.5, 2, 1.8, 1.6, 1.5, 0.5]]
    assert len(nr7(frame(rows), BAR)) == 1
    rows[-1] = (10, 11.5, 8.5, 10)   # tie with bar 5 range 3.0 -> not NR7
    assert nr7(frame(rows), BAR) == []


def test_zscore_direction():
    df = make_bars(list(np.r_[np.full(19, 100.0) + np.tile([0.1, -0.1], 10)[:19], 105]), spread=0.1)
    ev = zscore_extreme(df, BAR, 20, 2.0)
    assert ev and ev[-1].direction == "BEAR"


def test_orb_dst_aware():
    # 2026-03-30 is after UK DST start: London 08:00 = 07:00 UTC. 2026-03-27 is before: 08:00 UTC.
    def day(d, open_utc_hour):
        t = pd.date_range(f"{d} 06:00", periods=16, freq="15min", tz="UTC")
        c = np.full(16, 100.0)
        k = (open_utc_hour - 6) * 4
        c[k + 3] = 103   # first bar after 30-minute range closes above range
        o = np.r_[c[0], c[:-1]]
        return pd.DataFrame({"time": t, "open": o, "high": np.maximum(o, c) + 0.2,
                             "low": np.minimum(o, c) - 0.2, "close": c})
    for d, h in [("2026-03-27", 8), ("2026-03-30", 7)]:
        ev = opening_range(day(d, h), BAR, "Europe/London", minutes=30)
        assert len(ev) == 1 and ev[0].direction == "BULL"
        assert ev[0].available_at == pd.Timestamp(f"{d} {h:02d}:00", tz="UTC") + timedelta(minutes=60)


@pytest.mark.parametrize("name", list(DETECTORS))
def test_no_lookahead(name):
    """Events up to bar k must be identical whether or not later bars exist."""
    rng = np.random.default_rng(7)
    closes = 2000 + np.cumsum(rng.normal(0, 2, 400))
    df = make_bars(closes, spread=1.0)
    full = DETECTORS[name](df, BAR)
    k = 300
    trunc = DETECTORS[name](df.iloc[: k + 1].copy(), BAR)
    sel = lambda evs: [(e.bar_index, e.direction, tuple(sorted(e.levels.items()))) for e in evs if e.bar_index <= k]
    assert sel(full) == sel(trunc)
    assert all(e.available_at > df["time"].iloc[e.bar_index] for e in full)
