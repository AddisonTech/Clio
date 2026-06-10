# Clio

A small, zero-infrastructure **time-series historian** for the OT stack. Bridges
(Hermes, ModBridge, Argus, …) POST readings; agents and dashboards query them
back. One SQLite file, a handful of endpoints, nothing else to stand up.

Named for Clio, the muse of history.

## Why

The bridges in this ecosystem each logged to their own CSV or per-app SQLite —
useful in isolation, but there was no shared place to ask "what was this tag
doing an hour ago?" across sources. Clio is that shared backbone, kept
deliberately tiny so it runs anywhere with no external database.

## Run

```bash
pip install -r requirements.txt
python -m clio              # serves on http://127.0.0.1:8010
```

Configure via env (see `config.example.env`): `CLIO_HOST`, `CLIO_PORT`, `CLIO_DB_PATH`.

## API

| Method | Path        | Purpose                                              |
|--------|-------------|------------------------------------------------------|
| GET    | `/health`   | Liveness + total reading count                       |
| POST   | `/readings` | Ingest one reading (object) or a batch (array)       |
| GET    | `/readings` | Query by `tag`, `source`, `since`, `until`, `limit`  |
| GET    | `/latest`   | Latest reading for a `tag`                            |
| GET    | `/tags`     | Distinct tags seen                                    |

A reading:

```json
{
  "source": "hermes",
  "tag": "ns=2;s=Temperature",
  "value": 42.5,
  "value_text": null,
  "quality": "good",
  "ts": "2026-06-10T14:00:00Z"
}
```

`ts` accepts ISO-8601 or epoch seconds and defaults to now. Use `value` for
numeric points and `value_text` for strings/booleans.

## Pushing from a bridge

```python
from clio.client import ClioClient

clio = ClioClient("http://localhost:8010")
clio.push("hermes", "ns=2;s=Temperature", value=42.5)
clio.push_many([
    {"source": "modbridge", "tag": "hr0", "value": 12.0},
    {"source": "modbridge", "tag": "hr1", "value": 13.5},
])
```

## Tests

```bash
pytest
```

## License

MIT © AddisonTech
