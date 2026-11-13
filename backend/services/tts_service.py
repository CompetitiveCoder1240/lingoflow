"""
LingoFlow - Text-to-Speech Service (Edge-TTS)
Synthesizes text into natural-sounding audio using free Microsoft Neural Voices.
Supports sentence-level streaming for low-latency playback.
"""

import asyncio
import io
import logging
import re
from typing import AsyncGenerator

import edge_tts

from backend.config import (
    TTS_VOICE,
    TTS_RATE,
    TTS_VOLUME,
    SENTENCE_DELIMITERS,
    MIN_CHUNK_LENGTH,
)

logger = logging.getLogger(__name__)


class EdgeTTSService:
    """
    Synthesizes text to audio using Microsoft Edge-TTS neural voices.

    Usage:
        tts = EdgeTTSService()

        # Full synthesis
        audio_bytes = await tts.synthesize("Hello, how are you?")

        # Sentence-chunked streaming from LLM token stream
        async for audio_chunk in tts.stream_sentence_audio(token_generator):
            send_to_client(audio_chunk)
    """

    def __init__(self, voice: str = TTS_VOICE, rate: str = TTS_RATE, volume: str = TTS_VOLUME):
        self.voice = voice
        self.rate = rate
        self.volume = volume

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize a complete text string into MP3 audio bytes.

        Args:
            text: The text to convert to speech.

        Returns:
            bytes: MP3 audio data.
        """
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
        )

        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])

        audio_bytes = audio_buffer.getvalue()
        logger.debug(f"Synthesized {len(audio_bytes)} bytes of audio for: {text[:50]}...")
        return audio_bytes

    async def stream_sentence_audio(
        self, token_stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[tuple[str, bytes], None]:
        """
        Consume an LLM token stream, buffer tokens into sentence-level chunks,
        and yield (sentence_text, audio_bytes) tuples as soon as each sentence
        is complete. This enables sub-second time-to-first-audio.

        Args:
            token_stream: An async generator yielding text tokens from the LLM.

        Yields:
            tuple[str, bytes]: (sentence_text, mp3_audio_bytes) for each clause.
        """
        buffer = ""
        delimiter_pattern = re.compile(SENTENCE_DELIMITERS)

        async for token in token_stream:
            buffer += token

            # Check if buffer contains a sentence boundary
            match = delimiter_pattern.search(buffer)
            if match and len(buffer.strip()) >= MIN_CHUNK_LENGTH:
                # Split at the delimiter
                split_pos = match.end()
                sentence = buffer[:split_pos].strip()
                buffer = buffer[split_pos:].strip()

                if sentence:
                    # Synthesize this sentence immediately
                    try:
                        audio = await self.synthesize(sentence)
                        yield sentence, audio
                    except Exception as e:
                        logger.error(f"TTS synthesis error for '{sentence[:30]}...': {e}")
                        continue

        # Flush any remaining text in the buffer
        remaining = buffer.strip()
        if remaining:
            try:
                audio = await self.synthesize(remaining)
                yield remaining, audio
            except Exception as e:
                logger.error(f"TTS synthesis error for remaining text: {e}")

    def set_voice(self, voice_key: str, voices_map: dict) -> bool:
        """
        Switch the active TTS voice.

        Args:
            voice_key: Key to look up in the voices map (e.g., 'jenny', 'guy').
            voices_map: Dict mapping voice keys to Edge-TTS voice names.

        Returns:
            True if voice was switched, False if key not found.
        """
        if voice_key in voices_map:
            self.voice = voices_map[voice_key]
            logger.info(f"TTS voice changed to: {self.voice}")
            return True
        logger.warning(f"Unknown voice key: {voice_key}")
        return False
