"""
LingoFlow - Application Entrypoint (MVC)
Thin application factory setting up middleware, static assets, and router views.
"""

import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import HOST, PORT
from backend.views import router

# ── Logging Configuration ────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Application factory for LingoFlow."""
    application = FastAPI(
        title="LingoFlow",
        description="AI-Powered English Fluency Coach with Real-Time Voice Conversations (MVC Architecture)",
        version="0.2.0",
    )

    # Mount static assets for frontend view
    application.mount("/static", StaticFiles(directory="frontend"), name="static")

    # Register MVC Views and routes
    application.include_router(router)

    return application


app = create_app()


# ── Server Runner ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting LingoFlow server on http://{HOST}:{PORT}")
    uvicorn.run(
        "backend.app:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
    )
