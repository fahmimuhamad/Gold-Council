import math
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from gold_council.backtesting.engine import Costs, TradePlan, run
from gold_council.backtesting.plans import bias_for_daily, crt_atr_plans, weekly_bias
from gold_council.market_data.resample import resample


def hourly(start_utc, n, price=100.0):
    t = pd.date_range(start_utc, periods=n, freq="1h", tz="UTC")
    p = price + np.arange(n) * 0.1
    return pd.DataFrame({"time": t, "open": p, "high": p + 0.5, "low": p - 0.5, "close": p + 0.05})


def test_daily_candle_is_ny_close_to_ny_close_both_seasons():
    # Winter: 17:00 NY = 22:00 UTC. Summer (EDT): 17:00 NY = 21:00 UTC.
    for start, open_utc in [("2026-01-12 00:00", "22:00"), ("2026-07-13 00:00", "21:00")]:
        d = resample(hourly(start, 72), "1D")
        full = d[d["n_src"] == 24]
        assert len(full) >= 1
        assert all(x.strftime("%H:%M") == open_utc for x in full["time"])


def test_4h_candles_open_at_ny_1_5_9_13_17_21():
    d = resample(hourly("2026-01-12 00:00", 48), "4h")
    assert set(d["ny_open_hour"]) <= {1, 5, 9, 13, 17, 21}
    full = d[d["n_src"] == 4]
    row = full.iloc[0]
    src = hourly("2026-01-12 00:00", 48)
    m = (src["time"] >= row["time"]) & (src["time"] < row["time"] + pd.Timedelta(hours=4))
    assert row["open"] == src[m]["open"].iloc[0] and row["close"] == src[m]["close"].iloc[-1]
    assert row["high"] == src[m]["high"].max() and row["low"] == src[m]["low"].min()


def test_weekly_starts_sunday_17_ny():
    w = resample(hourly("2026-01-11 20:00", 24 * 9), "W")
    assert w["time"].iloc[1].tz_convert("America/New_York").strftime("%a %H:%M") == "Sun 17:00"


def test_channel_exit_next_open_and_financing():
    t = pd.date_range("2026-01-05", periods=8, freq="1D", tz="UTC")
    rows = [(100, 101, 99, 100), (100, 102, 99.5, 101), (101, 103, 100.5, 102), (102, 104, 101.5, 103),
            (103, 103.5, 100, 100.2),   # close 100.2 < min low of prior 2 bars (100.5) -> exit next open
            (100.1, 101, 99, 100.5), (100.5, 101, 100, 100.7), (100.7, 101, 100, 100.8)]
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"]).assign(time=t)
    p = TradePlan("p", 0, "LONG", stop=90, target=math.inf, exit_channel=2)
    (r,) = run(df, [p])
    assert r.reason == "CHANNEL" and r.exit_index == 5 and r.exit == 100.1
    (rf,) = run(df, [p], Costs(financing_per_year=0.0365))       # 4 days held x 0.0001 x 100 = 0.04
    assert rf.r == pytest.approx(r.r - 0.04 / 10)


def test_weekly_bias_rules():
    w = pd.DataFrame({"high": [10, 12, 11.5, 13, 13.5], "low": [8, 9, 7, 9, 8.5],
                      "close": [9, 11.5, 9, 12, 10]})
    # w1 close 11.5 > prev high 10 -> BULL; w2 wick below 9 (7), close 9 >= 9 -> BULL;
    # w3 close 12 > 11.5 -> BULL; w4 wick above 13, close 10 inside, low 8.5 > 9? no: 8.5 < 9 -> both -> NEUTRAL
    assert list(weekly_bias(w)) == ["NEUTRAL", "BULL", "BULL", "BULL", "NEUTRAL"]


def test_bias_never_uses_unfinished_week():
    d = resample(hourly("2026-01-11 22:00", 24 * 20), "1D")
    w = resample(hourly("2026-01-11 22:00", 24 * 20), "W")
    b = bias_for_daily(d, w)
    # first week's days cannot have any completed week yet
    first_week_end = w["time"].iloc[1]
    early = d["time"] + pd.Timedelta(days=1) < first_week_end
    assert set(b[early]) == {"NEUTRAL"}


def test_crt_time_filter_and_buffer():
    rows = [(105, 106, 100, 101), (101, 103, 99, 102)] * 30
    t = pd.date_range("2026-01-05 02:00", periods=60, freq="4h", tz="UTC")   # NY 21,1,5,9,13,17
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"]).assign(time=t)
    df["ny_open_hour"] = t.tz_convert("America/New_York").hour
    plans = crt_atr_plans(df, timedelta(hours=4), ny_hours={9})
    assert plans and all(int(df["ny_open_hour"].iloc[p.bar_index]) == 9 for p in plans)
    p = plans[0]
    assert p.side == "LONG" and p.target == 106 and p.stop < 99
