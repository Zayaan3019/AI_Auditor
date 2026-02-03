from __future__ import annotations

import uvicorn
from app.api.routes import app
from app.core.config import settings


def run() -> None:
    """Run the FastAPI application using Uvicorn."""
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()
