"""
clio/client.py
Tiny client for pushing readings to a Clio historian from other services
(Hermes, ModBridge, Argus, ...). Dependency-light: just httpx.

    from clio.client import ClioClient
    clio = ClioClient("http://localhost:8010")
    clio.push("hermes", "ns=2;s=Temperature", value=42.5)
"""
from __future__ import annotations

from typing import Any, Optional

import httpx


class ClioClient:
    def __init__(self, base_url: str = "http://localhost:8010", timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def push(
        self,
        source: str,
        tag: str,
        value: Optional[float] = None,
        value_text: Optional[str] = None,
        quality: str = "good",
        ts: Optional[str] = None,
    ) -> dict[str, Any]:
        payload = {
            "source": source,
            "tag": tag,
            "value": value,
            "value_text": value_text,
            "quality": quality,
            "ts": ts,
        }
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(f"{self.base_url}/readings", json=payload)
            r.raise_for_status()
            return r.json()

    def push_many(self, rows: list[dict]) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(f"{self.base_url}/readings", json=rows)
            r.raise_for_status()
            return r.json()

    def latest(self, tag: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.get(f"{self.base_url}/latest", params={"tag": tag})
            r.raise_for_status()
            return r.json()
