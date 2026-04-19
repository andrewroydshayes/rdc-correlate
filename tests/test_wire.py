import struct

from rdc_correlate.wire import parse_tlv_records


def _frame(records):
    body = b"".join(
        struct.pack("<HHI", rid, 0x00C0, len(val)) + val + struct.pack("<H", 0)
        for rid, val in records
    )
    return struct.pack("<IHHI", 12 + len(body), 2, len(records), 0) + body


def test_parse_single_int_record():
    buf = _frame([(0x044C, struct.pack("<i", 3600))])
    rs = list(parse_tlv_records(buf))
    assert len(rs) == 1
    _, rid, vlen, val = rs[0]
    assert rid == 0x044C
    assert vlen == 4
    assert struct.unpack("<i", val)[0] == 3600


def test_parse_multiple():
    buf = _frame([
        (0x044C, struct.pack("<i", 3600)),
        (0x0453, struct.pack("<i", 128)),
    ])
    rs = list(parse_tlv_records(buf))
    assert {r[1] for r in rs} == {0x044C, 0x0453}


def test_parse_rejects_wrong_version():
    body = struct.pack("<HHI", 0x044C, 0x00C0, 4) + struct.pack("<i", 3600) + struct.pack("<H", 0)
    bad = struct.pack("<IHHI", 12 + len(body), 3, 1, 0) + body
    assert list(parse_tlv_records(bad)) == []


def test_parse_skips_garbage_prefix():
    buf = b"\xAA" + _frame([(0x044C, struct.pack("<i", 3600))])
    rs = list(parse_tlv_records(buf))
    assert len(rs) == 1
