"""
LingoFlow - Routes & Presentation Layer (MVC: View)
Defines HTTP and WebSocket routes, delegating requests directly to Controllers.
"""

from fastapi import APIRouter, WebSocket
from fastapi.responses import FileResponse

from backend.controllers.http_controller import HttpController
from backend.controllers.conversation_controller import ConversationController
from backend.models.schemas import HealthResponse

router = APIRouter()


# ── HTTP Views ───────────────────────────────────────────────

@router.get("/", response_class=FileResponse, summary="Serve the Single-Page Voice UI")
async def serve_index():
    """Renders the main conversational client interface."""
    return await HttpController.serve_index()


@router.get("/health", response_model=HealthResponse, summary="System Health & Model Status")
async def health_check():
    """Health check endpoint reporting API and active model status."""
    return await HttpController.get_health()


@router.get("/api/voices", summary="List Available Neural Voices")
async def list_voices():
    """Returns available Microsoft Edge-TTS neural voices and accents."""
    return await HttpController.get_voices()


# ── WebSocket View ───────────────────────────────────────────

@router.websocket("/ws/conversation")
async def conversation_ws(websocket: WebSocket):
    """
    Real-time bidirectional voice conversation WebSocket endpoint.
    Delegates all protocol handling to ConversationController.
    """
    controller = ConversationController(websocket)
    await controller.run()
