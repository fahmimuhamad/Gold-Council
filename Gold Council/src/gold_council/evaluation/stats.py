"""Significance and multiple-testing statistics (no lookahead concerns: operate on finished trade lists)."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats as st


def newey_west_t(x: np.ndarray, lags: int = 5) -> tuple[float, float]:
    """HAC (Bartlett kernel) t-statistic for mean(x) > 0 and its one-sided p-value."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < lags + 2:
        return math.nan, math.nan
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, lags + 1):
        w = 1 - k / (lags + 1)
        s += 2 * w * (e[k:] @ e[:-k]) / n
    se = math.sqrt(s / n) if s > 0 else math.nan
    t = x.mean() / se if se and se > 0 else math.nan
    return t, (1 - st.norm.cdf(t)) if not math.isnan(t) else math.nan


def holm(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm-Bonferroni step-down. Returns per-test threshold and reject decision."""
    items = sorted(pvalues.items(), key=lambda kv: (math.inf if math.isnan(kv[1]) else kv[1]))
    m = len(items)
    out, still = {}, True
    for i, (k, p) in enumerate(items):
        thr = alpha / (m - i)
        rej = still and not math.isnan(p) and p < thr
        still = still and rej
        out[k] = {"p": p, "threshold": thr, "reject_null": rej}
    return out


def deflated_sharpe(returns: np.ndarray, n_trials: int, var_trial_sr: float) -> dict:
    """Bailey & Lopez de Prado (2014). Per-observation (non-annualised) Sharpe ratios throughout."""
    r = np.asarray(returns, dtype=float)
    T = len(r)
    if T < 3 or r.std(ddof=1) == 0:
        return {"sr": math.nan, "sr0": math.nan, "dsr": math.nan}
    sr = r.mean() / r.std(ddof=1)
    g = 0.5772156649
    sr0 = math.sqrt(max(var_trial_sr, 0.0)) * ((1 - g) * st.norm.ppf(1 - 1 / n_trials)
                                               + g * st.norm.ppf(1 - 1 / (n_trials * math.e)))
    skew, kurt = st.skew(r), st.kurtosis(r, fisher=False)
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    dsr = st.norm.cdf((sr - sr0) * math.sqrt(T - 1) / denom)
    return {"sr": float(sr), "sr0": float(sr0), "dsr": float(dsr)}
