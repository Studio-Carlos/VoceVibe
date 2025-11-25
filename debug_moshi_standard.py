#!/usr/bin/env python3
"""
Debug script for Moshi MLX transcription using the official implementation pattern.
This script prints ONLY transcription tokens (user speech), not AI responses.
Based on moshi_mlx.local reference implementation.
"""

import queue
import time
from typing import Optional

import numpy as np
import sounddevice as sd
import sentencepiece
import rustymimi
import mlx.core as mx
import mlx.nn as nn
from huggingface_hub import hf_hub_download
from moshi_mlx import models, utils

# Constants from moshi_mlx.local
SAMPLE_RATE = 24000
CHANNELS = 1
BLOCKSIZE = 1920  # 80 ms @ 24 kHz (Mimi framerate)

# Model configuration
HF_REPO = "kyutai/moshika-mlx-q4"  # Using Moshika (female voice, more stable)
QUANTIZED = 4


def load_model():
    """Load Moshika model following the official pattern."""
    print(f"[LOADING] Loading Moshika MLX model from {HF_REPO}...")
    
    # Download model files
    model_file = hf_hub_download(HF_REPO, "model.q4.safetensors")
    tokenizer_file = hf_hub_download(HF_REPO, "tokenizer_spm_32k_3.model")
    mimi_file = hf_hub_download(HF_REPO, "tokenizer-e351c8d8-checkpoint125.safetensors")
    
    print("[LOADING] Initializing tokenizers...")
    text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_file)  # type: ignore
    audio_tokenizer = rustymimi.StreamTokenizer(mimi_file)  # type: ignore
    
    print("[LOADING] Initializing language model...")
    mx.random.seed(299792458)
    lm_config = models.config_v0_1()
    lm = models.Lm(lm_config)
    lm.set_dtype(mx.bfloat16)
    
    # Quantize model
    group_size = 32
    nn.quantize(lm, bits=QUANTIZED, group_size=group_size)
    print(f"[LOADING] Quantized model to q{QUANTIZED} (group={group_size})")
    
    print("[LOADING] Loading weights...")
    lm.load_weights(model_file, strict=True)
    lm.warmup()
    print("[LOADING] Model warmed up")
    
    # Initialize generator with strict sampling (low temperature to prevent hallucinations)
    gen = models.LmGen(
        model=lm,
        max_steps=4000 + 5,
        text_sampler=utils.Sampler(temp=0.1, top_p=0.9),  # Strict sampling
        audio_sampler=utils.Sampler(temp=0.1, top_p=0.9),
        check=False,
    )
    
    print("[LOADING] ✅ Model ready!")
    return text_tokenizer, audio_tokenizer, gen


def main():
    """Main transcription loop."""
    print("=" * 60)
    print("🎤 Moshi MLX Transcription Debug (Standard Implementation)")
    print("=" * 60)
    print(f"Model: {HF_REPO}")
    print(f"Sample Rate: {SAMPLE_RATE} Hz")
    print(f"Block Size: {BLOCKSIZE} samples (80 ms)")
    print("=" * 60)
    print()
    
    # Load model
    text_tokenizer, audio_tokenizer, gen = load_model()
    
    # Audio input queue
    audio_queue = queue.Queue()
    
    # Audio callback (producer)
    def audio_callback(indata, frames, time_info, status):
        """Capture audio and put it in the queue."""
        if status:
            print(f"[AUDIO] Status: {status}")
        # Convert to mono if needed
        if indata.shape[1] > 1:
            mono = np.mean(indata, axis=1, dtype=np.float32)
        else:
            mono = indata[:, 0].astype(np.float32)
        try:
            audio_queue.put_nowait(mono.copy())
        except queue.Full:
            # Drop oldest if queue is full
            try:
                audio_queue.get_nowait()
                audio_queue.put_nowait(mono.copy())
            except queue.Empty:
                pass
    
    print("[STARTING] Starting audio stream...")
    print("[INFO] Speak now! Transcription will appear below.")
    print("-" * 60)
    
    # Start audio stream
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        blocksize=BLOCKSIZE,
        callback=audio_callback,
        dtype=np.float32,
    )
    
    stream.start()
    
    try:
        # Main processing loop (consumer)
        while True:
            try:
                # Get audio chunk from queue
                pcm_data = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            # Encode audio with Mimi
            audio_tokenizer.encode(pcm_data)
            
            # Get encoded audio tokens
            encoded_data = audio_tokenizer.get_encoded()
            if encoded_data is None:
                continue
            
            # Convert to MLX array and transpose (as in official implementation)
            # Shape: [batch, codebooks, time] -> transpose to [codebooks, batch, time]
            data = mx.array(encoded_data).transpose(1, 0)[:, :8]
            
            # Step through model
            text_token = gen.step(data)
            
            if text_token is None:
                continue
            
            text_token_id = int(text_token[0].item())
            
            # CRITICAL: Filter tokens - only keep transcription tokens
            # Tokens 0 and 3 are special tokens (padding, etc.) - ignore them
            # This is the key to avoiding AI response tokens
            if text_token_id not in (0, 3):
                # Decode token to text piece
                text_piece = text_tokenizer.id_to_piece(text_token_id)  # type: ignore
                # Replace sentencepiece space marker with actual space
                text_piece = text_piece.replace("▁", " ")
                cleaned = text_piece.strip()
                
                # Only print non-empty text
                if cleaned:
                    print(cleaned, end="", flush=True)
            
            # Note: We ignore audio_tokens (gen.last_audio_tokens()) 
            # because we only want transcription, not AI voice output
            
    except KeyboardInterrupt:
        print("\n\n[STOPPING] Interrupted by user")
    finally:
        stream.stop()
        stream.close()
        print("\n[STOPPED] Audio stream closed")


if __name__ == "__main__":
    main()


