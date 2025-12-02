# VoceVibe4 – Real-Time Audio-to-Visual Performance Application

## Overview
**VoceVibe** is a real-time speech-to-text (STT) application designed for generative art performance. It acts as a "cognitive bridge" that transforms spoken audio into structured visual prompts in real-time.

It utilizes **Kyutai's Dedicated STT 1B model** (running on PyTorch CPU for maximum stability on macOS), processes transcripts with a local Large Language Model (**Mistral NeMo** via Ollama), and sends engineered visual prompts via **OSC** (Open Sound Control) to external rendering engines like TouchDesigner, Stable Diffusion, or Flux.

> **⚠️ Hardware Requirement:** This project is developed and optimized for **macOS Apple Silicon (M1/M2/M3)**. While it uses the CPU for the STT model to ensure stability with specific PyTorch operators, the architecture is designed for the unified memory bandwidth of Mac chips.

## 🚀 Key Features

* **Real-Time Bilingual STT:** Powered by `kyutai/stt-1b-en_fr` (Dedicated STT model) running on PyTorch. Handles switching between French and English fluidly.
* **Hallucination-Free Architecture:** Uses a dedicated STT model (not a conversational one) with deterministic decoding (`temp=0.0`) to prevent the AI from "inventing" dialogue.
* **"Dual-Brain" Intelligence:**
    * **⚡️ Fast Lane (BrainEngine):** Generates instant, artistic visual prompts (SDXL-optimized) every few seconds based on immediate context.
    * **🐢 Slow Lane (SummaryEngine):** Accumulates the full conversation history to generate structured diagrams, mind maps, or summaries every minute.
* **Robust Audio Pipeline:** Includes Automatic Gain Control (AGC) and strict Noise Gating to ensure only clear voice data reaches the model.
* **OSC Integration:** Sends raw strings to `/visual/prompt` (for generative art) and `/visual/summary` (for archives/structure).
* **Cyberpunk UI:** A dark-mode `customtkinter` interface providing real-time monitoring of audio levels, transcriptions, and generated prompts.

## 📋 Prerequisites

* **macOS** (Apple Silicon M1/M2/M3 recommended).
* **Python 3.10+**.
* **Ollama** installed and running. You must pull the required LLM model before starting:
    ```bash
    ollama pull mistral-nemo
    ```

## 🛠️ Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/Studio-Carlos/VoceVibe.git](https://github.com/Studio-Carlos/VoceVibe.git)
    cd VoceVibe
    ```

2.  **Create a virtual environment** (Recommended)
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**
    This project requires specific versions of PyTorch to maintain compatibility with the Moshi/Kyutai loader.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Download STT Models**
    The application handles model downloading automatically via HuggingFace Hub upon the first launch. Ensure you have an internet connection for the first run (~2GB download).

## 🎮 Usage

1.  **Start the Application**
    ```bash
    python main.py
    ```

2.  **Configuration (In-App)**
    * **Audio Input:** Select your microphone or virtual cable (e.g., BlackHole) from the dropdown.
    * **OSC Target:** Set the IP and Port of your visualizer (default: `127.0.0.1:8000`).
    * **History Window:** Adjust the slider to control how much context the "Fast Brain" takes into account.

3.  **Perform**
    * Click **START**.
    * Speak into the microphone.
    * Monitor the **STT** (blue), **Fast Prompts** (pink), and **Summaries** (orange) in the logs.

## 🏗️ Architecture

The application runs on a multi-threaded architecture to ensure the UI never freezes:

* **`src/audio_engine.py`**: Handles audio capture (sounddevice) and transcription (PyTorch). Uses a Producer/Consumer pattern with a thread-safe queue.
* **`src/brain_engine.py`** (Fast Brain): Consumes transcripts, maintains a sliding window of context, and prompts Ollama for SDXL visual descriptions.
* **`src/summary_engine.py`** (Slow Brain): Accumulates the entire session transcript and triggers high-level summaries or diagram prompts at longer intervals.
* **`src/osc_client.py`**: Handles network communication.
* **`src/config.py`**: Centralized configuration and System Prompts.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to propose features or fix bugs.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


>>>>>>> 8347611 (refactor: Rename project to VoceVibe, update documentation, and refresh license year.)
**Copyright (c) 2025 Studio Carlos**
