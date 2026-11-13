"""
LingoFlow - Speech-to-Text Service (Deepgram)
Handles real-time streaming transcription using Deepgram Nova-2.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Callable, Optional

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

from backend.config import (
    DEEPGRAM_API_KEY,
    DEEPGRAM_MODEL,
    DEEPGRAM_LANGUAGE,
    DEEPGRAM_ENCODING,
    DEEPGRAM_SAMPLE_RATE,
    DEEPGRAM_CHANNELS,
)

logger = logging.getLogger(__name__)


class DeepgramSTTService:
    """
    Manages a real-time Deepgram WebSocket connection for live
    speech-to-text transcription.

    Usage:
        stt = DeepgramSTTService(on_transcript=callback, on_utterance_end=callback)
        await stt.start()
        await stt.send_audio(audio_bytes)
        await stt.stop()
    """

    def __init__(
        self,
        on_transcript: Optional[Callable] = None,
        on_utterance_end: Optional[Callable] = None,
    ):
        """
        Args:
            on_transcript: Async callback(text: str, is_final: bool) called
                           for each transcript result.
            on_utterance_end: Async callback() called when Deepgram detects
                              the speaker has finished an utterance.
        """
        self._on_transcript = on_transcript
        self._on_utterance_end = on_utterance_end
        self._connection = None
        self._client = None

    async def start(self) -> None:
        """Open a live transcription WebSocket to Deepgram."""
        if not DEEPGRAM_API_KEY:
            raise ValueError(
                "DEEPGRAM_API_KEY is not set. "
                "Get a free key at https://console.deepgram.com/signup"
            )

        config = DeepgramClientOptions(options={"keepalive": "true"})
        self._client = DeepgramClient(DEEPGRAM_API_KEY, config)
        self._connection = self._client.listen.asyncwebsocket.v("1")

        # Register event handlers
        self._connection.on(
            LiveTranscriptionEvents.Transcript, self._handle_transcript
        )
        self._connection.on(
            LiveTranscriptionEvents.UtteranceEnd, self._handle_utterance_end
        )
        self._connection.on(
            LiveTranscriptionEvents.Error, self._handle_error
        )

        options = LiveOptions(
            model=DEEPGRAM_MODEL,
            language=DEEPGRAM_LANGUAGE,
            encoding=DEEPGRAM_ENCODING,
            sample_rate=DEEPGRAM_SAMPLE_RATE,
            channels=DEEPGRAM_CHANNELS,
            punctuate=True,
            interim_results=True,
            utterance_end_ms=600,       # Detect end-of-speech after 600ms silence
            vad_events=True,
            smart_format=True,
        )

        started = await self._connection.start(options)
        if started:
            logger.info("Deepgram live transcription started.")
        else:
            raise ConnectionError("Failed to start Deepgram connection.")

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send raw audio bytes to the Deepgram WebSocket."""
        if self._connection:
            await self._connection.send(audio_bytes)

    async def stop(self) -> None:
        """Gracefully close the Deepgram connection."""
        if self._connection:
            await self._connection.finish()
            logger.info("Deepgram connection closed.")
        self._connection = None

    # ── Internal Event Handlers ──────────────────────────────

    async def _handle_transcript(self, _conn, result, **kwargs) -> None:
        """Process incoming transcript results from Deepgram."""
        try:
            transcript = result.channel.alternatives[0].transcript
            if not transcript:
                return

            is_final = result.is_final
            logger.debug(
                f"Transcript ({'final' if is_final else 'interim'}): {transcript}"
            )

            if self._on_transcript:
                await self._on_transcript(transcript, is_final)
        except (IndexError, AttributeError) as e:
            logger.warning(f"Error parsing transcript: {e}")

    async def _handle_utterance_end(self, _conn, result, **kwargs) -> None:
        """Called when Deepgram detects the speaker has stopped talking."""
        logger.debug("Utterance end detected.")
        if self._on_utterance_end:
            await self._on_utterance_end()

    async def _handle_error(self, _conn, error, **kwargs) -> None:
        """Log Deepgram errors."""
        logger.error(f"Deepgram error: {error}")
