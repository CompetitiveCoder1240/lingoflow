"""
LingoFlow - LLM Service (Google Gemini)
Handles streaming completions via Google's official unified SDK (google-genai)
using the latest free-tier Gemini 3.8 Flash model.
Parses the dual-channel JSON response (voice_reply + pedagogical feedback).
"""

import json
import re
import logging
from typing import AsyncGenerator

from google import genai
from google.genai import types

from backend.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_OUTPUT_TOKENS,
)
from backend.prompts.tutor_prompts import build_system_prompt

logger = logging.getLogger(__name__)


class GeminiLLMService:
    """
    Manages conversation history and streams LLM completions from Google Gemini.

    Usage:
        llm = GeminiLLMService()
        async for chunk in llm.stream_response("Hello, how are you?"):
            print(chunk)  # Token-by-token streaming
        parsed = llm.parse_response(full_text)
    """

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com"
            )
        self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._contents: list[types.Content] = []
        self._system_prompt = build_system_prompt()

    def reset_conversation(self) -> None:
        """Clear conversation history for a fresh session."""
        self._contents.clear()
        logger.info("Conversation history cleared.")

    async def stream_response(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Send user text to Gemini and yield response tokens as they stream in.

        Args:
            user_text: The transcribed user speech.

        Yields:
            str: Text chunks from the Gemini stream.
        """
        # Append user turn to conversation history
        self._contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_text)],
            )
        )

        # Configure request with system instruction, low thinking level for low latency
        config = types.GenerateContentConfig(
            system_instruction=self._system_prompt,
            temperature=GEMINI_TEMPERATURE,
            max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.LOW
            ),
        )

        try:
            response_stream = await self._client.aio.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=self._contents,
                config=config,
            )

            full_response = ""
            async for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    yield chunk.text

            # Record model turn in conversation history
            self._contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=full_response)],
                )
            )

        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            error_response = json.dumps({
                "voice_reply": "I'm sorry, I had a brief issue connecting. Could you say that again?",
                "feedback": {
                    "has_corrections": False,
                    "corrections": [],
                    "natural_alternative": None,
                    "vocabulary_tip": None,
                },
            })
            self._contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=error_response)],
                )
            )
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
