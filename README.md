# 🗣️ LingoFlow – AI English Fluency Coach

> A ChatGPT-style real-time voice conversation partner that helps you practice and improve your spoken English — powered by a **100% free** GenAI stack.

![Stack](https://img.shields.io/badge/STT-Deepgram_Nova--2-blue)
![Stack](https://img.shields.io/badge/LLM-Gemini_3.8_Flash-4285F4)
![Stack](https://img.shields.io/badge/TTS-Edge--TTS_Neural-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **🎤 Real-Time Voice Conversations** — Speak naturally and get instant voice replies, just like talking to a native speaker.
- **⚡ Sub-Second Latency** — Sentence-level streaming pipeline with Google Gemini 3.8 Flash delivers the first audio syllable in under 800ms.
- **📝 Live Grammar Feedback** — Non-intrusive visual corrections, vocabulary tips, and native phrasing suggestions displayed alongside the conversation.
- **🔊 Natural Neural Voices** — 6 high-quality Microsoft Neural voices to choose from (US and British accents).
- **🖐️ Barge-In Support** — Interrupt the AI mid-sentence, just like in a real conversation.
- **💰 100% Free** — No paid APIs. Uses Deepgram's free credit, Google Gemini's free tier on Google AI Studio, and Edge-TTS (no API key needed).

## 🏗️ Architecture

```
[Mic] → [Deepgram Nova-2 STT] → [Google Gemini 3.8 Flash LLM] → [Edge-TTS Neural] → [Speaker]
                                             ↓
                                  [Visual Feedback Panel]
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A free [Deepgram API key](https://console.deepgram.com/signup) ($200 free credit)
- A free [Gemini API key](https://aistudio.google.com) (free tier on Google AI Studio)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/CompetitiveCoder1240/lingoflow.git
cd lingoflow

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your free DEEPGRAM_API_KEY and GEMINI_API_KEY

# 5. Run the server
python -m backend.app
```

### Open the App

Navigate to **http://localhost:8000** in your browser, click the microphone, and start talking!

## 📂 Project Structure (MVC Architecture)

```
lingoflow/
├── backend/
│   ├── app.py                 # Thin FastAPI application factory (< 45 lines)
│   ├── config.py              # Centralized environment & model configuration
│   ├── models/                # [M] Data structures, schemas, and session state
│   │   ├── schemas.py         # Pydantic models for events, feedback, & controls
│   │   └── session.py         # Active conversation session runtime model
│   ├── views/                 # [V] API presentation & routing layer
│   │   └── routes.py          # HTTP endpoints & WebSocket route definitions
│   ├── controllers/           # [C] Business orchestration & workflow
│   │   ├── conversation_controller.py  # Real-time WebSocket voice pipeline
│   │   └── http_controller.py          # HTTP views & diagnostic health checks
│   ├── services/              # Domain & Provider integrations
│   │   ├── stt_service.py     # Deepgram Nova-2 streaming STT
│   │   ├── llm_service.py     # Google Gemini streaming LLM
│   │   └── tts_service.py     # Microsoft Edge-TTS neural speech synthesis
│   └── prompts/
│       └── tutor_prompts.py   # Instructor & Casual system prompt personas
├── frontend/                  # Client-side View
│   ├── index.html             # Main voice interface
│   ├── css/styles.css         # Modern dark-theme UI with animated voice orb
│   └── js/
│       ├── audio_recorder.js  # Mic capture with real-time RMS energy meter
│       ├── audio_player.js    # Gapless MP3 queue player with barge-in
│       └── app.js             # UI controller, Echo Guard, and WebSocket manager
├── test_mvc.py                # MVC unit & integration test suite
├── test_pipeline.py           # End-to-end service pipeline test suite
├── .env.example               # Free API keys template
├── requirements.txt           # Python dependencies
└── README.md
```

## 🎙️ Available Voices

| Name  | Voice ID              | Accent          |
| ----- | --------------------- | --------------- |
| Jenny | en-US-JennyNeural     | American (Warm) |
| Guy   | en-US-GuyNeural       | American (Pro)  |
| Aria  | en-US-AriaNeural      | American (Expr) |
| Davis | en-US-DavisNeural     | American (Frnd) |
| Sonia | en-GB-SoniaNeural     | British         |
| Ryan  | en-GB-RyanNeural      | British         |

## 🛠️ Tech Stack

| Component | Technology               | Cost |
| --------- | ------------------------ | ---- |
| STT       | Deepgram Nova-2          | Free ($200 credit) |
| LLM       | Google Gemini 3.8 Flash  | Free (Google AI Studio) |
| TTS       | Microsoft Edge-TTS       | Free (no key needed) |
| Backend   | FastAPI + WebSockets     | Open Source |
| Frontend  | Vanilla JS + Web Audio    | Open Source |

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
