"""SQLite storage. One file: data/orbflow.db"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "orbflow.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    item_id      INTEGER PRIMARY KEY,   -- poe2scout ItemId (used by history endpoint)
    api_id       TEXT UNIQUE,
    name         TEXT,
    category     TEXT
);
-- hourly price log per item, price expressed in exalted orbs
CREATE TABLE IF NOT EXISTS price_history (
    league   TEXT,
    item_id  INTEGER,
    ts       TEXT,          -- ISO UTC, hour bucket
    price_ex REAL,
    quantity INTEGER,
    PRIMARY KEY (league, item_id, ts)
);
-- raw per-pair data from each hourly exchange snapshot we collect ourselves
CREATE TABLE IF NOT EXISTS pair_snapshots (
    league        TEXT,
    snapshot_id   INTEGER,
    fetched_at    TEXT,
    one_api       TEXT,
    two_api       TEXT,
    volume_ex     REAL,
    one_rel_price REAL, one_value_traded REAL, one_volume INTEGER, one_stock_value REAL, one_highest_stock INTEGER,
    two_rel_price REAL, two_value_traded REAL, two_volume INTEGER, two_stock_value REAL, two_highest_stock INTEGER,
    PRIMARY KEY (league, snapshot_id, one_api, two_api)
);
-- every piece of advice we give is journaled here and graded later
CREATE TABLE IF NOT EXISTS recommendations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT,      -- wall clock when produced
    as_of        TEXT,      -- data cut-off the advice was based on
    league       TEXT,
    strategy     TEXT,
    api_id       TEXT,
    action       TEXT,      -- e.g. BUY_THEN_SELL
    entry_price  REAL,      -- ex
    target_price REAL,      -- ex
    horizon_h    INTEGER,
    score        REAL,
    rationale    TEXT,
    -- filled by evaluation
    evaluated_at TEXT,
    exit_price   REAL,
    realized_pct REAL,
    hit          INTEGER
);
"""


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con
