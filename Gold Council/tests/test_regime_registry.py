import numpy as np

from gold_council.config import load_config
from gold_council.regime.engine import classify
from gold_council.strategies.registry import StrategyDef, load_registry, validate_registry
from tests.conftest import make_bars


def test_insufficient_bars_unknown(root):
    cfg = load_config(root / "config.yaml").regime
    r = classify(make_bars(np.full(50, 100.0)), cfg, event_risk=False)
    assert r.label == "UNKNOWN" and not r.data_ok


def test_strong_uptrend_detected(root):
    cfg = load_config(root / "config.yaml").regime
    rng = np.random.default_rng(1)
    closes = 2000 + np.cumsum(np.r_[rng.normal(0, 1, 300), np.full(60, 1.5) + rng.normal(0, 0.2, 60)])
    r = classify(make_bars(closes, spread=0.3), cfg, event_risk=False)
    assert r.direction == "UP" and r.persistence == "TRENDING"


def test_missing_calendar_never_routes(root):
    cfg = load_config(root / "config.yaml").regime
    rng = np.random.default_rng(2)
    r = classify(make_bars(2000 + np.cumsum(rng.normal(0, 1, 400))), cfg, event_risk=None)
    assert r.label in {"UNKNOWN", "HIGH_VOL"}


def test_regime_reproducible(root):
    cfg = load_config(root / "config.yaml").regime
    df = make_bars(2000 + np.cumsum(np.random.default_rng(3).normal(0, 1, 400)))
    assert classify(df, cfg, False) == classify(df.copy(), cfg, False)


def test_all_registry_entries_are_draft_and_cannot_emit(root):
    defs = load_registry(root / "knowledge/strategies")
    assert len(defs) >= 10 and validate_registry(defs) == []
    assert all(s.status == "draft" and not s.can_emit_candidates() for s in defs)


def test_approval_requires_sources_reviewer_and_no_unresolved():
    s = StrategyDef(id="x", spec_id="S99", version="0.1.0", status="paper_approved", family="t",
                    setup_tf="M15", unresolved=["exit"])
    probs = validate_registry([s])
    assert any("without source_refs" in p for p in probs) and any("unresolved" in p for p in probs)
    assert any("approver" in p for p in probs) and not s.can_emit_candidates()


def test_shuffled_or_duplicate_bars_are_unknown(root):
    cfg = load_config(root / "config.yaml").regime
    df = make_bars(2000 + np.cumsum(np.random.default_rng(4).normal(0, 1, 400)))
    shuffled = df.sample(frac=1, random_state=0)
    assert classify(shuffled, cfg, False).label == "UNKNOWN"
    dup = df.copy(); dup.loc[5, "time"] = dup.loc[4, "time"]
    r = classify(dup, cfg, False)
    assert r.label == "UNKNOWN" and not r.data_ok
