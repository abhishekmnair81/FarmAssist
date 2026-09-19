# 🌾 FarmAssist: AI Krishi Mitra & Agricultural Assistant

> Real-time, hyperlocal AI agronomist for Indian farmers over **WhatsApp** and **Web**, supporting **Malayalam, Hindi, Tamil, and English**.

---

## 📖 Complete Technical Documentation

For the full, end-to-end technical blueprint, architecture diagram, models used, and AI system reference, please see:
👉 **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)**

---

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Groq API Key (for LLM reasoning & Whisper STT)
- NVIDIA NIM API Key (optional, for high-availability fallback & multimodal vision)

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### 3. Launch Services
```bash
docker-compose up -d --build
```

### 4. Connect WhatsApp
Access the OpenWA gateway at `http://localhost:2785` or check the logs to scan the WhatsApp QR code:
```bash
docker logs farmassist-openwa-gateway-1
```

---

## 🛠️ Tech Stack Highlights
- **Agent Framework:** LangGraph 1.1.6 with SQLite Checkpointing
- **Primary LLM:** Groq `openai/gpt-oss-120b`
- **Fallback & Vision:** NVIDIA NIM (`meta/llama-3.2-11b-vision-instruct`)
- **Speech Engine:** Groq Whisper STT + Microsoft Edge-TTS Neural Voices
- **Agricultural Grounding:** Open-Meteo Weather, APMC Mandi Rates, FAISS RAG, CIBRC/PPQS Agrochemical Database
