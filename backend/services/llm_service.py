"""
LingoFlow - LLM Service (Groq)
Handles streaming chat completions via Groq's ultra-fast inference.
Parses the dual-channel JSON response (voice_reply + pedagogical feedback).
"""

import json
import re
import logging
from typing import AsyncGenerator, Optional

from groq import AsyncGroq

from backend.config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, GROQ_TEMPERATURE
from backend.prompts.tutor_prompts import build_system_prompt

logger = logging.getLogger(__name__)


class GroqLLMService:
    """
    Manages conversation history and streams LLM completions from Groq.

    Usage:
        llm = GroqLLMService()
        async for chunk in llm.stream_response("Hello, how are you?"):
            print(chunk)  # Token-by-token streaming
        parsed = llm.parse_response(full_text)
    """

    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com/keys"
            )
        self._client = AsyncGroq(api_key=GROQ_API_KEY)
        self._conversation_history: list[dict] = []
        self._system_prompt = build_system_prompt()

    def reset_conversation(self) -> None:
        """Clear conversation history for a fresh session."""
        self._conversation_history.clear()
        logger.info("Conversation history cleared.")

    async def stream_response(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Send user text to Groq and yield response tokens as they stream in.

        Args:
            user_text: The transcribed user speech.

        Yields:
            str: Individual text tokens from the LLM stream.
        """
        # Add user message to history
        self._conversation_history.append({
            "role": "user",
            "content": user_text,
        })

        messages = [
            {"role": "system", "content": self._system_prompt},
            *self._conversation_history,
        ]

        try:
            stream = await self._client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=GROQ_MAX_TOKENS,
                temperature=GROQ_TEMPERATURE,
                stream=True,
            )

            full_response = ""
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response += delta.content
                    yield delta.content

            # Add assistant response to history
            self._conversation_history.append({
                "role": "assistant",
                "content": full_response,
            })

        except Exception as e:
            logger.error(f"Groq streaming error: {e}")
            error_response = json.dumps({
                "voice_reply": "I'm sorry, I had a little hiccup. Could you say that again?",
                "feedback": {"has_corrections": False, "corrections": []},
            })
            self._conversation_history.append({
                "role": "assistant",
                "content": error_response,
            })
            yield error_response

    @staticmethod
    def parse_response(full_text: str) -> dict:
        """
        Parse the LLM's JSON response into structured voice_reply and feedback.

        Args:
            full_text: The complete LLM response string.

        Returns:
            dict with 'voice_reply' (str) and 'feedback' (dict).
        """
        try:
            # Try direct JSON parse first
            data = json.loads(full_text)
            return data
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code fences or surrounding text
        json_match = re.search(r'\{[\s\S]*\}', full_text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data
            except json.JSONDecodeError:
                pass

        # Fallback: treat entire text as voice reply with no corrections
        logger.warning("Could not parse LLM response as JSON. Using raw text.")
        return {
            "voice_reply": full_text.strip(),
            "feedback": {
                "has_corrections": False,
                "corrections": [],
                "natural_alternative": None,
                "vocabulary_tip": None,
            },
        }
