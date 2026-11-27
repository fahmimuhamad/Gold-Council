from datetime import timedelta

import numpy as np
import pandas as pd

from gold_council.strategies.ict import cisd, displacement, fvg_lifecycle, liquidity_sweep, volume_imbalance

BAR = timedelta(minutes=15)


def frame(rows):
    t = pd.date_range("2026-01-05", periods=len(rows), freq="15min", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"]).assign(time=t)


BASE = [(10, 11, 9, 10.5), (10.5, 14, 10.4, 13.8), (13.8, 15, 12, 14.5)]   # bullish FVG [11, 12], CE 11.5


def test_fvg_ce_then_fill_then_inversion():
    df = frame(BASE + [(14.5, 14.6, 11.4, 12.5), (12.5, 12.6, 10.8, 11.2), (11.2, 11.3, 10, 10.2)])
    assert [s.status for s in fvg_lifecycle(df, BAR, upto=3)] == ["CE_REACHED"]
    assert [s.status for s in fvg_lifecycle(df, BAR, upto=4)] == ["FILLED"]       # wick below 11, close above
    s = [x for x in fvg_lifecycle(df, BAR) if x.event.bar_index == 2][0]   # bar 5 also forms a bearish FVG
    assert s.status == "INVERTED" and s.history[-1] == (5, "inverted")


def test_fvg_wick_variant_is_stricter():
    df = frame(BASE + [(12.5, 12.6, 10.8, 11.2)])
    assert fvg_lifecycle(df, BAR, invalidate_on="wick_far_edge")[0].status == "INVERTED"
    assert fvg_lifecycle(df, BAR)[0].status == "FILLED"


def test_displacement_threshold_and_own_bar_excluded():
    rows = [(100, 100.6, 99.6, 100.2), (100.2, 100.7, 99.8, 100.0)] * 10
    rows.append((100.0, 103.2, 99.9, 103.0))               # body 3.0, quiet ATR ~1 -> displacement
    ev = displacement(frame(rows), BAR)
    assert [e.bar_index for e in ev] == [20] and ev[0].direction == "BULL"
    rows[-1] = (100.0, 103.2, 99.0, 100.8)                  # mostly wick -> not displacement
    assert displacement(frame(rows), BAR) == []


def test_sweep_needs_close_back_inside():
    rows = [(100.5, 101.2, 99.2, 100), (100, 101, 99, 100.5), (100.5, 101, 98, 99), (99, 100, 98.5, 99.5),
            (99.5, 100.5, 99, 100), (100, 100.8, 99.6, 100.2)]   # swing low 98 at i=2, confirmed at 4
    df = frame(rows + [(100.2, 100.4, 97.5, 98.6)])
    assert [(e.direction, e.levels["swept"]) for e in liquidity_sweep(df, BAR)] == [("BULL", 98.0)]
    df2 = frame(rows + [(100.2, 100.4, 97.5, 97.8)])         # closes below -> breakdown, not sweep
    assert liquidity_sweep(df2, BAR) == []


def test_cisd_reference_is_first_open_of_opposite_run():
    rows = [(105, 105.5, 103.5, 104), (104, 104.2, 102, 102.5), (102.5, 106, 102, 105.5)]
    (e,) = cisd(frame(rows), BAR)
    assert e.bar_index == 2 and e.direction == "BULL" and e.levels["reference_open"] == 105


def test_volume_imbalance_is_not_fvg():
    rows = [(100, 101.5, 99.5, 101), (101.2, 102.5, 100.8, 102)]   # body gap 101 -> 101.2, wicks overlap
    (e,) = volume_imbalance(frame(rows), BAR)
    assert e.direction == "BULL" and e.levels == {"lower": 101, "upper": 101.2}


def test_ict_detectors_no_lookahead_realistic_wicks():
    from gold_council.strategies.detectors import DETECTORS
    rng = np.random.default_rng(3); n = 400
    c = 2000 + np.cumsum(rng.normal(0, 2, n)); o = np.r_[c[0], c[:-1]] + rng.normal(0, .4, n)
    df = pd.DataFrame({"time": pd.date_range("2026-01-05", periods=n, freq="15min", tz="UTC"), "open": o,
                       "high": np.maximum(o, c) + rng.uniform(.1, 2, n),
                       "low": np.minimum(o, c) - rng.uniform(.1, 2, n), "close": c})
    for k in ["displacement", "sweep", "cisd", "volume_imbalance", "bos", "crt", "snr"]:
        sel = lambda ev: [(e.bar_index, e.direction) for e in ev if e.bar_index <= 300]
        full, trunc = DETECTORS[k](df, BAR), DETECTORS[k](df.iloc[:301].copy(), BAR)
        assert sel(full) and sel(full) == sel(trunc), k
    for cut in (150, 300):   # FVG lifecycle at a point in time must not depend on later bars
        a = [(s.event.bar_index, s.status) for s in fvg_lifecycle(df, BAR, upto=cut)]
        b = [(s.event.bar_index, s.status) for s in fvg_lifecycle(df.iloc[:cut + 1].copy(), BAR)]
        assert a == b
