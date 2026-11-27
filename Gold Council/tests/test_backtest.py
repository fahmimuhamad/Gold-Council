import json
import math
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest

from gold_council.backtesting.engine import (Costs, HoldoutSealed, TradePlan, block_bootstrap_ci, chrono_split,
                                             metrics, run, segment)


def frame(rows):
    t = pd.date_range("2026-01-05", periods=len(rows), freq="1h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"]).assign(time=t)


def test_entry_is_next_bar_open_never_signal_bar():
    df = frame([(100, 101, 99, 100), (100.5, 103, 100.4, 102.5), (102.5, 106, 102, 105)])
    (r,) = run(df, [TradePlan("p", 0, "LONG", stop=99.5, target=104)])
    assert r.entry_index == 1 and r.entry == 100.5 and r.reason == "TP" and r.exit_index == 2
    assert r.r == pytest.approx((104 - 100.5) / (100.5 - 99.5))


def test_sl_first_when_both_in_same_bar():
    df = frame([(100, 101, 99, 100), (100, 100.5, 99.8, 100.2), (100.2, 105, 98, 101)])
    (r,) = run(df, [TradePlan("p", 0, "LONG", stop=99, target=104)])
    assert r.reason == "SL" and r.r == pytest.approx(-1.0)


def test_gap_through_stop_exits_at_open_worse_than_stop():
    df = frame([(100, 101, 99, 100), (100, 100.5, 99.6, 100.2), (97, 98, 96, 97.5)])
    (r,) = run(df, [TradePlan("p", 0, "LONG", stop=99, target=104)])
    assert r.reason == "SL_GAP" and r.exit == 97 and r.r == pytest.approx(-3.0)


def test_short_and_costs_are_adverse():
    df = frame([(100, 101, 99, 100), (100, 100.2, 99, 99.5), (99.5, 99.6, 95, 96)])
    (r,) = run(df, [TradePlan("p", 0, "SHORT", stop=102, target=96)], Costs(spread=0.2, slippage=0.1))
    # entry 100 - 0.1 - 0.1 = 99.8 ; exit 96 + 0.2 = 96.2 ; risk 2.2
    assert r.entry == pytest.approx(99.8) and r.exit == pytest.approx(96.2)
    assert r.r == pytest.approx((99.8 - 96.2) / 2.2)


def test_one_position_at_a_time_and_latency():
    df = frame([(100, 101, 99, 100)] + [(100, 100.5, 99.5, 100)] * 5)
    res = run(df, [TradePlan("a", 0, "LONG", 98, 110), TradePlan("b", 1, "LONG", 98, 110)])
    assert [x.reason for x in res] == ["END_OF_DATA", "SKIPPED_BUSY"]
    (r,) = run(df, [TradePlan("c", 0, "LONG", 98, 110)], Costs(latency_bars=2))
    assert r.entry_index == 3


def test_no_fill_when_open_gaps_past_stop_or_target():
    df = frame([(100, 101, 99, 100), (97, 98, 96, 97.5)])
    (r,) = run(df, [TradePlan("p", 0, "LONG", stop=98, target=104)])
    assert r.reason == "NO_FILL_GAPPED" and r.r is None
    (r,) = run(df, [TradePlan("q", 0, "SHORT", stop=104, target=98)])
    assert r.reason == "NO_FILL_GAPPED"
    assert metrics(run(df, [TradePlan("p", 0, "LONG", 98, 104)]))["not_traded"]["NO_FILL_GAPPED"] == 1


def test_invalid_when_costs_push_entry_past_target():
    df = frame([(100, 101, 99, 100), (100, 101, 99.5, 100.5)])
    (r,) = run(df, [TradePlan("p", 0, "LONG", stop=98, target=100.1)], Costs(spread=0.4))
    assert r.reason == "INVALID"


def test_metrics_known_values():
    df = frame([(100, 101, 99, 100), (100, 103, 99.9, 102), (102, 102.1, 98, 98.5),
                (98.5, 99, 98, 98.6), (98.6, 98.7, 97, 97.2)])
    res = run(df, [TradePlan("w", 0, "LONG", 99, 102), TradePlan("l", 2, "LONG", 97.5, 103)])
    m = metrics(res)
    assert m["trades"] == 2 and m["win_rate"] == 0.5
    assert m["total_r"] == pytest.approx(2.0 - 1.0) and m["profit_factor"] == pytest.approx(2.0)
    assert m["max_drawdown_r"] == pytest.approx(1.0)


def test_holdout_is_sealed():
    df = frame([(100, 101, 99, 100)] * 100)
    sp = chrono_split(len(df), gap_bars=2)
    assert sp.dev == (0, 60) and sp.validation == (62, 80) and sp.holdout == (82, 100)
    with pytest.raises(HoldoutSealed):
        segment(df, sp, "holdout")
    with pytest.raises(HoldoutSealed):
        segment(df, sp, "holdout", unseal_reason="   ")
    assert len(segment(df, sp, "holdout", unseal_reason="protocol v1 frozen; final evaluation")) == 18


def test_bootstrap_ci_contains_mean_and_needs_data():
    r = np.random.default_rng(0).normal(0.1, 1, 300)
    lo, hi = block_bootstrap_ci(r)
    assert lo < r.mean() < hi
    assert all(math.isnan(x) for x in block_bootstrap_ci(np.array([1.0, -1.0])))


def test_cli_backtest_labels_and_refuses_holdout(tmp_path, root, monkeypatch, capsys):
    from gold_council.cli import main
    rng = np.random.default_rng(5)
    c = 2000 + np.cumsum(rng.normal(0, 2, 800)); o = np.r_[c[0], c[:-1]]
    t = pd.date_range("2026-01-05", periods=800, freq="1h")
    p = tmp_path / "syn.csv"
    pd.DataFrame({"time": t.strftime("%Y-%m-%d %H:%M"), "open": o, "high": np.maximum(o, c) + 1,
                  "low": np.minimum(o, c) - 1, "close": c}).to_csv(p, index=False)
    monkeypatch.chdir(root)
    args = ["backtest", "--path", str(p), "--tz", "UTC", "--strategy", "donchian", "--spread", "0.3",
            "--label", "SYNTHETIC"]
    assert main(args) in (0, None)
    out = json.loads(capsys.readouterr().out)
    assert out["data_label"] == "SYNTHETIC" and out["trades"] > 0
    manifest = json.loads((root / out["saved_to"] / "manifest.json").read_text())
    assert manifest["data_sha256"] and manifest["split"]["holdout"]
    with pytest.raises(HoldoutSealed):
        main(args + ["--segment", "holdout"])
    # different settings must never share a run id (no silent overwrite)
    assert main(args + ["--gap-bars", "0"]) in (0, None)
    out2 = json.loads(capsys.readouterr().out)
    assert out2["run_id"] != out["run_id"]
    import shutil
    for o in (out, out2):
        shutil.rmtree(root / o["saved_to"])
