"""
VoiceVibe4 - Main entry point with customtkinter UI.
Real-time audio transcription and visual performance brain.

Features:
- Real-time STT transcription display (rolling text)
- LLM prompt visualization
- Terminal dashboard with rich
- Cyberpunk-style UI
"""
import customtkinter as ctk
import threading
import queue
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import json
import sounddevice as sd
import logging

# Configure logging to file (overwrite each run) and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("session.log", mode="w"),
        logging.StreamHandler()
    ]
)

# Rich for terminal dashboard
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("[WARNING] rich not available. Install with: pip install rich")

from src.config import get_config
from src.osc_client import OSCClient
from src.audio_engine import AudioEngine
from src.brain_engine import BrainEngine

# Configure customtkinter appearance (Cyberpunk theme)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Cyberpunk colors
CYBERPUNK_BG = "#0a0a0a"
CYBERPUNK_FG = "#00ff41"  # Matrix green
CYBERPUNK_ACCENT = "#ff0080"  # Neon pink
CYBERPUNK_BLUE = "#00d9ff"  # Cyan
CYBERPUNK_CYAN = "#00d9ff"  # Cyan (alias)
CYBERPUNK_PURPLE = "#9d00ff"  # Purple


class TerminalDashboard:
    """Terminal dashboard using rich for real-time monitoring."""
    
    def __init__(self):
        if not RICH_AVAILABLE:
            self.console = None
            return
        
        self.console = Console()
        self.last_stt_text = ""
        self.last_prompt_data: Optional[Dict] = None
        self.status = "STOPPED"
    
    def update_stt(self, text: str):
        """Update STT text in dashboard."""
        if not self.console:
            return
        self.last_stt_text = text
    
    def update_prompt(self, prompt_data: Dict):
        """Update prompt data in dashboard."""
        if not self.console:
            return
        self.last_prompt_data = prompt_data
    
    def update_status(self, status: str):
        """Update status."""
        if not self.console:
            return
        self.status = status
    
    def render(self):
        """Render the dashboard."""
        if not self.console:
            return
        
        try:
            # Create layout
            layout = Layout()
            
            # Header
            header_text = Text("🎤 VoiceVibe4 - Real-Time Dashboard", style="bold cyan")
            layout["header"] = Panel(header_text, box=box.DOUBLE, border_style="cyan")
            
            # STT Section
            stt_content = Text()
            stt_content.append("[AUDIO] ", style="bold blue")
            stt_content.append(self.last_stt_text[:200] or "Waiting for audio...", style="white")
            layout["stt"] = Panel(stt_content, title="[STT] Speech-to-Text", border_style="blue", box=box.ROUNDED)
            
            # Brain Section
            brain_content = Text()
            if self.last_prompt_data:
                brain_content.append("[BRAIN] ", style="bold magenta")
                brain_content.append(f"Prompt: {self.last_prompt_data.get('prompt', 'N/A')[:100]}", style="white")
                brain_content.append("\n", style="white")
            else:
                brain_content.append("[BRAIN] ", style="bold magenta")
                brain_content.append("Waiting for analysis...", style="dim white")
            layout["brain"] = Panel(brain_content, title="[LLM] Visual Prompt", border_style="magenta", box=box.ROUNDED)
            
            # Status Section
            status_style = "green" if self.status == "RUNNING" else "red"
            status_content = Text()
            status_content.append(f"Status: {self.status}", style=f"bold {status_style}")
            layout["status"] = Panel(status_content, border_style=status_style, box=box.ROUNDED)
            
            # Split layout
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="stt", size=5),
                Layout(name="brain", size=5),
                Layout(name="status", size=3),
            )
            
            # Render (don't clear, just print to avoid flickering)
            self.console.print(layout)
        except Exception as e:
            # Fallback if rich rendering fails
            pass


class VoiceVibeApp(ctk.CTk):
    """Main application window with cyberpunk-style UI."""
    
    def __init__(self):
        super().__init__()
        
        self.config = get_config()
        
        # Engines
        self.audio_engine: Optional[AudioEngine] = None
        self.brain_engine: Optional[BrainEngine] = None
        self.osc_client: Optional[OSCClient] = None
        
        # UI state
        self.is_running = False
        
        # Data buffers (thread-safe)
        self.stt_text_buffer = []  # Rolling buffer for STT
        self.last_prompt_data: Optional[Dict] = None
        self.current_audio_level = 0.0
        self.audio_devices: List[Tuple[int, str]] = []
        
        # Terminal dashboard
        self.terminal_dashboard = TerminalDashboard()
        
        # Setup UI
        self._setup_ui()
        
        # Initialize OSC client (not connected yet)
        self._init_osc_client()
        
        # Start terminal dashboard update thread
        self._start_terminal_dashboard()
        
        # Start engine monitor (crash recovery)
        self._start_engine_monitor()
    
    def _setup_ui(self):
        """Setup the cyberpunk-style user interface."""
        self.title("🎤 VoiceVibe4 - Visual Performance Brain")
        self.title("🎤 VoiceVibe4 - Visual Performance Brain")
        
        # Maximize window on startup
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Configure window background
        self.configure(bg=CYBERPUNK_BG)
        
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color=CYBERPUNK_BG)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title with cyberpunk style
        title_label = ctk.CTkLabel(
            main_frame,
            text="VOICEVIBE4",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=CYBERPUNK_CYAN,
        )
        title_label.pack(pady=(10, 5))
        
        subtitle_label = ctk.CTkLabel(
            main_frame,
            text="Real-Time Audio → Visual Performance Brain",
            font=ctk.CTkFont(size=12),
            text_color=CYBERPUNK_FG,
        )
        subtitle_label.pack(pady=(0, 20))
        
        # STT Transcription Zone (Rolling Text)
        stt_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a", corner_radius=10)
        stt_frame.pack(fill="x", padx=10, pady=10)
        
        stt_label = ctk.CTkLabel(
            stt_frame,
            text="[STT] Speech Transcription",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=CYBERPUNK_BLUE,
        )
        stt_label.pack(pady=(10, 5))
        
        # Audio level visualizer (simple waveform)
        self.audio_level_frame = ctk.CTkFrame(stt_frame, fg_color="#0a0a0a", height=30)
        self.audio_level_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.audio_level_label = ctk.CTkLabel(
            self.audio_level_frame,
            text="🔇 Audio Level: [                    ] 0%",
            font=ctk.CTkFont(size=12),
            text_color=CYBERPUNK_BLUE,
        )
        self.audio_level_label.pack(pady=5)
        self.current_audio_level = 0.0
        
        # Textbox for rolling transcription
        self.stt_textbox = ctk.CTkTextbox(
            stt_frame,
            height=120,
            font=ctk.CTkFont(size=16, family="Monaco"),
            fg_color="#0a0a0a",
            text_color=CYBERPUNK_FG,
            wrap="word",
        )
        self.stt_textbox.pack(fill="x", padx=10, pady=(0, 10))
        self.stt_textbox.insert("1.0", "Waiting for audio transcription...\n")
        self.stt_textbox.configure(state="disabled")
        
        # Brain Prompt Zone
        brain_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a", corner_radius=10)
        brain_frame.pack(fill="x", padx=10, pady=10)
        
        brain_label = ctk.CTkLabel(
            brain_frame,
            text="[BRAIN] Last Visual Prompt",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=CYBERPUNK_ACCENT,
        )
        brain_label.pack(pady=(10, 5))
        
        # Prompt display
        self.prompt_label = ctk.CTkLabel(
            brain_frame,
            text="Waiting for LLM analysis...",
            font=ctk.CTkFont(size=14),
            text_color=CYBERPUNK_FG,
            wraplength=900,
            justify="left",
        )
        self.prompt_label.pack(fill="x", padx=10, pady=(0, 10))
        
        # Configuration section (collapsible)
        config_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a")
        config_frame.pack(fill="x", padx=10, pady=10)
        
        config_label = ctk.CTkLabel(
            config_frame,
            text="OSC Configuration",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=CYBERPUNK_CYAN,
        )
        config_label.pack(pady=5)
        
        # IP and Port in one row
        config_row = ctk.CTkFrame(config_frame, fg_color="#1a1a1a")
        config_row.pack(fill="x", padx=10, pady=5)
        
        ip_label = ctk.CTkLabel(config_row, text="IP:", width=30)
        ip_label.pack(side="left", padx=5)
        
        self.ip_entry = ctk.CTkEntry(config_row, width=150)
        self.ip_entry.insert(0, self.config.osc_target_ip)
        self.ip_entry.pack(side="left", padx=5)
        
        port_label = ctk.CTkLabel(config_row, text="Port:", width=40)
        port_label.pack(side="left", padx=5)
        
        self.port_entry = ctk.CTkEntry(config_row, width=100)
        self.port_entry.insert(0, str(self.config.osc_target_port))
        
        # Save config on change
        def on_config_change(*args):
            try:
                ip = self.ip_entry.get().strip()
                port = int(self.port_entry.get().strip())
                # Update .env file
                import os
                env_file = os.path.join(os.path.dirname(__file__), '.env')
                if os.path.exists(env_file):
                    with open(env_file, 'r') as f:
                        lines = f.readlines()
                    with open(env_file, 'w') as f:
                        for line in lines:
                            if line.startswith('OSC_TARGET_IP='):
                                f.write(f'OSC_TARGET_IP={ip}\n')
                            elif line.startswith('OSC_TARGET_PORT='):
                                f.write(f'OSC_TARGET_PORT={port}\n')
                            else:
                                f.write(line)
                self._update_config()
            except:
                pass
        
        self.ip_entry.bind('<FocusOut>', on_config_change)
        self.port_entry.bind('<FocusOut>', on_config_change)
        self.port_entry.pack(side="left", padx=5)
        
        update_button = ctk.CTkButton(
            config_row,
            text="Update",
            command=self._update_config,
            width=80,
            fg_color=CYBERPUNK_BLUE,
            hover_color=CYBERPUNK_CYAN,
        )
        update_button.pack(side="left", padx=5)
        
        # History Slider
        history_frame = ctk.CTkFrame(config_frame, fg_color="#1a1a1a")
        history_frame.pack(fill="x", padx=10, pady=5)
        
        self.history_label = ctk.CTkLabel(history_frame, text="History: 30s", width=80)
        self.history_label.pack(side="left", padx=5)
        
        self.history_slider = ctk.CTkSlider(
            history_frame, 
            from_=5, 
            to=60, 
            number_of_steps=55,
            command=self._on_history_change
        )
        self.history_slider.set(30) # Default
        self.history_slider.pack(side="left", fill="x", expand=True, padx=5)
        
        # Prompt Rate Slider
        rate_frame = ctk.CTkFrame(config_frame, fg_color="#1a1a1a")
        rate_frame.pack(fill="x", padx=10, pady=5)
        
        self.rate_label = ctk.CTkLabel(rate_frame, text="Rate: Fastest", width=80)
        self.rate_label.pack(side="left", padx=5)
        
        self.rate_slider = ctk.CTkSlider(
            rate_frame, 
            from_=1, 
            to=30, 
            number_of_steps=29,
            command=self._on_rate_change
        )
        self.rate_slider.set(1) # Default to Fastest
        self.rate_slider.pack(side="left", fill="x", expand=True, padx=5)
        
        # Reset Memory Button
        reset_button = ctk.CTkButton(
            history_frame,
            text="RESET MEMORY",
            command=self._on_reset_memory,
            width=120,
            fg_color="#ff4444",
            hover_color="#cc0000",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        reset_button.pack(side="left", padx=5)
        
        # Audio device selection
        audio_device_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a", corner_radius=10)
        audio_device_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        audio_device_label = ctk.CTkLabel(
            audio_device_frame,
            text="Audio Input Device",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=CYBERPUNK_CYAN,
        )
        audio_device_label.pack(pady=(10, 5))
        
        audio_device_row = ctk.CTkFrame(audio_device_frame, fg_color="#1a1a1a")
        audio_device_row.pack(fill="x", padx=10, pady=(0, 10))
        
        self.audio_device_var = ctk.StringVar(value="Default (macOS)")
        self.audio_device_combobox = ctk.CTkComboBox(
            audio_device_row,
            variable=self.audio_device_var,
            values=["Default (macOS)"],
            command=self._on_audio_device_change,
            width=320,
        )
        self.audio_device_combobox.pack(side="left", padx=5, pady=5, expand=True, fill="x")
        
        refresh_button = ctk.CTkButton(
            audio_device_row,
            text="Refresh",
            width=100,
            command=self._refresh_audio_devices,
            fg_color=CYBERPUNK_BLUE,
            hover_color=CYBERPUNK_CYAN,
        )
        refresh_button.pack(side="left", padx=5, pady=5)
        
        self._refresh_audio_devices(initial=True)
        
        # Control section
        control_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a")
        control_frame.pack(fill="x", padx=10, pady=10)
        
        self.start_button = ctk.CTkButton(
            control_frame,
            text="▶ START",
            command=self._start_engines,
            fg_color="#00ff41",
            hover_color="#00cc33",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=50,
            width=200,
        )
        self.start_button.pack(side="left", padx=10, pady=10, expand=True)
        
        self.stop_button = ctk.CTkButton(
            control_frame,
            text="⏹ STOP",
            command=self._stop_engines,
            fg_color="#ff0080",
            hover_color="#cc0066",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=50,
            width=200,
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=10, pady=10, expand=True)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            control_frame,
            text="● Status: STOPPED",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#666666",
        )
        self.status_label.pack(pady=10)
        
        # Console section (minimal)
        console_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a")
        console_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        console_label = ctk.CTkLabel(
            console_frame,
            text="[LOG] System Console",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=CYBERPUNK_CYAN,
        )
        console_label.pack(pady=5)
        
        # Text widget for logs
        import tkinter as tk
        self.console_text = tk.Text(
            console_frame,
            bg="#0a0a0a",
            fg=CYBERPUNK_FG,
            font=("Monaco", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            insertbackground=CYBERPUNK_FG,
        )
        self.console_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(console_frame, command=self.console_text.yview)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.console_text.configure(yscrollcommand=scrollbar.set)
    
    def _log(self, message: str, tag: str = "INFO"):
        """Add a message to the console with color coding."""
        # Log to file (and console via StreamHandler)
        logging.info(f"[{tag}] {message}")
        # print(f"[{tag}] {message}")  # Removed duplicate print
        
        # Thread-safe: use after() to update UI from any thread
        self.after(0, self._update_console, message, tag)
    
    def _update_console(self, message: str, tag: str = "INFO"):
        """Update console (called from main thread)."""
        self.console_text.configure(state="normal")
        
        # Color coding based on tag
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if tag == "AUDIO":
            prefix = f"[{timestamp}] [AUDIO] "
            self.console_text.insert("end", prefix, "blue")
        elif tag == "BRAIN":
            prefix = f"[{timestamp}] [BRAIN] "
            self.console_text.insert("end", prefix, "magenta")
        elif tag == "OSC":
            prefix = f"[{timestamp}] [OSC] "
            self.console_text.insert("end", prefix, "green")
        elif tag == "ERROR":
            prefix = f"[{timestamp}] [ERROR] "
            self.console_text.insert("end", prefix, "red")
        else:
            prefix = f"[{timestamp}] "
            self.console_text.insert("end", prefix)
        
        self.console_text.insert("end", f"{message}\n")
        self.console_text.see("end")
        self.console_text.configure(state="disabled")
        
        # Configure text tags for colors
        self.console_text.tag_config("blue", foreground="#00d9ff")
        self.console_text.tag_config("magenta", foreground="#ff0080")
        self.console_text.tag_config("green", foreground="#00ff41")
        self.console_text.tag_config("red", foreground="#ff4444")
    
    def on_audio_data(self, text: str):
        """
        Callback for audio transcription (called from AudioEngine thread).
        Thread-safe: uses after() to update UI from main thread.
        """
        self.after(0, self._update_transcript_ui, text)
    
    def _update_audio_level(self, level: float):
        """Update audio level visualizer (called from main thread)."""
        self.current_audio_level = level
        level_percent = int(level * 100)
        
        # Create visual bar (20 chars)
        bar_length = int(level * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        
        # Update label
        emoji = "🔊" if level > 0.1 else "🔇"
        self.audio_level_label.configure(
            text=f"{emoji} Audio Level: [{bar}] {level_percent}%",
            text_color=CYBERPUNK_FG if level > 0.1 else CYBERPUNK_BLUE
        )
    
    def _load_audio_devices(self) -> List[Tuple[int, str]]:
        """Load available audio input devices."""
        devices: List[Tuple[int, str]] = []
        try:
            for idx, dev in enumerate(sd.query_devices()):
                if dev.get("max_input_channels", 0) > 0:
                    label = f"{idx} - {dev['name']} ({dev['max_input_channels']} ch)"
                    devices.append((idx, label))
        except Exception as e:
            self._log(f"Unable to query audio devices: {e}", tag="ERROR")
        return devices
    
    def _refresh_audio_devices(self, initial: bool = False):
        """Populate the audio device combobox."""
        self.audio_devices = self._load_audio_devices()
        values = ["Default (macOS)"] + [label for _, label in self.audio_devices]
        self.audio_device_combobox.configure(values=values)
        
        current_device = self.config.audio_device
        if current_device is None:
            self.audio_device_var.set("Default (macOS)")
        else:
            matched_label = next((label for idx, label in self.audio_devices if idx == current_device), None)
            if matched_label:
                self.audio_device_var.set(matched_label)
            else:
                self.audio_device_var.set("Default (macOS)")
        
        if not initial:
            self._log("Audio device list refreshed", tag="AUDIO")
    
    def _on_audio_device_change(self, value: str):
        """Handle audio device change from combobox."""
        if not value or value.startswith("Default"):
            self.config.update_audio_device(None)
            self._log("Audio input set to macOS default device", tag="AUDIO")
            return
        
        try:
            device_id = int(value.split(" ", 1)[0])
            self.config.update_audio_device(device_id)
            self._log(f"Audio input set to device #{device_id}", tag="AUDIO")
        except ValueError:
            self._log(f"Unable to parse audio device selection: {value}", tag="ERROR")
    
    def _update_transcript_ui(self, text: str):
        """Update transcription display (called from main thread)."""
        if not text or not text.strip():
            return
        
        # Add to rolling buffer (keep last 3-4 sentences)
        self.stt_text_buffer.append(text)
        if len(self.stt_text_buffer) > 4:
            self.stt_text_buffer.pop(0)
        
        # Update textbox
        self.stt_textbox.configure(state="normal")
        self.stt_textbox.delete("1.0", "end")
        
        # Display rolling text
        display_text = " ".join(self.stt_text_buffer)
        # Limit to ~500 chars to avoid lag
        if len(display_text) > 500:
            display_text = "..." + display_text[-500:]
        
        self.stt_textbox.insert("1.0", display_text)
        self.stt_textbox.configure(state="disabled")
        
        # Update terminal dashboard
        if self.terminal_dashboard:
            self.terminal_dashboard.update_stt(display_text)
    
    def on_brain_prompt(self, prompt_data: Dict):
        """
        Callback for brain prompt (called from BrainEngine thread).
        Thread-safe: uses after() to update UI from main thread.
        """
        self.after(0, self._update_prompt_ui, prompt_data)
    
    def _update_prompt_ui(self, prompt_data: Dict):
        """Update prompt display (called from main thread)."""
        self.last_prompt_data = prompt_data
        
        # Format prompt text
        prompt_text = f"Prompt: {prompt_data.get('prompt', 'N/A')}\n"
        
        # Update label
        self.prompt_label.configure(text=prompt_text)
        
        # Update terminal dashboard
        if self.terminal_dashboard:
            self.terminal_dashboard.update_prompt(prompt_data)
        
        # Log
        self._log(f"Generated prompt: {prompt_data.get('prompt', '')[:50]}...", tag="BRAIN")
    
    def _start_terminal_dashboard(self):
        """Start terminal dashboard update thread."""
        if not RICH_AVAILABLE:
            self._log("Terminal dashboard disabled (rich not available)", tag="INFO")
            return
        
        def dashboard_loop():
            import time
            import sys
            # Only show dashboard if running in terminal (not in IDE)
            if not sys.stdout.isatty():
                return
            
            while True:
                try:
                    if self.terminal_dashboard and self.terminal_dashboard.console:
                        # Move cursor to top and clear screen
                        # self.terminal_dashboard.console.print("\033[H\033[J", end="")
                        self.terminal_dashboard.render()
                    time.sleep(0.5)  # Update every 500ms
                except (KeyboardInterrupt, SystemExit):
                    break
                except Exception as e:
                    # Silently fail to avoid spamming errors
                    time.sleep(1)
        
        dashboard_thread = threading.Thread(target=dashboard_loop, daemon=True)
        dashboard_thread = threading.Thread(target=dashboard_loop, daemon=True)
        dashboard_thread.start()
        
    def _start_engine_monitor(self):
        """Start thread to monitor engines and restart if they crash."""
        def monitor_loop():
            import time
            while True:
                time.sleep(2.0)  # Check every 2 seconds
                
                if not self.is_running:
                    continue
                    
                # Check Audio Engine
                if self.audio_engine and not self.audio_engine.is_alive():
                    self._log("⚠️ Audio Engine died! Restarting...", tag="ERROR")
                    try:
                        # Clean up old engine
                        try:
                            self.audio_engine.stop()
                        except:
                            pass
                        
                        # Restart
                        text_queue = self.brain_engine.text_queue if self.brain_engine else queue.Queue()
                        
                        def audio_log_callback(message: str):
                            self._log(message, tag="AUDIO")
                        
                        def audio_level_callback(level: float):
                            self.after(0, self._update_audio_level, level)
                            
                        self.audio_engine = AudioEngine(
                            text_queue=text_queue,
                            transcription_callback=self.on_audio_data,
                            audio_level_callback=audio_level_callback,
                            log_callback=audio_log_callback
                        )
                        self.audio_engine.start()
                        self._log("✅ Audio Engine restarted successfully", tag="AUDIO")
                    except Exception as e:
                        self._log(f"❌ Failed to restart Audio Engine: {e}", tag="ERROR")
                
                # Check Brain Engine
                if self.brain_engine and not self.brain_engine.is_alive():
                    self._log("⚠️ Brain Engine died! Restarting...", tag="ERROR")
                    try:
                        # Clean up
                        try:
                            self.brain_engine.stop()
                        except:
                            pass
                            
                        # Restart
                        text_queue = self.audio_engine.text_queue if self.audio_engine else queue.Queue()
                        
                        def brain_log_callback(message: str):
                            self._log(message, tag="BRAIN")
                        
                        def brain_prompt_callback(prompt_data: Dict):
                            self.on_brain_prompt(prompt_data)
                            
                        self.brain_engine = BrainEngine(
                            text_queue=text_queue,
                            osc_client=self.osc_client,
                            log_callback=brain_log_callback,
                            prompt_callback=brain_prompt_callback
                        )
                        self.brain_engine.start()
                        self._log("✅ Brain Engine restarted successfully", tag="BRAIN")
                    except Exception as e:
                        self._log(f"❌ Failed to restart Brain Engine: {e}", tag="ERROR")
                        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def _on_history_change(self, value):
        """Handle history slider change."""
        history_val = int(value)
        self.history_label.configure(text=f"History: {history_val}s")
        
        # Constraint: Rate must be <= History
        # If History is lowered below Rate, lower Rate to match
        current_rate = self.rate_slider.get()
        if current_rate > history_val:
            self.rate_slider.set(history_val)
            self._on_rate_change(history_val)
            
        if self.brain_engine:
            self.brain_engine.set_context_window(history_val)

    def _on_rate_change(self, value):
        """Handle prompt rate slider change."""
        rate_val = int(value)
        
        # Update label
        if rate_val <= 2:
            self.rate_label.configure(text="Rate: Fastest")
        else:
            self.rate_label.configure(text=f"Rate: {rate_val}s")
            
        # Constraint: Rate must be <= History
        # If Rate is raised above History, raise History to match
        current_history = self.history_slider.get()
        if rate_val > current_history:
            self.history_slider.set(rate_val)
            self._on_history_change(rate_val)
            
        if self.brain_engine:
            self.brain_engine.set_generation_interval(rate_val)

    def _on_reset_memory(self):
        """Handle reset memory button click."""
        # Clear Brain Engine history
        if self.brain_engine:
            self.brain_engine.clear_memory()
        
        # Clear UI buffers
        self.stt_text_buffer = []
        self.stt_textbox.configure(state="normal")
        self.stt_textbox.delete("1.0", "end")
        self.stt_textbox.insert("1.0", "Memory wiped. Waiting for new audio...\n")
        self.stt_textbox.configure(state="disabled")
        
        # Clear terminal dashboard if active
        if self.terminal_dashboard:
            self.terminal_dashboard.update_stt("")
            
        self._log("🧹 Memory wiped manually", tag="INFO")

    def _update_config(self):
        """Update OSC configuration from UI fields."""
        try:
            ip = self.ip_entry.get().strip()
            port = int(self.port_entry.get().strip())
            
            self.config.update_osc_config(ip, port)
            
            if self.osc_client:
                self.osc_client.update_target(ip, port)
            
            self._log(f"Configuration updated: {ip}:{port}")
        except ValueError:
            self._log("Error: Invalid port number", tag="ERROR")
        except Exception as e:
            self._log(f"Error updating config: {e}", tag="ERROR")
    
    def _init_osc_client(self):
        """Initialize OSC client."""
        self.osc_client = OSCClient(
            self.config.osc_target_ip,
            self.config.osc_target_port
        )
    
    def _start_engines(self):
        """Start audio and brain engines."""
        if self.is_running:
            return
        
        self._log("=" * 50)
        self._log("Starting VoiceVibe4 engines...")
        
        try:
            # Update config first
            self._update_config()
            
            # Connect OSC client
            if self.osc_client:
                self.osc_client.connect()
                self._log("OSC client connected", tag="OSC")
            
            # Create text queue for communication between engines
            text_queue = queue.Queue()
            
            # Start audio engine with callbacks
            def audio_log_callback(message: str):
                """Log callback for audio engine."""
                self._log(message, tag="AUDIO")
            
            def audio_level_callback(level: float):
                """Audio level callback for visualization."""
                self.after(0, self._update_audio_level, level)
            
            self.audio_engine = AudioEngine(
                text_queue=text_queue,
                transcription_callback=self.on_audio_data,
                audio_level_callback=audio_level_callback,
                log_callback=audio_log_callback
            )
            self._log("🔄 Loading Moshi STT models...", tag="AUDIO")
            self.audio_engine.start()
            self._log("✅ Audio engine thread started", tag="AUDIO")
            
            # Start brain engine with callbacks
            def brain_log_callback(message: str):
                """Log callback for brain engine."""
                self._log(message, tag="BRAIN")
            
            def brain_prompt_callback(prompt_data: Dict):
                """Prompt callback for brain engine."""
                self.on_brain_prompt(prompt_data)
            
            self._log("🔄 Initializing Brain engine...", tag="BRAIN")
            self.brain_engine = BrainEngine(
                text_queue=text_queue,
                osc_client=self.osc_client,
                log_callback=brain_log_callback,
                prompt_callback=brain_prompt_callback
            )
            self.brain_engine.start()
            self._log("✅ Brain engine thread started", tag="BRAIN")
            self._log("🔄 Checking Ollama model availability...", tag="BRAIN")
            
            # Update UI
            self.is_running = True
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.status_label.configure(
                text="● Status: RUNNING",
                text_color="#00ff41"
            )
            
            # Update terminal dashboard
            if self.terminal_dashboard:
                self.terminal_dashboard.update_status("RUNNING")
            
            self._log("All engines started successfully!")
            self._log("=" * 50)
        
        except Exception as e:
            self._log(f"Error starting engines: {e}", tag="ERROR")
            import traceback
            traceback.print_exc()
            self._stop_engines()
    
    def _stop_engines(self):
        """Stop audio and brain engines."""
        if not self.is_running:
            return
        
        self._log("=" * 50)
        self._log("Stopping VoiceVibe4 engines...")
        
        try:
            # Stop brain engine
            if self.brain_engine:
                self.brain_engine.stop()
                self.brain_engine = None
                self._log("Brain engine stopped", tag="BRAIN")
            
            # Stop audio engine
            if self.audio_engine:
                self.audio_engine.stop()
                # Join thread to ensure it's truly dead
                if self.audio_engine.is_alive():
                    self.audio_engine.join(timeout=1.0)
                self.audio_engine = None
                self._log("Audio engine stopped", tag="AUDIO")
            
            # Disconnect OSC client
            if self.osc_client:
                self.osc_client.disconnect()
                self._log("OSC client disconnected", tag="OSC")
            
            # Update UI
            self.is_running = False
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.status_label.configure(
                text="● Status: STOPPED",
                text_color="#666666"
            )
            
            # Update terminal dashboard
            if self.terminal_dashboard:
                self.terminal_dashboard.update_status("STOPPED")
            
            self._log("All engines stopped.")
            self._log("=" * 50)
        
        except Exception as e:
            self._log(f"Error stopping engines: {e}", tag="ERROR")
    
    def on_closing(self):
        """Handle window closing event."""
        if self.is_running:
            self._stop_engines()
        self.destroy()


def main():
    """Main entry point."""
    app = VoiceVibeApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
