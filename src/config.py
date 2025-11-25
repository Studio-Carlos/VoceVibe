"""
Configuration management for VoiceVibe4.
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
    system_prompt: str = """You are a real-time AI Visual Jockey (VJ). 
Your goal is to translate the user's conversation into a short, impactful visual description for SDXL-Turbo image generation.

STRICT RULES:
1. OUTPUT FORMAT: Single valid JSON object. No markdown, no chatting.
2. LANGUAGE: The 'prompt' value MUST be in ENGLISH.
3. PROMPT SYNTAX: Use the specific SDXL-Turbo order: [Art Style], [Subject], [Action], [Environment], [Lighting].
4. LENGTH: Keep the prompt under 25 words. Focus on the main visual impact.
5. NO NEGATIVES: Do not describe what NOT to see.

Expected JSON Structure:
{
    "prompt": "cinematic photo, a lonely astronaut floating in space, dark nebula background, cold blue lighting",
    "style": "Cinematic Sci-Fi",
    "mood": "Melancholic"
}

If the input is French, TRANSLATE the core visual concept to English.
Be creative but direct."""

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

