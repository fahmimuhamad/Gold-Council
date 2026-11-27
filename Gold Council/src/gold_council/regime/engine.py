"""Deterministic multi-dimensional regime classification (Step 10). Draft thresholds."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from gold_council.config import RegimeConfig
from gold_council.features.indicators import adx, atr, efficiency_ratio, ema, rolling_percentile

REGIME_VERSION = "0.1.0-draft"


@dataclass(frozen=True)
class Regime:
    version: str
    direction: str      # UP | DOWN | FLAT | UNKNOWN
    persistence: str    # TRENDING | RANGING | UNKNOWN
    volatility: str     # LOW | NORMAL | HIGH | UNKNOWN
    label: str          # TREND_UP | TREND_DOWN | RANGE | COMPRESSION | HIGH_VOL | UNKNOWN
    event_risk: bool | None
    data_ok: bool
    inputs: dict

    def to_dict(self) -> dict:
        return asdict(self)


def classify(df: pd.DataFrame, cfg: RegimeConfig, event_risk: bool | None = None) -> Regime:
    """Classify the last completed bar of df. Uses only rows in df."""
    t = df["time"] if "time" in df else None
    unordered = t is not None and (t.duplicated().any() or not t.is_monotonic_increasing)
    if unordered or len(df) < cfg.min_bars or df[["open", "high", "low", "close"]].isna().any().any():
        return Regime(REGIME_VERSION, "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", event_risk, False,
                      {"bars": len(df)})
    df = df.reset_index(drop=True)
    a = adx(df, cfg.adx_period).iloc[-1]
    er = efficiency_ratio(df["close"], cfg.er_period).iloc[-1]
    ap = rolling_percentile(atr(df, cfg.atr_period), cfg.atr_pct_lookback).iloc[-1]
    e = ema(df["close"], cfg.ema_period)
    slope = e.iloc[-1] - e.iloc[-6]
    inputs = {"adx": float(a), "er": float(er), "atr_pct": float(ap), "ema_slope_5": float(slope)}
    if any(np.isnan(v) for v in inputs.values()):
        return Regime(REGIME_VERSION, "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", event_risk, False, inputs)

    trending = a >= cfg.adx_trend_min and er >= cfg.er_trend_min
    persistence = "TRENDING" if trending else "RANGING"
    direction = ("UP" if slope > 0 else "DOWN" if slope < 0 else "FLAT") if trending else "FLAT"
    vol = "HIGH" if ap >= cfg.atr_pct_high else "LOW" if ap <= cfg.atr_pct_low else "NORMAL"

    if event_risk is None or event_risk or vol == "HIGH":
        label = "HIGH_VOL" if (vol == "HIGH" or event_risk) else "UNKNOWN"
    elif trending:
        label = "TREND_UP" if direction == "UP" else "TREND_DOWN" if direction == "DOWN" else "UNKNOWN"
    elif vol == "LOW":
        label = "COMPRESSION"
    else:
        label = "RANGE"
    return Regime(REGIME_VERSION, direction, persistence, vol, label, event_risk, True, inputs)


# Spec Step 10 routing table: regime label -> strategy families eligible for research.
ROUTING = {
    "TREND_UP": {"donchian", "fvg_pullback"},
    "TREND_DOWN": {"donchian", "fvg_pullback"},
    "RANGE": {"zscore_reversion", "turtle_soup"},
    "COMPRESSION": {"orb", "atr_breakout", "nr7_breakout"},
    "HIGH_VOL": set(),
    "UNKNOWN": set(),
}
