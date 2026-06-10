"""Run the Clio historian: ``python -m clio`` (serves on CLIO_PORT, default 8010)."""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "clio.app:app",
        host=os.environ.get("CLIO_HOST", "127.0.0.1"),
        port=int(os.environ.get("CLIO_PORT", "8010")),
        reload=False,
    )
