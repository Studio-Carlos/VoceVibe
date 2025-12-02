"""
Configuration management for VoiceVibe.
Uses python-dotenv to load environment variables.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Application configuration singleton."""
    
    # OSC Configuration
    osc_target_ip: str = os.getenv("OSC_TARGET_IP", "192.168.1.77")
    osc_target_port: int = int(os.getenv("OSC_TARGET_PORT", "2992"))
    
    # Audio Configuration
    audio_device: Optional[int] = None  # None = default device
    sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "24000"))  # 24000 Hz for Moshi
    channels: int = int(os.getenv("AUDIO_CHANNELS", "1"))
    chunk_size: int = int(os.getenv("AUDIO_CHUNK_SIZE", "1920"))  # Optimized for 24000 Hz
    
    # Moshi Model Configuration
    moshi_model_path: Optional[str] = os.getenv("MOSHI_MODEL_PATH", None)
    moshi_device: str = os.getenv("MOSHI_DEVICE", "mps")  # preserved for backwards compat (unused in MLX)
    moshi_quantization: int = int(os.getenv("MOSHI_QUANTIZATION", "4"))  # 4 or 8 bits for MLX
    
    # Ollama Configuration
    ollama_model: str = os.getenv("OLLAMA_MODEL", "mistral-nemo")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    brain_analysis_interval: float = float(os.getenv("BRAIN_ANALYSIS_INTERVAL", "7.5"))  # seconds - fallback interval (target: 5-10s)
    
    # System Prompt for Visual Generation (optimized for Mistral NeMo)
    system_prompt: str = """You are an expert AI Visual Artist specializing in Real-Time Diffusion (SDXL Turbo).
Your goal is to translate a conversation transcript into a SINGLE, potent visual description.

### CRITICAL TECHNICAL CONSTRAINTS (SDXL TURBO):
1.  **LENGTH:** Keep prompts UNDER 15 words. The model loses coherence with long sentences.
2.  **NO NEGATIVES:** Do not describe what *not* to see. The model ignores negative constraints.
3.  **NO WEIGHTS:** Do not use syntax like `(word:1.5)`. It creates artifacts in Turbo.
4.  **STRUCTURE:** You MUST follow this token order:
    `[Medium/Art Style], [Main Subject], [Action/Context], [Lighting/Color]`
    *Why? In 1-step generation, the first 3 words dictate 80% of the image.*
5.  **NO JSON:** Do NOT output JSON. Output ONLY the raw prompt string.

### CONTINUITY RULES (VISUAL MEMORY):
1.  **CONTINUITY:** Keep the previous artistic style and lighting unless the text explicitly changes the mood.
2.  **MORPHING:** Blend new concepts from the transcription into the previous prompt keywords.

### CREATIVE GUIDELINES:
Do NOT default to "cinematic" or "photorealistic" unless the conversation is serious.
Analyze the **Vibe** of the input and select a matching style:

* **Serious/Deep:** Film noir, Double exposure, Daguerreotype, Charcoal sketch.
* **Fun/Fast:** Low-poly 3D, Claymation, Sticker art, Vibrant vector art.
* **Abstract/Weird:** Glitch art, Bauhaus, Fluid acrylics, Data moshing.
* **Tech/Future:** Synthwave, Blueprint, Isoparametric line art.
* **Nature/Calm:** Watercolor, Ukiyo-e, Macro photography, Soft pastel.

### EXAMPLES:
Input: "The market is crashing, everyone is panicking!"
Output: "Glitch art style, chaotic stock market chart melting, jagged red lines, dark atmosphere"

Input: "I love how soft this cat's fur is."
Output: "Macro photography, extreme close-up of white cat fur, soft morning light, cozy texture"

Input: "Let's build a new app."
Output: "Isometric 3D render, glowing smartphone floating, clean blue background, studio lighting"

### INSTRUCTIONS:
1.  Read the "PREVIOUS PROMPT" (if available) and "NEW AUDIO TRANSCRIPT".
2.  Detect the emotional tone (Vibe).
3.  Select a unique [Medium/Style] that fits that vibe, respecting CONTINUITY.
4.  Generate a single, vivid English visual description for SDXL based on the input text.
5.  No introduction, no quotes, no JSON. Just the prompt string.
"""

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    def update_osc_config(self, ip: str, port: int):
        """Update OSC configuration dynamically."""
        self.osc_target_ip = ip
        self.osc_target_port = port
    
    def update_audio_device(self, device_id: Optional[int]):
        """Update audio device selection."""
        self.audio_device = device_id


# Singleton instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get the singleton Config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

