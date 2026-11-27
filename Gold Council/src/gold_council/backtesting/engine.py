"""Conservative OHLC backtester. Research only; results on synthetic data prove nothing.

Rules (documented, deliberately pessimistic):
- A plan created at the close of bar t can fill no earlier than the OPEN of bar t+1 (+latency_bars).
- Market entries fill at that open, adverse spread + slippage applied.
- If SL and TP are both inside one bar, the SL is assumed hit first (unknown intrabar order).
- A gap through SL exits at the bar open (worse than SL). A gap through TP exits at TP (no favourable gap credit).
- One position at a time; plans arriving while in a position are logged as SKIPPED_BUSY.
- If the fill bar opens already beyond the stop or the target, the plan is NOT filled (NO_FILL_GAPPED).
  This mirrors the live risk engine, which rejects STOP_OR_TARGET_ALREADY_CROSSED. Counts are reported in
  `not_traded`; a high NO_FILL_GAPPED share means the strategy's results are sensitive to this rule.
- Results are reported in R (multiples of planned risk incl. costs) so no account-size assumption is needed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TradePlan:
    plan_id: str
    bar_index: int          # bar whose close created the plan
    side: str               # LONG | SHORT
    stop: float
    target: float
    expires_bars: int = 1   # reserved for limit orders (not implemented); market plans fill at next open
    source: str = ""
    exit_channel: int | None = None   # exit when a close breaks the opposite N-bar channel (prior bars only)


@dataclass(frozen=True)
class Costs:
    spread: float = 0.0          # price units, round trip half applied at entry and half at exit
    slippage: float = 0.0        # price units per fill, adverse
    latency_bars: int = 0        # extra bars before the order can fill
    financing_per_year: float = 0.0   # fraction of entry price charged per year held (longs and shorts)


@dataclass
class TradeResult:
    plan_id: str
    side: str
    entry_index: int
    entry: float
    exit_index: int | None
    exit: float | None
    reason: str              # TP | SL | SL_GAP | END_OF_DATA | SKIPPED_BUSY | EXPIRED | INVALID
    r: float | None = None


def _adverse(px: float, side: str, amount: float, entering: bool) -> float:
    sign = 1 if (side == "LONG") == entering else -1
    return px + sign * amount


def n_rows_ok(df: pd.DataFrame) -> bool:
    return len(df) >= 2


def run(df: pd.DataFrame, plans: list[TradePlan], costs: Costs = Costs()) -> list[TradeResult]:
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    times = list(df["time"]) if "time" in df else None
    bar_dur = (df["time"].diff().dropna().min() if times is not None and n_rows_ok(df) else None)
    n = len(df)
    results: list[TradeResult] = []
    busy_until = -1
    for p in sorted(plans, key=lambda x: (x.bar_index, x.plan_id)):
        start = p.bar_index + 1 + costs.latency_bars
        if start >= n:
            results.append(TradeResult(p.plan_id, p.side, start, math.nan, None, None, "END_OF_DATA"))
            continue
        if start <= busy_until:
            results.append(TradeResult(p.plan_id, p.side, start, math.nan, None, None, "SKIPPED_BUSY"))
            continue
        cost = costs.spread / 2 + costs.slippage
        entry = _adverse(o[start], p.side, cost, entering=True)
        long = p.side == "LONG"
        raw = o[start]
        if (long and (raw <= p.stop or raw >= p.target)) or (not long and (raw >= p.stop or raw <= p.target)):
            results.append(TradeResult(p.plan_id, p.side, start, float(raw), None, None, "NO_FILL_GAPPED"))
            continue
        risk = (entry - p.stop) if long else (p.stop - entry)
        reward_ok = (p.target > entry) if long else (p.target < entry)
        if risk <= 0 or not reward_ok:
            results.append(TradeResult(p.plan_id, p.side, start, entry, None, None, "INVALID"))
            continue
        exit_px, exit_i, reason = None, None, "END_OF_DATA"
        exit_next_open = False
        for j in range(start, n):
            if exit_next_open:                      # channel exit decided at previous close
                exit_px, exit_i, reason = o[j], j, "CHANNEL"; break
            # gap at open (not on the entry bar, whose open IS the entry)
            if j > start:
                if (long and o[j] <= p.stop) or (not long and o[j] >= p.stop):
                    exit_px, exit_i, reason = o[j], j, "SL_GAP"; break
            hit_sl = (l[j] <= p.stop) if long else (h[j] >= p.stop)
            hit_tp = (h[j] >= p.target) if long else (l[j] <= p.target)
            if hit_sl:
                exit_px, exit_i, reason = p.stop, j, "SL"; break
            if hit_tp:
                exit_px, exit_i, reason = p.target, j, "TP"; break
            if p.exit_channel and j >= p.exit_channel:
                w = slice(j - p.exit_channel, j)     # prior N bars, excluding j
                if (long and c[j] < l[w].min()) or (not long and c[j] > h[w].max()):
                    exit_next_open = True
        if exit_px is None:
            exit_i = n - 1
            exit_px = df["close"].iloc[-1]
        exit_px = _adverse(exit_px, p.side, cost, entering=False)
        pnl = (exit_px - entry) if long else (entry - exit_px)
        if costs.financing_per_year and times is not None:
            # exits at an open (CHANNEL, SL_GAP) end at that open; intrabar/END_OF_DATA exits are charged
            # through the END of the exit bar (conservative)
            end_t = times[exit_i] if reason in ("CHANNEL", "SL_GAP") else times[exit_i] + bar_dur
            days = (end_t - times[start]).total_seconds() / 86400
            pnl -= entry * costs.financing_per_year * days / 365
        results.append(TradeResult(p.plan_id, p.side, start, float(entry), exit_i, float(exit_px), reason, pnl / risk))
        busy_until = exit_i
    return results


def block_bootstrap_ci(r: np.ndarray, block: int = 5, n_boot: int = 2000, seed: int = 0,
                       alpha: float = 0.05) -> tuple[float, float]:
    """Moving-block bootstrap CI for mean R (trades are not assumed independent)."""
    if len(r) < block * 2:
        return (math.nan, math.nan)
    rng = np.random.default_rng(seed)
    k = math.ceil(len(r) / block)
    starts = np.arange(len(r) - block + 1)
    means = []
    for _ in range(n_boot):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, k)])[: len(r)]
        means.append(r[idx].mean())
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)))


def metrics(results: list[TradeResult]) -> dict:
    done = [x for x in results if x.r is not None]
    r = np.array([x.r for x in done], dtype=float)
    out = {"plans": len(results), "trades": len(done),
           "not_traded": {k: sum(1 for x in results if x.reason == k and x.r is None)
                          for k in ("SKIPPED_BUSY", "NO_FILL_GAPPED", "INVALID", "END_OF_DATA")}}
    if not len(r):
        return {**out, "note": "no completed trades"}
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[1:]
    gains, losses = r[r > 0].sum(), -r[r < 0].sum()
    lo, hi = block_bootstrap_ci(r)
    out.update({
        "win_rate": float((r > 0).mean()), "expectancy_r": float(r.mean()), "total_r": float(r.sum()),
        "profit_factor": float(gains / losses) if losses > 0 else math.inf,
        "max_drawdown_r": float((peak - eq).max()), "avg_win_r": float(r[r > 0].mean()) if (r > 0).any() else 0.0,
        "avg_loss_r": float(r[r < 0].mean()) if (r < 0).any() else 0.0,
        "expectancy_ci95_block_bootstrap": [lo, hi],
        "exits": {k: sum(1 for x in done if x.reason == k) for k in ("TP", "SL", "SL_GAP", "CHANNEL", "END_OF_DATA")},
    })
    return out


# ------------------------------------------------------------------ chronological splits

@dataclass(frozen=True)
class Split:
    dev: tuple[int, int]
    validation: tuple[int, int]
    holdout: tuple[int, int]


def chrono_split(n: int, dev: float = 0.6, val: float = 0.2, gap_bars: int = 0) -> Split:
    """60/20/20 by default, with optional embargo gap between segments. End index exclusive."""
    a = int(n * dev)
    b = int(n * (dev + val))
    return Split((0, a), (a + gap_bars, b), (b + gap_bars, n))


class HoldoutSealed(RuntimeError):
    pass


MIN_UNSEAL_REASON = 20


def segment(df: pd.DataFrame, split: Split, name: str, unseal_reason: str | None = None) -> pd.DataFrame:
    if name == "holdout" and len((unseal_reason or "").strip()) < MIN_UNSEAL_REASON:
        raise HoldoutSealed("final holdout is sealed; unsealing requires a recorded reason and a frozen protocol")
    s, e = getattr(split, name)
    return df.iloc[s:e].reset_index(drop=True)
