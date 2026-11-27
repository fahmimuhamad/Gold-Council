import json
import subprocess
import sys

from gold_council.cli import main


def test_help_runs():
    r = subprocess.run([sys.executable, "-m", "gold_council.cli", "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "no live trading" in r.stdout


def test_status_reports_safety(capsys, root, monkeypatch):
    monkeypatch.chdir(root)
    assert main(["status"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["can_place_orders"] is False and out["allow_real_account"] is False
    assert "any order execution" in out["not_implemented"]


def test_strategies_validate(capsys, root, monkeypatch):
    monkeypatch.chdir(root)
    assert main(["strategies", "validate"]) == 0
