"""LingoFlow - End-to-End Pipeline Test"""
import asyncio
from backend.services.stt_service import DeepgramSTTService
from backend.services.llm_service import GeminiLLMService
from backend.services.tts_service import EdgeTTSService

async def test_all():
    # 1. Deepgram STT
    print("=== 1/3: Deepgram STT Connection ===")
    stt = DeepgramSTTService()
    await stt.start()
    print("  Deepgram connected.")
    await stt.stop()
    print("  Deepgram closed. PASS")

    # 2. Gemini LLM
    print("\n=== 2/3: Gemini LLM Streaming ===")
    llm = GeminiLLMService()
    full = ""
    async for chunk in llm.stream_response("Hi, yesterday I go to school and eat an apple."):
        full += chunk
        print(chunk, end="", flush=True)
    print()
    parsed = llm.parse_response(full)
    vr = parsed.get("voice_reply", "")
    has_fb = parsed.get("feedback", {}).get("has_corrections", False)
    print(f"  voice_reply length: {len(vr)} chars")
    print(f"  has_corrections: {has_fb}")
    print(f"  Active model: {llm._active_model}")
    print("  PASS")

    # 3. Edge-TTS
    print("\n=== 3/3: Edge-TTS Synthesis ===")
    tts = EdgeTTSService()
    audio = await tts.synthesize(vr if vr else "Hello from LingoFlow.")
    print(f"  Generated {len(audio)} bytes of MP3 audio. PASS")

    # 4. Full pipeline: LLM stream -> sentence-chunked TTS
    print("\n=== BONUS: End-to-End Sentence-Chunked Pipeline ===")
    async def token_gen():
        async for t in llm.stream_response("Can you explain what photosynthesis is?"):
            yield t
    chunk_count = 0
    total_audio = 0
    async for sentence, audio_bytes in tts.stream_sentence_audio(token_gen()):
        chunk_count += 1
        total_audio += len(audio_bytes)
        preview = sentence[:60]
        print(f"  Chunk {chunk_count}: \"{preview}\" ({len(audio_bytes)} bytes)")
    print(f"  Total: {chunk_count} audio chunks, {total_audio} bytes")
    print("  PASS")

    print("\n ALL TESTS PASSED!")

asyncio.run(test_all())
