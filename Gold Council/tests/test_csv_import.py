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
