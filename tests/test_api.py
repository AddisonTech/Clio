"""
tests/test_api.py
End-to-end tests for the Clio historian over an isolated temp database.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    import clio.app as appmod
    from clio.db import Historian

    # Point the app at a throwaway DB before the lifespan initializes it.
    appmod.historian = Historian(str(tmp_path / "test.db"))
    with TestClient(appmod.app) as c:
        yield c


def test_health_empty(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["readings"] == 0


def test_ingest_single_then_latest_and_query(client):
    r = client.post("/readings", json={"source": "hermes", "tag": "ns=2;s=Temp", "value": 42.5})
    assert r.status_code == 200
    assert r.json()["ingested"] == 1

    r = client.get("/latest", params={"tag": "ns=2;s=Temp"})
    assert r.status_code == 200
    assert r.json()["value"] == 42.5
    assert r.json()["source"] == "hermes"

    r = client.get("/readings", params={"tag": "ns=2;s=Temp"})
    assert r.status_code == 200
    assert r.json()["count"] == 1

    r = client.get("/tags")
    assert "ns=2;s=Temp" in r.json()["tags"]


def test_ingest_batch(client):
    rows = [{"source": "modbridge", "tag": "hr0", "value": float(i)} for i in range(5)]
    r = client.post("/readings", json=rows)
    assert r.status_code == 200
    assert r.json()["ingested"] == 5

    r = client.get("/readings", params={"tag": "hr0", "limit": 10})
    assert r.json()["count"] == 5


def test_value_text_and_quality(client):
    r = client.post(
        "/readings",
        json={"source": "hermes", "tag": "ns=2;s=Mode", "value_text": "AUTO", "quality": "good"},
    )
    assert r.json()["ingested"] == 1
    row = client.get("/latest", params={"tag": "ns=2;s=Mode"}).json()
    assert row["value_text"] == "AUTO"
    assert row["value"] is None


def test_latest_404_for_unknown_tag(client):
    r = client.get("/latest", params={"tag": "does-not-exist"})
    assert r.status_code == 404
