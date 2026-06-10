"""
clio/app.py
Clio — a small SQLite historian for the OT stack.

Bridges (Hermes, ModBridge, Argus, ...) POST readings here; agents and
dashboards query them back. Intentionally tiny: one table, a handful of
endpoints, zero external services to stand up.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import List, Optional, Union

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from clio.db import Historian

DB_PATH = os.environ.get("CLIO_DB_PATH", "clio.db")
historian = Historian(DB_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await historian.init()
    yield


app = FastAPI(title="Clio Historian", version="0.1.0", lifespan=lifespan)


class Reading(BaseModel):
    source: str = Field(..., description="Originating bridge/service, e.g. 'hermes'")
    tag: str = Field(..., description="Point identifier (OPC-UA node, Modbus register, ...)")
    value: Optional[float] = Field(None, description="Numeric value, if applicable")
    value_text: Optional[str] = Field(None, description="String/boolean value, if not numeric")
    quality: str = Field("good", description="Reading quality, e.g. 'good' | 'bad'")
    ts: Optional[str] = Field(None, description="ISO-8601 or epoch seconds; defaults to now")


@app.get("/health")
async def health():
    return {"status": "ok", "db": DB_PATH, "readings": await historian.count()}


@app.post("/readings")
async def ingest(payload: Union[Reading, List[Reading]]):
    """Ingest one reading or a batch (JSON object or array)."""
    items = payload if isinstance(payload, list) else [payload]
    if not items:
        raise HTTPException(status_code=400, detail="no readings provided")
    n = await historian.insert_many([r.model_dump() for r in items])
    return {"ingested": n}


@app.get("/readings")
async def get_readings(
    tag: Optional[str] = None,
    source: Optional[str] = None,
    since: Optional[str] = Query(None, description="ISO-8601 or epoch; lower bound"),
    until: Optional[str] = Query(None, description="ISO-8601 or epoch; upper bound"),
    limit: int = Query(500, ge=1, le=10000),
):
    rows = await historian.query(tag=tag, source=source, since=since, until=until, limit=limit)
    return {"count": len(rows), "readings": rows}


@app.get("/latest")
async def get_latest(tag: str):
    row = await historian.latest(tag)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no readings for tag '{tag}'")
    return row


@app.get("/tags")
async def get_tags():
    return {"tags": await historian.tags()}
