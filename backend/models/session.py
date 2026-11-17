"""
LingoFlow - Session Model (MVC: Model)
Encapsulates runtime state, transcript buffers, and cancellation events for a conversation.
"""

import asyncio
import uuid
import logging
from typing import Optional

from backend.config import DEFAULT_COACHING_MODE, TTS_VOICE

logger = logging.getLogger(__name__)


class ConversationSession:
    """
    Manages active session state for a real-time voice conversation.
    Handles barge-in cancellation events, transcript aggregation, and state transitions.
    """

    def __init__(self, mode: str = DEFAULT_COACHING_MODE, voice: str = TTS_VOICE):
        self.session_id: str = str(uuid.uuid4())
        self.state: str = "idle"  # idle | listening | thinking | speaking
        self.coaching_mode: str = mode
        self.voice_key: str = "jenny"
        self._is_cancelled: asyncio.Event = asyncio.Event()
        self._transcript_buffer: str = ""

    @property
    def is_cancelled(self) -> asyncio.Event:
        """Cancellation event for mid-sentence barge-in."""
        return self._is_cancelled

    def cancel(self) -> None:
        """Trigger cancellation (barge-in interruption)."""
        self._is_cancelled.set()
        logger.debug(f"[Session {self.session_id[:8]}] Cancelled active generation.")

    def clear_cancel(self) -> None:
        """Reset cancellation flag before a new turn."""
        self._is_cancelled.clear()

    def append_transcript(self, text: str) -> None:
        """Append finalized transcript segment to buffer."""
        self._transcript_buffer += (" " if self._transcript_buffer else "") + text.strip()

    def consume_transcript(self) -> str:
        """Retrieve full buffered user transcript and clear the buffer."""
        text = self._transcript_buffer.strip()
        self._transcript_buffer = ""
        return text

    def set_state(self, new_state: str) -> None:
        """Update session state."""
        self.state = new_state

    def reset(self) -> None:
        """Reset state and clear buffers."""
        self._transcript_buffer = ""
        self._is_cancelled.clear()
        self.state = "idle"
        logger.debug(f"[Session {self.session_id[:8]}] Session state reset.")
