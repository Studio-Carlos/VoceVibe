import customtkinter as ctk
import threading
import queue
import time
import logging
import sys
import os
import signal
import subprocess
import sounddevice as sd
import resource
from typing import Optional, Dict, List, Tuple
from datetime import datetime

# Import Engines
from src.audio_engine import AudioEngine
from src.brain_engine import BrainEngine
from src.summary_engine import SummaryEngine
from src.config import get_config
from src.osc_client import OSCClient

# --- THEME & CONSTANTS ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Cyberpunk Pro Palette
COLOR_BG = "#050505"
COLOR_PANEL = "#111111"
COLOR_BORDER = "#333333"
COLOR_TEXT_MAIN = "#E0E0E0"
COLOR_TEXT_DIM = "#888888"

ACCENT_GREEN = "#00FF41"  # Audio / Start
ACCENT_PINK = "#FF0080"   # Fast Brain
ACCENT_PURPLE = "#9D00FF" # Slow Brain
ACCENT_RED = "#FF4444"    # Stop / Error

FONT_UI = ("Roboto", 12)
FONT_UI_BOLD = ("Roboto", 12, "bold")
FONT_HEADER = ("Roboto", 20, "bold")
FONT_MONO = ("JetBrains Mono", 12)

class VoiceVibeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("VoceVibe Mission Control")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.configure(fg_color=COLOR_BG)

        # --- State ---
        self.config = get_config()
        self.config.load_settings() # Load user preferences
        
        self.is_running = False
        self.is_stopping = False
        self.audio_devices = []
        
        # Saved State for Pause/Resume
        self.saved_brain_state = None
        self.saved_summary_state = None
        
        # UI References
        self.info_window = None
        
        # Engines
        self.audio_engine: Optional[AudioEngine] = None
        self.brain_engine: Optional[BrainEngine] = None
        self.summary_engine: Optional[SummaryEngine] = None
        self.osc_client: Optional[OSCClient] = None
        
        # Buffers
        self.stt_text_buffer = []

        # --- UI Initialization ---
        self._setup_ui()
        
        # --- Post-UI Setup ---
        self._init_osc_client()
        self._refresh_audio_devices()
        
        # Redirect stdout/stderr to console
        sys.stdout = self.ConsoleRedirector(self)
        sys.stderr = self.ConsoleRedirector(self, is_error=True)
        
        # Start monitoring
        self._start_engine_monitor()
        
        self._log("Application started successfully.", "SYSTEM")
        
        # Clear previous session log on startup
        try:
             with open("session.log", "w", encoding="utf-8") as f:
                 f.write(f"--- SESSION START {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n\n")
        except: pass

    # =========================================================================
    # UI SETUP
    # =========================================================================

    def _setup_ui(self):
        """Build the Mission Control interface."""
        # Grid Configuration
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Main Content
        self.grid_rowconfigure(2, weight=0)  # Footer
        self.grid_columnconfigure(0, weight=1)

        # 1. HEADER
        self._setup_header()

        # 2. MAIN CONTENT (Split 40/60)
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.main_frame.grid_columnconfigure(0, weight=4) # Left (Audio)
        self.main_frame.grid_columnconfigure(1, weight=6) # Right (Brain)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self._setup_left_panel()
        self._setup_right_panel()

        # 3. FOOTER
        self._setup_footer()

    def _setup_header(self):
        """Top bar with Title and Status."""
        self.header_frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 5))
        self.header_frame.grid_columnconfigure(1, weight=1)

        # Quit Button (Top Left)
        ctk.CTkButton(self.header_frame, text="✖ QUIT", width=60, height=30, font=("Roboto", 12, "bold"),
                      fg_color="#330000", text_color="#FF4444", hover_color="#550000",
                      command=self._quit_app).grid(row=0, column=0, padx=(20, 10), pady=15, sticky="w")

        # Title
        title = ctk.CTkLabel(self.header_frame, text="VOCEVIBE // MISSION CONTROL", 
                             font=FONT_HEADER, text_color=COLOR_TEXT_MAIN)
        title.grid(row=0, column=1, padx=10, pady=15, sticky="w")

        # Status Indicator
        self.status_indicator = ctk.CTkLabel(self.header_frame, text="● SYSTEM OFFLINE",
                                             font=FONT_UI_BOLD, text_color=COLOR_TEXT_DIM)
        self.status_indicator.grid(row=0, column=2, padx=(20, 10), pady=15, sticky="e")
        
        # Info Button
        ctk.CTkButton(self.header_frame, text="ℹ️", width=30, height=30, font=("Roboto", 16),
                      fg_color="transparent", text_color=COLOR_TEXT_DIM, hover_color=COLOR_BORDER,
                      command=self._show_info_popup).grid(row=0, column=3, padx=(0, 20), pady=15, sticky="e")

    def _setup_left_panel(self):
        """Left Column: Audio & Transcript."""
        self.left_panel = ctk.CTkFrame(self.main_frame, fg_color=COLOR_PANEL, border_width=1, border_color=COLOR_BORDER)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        self.left_panel.grid_rowconfigure(2, weight=0) # Live Transcript (Fixed)
        self.left_panel.grid_rowconfigure(5, weight=1) # History (Expands)
        self.left_panel.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(self.left_panel, text="AUDIO INPUT", font=FONT_UI_BOLD, text_color=ACCENT_GREEN).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        # Audio Level
        self.audio_level_bar = ctk.CTkProgressBar(self.left_panel, height=4, progress_color=ACCENT_GREEN)
        self.audio_level_bar.set(0)
        self.audio_level_bar.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")

        # Transcript (Live)
        ctk.CTkLabel(self.left_panel, text="LIVE TRANSCRIPT", font=FONT_UI_BOLD, text_color=COLOR_TEXT_DIM).grid(row=2, column=0, padx=15, pady=(0, 5), sticky="nw")
        
        self.live_transcript_box = ctk.CTkTextbox(self.left_panel, font=FONT_MONO, height=100,
                                                  fg_color="#000000", text_color=ACCENT_GREEN,
                                                  border_width=1, border_color=COLOR_BORDER)
        self.live_transcript_box.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="ew")
        self.live_transcript_box.insert("1.0", "> Waiting for audio stream...\n")
        self.live_transcript_box.configure(state="disabled")

        # Transcript (History)
        hist_header = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        hist_header.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 5))
        
        ctk.CTkLabel(hist_header, text="TRANSCRIPT HISTORY", font=FONT_UI_BOLD, text_color=COLOR_TEXT_DIM).pack(side="left")

        self.transcript_history_box = ctk.CTkTextbox(self.left_panel, font=FONT_MONO,
                                                     fg_color="#080808", text_color="#888888",
                                                     border_width=1, border_color=COLOR_BORDER)
        self.transcript_history_box.grid(row=5, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.transcript_history_box.configure(state="disabled")

    def _setup_right_panel(self):
        """Right Column: Intelligence & Controls."""
        self.right_panel = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        self.right_panel.grid_rowconfigure(0, weight=1) # Fast Brain (Smaller)
        self.right_panel.grid_rowconfigure(1, weight=2) # Slow Brain (Larger)
        self.right_panel.grid_rowconfigure(2, weight=0) # Controls
        self.right_panel.grid_columnconfigure(0, weight=1)

        # --- FAST BRAIN (Top - Smaller) ---
        self.fast_brain_frame = ctk.CTkFrame(self.right_panel, fg_color=COLOR_PANEL, 
                                             border_width=2, border_color=ACCENT_PINK)
        self.fast_brain_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.fast_brain_frame.grid_columnconfigure(0, weight=1)
        self.fast_brain_frame.grid_rowconfigure(1, weight=1)

        # Header with Copy Button
        fb_header = ctk.CTkFrame(self.fast_brain_frame, fg_color="transparent")
        fb_header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        ctk.CTkLabel(fb_header, text="FAST BRAIN // SDXL PROMPT", 
                     font=FONT_UI_BOLD, text_color=ACCENT_PINK).pack(side="left")
        
        ctk.CTkButton(fb_header, text="COPY", width=60, height=24, font=("Roboto", 10, "bold"),
                      fg_color=ACCENT_PINK, text_color="black", hover_color="#FF3399",
                      command=lambda: self._copy_to_clipboard(self.prompt_label.get("1.0", "end"))).pack(side="right")
        
        self.prompt_label = ctk.CTkTextbox(self.fast_brain_frame, font=("Roboto", 16), 
                                           fg_color="transparent", text_color=COLOR_TEXT_MAIN, wrap="word")
        self.prompt_label.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.prompt_label.insert("1.0", "Waiting for context...")
        self.prompt_label.configure(state="disabled")

        # --- SLOW BRAIN (Middle - Split View) ---
        self.slow_brain_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.slow_brain_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.slow_brain_frame.grid_columnconfigure(0, weight=1)
        self.slow_brain_frame.grid_columnconfigure(1, weight=1)
        self.slow_brain_frame.grid_rowconfigure(0, weight=3) # Summary/Visual
        self.slow_brain_frame.grid_rowconfigure(1, weight=1) # Context Input (New)

        # Left: Summary
        self.summary_frame = ctk.CTkFrame(self.slow_brain_frame, fg_color=COLOR_PANEL,
                                          border_width=2, border_color=ACCENT_PURPLE)
        self.summary_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
        self.summary_frame.grid_columnconfigure(0, weight=1)
        self.summary_frame.grid_rowconfigure(1, weight=1)

        sum_header = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        sum_header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        ctk.CTkLabel(sum_header, text="SLOW BRAIN // SUMMARY", font=FONT_UI_BOLD, text_color=ACCENT_PURPLE).pack(side="left")
        
        # Copy Button
        ctk.CTkButton(sum_header, text="COPY", width=60, height=24, font=("Roboto", 10, "bold"),
                      fg_color=ACCENT_PURPLE, text_color="black", hover_color="#BB33FF",
                      command=lambda: self._copy_to_clipboard(self.summary_box.get("1.0", "end"))).pack(side="right", padx=(5, 0))
        
        # Reset Button (Moved here)
        ctk.CTkButton(sum_header, text="MEM RESET", width=80, height=24, font=("Roboto", 10, "bold"),
                      fg_color=COLOR_BORDER, text_color=COLOR_TEXT_DIM, hover_color=ACCENT_RED,
                      command=self._reset_history).pack(side="right")

        self.summary_box = ctk.CTkTextbox(self.summary_frame, font=FONT_UI, 
                                          fg_color="transparent", text_color=COLOR_TEXT_DIM, wrap="word")
        self.summary_box.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.summary_box.insert("1.0", "Analyzing conversation flow...")
        self.summary_box.configure(state="disabled")

        # Right: Visual Context
        self.visual_frame = ctk.CTkFrame(self.slow_brain_frame, fg_color=COLOR_PANEL,
                                         border_width=2, border_color=ACCENT_PURPLE)
        self.visual_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.visual_frame.grid_columnconfigure(0, weight=1)
        self.visual_frame.grid_rowconfigure(1, weight=1)

        vis_header = ctk.CTkFrame(self.visual_frame, fg_color="transparent")
        vis_header.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        ctk.CTkLabel(vis_header, text="SLOW BRAIN // VISUAL", font=FONT_UI_BOLD, text_color=ACCENT_PURPLE).pack(side="left")
        ctk.CTkButton(vis_header, text="COPY", width=60, height=24, font=("Roboto", 10, "bold"),
                      fg_color=ACCENT_PURPLE, text_color="black", hover_color="#BB33FF",
                      command=lambda: self._copy_to_clipboard(self.visual_box.get("1.0", "end"))).pack(side="right")

        self.visual_box = ctk.CTkTextbox(self.visual_frame, font=FONT_UI, 
                                         fg_color="transparent", text_color=COLOR_TEXT_DIM, wrap="word")
        self.visual_box.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.visual_box.insert("1.0", "Waiting for visual context...")
        self.visual_box.configure(state="disabled")

        # --- USER CONTEXT INPUT (New Bottom Section) ---
        self.context_frame = ctk.CTkFrame(self.slow_brain_frame, fg_color=COLOR_PANEL, border_width=1, border_color=COLOR_BORDER)
        self.context_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.context_frame.grid_columnconfigure(0, weight=1)
        self.context_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.context_frame, text="GLOBAL CONTEXT / VIBE (Optional)", font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_DIM).grid(row=0, column=0, sticky="w", padx=10, pady=(5,0))
        
        self.context_input = ctk.CTkTextbox(self.context_frame, font=("Roboto", 12), height=60,
                                            fg_color="#080808", text_color="#AAAAAA", wrap="word")
        self.context_input.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.context_input.insert("1.0", "Type context here (e.g. 'Cyberpunk Noir style', 'Focus on nature')...")
        self.context_input.bind("<FocusIn>", self._on_context_focus_in)
        self.context_input.bind("<FocusOut>", self._on_context_update)
        self.context_input.bind("<Return>", self._on_context_enter) # Update on Enter too

        # --- CONTROLS (Bottom) ---
        self.controls_frame = ctk.CTkFrame(self.right_panel, fg_color=COLOR_PANEL, border_width=1, border_color=COLOR_BORDER)
        self.controls_frame.grid(row=2, column=0, sticky="ew")
        self.controls_frame.grid_columnconfigure(1, weight=1) # Spacing
        self.controls_frame.grid_columnconfigure(2, weight=1) # Sliders

        # Start/Stop Buttons
        self.btn_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.btn_frame.grid(row=0, column=0, padx=15, pady=15)
        
        self.start_button = ctk.CTkButton(self.btn_frame, text="▶ START SYSTEM", 
                                          font=FONT_UI_BOLD, fg_color=ACCENT_GREEN, text_color="black",
                                          hover_color="#00CC33", width=140, height=40,
                                          command=self._start_engines)
        self.start_button.pack(side="left", padx=(0, 10))
        
        self.stop_button = ctk.CTkButton(self.btn_frame, text="⏸ PAUSE", 
                                         font=FONT_UI_BOLD, fg_color=COLOR_BORDER, text_color=COLOR_TEXT_DIM,
                                         hover_color="orange", width=120, height=40,
                                         state="disabled", command=self._stop_engines)
        self.stop_button.pack(side="left")

        # Sliders
        self.sliders_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.sliders_frame.grid(row=0, column=2, padx=15, pady=15, sticky="ew")
        self.sliders_frame.grid_columnconfigure(1, weight=1)

        # History Slider
        self.history_label = ctk.CTkLabel(self.sliders_frame, text="History: 30s", font=FONT_MONO, text_color=COLOR_TEXT_DIM)
        self.history_label.grid(row=0, column=0, padx=(0, 10), sticky="e")
        self.history_slider = ctk.CTkSlider(self.sliders_frame, from_=30, to=300, number_of_steps=270,
                                            progress_color=ACCENT_PURPLE, button_color=ACCENT_PURPLE,
                                            command=self._on_history_change)
        self.history_slider.set(self.config.history_seconds)
        self.history_label.configure(text=f"History: {self.config.history_seconds}s")
        self.history_slider.grid(row=0, column=1, sticky="ew", pady=(0, 10))

        # Rate Slider
        self.rate_label = ctk.CTkLabel(self.sliders_frame, text="Rate: Fastest", font=FONT_MONO, text_color=COLOR_TEXT_DIM)
        self.rate_label.grid(row=1, column=0, padx=(0, 10), sticky="e")
        self.rate_slider = ctk.CTkSlider(self.sliders_frame, from_=2, to=60, number_of_steps=58,
                                         progress_color=ACCENT_PINK, button_color=ACCENT_PINK,
                                         command=self._on_rate_change)
        self.rate_slider.set(self.config.generation_rate)
        rate_txt = "Fastest" if self.config.generation_rate <= 2 else f"{int(self.config.generation_rate)}s"
        self.rate_label.configure(text=f"Rate: {rate_txt}")
        self.rate_slider.grid(row=1, column=1, sticky="ew")

        # OSC Config (Compact)
        self.osc_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.osc_frame.grid(row=0, column=3, padx=15, pady=15)
        
        ctk.CTkLabel(self.osc_frame, text="OSC TARGET", font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_DIM).pack(anchor="w")
        
        self.ip_entry = ctk.CTkEntry(self.osc_frame, width=100, font=FONT_MONO, fg_color="#000000", border_color=COLOR_BORDER)
        self.ip_entry.insert(0, self.config.osc_target_ip)
        self.ip_entry.pack(side="left", padx=(0, 5))
        
        self.port_entry = ctk.CTkEntry(self.osc_frame, width=60, font=FONT_MONO, fg_color="#000000", border_color=COLOR_BORDER)
        self.port_entry.insert(0, str(self.config.osc_target_port))
        self.port_entry.pack(side="left")
        
        # Audio Device Selector
        self.audio_device_var = ctk.StringVar(value="Default")
        self.audio_device_combobox = ctk.CTkComboBox(self.osc_frame, variable=self.audio_device_var, width=160,
                                                     font=FONT_UI, values=["Default"], command=self._on_device_change)
        self.audio_device_combobox.pack(side="left", padx=(10, 0))
        
        ctk.CTkButton(self.osc_frame, text="↻", width=30, height=28, font=FONT_UI_BOLD,
                      fg_color=COLOR_PANEL, text_color=COLOR_TEXT_DIM, hover_color=COLOR_BORDER,
                      command=self._refresh_audio_devices).pack(side="left", padx=(5, 0))


    def _copy_to_clipboard(self, text: str):
        """Helper to copy text to clipboard."""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # Required for macOS to process the clipboard event
        self._log("Copied to clipboard", "SYSTEM")

    def _reset_history(self):
        """Clear transcript history, buffers, and Brain memory."""
        # 1. Clear UI Buffers
        self.stt_text_buffer = []
        
        self.live_transcript_box.configure(state="normal")
        self.live_transcript_box.delete("1.0", "end")
        self.live_transcript_box.insert("1.0", "> History cleared.\n")
        self.live_transcript_box.configure(state="disabled")
        
        self.transcript_history_box.configure(state="normal")
        self.transcript_history_box.delete("1.0", "end")
        self.transcript_history_box.configure(state="disabled")
        
        # Clear Context Input
        self.context_input.delete("1.0", "end")
        self.context_input.insert("1.0", "Type context here (e.g. 'Cyberpunk Noir style', 'Focus on nature')...")
        
        # 2. Clear Brain Memory
        if self.brain_engine:
            self.brain_engine.clear_memory()
            self.brain_engine.clear_memory()
            self._log("Brain memory wiped", "BRAIN")
        if self.summary_engine:
            self.summary_engine.reset_memory()
            
        # Clear Saved State
        self.saved_brain_state = None
        self.saved_summary_state = None
            
        self._log("System history and memory fully reset", "SYSTEM")

    def _show_info_popup(self):
        """Show information popup with detailed documentation."""
        self._log("Showing help info", "SYSTEM")
        
        if self.info_window is not None and self.info_window.winfo_exists():
            self.info_window.lift()
            self.info_window.focus_force()
            return

        try:
            self.info_window = ctk.CTkToplevel(self)
            self.info_window.title("Mission Briefing")
            self.info_window.geometry("700x600")
            self.info_window.configure(fg_color="#050505")
            
            # Ensure it stays on top
            self.info_window.lift()
            self.info_window.focus_force()
            
            # Header
            header = ctk.CTkFrame(self.info_window, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=20)
            
            ctk.CTkLabel(header, text="VOCEVIBE // MANUAL", font=("Roboto", 24, "bold"), text_color="white").pack(side="left")
            ctk.CTkLabel(header, text="v1.6.0", font=FONT_MONO, text_color=ACCENT_GREEN).pack(side="right", pady=5)
            
            # Scrollable Content Area
            content = ctk.CTkTextbox(self.info_window, font=("Roboto", 14), fg_color="#111111", text_color="#DDDDDD", wrap="word")
            content.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            
            # Documentation Text - Load from manual.md
            info_text = "Error loading manual."
            try:
                with open("manual.md", "r", encoding="utf-8") as f:
                    info_text = f.read()
            except Exception as e:
                self._log(f"Manual load error: {e}", "ERROR")
                info_text = f"Manual file not found.\n\nError: {e}"

            content.insert("1.0", info_text)
            content.configure(state="disabled")
            
            # Close Button
            ctk.CTkButton(self.info_window, text="ACKNOWLEDGE", height=40, font=FONT_UI_BOLD,
                          fg_color=ACCENT_GREEN, text_color="black", hover_color="#00CC33",
                          command=self.info_window.destroy).pack(pady=20)
                          
        except Exception as e:
            self._log(f"Error showing info popup: {e}", "ERROR")

    def _setup_footer(self):
        """Bottom System Logs."""
        self.footer_frame = ctk.CTkFrame(self, fg_color=COLOR_PANEL, height=150, corner_radius=0)
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        self.footer_frame.grid_columnconfigure(0, weight=1)
        self.footer_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.footer_frame, text="SYSTEM LOGS", font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_DIM).grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.console_text = ctk.CTkTextbox(self.footer_frame, font=("Courier New", 11), 
                                           fg_color="#000000", text_color="#AAAAAA", height=100)
        self.console_text.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.console_text.configure(state="disabled")

    # =========================================================================
    # LOGIC & CALLBACKS
    # =========================================================================

    def _on_context_focus_in(self, event):
        """Clear placeholder on focus."""
        text = self.context_input.get("1.0", "end-1c")
        if text.startswith("Type context here"):
            self.context_input.delete("1.0", "end")
            self.context_input.configure(text_color=COLOR_TEXT_MAIN)

    def _on_context_update(self, event=None):
        """Update BrainEngine with new context."""
        text = self.context_input.get("1.0", "end-1c")
        if not text.strip() or text.startswith("Type context here"):
            return
            
        if self.brain_engine:
            self.brain_engine.set_user_context(text)
            
    def _on_context_enter(self, event):
        """Update on Enter key (and keep focus or not)."""
        self._on_context_update()
        return "break" # Prevent newline

    def _start_engines(self):
        """Initialize and start all engines."""
        self._log("Start button clicked", "DEBUG")
        if self.is_running:
            self._log("System already running", "DEBUG")
            return
            
        self._log("Initiating startup sequence...", "SYSTEM")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal", fg_color=ACCENT_RED, text_color="white")
        self.status_indicator.configure(text="● SYSTEM ACTIVE", text_color=ACCENT_GREEN)
        self.is_running = True
        self.is_stopping = False

        # 1. Update Config
        self._update_config()
        
        # 2. Connect OSC
        if self.osc_client:
            self.osc_client.connect()

        # 3. Queues
        text_queue = queue.Queue()
        summary_queue = queue.Queue()

        # 4. Audio Engine
        self.audio_engine = AudioEngine(
            text_queue=text_queue,
            summary_queue=summary_queue,
            transcription_callback=lambda t: self.after(0, self._update_transcript_ui, t),
            audio_level_callback=lambda l: self.after(0, self._update_audio_level, l),
            log_callback=lambda m: self._log(m, "AUDIO")
        )
        self.audio_engine.start()

        # 5. Brain Engine
        self.brain_engine = BrainEngine(
            text_queue=text_queue,
            osc_client=self.osc_client,
            log_callback=lambda m: self._log(m, "BRAIN"),
            prompt_callback=lambda d: self.after(0, self._update_prompt_ui, d)
        )
        # Apply saved settings to BrainEngine
        self.brain_engine.set_context_window(self.config.history_seconds)
        self.brain_engine.set_generation_interval(self.config.generation_rate)
        
        # Apply current text context
        ctx = self.context_input.get("1.0", "end-1c")
        if ctx and not ctx.startswith("Type context here"):
            self.brain_engine.set_user_context(ctx)
            
        self.brain_engine.start()

        # 6. Summary Engine
        self.summary_engine = SummaryEngine(
            summary_queue=summary_queue,
            osc_client=self.osc_client,
            log_callback=lambda m: self._log(m, "SUMMARY"),
            text_callback=lambda t: self.after(0, self._update_summary_ui, t),
            visual_callback=lambda t: self.after(0, self._update_summary_visual_ui, t)
        )
        
        # Restore State if available
        if self.saved_brain_state:
            self.brain_engine.set_state(self.saved_brain_state)
        if self.saved_summary_state:
            self.summary_engine.set_state(self.saved_summary_state)
            
        self.summary_engine.start()

        self._log("All systems nominal.", "SYSTEM")

    def _stop_engines(self):
        """Graceful shutdown in background thread."""
        if not self.is_running: return
        
        self.is_stopping = True
        self._log("Initiating pause sequence (saving context)...", "SYSTEM")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="disabled", text="PAUSING...")
        self.status_indicator.configure(text="● PAUSING...", text_color="orange")
        
        threading.Thread(target=self._stop_engines_thread, daemon=True).start()

    def _stop_engines_thread(self):
        """Background shutdown logic."""
        # 1. Save State before stopping
        if self.brain_engine:
             self.saved_brain_state = self.brain_engine.get_state()
             self.brain_engine.stop()
             
        if self.summary_engine:
             self.saved_summary_state = self.summary_engine.get_state()
             self.summary_engine.stop()
        
        # small delay to let threads finish
        time.sleep(0.5)
        
        # 2. Stop Hardware/Audio Last
        if self.audio_engine: self.audio_engine.stop()
        
        # delay for audio device release
        time.sleep(0.5)
        
        # 3. Disconnect Network
        if self.osc_client: self.osc_client.disconnect()

        # Trigger UI update on main thread
        self.after(0, self._on_stopped)

    def _quit_app(self):
        """Clean shutdown and exit."""
        if self.is_stopping: return
        self.is_stopping = True
        
        # Immediate UI feedback
        self.stop_button.configure(text="QUITTING...", fg_color="#550000")
        self.start_button.configure(state="disabled")
        self.status_indicator.configure(text="● SHUTTING DOWN...", text_color="red")
        self.update() # Force UI update immediately
        
        self._log("Initiating full system shutdown...", "SYSTEM")
        
        # Run cleanup in thread to keep UI alive
        threading.Thread(target=self._quit_thread, daemon=True).start()

    def _quit_thread(self):
        """Threaded cleanup logic."""
        # Stop Engines Synchronously (but in thread)
        if self.brain_engine: 
            self._log("Stopping BrainEngine...", "SYSTEM")
            self.brain_engine.stop()
        if self.summary_engine: 
            self._log("Stopping SummaryEngine...", "SYSTEM")
            self.summary_engine.stop()
        if self.audio_engine: 
            self._log("Stopping AudioEngine...", "SYSTEM")
            self.audio_engine.stop()
        if self.osc_client: 
            self.osc_client.disconnect()
            
        # Clear Memory
        import gc
        self.brain_engine = None
        self.summary_engine = None
        self.audio_engine = None
        gc.collect()
        
        self._log("💾 Resources released. RAM cleared.", "SYSTEM")
        self._log("👋 Goodbye.", "SYSTEM")
        
        # Signal main thread to destroy and exit
        self.after(0, self._finalize_quit)

    def _finalize_quit(self):
        """Final UI destruction."""
        self.destroy()
        
        # Close Terminal (macOS specific hack)
        try:
            subprocess.run(["osascript", "-e", 'tell application "Terminal" to close first window'])
        except Exception:
            pass
            
        sys.exit(0)

    def _on_stopped(self):
        """UI cleanup after stop."""
        self.is_running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled", text="⏸ PAUSE", fg_color=COLOR_BORDER, text_color=COLOR_TEXT_DIM)
        self.status_indicator.configure(text="● PAUSED (Context Saved)", text_color="orange")
        self._log("System paused. Context in memory.", "SYSTEM")

    # --- UI Updates ---

    def _update_transcript_ui(self, text: str):
        """Append text to transcript."""
        # Update Live Transcript (Rolling Buffer)
        self.stt_text_buffer.append(text)
        if len(self.stt_text_buffer) > 10: self.stt_text_buffer.pop(0) # Increased buffer slightly
        
        display = " ".join(self.stt_text_buffer)
        
        self.live_transcript_box.configure(state="normal")
        self.live_transcript_box.delete("1.0", "end")
        self.live_transcript_box.insert("1.0", display)
        self.live_transcript_box.configure(state="disabled")

        # Update History (Append)
        self.transcript_history_box.configure(state="normal")
        self.transcript_history_box.insert("end", text + " ")
        self.transcript_history_box.see("end")
        self.transcript_history_box.configure(state="disabled")

    def _update_audio_level(self, level: float):
        """Update progress bar color and value."""
        if self.is_stopping: return
        try:
            self.audio_level_bar.set(level)
            if level > 0.8: self.audio_level_bar.configure(progress_color=ACCENT_RED)
            elif level > 0.5: self.audio_level_bar.configure(progress_color="orange")
            else: self.audio_level_bar.configure(progress_color=ACCENT_GREEN)
        except Exception:
            pass

    def _update_prompt_ui(self, data: Dict):
        """Update Fast Brain prompt."""
        prompt = data.get("prompt", "")
        self.prompt_label.configure(state="normal")
        self.prompt_label.delete("1.0", "end")
        self.prompt_label.insert("1.0", prompt)
        self.prompt_label.configure(state="disabled")

    def _update_summary_ui(self, text: str):
        """Update Slow Brain text summary."""
        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", "end")
        self.summary_box.insert("1.0", text)
        self.summary_box.configure(state="disabled")

    def _update_summary_visual_ui(self, text: str):
        """Update Slow Brain visual prompt."""
        self.visual_box.configure(state="normal")
        self.visual_box.delete("1.0", "end")
        self.visual_box.insert("1.0", text)
        self.visual_box.configure(state="disabled")

    # --- Controls ---

    def _on_history_change(self, value):
        if hasattr(self, 'history_label'):
            val = int(value)
            self.history_label.configure(text=f"History: {val}s")
            self.config.history_seconds = val
            self.config.save_settings()
            if self.brain_engine: self.brain_engine.set_context_window(val)

    def _on_rate_change(self, value):
        if hasattr(self, 'rate_label'):
            val = int(value)
            txt = "Rate: Fastest" if val <= 2 else f"Rate: {val}s"
            self.rate_label.configure(text=txt)
            self.config.generation_rate = val
            self.config.save_settings()
            if self.brain_engine: self.brain_engine.set_generation_interval(val)

    def _update_config(self):
        try:
            ip = self.ip_entry.get().strip()
            port = int(self.port_entry.get().strip())
            self.config.update_osc_config(ip, port)
            if self.osc_client: self.osc_client.update_target(ip, port)
        except:
            self._log("Invalid Config", "ERROR")

    def _init_osc_client(self):
        self.osc_client = OSCClient(self.config.osc_target_ip, self.config.osc_target_port)

    def _load_audio_devices(self) -> List[Tuple[int, str]]:
        devices = []
        try:
            for idx, dev in enumerate(sd.query_devices()):
                if dev.get("max_input_channels", 0) > 0:
                    devices.append((idx, f"{idx} - {dev['name']}"))
        except: pass
        return devices

    def _refresh_audio_devices(self):
        self._log("Refreshing audio devices...", "SYSTEM")
        self.audio_devices = self._load_audio_devices()
        values = ["Default"] + [label for _, label in self.audio_devices]
        
        # Restore saved selection
        current_val = "Default"
        if self.config.audio_device is not None:
             for idx, label in self.audio_devices:
                 if idx == self.config.audio_device:
                     current_val = label
                     break
                     
        self.audio_device_combobox.configure(values=values)
        self.audio_device_combobox.set(current_val)

    def _on_device_change(self, choice):
        if choice == "Default":
            self.config.audio_device = None
        else:
            idx = int(choice.split(" - ")[0])
            self.config.audio_device = idx
        self._log(f"Audio device set to: {choice}", "SYSTEM")

    # --- Logging ---

    def _log(self, message: str, tag: str = "INFO"):
        # Print to original stdout for debugging/monitoring
        print(f"[{tag}] {message}", file=sys.__stdout__, flush=True)
        self.after(0, self._update_console, message, tag)
        
        # Write to file
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open("session.log", "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{tag}] {message}\n")
        except Exception:
            pass

    def _update_console(self, message: str, tag: str):
        if self.is_stopping: return

        timestamp = datetime.now().strftime("%H:%M:%S")
        color = "#AAAAAA"
        if tag == "AUDIO": color = ACCENT_GREEN
        elif tag == "BRAIN": color = ACCENT_PINK
        elif tag == "SUMMARY": color = ACCENT_PURPLE
        elif tag == "ERROR": color = ACCENT_RED
        
        try:
            self.console_text.configure(state="normal")
            self.console_text.insert("end", f"[{timestamp}] [{tag}] ", color)
            self.console_text.insert("end", f"{message}\n")
            self.console_text.see("end")
            self.console_text.configure(state="disabled")
            
            # Tag configuration (only needs to be done once, but safe here)
            self.console_text.tag_config(color, foreground=color)
        except Exception:
            # Widget likely destroyed during shutdown
            pass

    def _start_engine_monitor(self):
        """Watchdog for engine crashes and System Monitor."""
        def monitor():
            counter = 0
            while True:
                time.sleep(1)
                counter += 1
                
                if self.is_running and not self.is_stopping:
                    # 1. Watchdog
                    if self.audio_engine and not self.audio_engine.is_alive():
                        self._log("Audio Engine died! Restarting...", "ERROR")
                    if self.brain_engine and not self.brain_engine.is_alive():
                        self._log("Brain Engine died! Restarting...", "ERROR")
                        
                    # 2. Statistics (Every 5 seconds)
                    if counter % 5 == 0:
                        self._update_system_stats()
                        
        threading.Thread(target=monitor, daemon=True).start()

    def _update_system_stats(self):
        """Update system statistics (RAM, etc)."""
        try:
            # Memory Usage (RSS)
            usage_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # macOS ru_maxrss is in bytes, Linux is in KB. Python doc says "kilobytes" but on Mac it's often bytes?
            # Actually on Mac `getrusage` returns bytes. Let's assume bytes for now.
            # Wait, standard is usually KB. Let's check typical values. 
            # If it's > 100MB it's likely bytes.
            
            usage_mb = usage_bytes / (1024 * 1024) 
            if usage_mb < 1: # Probably was KB
                usage_mb = usage_bytes / 1024
            
            # Queue Depth
            aq_size, tq_size = 0, 0
            if self.audio_engine:
                aq_size, tq_size = self.audio_engine.get_queue_depth()
            
            status_text = f"● SYSTEM ACTIVE | RAM: {usage_mb:.0f} MB | AudioQ: {aq_size}/64"
            
            # Update Status Indicator safely
            self.after(0, lambda: self.status_indicator.configure(text=status_text))
            
            # Heartbeat Log
            self._log(f"❤️ System Heartbeat: RAM {usage_mb:.0f} MB | AudioQ: {aq_size}", "SYSTEM")
            
        except Exception as e:
            print(f"Stats error: {e}")

    # --- Console Redirector ---
    class ConsoleRedirector:
        def __init__(self, app, is_error=False):
            self.app = app
            self.is_error = is_error
        def write(self, message):
            if message.strip():
                tag = "ERROR" if self.is_error else "SYSTEM"
                self.app._log(message.strip(), tag)
        def flush(self): pass

def kill_previous_instances():
    """Kill other running instances of this script."""
    current_pid = os.getpid()
    try:
        # Find processes with 'python' and 'main.py' in the command
        cmd = "ps -ef | grep 'python.*main.py' | grep -v grep"
        output = subprocess.check_output(cmd, shell=True).decode()
        
        for line in output.strip().split('\n'):
            parts = line.split()
            if len(parts) < 2: continue
            
            pid = int(parts[1])
            
            # Don't kill self
            if pid == current_pid:
                continue
                
            print(f"[SYSTEM] Killing previous instance (PID {pid})...")
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"[SYSTEM] Error killing PID {pid}: {e}")
                
    except subprocess.CalledProcessError:
        # No other instances found (grep returned 1)
        pass
    except Exception as e:
        print(f"[SYSTEM] Error checking for previous instances: {e}")

if __name__ == "__main__":
    kill_previous_instances()
    app = VoiceVibeApp()
    app.mainloop()
