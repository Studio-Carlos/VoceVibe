"""
Audio engine powered by Moshika MLX (Apple Silicon optimized).
Uses the official moshi_mlx.local implementation pattern for stable transcription.
Captures microphone audio, encodes it with Mimi (rustymimi), feeds Moshika LM,
and streams decoded text back to the UI/Brain engine.

Based on the reference implementation in moshi_mlx.local.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Optional, Tuple

import numpy as np
import sounddevice as sd
import sentencepiece
import rustymimi
import mlx.core as mx
import mlx.nn as nn
from huggingface_hub import hf_hub_download
from moshi_mlx import models, utils

from src.config import get_config

# Constants from moshi_mlx.local (official implementation)
SAMPLE_RATE = 24000
CHANNELS = 1
BLOCKSIZE = 1920  # 80 ms @ 24 kHz (Mimi framerate requirement)
GATE_THRESHOLD = 0.04  # Hard noise gate threshold - ignore audio below this level


class AudioEngine(threading.Thread):
    """
    Thread that performs Moshika MLX streaming STT.
    Uses the official moshi_mlx.local implementation pattern for stability.
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

        # Moshika MLX components (following official pattern)
        self.audio_tokenizer: Optional[rustymimi.StreamTokenizer] = None
        self.text_tokenizer: Optional[sentencepiece.SentencePieceProcessor] = None
        self.lm: Optional[models.Lm] = None
        self.gen: Optional[models.LmGen] = None
        self._moshi_loaded = False

        # Audio processing
        self._silence_counter = 0
        self._silence_warning_every = 50

        self.quantization_bits = self._sanitize_quantization(
            self.config.moshi_quantization
        )

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

    @staticmethod
    def _sanitize_quantization(value: int) -> int:
        """Sanitize quantization value to 4 or 8."""
        return 4 if value not in (4, 8) else value

    def _resolve_repo(self) -> Tuple[str, str]:
        """Resolve HuggingFace repo and model file based on quantization."""
        if self.quantization_bits == 8:
            return "kyutai/moshika-mlx-q8", "model.q8.safetensors"
        if self.quantization_bits == 4:
            return "kyutai/moshika-mlx-q4", "model.q4.safetensors"
        return "kyutai/moshika-mlx-bf16", "model.safetensors"

    # --------------------------------------------------------------------- #
    # Model loading (following official moshi_mlx.local pattern)            #
    # --------------------------------------------------------------------- #

    def _load_moshi_model(self):
        """Load Moshika model following the official moshi_mlx.local pattern."""
        repo, weight_file = self._resolve_repo()
        self._log(
            f"📥 Loading Moshika MLX (repo={repo}, quantization=q{self.quantization_bits})"
        )

        # Download model files (following official pattern)
        model_path = hf_hub_download(repo, weight_file)
        tokenizer_path = hf_hub_download(repo, "tokenizer_spm_32k_3.model")
        mimi_path = hf_hub_download(repo, "tokenizer-e351c8d8-checkpoint125.safetensors")

        # Initialize tokenizers
        self._log("📥 Initializing tokenizers...")
        self.text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_path)  # type: ignore
        self.audio_tokenizer = rustymimi.StreamTokenizer(mimi_path)  # type: ignore

        # Initialize language model (following official pattern)
        self._log("📥 Initializing language model...")
        mx.random.seed(299792458)  # Same seed as official implementation
        lm_config = models.config_v0_1()
        self.lm = models.Lm(lm_config)
        self.lm.set_dtype(mx.bfloat16)

        # Quantize model if needed
        if self.quantization_bits in (4, 8):
            group_size = 32 if self.quantization_bits == 4 else 64
            nn.quantize(self.lm, bits=self.quantization_bits, group_size=group_size)
            self._log(f"⚙️  Quantized model to q{self.quantization_bits} (group={group_size})")

        # Load weights
        self._log("📦 Loading LM weights...")
        self.lm.load_weights(model_path, strict=True)
        self.lm.warmup()
        self._log("✅ Model warmed up")

        # Initialize generator with strict sampling (following official pattern)
        # Low temperature to prevent hallucinations
        self.gen = models.LmGen(
            model=self.lm,
            max_steps=4000 + 5,
            text_sampler=utils.Sampler(temp=0.1, top_p=0.9),  # Strict sampling
            audio_sampler=utils.Sampler(temp=0.1, top_p=0.9),
            check=False,
        )

        self._moshi_loaded = True
        self._log("✅ Moshika MLX loaded and ready")

    # --------------------------------------------------------------------- #
    # Audio processing (following official pattern)                         #
    # --------------------------------------------------------------------- #

    def _handle_text_token(self, token_id: int):
        """
        Handle text token output.
        CRITICAL: Only process tokens that are NOT 0 or 3 (special tokens).
        This filters out AI response tokens and keeps only transcription.
        """
        # Filter special tokens (0 and 3) - these are padding/special tokens
        # This is the key to avoiding AI response tokens
        if token_id in (0, 3):
            return

        if not self.text_tokenizer:
            return

        # Decode token to text piece (following official pattern)
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
        Process audio chunk following official moshi_mlx.local pattern.
        """
        if not self._moshi_loaded or not self.audio_tokenizer or not self.gen:
            return

        try:
            # Encode audio with Mimi (following official pattern)
            self.audio_tokenizer.encode(pcm_data)

            # Get encoded audio tokens
            encoded_data = self.audio_tokenizer.get_encoded()
            if encoded_data is None:
                return

            # Convert to MLX array and transpose (as in official implementation)
            # Shape: [batch, codebooks, time] -> transpose to [codebooks, batch, time]
            # Take first 8 codebooks (as per official implementation)
            data = mx.array(encoded_data).transpose(1, 0)[:, :8]

            # Step through model (following official pattern)
            text_token = self.gen.step(data)

            if text_token is None:
                return

            # Extract token ID
            text_token_id = int(text_token[0].item())

            # Handle text token (will filter out special tokens 0 and 3)
            self._handle_text_token(text_token_id)

            # Note: We ignore audio_tokens (gen.last_audio_tokens())
            # because we only want transcription, not AI voice output

        except Exception as exc:
            self._log(f"❌ Error processing audio chunk: {exc}")
            import traceback
            traceback.print_exc()

    def _audio_callback(self, indata, frames, time_info, status):
        """
        Audio callback (producer) - ultra-lightweight, just queues audio.
        Following producer-consumer pattern for stability.
        """
        if status:
            self._log(f"Audio status: {status}")
        if not self._running or not self._moshi_loaded:
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
        """Main thread loop following official implementation pattern."""
        self._log("🚀 AudioEngine thread starting (Moshika MLX backend - official pattern)")
        if not self._moshi_loaded:
            self._load_moshi_model()
        if not self._moshi_loaded:
            self._log("❌ Failed to load Moshika MLX – aborting thread")
            return

        self._running = True
        self._stop_event.clear()

        # Get input device
        input_device = self.config.audio_device
        if input_device is None:
            default = sd.default.device
            if isinstance(default, (list, tuple)) and default:
                input_device = default[0]

        self._log(
            f"🔊 Starting audio stream on device "
            f"{input_device if input_device is not None else 'Default'} "
            f"({SAMPLE_RATE} Hz, block={BLOCKSIZE})"
        )

        try:
            # Start audio stream (following official pattern)
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

            # Main processing loop (consumer) - following official pattern
            while self._running and not self._stop_event.is_set():
                try:
                    # Get audio chunk from queue
                    chunk = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if not self._moshi_loaded:
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

                # AGC (Auto Gain Control) - Normalize audio level
                peak = float(np.abs(mono).max())
                if peak > 0.001:  # If not absolute silence
                    # Warn if signal is very weak
                    if peak < 0.05:
                        if not hasattr(self, '_weak_signal_warned') or not self._weak_signal_warned:
                            self._log("⚠️  Signal très faible, montez le volume de la source !")
                            self._weak_signal_warned = True

                    target_level = 0.95  # Target 95% of max volume (aggressive)
                    gain = target_level / (peak + 1e-6)
                    gain = min(gain, 8.0)  # Max gain 8x to avoid boosting noise
                    mono = mono * gain
                    mono = np.clip(mono, -1.0, 1.0)
                else:
                    # Reset warning flag when signal is detected
                    if hasattr(self, '_weak_signal_warned'):
                        self._weak_signal_warned = False

                # Recalculate level after normalization
                level = float(np.abs(mono).max())

                # Hard noise gate: ignore audio below threshold completely
                if level < GATE_THRESHOLD:
                    self._silence_counter += 1
                    if self._silence_counter % (self._silence_warning_every * 10) == 0:
                        self._log(
                            "⚠️  Still no audio detected. Check microphone/permissions."
                        )
                    # CRITICAL: Skip this chunk entirely - don't send to model
                    continue

                # If we reach here, there's actual voice audio
                if self._silence_counter > 0:
                    self._log("✅ Audio detected.")
                self._silence_counter = 0

                # Process audio chunk (following official pattern)
                self._process_audio_chunk(mono)

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
