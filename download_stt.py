"""
Download Kyutai STT model files from HuggingFace.
Repo: kyutai/stt-1b-en_fr
"""
from huggingface_hub import hf_hub_download
import os

REPO_ID = "kyutai/stt-1b-en_fr"
FILES = [
    "model.safetensors",
    "config.json",
    "tokenizer_en_fr_audio_8000.model",  # Actual tokenizer name in repo
    "mimi-pytorch-e351c8d8@125.safetensors",  # Mimi audio encoder
]

def download_stt_model():
    """Download all required files for STT model."""
    print(f"📥 Downloading Kyutai STT model from {REPO_ID}...")
    
    downloaded_files = []
    for filename in FILES:
        try:
            print(f"⏳ Downloading {filename}...")
            path = hf_hub_download(REPO_ID, filename)
            print(f"✅ {filename}: {path}")
            downloaded_files.append((filename, path))
        except Exception as e:
            print(f"❌ Failed to download {filename}: {e}")
            return False
    
    print("\n" + "="*60)
    print("✅ All files downloaded successfully!")
    print("="*60)
    print("\nDownloaded files:")
    for filename, path in downloaded_files:
        print(f"  • {filename}")
    print("\nModel ready to use!")
    return True

if __name__ == "__main__":
    success = download_stt_model()
    exit(0 if success else 1)
