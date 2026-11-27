from datetime import timedelta

import pandas as pd
import pytest

from gold_council.strategies.msnr import bos, crt, snr_levels, swing_points, turtle_soup_wick, update_freshness

BAR = timedelta(hours=1)


def frame(rows):
    t = pd.date_range("2026-01-05 00:00", periods=len(rows), freq="1h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"]).assign(time=t)


# --- SNR (E03 p8-9) ---------------------------------------------------------

def test_classic_a_is_bull_close_to_bear_open_ignoring_wicks():
    df = frame([(100, 106, 99, 105), (105.2, 109, 101, 102)])  # bull then bear, big upper wick
    (lvl,) = snr_levels(df, BAR)
    assert lvl.kind == "CLASSIC_A" and lvl.role == "RESISTANCE"
    assert lvl.price == 105 and lvl.alt_price == 105.2          # body edges, not the 109 wick
    assert lvl.available_at == df["time"].iloc[1] + BAR


def test_classic_v_and_gaps():
    kinds = [l.kind for l in snr_levels(frame([(105, 106, 99, 100), (100, 104, 99.5, 103)]), BAR)]
    assert kinds == ["CLASSIC_V"]
    assert snr_levels(frame([(100, 103, 99, 102), (102, 105, 101.5, 104)]), BAR)[0].kind == "GAP_BULL"
    assert snr_levels(frame([(104, 105, 101, 102), (102, 102.5, 98, 99)]), BAR)[0].kind == "GAP_BEAR"


def test_doji_forms_no_level():
    assert snr_levels(frame([(100, 101, 99, 100), (100, 101, 99, 99.5)]), BAR) == []


# --- freshness (E03 p14-15) --------------------------------------------------

def _resistance_then(rows):
    base = [(100, 106, 99, 105), (105, 105.5, 101, 102)]   # A level at 105
    df = frame(base + rows)
    lvl = [l for l in snr_levels(df, BAR) if l.formed_index == 1][0]
    return df, lvl


def test_untouched_level_stays_fresh():
    df, lvl = _resistance_then([(102, 104, 101, 103), (103, 104.9, 102, 104)])
    assert update_freshness(df, lvl).status == "FRESH"


def test_wick_touch_makes_unfresh():
    df, lvl = _resistance_then([(102, 105.3, 101, 103)])
    lvl = update_freshness(df, lvl)
    assert lvl.status == "UNFRESH" and lvl.role == "RESISTANCE"


def test_body_close_through_flips_to_support_then_retest():
    df, lvl = _resistance_then([(102, 105.3, 101, 103), (103, 108, 102.5, 107), (107, 107.5, 104.8, 106)])
    lvl = update_freshness(df, lvl, upto=3)
    assert lvl.status == "FLIPPED_FRESH" and lvl.role == "SUPPORT"    # RBS
    lvl = update_freshness(df, lvl)
    assert lvl.history[-1] == (4, "flip_retest") and lvl.status == "UNFRESH"


def test_freshness_is_point_in_time():
    df, lvl = _resistance_then([(102, 104, 101, 103), (103, 105.3, 102, 104)])
    assert update_freshness(df, lvl, upto=2).status == "FRESH"     # bar 3 touch not yet known
    assert update_freshness(df, lvl, upto=3).status == "UNFRESH"


# --- BOS (E03 p37) ----------------------------------------------------------

def test_wick_through_swing_is_not_bos_body_close_is():
    rows = [(100, 101, 99, 100.5), (100.5, 102, 100, 101.5), (101.5, 105, 101, 104),  # swing high 105 at i=2
            (104, 104.5, 102, 102.5), (102.5, 103, 101, 101.5),                          # confirms at i=4 (k=2)
            (101.5, 106, 101, 104.8),                                                    # wick above, close below
            (104.8, 107, 104, 106)]                                                      # body close above
    df = frame(rows)
    assert (2, "HIGH", 105.0, 4) in swing_points(df, 2)
    ev = [e for e in bos(df, BAR, 2) if e.direction == "BULL"]
    assert [e.bar_index for e in ev] == [6]


def test_swing_not_usable_before_confirmation():
    rows = [(100, 101, 99, 100.5), (100.5, 102, 100, 101.5), (101.5, 105, 101, 104),
            (104, 106, 103, 105.5)]   # closes above 105 one bar after the pivot - pivot not confirmed yet
    assert [e for e in bos(frame(rows), BAR, 2) if e.direction == "BULL"] == []


# --- CRT & Turtle Soup (E04) -------------------------------------------------

def test_bullish_crt_purge_low_close_inside():
    df = frame([(105, 106, 100, 101), (101, 103, 99, 102)])
    (e,) = crt(df, BAR)
    assert e.direction == "BULL" and e.levels["mid"] == 103 and e.levels["purge_extreme"] == 99
    assert e.levels["candle1_bearish"] is True


def test_crt_close_outside_is_breakout_not_crt():
    assert crt(frame([(105, 106, 100, 101), (101, 102, 98, 99)]), BAR) == []


def test_crt_double_purge_skipped():
    assert crt(frame([(105, 106, 100, 101), (101, 107, 99, 102)]), BAR) == []


def test_turtle_soup_wick_requires_no_close_beyond():
    rows = [(100, 101, 99, 100)] * 20
    ok = frame(rows + [(100, 100.5, 98.5, 99.5)])
    assert [e.direction for e in turtle_soup_wick(ok, BAR, 20)] == ["BULL"]
    broke = frame(rows + [(100, 100.5, 98.5, 98.8)])
    assert turtle_soup_wick(broke, BAR, 20) == []


def test_bos_no_lookahead_on_random_wicks():
    import numpy as np
    rng = np.random.default_rng(11)
    c = 2000 + np.cumsum(rng.normal(0, 2, 500))
    o = np.r_[c[0], c[:-1]] + rng.normal(0, 0.3, 500)
    h = np.maximum(o, c) + rng.uniform(0.1, 2, 500)
    l = np.minimum(o, c) - rng.uniform(0.1, 2, 500)
    df = frame(list(zip(o, h, l, c)))
    full = bos(df, BAR, 2)
    k = 350
    trunc = bos(df.iloc[: k + 1].copy(), BAR, 2)
    sel = lambda ev: [(e.bar_index, e.direction, e.levels["swing_index"]) for e in ev if e.bar_index <= k]
    assert len(sel(full)) > 10 and sel(full) == sel(trunc)
    for e in full:   # the broken swing was confirmed strictly before the breaking bar
        assert e.levels["swing_index"] + 2 < e.bar_index
