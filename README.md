# 🗣️ LingoFlow – AI English Fluency Coach

> A ChatGPT-style real-time voice conversation partner that helps you practice and improve your spoken English — powered by a **100% free** GenAI stack.

![Stack](https://img.shields.io/badge/STT-Deepgram_Nova--2-blue)
![Stack](https://img.shields.io/badge/LLM-Groq_Llama_3.3-orange)
![Stack](https://img.shields.io/badge/TTS-Edge--TTS_Neural-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **🎤 Real-Time Voice Conversations** — Speak naturally and get instant voice replies, just like talking to a native speaker.
- **⚡ Sub-Second Latency** — Sentence-level streaming pipeline delivers the first audio syllable in under 800ms.
- **📝 Live Grammar Feedback** — Non-intrusive visual corrections, vocabulary tips, and native phrasing suggestions displayed alongside the conversation.
- **🔊 Natural Neural Voices** — 6 high-quality Microsoft Neural voices to choose from (US and British accents).
- **🖐️ Barge-In Support** — Interrupt the AI mid-sentence, just like in a real conversation.
- **💰 100% Free** — No paid APIs. Uses Deepgram's free credit, Groq's perpetual free tier, and Edge-TTS (no API key needed).

## 🏗️ Architecture

```
[Mic] → [Deepgram Nova-2 STT] → [Groq Llama 3.3 70B LLM] → [Edge-TTS Neural] → [Speaker]
                                         ↓
                              [Visual Feedback Panel]
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A free [Deepgram API key](https://console.deepgram.com/signup) ($200 free credit)
- A free [Groq API key](https://console.groq.com/keys) (perpetual free tier)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/lingoflow.git
cd lingoflow

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your free API keys

# 5. Run the server
python -m backend.app
```

### Open the App

Navigate to **http://localhost:8000** in your browser, click the microphone, and start talking!

## 📂 Project Structure

```
lingoflow/
├── backend/
│   ├── app.py                 # FastAPI server & WebSocket endpoint
│   ├── config.py              # All configuration settings
│   ├── services/
│   │   ├── stt_service.py     # Deepgram real-time transcription
│   │   ├── llm_service.py     # Groq streaming chat completions
│   │   └── tts_service.py     # Edge-TTS sentence-chunked synthesis
│   └── prompts/
│       └── tutor_prompts.py   # English fluency coach persona
├── frontend/
│   ├── index.html             # Voice interface
│   ├── css/styles.css         # Dark-theme UI with animated orb
│   └── js/
│       ├── audio_recorder.js  # Mic capture & PCM streaming
│       ├── audio_player.js    # MP3 queue player with barge-in
│       └── app.js             # UI orchestrator & WebSocket manager
├── .env.example               # API key template
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

| Component | Technology            | Cost |
| --------- | --------------------- | ---- |
| STT       | Deepgram Nova-2       | Free ($200 credit) |
| LLM       | Groq Llama 3.3 70B   | Free (perpetual) |
| TTS       | Microsoft Edge-TTS    | Free (no key needed) |
| Backend   | FastAPI + WebSockets  | Open Source |
| Frontend  | Vanilla JS + Web Audio | Open Source |

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
