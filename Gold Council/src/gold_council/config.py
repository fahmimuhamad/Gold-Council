"""Configuration loading and validation. Fails closed."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_per_trade_pct: float = Field(gt=0, le=1.0)
    daily_drawdown_limit_pct: float = Field(gt=0, le=10)
    total_drawdown_limit_pct: float = Field(gt=0, le=20)
    internal_daily_stop_pct: float = Field(gt=0)
    internal_total_stop_pct: float = Field(gt=0)
    max_trades_per_day: int = Field(ge=0)
    max_open_positions: int = Field(ge=0)
    max_consecutive_losses: int = Field(ge=0)
    min_reward_risk: float = Field(gt=0)
    max_spread_points: float = Field(gt=0)
    max_quote_age_seconds: float = Field(gt=0)
    max_entry_deviation_points: float = Field(gt=0)
    news_blackout_minutes_before: int = Field(ge=0)
    news_blackout_minutes_after: int = Field(ge=0)
    slippage_allowance_points: float = Field(ge=0)
    martingale: Literal[False] = False
    grid_recovery: Literal[False] = False
    allow_real_account: Literal[False] = False

    @field_validator("internal_daily_stop_pct")
    @classmethod
    def _daily_buffer(cls, v, info):
        lim = info.data.get("daily_drawdown_limit_pct")
        if lim is not None and v >= lim:
            raise ValueError("internal_daily_stop_pct must be below daily_drawdown_limit_pct")
        return v

    @field_validator("internal_total_stop_pct")
    @classmethod
    def _total_buffer(cls, v, info):
        lim = info.data.get("total_drawdown_limit_pct")
        if lim is not None and v >= lim:
            raise ValueError("internal_total_stop_pct must be below total_drawdown_limit_pct")
        return v


class RegimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    adx_period: int = 14
    adx_trend_min: float = 25
    er_period: int = 20
    er_trend_min: float = 0.30
    atr_period: int = 14
    atr_pct_lookback: int = 250
    atr_pct_high: float = 0.80
    atr_pct_low: float = 0.20
    ema_period: int = 50
    min_bars: int = 300


class InstrumentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    symbol: str
    secondary: list[str] = []


class PathsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    knowledge_db: str = "data/knowledge.db"
    risk_state: str = "data/risk_state.json"
    strategies: str = "knowledge/strategies"


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode: Literal["offline", "paper"]
    instrument: InstrumentConfig
    paths: PathsConfig = PathsConfig()
    risk: RiskConfig
    regime: RegimeConfig = RegimeConfig()


def project_root() -> Path:
    here = Path.cwd()
    for p in [here, *here.parents]:
        if (p / "config.yaml").exists() and (p / "pyproject.toml").exists():
            return p
    return here


def load_config(path: str | Path | None = None) -> Config:
    p = Path(path) if path else project_root() / "config.yaml"
    with open(p, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config.model_validate(raw)
