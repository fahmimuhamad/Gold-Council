import lzma
import struct
from datetime import datetime, timezone

import pytest

from gold_council.market_data.dukascopy import decode


def blob(records):
    return lzma.compress(b"".join(struct.pack(">5if", *r) for r in records), format=lzma.FORMAT_ALONE)


def test_decode_scales_prices_and_drops_closed_hours():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    raw = blob([(0, 2062688, 2062688, 2062688, 2062688, 0.0),          # closed market: dropped
                (3600, 2074465, 2074145, 2072865, 2076665, 0.608)])
    df = decode(raw, start, 1000)
    assert len(df) == 1
    r = df.iloc[0]
    assert r["time"] == datetime(2024, 1, 1, 1, tzinfo=timezone.utc)
    assert (r["open"], r["high"], r["low"], r["close"]) == (2074.465, 2076.665, 2072.865, 2074.145)


def test_corrupt_payload_rejected():
    with pytest.raises(ValueError):
        decode(lzma.compress(b"x" * 25, format=lzma.FORMAT_ALONE), datetime(2024, 1, 1, tzinfo=timezone.utc), 1000)
