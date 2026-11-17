"""
LingoFlow - HTTP Controller (MVC: Controller)
Handles standard HTTP endpoints, page delivery, and health diagnostics.
"""

import logging
from fastapi.responses import FileResponse

from backend.config import AVAILABLE_VOICES, GEMINI_MODEL
from backend.models.schemas import HealthResponse

logger = logging.getLogger(__name__)


class HttpController:
    """Controller handling HTTP endpoints for UI serving and system health."""

    @staticmethod
    async def serve_index() -> FileResponse:
        """Serve the main single-page voice interface."""
        return FileResponse("frontend/index.html")

    @staticmethod
    async def get_health() -> HealthResponse:
        """Diagnostic health check endpoint."""
        return HealthResponse(
            status="ok",
            service="LingoFlow",
            llm=f"Google Gemini ({GEMINI_MODEL})",
        )

    @staticmethod
    async def get_voices() -> dict:
        """Return available neural voices."""
        return {"voices": AVAILABLE_VOICES}
