# VoceVibe – Real-Time Audio-to-Visual Performance Application

## Overview
VoceVibe is a real-time speech-to-text (STT) application that transforms spoken audio into visual prompts. It uses Kyutai's Moshika MLX models optimized for Apple Silicon, processes transcriptions with an LLM (Ollama), and sends visual prompts via OSC to external applications like SDXL Turbo.

## Key Features
- **Real-Time STT**: Uses Kyutai Moshika MLX models optimized for Apple Silicon (M1/M2/M3)
- **Bilingual Support**: English and French transcription
- **Producer-Consumer Architecture**: Stable audio processing with non-blocking ML inference
- **Automatic Gain Control (AGC)**: Normalizes varying audio input levels
- **Noise Gating**: Filters background noise for accurate transcription
- **Visual Brain**: LLM (Ollama) analyzes text and generates visual prompts
- **OSC Integration**: Sends prompt strings via Open Sound Control
- **Dynamic Controls**:
  - **Prompt Rate**: Adjustable generation interval (Fastest to 30s)
  - **History Window**: Adjustable context window (5s to 60s)
  - **Visual Memory**: Maintains continuity between prompts
- **Modern UI**: CustomTkinter interface with real-time audio level visualization

## Setup
1. **Clone the repository**
   ```bash
   git clone <repo‑url>
   cd VoceVibe
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
- The repository's `.gitignore` excludes large artefacts (`.venv/`, `models_cache/`, `*.safetensors`, `*.pt`, `*.pth`, `*.bin`, audio files, logs, etc.).
- The model uses MLX framework optimized for Apple Silicon (no PyTorch MPS issues).
- Strict sampling parameters (`temp=0.1`, `top_p=0.9`) ensure deterministic transcription.
- **Prompt Rate Constraint**: The prompt generation rate is always ≤ history window duration.

## Requirements
- Python 3.10+ (3.12 recommended)
- macOS with Apple Silicon (M1/M2/M3)
- Ollama installed and running (for LLM functionality)

## Contributing
Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Copyright (c) 2024 Studio Carlos**

Permission is granted to use, modify, and distribute this software, provided that the original copyright notice and license are included in all copies or substantial portions of the software.
