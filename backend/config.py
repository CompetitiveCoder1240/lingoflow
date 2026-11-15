"""
LingoFlow - Application Configuration
Centralizes all settings for STT, LLM, TTS, and application behavior.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# API Keys
# ──────────────────────────────────────────────
DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ──────────────────────────────────────────────
# Deepgram STT Configuration
# ──────────────────────────────────────────────
DEEPGRAM_MODEL: str = "nova-2"           # Best accuracy model on Deepgram
DEEPGRAM_LANGUAGE: str = "en"            # English-only for POC
DEEPGRAM_ENCODING: str = "linear16"      # Raw PCM from browser mic
DEEPGRAM_SAMPLE_RATE: int = 16000        # 16kHz mono
DEEPGRAM_CHANNELS: int = 1
DEEPGRAM_ENDPOINTING_MS: int = 500       # Silence to trigger end-of-speech (learner-friendly)

# ──────────────────────────────────────────────
# Google Gemini LLM Configuration
# ──────────────────────────────────────────────
# Primary: fast, responsive free-tier model with sub-second latency for voice
GEMINI_MODEL: str = "gemini-3.5-flash-lite"
# Fallback: high-capacity model
GEMINI_FALLBACK_MODEL: str = "gemini-3.8-flash"
GEMINI_TEMPERATURE: float = 0.7
GEMINI_MAX_OUTPUT_TOKENS: int = 512

# ──────────────────────────────────────────────
# Edge-TTS Configuration (Free Neural Voices)
# ──────────────────────────────────────────────
TTS_VOICE: str = "en-US-JennyNeural"     # Warm, natural female voice
TTS_RATE: str = "+0%"                    # Speech rate adjustment
TTS_VOLUME: str = "+0%"                  # Volume adjustment

# Available English voices for potential selection
AVAILABLE_VOICES: dict = {
    "jenny":   "en-US-JennyNeural",      # Female, warm & conversational
    "guy":     "en-US-GuyNeural",        # Male, clear & professional
    "aria":    "en-US-AriaNeural",       # Female, expressive
    "davis":   "en-US-DavisNeural",      # Male, friendly
    "sonia":   "en-GB-SoniaNeural",      # Female, British accent
    "ryan":    "en-GB-RyanNeural",       # Male, British accent
}

# ──────────────────────────────────────────────
# Coaching Mode
# ──────────────────────────────────────────────
DEFAULT_COACHING_MODE: str = "instructor"  # "instructor" or "casual"

# ──────────────────────────────────────────────
# Sentence Chunking (for streaming TTS)
# ──────────────────────────────────────────────
SENTENCE_DELIMITERS: str = r"[.?!;:\n]"  # Regex pattern for clause boundaries
MIN_CHUNK_LENGTH: int = 10               # Min chars before triggering TTS on a chunk

# ──────────────────────────────────────────────
# Server
# ──────────────────────────────────────────────
HOST: str = "0.0.0.0"
PORT: int = 8000
