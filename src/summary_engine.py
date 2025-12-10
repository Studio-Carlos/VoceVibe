"""
Summary Engine (Slow Brain) for VoiceVibe.
Accumulates the entire conversation history and generates:
1. Text summaries every 30s.
2. Complex visual prompts every 60s.
"""

import threading
import time
import queue
import requests
from typing import Optional, List, Callable

from src.config import get_config
from src.osc_client import OSCClient


class SummaryEngine(threading.Thread):
    """
    Slow Brain engine that processes the full conversation history.
    """

    def __init__(
        self,
        summary_queue: queue.Queue,
        osc_client: Optional[OSCClient] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        text_callback: Optional[Callable[[str], None]] = None,
        visual_callback: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(daemon=True)
        self.config = get_config()
        self.summary_queue = summary_queue
        self.osc_client = osc_client
        self.log_callback = log_callback
        self.text_callback = text_callback
        self.visual_callback = visual_callback

        self._running = False
        self._stop_event = threading.Event()
        
        # State
        self.full_transcript: List[str] = []
        self.last_summary_time = time.time()
        self.last_visual_time = time.time()
        
        # Constants
        self.SUMMARY_INTERVAL = 30.0  # seconds
        self.VISUAL_INTERVAL = 60.0   # seconds

    def _log(self, message: str):
        """Log message."""
        full_msg = f"[SummaryEngine] {message}"
        if self.log_callback:
            try:
                self.log_callback(full_msg)
            except:
                pass
        else:
            print(full_msg)

    def run(self):
        """Main loop."""
        self._log("🐢 SummaryEngine (Slow Brain) started")
        self._running = True
        self._stop_event.clear()
        
        while self._running and not self._stop_event.is_set():
            # 1. Consume queue (non-blocking to allow timer checks)
            try:
                while True:
                    word = self.summary_queue.get_nowait()
                    self.full_transcript.append(word)
            except queue.Empty:
                pass
            
            # 2. Check Timers
            now = time.time()
            
            # Task A: Text Summary (30s)
            if now - self.last_summary_time >= self.SUMMARY_INTERVAL:
                if self.full_transcript:
                    self._generate_text_summary()
                self.last_summary_time = now
                
            # Task B: Visual Prompt (60s)
            if now - self.last_visual_time >= self.VISUAL_INTERVAL:
                if self.full_transcript:
                    self._generate_visual_summary()
                self.last_visual_time = now
            
            # Sleep briefly to prevent CPU hogging
            time.sleep(0.1)
            
        self._log("🛑 SummaryEngine stopped")

    def _generate_text_summary(self):
        """Generate text summary using Ollama."""
        full_text = " ".join(self.full_transcript)
        if not full_text.strip():
            return
            
        # Truncate to last 15000 chars to prevent context overflow/timeouts
        if len(full_text) > 15000:
            full_text = full_text[-15000:]
            
        if self._stop_event.is_set(): return

        self._log("📝 Generating text summary...")
        
        try:
            # Run in a separate thread to avoid blocking the queue consumer?
            # For simplicity in this version, we block briefly. 
            # Ideally, we should offload this if it takes too long.
            # But since this is the "Slow Brain", blocking for 1-2s is acceptable 
            # as long as the queue doesn't overflow (it's infinite by default).
            
            if self._stop_event.is_set(): return

            response = self._call_ollama(
                system_prompt=self.config.summary_text_system_prompt,
                user_prompt=f"TRANSCRIPT:\n{full_text}"
            )
            
            if self._stop_event.is_set(): return
            
            if response:
                self._log("✅ Summary generated")
                # Send via OSC
                if self.osc_client:
                    self.osc_client.send_message("/summary/text", response)
                # Update UI
                if self.text_callback:
                    self.text_callback(response)
                    
        except Exception as e:
            self._log(f"❌ Text summary failed: {e}")

    def _generate_visual_summary(self):
        """Generate complex visual prompt using Ollama."""
        full_text = " ".join(self.full_transcript)
        if not full_text.strip():
            return

        # Truncate to last 15000 chars
        if len(full_text) > 15000:
            full_text = "... " + full_text[-15000:]

        self._log("🎨 Generating visual summary prompt...")
        
        if self._stop_event.is_set(): return

        try:
            response = self._call_ollama(
                system_prompt=self.config.summary_visual_system_prompt,
                user_prompt=f"TRANSCRIPT:\n{full_text}"
            )
            
            if self._stop_event.is_set(): return
            
            if response:
                self._log("✅ Visual prompt generated")
                # Send via OSC
                if self.osc_client:
                    self.osc_client.send_message("/summary/image_prompt", response)
                # Update UI
                if self.visual_callback:
                    self.visual_callback(response)
                    
        except Exception as e:
            self._log(f"❌ Visual summary failed: {e}")

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Helper to call Ollama API."""
        url = f"{self.config.ollama_base_url}/api/generate"
        payload = {
            "model": self.config.ollama_model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 32768  # Large context for full history
            }
        }
        
        try:
            res = requests.post(url, json=payload, timeout=120)
            if res.status_code == 200:
                return res.json().get("response", "").strip()
            else:
                self._log(f"Ollama error: {res.status_code} - {res.text}")
                return None
        except Exception as e:
            self._log(f"Ollama connection failed: {e}")
            return None

    def reset_memory(self):
        """Clear the accumulated transcript."""
        self.full_transcript = []
        self._log("🧹 Memory wiped")

    def get_state(self) -> dict:
        """Get state for pausing."""
        return {
            "full_transcript": list(self.full_transcript)
        }

    def set_state(self, state: dict):
        """Restore state from pause."""
        if not state: return
        self.full_transcript = state.get("full_transcript", [])
        self._log("🐢 Summary history restored from pause")

    def stop(self):
        """Stop the engine."""
        self._running = False
        self._stop_event.set()
        self.join(timeout=2.0)
