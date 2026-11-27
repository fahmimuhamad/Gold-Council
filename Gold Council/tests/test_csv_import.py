import pytest
from datetime import timedelta

from gold_council.market_data.csv_import import load_csv, validate

CSV = """time,open,high,low,close,tick_volume
2026-01-05 10:00,2000,2001,1999,2000.5,10
2026-01-05 10:15,2000.5,2002,2000,2001,12
2026-01-05 10:15,2000.5,2002,2000,2001,12
2026-01-05 11:00,2001,2000,2000.5,2001.5,9
"""


def test_requires_explicit_timezone(tmp_path):
    p = tmp_path / "x.csv"; p.write_text(CSV)
    with pytest.raises(ValueError):
        load_csv(p, None)


def test_validation_flags_problems(tmp_path):
    p = tmp_path / "x.csv"; p.write_text(CSV)
    df = load_csv(p, "Europe/Athens")
    assert str(df["time"].iloc[0]) == "2026-01-05 08:00:00+00:00"
    rep = validate(df, timedelta(minutes=15))
    assert rep.duplicates == 1 and rep.bad_ohlc == 1 and rep.gaps == 1 and not rep.ok


def test_ny_plus_7_broker_clock(tmp_path):
    # Broker midnight = 17:00 New York = 22:00 UTC in winter, 21:00 UTC in summer (US DST)
    p = tmp_path / "b.csv"
    p.write_text("time,open,high,low,close\n2026-01-06 00:00,1,1,1,1\n2026-07-07 00:00,1,1,1,1\n")
    df = load_csv(p, "America/New_York+7")
    assert [str(x) for x in df["time"]] == ["2026-01-05 22:00:00+00:00", "2026-07-06 21:00:00+00:00"]


def test_bad_tz_spec_rejected(tmp_path):
    p = tmp_path / "x.csv"; p.write_text(CSV)
    with pytest.raises(ValueError):
        load_csv(p, "GMT+2")
