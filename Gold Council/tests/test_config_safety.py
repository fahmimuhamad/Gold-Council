import copy

import pytest
import yaml
from pydantic import ValidationError

from gold_council.config import Config, load_config


def raw(root):
    return yaml.safe_load(open(root / "config.yaml"))


def test_project_config_loads_offline(root):
    cfg = load_config(root / "config.yaml")
    assert cfg.mode == "offline"
    assert cfg.risk.allow_real_account is False


@pytest.mark.parametrize("key", ["allow_real_account", "martingale", "grid_recovery"])
def test_dangerous_flags_cannot_be_enabled(root, key):
    r = raw(root); r["risk"][key] = True
    with pytest.raises(ValidationError):
        Config.model_validate(r)


def test_live_mode_rejected(root):
    r = raw(root); r["mode"] = "live"
    with pytest.raises(ValidationError):
        Config.model_validate(r)


def test_internal_stops_must_sit_below_hard_limits(root):
    r = raw(root); r["risk"]["internal_daily_stop_pct"] = 2.5
    with pytest.raises(ValidationError):
        Config.model_validate(r)


def test_unknown_keys_rejected(root):
    r = raw(root); r["risk"]["override_risk"] = True
    with pytest.raises(ValidationError):
        Config.model_validate(r)


def test_config_is_immutable(root):
    cfg = load_config(root / "config.yaml")
    with pytest.raises(ValidationError):
        cfg.risk.risk_per_trade_pct = 5.0


def test_no_execution_capability():
    from gold_council.execution import CAN_PLACE_ORDERS
    assert CAN_PLACE_ORDERS is False


def test_no_secrets_in_env_example(root):
    txt = (root / ".env.example").read_text()
    assert "sk-" not in txt and "ANTHROPIC_API_KEY=" not in txt
