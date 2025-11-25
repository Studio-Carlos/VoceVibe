"""
Brain engine for analyzing transcribed text and generating visual prompts.
Runs in a separate thread, analyzes text periodically, and sends OSC messages.

Features:
- Accumulates text until a phrase is complete or ~5 seconds elapsed
- Maintains a sliding window buffer of last 60 seconds for context
- Uses strict JSON format for Ollama responses
"""
import threading
import time
import json
from typing import Optional, List, Tuple
from collections import deque
import ollama
from src.config import get_config
from src.osc_client import OSCClient


class BrainEngine(threading.Thread):
    """
    Thread that analyzes transcribed text and generates visual prompts via LLM.
    
    Accumulates text chunks and analyzes them periodically (every ~5 seconds or when a phrase is complete).
    Maintains a 60-second sliding window buffer for context.
    """
    
    def __init__(self, text_queue, osc_client: OSCClient, log_callback: Optional[callable] = None, prompt_callback: Optional[callable] = None):
        """
        Initialize the brain engine.
        
        Args:
            text_queue: Queue.Queue containing transcribed text chunks
            osc_client: OSCClient instance for sending prompts
            log_callback: Optional callback for logging messages
            prompt_callback: Optional callback called with prompt_data dict when prompt is generated
        """
        super().__init__(daemon=True)
        self.config = get_config()
        self.text_queue = text_queue
        self.osc_client = osc_client
        self.log_callback = log_callback
        self.prompt_callback = prompt_callback
        
        # Control flags
        self._running = False
        self._stop_event = threading.Event()
        
        # Text buffer with timestamps for sliding window (60 seconds)
        # Format: deque of (timestamp, text) tuples
        self._text_buffer: deque = deque(maxlen=1000)  # Max 1000 entries (should be enough for 60s)
        self._buffer_lock = threading.Lock()
        
        # Accumulation buffer for current analysis cycle
        self._accumulation_buffer: List[str] = []
        self._accumulation_start_time: Optional[float] = None
        self._accumulation_lock = threading.Lock()
        
        # Configuration
        self._accumulation_timeout = 7.5  # seconds - analyze if no new text for this long (target: 5-10s interval)
        self._context_window_seconds = 30.0  # Keep last 30 seconds of context (rolling window)
        self._min_char_threshold = 15  # Minimum characters before analyzing (prevents noisy triggers on short fragments)
    
    def _log(self, message: str):
        """Log a message via callback if available."""
        if self.log_callback:
            try:
                self.log_callback(message)
            except Exception as e:
                print(f"[BrainEngine] Log callback error: {e}")
        else:
            print(f"[BrainEngine] {message}")
    
    def _add_to_buffer(self, text: str):
        """
        Add text to the sliding window buffer with timestamp.
        
        Args:
            text: Text chunk to add
        """
        current_time = time.time()
        with self._buffer_lock:
            self._text_buffer.append((current_time, text))
    
    def _get_context_window(self) -> str:
        """
        Get text from the last 30 seconds (sliding window).
        
        Returns:
            Concatenated text from the context window
        """
        current_time = time.time()
        cutoff_time = current_time - self._context_window_seconds
        
        with self._buffer_lock:
            # Filter entries within the time window
            recent_texts = [
                text for timestamp, text in self._text_buffer
                if timestamp >= cutoff_time
            ]
        
        return " ".join(recent_texts)
    
    def _collect_recent_text(self) -> Tuple[str, bool]:
        """
        Collect recent text from queue and accumulation buffer.
        
        Returns:
            Tuple of (text_to_analyze, should_analyze_now)
            should_analyze_now is True if we should analyze (phrase complete or timeout)
        """
        current_time = time.time()
        should_analyze = False
        
        # Collect new text from queue
        new_texts = []
        while True:
            try:
                text = self.text_queue.get_nowait()
                new_texts.append(text)
                # Add to sliding window buffer
                self._add_to_buffer(text)
            except:
                break
        
        with self._accumulation_lock:
            # Add new texts to accumulation buffer
            if new_texts:
                self._accumulation_buffer.extend(new_texts)
                if self._accumulation_start_time is None:
                    self._accumulation_start_time = current_time
            
            # Check if we should analyze:
            # 1. Timeout reached (no new text for accumulation_timeout seconds) - ALWAYS analyze
            # 2. Phrase seems complete (ends with punctuation) AND has minimum length
            # 3. Text length exceeds minimum threshold (even without punctuation)
            if self._accumulation_buffer:
                accumulated_text = " ".join(self._accumulation_buffer)
                current_length = len(accumulated_text)
                
                # Check timeout (always analyze if timeout reached, regardless of length)
                if self._accumulation_start_time is not None:
                    elapsed = current_time - self._accumulation_start_time
                    if elapsed >= self._accumulation_timeout:
                        should_analyze = True
                
                # Check punctuation and length (only if not already triggered by timeout)
                if not should_analyze:
                    # Check if last text ends with sentence-ending punctuation
                    is_complete_sentence = False
                    if self._accumulation_buffer:
                        last_text = self._accumulation_buffer[-1].strip()
                        if last_text and last_text[-1] in '.!?':
                            is_complete_sentence = True
                    
                    # Check length threshold
                    is_long_enough = current_length >= self._min_char_threshold
                    
                    # Analyze if: complete sentence OR long enough (both require minimum length)
                    # This prevents triggering on single words like "Le" or "The"
                    if is_long_enough:
                        should_analyze = True
                
                if should_analyze:
                    # Reset accumulation buffer
                    self._accumulation_buffer = []
                    self._accumulation_start_time = None
                    return accumulated_text, True
                else:
                    return accumulated_text, False
        
        return "", False
    
    def _check_ollama_model(self):
        """Check if Ollama model is available on disk and in memory."""
        import subprocess
        import json
        
        try:
            # Check if model is in Ollama's model list
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            model_name = self.config.ollama_model
            if model_name in result.stdout:
                print(f"[BrainEngine] ✅ LLM Model '{model_name}' found in Ollama")
                
                # Try to get model info
                try:
                    info_result = subprocess.run(
                        ['ollama', 'show', model_name, '--json'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if info_result.returncode == 0:
                        info = json.loads(info_result.stdout)
                        size = info.get('size', 0)
                        if size:
                            size_gb = size / (1024**3)
                            print(f"[BrainEngine] 📦 Model size on disk: {size_gb:.2f} GB")
                except:
                    pass
                
                print(f"[BrainEngine] 🧠 Model will be loaded in RAM when first used")
                return True
            else:
                print(f"[BrainEngine] ⚠️  LLM Model '{model_name}' NOT found in Ollama")
                print(f"[BrainEngine] 📥 Run: ollama pull {model_name}")
                return False
        except Exception as e:
            print(f"[BrainEngine] ⚠️  Could not check Ollama model: {e}")
            return False
    
    def _analyze_with_ollama(self, text: str) -> Optional[dict]:
        """
        Analyze text using Ollama LLM and generate visual prompt.
        Uses strict JSON format and context window.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with prompt, style, mood, or None if error
        """
        if not text or not text.strip():
            return None
        
        try:
            # Get context window (last 30 seconds)
            context_text = self._get_context_window()
            
            self._log(f"Analyzing text ({len(text)} chars, context: {len(context_text)} chars)...")
            
            # Prepare the user prompt with context (optimized for Mistral NeMo)
            if context_text and context_text != text:
                user_prompt = f"""Contexte récent (dernières 30 secondes):
{context_text}

Texte actuel à analyser:
{text}

Génère un prompt visuel JSON pour SDXL basé sur ce texte. Réponds UNIQUEMENT avec un objet JSON valide contenant les clés: prompt, style, mood. Pas de texte supplémentaire."""
            else:
                user_prompt = f"""Analyse ce texte transcrit en temps réel et génère un prompt visuel:

{text}

Génère UNIQUEMENT un objet JSON valide avec les clés: prompt, style, mood. Réponds uniquement avec le JSON, rien d'autre."""
            
            # Call Ollama with strict JSON format
            self._log(f"🤖 Calling LLM ({self.config.ollama_model})...")
            llm_start_time = time.time()
            
            response = ollama.chat(
                model=self.config.ollama_model,
                messages=[
                    {
                        'role': 'system',
                        'content': self.config.system_prompt
                    },
                    {
                        'role': 'user',
                        'content': user_prompt
                    }
                ],
                format='json',  # Force JSON output
                options={
                    'num_ctx': 4096  # Context window size
                }
            )
            
            llm_response_time = time.time() - llm_start_time
            self._log(f"⏱️  LLM response time: {llm_response_time:.2f}s")
            
            content = response.get("message", {}).get("content", "")
            
            # Parse JSON (should be clean JSON due to format='json')
            content = content.strip()
            
            # Remove markdown code blocks if present (shouldn't be with format='json', but just in case)
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()
            
            # Parse JSON
            try:
                prompt_data = json.loads(content)
                
                # Validate structure
                if not isinstance(prompt_data, dict):
                    raise ValueError("Response is not a dictionary")
                
                # Ensure required keys exist
                if "prompt" not in prompt_data:
                    prompt_data["prompt"] = text[:100]  # Fallback
                if "style" not in prompt_data:
                    prompt_data["style"] = "abstract"
                if "mood" not in prompt_data:
                    prompt_data["mood"] = "dynamic"
                
                prompt_text = prompt_data.get('prompt', '')[:50]
                self._log(f"✅ Generated prompt: '{prompt_text}...'")
                self._log(f"   Style: {prompt_data.get('style', 'N/A')} | Mood: {prompt_data.get('mood', 'N/A')}")
                return prompt_data
                
            except json.JSONDecodeError as e:
                self._log(f"Failed to parse JSON from Ollama response: {e}")
                self._log(f"Response content: {content[:200]}")
                
                # Fallback: create a simple prompt from the text
                return {
                    "prompt": text[:200],
                    "style": "abstract",
                    "mood": "dynamic"
                }
            
        except Exception as e:
            self._log(f"Error calling Ollama: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run(self):
        """Main thread loop: analyze text periodically and send OSC."""
        self._running = True
        self._stop_event.clear()
        
        print("[BrainEngine] " + "="*60)
        print("[BrainEngine] 🔄 Starting Brain Engine (LLM)...")
        print(f"[BrainEngine] Model: {self.config.ollama_model}")
        
        # Check if Ollama model is available
        self._check_ollama_model()
        
        self._log("Brain engine started")
        print("[BrainEngine] " + "="*60)
        
        last_analysis_time = time.time()
        
        try:
            while self._running and not self._stop_event.is_set():
                current_time = time.time()
                
                # Collect recent text and check if we should analyze
                recent_text, should_analyze = self._collect_recent_text()
                
                # Analyze if:
                # 1. We have text and should analyze (phrase complete or timeout)
                # 2. OR interval has elapsed (fallback periodic analysis)
                interval_elapsed = current_time - last_analysis_time >= self.config.brain_analysis_interval
                
                if recent_text.strip() and (should_analyze or interval_elapsed):
                    # Analyze with Ollama
                    prompt_data = self._analyze_with_ollama(recent_text)
                    
                    if prompt_data:
                        # Send via OSC
                        self.osc_client.send_json_prompt(prompt_data)
                        self._log(f"Sent OSC prompt: {prompt_data.get('prompt', '')[:50]}...")
                        
                        # Call prompt callback if provided
                        if self.prompt_callback:
                            try:
                                self.prompt_callback(prompt_data)
                            except Exception as e:
                                self._log(f"Error in prompt callback: {e}")
                    
                    last_analysis_time = current_time
                
                # Sleep a bit to avoid busy-waiting
                time.sleep(0.1)  # Check more frequently for better responsiveness
        
        except Exception as e:
            self._log(f"Error in brain engine: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._log("Brain engine stopped")
    
    def stop(self):
        """Stop the brain engine gracefully."""
        self._log("Stopping brain engine...")
        self._running = False
        self._stop_event.set()
        
        # Analyze any remaining accumulated text before stopping
        with self._accumulation_lock:
            if self._accumulation_buffer:
                remaining_text = " ".join(self._accumulation_buffer)
                if remaining_text.strip():
                    prompt_data = self._analyze_with_ollama(remaining_text)
                    if prompt_data:
                        self.osc_client.send_json_prompt(prompt_data)
                        if self.prompt_callback:
                            try:
                                self.prompt_callback(prompt_data)
                            except Exception as e:
                                pass
        
        # Wait for thread to finish
        self.join(timeout=2.0)
    
    def is_running(self) -> bool:
        """Check if the engine is running."""
        return self._running
