# VoceVibe4 – PyTorch STT Application

## Overview
This project implements a speech‑to‑text (STT) engine using the official PyTorch model `kyutai/stt-1b-en_fr`. It runs on CPU, uses deterministic decoding (`temp=0.0`) and provides a producer‑consumer audio pipeline.

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

## License
[Specify your license here]
