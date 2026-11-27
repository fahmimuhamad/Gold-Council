import math

import numpy as np
import pandas as pd
import pytest

from gold_council.backtesting.returns_strategies import asian_drift, rsi, rsi2_reversion, weekend_long
from gold_council.evaluation.stats import deflated_sharpe, holm, newey_west_t
from gold_council.market_data.resample import resample


def h1(start, n, step=0.0, price=1000.0):
    t = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    p = price + np.arange(n) * step
    return pd.DataFrame({"time": t, "open": p, "high": p + 1, "low": p - 1, "close": p})


def test_asian_drift_entry_23_exit_07_costs():
    df = h1("2026-01-05 20:00", 14, step=1.0)            # opens 1000,1001,...; 23:00 open = 1003; 07:00 open = 1011
    (t,) = asian_drift(df, spread=0.4, slip=0.1)
    assert t.entry_time.hour == 23 and t.exit_time.hour == 7
    assert t.entry == pytest.approx(1003.3) and t.exit == pytest.approx(1010.7)
    assert t.net_bp == pytest.approx((1010.7 - 1003.3) / 1003.3 * 1e4)


def test_asian_drift_skips_when_exit_bar_missing():
    df = h1("2026-01-05 20:00", 14)
    df = df[df["time"].dt.hour != 7]
    assert asian_drift(df.reset_index(drop=True), 0.4, 0.1) == []


def test_rsi2_known_values():
    c = pd.Series([10.0, 11, 10, 9, 10])
    r = rsi(c, 2)
    # gains: [1,0,0,1], losses: [0,1,1,0]; Wilder n=2 seeded by mean of first 2
    # t=2: g=.5 l=.5 ->50 ; t=3: g=.25 l=.75 -> 25 ; t=4: g=.625 l=.375 -> 62.5
    assert r.iloc[2] == pytest.approx(50) and r.iloc[3] == pytest.approx(25) and r.iloc[4] == pytest.approx(62.5)


def test_rsi2_reversion_entry_next_open_exit_after_close_above_sma5():
    n = 230
    close = list(np.linspace(1000, 1200, n - 6)) + [1150, 1120, 1130, 1210, 1215, 1220]
    t = pd.date_range("2020-01-01 22:00", periods=n, freq="1D", tz="UTC")
    d = pd.DataFrame({"time": t, "close": close})
    d["open"] = d["close"].shift(1).fillna(d["close"])
    d["high"], d["low"] = d[["open", "close"]].max(axis=1) + 1, d[["open", "close"]].min(axis=1) - 1
    trades = rsi2_reversion(d, 0.0, 0.0, 0.0)
    assert trades, "expected a dip-buy after the two down days"
    tr = trades[-1]
    sig = d.index[d["time"] == tr.entry_time][0] - 1
    assert d["close"].iloc[sig] < d["close"].iloc[sig - 1]      # bought after a down close, at next open


def test_weekend_only_friday_to_monday_above_sma():
    src = h1("2025-01-05 22:00", 24 * 7 * 40, step=0.01)      # rising market, 40 weeks
    from gold_council.market_data.resample import to_broker_clock
    src = src[to_broker_clock(src["time"]).dt.weekday < 5].reset_index(drop=True)   # market closed at weekends
    d1 = resample(src, "1D")
    trades = weekend_long(d1, 0.0, 0.0, 0.0)
    assert trades and all(tr.entry_time.tz_convert("America/New_York").strftime("%a %H") == "Fri 17" for tr in trades)
    assert all((tr.exit_time - tr.entry_time) == pd.Timedelta(days=3) for tr in trades)


def test_newey_west_and_holm():
    rng = np.random.default_rng(0)
    t, p = newey_west_t(rng.normal(0.3, 1, 500))
    assert t > 3 and p < 0.001
    _, p0 = newey_west_t(rng.normal(0, 1, 500))
    assert p0 > 0.01
    h = holm({"a": 0.01, "b": 0.02, "c": 0.04})
    assert h["a"]["reject_null"] and h["b"]["reject_null"] and h["c"]["reject_null"]
    h = holm({"a": 0.01, "b": 0.03, "c": 0.04})
    assert h["a"]["reject_null"] and not h["b"]["reject_null"] and not h["c"]["reject_null"]


def test_deflated_sharpe_penalises_many_trials():
    r = np.random.default_rng(1).normal(0.05, 1, 1000)
    few = deflated_sharpe(r, 2, 0.002)["dsr"]
    many = deflated_sharpe(r, 100, 0.002)["dsr"]
    assert 0 <= many < few <= 1
