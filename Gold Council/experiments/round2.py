"""Round 2 runner — implements reports/2026-11-27_preregistration_round2.md exactly. DEV only."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from gold_council.backtesting.engine import Costs, chrono_split, metrics, run
from gold_council.backtesting.plans import bias_for_daily, crt_atr_plans, donchian_channel_plans
from gold_council.config import load_config
from gold_council.market_data.csv_import import load_csv
from gold_council.market_data.resample import resample

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data/historical/dukascopy/XAUUSD_H1_dukascopy_bid_utc.csv"
COSTS = Costs(spread=0.44, slippage=0.10, financing_per_year=0.04)


def main():
    h1 = load_csv(CSV, "UTC")
    sp = chrono_split(len(h1), gap_bars=24)
    dev_end = h1["time"].iloc[sp.dev[1] - 1]                  # last DEV hour (round-1 boundary)
    d1, h4, w1 = resample(h1, "1D"), resample(h1, "4h"), resample(h1, "W")
    dur = {"D1": timedelta(days=1), "H4": timedelta(hours=4)}

    def dev(df, d):   # candles that END by the DEV boundary
        return df[df["time"] + d <= dev_end + timedelta(hours=1)].reset_index(drop=True)

    d1d, h4d = dev(d1, dur["D1"]), dev(h4, dur["H4"])
    w1d = w1[w1["time"] < dev_end].reset_index(drop=True)
    reg = load_config(ROOT / "config.yaml").regime
    tests = {
        "R2-1 Donchian D1 20/10": (d1d, donchian_channel_plans(d1d, dur["D1"])),
        "R2-2 Donchian H4 20/10": (h4d, donchian_channel_plans(h4d, dur["H4"])),
        "R2-3 CRT H4 1/5/9am NY": (h4d, crt_atr_plans(h4d, dur["H4"], ny_hours={1, 5, 9})),
        "R2-4 CRT D1 weekly bias": (d1d, crt_atr_plans(d1d, dur["D1"], bias_at_bar=bias_for_daily(d1d, w1d))),
        "R2-5 Donchian D1 + regime": (d1d, donchian_channel_plans(d1d, dur["D1"], regime=reg)),
    }
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    out = {"run_at": datetime.now(timezone.utc).isoformat(), "preregistration": "reports/2026-11-27_preregistration_round2.md",
           "code_commit": commit, "data_sha256": hashlib.sha256(CSV.read_bytes()).hexdigest(),
           "dev_end_utc": str(dev_end), "costs": COSTS.__dict__, "data_label": "REAL_PUBLIC", "results": {}}
    for name, (df, plans) in tests.items():
        res = run(df, plans, COSTS)
        m = metrics(res)
        pid = {p.plan_id: p for p in plans}
        h, l = df["high"].to_numpy(), df["low"].to_numpy()
        amb = sum(1 for r in res if r.reason == "SL" and np.isfinite(pid[r.plan_id].target) and
                  (h[r.exit_index] >= pid[r.plan_id].target if r.side == "LONG" else l[r.exit_index] <= pid[r.plan_id].target))
        m0 = metrics(run(df, plans, Costs()))
        lo = m.get("expectancy_ci95_block_bootstrap", [float("nan")])[0]
        verdict = ("INSUFFICIENT SAMPLE (<100 trades)" if m["trades"] < 100 else
                   "PASS -> validation" if m.get("expectancy_r", -1) > 0 and lo > 0 else "FAIL")
        out["results"][name] = {"verdict": verdict, "period": [str(df["time"].iloc[0]), str(df["time"].iloc[-1])],
                                "ambiguous_same_bar_SL": amb, "zero_cost_expectancy_r": m0.get("expectancy_r"),
                                "zero_cost_ci95": m0.get("expectancy_ci95_block_bootstrap"), **m}
    dest = ROOT / "reports/backtests/round2"; dest.mkdir(parents=True, exist_ok=True)
    (dest / "results.json").write_text(json.dumps(out, indent=2, default=str))
    for k, v in out["results"].items():
        print(f"{k:28} {v['verdict']:34} trades={v['trades']:4} win={v.get('win_rate', 0):.1%} "
              f"expR={v.get('expectancy_r', float('nan')):+.3f} CI={[round(x, 3) for x in v.get('expectancy_ci95_block_bootstrap', [])]} "
              f"maxDD={v.get('max_drawdown_r', float('nan')):.1f} zeroCost={v['zero_cost_expectancy_r']:+.3f} amb={v['ambiguous_same_bar_SL']} exits={v.get('exits')}")


if __name__ == "__main__":
    main()
