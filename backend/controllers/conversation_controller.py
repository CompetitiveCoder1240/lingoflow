"""
LingoFlow - Conversation Controller (MVC: Controller)
Orchestrates the bidirectional real-time voice pipeline over WebSockets:
  Microphone Audio -> Deepgram STT -> Gemini LLM -> Edge-TTS -> Speaker
"""

import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.config import AVAILABLE_VOICES, DEFAULT_COACHING_MODE
from backend.models.session import ConversationSession
from backend.models.schemas import (
    StateEvent,
    TranscriptEvent,
    AITextEvent,
    FeedbackEvent,
    ModeUpdatedEvent,
    ErrorEvent,
    CorrectionItem,
)
from backend.services.stt_service import DeepgramSTTService
from backend.services.llm_service import GeminiLLMService
from backend.services.tts_service import EdgeTTSService

logger = logging.getLogger(__name__)


class ConversationController:
    """
    Controller responsible for a single WebSocket conversation session.
    Binds the ConversationSession (Model) to STT, LLM, and TTS Services.
    """

    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.session = ConversationSession(mode=DEFAULT_COACHING_MODE)
        self.llm_service = GeminiLLMService(coaching_mode=self.session.coaching_mode)
        self.tts_service = EdgeTTSService()
        self.stt_service: Optional[DeepgramSTTService] = None

    async def run(self) -> None:
        """Lifecycle manager for the WebSocket conversation connection."""
        await self.ws.accept()
        logger.info(f"[Session {self.session.session_id[:8]}] Client connected.")

        # Initialize Deepgram STT with callback hooks
        self.stt_service = DeepgramSTTService(
            on_transcript=self.on_transcript,
            on_utterance_end=self.on_utterance_end,
        )

        try:
            await self.stt_service.start()

            # Signal ready to client with initial state and mode
            await self.send_event(StateEvent(state="idle", mode=self.session.coaching_mode))

            # Main WebSocket event loop
            while True:
                message = await self.ws.receive()

                if "bytes" in message:
                    # Binary frame: PCM audio from client mic
                    await self.stt_service.send_audio(message["bytes"])

                elif "text" in message:
                    # Text frame: JSON control or configuration action
                    await self.handle_client_text(message["text"])

        except WebSocketDisconnect:
            logger.info(f"[Session {self.session.session_id[:8]}] Client disconnected cleanly.")
        except Exception as e:
            logger.error(f"[Session {self.session.session_id[:8]}] WebSocket error: {e}", exc_info=True)
            try:
                await self.send_event(ErrorEvent(message=str(e)))
            except Exception:
                pass
        finally:
            if self.stt_service:
                await self.stt_service.stop()
            logger.info(f"[Session {self.session.session_id[:8]}] Cleaned up session.")

    # ── STT Callbacks ────────────────────────────────────────

    async def on_transcript(self, text: str, is_final: bool) -> None:
        """Invoked when Deepgram yields interim or final transcription."""
        await self.send_event(TranscriptEvent(text=text, is_final=is_final))
        if is_final:
            self.session.append_transcript(text)

    async def on_utterance_end(self) -> None:
        """Invoked when speaker finishes an utterance (VAD endpointing triggered)."""
        user_text = self.session.consume_transcript()
        if not user_text:
            return

        logger.info(f"[Session {self.session.session_id[:8]}] User said: '{user_text}'")
        self.session.clear_cancel()

        try:
            # 1. Transition to 'thinking' state
            self.session.set_state("thinking")
            await self.send_event(StateEvent(state="thinking"))

            # 2. Query LLM (streaming)
            full_response = ""
            async for token in self.llm_service.stream_response(user_text):
                if self.session.is_cancelled.is_set():
                    logger.info("Turn cancelled during LLM stream (barge-in).")
                    break
                full_response += token

            if self.session.is_cancelled.is_set():
                self.session.set_state("idle")
                await self.send_event(StateEvent(state="idle"))
                return

            # 3. Parse dual-channel output
            parsed = self.llm_service.parse_response(full_response)
            voice_reply = parsed.get("voice_reply", "").strip()
            feedback = parsed.get("feedback", {})

            if not voice_reply:
                self.session.set_state("idle")
                await self.send_event(StateEvent(state="idle"))
                return

            # 4. Transition to 'speaking' state
            self.session.set_state("speaking")
            await self.send_event(StateEvent(state="speaking"))

            # 5. Synthesize voice_reply via sentence-chunked streaming
            async def voice_reply_generator():
                yield voice_reply

            async for sentence_text, audio_bytes in self.tts_service.stream_sentence_audio(
                voice_reply_generator()
            ):
                if self.session.is_cancelled.is_set():
                    logger.info("Playback cancelled during TTS stream (barge-in).")
                    break

                # Send sentence caption
                await self.send_event(AITextEvent(text=sentence_text))

                # Send binary audio chunk
                await self.ws.send_bytes(audio_bytes)

            # 6. Deliver pedagogical feedback to companion UI
            if not self.session.is_cancelled.is_set() and feedback:
                corrections = [
                    CorrectionItem(**c) if isinstance(c, dict) else c
                    for c in feedback.get("corrections", [])
                ]
                await self.send_event(
                    FeedbackEvent(
                        has_corrections=feedback.get("has_corrections", False),
                        corrections=corrections,
                        natural_alternative=feedback.get("natural_alternative"),
                        vocabulary_tip=feedback.get("vocabulary_tip"),
                    )
                )

            # 7. Return to 'idle' state
            self.session.set_state("idle")
            await self.send_event(StateEvent(state="idle"))

        except Exception as e:
            logger.error(f"Error in conversation pipeline turn: {e}", exc_info=True)
            self.session.set_state("idle")
            await self.send_event(ErrorEvent(message=f"Pipeline error: {str(e)}"))
            await self.send_event(StateEvent(state="idle"))

    # ── Client Message Handling ──────────────────────────────

    async def handle_client_text(self, text_payload: str) -> None:
        """Parse and route JSON control/configuration commands from the client."""
        try:
            data = json.loads(text_payload)
            msg_type = data.get("type")

            if msg_type == "control":
                action = data.get("action")
                if action == "cancel":
                    self.session.cancel()
                    logger.info(f"[Session {self.session.session_id[:8]}] Barge-in cancel requested.")
                elif action == "reset":
                    self.session.reset()
                    self.llm_service.reset_conversation()
                    await self.send_event(StateEvent(state="idle", mode=self.session.coaching_mode))
                    logger.info(f"[Session {self.session.session_id[:8]}] Conversation reset.")

            elif msg_type == "config":
                # Voice configuration
                voice_key = data.get("voice")
                if voice_key:
                    self.tts_service.set_voice(voice_key, AVAILABLE_VOICES)
                    self.session.voice_key = voice_key

                # Coaching mode configuration
                mode = data.get("mode")
                if mode:
                    self.session.coaching_mode = mode
                    self.llm_service.set_coaching_mode(mode)
                    await self.send_event(ModeUpdatedEvent(mode=mode))
                    logger.info(f"[Session {self.session.session_id[:8]}] Coaching mode switched to '{mode}'.")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received from client: {text_payload[:100]}")

    # ── Helpers ──────────────────────────────────────────────

    async def send_event(self, event: BaseModel) -> None:
        """Safely serialize and transmit a Pydantic event to the WebSocket."""
        try:
            await self.ws.send_text(event.model_dump_json())
        except Exception as e:
            logger.debug(f"Failed to send event {event.type}: {e}")
