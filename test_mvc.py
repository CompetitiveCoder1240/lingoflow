"""
LingoFlow - MVC Architecture Verification Suite
Tests the separation of Models, Views, and Controllers.
"""

import asyncio
from fastapi.testclient import TestClient

from backend.app import app
from backend.models.schemas import (
    HealthResponse,
    CorrectionItem,
    FeedbackData,
    VoiceReplyPayload,
    StateEvent,
    TranscriptEvent,
)
from backend.models.session import ConversationSession
from backend.controllers.http_controller import HttpController


def test_models():
    print("=== 1. Testing Models & Schemas ===")
    # 1. Validation
    item = CorrectionItem(original="I go", corrected="I went", rule="Past tense")
    feedback = FeedbackData(
        has_corrections=True,
        corrections=[item],
        natural_alternative="I went to the store",
        vocabulary_tip="snack on",
    )
    payload = VoiceReplyPayload(voice_reply="Nice job!", feedback=feedback)
    assert payload.voice_reply == "Nice job!"
    assert len(payload.feedback.corrections) == 1
    print("  Pydantic schemas validated. PASS")

    # 2. Session Model
    session = ConversationSession(mode="instructor", voice="en-US-JennyNeural")
    assert session.state == "idle"
    session.append_transcript("Hello")
    session.append_transcript("world")
    consumed = session.consume_transcript()
    assert consumed == "Hello world"
    assert session.consume_transcript() == ""
    print("  ConversationSession model validated. PASS")


def test_controllers_and_views():
    print("\n=== 2. Testing HTTP Controller & Views ===")
    client = TestClient(app)

    # Health check
    res_health = client.get("/health")
    assert res_health.status_code == 200
    data = res_health.json()
    assert data["status"] == "ok"
    assert "Gemini" in data["llm"]
    print(f"  GET /health: {data}. PASS")

    # Voices API
    res_voices = client.get("/api/voices")
    assert res_voices.status_code == 200
    voices_data = res_voices.json()
    assert "jenny" in voices_data["voices"]
    print(f"  GET /api/voices: {len(voices_data['voices'])} voices available. PASS")

    # Index page
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "LingoFlow" in res_index.text
    print("  GET /: UI template served. PASS")


if __name__ == "__main__":
    test_models()
    test_controllers_and_views()
    print("\n ALL MVC ARCHITECTURE TESTS PASSED!")
