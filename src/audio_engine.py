"""
Audio engine powered by Kyutai STT (PyTorch CPU).
Dedicated STT model for pure transcription without AI responses.
Uses CPU to avoid MPS compatibility issues with Moshi operations.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import sentencepiece
import torch
import json
from huggingface_hub import hf_hub_download
from moshi.models import loaders, lm as moshi_lm

from src.config import get_config

# Constants
SAMPLE_RATE = 24000
CHANNELS = 1
BLOCKSIZE =1920  # 80 ms @ 24 kHz 
GATE_THRESHOLD = 0.04  # Hard noise gate threshold


class AudioEngine(threading.Thread):
    """
    Thread that performs Kyutai STT streaming transcription.
    Uses PyTorch on CPU for stable inference (avoiding MPS issues).
    """

    def __init__(
        self,
        text_queue: Optional[queue.Queue] = None,
        transcription_callback: Optional[Callable[[str], None]] = None,
        audio_level_callback: Optional[Callable[[float], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(daemon=True)
        self.config = get_config()
        self.text_queue = text_queue or queue.Queue()
        self.transcription_callback = transcription_callback
        self.audio_level_callback = audio_level_callback
        self.log_callback = log_callback

        self._running = False
        self._stop_event = threading.Event()
        self._stream: Optional[sd.InputStream] = None
        self.audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=64)

        # PyTorch STT components
        self.device = torch.device("cpu")  # Force CPU (MPS has issues)
        self.model = None
        self.mimi = None
        self.text_tokenizer: Optional[sentencepiece.SentencePieceProcessor] = None
        self.lm_gen = None
        self._model_loaded = False

        # Audio processing
        self._silence_counter = 0
        self._silence_warning_every = 50

    # --------------------------------------------------------------------- #
    # Utility helpers                                                       #
    # --------------------------------------------------------------------- #

    def _log(self, message: str):
        """Log a message via callback if available."""
        full = f"[AudioEngine] {message}"
        if self.log_callback:
            try:
                self.log_callback(full)
                return
            except Exception:
                pass
        print(full)

    # --------------------------------------------------------------------- #
    # Model loading (PyTorch STT)                                          #
    # --------------------------------------------------------------------- #

    def _load_stt_model(self):
        """Load Kyutai STT model using moshi loaders correctly."""
        self._log("📥 Loading Kyutai STT Model (PyTorch, CPU, temp=0.0)")
        
        try:
            # Download model files
            model_path = hf_hub_download("kyutai/stt-1b-en_fr", "model.safetensors")
            config_path = hf_hub_download("kyutai/stt-1b-en_fr", "config.json")
            tokenizer_path = hf_hub_download("kyutai/stt-1b-en_fr", "tokenizer_en_fr_audio_8000.model")
            mimi_path = hf_hub_download("kyutai/stt-1b-en_fr", "mimi-pytorch-e351c8d8@125.safetensors")
            
            self._log(f"📦 Model files located in HF cache")
            
            # Load config
            self._log("🔧 Loading model configuration...")
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            
            # Filter config to remove metadata keys that cause TypeError
            keys_to_remove = [
                "model_id", "lm_gen_config", "stt_config", "model_type", 
                "mimi_name", "tokenizer_name", "quantization_config"
            ]
            for key in keys_to_remove:
                if key in config_dict:
                    del config_dict[key]

            # Load LM using loaders (passing filtered config as lm_kwargs)
            self._log("🏗️  Loading STT model...")
            self.model = loaders.get_moshi_lm(
                filename=model_path,
                lm_kwargs=config_dict,
                device=self.device
            )
            self.model.eval()

            # Load Mimi audio encoder
            self._log("🎧 Loading Mimi audio encoder...")
            self.mimi = loaders.get_mimi(
                filename=mimi_path,
                device=self.device,
                num_codebooks=32  # STT model expects 32 codebooks (n_q=32 in config)
            )
            self.mimi.eval()
            
            # Initialize tokenizer
            self._log("📝 Loading tokenizer...")
            self.text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_path)  # type: ignore
            
            # Create streaming generator with temp=0 (DETERMINISTIC)
            self._log("🎯 Creating streaming generator (temp=0.0)...")
            self.lm_gen = moshi_lm.LMGen(
                lm_model=self.model,
                temp=0.0,
                temp_text=0.0,
                top_k=1,      # Deterministic
                top_k_text=1, # Deterministic
                check=False
            )
            
            self._model_loaded = True
            self._log("✅ STT Model loaded successfully (CPU, temp=0.0, NO hallucinations)")
            
        except Exception as exc:
            self._log(f"❌ Failed to load STT model: {exc}")
            import traceback
            traceback.print_exc()
            raise

    # --------------------------------------------------------------------- #
    # Audio processing                                                      #
    # --------------------------------------------------------------------- #

    def _handle_text_token(self, token_id: int):
        """
        Handle text token output.
        Filter special tokens to avoid noise.
        """
        # Filter special tokens (0 and 3) - padding/special tokens
        if token_id in (0, 3):
            return

        if not self.text_tokenizer:
            return

        # Decode token to text piece
        text_piece = self.text_tokenizer.id_to_piece(token_id)  # type: ignore
        # Replace sentencepiece space marker with actual space
        text_piece = text_piece.replace("▁", " ")
        cleaned = text_piece.strip()

        if not cleaned:
            return

        # Log transcription
        self._log(f"📝 STT: '{cleaned}'")

        # Add to text queue
        try:
            self.text_queue.put_nowait(cleaned)
        except queue.Full:
            # Drop oldest if queue is full
            try:
                self.text_queue.get_nowait()
                self.text_queue.put_nowait(cleaned)
            except queue.Empty:
                pass

        # Call transcription callback
        if self.transcription_callback:
            try:
                self.transcription_callback(cleaned)
            except Exception as exc:
                self._log(f"Callback error: {exc}")

    def _process_audio_chunk(self, pcm_data: np.ndarray):
        """
        Process audio chunk with PyTorch STT model.
        """
        if not self._model_loaded or not self.lm_gen:
            return

        try:
            # Convert to torch tensor AND reshape for (Batch, Channels, Time)
            # Shape must be (1, 1, 1920) for streaming generator
            audio_tensor = torch.from_numpy(pcm_data).to(self.device).unsqueeze(0).unsqueeze(0)
            
            # Encode audio with Mimi
            with torch.no_grad():
                codes = self.mimi.encode(audio_tensor)
                
            # LMGen step (handles its own gradient context)
            text_token = self.lm_gen.step(codes)
            
            if text_token is None:
                return
            
            # Extract token ID
            # text_token is likely a tensor.
            # If it's the text stream token.
            text_token_id = int(text_token.item())
            
            # Handle text token
            self._handle_text_token(text_token_id)
            
        except Exception as exc:
            self._log(f"❌ Error processing audio chunk: {exc}")
            import traceback
            traceback.print_exc()

    def _audio_callback(self, indata, frames, time_info, status):
        """
        Audio callback (producer) - ultra-lightweight, just queues audio.
        """
        if status:
            self._log(f"Audio status: {status}")
        if not self._running or not self._model_loaded:
            return

        try:
            self.audio_queue.put_nowait(indata.copy())
        except queue.Full:
            # Drop oldest if queue is full
            try:
                _ = self.audio_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.audio_queue.put_nowait(indata.copy())
            except queue.Full:
                pass

    # --------------------------------------------------------------------- #
    # Thread lifecycle                                                      #
    # --------------------------------------------------------------------- #

    def run(self):
        """Main thread loop."""
        self._log("🚀 AudioEngine thread starting (PyTorch STT backend)")
        
        # Load model if not loaded
        if not self._model_loaded:
            try:
                self._load_stt_model()
            except Exception as e:
                self._log(f"❌ Failed to load STT model: {e}")
                return

        self._running = True
        self._stop_event.clear()

        # Get input device
        input_device = self.config.audio_device
        if input_device is None:
            default = sd.default.device
            if isinstance(default, (list, tuple)) and default:
                input_device = default[0]

        self._log(f"🔊 Starting audio stream on device {input_device} ({SAMPLE_RATE} Hz)")

        try:
            # Start audio stream
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                blocksize=BLOCKSIZE,
                callback=self._audio_callback,
                dtype=np.float32,
                device=input_device,
            )
            self._stream.start()
            self._log("🎤 MICROPHONE ACTIVE - speak now")

            # Enter streaming context (maintains state across chunks)
            if self.lm_gen:
                with self.lm_gen.streaming(batch_size=1):
                    while self._running and not self._stop_event.is_set():
                        try:
                            # Get audio chunk from queue
                            chunk = self.audio_queue.get(timeout=0.1)
                        except queue.Empty:
                            continue

                        # Convert to mono if needed
                        if chunk.shape[1] > 1:
                            mono = np.mean(chunk, axis=1, dtype=np.float32)
                        else:
                            mono = chunk[:, 0].astype(np.float32)

                        # Calculate audio level for UI callback
                        level = float(np.abs(mono).max())
                        if self.audio_level_callback:
                            try:
                                self.audio_level_callback(level)
                            except Exception:
                                pass

                        # AGC (Auto Gain Control)
                        if level > 0.001:
                            target_level = 0.95
                            gain = target_level / (level + 1e-6)
                            gain = min(gain, 8.0)
                            mono = mono * gain
                            mono = np.clip(mono, -1.0, 1.0)

                        # Hard noise gate
                        if level < GATE_THRESHOLD:
                            continue

                        # Process audio chunk
                        self._process_audio_chunk(mono)
            else:
                 self._log("❌ LMGen not initialized")

        except Exception as exc:
            self._log(f"❌ CRITICAL audio stream error: {exc}")
            import traceback
            traceback.print_exc()
        finally:
            self._cleanup()

    def _cleanup(self):
        """Clean up resources."""
        self._running = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:
                self._log(f"Error closing stream: {exc}")
            finally:
                self._stream = None

        self._log("🛑 AudioEngine stopped")

    def stop(self):
        """Stop the audio engine gracefully."""
        self._log("Stopping AudioEngine…")
        self._running = False
        self._stop_event.set()
        self.join(timeout=2.0)

    def is_running(self) -> bool:
        """Check if the engine is running."""
        return self._running

    def get_text_queue(self) -> queue.Queue:
        """Get the text queue for external access."""
        return self.text_queue
