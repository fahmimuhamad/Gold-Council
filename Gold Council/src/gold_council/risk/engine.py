"""Deterministic risk engine (Step 18). Not an LLM. Fails closed.

Every check appends a reason code; any reason => REJECTED. Claude output can
only be an *input* (a proposed signal); it can never change RiskConfig.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from gold_council.config import RiskConfig
from gold_council.strategies.registry import StrategyDef

Side = Literal["LONG", "SHORT"]
ALLOWED_ACCOUNT_TYPES = {"paper", "demo"}


@dataclass(frozen=True)
class SymbolSpec:
    symbol: str
    point: float            # minimum price increment used for spread/stops
    tick_size: float
    tick_value: float       # account-currency value of one tick for 1.0 lot
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level_points: float = 0.0
    commission_per_lot: float = 0.0   # round-turn, account currency


@dataclass(frozen=True)
class Quote:
    bid: float
    ask: float
    time: datetime


@dataclass(frozen=True)
class Signal:
    signal_id: str
    symbol: str
    side: Side
    entry: float
    stop_loss: float | None
    take_profit: float | None
    created_at: datetime
    expires_at: datetime
    strategy_id: str


@dataclass
class AccountState:
    account_type: str
    initial_balance: float
    equity: float
    day_start_equity: float
    trades_today: int = 0
    open_positions: int = 0
    consecutive_losses: int = 0
    open_risk: float = 0.0          # cash risk reserved by open/pending orders
    kill_switch: bool = False


@dataclass
class RiskDecision:
    approved: bool
    volume: float = 0.0
    planned_cash_risk: float = 0.0
    reasons: list[str] = field(default_factory=list)


APPROVED_STRATEGY_STATUSES = {"paper_approved"}
FUTURE_TOLERANCE_SECONDS = 1.0


def _finite_pos(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x) and x > 0


def _finite_nonneg(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x) and x >= 0


def _input_problems(sig: "Signal", quote: "Quote", acct: "AccountState", spec: "SymbolSpec") -> list[str]:
    r = []
    if sig.side not in ("LONG", "SHORT"):
        r.append("INVALID_SIDE")
    for v in (sig.entry, quote.bid, quote.ask):
        if not _finite_pos(v):
            r.append("NON_FINITE_PRICE"); break
    for v in (sig.stop_loss, sig.take_profit):
        if v is not None and not _finite_pos(v):
            r.append("NON_FINITE_PRICE"); break
    if not all(_finite_pos(v) for v in (acct.initial_balance, acct.equity, acct.day_start_equity)):
        r.append("INVALID_ACCOUNT_VALUES")
    if not (_finite_nonneg(acct.open_risk) and acct.trades_today >= 0 and acct.open_positions >= 0
            and acct.consecutive_losses >= 0):
        r.append("INVALID_ACCOUNT_COUNTERS")
    if not (all(_finite_pos(v) for v in (spec.point, spec.tick_size, spec.tick_value, spec.volume_min,
                                         spec.volume_max, spec.volume_step))
            and _finite_nonneg(spec.stops_level_points) and _finite_nonneg(spec.commission_per_lot)
            and spec.volume_min <= spec.volume_max):
        r.append("INVALID_SYMBOL_SPEC")
    return r


def _round_down(value: float, step: float) -> float:
    if step <= 0:
        return 0.0
    n = math.floor(value / step + 1e-9)
    return round(n * step, 10)


def drawdowns(acct: AccountState) -> tuple[float, float]:
    """Return (daily_dd_pct, total_dd_pct) based on equity (includes open P&L)."""
    daily = max(0.0, (acct.day_start_equity - acct.equity) / acct.day_start_equity * 100)
    total = max(0.0, (acct.initial_balance - acct.equity) / acct.initial_balance * 100)
    return daily, total


class RiskEngine:
    def __init__(self, cfg: RiskConfig, strategies: dict[str, StrategyDef],
                 seen_signal_ids: set[str] | None = None):
        if cfg.allow_real_account:  # defensive; config model already forbids it
            raise RuntimeError("real accounts are prohibited in V1")
        self.cfg = cfg
        self.strategies = strategies   # registry lookup; the signal's own claims are never trusted
        self.seen = seen_signal_ids if seen_signal_ids is not None else set()

    def evaluate(self, sig: Signal, quote: Quote, acct: AccountState, spec: SymbolSpec,
                 now: datetime, in_news_blackout: bool | None) -> RiskDecision:
        try:
            return self._evaluate(sig, quote, acct, spec, now, in_news_blackout)
        except Exception as exc:  # any unexpected error fails closed
            return RiskDecision(False, reasons=[f"INTERNAL_ERROR:{type(exc).__name__}"])

    def _evaluate(self, sig, quote, acct, spec, now, in_news_blackout) -> RiskDecision:
        c = self.cfg
        bad = _input_problems(sig, quote, acct, spec)
        if bad:
            return RiskDecision(False, reasons=bad)
        r: list[str] = []

        if acct.kill_switch:
            r.append("KILL_SWITCH_ACTIVE")
        if acct.account_type not in ALLOWED_ACCOUNT_TYPES:
            r.append("ACCOUNT_TYPE_NOT_ALLOWED")
        strat = self.strategies.get(sig.strategy_id)
        if strat is None:
            r.append("UNKNOWN_STRATEGY")
        elif strat.status not in APPROVED_STRATEGY_STATUSES or not strat.can_emit_candidates():
            r.append("STRATEGY_NOT_PAPER_APPROVED")
        if sig.symbol != spec.symbol:
            r.append("SYMBOL_MISMATCH")
        if sig.signal_id in self.seen:
            r.append("DUPLICATE_SIGNAL")
        for t in (now, quote.time, sig.created_at, sig.expires_at):
            if t.tzinfo is None:
                r.append("NAIVE_TIMESTAMP")
                break
        else:
            if now >= sig.expires_at:
                r.append("SIGNAL_EXPIRED")
            if now < sig.created_at:
                r.append("SIGNAL_FROM_FUTURE")
            age = (now - quote.time).total_seconds()
            if age > c.max_quote_age_seconds:
                r.append("STALE_QUOTE")
            if age < -FUTURE_TOLERANCE_SECONDS:
                r.append("QUOTE_FROM_FUTURE")
        if in_news_blackout is None:
            r.append("NEWS_CALENDAR_MISSING")
        elif in_news_blackout:
            r.append("NEWS_BLACKOUT")

        if not (quote.bid > 0 and quote.ask > 0 and quote.ask >= quote.bid):
            r.append("INVALID_QUOTE")
        elif (quote.ask - quote.bid) / spec.point > c.max_spread_points:
            r.append("SPREAD_TOO_WIDE")

        if sig.stop_loss is None:
            r.append("MISSING_STOP_LOSS")
        if sig.take_profit is None:
            r.append("MISSING_TAKE_PROFIT")

        daily, total = drawdowns(acct)
        if daily >= c.internal_daily_stop_pct:
            r.append("DAILY_DRAWDOWN_STOP")
        if total >= c.internal_total_stop_pct:
            r.append("TOTAL_DRAWDOWN_STOP")
        if acct.trades_today >= c.max_trades_per_day:
            r.append("MAX_TRADES_PER_DAY")
        if acct.open_positions >= c.max_open_positions:
            r.append("MAX_OPEN_POSITIONS")
        if acct.consecutive_losses >= c.max_consecutive_losses:
            r.append("MAX_CONSECUTIVE_LOSSES")

        volume = 0.0
        cash_risk = 0.0
        if sig.stop_loss is not None and sig.take_profit is not None:
            if sig.side == "LONG":
                ok = sig.stop_loss < sig.entry < sig.take_profit
                exec_px, mark = quote.ask, quote.bid
                crossed = mark <= sig.stop_loss or mark >= sig.take_profit
            else:
                ok = sig.take_profit < sig.entry < sig.stop_loss
                exec_px, mark = quote.bid, quote.ask
                crossed = mark >= sig.stop_loss or mark <= sig.take_profit
            if not ok:
                r.append("INVALID_SL_TP_DIRECTION")
            elif crossed:
                r.append("STOP_OR_TARGET_ALREADY_CROSSED")
            else:
                if abs(exec_px - sig.entry) / spec.point > c.max_entry_deviation_points:
                    r.append("PRICE_DEVIATION_FROM_ENTRY")
                # Size from the worse of planned entry and current executable price.
                stop_dist = max(abs(sig.entry - sig.stop_loss), abs(exec_px - sig.stop_loss))
                tp_dist = min(abs(sig.take_profit - sig.entry), abs(sig.take_profit - exec_px))
                if tp_dist / stop_dist < c.min_reward_risk:
                    r.append("REWARD_RISK_TOO_LOW")
                if stop_dist / spec.point < spec.stops_level_points:
                    r.append("STOP_INSIDE_STOPS_LEVEL")
                slip = c.slippage_allowance_points * spec.point
                ticks = (stop_dist + slip) / spec.tick_size
                loss_per_lot = ticks * spec.tick_value + spec.commission_per_lot
                budget = acct.equity * c.risk_per_trade_pct / 100.0
                remaining_total = acct.equity - acct.initial_balance * (1 - c.internal_total_stop_pct / 100)
                remaining_daily = acct.equity - acct.day_start_equity * (1 - c.internal_daily_stop_pct / 100)
                budget = min(budget, remaining_total - acct.open_risk, remaining_daily - acct.open_risk)
                if budget <= 0:
                    r.append("NO_RISK_BUDGET")
                else:
                    volume = min(_round_down(budget / loss_per_lot, spec.volume_step), spec.volume_max)
                    if volume < spec.volume_min or volume <= 0:
                        r.append("MIN_VOLUME_EXCEEDS_RISK")
                        volume = 0.0
                    cash_risk = volume * loss_per_lot

        approved = not r
        if approved:
            self.seen.add(sig.signal_id)
        return RiskDecision(approved, volume if approved else 0.0, cash_risk if approved else 0.0, r)


class RiskState:
    """Persisted kill switch + seen signal IDs. Missing or corrupt state fails closed.

    A brand-new install must call `initialize()` once, explicitly. After that, a missing
    file is treated like corruption (kill switch ON, needs human reconciliation).
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def initialize(self) -> None:
        if self.path.exists():
            raise FileExistsError(f"risk state already exists: {self.path}")
        self.save(False, set())

    def load(self) -> dict:
        if not self.path.exists():
            return {"kill_switch": True, "seen_signal_ids": [], "updated_at": None, "error": "MISSING_STATE"}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            assert isinstance(data.get("seen_signal_ids"), list)
            assert isinstance(data.get("kill_switch"), bool)
            return data
        except Exception:
            return {"kill_switch": True, "seen_signal_ids": [], "updated_at": None, "error": "CORRUPT_STATE"}

    def save(self, kill_switch: bool, seen: set[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"kill_switch": kill_switch, "seen_signal_ids": sorted(seen),
                                   "updated_at": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
        tmp.replace(self.path)
