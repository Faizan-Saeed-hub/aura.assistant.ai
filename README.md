# Aura — Next-Gen AI Personal Assistant 🌟

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![LLM Support](https://img.shields.io/badge/LLM-OpenRouter%20%7C%20Gemini%20%7C%20Groq%20%7C%20Ollama-7c3aed.svg)](#multi-provider-llm-architecture)
[![Zero Cost Tools](https://img.shields.io/badge/Tools-100%25%20Free%20APIs-success.svg)](#agentic-tools--apis)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Aura** is a modular, agentic **AI Personal Assistant** engineered in Python. It features conversational reasoning, multi-provider LLM support with automatic free model failover, dual-layer memory, document RAG (Retrieval-Augmented Generation), bilingual voice interaction (English & Roman Urdu), and full-screen creative studios for email composition and photo retouching.

---

## 🚀 Key Features

### 1. 💬 Conversational Brain & Multi-Provider LLM Engine
- **Multi-Provider Architecture**:
  - **OpenRouter (100% Free)**: Access to `meta-llama/llama-3.3-70b-instruct:free`, `deepseek/deepseek-r1:free`, `google/gemini-2.0-flash-exp:free`, and `qwen/qwen-2.5-72b-instruct:free` with zero credit card required and automatic fallback.
  - **Google Gemini**: Official Google AI Studio free tier (`gemini-2.5-flash-lite`, `gemini-2.5-flash`).
  - **Groq Cloud**: Ultra-fast low-latency inference (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`).
  - **Ollama**: 100% offline, local, private execution without any API keys.
  - **OpenAI**: Direct GPT-4o compatibility.
- **Dynamic Failover**: If any upstream provider experiences rate limits or server downtime, Aura automatically routes the query to the next available provider.

### 2. 🗣️ Bilingual Voice Interaction & Language Mirroring
- **Web Speech Dictation (STT)**: Bottom omnibar language toggle between **English (`en-US`)** and **Urdu / Roman Urdu (`ur-PK`)**.
- **Continuous Voice Input & Manual Send**: Speak multi-sentence queries freely with cumulative live transcription; microphone automatically halts and composition resets upon sending.
- **Strict Language Mirroring**:
  - Prompts in **Roman Urdu** or **Urdu script** are answered strictly in conversational **Roman Urdu**.
  - Prompts in **English** are answered strictly in clear, professional **English**.
- **Bilingual Voice Synthesis (TTS)**: Intelligent phonetic voice matching for English and Urdu pronunciations.

### 3. ✉️ Full-Screen AI Email Studio & Voice Drafter
- **In-Page Workspace**: Full-screen layout with zero popup modals.
- **Voice Dictation Button**: Speak and dictate key points directly into the prompt box via microphone in English or Roman Urdu.
- **1-Click Quick Starters**: Templates for *Client Pitch*, *Job Application*, *Follow-up*, *Schedule Sync*, and *Launch Update*.
- **Tone Customizer**: Professional, Friendly, Persuasive, Concise, Urgent.
- **Real-Time Word & Character Counters**: Dynamic metrics for input key points and generated email copy.
- **Export Options**: Copy text to clipboard, download as standard RFC822 `.eml` (compatible with Outlook, Apple Mail, Thunderbird), or open directly in your mail app.

### 4. 🖼️ Full-Screen Social Media Image Studio & AI Retouch Suite
- **Dual-Mode Studio Workspace**:
  - **Tab 1: 📐 Framing & Sizing**: Social presets for **WhatsApp** (DP 1:1, Status 9:16), **Instagram** (Square 1:1, Portrait 4:5, Story 9:16, Landscape), **Facebook**, **YouTube**, **LinkedIn**, and **Twitter/X**. Supports Blurred Background, Circular DP Mask, Fill & Crop, Letterbox, Zoom, Pan, and 90° Rotation.
  - **Tab 2: ✨ AI Face Glow & Retouch**: Client-side canvas pixel processing engine.
- **Strict Facial Structure Preservation Guarantee**:
  - Deterministic color-space luminance curves, tear-trough shadow lifting, and edge-preserving bilateral filtering.
  - **Zero generative morphing or AI distortion**: Facial expressions, eyes, smile, jawline, nose, and identity are 100% untouched and preserved.
- **Retouch Controls**:
  - **Dark Circles Remover**: Toggle switch & intensity slider (0–100%) targeting under-eye tear trough shadows, lifting luminance toward cheek radiance and neutralizing tired blue/purple undertones.
  - **Natural Light & Face Glow Slider (0–100%)**: Softbox fill lighting lifting midtones without clipping highlights.
  - **Skin Texture Softening Slider (0–100%)**: Smooths pores and blemishes while preserving crisp eye borders and lips.
  - **Skin Tone Warmth Slider (-50 to +50)**: Balances cool editorial tones and warm golden amber radiance.
  - **4 1-Click Retouch Presets**: *Natural Glow*, *Erase Dark Circles*, *Studio Glam*, and *Reset*.
  - **Hold to Compare**: Press and hold to instantly display the raw unretouched original with a floating badge.
  - **Direct Export**: Download high-resolution PNG or set directly as your assistant profile picture (**Set as Account DP**).
- **In-Chat Quick Studio & Photo Retouch (+)**:
  - Direct `+` menu on the fixed bottom omnibar allows instant photo upload, AI art generation, and email drafting without leaving the chat.
  - Attached photos can be retouched right in chat with instant presets (`✨ Face Glow`, `👁️ Conceal Dark Circles`, `📷 1:1 WhatsApp DP`, `💎 Glam`, `🖤 B&W`) and returned with 1-click Download, Set as DP, or Fine-tune in Studio.

### 5. 🧠 Dual-Layer Memory Engine
- **Short-Term Memory**: Session conversation history with SQLite persistence and sliding window context.
- **Long-Term Memory Vault**: Enduring user facts, preferences, and personal rules.
- **Dynamic Memory Tools**:
  - `remember_fact`: Executed autonomously when the user shares personal preferences (e.g., *"Remember that I prefer dark mode"*).
  - `forget_memory`: Executed autonomously when the user asks to forget or remove facts.

### 6. 📚 Document Knowledge Base (RAG)
- **Multi-Format Ingestion**: Ingests PDF, DOCX, TXT, Markdown, and CSV files.
- **Recursive Text Chunker**: Overlapping chunking with metadata preservation.
- **Persistent Vector Store**: Lightweight, zero-dependency cosine vector store with source citations and ground truth answers.

### 7. 🛠️ 100% Free Autonomous Agentic Tools (Zero Key Required)
- 🔍 **DuckDuckGo Web Search**: Live search for articles, news, and current events.
- 🌤️ **Open-Meteo Weather API**: Instant global weather, temperature, humidity, and forecasts.
- 📖 **Wikipedia Knowledge API**: Encyclopedic summaries on demand.
- 🧮 **Math Calculator**: Safe evaluation of arithmetic, trigonometry, and algebraic formulas.
- 📝 **Notes & Tasks Manager**: Create, search, filter, and complete personal to-dos.
- ⏰ **System Utilities**: Real-time clock, calendar, weekday, and system status.

### 8. 👤 User Profile & Account Management
- **Multi-Account Registration**: Register and switch user profiles.
- **Gender Selection & Automatic DP Matching**: Instant professional male or female default avatar assignment.
- **Custom Photo Upload**: Pick and upload any local portrait picture directly to your profile.

---

## 🏗️ Project Architecture

```
aura.assistant.ai/
├── backend/
│   ├── app.py              # FastAPI application & REST endpoints
│   ├── config.py           # Environment settings & provider configurations
│   ├── database.py         # SQLite schema (sessions, messages, memories, notes, users)
│   ├── agent/
│   │   └── orchestrator.py # Cognitive coordinator: LLM, tools, memory & RAG
│   ├── llm/
│   │   ├── client.py       # Multi-provider LLM adapter with failover
│   │   └── prompts.py      # System personas & strict language rules
│   ├── memory/
│   │   ├── conversation.py # Short-term chat history
│   │   └── long_term.py    # Long-term memory extraction & vault
│   ├── rag/
│   │   ├── parser.py       # Document parser (PDF, DOCX, TXT, CSV)
│   │   ├── chunker.py      # Recursive text chunking
│   │   └── vector_store.py # Persistent vector search engine
│   └── tools/
│       ├── registry.py     # Tool dispatcher & schema declarations
│       ├── web_search.py   # DuckDuckGo live search
│       ├── weather.py      # Open-Meteo weather API
│       ├── calculator.py   # Safe mathematical evaluator
│       ├── wikipedia.py    # Wikipedia summaries
│       ├── notes.py        # Task & notes manager
│       └── system_info.py  # Real-time date & clock utilities
├── frontend/
│   ├── index.html          # Neo-productivity workspace & full-page studio views
│   ├── css/style.css       # Unified design system & responsive styling
│   └── js/app.js           # Client-side router, voice dictation, canvas retouch engine
├── data/
│   ├── avatars/            # Custom user profile pictures (.gitkeep)
│   ├── uploads/            # Uploaded RAG documents (.gitkeep)
│   └── vector_db/          # Persistent vector index (.gitkeep)
├── tests/
│   └── test_backend.py     # Automated subsystem integration test suite
├── .env.example            # Template for API keys and configuration
├── .gitignore              # Secure exclusions for secrets, venv, and local data
├── requirements.txt        # Python package dependencies
├── run.py                  # One-click startup launcher
└── README.md
```

---

## ⚡ Quick Start Guide

### Prerequisites
- Python 3.10 or higher
- Git

### 1. Clone Repository
```bash
git clone https://github.com/Faizan-Saeed-hub/aura.assistant.ai.git
cd aura.assistant.ai
```

### 2. Create Virtual Environment & Install Dependencies
```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment
Copy the `.env.example` template:
```bash
cp .env.example .env
```

Add your preferred free API key (choose at least one):
- **OpenRouter (Free Models)**: Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys)
- **Google Gemini (Free Tier)**: Get a free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- **Groq (Free Tier)**: Get a free key at [console.groq.com/keys](https://console.groq.com/keys)
- **Ollama (Offline)**: Install from [ollama.com](https://ollama.com) — zero API key required!

### 4. Run Aura
```powershell
python run.py
```
Aura will boot the backend web server and automatically open the application at **`http://localhost:8000`** in your browser.

---

## 🧪 Running Automated Tests

A comprehensive integration test suite verifies database operations, memory extraction, agentic tools, and vector search:
```powershell
python tests/test_backend.py
```

---

## 🔒 Security & Privacy

- **API Keys & Secrets**: All credentials are kept in `.env` and strictly excluded from git tracking via `.gitignore`.
- **Local Data Storage**: User databases (`assistant.db`), custom avatars, and indexed RAG documents remain on your local machine.
- **Client-Side Image Processing**: Facial retouching, dark circles removal, and framing effects execute 100% locally in your browser's HTML5 Canvas. No personal photos are sent to third-party image processing servers.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
