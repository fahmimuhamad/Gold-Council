from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from gold_council.config import load_config
from gold_council.risk.engine import AccountState, Quote, RiskEngine, RiskState, Signal, SymbolSpec
from gold_council.strategies.registry import SourceRef, StrategyDef

# Test-only strategy fixtures. The real registry has no approved strategies.
APPROVED = StrategyDef(id="test", spec_id="T01", version="0.0.1", status="paper_approved", family="t",
                       setup_tf="M15", source_refs=[SourceRef(source_id="fixture", location="p1")],
                       approved_by="test-fixture")
DRAFT = StrategyDef(id="draft_one", spec_id="T02", version="0.0.1", status="draft", family="t", setup_tf="M15")
STRATS = {s.id: s for s in (APPROVED, DRAFT)}

NOW = datetime(2026, 1, 6, 10, 0, tzinfo=timezone.utc)
# Illustrative contract spec only (100 oz contract, 0.01 tick => $1/tick/lot). Verify with your broker.
SPEC = SymbolSpec("XAUUSD", point=0.01, tick_size=0.01, tick_value=1.0, volume_min=0.01,
                  volume_max=50, volume_step=0.01, stops_level_points=10, commission_per_lot=7.0)


@pytest.fixture
def cfg(root):
    return load_config(root / "config.yaml").risk


def sig(**kw):
    base = dict(signal_id="s1", symbol="XAUUSD", side="LONG", entry=2000.0, stop_loss=1995.0,
                take_profit=2011.0, created_at=NOW - timedelta(minutes=1), expires_at=NOW + timedelta(minutes=30),
                strategy_id="test")
    base.update(kw)
    return Signal(**base)


def acct(**kw):
    base = dict(account_type="paper", initial_balance=10_000, equity=10_000, day_start_equity=10_000)
    base.update(kw)
    return AccountState(**base)


Q = Quote(bid=1999.9, ask=2000.1, time=NOW - timedelta(seconds=2))


def ev(cfg, s=None, q=Q, a=None, news=False, engine=None):
    e = engine or RiskEngine(cfg, STRATS)
    return e.evaluate(s or sig(), q, a or acct(), SPEC, NOW, news)


def test_valid_signal_sized_and_rounded_down(cfg):
    d = ev(cfg)
    assert d.approved, d.reasons
    # budget 25 USD; stop measured from ask 2000.1: (5.10+0.20)/0.01*1 + 7 = 537 -> 0.0465 -> 0.04 lots
    assert d.volume == pytest.approx(0.04)
    assert d.planned_cash_risk <= 25.0


@pytest.mark.parametrize("kw,code", [
    (dict(stop_loss=None), "MISSING_STOP_LOSS"),
    (dict(stop_loss=2001.0), "INVALID_SL_TP_DIRECTION"),
    (dict(take_profit=2009.0), "REWARD_RISK_TOO_LOW"),
    (dict(expires_at=NOW - timedelta(seconds=1)), "SIGNAL_EXPIRED"),
    (dict(symbol="XAGUSD"), "SYMBOL_MISMATCH"),
    (dict(strategy_id="draft_one"), "STRATEGY_NOT_PAPER_APPROVED"),
    (dict(strategy_id="nope"), "UNKNOWN_STRATEGY"),
    (dict(created_at=NOW + timedelta(minutes=1)), "SIGNAL_FROM_FUTURE"),
    (dict(side="SHORT"), "INVALID_SL_TP_DIRECTION"),
])
def test_signal_vetoes(cfg, kw, code):
    d = ev(cfg, sig(**kw))
    assert not d.approved and code in d.reasons and d.volume == 0


@pytest.mark.parametrize("kw,code", [
    (dict(account_type="real"), "ACCOUNT_TYPE_NOT_ALLOWED"),
    (dict(account_type="unknown"), "ACCOUNT_TYPE_NOT_ALLOWED"),
    (dict(kill_switch=True), "KILL_SWITCH_ACTIVE"),
    (dict(equity=9_840), "DAILY_DRAWDOWN_STOP"),
    (dict(initial_balance=10_700, day_start_equity=10_000, equity=10_000), "TOTAL_DRAWDOWN_STOP"),
    (dict(trades_today=3), "MAX_TRADES_PER_DAY"),
    (dict(open_positions=1), "MAX_OPEN_POSITIONS"),
    (dict(consecutive_losses=3), "MAX_CONSECUTIVE_LOSSES"),
    (dict(equity=100, day_start_equity=100, initial_balance=100), "MIN_VOLUME_EXCEEDS_RISK"),
])
def test_account_vetoes(cfg, kw, code):
    d = ev(cfg, a=acct(**kw))
    assert not d.approved and code in d.reasons


def test_quote_vetoes(cfg):
    stale = Quote(1999.9, 2000.1, NOW - timedelta(seconds=60))
    assert "STALE_QUOTE" in ev(cfg, q=stale).reasons
    wide = Quote(1999.0, 2000.0, NOW)
    assert "SPREAD_TOO_WIDE" in ev(cfg, q=wide).reasons
    crossed = Quote(2000.2, 2000.1, NOW)
    assert "INVALID_QUOTE" in ev(cfg, q=crossed).reasons


def test_news_missing_calendar_fails_closed(cfg):
    assert "NEWS_CALENDAR_MISSING" in ev(cfg, news=None).reasons
    assert "NEWS_BLACKOUT" in ev(cfg, news=True).reasons


def test_naive_timestamp_rejected(cfg):
    d = ev(cfg, sig(created_at=datetime(2026, 1, 6, 9, 59)))
    assert "NAIVE_TIMESTAMP" in d.reasons


def test_duplicate_signal_rejected(cfg):
    e = RiskEngine(cfg, STRATS)
    assert ev(cfg, engine=e).approved
    assert "DUPLICATE_SIGNAL" in ev(cfg, engine=e).reasons


def test_open_risk_reduces_budget(cfg):
    # daily internal floor = 9850; equity 9860 leaves 10; open risk 8 leaves 2 -> below min volume
    d = ev(cfg, a=acct(equity=9_860, open_risk=8))
    assert not d.approved and ("MIN_VOLUME_EXCEEDS_RISK" in d.reasons or "NO_RISK_BUDGET" in d.reasons)


def test_state_persistence_and_corruption_fails_closed(tmp_path):
    st = RiskState(tmp_path / "s.json")
    assert st.load()["kill_switch"] is True          # never initialised -> fail closed
    st.initialize()
    assert st.load()["kill_switch"] is False
    st.save(True, {"x"})
    (tmp_path / "s.json").unlink()                   # deleting the file must not clear the kill switch
    assert st.load()["kill_switch"] is True
    st.save(False, {"a", "b"})
    assert set(st.load()["seen_signal_ids"]) == {"a", "b"}
    (tmp_path / "s.json").write_text("{broken")
    assert st.load()["kill_switch"] is True


# --- regressions from independent review 2026-11-27 ---

@pytest.mark.parametrize("bid,ask,code", [
    (2049.9, 2050.1, "PRICE_DEVIATION_FROM_ENTRY"),
    (1990.0, 1990.2, "STOP_OR_TARGET_ALREADY_CROSSED"),
    (2015.0, 2015.2, "STOP_OR_TARGET_ALREADY_CROSSED"),
])
def test_quote_must_be_consistent_with_signal(cfg, bid, ask, code):
    d = ev(cfg, s=sig(take_profit=2100.0) if code == "PRICE_DEVIATION_FROM_ENTRY" else None, q=Quote(bid, ask, NOW))
    assert not d.approved and code in d.reasons


def test_sizing_uses_worse_executable_price(cfg):
    # ask 2000.40 is 40 points from entry (allowed) but makes the stop 5.40 away, not 5.00
    d = ev(cfg, s=sig(take_profit=2012.0), q=Quote(2000.30, 2000.40, NOW))
    assert d.approved, d.reasons
    loss_per_lot = (5.40 + 0.20) / 0.01 * 1.0 + 7.0
    assert d.volume * loss_per_lot <= 25.0 + 1e-9


def test_signal_status_claims_are_not_trusted(cfg):
    import dataclasses
    assert "strategy_status" not in {f.name for f in dataclasses.fields(Signal)}


def test_future_quote_rejected(cfg):
    assert "QUOTE_FROM_FUTURE" in ev(cfg, q=Quote(1999.9, 2000.1, NOW + timedelta(hours=5))).reasons


@pytest.mark.parametrize("akw,skw,code", [
    (dict(open_risk=-1000), {}, "INVALID_ACCOUNT_COUNTERS"),
    (dict(trades_today=-5), {}, "INVALID_ACCOUNT_COUNTERS"),
    (dict(consecutive_losses=-1), {}, "INVALID_ACCOUNT_COUNTERS"),
    (dict(day_start_equity=0), {}, "INVALID_ACCOUNT_VALUES"),
    (dict(equity=float("nan")), {}, "INVALID_ACCOUNT_VALUES"),
    (dict(equity=float("inf")), {}, "INVALID_ACCOUNT_VALUES"),
    ({}, dict(side="BUY"), "INVALID_SIDE"),
    ({}, dict(take_profit=float("inf")), "NON_FINITE_PRICE"),
])
def test_bad_inputs_rejected_not_raised(cfg, akw, skw, code):
    d = ev(cfg, s=sig(**skw), a=acct(**akw))
    assert not d.approved and code in d.reasons


@pytest.mark.parametrize("field,val", [("tick_value", 0.0), ("volume_step", 0.0), ("volume_min", 0.0)])
def test_bad_symbol_spec_rejected(cfg, field, val):
    from dataclasses import replace as rep
    d = RiskEngine(cfg, STRATS).evaluate(sig(), Q, acct(), rep(SPEC, **{field: val}), NOW, False)
    assert not d.approved and "INVALID_SYMBOL_SPEC" in d.reasons
