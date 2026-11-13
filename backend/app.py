"""
LingoFlow - Main Application Server
FastAPI backend with WebSocket endpoint for real-time voice conversation.

Architecture:
  Client Mic → WebSocket → Deepgram STT → Google Gemini 3.8 Flash (streaming) →
  Edge-TTS (sentence-chunked) → WebSocket → Client Speaker
"""

import asyncio
import base64
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import HOST, PORT, AVAILABLE_VOICES
from backend.services.stt_service import DeepgramSTTService
from backend.services.llm_service import GeminiLLMService
from backend.services.tts_service import EdgeTTSService

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title="LingoFlow",
    description="AI-Powered English Fluency Coach with Real-Time Voice Conversations",
    version="0.1.0",
)

# Serve frontend static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def serve_index():
    """Serve the main voice interface."""
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "LingoFlow", "llm": "Gemini 3.8 Flash"}


# ── WebSocket Conversation Endpoint ─────────────────────────

@app.websocket("/ws/conversation")
async def conversation_ws(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time voice conversation.

    Protocol (Client → Server):
        - Binary frames: Raw PCM audio data from the microphone.
        - JSON text frames:
            {"type": "control", "action": "start"}  - Begin listening
            {"type": "control", "action": "stop"}   - Stop listening
            {"type": "control", "action": "cancel"}  - Cancel current AI response (barge-in)
            {"type": "control", "action": "reset"}   - Reset conversation history
            {"type": "config", "voice": "jenny"}     - Change TTS voice

    Protocol (Server → Client):
        - JSON text frames:
            {"type": "transcript", "text": "...", "is_final": bool}
            {"type": "state", "state": "listening|thinking|speaking|idle"}
            {"type": "ai_text", "text": "..."}       - Sentence being spoken
            {"type": "feedback", ...}                 - Pedagogical corrections
            {"type": "error", "message": "..."}
        - Binary frames: MP3 audio chunks for playback.
    """
    await websocket.accept()
    logger.info("Client connected to conversation WebSocket.")

    # Initialize services
    llm_service = GeminiLLMService()
    tts_service = EdgeTTSService()

    # State
    is_cancelled = asyncio.Event()
    final_transcript_buffer = ""

    # ── Callback: Deepgram transcript received ───────────
    async def on_transcript(text: str, is_final: bool):
        nonlocal final_transcript_buffer
        try:
            await websocket.send_text(json.dumps({
                "type": "transcript",
                "text": text,
                "is_final": is_final,
            }))
            if is_final:
                final_transcript_buffer += " " + text
        except Exception:
            pass

    # ── Callback: Deepgram utterance end ─────────────────
    async def on_utterance_end():
        nonlocal final_transcript_buffer
        user_text = final_transcript_buffer.strip()
        final_transcript_buffer = ""

        if not user_text:
            return

        logger.info(f"User said: {user_text}")
        is_cancelled.clear()

        try:
            # Signal: AI is thinking
            await websocket.send_text(json.dumps({
                "type": "state", "state": "thinking",
            }))

            # Stream LLM response and pipe through sentence-chunked TTS
            full_response = ""

            async def token_generator():
                nonlocal full_response
                async for token in llm_service.stream_response(user_text):
                    if is_cancelled.is_set():
                        return
                    full_response += token
                    yield token

            # Signal: AI is speaking
            await websocket.send_text(json.dumps({
                "type": "state", "state": "speaking",
            }))

            async for sentence_text, audio_bytes in tts_service.stream_sentence_audio(
                token_generator()
            ):
                if is_cancelled.is_set():
                    logger.info("Response cancelled by user (barge-in).")
                    break

                # Send the sentence text for display
                await websocket.send_text(json.dumps({
                    "type": "ai_text",
                    "text": sentence_text,
                }))

                # Send the audio as a binary frame
                await websocket.send_bytes(audio_bytes)

            # Parse full response for pedagogical feedback
            if not is_cancelled.is_set() and full_response:
                parsed = llm_service.parse_response(full_response)
                feedback = parsed.get("feedback", {})
                if feedback:
                    await websocket.send_text(json.dumps({
                        "type": "feedback",
                        **feedback,
                    }))

            # Signal: back to idle
            await websocket.send_text(json.dumps({
                "type": "state", "state": "idle",
            }))

        except Exception as e:
            logger.error(f"Error in conversation pipeline: {e}")
            await websocket.send_text(json.dumps({
                "type": "error", "message": str(e),
            }))

    # ── Initialize Deepgram STT ──────────────────────────
    stt_service = DeepgramSTTService(
        on_transcript=on_transcript,
        on_utterance_end=on_utterance_end,
    )

    try:
        await stt_service.start()

        # Signal ready
        await websocket.send_text(json.dumps({
            "type": "state", "state": "idle",
        }))

        # ── Main message loop ────────────────────────────
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                # Binary frame: raw audio from microphone
                await stt_service.send_audio(message["bytes"])

            elif "text" in message:
                data = json.loads(message["text"])
                msg_type = data.get("type")

                if msg_type == "control":
                    action = data.get("action")
                    if action == "cancel":
                        is_cancelled.set()
                        logger.info("Barge-in: cancelling current response.")
                    elif action == "reset":
                        llm_service.reset_conversation()
                        await websocket.send_text(json.dumps({
                            "type": "state", "state": "idle",
                        }))
                        logger.info("Conversation reset.")

                elif msg_type == "config":
                    voice_key = data.get("voice")
                    if voice_key:
                        tts_service.set_voice(voice_key, AVAILABLE_VOICES)

    except WebSocketDisconnect:
        logger.info("Client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await stt_service.stop()
        logger.info("Session cleaned up.")


# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
    )
