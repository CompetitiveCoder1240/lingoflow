"""
LingoFlow - LLM Service (Google Gemini)
Handles streaming completions via Google's official unified SDK (google-genai).
Tries gemini-3.8-flash first, falls back to gemini-3.5-flash-lite if unavailable.
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
    GEMINI_FALLBACK_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_OUTPUT_TOKENS,
    DEFAULT_COACHING_MODE,
)
from backend.prompts.tutor_prompts import build_system_prompt

logger = logging.getLogger(__name__)

# Models that support the ThinkingConfig parameter
_THINKING_SUPPORTED_MODELS = {"gemini-3.8-flash", "gemini-3.5-flash"}


class GeminiLLMService:
    """
    Manages conversation history and streams LLM completions from Google Gemini.
    Automatically falls back to a lighter model if the primary model is unavailable.

    Usage:
        llm = GeminiLLMService()
        async for chunk in llm.stream_response("Hello, how are you?"):
            print(chunk)
        parsed = llm.parse_response(full_text)
    """

    def __init__(self, coaching_mode: str = DEFAULT_COACHING_MODE):
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com"
            )
        self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._contents: list[types.Content] = []
        self._coaching_mode = coaching_mode
        self._system_prompt = build_system_prompt(mode=coaching_mode)
        self._active_model = GEMINI_MODEL
        self._failed_models: set[str] = set()

    def set_coaching_mode(self, mode: str) -> None:
        """Switch between 'instructor' and 'casual' coaching modes."""
        if mode in ("instructor", "casual"):
            self._coaching_mode = mode
            self._system_prompt = build_system_prompt(mode=mode)
            logger.info(f"Coaching mode set to: {mode}")

    def reset_conversation(self) -> None:
        """Clear conversation history for a fresh session."""
        self._contents.clear()
        self._failed_models.clear()
        self._active_model = GEMINI_MODEL
        logger.info("Conversation history cleared.")

    def _build_config(self, model: str) -> types.GenerateContentConfig:
        """Build generation config, adding ThinkingConfig only for supported models."""
        kwargs = {
            "system_instruction": self._system_prompt,
            "temperature": GEMINI_TEMPERATURE,
            "max_output_tokens": GEMINI_MAX_OUTPUT_TOKENS,
        }
        if model in _THINKING_SUPPORTED_MODELS:
            kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.LOW
            )
        return types.GenerateContentConfig(**kwargs)

    async def _try_stream(self, model: str) -> AsyncGenerator[str, None]:
        """Attempt to stream from a specific model."""
        config = self._build_config(model)
        response_stream = await self._client.aio.models.generate_content_stream(
            model=model,
            contents=self._contents,
            config=config,
        )
        async for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    async def stream_response(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Send user text to Gemini and yield response tokens as they stream in.
        Falls back to GEMINI_FALLBACK_MODEL if the primary model fails.

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

        # Build ordered list of models to try
        models_to_try = []
        if self._active_model not in self._failed_models:
            models_to_try.append(self._active_model)
        if GEMINI_FALLBACK_MODEL not in self._failed_models:
            if GEMINI_FALLBACK_MODEL != self._active_model:
                models_to_try.append(GEMINI_FALLBACK_MODEL)

        full_response = ""
        succeeded = False

        for model in models_to_try:
            try:
                logger.info(f"Streaming from {model}...")
                async for chunk_text in self._try_stream(model):
                    full_response += chunk_text
                    yield chunk_text

                # If we got here, it worked
                if model != self._active_model:
                    logger.info(f"Switched active model to {model}")
                    self._active_model = model
                succeeded = True
                break

            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    logger.warning(f"{model} unavailable (503), trying fallback...")
                    self._failed_models.add(model)
                    continue
                else:
                    logger.error(f"Gemini streaming error on {model}: {e}")
                    break

        if not succeeded and not full_response:
            error_response = json.dumps({
                "voice_reply": "I'm sorry, I had a brief issue connecting. Could you say that again?",
                "feedback": {
                    "has_corrections": False,
                    "corrections": [],
                    "natural_alternative": None,
                    "vocabulary_tip": None,
                },
            })
            full_response = error_response
            yield error_response

        # Record model turn in conversation history
        self._contents.append(
            types.Content(
                role="model",
                parts=[types.Part.from_text(text=full_response)],
            )
        )

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
