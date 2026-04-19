"""SQLite storage for wire_records + cloud_samples + cloud_fields."""

import sqlite3


SCHEMA = """
CREATE TABLE IF NOT EXISTS wire_records (
    ts REAL NOT NULL,
    param_id INTEGER NOT NULL,
    vlen INTEGER NOT NULL,
    value_i32 INTEGER,
    value_i64 INTEGER,
    value_bytes BLOB
);
CREATE INDEX IF NOT EXISTS idx_wire_ts ON wire_records(ts);
CREATE INDEX IF NOT EXISTS idx_wire_pid ON wire_records(param_id);

CREATE TABLE IF NOT EXISTS cloud_samples (
    ts INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (ts, device_id)
);

CREATE TABLE IF NOT EXISTS cloud_fields (
    ts INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    value REAL,
    value_text TEXT,
    PRIMARY KEY (ts, device_id, path)
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect(path):
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def insert_wire_record(con, ts, param_id, vlen, value_bytes):
    import struct
    v32 = v64 = None
    try:
        if vlen == 4:
            v32 = struct.unpack("<i", value_bytes)[0]
        elif vlen == 8:
            v64 = struct.unpack("<q", value_bytes)[0]
    except struct.error:
        pass
    con.execute(
        "INSERT INTO wire_records(ts, param_id, vlen, value_i32, value_i64, value_bytes) VALUES (?,?,?,?,?,?)",
        (ts, param_id, vlen, v32, v64, value_bytes),
    )


def wire_records_between(con, t0, t1):
    cur = con.execute(
        "SELECT ts, param_id, vlen, value_i32, value_i64 FROM wire_records WHERE ts BETWEEN ? AND ? ORDER BY ts",
        (t0, t1),
    )
    for row in cur:
        yield row


def cloud_fields_between(con, t0, t1):
    cur = con.execute(
        "SELECT ts, path, value, value_text FROM cloud_fields WHERE ts BETWEEN ? AND ? ORDER BY ts",
        (t0, t1),
    )
    for row in cur:
        yield row
