# VoceVibe4 – PyTorch STT Application

## Overview
This project implements a speech‑to‑text (STT) engine using the official PyTorch model `kyutai/stt-1b-en_fr`. It transforms spoken audio into real-time visual prompts for SDXL Turbo via OSC.

## Key Features
- **Real-Time STT**: Uses Kyutai Moshi (PyTorch CPU) for low-latency transcription.
- **Visual Brain**: LLM (Ollama) analyzes text and generates visual prompts.
- **Strict String Output**: Sends raw prompt strings via OSC (no JSON).
- **Dynamic Controls**:
  - **Prompt Rate**: Adjustable generation interval (Fastest to 30s).
  - **History Window**: Adjustable context window (5s to 60s).
  - **Visual Memory**: Maintains continuity between prompts.
- **Cyberpunk UI**: Customtkinter interface with real-time dashboard.

## Setup
1. **Clone the repository**
   ```bash
   git clone <repo‑url>
   cd VoceVibe4
   ```
2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # on macOS/Linux
   # .venv\Scripts\activate   # on Windows
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Download the STT model files**
   ```bash
   python download_stt.py
   ```
   This script pulls `model.safetensors`, `config.json`, `tokenizer_spm_32k_3.model` and other required files from HuggingFace.

## Running the Application
```bash
python main.py
```
The audio engine will start, capture microphone input at 24 kHz, and output transcriptions in French.

## Project Structure
- `src/audio_engine.py` – Core STT logic.
- `download_stt.py` – Helper to fetch model files.
- `requirements.txt` – Pinning `torch==2.5.1` and related packages.
- `README.md` – This file.
- `DEVELOPMENT_HISTORY.md` – Full chronological development log.

## Notes
- The repository’s `.gitignore` excludes large artefacts (`.venv/`, `models_cache/`, `*.safetensors`, `*.pt`, `*.pth`, `*.bin`, audio files, logs, etc.).
- The model runs on CPU; no MPS support is required.
- Deterministic decoding (`temp=0.0`) eliminates hallucinations.
- **Prompt Rate Constraint**: The prompt generation rate is always ≤ history window duration.

## License
[Specify your license here]
