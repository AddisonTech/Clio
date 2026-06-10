"""
clio/db.py
SQLite-backed time-series store for industrial readings.

One table, ``readings``, indexed by (tag, ts) for fast range queries. Timestamps
are stored as UTC epoch seconds (REAL) for efficient ordering and returned as
ISO-8601 strings by the API layer. aiosqlite keeps every call non-blocking, the
same pattern Argus and Mnemosyne use elsewhere in the stack.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT NOT NULL,
    tag        TEXT NOT NULL,
    value      REAL,
    value_text TEXT,
    quality    TEXT NOT NULL DEFAULT 'good',
    ts         REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_readings_tag_ts ON readings (tag, ts);
CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings (ts);
"""


def utcnow_epoch() -> float:
    return datetime.now(timezone.utc).timestamp()


def to_iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def parse_ts(value: Any) -> float:
    """Accept epoch seconds (int/float) or an ISO-8601 string; return epoch float.

    ``None`` means 'now'. This lets bridges send whichever format is convenient.
    """
    if value is None or value == "":
        return utcnow_epoch()
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


class Historian:
    """Async accessor for the readings store."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self) -> None:
        parent = Path(self.db_path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()

    async def insert_many(self, rows: list[dict]) -> int:
        prepared = [
            (
                r["source"],
                r["tag"],
                r.get("value"),
                r.get("value_text"),
                r.get("quality") or "good",
                parse_ts(r.get("ts")),
            )
            for r in rows
        ]
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                "INSERT INTO readings (source, tag, value, value_text, quality, ts) "
                "VALUES (?,?,?,?,?,?)",
                prepared,
            )
            await db.commit()
        return len(prepared)

    async def query(
        self,
        tag: Optional[str] = None,
        source: Optional[str] = None,
        since: Any = None,
        until: Any = None,
        limit: int = 500,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[Any] = []
        if tag:
            clauses.append("tag = ?")
            params.append(tag)
        if source:
            clauses.append("source = ?")
            params.append(source)
        if since is not None:
            clauses.append("ts >= ?")
            params.append(parse_ts(since))
        if until is not None:
            clauses.append("ts <= ?")
            params.append(parse_ts(until))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            f"SELECT source, tag, value, value_text, quality, ts FROM readings "
            f"{where} ORDER BY ts DESC LIMIT ?"
        )
        params.append(int(limit))
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(sql, params)
            rows = await cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

    async def latest(self, tag: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT source, tag, value, value_text, quality, ts FROM readings "
                "WHERE tag = ? ORDER BY ts DESC LIMIT 1",
                (tag,),
            )
            row = await cur.fetchone()
        return self._row_to_dict(row) if row else None

    async def tags(self) -> list[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT DISTINCT tag FROM readings ORDER BY tag")
            rows = await cur.fetchall()
        return [r[0] for r in rows]

    async def count(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM readings")
            row = await cur.fetchone()
        return int(row[0]) if row else 0

    @staticmethod
    def _row_to_dict(r: aiosqlite.Row) -> dict:
        return {
            "source": r["source"],
            "tag": r["tag"],
            "value": r["value"],
            "value_text": r["value_text"],
            "quality": r["quality"],
            "ts": to_iso(r["ts"]),
        }
