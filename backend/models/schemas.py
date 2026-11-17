"""
LingoFlow - Data Models & Schemas (MVC: Model)
Defines Pydantic models for validation, serialization, and structured communication.
"""

from enum import Enum
from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field


# ── Pedagogical Feedback Models ─────────────────────────────

class CorrectionItem(BaseModel):
    """Represents an individual grammar or usage correction."""
    original: str = Field(..., description="The learner's original utterance with the error")
    corrected: str = Field(..., description="The corrected native version")
    rule: Optional[str] = Field(None, description="Grammar or usage explanation")


class FeedbackData(BaseModel):
    """Structured pedagogical feedback payload."""
    has_corrections: bool = False
    corrections: List[CorrectionItem] = Field(default_factory=list)
    natural_alternative: Optional[str] = None
    vocabulary_tip: Optional[str] = None


class VoiceReplyPayload(BaseModel):
    """Complete structured response from the LLM."""
    voice_reply: str
    feedback: FeedbackData = Field(default_factory=FeedbackData)


# ── HTTP API Models ──────────────────────────────────────────

class HealthResponse(BaseModel):
    """Response schema for the /health endpoint."""
    status: str = "ok"
    service: str = "LingoFlow"
    llm: str = "Gemini 3.5 Flash Lite"


# ── WebSocket Incoming Message Models ────────────────────────

class ControlAction(str, Enum):
    START = "start"
    STOP = "stop"
    CANCEL = "cancel"
    RESET = "reset"


class ClientControlMessage(BaseModel):
    type: Literal["control"]
    action: ControlAction


class ClientConfigMessage(BaseModel):
    type: Literal["config"]
    voice: Optional[str] = None
    mode: Optional[str] = None


# ── WebSocket Outgoing Event Models ──────────────────────────

class StateEvent(BaseModel):
    type: Literal["state"] = "state"
    state: str
    mode: Optional[str] = None


class TranscriptEvent(BaseModel):
    type: Literal["transcript"] = "transcript"
    text: str
    is_final: bool


class AITextEvent(BaseModel):
    type: Literal["ai_text"] = "ai_text"
    text: str


class FeedbackEvent(BaseModel):
    type: Literal["feedback"] = "feedback"
    has_corrections: bool = False
    corrections: List[CorrectionItem] = Field(default_factory=list)
    natural_alternative: Optional[str] = None
    vocabulary_tip: Optional[str] = None


class ModeUpdatedEvent(BaseModel):
    type: Literal["mode_updated"] = "mode_updated"
    mode: str


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
