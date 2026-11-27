"""Round 3 runner — implements reports/2026-11-27_preregistration_round3.md exactly. DEV only."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from gold_council.backtesting.engine import Costs, block_bootstrap_ci, chrono_split, run
from gold_council.backtesting.plans import BUILDERS
from gold_council.backtesting.returns_strategies import asian_drift, rsi2_reversion, weekend_long
from gold_council.evaluation.stats import deflated_sharpe, holm, newey_west_t
from gold_council.market_data.csv_import import load_csv
from gold_council.market_data.resample import resample

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data/historical/dukascopy/XAUUSD_H1_dukascopy_bid_utc.csv"
SPREAD, SLIP, FIN = 0.44, 0.10, 0.04


def prior_trial_returns(h1):
    """Per-trade returns (R) of the 8 earlier trials, recomputed on the same engine, for DSR variance."""
    sp = chrono_split(len(h1), gap_bars=24)
    seg = h1.iloc[sp.dev[0]:sp.dev[1]].reset_index(drop=True)
    out = {}
    for name in ("donchian", "crt_mid", "crt_far"):
        res = run(seg, BUILDERS[name](seg, timedelta(hours=1)), Costs(spread=SPREAD, slippage=SLIP))
        out[f"R1 {name}"] = np.array([r.r for r in res if r.r is not None])
    spec = importlib.util.spec_from_file_location("round2", ROOT / "experiments/round2.py")
    r2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r2)
    tests, _ = r2.build_tests(h1)
    for name, (df, plans) in tests.items():
        out[name] = np.array([r.r for r in run(df, plans, r2.COSTS) if r.r is not None])
    return out


def main():
    h1 = load_csv(CSV, "UTC")
    sp = chrono_split(len(h1), gap_bars=24)
    dev_end = h1["time"].iloc[sp.dev[1] - 1]
    h1d = h1[h1["time"] <= dev_end].reset_index(drop=True)
    d1 = resample(h1, "1D")
    d1d = d1[d1["time"] + timedelta(days=1) <= dev_end + timedelta(hours=1)].reset_index(drop=True)

    trades = {
        "R3-A Asian drift 23->07 UTC": asian_drift(h1d, SPREAD, SLIP),
        "R3-C RSI(2) D1": rsi2_reversion(d1d, SPREAD, SLIP, FIN),
        "R3-W Weekend long (>SMA200)": weekend_long(d1d, SPREAD, SLIP, FIN),
    }
    trades = {k: [t for t in v if t.exit_time <= dev_end + timedelta(hours=1)] for k, v in trades.items()}

    prior = prior_trial_returns(h1)
    srs = [r.mean() / r.std(ddof=1) for r in prior.values() if len(r) > 2]
    rets = {k: np.array([t.net_bp for t in v]) for k, v in trades.items()}
    srs += [r.mean() / r.std(ddof=1) for r in rets.values() if len(r) > 2]
    var_sr, n_trials = float(np.var(srs, ddof=1)), len(srs)
    assert n_trials == 11, f"expected 11 cumulative trials, got {n_trials}"

    pvals = {k: newey_west_t(r, 5)[1] for k, r in rets.items()}
    hm = holm(pvals, 0.05)
    out = {"run_at": datetime.now(timezone.utc).isoformat(), "preregistration": "reports/2026-11-27_preregistration_round3.md",
           "code_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
           "data_sha256": hashlib.sha256(CSV.read_bytes()).hexdigest(), "dev_end_utc": str(dev_end),
           "costs": {"spread": SPREAD, "slippage": SLIP, "financing_per_year": FIN},
           "n_trials_cumulative": n_trials, "var_trial_sharpe": var_sr, "data_label": "REAL_PUBLIC", "results": {}}
    for k, r in rets.items():
        lo, hi = block_bootstrap_ci(r, block=5)
        t, p = newey_west_t(r, 5)
        passed = len(r) >= 100 and r.mean() > 0 and lo > 0 and hm[k]["reject_null"]
        verdict = "PASS -> validation" if passed else ("INSUFFICIENT SAMPLE (<100 trades)" if len(r) < 100 else "FAIL")
        dsr = deflated_sharpe(r, n_trials, var_sr)
        out["results"][k] = {"verdict": verdict, "trades": int(len(r)), "mean_net_bp": float(r.mean()),
                             "median_net_bp": float(np.median(r)), "win_rate": float((r > 0).mean()),
                             "total_net_bp": float(r.sum()), "ci95_mean_bp": [lo, hi], "nw_t": t, "p_one_sided": p,
                             "holm": hm[k], "deflated_sharpe": dsr,
                             "first": str(trades[k][0].entry_time) if trades[k] else None,
                             "last": str(trades[k][-1].exit_time) if trades[k] else None}
    dest = ROOT / "reports/backtests/round3"; dest.mkdir(parents=True, exist_ok=True)
    (dest / "results.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"cumulative trials={n_trials}  var(trial SR)={var_sr:.5f}")
    for k, v in out["results"].items():
        print(f"{k:30} {v['verdict']:28} n={v['trades']:5} mean={v['mean_net_bp']:+.2f}bp win={v['win_rate']:.1%} "
              f"CI=[{v['ci95_mean_bp'][0]:+.2f},{v['ci95_mean_bp'][1]:+.2f}] t={v['nw_t']:.2f} p={v['p_one_sided']:.4f} "
              f"holm_thr={v['holm']['threshold']:.4f} DSR={v['deflated_sharpe']['dsr']:.3f}")


if __name__ == "__main__":
    main()
