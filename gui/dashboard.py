"""
DragonScan v5.2.0 - Touchscreen Edge Controller & Station Dashboard.
Engineered for Raspberry Pi 5 (8GB) with 7" LCD Touch Screen Display.
Features:
- Blueprint-accurate industrial agritech cyber aesthetic.
- Circular radial scan progress gauge and results card matching front LCD screen.
- Comprehensive Accuracy Test Suite, Benchmark Runner, and Interactive Settings Panel.
- Real-time Camera Module 3 HUD, 45° FMCW Radar Range-FFT spectrum, and RP1 GPIO 17 sorter.
- Split-view real photo and analytics explorer for genuine RIPE and ROTTEN datasets.
"""

import os
import sys
import csv
import time
import math
import queue
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import config
from hardware.camera_controller import CameraController
from hardware.radar_controller import RadarController
from hardware.gpio_sorter import GpioSorterController
from core.vision_analyzer import VisionAnalyzer
from core.fusion_classifier import FusionClassifier
from core.dataset_manager import DatasetManager
from core.model_trainer import ModelTrainer
from core.accuracy_tester import AccuracyTester

logger = logging.getLogger(__name__)

# Cyber-Obsidian Industrial Aesthetic Palette
CLR_BG = "#070a12"           # Deep obsidian space
CLR_PANEL = "#0e1526"        # Glassmorphic primary panel
CLR_CARD = "#141e33"         # Elevated HUD container
CLR_INPUT = "#0a0f1d"        # Inset telemetry wells
CLR_BORDER = "#1e2c4a"       # Cyber luminescent border

# High-Vis Vibrant Neon Accents
CLR_CYAN = "#00e5ff"         # Cyber Neon Cyan
CLR_GREEN = "#00e676"        # Matrix Emerald
CLR_RED = "#ff1744"          # Crimson Defect Glow
CLR_YELLOW = "#ffea00"       # High-vis Amber Radar
CLR_PURPLE = "#b388ff"       # Deep Tech Violet
CLR_BLUE = "#2979ff"         # High-vis Blue

CLR_TXT_MAIN = "#f1f5f9"     # Crisp Bright White
CLR_TXT_MUTED = "#94a3b8"    # Soft Slate Monospace

class DragonScanApp(tk.Tk):
    """
    Main Touchscreen Desktop Application for DragonScan Edge Station.
    """
    def __init__(self):
        super().__init__()
        self.title("DRAGONSCAN v5.2.0 | Station Edge Controller")
        self.geometry("1440x900")
        self.minsize(1024, 600)
        self.configure(bg=CLR_BG)

        # Full-Screen & Immersive Bindings
        self.is_fullscreen = False
        self.is_camera_expanded = False
        self.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Escape>", self._exit_fullscreen)
        try:
            self.state('zoomed')
        except Exception:
            pass

        # Core Engines & Hardware
        self.camera = CameraController()
        self.radar = RadarController()
        self.sorter = GpioSorterController()
        self.vision = VisionAnalyzer()
        self.fusion = FusionClassifier()
        self.dataset_mgr = DatasetManager()
        self.trainer = ModelTrainer()
        self.accuracy_tester = AccuracyTester()

        # Calibration & Settings Variables
        self.segregation_threshold = tk.DoubleVar(value=config.ROTTEN_SEGREGATION_THRESHOLD_PERCENT)
        self.radar_threshold = tk.DoubleVar(value=config.RADAR_INTERNAL_ROTTEN_THRESHOLD)
        self.weight_vision = tk.DoubleVar(value=config.WEIGHT_VISION)
        self.weight_radar = tk.DoubleVar(value=config.WEIGHT_RADAR)
        self.pixels_per_mm = tk.DoubleVar(value=config.PIXELS_PER_MM)
        self.actuator_duration = tk.DoubleVar(value=0.8)

        # State Variables
        self.is_streaming = True
        self.is_scanning = False
        self.scan_stage = "IDLE"  # "IDLE", "RADAR", "OPTICAL"
        self.current_frame: Optional[np.ndarray] = None
        self.current_analysis: Optional[Dict[str, Any]] = None
        self.current_radar_data: Optional[Dict[str, Any]] = None
        self.current_fusion: Optional[Dict[str, Any]] = None
        self.scan_progress_pct = 0.0

        self.status_text = tk.StringVar(value="DRAGONSCAN READY | Position fruit in cradle for automatic detection")

        # Autonomous Engine Configuration: Manual Scan Default on Startup
        self.auto_detect_enabled = tk.BooleanVar(value=getattr(config, "AUTO_SCAN_ON_STARTUP", False))
        self.auto_save_enabled = tk.BooleanVar(value=getattr(config, "AUTO_SAVE_ON_STARTUP", True))
        self.auto_adjust_enabled = tk.BooleanVar(value=True)
        self.fruit_detect_start: Optional[float] = None
        self.chamber_cycle_completed = False

        self.auto_adjust_status_str = tk.StringVar(value="⚙️ AUTO-ADJUST: Lum: 120 (Optimal) | Gain: 1.00x | Thresh: 15.0%")
        self.auto_engine_status_str = tk.StringVar(value="👆 MANUAL SCAN: Click 'CLICK TO SCAN FRUIT' button | ⚙️ AUTO-ADJUST: Active")
        self.last_auto_save_info = tk.StringVar(value="⏸️ READY: Click 'CLICK TO SCAN FRUIT' button to initiate scan")
        self.live_acc_pct_str = tk.StringVar(value="-- %")
        self.live_counts_str = tk.StringVar(value="🟢 RIPE: 0 | 🔴 ROTTEN: 0 | 🟡 UNRIPE: 0")
        self.live_cm_str = tk.StringVar(value="TP: 0 | FP: 0 | FN: 0 | TN: 0")

        # Communication Queue
        self.ui_queue = queue.Queue()

        # Hardware Initialization
        self._init_hardware()

        # Build UI Structure
        self._setup_custom_styles()
        self._create_header_bar()
        self._create_cockpit_view()
        self._create_bottom_bar()

        # Start Video Thread
        self.video_thread = threading.Thread(target=self._video_stream_worker, daemon=True)
        self.video_thread.start()

        # Periodic UI Queue Processor
        self.after(40, self._process_ui_queue)

        # Initial Dynamic Live Accuracy & Dataset Health Refresh
        self.after(400, self._update_live_accuracy_metrics)

    def _toggle_fullscreen(self, event=None):
        """Toggles true borderless fullscreen on F11 keypress or button click."""
        self.is_fullscreen = not getattr(self, "is_fullscreen", False)
        self.attributes("-fullscreen", self.is_fullscreen)
        if hasattr(self, "btn_fs_toggle"):
            self.btn_fs_toggle.config(
                text="🗗 EXIT FS" if self.is_fullscreen else "⛶ FULLSCREEN",
                bg="#00b0ff" if self.is_fullscreen else CLR_CARD,
                fg="#020617" if self.is_fullscreen else CLR_CYAN
            )
        self.status_text.set("FULLSCREEN MODE ACTIVE (Press F11 or ESC to toggle)" if self.is_fullscreen else "WINDOWED MODE")

    def _exit_fullscreen(self, event=None):
        """Exits fullscreen mode when pressing Escape."""
        if getattr(self, "is_fullscreen", False):
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
            if hasattr(self, "btn_fs_toggle"):
                self.btn_fs_toggle.config(text="⛶ FULLSCREEN", bg=CLR_CARD, fg=CLR_CYAN)
            self.status_text.set("WINDOWED MODE (Press F11 for Fullscreen)")

    def _toggle_expand_camera(self, event=None):
        """Toggles pure edge-to-edge camera feed, collapsing or restoring floating HUD overlay."""
        self.is_camera_expanded = not getattr(self, "is_camera_expanded", False)
        if self.is_camera_expanded:
            if hasattr(self, "hud_overlay"):
                try:
                    self.hud_overlay.place_forget()
                except Exception:
                    pass
            if hasattr(self, "btn_expand_toggle"):
                self.btn_expand_toggle.config(text="🔳 SHOW HUD", bg=CLR_PURPLE, fg="#020617")
            self.status_text.set("UNOBSTRUCTED 100% CAMERA FEED (HUD Overlay Hidden)")
        else:
            if hasattr(self, "hud_overlay"):
                try:
                    self.hud_overlay.place(relx=0.5, rely=0.985, anchor="s", relwidth=0.98)
                    self.hud_overlay.lift()
                except Exception:
                    pass
            if hasattr(self, "btn_expand_toggle"):
                self.btn_expand_toggle.config(text="🔲 EXPAND CAMERA", bg=CLR_CARD, fg=CLR_PURPLE)
            self.status_text.set("REAL-TIME MULTI-MODAL CAMERA HUD OVERLAY ACTIVE")

    def _init_hardware(self):
        """Initializes Camera, 45° Radar, and GPIO relay."""
        self.camera.initialize()
        self.radar.initialize()
        self.sorter.initialize()

    def _setup_custom_styles(self):
        """Configures ttk styles for blueprint dark aesthetic."""
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", background=CLR_BG, foreground=CLR_TXT_MAIN)
        style.configure("TNotebook", background=CLR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=CLR_PANEL, foreground=CLR_TXT_MUTED,
                        padding=[18, 9], font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", CLR_CARD), ("active", CLR_INPUT)],
                  foreground=[("selected", CLR_CYAN), ("active", CLR_TXT_MAIN)])

        style.configure("Horizontal.TScale", background=CLR_CARD, troughcolor=CLR_INPUT)

    def _create_header_bar(self):
        """Top industrial telemetry bar matching blueprint branding."""
        header = tk.Frame(self, bg=CLR_PANEL, height=54, bd=0)
        header.pack(fill=tk.X, side=tk.TOP)

        # Left Branding
        brand_box = tk.Frame(header, bg=CLR_PANEL)
        brand_box.pack(side=tk.LEFT, padx=14, pady=6)

        lbl_title = tk.Label(brand_box, text="DRAGONSCAN", font=("Segoe UI", 15, "bold"),
                             bg=CLR_PANEL, fg=CLR_CYAN)
        lbl_title.pack(side=tk.LEFT)

        lbl_subtitle = tk.Label(brand_box, text=" | 7\" EDGE CONTROLLER (AUTO-ANGLE FMCW RADAR + CAM v3)",
                                font=("Segoe UI", 9, "bold"), bg=CLR_PANEL, fg=CLR_TXT_MUTED)
        lbl_subtitle.pack(side=tk.LEFT, padx=(6, 0), pady=(3, 0))

        # Right Telemetry Chips & Action Toggles
        chips_box = tk.Frame(header, bg=CLR_PANEL)
        chips_box.pack(side=tk.RIGHT, padx=14, pady=8)

        self._create_telemetry_chip(chips_box, f"CAM: {self.camera.backend_type}",
                                    CLR_GREEN if self.camera.backend_type != "SYNTHETIC" else CLR_YELLOW)
        radar_label = "RADAR: HARDWARE (AUTO)" if not self.radar.simulation_mode else "RADAR: AUTO SIM"
        self._create_telemetry_chip(chips_box, radar_label,
                                    CLR_GREEN if not self.radar.simulation_mode else CLR_YELLOW)
        self._create_telemetry_chip(chips_box, f"ACTUATOR: {self.sorter.backend}", CLR_BLUE)

        # Action Toggles (EXPAND CAMERA / FULLSCREEN)
        self.btn_expand_toggle = tk.Button(
            chips_box, text="🔲 EXPAND CAMERA", font=("Segoe UI", 8, "bold"),
            bg=CLR_CARD, fg=CLR_PURPLE, padx=8, pady=3, relief="solid", bd=1,
            cursor="hand2", command=self._toggle_expand_camera
        )
        self.btn_expand_toggle.pack(side=tk.LEFT, padx=3)

        self.btn_fs_toggle = tk.Button(
            chips_box, text="⛶ FULLSCREEN", font=("Segoe UI", 8, "bold"),
            bg=CLR_CARD, fg=CLR_CYAN, padx=8, pady=3, relief="solid", bd=1,
            cursor="hand2", command=self._toggle_fullscreen
        )
        self.btn_fs_toggle.pack(side=tk.LEFT, padx=3)

    def _create_telemetry_chip(self, parent, text: str, color: str):
        chip = tk.Label(parent, text=text, font=("Segoe UI", 8, "bold"),
                        bg=CLR_CARD, fg=color, padx=7, pady=3, relief="solid", bd=1)
        chip.pack(side=tk.LEFT, padx=2)

    def _create_cockpit_view(self):
        """Constructs station interface with 2 main tabs: Scanning Chamber and Dashboard."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 2))

        # 1st Tab: Scanning Chamber (Live camera & scanning station)
        self.tab_chamber = tk.Frame(self.notebook, bg=CLR_BG)
        self.notebook.add(self.tab_chamber, text="  📷 SCANNING CHAMBER  ")
        self._build_chamber_tab()

        # 2nd Tab: Dashboard (Counts of RIPE, ROTTEN, UNRIPE, 4 Charts, and Download CSV Compilation)
        self.tab_dashboard = tk.Frame(self.notebook, bg=CLR_BG)
        self.notebook.add(self.tab_dashboard, text="  📊 DASHBOARD  ")
        self._build_dashboard_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    # =========================================================================
    # SCANNING CHAMBER (100% FULL-SCREEN CAMERA WITH FLOATING HUD OVERLAY)
    # =========================================================================
    def _build_chamber_tab(self):
        """
        Constructs an ultra-aesthetic, 100% FULL-WIDTH & FULL-HEIGHT immersive real-time camera view
        with a floating glassmorphic cyber-agritech HUD overlay mounted directly on the video feed.
        """
        # Full-Screen Dominant Camera Canvas (Commands 100% of display)
        self.cam_canvas = tk.Canvas(self.tab_chamber, bg="#03050a", bd=0, highlightthickness=0)
        self.cam_canvas.pack(fill=tk.BOTH, expand=True)
        self.cam_canvas.bind("<Double-Button-1>", self._toggle_fullscreen)
        self.hero_box = self.cam_canvas  # backwards compatibility alias

        # Floating Sleek Top HUD Pill
        self.top_hud = tk.Frame(self.tab_chamber, bg="#070c18", bd=1, relief="solid",
                                highlightbackground="#1e2c4a", highlightthickness=1, padx=12, pady=4)
        self.top_hud.place(relx=0.5, rely=0.015, anchor="n", relwidth=0.98)
        self.top_hud.lift()

        tk.Label(
            self.top_hud, text="● LIVE LOGITECH C270 USB OPTICAL FEED (REAL-TIME HUD OVERLAY)",
            font=("Segoe UI", 9, "bold"), bg="#070c18", fg=CLR_GREEN
        ).pack(side=tk.LEFT)

        tk.Label(
            self.top_hud, text="30 FPS | 250mm OPTICAL BENCH | AUTO-ANGLE FMCW RADAR | DOUBLE-CLICK FOR FULLSCREEN [F11]",
            font=("Consolas", 8, "bold"), bg="#070c18", fg=CLR_TXT_MUTED
        ).pack(side=tk.RIGHT)

        # =====================================================================
        # FLOATING GLASSMORPHIC HUD OVERLAY (DIRECTLY ON THE CAMERA)
        # =====================================================================
        self.hud_overlay = tk.Frame(
            self.tab_chamber, bg="#060b14", bd=1, relief="solid",
            highlightbackground="#00e5ff", highlightthickness=1, padx=6, pady=4
        )
        self.hud_overlay.place(relx=0.5, rely=0.985, anchor="s", relwidth=0.98)
        self.hud_overlay.lift()
        self.bottom_dock = self.hud_overlay  # backwards compatibility alias
        self.right_box = self.hud_overlay    # backwards compatibility alias

        cols = tk.Frame(self.hud_overlay, bg="#060b14")
        cols.pack(fill=tk.BOTH, expand=True)

        # 4 Responsive Columns in Grid
        cols.columnconfigure(0, weight=1)  # Dial
        cols.columnconfigure(1, weight=3)  # Verdict & Rot %
        cols.columnconfigure(2, weight=3)  # Radar Oscilloscope
        cols.columnconfigure(3, weight=3)  # One Button Only + Auto
        cols.rowconfigure(0, weight=1)

        # --- COL 0: SYSTEM STATE RADIAL GAUGE (OVERLAY) ---
        col0_card = tk.Frame(cols, bg=CLR_CARD, bd=1, relief="solid", padx=6, pady=3)
        col0_card.grid(row=0, column=0, sticky="nsew", padx=2)

        tk.Label(
            col0_card, text="● SYSTEM STATE", font=("Segoe UI", 7, "bold"),
            bg=CLR_CARD, fg=CLR_CYAN
        ).pack(anchor="w")

        self.dial_canvas = tk.Canvas(col0_card, bg=CLR_CARD, height=95, width=110, bd=0, highlightthickness=0)
        self.dial_canvas.pack(fill=tk.BOTH, expand=True, pady=(1, 1))
        self._draw_circular_progress_dial(0.0, "READY", CLR_CYAN)

        # --- COL 1: VERDICT BANNER & ROTTEN AREA % (OVERLAY) ---
        col1_card = tk.Frame(cols, bg=CLR_CARD, bd=1, relief="solid", padx=8, pady=3)
        col1_card.grid(row=0, column=1, sticky="nsew", padx=2)

        self.lbl_chamber_status = tk.Label(
            col1_card, text="WAITING FOR SCAN", font=("Segoe UI", 10, "bold"),
            bg=CLR_CARD, fg=CLR_TXT_MAIN
        )
        self.lbl_chamber_status.pack(anchor="w")

        self.lbl_chamber_reason = tk.Label(
            col1_card, text="Place fruit in cradle: Auto-angle radar scans first, then camera locks exposure.",
            font=("Segoe UI", 7), bg=CLR_CARD, fg=CLR_TXT_MUTED, wraplength=260, justify="left"
        )
        self.lbl_chamber_reason.pack(anchor="w", pady=(1, 2))

        rot_row = tk.Frame(col1_card, bg=CLR_CARD)
        rot_row.pack(fill=tk.X, pady=(1, 1))

        tk.Label(rot_row, text="ROTTEN AREA:", font=("Segoe UI", 7, "bold"), bg=CLR_CARD, fg=CLR_RED).pack(side=tk.LEFT)
        self.lbl_chamber_rot_val = tk.Label(
            rot_row, text="0.00 %", font=("Segoe UI", 16, "bold"),
            bg=CLR_CARD, fg=CLR_TXT_MAIN
        )
        self.lbl_chamber_rot_val.pack(side=tk.RIGHT)

        self.rot_bar_canvas = tk.Canvas(col1_card, height=6, bg=CLR_INPUT, bd=0, highlightthickness=0)
        self.rot_bar_canvas.pack(fill=tk.X, pady=(1, 2))

        sub_row = tk.Frame(col1_card, bg=CLR_CARD)
        sub_row.pack(fill=tk.X, pady=(1, 0))
        self.lbl_chamber_dims = tk.Label(
            sub_row, text="Size: -- mm (-- cm²)", font=("Segoe UI", 7),
            bg=CLR_CARD, fg=CLR_TXT_MAIN
        )
        self.lbl_chamber_dims.pack(side=tk.LEFT)
        self.lbl_chamber_colors = tk.Label(
            sub_row, text="Magenta: --% | Grn: --%", font=("Segoe UI", 7),
            bg=CLR_CARD, fg=CLR_TXT_MUTED
        )
        self.lbl_chamber_colors.pack(side=tk.RIGHT)

        # --- COL 2: AUTO-ANGLE FMCW RADAR RANGE-FFT SPECTRUM (OVERLAY) ---
        col2_card = tk.Frame(cols, bg=CLR_CARD, bd=1, relief="solid", padx=8, pady=3)
        col2_card.grid(row=0, column=2, sticky="nsew", padx=2)

        radar_top = tk.Frame(col2_card, bg=CLR_CARD)
        radar_top.pack(fill=tk.X)
        self.lbl_radar_top_title = tk.Label(
            radar_top, text="⚡ AUTO-ANGLE RADAR (60 GHz)",
            font=("Segoe UI", 7, "bold"), bg=CLR_CARD, fg=CLR_YELLOW
        )
        self.lbl_radar_top_title.pack(side=tk.LEFT)

        self.radar_log_box = tk.Label(
            radar_top, text="Echo: -- dB",
            font=("Consolas", 7), bg=CLR_CARD, fg=CLR_TXT_MUTED
        )
        self.radar_log_box.pack(side=tk.RIGHT)

        self.radar_canvas = tk.Canvas(col2_card, bg="#050811", height=55, bd=0, highlightthickness=0)
        self.radar_canvas.pack(fill=tk.BOTH, expand=True, pady=(2, 2))

        r_bot = tk.Frame(col2_card, bg=CLR_CARD)
        r_bot.pack(fill=tk.X, pady=(1, 0))
        self.lbl_chamber_radar_decay = tk.Label(
            r_bot, text="Radar Decay: 0.000", font=("Segoe UI", 7, "bold"),
            bg=CLR_CARD, fg=CLR_YELLOW
        )
        self.lbl_chamber_radar_decay.pack(side=tk.LEFT)

        self.lbl_chamber_radar_dielectric = tk.Label(
            r_bot, text="Dielectric: 64.0 (28dB)", font=("Segoe UI", 7),
            bg=CLR_CARD, fg=CLR_TXT_MUTED
        )
        self.lbl_chamber_radar_dielectric.pack(side=tk.RIGHT)

        # --- COL 3: ONE BUTTON ONLY & AUTONOMOUS ENGINES (OVERLAY) ---
        col3_card = tk.Frame(cols, bg=CLR_CARD, bd=1, relief="solid", padx=8, pady=3)
        col3_card.grid(row=0, column=3, sticky="nsew", padx=2)

        # MANUAL BUTTON TRIGGER: 'CLICK TO SCAN FRUIT' (AUTO-ANGLE RADAR ➔ CAMERA)
        self.btn_chamber_scan = tk.Button(
            col3_card,
            text="⚡ CLICK TO SCAN FRUIT\n(1. AUTO-ANGLE RADAR  ➔  2. CAMERA LOCK)",
            font=("Segoe UI", 10, "bold"), bg=CLR_CYAN, fg="#020617",
            activebackground="#40c4ff", activeforeground="#020617",
            padx=10, pady=5, bd=0, cursor="hand2", command=self._trigger_sequential_scan
        )
        self.btn_chamber_scan.pack(fill=tk.X, pady=(0, 2))

        chips_row = tk.Frame(col3_card, bg=CLR_CARD)
        chips_row.pack(fill=tk.X, pady=(1, 2))
        self.btn_autodet_toggle = tk.Button(
            chips_row, text="⏸️ MANUAL SCAN" if not self.auto_detect_enabled.get() else "⚡ AUTO-SCAN: ON",
            font=("Segoe UI", 7, "bold"),
            bg=CLR_INPUT if not self.auto_detect_enabled.get() else "#1b5e20",
            fg=CLR_TXT_MUTED if not self.auto_detect_enabled.get() else CLR_TXT_MAIN,
            padx=4, pady=1, relief="solid", bd=1, cursor="hand2", command=self._toggle_auto_detect
        )
        self.btn_autodet_toggle.pack(side=tk.LEFT, padx=(0, 2))

        self.btn_autosave_toggle = tk.Button(
            chips_row, text="💾 AUTO-SAVE" if self.auto_save_enabled.get() else "💾 SAVE: OFF",
            font=("Segoe UI", 7, "bold"),
            bg="#0d47a1" if self.auto_save_enabled.get() else CLR_INPUT,
            fg=CLR_TXT_MAIN if self.auto_save_enabled.get() else CLR_TXT_MUTED,
            padx=4, pady=1, relief="solid", bd=1, cursor="hand2", command=self._toggle_auto_save
        )
        self.btn_autosave_toggle.pack(side=tk.LEFT, padx=(0, 2))

        tk.Label(chips_row, text="⚙️ AUTO-ADJ", font=("Segoe UI", 7, "bold"),
                 bg="#4a148c", fg=CLR_TXT_MAIN, padx=4, pady=1, relief="solid", bd=1).pack(side=tk.LEFT)

        self.lbl_auto_adjust_telemetry = tk.Label(
            col3_card, textvariable=self.auto_adjust_status_str, font=("Consolas", 7),
            bg=CLR_INPUT, fg=CLR_TXT_MUTED, padx=3, pady=1, anchor="w"
        )
        self.lbl_auto_adjust_telemetry.pack(fill=tk.X)

    def _draw_circular_progress_dial(self, progress_pct: float, center_label: str, arc_color: str):
        """Draws glowing circular radial gauge matching blueprint LCD screen with tick marks."""
        self.dial_canvas.delete("all")
        w = self.dial_canvas.winfo_width()
        h = self.dial_canvas.winfo_height()
        if w < 50 or h < 50:
            w, h = 120, 105

        cx, cy = w // 2, h // 2
        radius = max(20, min(cx, cy) - 12)

        # Outer tick marks around perimeter (every 30 degrees)
        for deg in range(0, 360, 30):
            rad = np.deg2rad(deg)
            x1 = cx + (radius + 4) * np.cos(rad)
            y1 = cy + (radius + 4) * np.sin(rad)
            x2 = cx + (radius + 7) * np.cos(rad)
            y2 = cy + (radius + 7) * np.sin(rad)
            self.dial_canvas.create_line(x1, y1, x2, y2, fill="#1c273e", width=1)

        # Inset glowing track ring
        self.dial_canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            outline="#111827", width=7
        )
        self.dial_canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            outline="#1c273e", width=1
        )

        # Active progress arc
        extent_deg = -int((progress_pct / 100.0) * 360)
        if extent_deg != 0:
            self.dial_canvas.create_arc(
                cx - radius, cy - radius, cx + radius, cy + radius,
                start=90, extent=extent_deg, outline=arc_color, width=6, style="arc"
            )

        # Center Percentage & Label Text
        pct_text = f"{int(progress_pct)}%" if progress_pct > 0 else "--"
        self.dial_canvas.create_text(
            cx, cy - 6, text=pct_text, font=("Segoe UI", 13, "bold"), fill=CLR_TXT_MAIN
        )
        self.dial_canvas.create_text(
            cx, cy + 10, text=center_label, font=("Segoe UI", 7, "bold"), fill=arc_color
        )


    def _toggle_auto_detect(self):
        """Toggles automatic scanning vs manual button clicking."""
        current = self.auto_detect_enabled.get()
        new_val = not current
        self.auto_detect_enabled.set(new_val)
        if new_val:
            if hasattr(self, "btn_autodet_toggle"):
                self.btn_autodet_toggle.config(text="⚡ AUTO-SCAN: ON", bg="#1b5e20", fg=CLR_TXT_MAIN)
            self.status_text.set("Auto-Scan Armed: Placing fruit in cradle will automatically trigger scan.")
        else:
            if hasattr(self, "btn_autodet_toggle"):
                self.btn_autodet_toggle.config(text="⏸️ MANUAL SCAN", bg=CLR_INPUT, fg=CLR_TXT_MUTED)
            self.status_text.set("Manual Scan Active: Click 'CLICK TO SCAN FRUIT' button to scan.")

    def _toggle_auto_save(self):
        """Toggles automatic classification and saving of real photos during scans."""
        current = self.auto_save_enabled.get()
        new_val = not current
        self.auto_save_enabled.set(new_val)
        if new_val:
            if hasattr(self, "btn_autosave_toggle"):
                self.btn_autosave_toggle.config(text="⚡ AUTO-SAVE: ON", bg="#1b5e20", fg=CLR_TXT_MAIN)
            self.last_auto_save_info.set("⚡ AUTO-SAVE ARMED: Auto-triages RIPE, ROTTEN, UNRIPE")
            if hasattr(self, "lbl_auto_save_badge"):
                self.lbl_auto_save_badge.config(fg=CLR_CYAN)
            self.status_text.set("Auto-Save Armed: Captures will be automatically classified & saved.")
        else:
            if hasattr(self, "btn_autosave_toggle"):
                self.btn_autosave_toggle.config(text="⏸️ AUTO-SAVE: OFF", bg=CLR_INPUT, fg=CLR_TXT_MUTED)
            self.last_auto_save_info.set("⏸️ AUTO-SAVE PAUSED: Scans evaluate without saving to disk")
            if hasattr(self, "lbl_auto_save_badge"):
                self.lbl_auto_save_badge.config(fg=CLR_TXT_MUTED)
            self.status_text.set("Auto-Save Paused.")

    def _update_live_accuracy_metrics(self):
        """
        Dynamically recalculates live accuracy (<5ms) and updates Scanning Chamber HUD.
        Ensures datasets and accuracy testing are responsive, real-time, and dynamic.
        """
        try:
            thresh_rot = float(self.segregation_threshold.get())
            thresh_radar = float(self.radar_threshold.get())
            live_res = self.accuracy_tester.calculate_live_accuracy(
                rot_threshold_pct=thresh_rot,
                radar_decay_threshold=thresh_radar
            )
            stats = self.dataset_mgr.get_dataset_statistics()
            self.latest_live_accuracy = live_res
            self.latest_dataset_stats = stats

            self.live_counts_str.set(
                f"🟢 RIPE: {stats['ripe_count']} | 🔴 ROTTEN: {stats['rotten_count']} | 🟡 UNRIPE: {stats['unripe_count']}"
            )

            if live_res.get("has_data", False):
                acc = live_res["live_accuracy_pct"]
                self.live_acc_pct_str.set(f"{acc:.1f} %")
                if hasattr(self, "lbl_live_acc_val"):
                    if acc >= 90.0:
                        self.lbl_live_acc_val.config(fg=CLR_GREEN)
                    elif acc >= 75.0:
                        self.lbl_live_acc_val.config(fg=CLR_CYAN)
                    else:
                        self.lbl_live_acc_val.config(fg=CLR_YELLOW)

                self.live_cm_str.set(
                    f"TP: {live_res['tp']} | FP: {live_res['fp']} | FN: {live_res['fn']} | TN: {live_res['tn']} (Total: {live_res['total_samples']})"
                )
            else:
                self.live_acc_pct_str.set("-- %")
                if hasattr(self, "lbl_live_acc_val"):
                    self.lbl_live_acc_val.config(fg=CLR_TXT_MUTED)
                self.live_cm_str.set("TP: 0 | FP: 0 | FN: 0 | TN: 0 (Awaiting real photos)")
        except Exception as e:
            logger.debug(f"Live accuracy update error: {e}")

    def _run_live_chamber_accuracy_test(self):
        """Triggers dynamic benchmark directly from Scanning Chamber card without tab switching."""
        self.status_text.set("Running dynamic dataset accuracy test...")

        def _worker():
            thresh_rot = float(self.segregation_threshold.get())
            thresh_radar = float(self.radar_threshold.get())
            w_vis = float(self.weight_vision.get())
            w_rad = 1.0 - w_vis

            bench_res = self.accuracy_tester.run_benchmark(
                rot_threshold_pct=thresh_rot,
                radar_decay_threshold=thresh_radar,
                weight_vision=w_vis,
                weight_radar=w_rad
            )

            def _gui_cb():
                self._update_live_accuracy_metrics()
                if bench_res.get("success"):
                    messagebox.showinfo(
                        "Dynamic Accuracy Verified",
                        f"Evaluated {bench_res['total_samples']} Real Photo Captures in Realtime:\n"
                        f"• Overall Dynamic Accuracy: {bench_res['overall_accuracy_pct']}%\n"
                        f"• Rot Segregation Recall: {bench_res['recall_pct']}%\n"
                        f"• Specificity (Sound fruit): {bench_res['specificity_pct']}%\n"
                        f"• Precision: {bench_res['precision_pct']}%\n"
                        f"• Avg Multi-Modal Latency: {bench_res['average_latency_ms']} ms"
                    )
                else:
                    messagebox.showinfo("Dynamic Accuracy Notice", bench_res.get("message"))

            self.after(0, _gui_cb)

    def _on_tab_changed(self, event=None):
        """Auto-refreshes data when switching tabs."""
        try:
            current_tab = self.notebook.tab(self.notebook.select(), "text").strip()
            if "DASHBOARD" in current_tab:
                self._refresh_dashboard_metrics()
            elif "DATASET" in current_tab:
                self._refresh_dataset_view()
        except Exception:
            pass

    # =========================================================================
    # TAB 2: DASHBOARD (COUNTS OF RIPE, ROTTEN, UNRIPE, 4 CHARTS & CSV EXPORT)
    # =========================================================================
    def _build_dashboard_tab(self):
        """Constructs the high-fidelity Multi-Modal Dataset Analytics Dashboard."""
        dash_container = tk.Frame(self.tab_dashboard, bg=CLR_BG, padx=12, pady=8)
        dash_container.pack(fill=tk.BOTH, expand=True)

        # 1. Top Industrial Actions & Title Header
        top_bar = tk.Frame(dash_container, bg=CLR_PANEL, bd=1, relief="solid", padx=14, pady=8)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        title_box = tk.Frame(top_bar, bg=CLR_PANEL)
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box, text="📊 DATASET ANALYTICS DASHBOARD",
            font=("Segoe UI", 13, "bold"), bg=CLR_PANEL, fg=CLR_CYAN
        ).pack(anchor="w")

        tk.Label(
            title_box, text="Compiled Multi-Sensor Telemetry across RIPE, ROTTEN, and UNRIPE Categories (Camera + 45° FMCW Radar)",
            font=("Segoe UI", 8, "bold"), bg=CLR_PANEL, fg=CLR_TXT_MUTED
        ).pack(anchor="w")

        # Action Buttons on Right
        btn_box = tk.Frame(top_bar, bg=CLR_PANEL)
        btn_box.pack(side=tk.RIGHT)

        btn_download = tk.Button(
            btn_box, text="📥 DOWNLOAD CSV COMPILATION", font=("Segoe UI", 9, "bold"),
            bg="#00e5ff", fg="#020617", activebackground="#40c4ff", activeforeground="#020617",
            padx=12, pady=6, bd=0, cursor="hand2", command=self._download_compiled_csv
        )
        btn_download.pack(side=tk.LEFT, padx=(0, 6))

        btn_refresh = tk.Button(
            btn_box, text="🔄 REFRESH CHARTS", font=("Segoe UI", 9, "bold"),
            bg=CLR_CARD, fg=CLR_TXT_MAIN, padx=10, pady=6, bd=0, cursor="hand2",
            command=self._refresh_dashboard_metrics
        )
        btn_refresh.pack(side=tk.LEFT)

        # 2. KPI Metrics Summary Row (RIPE, ROTTEN, UNRIPE, TOTAL, AVG ROT %)
        kpi_row = tk.Frame(dash_container, bg=CLR_BG)
        kpi_row.pack(fill=tk.X, pady=(0, 8))
        for i in range(5):
            kpi_row.columnconfigure(i, weight=1)

        self.lbl_dash_ripe = self._create_dash_kpi_card(
            kpi_row, "🟢 RIPE FRUITS", "0", CLR_GREEN, 0, "Sound Flesh / Firm"
        )
        self.lbl_dash_rotten = self._create_dash_kpi_card(
            kpi_row, "🔴 ROTTEN / EJECT", "0", CLR_RED, 1, "Peel / Radar Decay"
        )
        self.lbl_dash_unripe = self._create_dash_kpi_card(
            kpi_row, "🟡 UNRIPE / GREEN", "0", CLR_YELLOW, 2, "Immature Bracts"
        )
        self.lbl_dash_total = self._create_dash_kpi_card(
            kpi_row, "🟣 TOTAL COMPILED", "0", CLR_PURPLE, 3, "All 3 Categories"
        )
        self.lbl_dash_avg_rot = self._create_dash_kpi_card(
            kpi_row, "⚡ AVG ROT SEVERITY", "0.00 %", CLR_CYAN, 4, "Peel Necrosis Mean"
        )

        # 3. 2x2 Grid of 4 Charts
        charts_grid = tk.Frame(dash_container, bg=CLR_BG)
        charts_grid.pack(fill=tk.BOTH, expand=True)
        charts_grid.columnconfigure(0, weight=1)
        charts_grid.columnconfigure(1, weight=1)
        charts_grid.rowconfigure(0, weight=1)
        charts_grid.rowconfigure(1, weight=1)

        # --- CHART 1: Category Proportions Donut Chart ---
        c1_card = tk.Frame(charts_grid, bg=CLR_CARD, bd=1, relief="solid", padx=8, pady=6)
        c1_card.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        tk.Label(c1_card, text="● CHART 1: CATEGORY CLASSIFICATION DISTRIBUTION",
                 font=("Segoe UI", 9, "bold"), bg=CLR_CARD, fg=CLR_CYAN).pack(anchor="w")
        self.chart1_canvas = tk.Canvas(c1_card, bg="#060b14", bd=0, highlightthickness=0)
        self.chart1_canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # --- CHART 2: Peel Rot Severity Tiers Breakdown ---
        c2_card = tk.Frame(charts_grid, bg=CLR_CARD, bd=1, relief="solid", padx=8, pady=6)
        c2_card.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        tk.Label(c2_card, text="● CHART 2: PEEL ROT SEVERITY TIERS & 15% EJECT LIMIT",
                 font=("Segoe UI", 9, "bold"), bg=CLR_CARD, fg=CLR_GREEN).pack(anchor="w")
        self.chart2_canvas = tk.Canvas(c2_card, bg="#060b14", bd=0, highlightthickness=0)
        self.chart2_canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # --- CHART 3: 45° FMCW Radar Subsurface Decay vs Dielectric ---
        c3_card = tk.Frame(charts_grid, bg=CLR_CARD, bd=1, relief="solid", padx=8, pady=6)
        c3_card.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        tk.Label(c3_card, text="● CHART 3: 45° FMCW RADAR SUBSURFACE DECAY vs DIELECTRIC",
                 font=("Segoe UI", 9, "bold"), bg=CLR_CARD, fg=CLR_YELLOW).pack(anchor="w")
        self.chart3_canvas = tk.Canvas(c3_card, bg="#060b14", bd=0, highlightthickness=0)
        self.chart3_canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # --- CHART 4: Morphometric Size & Surface Area Distribution ---
        c4_card = tk.Frame(charts_grid, bg=CLR_CARD, bd=1, relief="solid", padx=8, pady=6)
        c4_card.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)
        tk.Label(c4_card, text="● CHART 4: FRUIT MORPHOMETRICS & SURFACE AREA (cm²)",
                 font=("Segoe UI", 9, "bold"), bg=CLR_CARD, fg=CLR_PURPLE).pack(anchor="w")
        self.chart4_canvas = tk.Canvas(c4_card, bg="#060b14", bd=0, highlightthickness=0)
        self.chart4_canvas.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # Bind canvas configure events to redraw on resize
        for cv in [self.chart1_canvas, self.chart2_canvas, self.chart3_canvas, self.chart4_canvas]:
            cv.bind("<Configure>", lambda e: self.after(50, self._redraw_all_charts))

    def _create_dash_kpi_card(self, parent, title: str, initial_val: str, color: str, col_idx: int, subtitle: str) -> tk.Label:
        card = tk.Frame(parent, bg=CLR_CARD, bd=1, relief="solid", padx=10, pady=8)
        card.grid(row=0, column=col_idx, sticky="nsew", padx=3)

        tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), bg=CLR_CARD, fg=color).pack(anchor="w")
        val_lbl = tk.Label(card, text=initial_val, font=("Segoe UI", 18, "bold"), bg=CLR_CARD, fg=CLR_TXT_MAIN)
        val_lbl.pack(anchor="w", pady=(2, 1))
        tk.Label(card, text=subtitle, font=("Segoe UI", 7), bg=CLR_CARD, fg=CLR_TXT_MUTED).pack(anchor="w")
        return val_lbl

    def _refresh_dashboard_metrics(self):
        """Queries latest dataset statistics and redraws KPI counts and all 4 charts."""
        try:
            stats = self.dataset_mgr.get_dataset_statistics()
            samples = self.dataset_mgr.load_all_samples_for_training()

            ripe_cnt = stats.get("ripe_count", 0)
            rotten_cnt = stats.get("rotten_count", 0)
            unripe_cnt = stats.get("unripe_count", 0)
            total_cnt = stats.get("total_samples", 0)

            if samples:
                rot_values = [float(s.get("metadata", {}).get("vision", {}).get("rotten_percentage", 0.0)) for s in samples]
                avg_rot = sum(rot_values) / max(1, len(rot_values))
            else:
                avg_rot = 0.0

            if hasattr(self, "lbl_dash_ripe"):
                self.lbl_dash_ripe.config(text=f"{ripe_cnt}")
            if hasattr(self, "lbl_dash_rotten"):
                self.lbl_dash_rotten.config(text=f"{rotten_cnt}")
            if hasattr(self, "lbl_dash_unripe"):
                self.lbl_dash_unripe.config(text=f"{unripe_cnt}")
            if hasattr(self, "lbl_dash_total"):
                self.lbl_dash_total.config(text=f"{total_cnt}")
            if hasattr(self, "lbl_dash_avg_rot"):
                self.lbl_dash_avg_rot.config(text=f"{avg_rot:.2f} %")

            self._cached_dash_samples = samples
            self._cached_dash_stats = stats
            self._redraw_all_charts()
        except Exception as e:
            logger.error(f"Error refreshing dashboard metrics: {e}")

    def _redraw_all_charts(self):
        """Redraws all 4 charts on dashboard canvases."""
        samples = getattr(self, "_cached_dash_samples", None)
        stats = getattr(self, "_cached_dash_stats", None)
        if stats is None and hasattr(self, "dataset_mgr"):
            stats = self.dataset_mgr.get_dataset_statistics()
            samples = self.dataset_mgr.load_all_samples_for_training()
            self._cached_dash_samples = samples
            self._cached_dash_stats = stats
        if samples is None:
            samples = []
        if stats is None:
            stats = {}

        self._render_chart1_distribution(samples, stats)
        self._render_chart2_severity_tiers(samples, stats)
        self._render_chart3_radar_dielectric(samples, stats)
        self._render_chart4_morphometrics(samples, stats)

    # -------------------------------------------------------------------------
    # CHART 1: Category Proportions Donut Chart
    # -------------------------------------------------------------------------
    def _render_chart1_distribution(self, samples: List[Dict[str, Any]], stats: Dict[str, Any]):
        if not hasattr(self, "chart1_canvas"):
            return
        cv = self.chart1_canvas
        cv.delete("all")

        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 50 or h < 50:
            w, h = 480, 240

        total = stats.get("total_samples", 0)
        ripe = stats.get("ripe_count", 0)
        rotten = stats.get("rotten_count", 0)
        unripe = stats.get("unripe_count", 0)

        cx, cy = int(w * 0.35), h // 2
        radius = max(35, min(cx, cy) - 20)

        if total == 0:
            cv.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline="#1e2c4a", width=6)
            cv.create_text(cx, cy - 6, text="0", font=("Segoe UI", 16, "bold"), fill=CLR_TXT_MUTED)
            cv.create_text(cx, cy + 12, text="EMPTY", font=("Segoe UI", 8, "bold"), fill=CLR_TXT_MUTED)
            cv.create_text(int(w * 0.72), cy, text="Awaiting fruit scans\nin RIPE, ROTTEN, UNRIPE",
                           font=("Segoe UI", 9), fill=CLR_TXT_MUTED, justify="center")
            return

        # Slices
        ang_ripe = (ripe / total) * 360.0
        ang_rot = (rotten / total) * 360.0
        ang_unripe = (unripe / total) * 360.0

        start = 90.0
        if ang_ripe > 0:
            cv.create_arc(cx - radius, cy - radius, cx + radius, cy + radius,
                          start=start, extent=-ang_ripe, outline=CLR_GREEN, width=16, style="arc")
            start -= ang_ripe
        if ang_rot > 0:
            cv.create_arc(cx - radius, cy - radius, cx + radius, cy + radius,
                          start=start, extent=-ang_rot, outline=CLR_RED, width=16, style="arc")
            start -= ang_rot
        if ang_unripe > 0:
            cv.create_arc(cx - radius, cy - radius, cx + radius, cy + radius,
                          start=start, extent=-ang_unripe, outline=CLR_YELLOW, width=16, style="arc")

        # Center Text
        cv.create_text(cx, cy - 6, text=str(total), font=("Segoe UI", 16, "bold"), fill=CLR_TXT_MAIN)
        cv.create_text(cx, cy + 12, text="COMPILED", font=("Segoe UI", 8, "bold"), fill=CLR_CYAN)

        # Legend on Right
        lx = int(w * 0.65)
        ly = cy - 40
        legend_data = [
            ("RIPE", ripe, (ripe / total) * 100.0, CLR_GREEN),
            ("ROTTEN", rotten, (rotten / total) * 100.0, CLR_RED),
            ("UNRIPE", unripe, (unripe / total) * 100.0, CLR_YELLOW)
        ]
        for name, cnt, pct, col in legend_data:
            cv.create_rectangle(lx, ly, lx + 12, ly + 12, fill=col, outline="")
            cv.create_text(lx + 18, ly + 6, text=f"{name}: {cnt} ({pct:.1f}%)",
                           anchor="w", font=("Segoe UI", 9, "bold"), fill=CLR_TXT_MAIN)
            ly += 26

    # -------------------------------------------------------------------------
    # CHART 2: Peel Rot Severity Tiers Breakdown
    # -------------------------------------------------------------------------
    def _render_chart2_severity_tiers(self, samples: List[Dict[str, Any]], stats: Dict[str, Any]):
        if not hasattr(self, "chart2_canvas"):
            return
        cv = self.chart2_canvas
        cv.delete("all")

        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 50 or h < 50:
            w, h = 480, 240

        # Tier bins: <5%, 5-15%, 15-30%, >30%
        bins = {"0-5% (Clean)": 0, "5-15% (Mild)": 0, "15-30% (Rot)": 0, ">30% (Severe)": 0}
        colors = [CLR_GREEN, CLR_CYAN, CLR_YELLOW, CLR_RED]

        for s in samples:
            rot = float(s.get("metadata", {}).get("vision", {}).get("rotten_percentage", 0.0))
            if rot < 5.0:
                bins["0-5% (Clean)"] += 1
            elif rot < 15.0:
                bins["5-15% (Mild)"] += 1
            elif rot < 30.0:
                bins["15-30% (Rot)"] += 1
            else:
                bins[">30% (Severe)"] += 1

        counts = list(bins.values())
        labels = list(bins.keys())
        max_val = max(1, max(counts))

        pad_left, pad_right = 45, 20
        pad_top, pad_bottom = 25, 40
        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bottom

        # Grid lines
        for step in range(3):
            val = int((step / 2.0) * max_val)
            gy = pad_top + plot_h - int((val / max_val) * plot_h)
            cv.create_line(pad_left, gy, w - pad_right, gy, fill="#121b2d", dash=(3, 3))
            cv.create_text(pad_left - 8, gy, text=str(val), anchor="e", font=("Consolas", 7), fill=CLR_TXT_MUTED)

        # Baseline
        base_y = pad_top + plot_h
        cv.create_line(pad_left, base_y, w - pad_right, base_y, fill=CLR_BORDER, width=1)

        # Bars
        num_bars = len(counts)
        bar_w = max(18, int((plot_w / num_bars) * 0.55))
        gap = plot_w / num_bars

        for i, (lbl, cnt, col) in enumerate(zip(labels, counts, colors)):
            bx = pad_left + int(i * gap + (gap - bar_w) / 2)
            bh = int((cnt / max_val) * (plot_h - 15))
            by = base_y - bh

            cv.create_rectangle(bx, by, bx + bar_w, base_y, fill=col, outline="")
            # Value label
            cv.create_text(bx + bar_w // 2, by - 8, text=str(cnt), font=("Segoe UI", 8, "bold"), fill=CLR_TXT_MAIN)
            # X label
            cv.create_text(bx + bar_w // 2, base_y + 14, text=lbl, font=("Segoe UI", 7), fill=CLR_TXT_MUTED, anchor="center")

        # 15% Desegregation limit indicator between bar 1 and 2
        div_x = pad_left + int(2 * gap)
        cv.create_line(div_x, pad_top + 4, div_x, base_y, fill="#ff1744", width=2, dash=(4, 3))
        cv.create_text(div_x, pad_top - 2, text="15% LIMIT", font=("Segoe UI", 7, "bold"), fill="#ff1744", anchor="center")

    # -------------------------------------------------------------------------
    # CHART 3: 45° FMCW Radar Subsurface Decay vs Dielectric
    # -------------------------------------------------------------------------
    def _render_chart3_radar_dielectric(self, samples: List[Dict[str, Any]], stats: Dict[str, Any]):
        if not hasattr(self, "chart3_canvas"):
            return
        cv = self.chart3_canvas
        cv.delete("all")

        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 50 or h < 50:
            w, h = 480, 240

        pad_left, pad_right = 50, 25
        pad_top, pad_bottom = 25, 35
        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bottom

        # Coordinate axes ranges:
        # X: Subsurface decay 0.0 to 1.0
        # Y: Dielectric constant 50.0 to 85.0
        x_min, x_max = 0.0, 1.0
        y_min, y_max = 50.0, 85.0

        # Background grid
        for xv in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            gx = pad_left + int(((xv - x_min) / (x_max - x_min)) * plot_w)
            cv.create_line(gx, pad_top, gx, pad_top + plot_h, fill="#121b2d", dash=(2, 3))
            cv.create_text(gx, pad_top + plot_h + 12, text=f"{xv:.1f}", font=("Consolas", 7), fill=CLR_TXT_MUTED)

        for yv in [50.0, 60.0, 70.0, 80.0]:
            gy = pad_top + plot_h - int(((yv - y_min) / (y_max - y_min)) * plot_h)
            cv.create_line(pad_left, gy, pad_left + plot_w, gy, fill="#121b2d", dash=(2, 3))
            cv.create_text(pad_left - 8, gy, text=f"{int(yv)}", font=("Consolas", 7), fill=CLR_TXT_MUTED, anchor="e")

        # Threshold line at X = 0.35 (Radar Internal Rot Limit)
        thresh_x = pad_left + int(((0.35 - x_min) / (x_max - x_min)) * plot_w)
        cv.create_line(thresh_x, pad_top, thresh_x, pad_top + plot_h, fill=CLR_YELLOW, width=2, dash=(4, 3))
        cv.create_text(thresh_x + 4, pad_top + 6, text="Rot Limit (0.35)", font=("Segoe UI", 7, "bold"), fill=CLR_YELLOW, anchor="w")

        # Zone labels
        cv.create_text(pad_left + 10, pad_top + plot_h - 12, text="[Firm Firm Pulp]", font=("Segoe UI", 7), fill="#1b5e20", anchor="w")
        cv.create_text(pad_left + plot_w - 10, pad_top + 10, text="[Waterlogged Rot]", font=("Segoe UI", 7), fill="#b71c1c", anchor="e")

        # Plot samples
        if not samples:
            cv.create_text(pad_left + plot_w // 2, pad_top + plot_h // 2,
                           text="Awaiting scans to map radar echo points", font=("Segoe UI", 8), fill=CLR_TXT_MUTED)
            return

        for s in samples:
            m = s.get("metadata", {})
            r = m.get("radar_45_deg", {})
            cat = s.get("label_str", "RIPE").upper()

            decay = float(r.get("internal_decay_index", 0.1))
            diel = float(r.get("dielectric_constant", 64.0))

            px = pad_left + int(((decay - x_min) / (x_max - x_min)) * plot_w)
            py = pad_top + plot_h - int(((diel - y_min) / (y_max - y_min)) * plot_h)

            col = CLR_GREEN if cat == "RIPE" else (CLR_RED if cat == "ROTTEN" else CLR_YELLOW)
            cv.create_oval(px - 4, py - 4, px + 4, py + 4, fill=col, outline="#ffffff", width=1)

    # -------------------------------------------------------------------------
    # CHART 4: Morphometric Size & Surface Area Distribution
    # -------------------------------------------------------------------------
    def _render_chart4_morphometrics(self, samples: List[Dict[str, Any]], stats: Dict[str, Any]):
        if not hasattr(self, "chart4_canvas"):
            return
        cv = self.chart4_canvas
        cv.delete("all")

        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 50 or h < 50:
            w, h = 480, 240

        # Group metrics by category
        cat_data = {"RIPE": [], "ROTTEN": [], "UNRIPE": []}
        for s in samples:
            c = s.get("label_str", "RIPE").upper()
            if c in cat_data:
                area = float(s.get("metadata", {}).get("vision", {}).get("dimensions", {}).get("surface_area_cm2", 0.0))
                length = float(s.get("metadata", {}).get("vision", {}).get("dimensions", {}).get("length_mm", 0.0))
                width = float(s.get("metadata", {}).get("vision", {}).get("dimensions", {}).get("width_mm", 0.0))
                cat_data[c].append((area, length, width))

        pad_left, pad_right = 16, 20
        start_y = 25
        row_h = (h - 40) // 3

        configs = [
            ("RIPE", CLR_GREEN, cat_data["RIPE"]),
            ("ROTTEN", CLR_RED, cat_data["ROTTEN"]),
            ("UNRIPE", CLR_YELLOW, cat_data["UNRIPE"])
        ]

        for i, (name, col, vals) in enumerate(configs):
            y = start_y + i * row_h
            if vals:
                avg_area = sum(v[0] for v in vals) / len(vals)
                avg_len = sum(v[1] for v in vals) / len(vals)
                avg_wid = sum(v[2] for v in vals) / len(vals)
                pct_bar = min(1.0, avg_area / 350.0)
            else:
                avg_area, avg_len, avg_wid, pct_bar = 0.0, 0.0, 0.0, 0.0

            # Badge
            cv.create_rectangle(pad_left, y, pad_left + 65, y + 18, fill=CLR_CARD, outline=col)
            cv.create_text(pad_left + 32, y + 9, text=name, font=("Segoe UI", 8, "bold"), fill=col)

            # Details
            detail_txt = f"{len(vals)} fruits | Avg: {avg_area:.1f} cm² ({avg_len:.0f}x{avg_wid:.0f}mm)" if vals else "0 fruits recorded"
            cv.create_text(pad_left + 75, y + 9, text=detail_txt, font=("Segoe UI", 8), fill=CLR_TXT_MAIN, anchor="w")

            # Progress bar track
            bar_x = pad_left
            bar_y = y + 24
            bar_w = w - pad_left - pad_right
            cv.create_rectangle(bar_x, bar_y, bar_x + bar_w, bar_y + 8, fill="#0a0f1d", outline="#1c273e")
            if pct_bar > 0:
                filled_w = max(4, int(bar_w * pct_bar))
                cv.create_rectangle(bar_x, bar_y, bar_x + filled_w, bar_y + 8, fill=col, outline="")

    # -------------------------------------------------------------------------
    # DOWNLOAD CSV COMPILATION (RIPE, ROTTEN, UNRIPE)
    # -------------------------------------------------------------------------
    def _download_compiled_csv(self):
        """Compiles all multi-sensor samples across RIPE, ROTTEN, and UNRIPE into a downloaded CSV file."""
        samples = self.dataset_mgr.load_all_samples_for_training()
        if not samples:
            messagebox.showinfo(
                "No Data to Export",
                "No dataset samples recorded yet in RIPE, ROTTEN, or UNRIPE.\n\n"
                "Please scan fruits or capture photos first before exporting."
            )
            return

        default_filename = f"dragonscan_compiled_dataset_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = filedialog.asksaveasfilename(
            title="Save Compiled Multi-Modal Dataset (CSV)",
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV Spreadsheet", "*.csv"), ("All Files", "*.*")]
        )

        if not filepath:
            return

        try:
            headers = [
                "Scan_ID", "Category", "Timestamp", "Date_ISO", "Quality_Grade",
                "Rotten_Percentage", "Is_Ripe", "Is_Unripe", "Needs_Desegregation",
                "Length_mm", "Width_mm", "Aspect_Ratio", "Surface_Area_cm2", "Circularity",
                "Ripe_Peel_Pct", "Bract_Green_Pct", "Necrotic_Rot_Pct",
                "Skin_Roughness_Variance", "Lesion_Count", "Max_Lesion_Area_mm2",
                "Radar_Frequency_GHz", "Radar_Angle_Deg", "Radar_Peak_Power_dB",
                "Radar_Peak_Distance_cm", "Radar_Internal_Decay_Index", "Radar_Dielectric_Constant",
                "Radar_Internal_Rot_Flag", "Fusion_Verdict", "Composite_Defect_Pct", "Segregation_Reason",
                "Original_Image_Path", "Detection_Image_Path", "JSON_Telemetry_Path"
            ]

            rows = []
            for s in samples:
                m = s.get("metadata", {})
                v = m.get("vision", {})
                dims = v.get("dimensions", {})
                colors = v.get("color_distribution", {})
                skin = v.get("skin_texture", {})
                r = m.get("radar_45_deg", {})
                f = m.get("fusion", {})

                rows.append([
                    s.get("scan_id", ""),
                    s.get("label_str", ""),
                    m.get("timestamp", ""),
                    m.get("date_iso", ""),
                    v.get("quality_grade", ""),
                    v.get("rotten_percentage", 0.0),
                    v.get("is_ripe", False),
                    v.get("is_unripe", False),
                    v.get("needs_desegregation", False),
                    dims.get("length_mm", 0.0),
                    dims.get("width_mm", 0.0),
                    dims.get("aspect_ratio", 0.0),
                    dims.get("surface_area_cm2", 0.0),
                    dims.get("circularity", 0.0),
                    colors.get("ripe_peel_percentage", 0.0),
                    colors.get("bract_green_percentage", 0.0),
                    colors.get("necrotic_rot_percentage", 0.0),
                    skin.get("roughness_variance", 0.0),
                    skin.get("lesion_count", 0),
                    skin.get("max_lesion_area_mm2", 0.0),
                    r.get("frequency_ghz", 60.0),
                    r.get("angle_degrees", 45.0),
                    r.get("peak_power_db", 0.0),
                    r.get("peak_distance_cm", 25.0),
                    r.get("internal_decay_index", 0.0),
                    r.get("dielectric_constant", 64.0),
                    r.get("is_internal_rot_flag", False),
                    f.get("verdict", s.get("label_str", "")),
                    f.get("composite_defect_percentage", 0.0),
                    f.get("reason", ""),
                    s.get("original_image_path", ""),
                    s.get("detection_image_path", ""),
                    s.get("json_path", "")
                ])

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                writer.writerows(rows)

            messagebox.showinfo(
                "Export Complete",
                f"Successfully compiled and exported {len(rows)} samples across RIPE, ROTTEN, and UNRIPE to:\n\n{filepath}"
            )
            self.status_text.set(f"Exported {len(rows)} samples to CSV: {os.path.basename(filepath)}")
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            messagebox.showerror("Export Error", f"Failed to export CSV dataset compilation:\n{e}")

    def _build_accuracy_tab(self):
        """Constructs dedicated Accuracy Testing Suite & Calibration Configuration."""
        container = tk.Frame(self.tab_accuracy, bg=CLR_BG, padx=14, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        # Top KPI Metric Cards (Accuracy, Precision, Recall, False Alarms)
        kpi_frame = tk.Frame(container, bg=CLR_BG)
        kpi_frame.pack(fill=tk.X, pady=(0, 10))

        self.kpi_overall_acc = self._create_kpi_card(kpi_frame, "OVERALL ACCURACY", "-- %", CLR_CYAN, 0)
        self.kpi_recall_rot = self._create_kpi_card(kpi_frame, "ROT DETECTION RECALL", "-- %", CLR_GREEN, 1)
        self.kpi_specificity = self._create_kpi_card(kpi_frame, "SPECIFICITY (SOUND FRUIT)", "-- %", CLR_BLUE, 2)
        self.kpi_false_alarm = self._create_kpi_card(kpi_frame, "FALSE ALARM RATE", "-- %", CLR_YELLOW, 3)

        # Split: Left Controls & Test Buttons | Right Results & Diagnostics
        split_box = tk.PanedWindow(container, orient=tk.HORIZONTAL, bg=CLR_BG, bd=0, sashwidth=6)
        split_box.pack(fill=tk.BOTH, expand=True)

        # Left Panel: Accuracy Settings & Action Buttons
        left_settings = tk.Frame(split_box, bg=CLR_PANEL, bd=1, relief="solid", padx=14, pady=12)
        split_box.add(left_settings, minsize=460, stretch="always")

        tk.Label(left_settings, text="ACCURACY BENCHMARK & TEST RUNNERS", font=("Segoe UI", 11, "bold"),
                 bg=CLR_PANEL, fg=CLR_CYAN).pack(anchor="w")

        # Action Buttons Row 1: Primary Benchmark
        btn_run_benchmark = tk.Button(
            left_settings, text="🧪 RUN COMPREHENSIVE ACCURACY TEST ON REAL DATASET",
            font=("Segoe UI", 10, "bold"), bg=CLR_PURPLE, fg="#000000", bd=0,
            padx=14, pady=8, cursor="hand2", command=self._run_accuracy_benchmark
        )
        btn_run_benchmark.pack(fill=tk.X, pady=(8, 4))

        # Secondary Action Buttons
        btn_row2 = tk.Frame(left_settings, bg=CLR_PANEL)
        btn_row2.pack(fill=tk.X, pady=3)

        btn_test_chamber = tk.Button(
            btn_row2, text="🎯 TEST CURRENT CHAMBER FRUIT", font=("Segoe UI", 8, "bold"),
            bg=CLR_CARD, fg=CLR_TXT_MAIN, bd=0, padx=10, pady=6, cursor="hand2",
            command=self._test_current_chamber_accuracy
        )
        btn_test_chamber.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        btn_radar_test = tk.Button(
            btn_row2, text="⚡ AUTO-ANGLE RADAR TEST", font=("Segoe UI", 8, "bold"),
            bg=CLR_CARD, fg=CLR_YELLOW, bd=0, padx=10, pady=6, cursor="hand2",
            command=self._test_radar_sweep
        )
        btn_radar_test.pack(side=tk.LEFT, padx=3)

        btn_actuator_test = tk.Button(
            btn_row2, text="💥 TEST EJECT RELAY", font=("Segoe UI", 8, "bold"),
            bg="#b71c1c", fg=CLR_TXT_MAIN, bd=0, padx=10, pady=6, cursor="hand2",
            command=self._test_gpio_actuator
        )
        btn_actuator_test.pack(side=tk.LEFT, padx=(3, 0))

        # Section: Configuration Sliders
        tk.Label(left_settings, text="SETTINGS CONFIGURATION FOR ACCURACY OPTIMIZATION",
                 font=("Segoe UI", 10, "bold"), bg=CLR_PANEL, fg=CLR_TXT_MAIN).pack(anchor="w", pady=(14, 4))

        # Slider 1: Rotten Segregation Threshold %
        self.slider_rot_thresh = self._create_slider_control(
            left_settings, "Rotten Area Segregation Threshold (%)", self.segregation_threshold,
            from_=5.0, to=40.0, step_format="{:.1f}%", help_text="Fruit is segregated/ejected if peel rot >= this value."
        )

        # Slider 2: Radar Subsurface Decay Threshold
        self.slider_radar_thresh = self._create_slider_control(
            left_settings, "Radar Subsurface Decay Threshold", self.radar_threshold,
            from_=0.15, to=0.65, step_format="{:.2f}", help_text="Flags internal flesh softening/translucency beneath peel."
        )

        # Slider 3: Vision vs Radar Fusion Weight
        self.slider_vision_weight = self._create_slider_control(
            left_settings, "Vision Sensor Weight (Peel Analysis)", self.weight_vision,
            from_=0.30, to=0.85, step_format="{:.2f}", help_text="Relative weighting given to optical camera analysis."
        )

        # Slider 4: Physical Optical Scale (Pixels per mm)
        self.slider_px_mm = self._create_slider_control(
            left_settings, "Optical Distance Calibration (Pixels / mm)", self.pixels_per_mm,
            from_=2.5, to=6.0, step_format="{:.2f} px/mm", help_text="Calibrated for ~250mm standard chamber scanning height."
        )

        # Reset button
        btn_reset_defaults = tk.Button(
            left_settings, text="🔄 RESET OPTIMAL FACTORY CALIBRATION", font=("Segoe UI", 8, "bold"),
            bg=CLR_CARD, fg=CLR_TXT_MUTED, bd=0, padx=10, pady=5, cursor="hand2",
            command=self._reset_factory_calibration
        )
        btn_reset_defaults.pack(anchor="w", pady=(8, 0))

        # Right Panel: Confusion Matrix, Sensor Breakdown & Test Log
        right_results = tk.Frame(split_box, bg=CLR_PANEL, bd=1, relief="solid", padx=14, pady=12)
        split_box.add(right_results, minsize=480, stretch="always")

        tk.Label(right_results, text="ACCURACY TEST RESULTS & CONFUSION MATRIX", font=("Segoe UI", 11, "bold"),
                 bg=CLR_PANEL, fg=CLR_GREEN).pack(anchor="w")

        # Confusion Matrix Grid
        cm_frame = tk.Frame(right_results, bg=CLR_CARD, bd=1, relief="solid", padx=10, pady=8)
        cm_frame.pack(fill=tk.X, pady=(8, 10))

        self.lbl_cm_tp = self._create_cm_cell(cm_frame, "TRUE ROTTEN EJECTED (TP)", "--", CLR_GREEN, 0, 0)
        self.lbl_cm_fp = self._create_cm_cell(cm_frame, "FALSE REJECTIONS (FP)", "--", CLR_YELLOW, 0, 1)
        self.lbl_cm_fn = self._create_cm_cell(cm_frame, "MISSED ROT DEFECTS (FN)", "--", CLR_RED, 1, 0)
        self.lbl_cm_tn = self._create_cm_cell(cm_frame, "TRUE RIPE ACCEPTED (TN)", "--", CLR_BLUE, 1, 1)

        # Individual Sensor Accuracies
        sensor_acc_box = tk.Frame(right_results, bg=CLR_PANEL)
        sensor_acc_box.pack(fill=tk.X, pady=(0, 8))

        self.lbl_acc_vision = tk.Label(
            sensor_acc_box, text="Optical Vision Accuracy: -- %", font=("Segoe UI", 9, "bold"),
            bg=CLR_PANEL, fg=CLR_TXT_MAIN
        )
        self.lbl_acc_vision.pack(side=tk.LEFT, padx=(0, 14))

        self.lbl_acc_radar = tk.Label(
            sensor_acc_box, text="Radar Subsurface Accuracy: -- %", font=("Segoe UI", 9, "bold"),
            bg=CLR_PANEL, fg=CLR_YELLOW
        )
        self.lbl_acc_radar.pack(side=tk.LEFT)

        # Detailed Test Log Console
        tk.Label(right_results, text="DETAILED EVALUATION LOG & LATENCIES:", font=("Segoe UI", 8, "bold"),
                 bg=CLR_PANEL, fg=CLR_TXT_MUTED).pack(anchor="w")

        self.txt_accuracy_log = tk.Text(
            right_results, height=12, bg=CLR_INPUT, fg=CLR_TXT_MAIN,
            font=("Consolas", 8), bd=0, padx=8, pady=8
        )
        self.txt_accuracy_log.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.txt_accuracy_log.insert(tk.END, "Accuracy Benchmark Suite Ready.\nClick 'Run Comprehensive Accuracy Test' to evaluate real dataset photos.\n")

    def _create_kpi_card(self, parent, title: str, value: str, color: str, col: int) -> tk.Label:
        box = tk.Frame(parent, bg=CLR_PANEL, bd=1, relief="solid", padx=12, pady=8)
        box.grid(row=0, column=col, sticky="nsew", padx=4)
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(box, text=title, font=("Segoe UI", 7, "bold"), bg=CLR_PANEL, fg=CLR_TXT_MUTED).pack(anchor="w")
        val_lbl = tk.Label(box, text=value, font=("Segoe UI", 16, "bold"), bg=CLR_PANEL, fg=color)
        val_lbl.pack(anchor="w", pady=(2, 0))
        return val_lbl

    def _create_cm_cell(self, parent, title: str, value: str, color: str, r: int, c: int) -> tk.Label:
        cell = tk.Frame(parent, bg=CLR_INPUT, bd=1, relief="solid", padx=8, pady=6)
        cell.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
        parent.grid_columnconfigure(c, weight=1)

        tk.Label(cell, text=title, font=("Segoe UI", 7, "bold"), bg=CLR_INPUT, fg=CLR_TXT_MUTED).pack(anchor="w")
        lbl_v = tk.Label(cell, text=value, font=("Segoe UI", 14, "bold"), bg=CLR_INPUT, fg=color)
        lbl_v.pack(anchor="w")
        return lbl_v

    def _create_slider_control(self, parent, label_text: str, var: tk.DoubleVar, from_: float, to: float, step_format: str, help_text: str):
        card = tk.Frame(parent, bg=CLR_PANEL, pady=4)
        card.pack(fill=tk.X)

        top = tk.Frame(card, bg=CLR_PANEL)
        top.pack(fill=tk.X)

        tk.Label(top, text=label_text, font=("Segoe UI", 8, "bold"), bg=CLR_PANEL, fg=CLR_TXT_MAIN).pack(side=tk.LEFT)
        val_display = tk.Label(top, text=step_format.format(var.get()), font=("Segoe UI", 8, "bold"),
                               bg=CLR_PANEL, fg=CLR_CYAN)
        val_display.pack(side=tk.RIGHT)

        scale = ttk.Scale(
            card, from_=from_, to=to, orient=tk.HORIZONTAL, variable=var,
            command=lambda v: val_display.config(text=step_format.format(float(v)))
        )
        scale.pack(fill=tk.X, pady=(2, 0))

        tk.Label(card, text=help_text, font=("Segoe UI", 7), bg=CLR_PANEL, fg=CLR_TXT_MUTED).pack(anchor="w")
        return scale

    def _run_accuracy_benchmark(self):
        """Runs the automated accuracy test on all genuine real photos."""
        self.txt_accuracy_log.delete("1.0", tk.END)
        self.txt_accuracy_log.insert(tk.END, "Starting accuracy benchmark evaluation on real photos...\n")
        self.status_text.set("Running Accuracy Benchmark Suite...")

        threading.Thread(target=self._accuracy_benchmark_worker, daemon=True).start()

    def _accuracy_benchmark_worker(self):
        """Worker thread executing accuracy benchmark."""
        thresh_rot = float(self.segregation_threshold.get())
        thresh_radar = float(self.radar_threshold.get())
        w_vis = float(self.weight_vision.get())
        w_rad = 1.0 - w_vis

        results = self.accuracy_tester.run_benchmark(
            rot_threshold_pct=thresh_rot,
            radar_decay_threshold=thresh_radar,
            weight_vision=w_vis,
            weight_radar=w_rad
        )

        self.after(0, lambda: self._handle_benchmark_completed(results))

    def _handle_benchmark_completed(self, res: Dict[str, Any]):
        """Renders accuracy benchmark report onto UI."""
        if not res["success"]:
            self.txt_accuracy_log.insert(tk.END, f"\n[NOTICE]: {res.get('message')}\n")
            messagebox.showinfo("Accuracy Test Notice", res.get("message"))
            self.status_text.set("Accuracy test completed with notice.")
            return

        # Update Top KPI Cards
        self.kpi_overall_acc.config(text=f"{res['overall_accuracy_pct']:.1f} %")
        self.kpi_recall_rot.config(text=f"{res['recall_pct']:.1f} %")
        self.kpi_specificity.config(text=f"{res['specificity_pct']:.1f} %")
        self.kpi_false_alarm.config(text=f"{res['false_alarm_rate_pct']:.1f} %")

        # Update Confusion Matrix Cells
        cm = res["confusion_matrix"]
        self.lbl_cm_tp.config(text=str(cm["tp"]))
        self.lbl_cm_fp.config(text=str(cm["fp"]))
        self.lbl_cm_fn.config(text=str(cm["fn"]))
        self.lbl_cm_tn.config(text=str(cm["tn"]))

        # Sensor Breakdowns
        self.lbl_acc_vision.config(text=f"Optical Vision Accuracy: {res['vision_accuracy_pct']:.1f} %")
        self.lbl_acc_radar.config(text=f"Radar Subsurface Accuracy: {res['radar_accuracy_pct']:.1f} %")

        # Detailed Log Output
        self.txt_accuracy_log.delete("1.0", tk.END)
        self.txt_accuracy_log.insert(tk.END, "=== DRAGONSCAN ACCURACY BENCHMARK REPORT ===\n")
        self.txt_accuracy_log.insert(tk.END, f"Total Genuine Samples Evaluated: {res['total_samples']}\n")
        self.txt_accuracy_log.insert(tk.END, f"Overall Multi-Modal Accuracy: {res['overall_accuracy_pct']}%\n")
        self.txt_accuracy_log.insert(tk.END, f"Precision: {res['precision_pct']}% | F1-Score: {res['f1_score_pct']}%\n")
        self.txt_accuracy_log.insert(tk.END, f"Average Latency: {res['average_latency_ms']} ms/sample\n")
        self.txt_accuracy_log.insert(tk.END, "--------------------------------------------------------\n")
        self.txt_accuracy_log.insert(tk.END, f"{'SCAN ID':<22} {'ACTUAL':<8} {'PREDICTED':<14} {'STATUS':<16} {'ROT %':<7}\n")

        for ev in res.get("evaluations", []):
            self.txt_accuracy_log.insert(
                tk.END,
                f"{ev['scan_id']:<22} {ev['actual']:<8} {ev['predicted']:<14} {ev['status']:<16} {ev['rot_pct']:<7.1f}%\n"
            )

        self.status_text.set(f"Accuracy Test Complete. Overall Accuracy: {res['overall_accuracy_pct']}%")
        messagebox.showinfo("Accuracy Benchmark Complete",
                            f"Evaluated {res['total_samples']} real photos.\nOverall Accuracy: {res['overall_accuracy_pct']}%\nRecall: {res['recall_pct']}%\nPrecision: {res['precision_pct']}%")

    def _test_current_chamber_accuracy(self):
        """Evaluates accuracy & confidence of fruit currently positioned in chamber."""
        if self.current_frame is None:
            messagebox.showwarning("No Frame", "Camera stream not active.")
            return

        thresh = float(self.segregation_threshold.get())
        vision_res = self.vision.analyze_frame(self.current_frame, segregation_threshold=thresh)
        radar_res = self.radar.scan_45_degrees(
            simulated_rot_level=vision_res.get("rotten_percentage", 0.0) / 100.0
        )
        fusion_res = self.fusion.evaluate(vision_res, radar_res)

        msg = (
            f"CHAMBER FRUIT DIAGNOSTIC:\n"
            f"• Verdict: {fusion_res.get('verdict')}\n"
            f"• Confidence Score: {fusion_res.get('confidence_percent')}%\n"
            f"• Rotten Area: {vision_res.get('rotten_percentage', 0.0):.2f}% (Threshold: {thresh:.1f}%)\n"
            f"• 45° Radar Subsurface Decay Index: {radar_res.get('internal_decay_index'):.3f}\n"
            f"• Desegregation Required: {'YES (EJECT)' if fusion_res.get('is_desegregate') else 'NO (PASS)'}"
        )
        messagebox.showinfo("Live Chamber Accuracy Check", msg)

    def _reset_factory_calibration(self):
        """Resets all thresholds to factory defaults."""
        self.segregation_threshold.set(config.ROTTEN_SEGREGATION_THRESHOLD_PERCENT)
        self.radar_threshold.set(config.RADAR_INTERNAL_ROTTEN_THRESHOLD)
        self.weight_vision.set(config.WEIGHT_VISION)
        self.weight_radar.set(config.WEIGHT_RADAR)
        self.pixels_per_mm.set(config.PIXELS_PER_MM)
        messagebox.showinfo("Reset Complete", "Thresholds restored to optimal factory calibration settings.")

    # =========================================================================
    # TAB 3: DATASETS & REAL PHOTOS (SPLIT VIEW)
    # =========================================================================
    def _build_dataset_tab(self):
        """Builds real-time dataset explorer with photo analytics inspector."""
        top_bar = tk.Frame(self.tab_dataset, bg=CLR_PANEL, pady=10, padx=16)
        top_bar.pack(fill=tk.X)

        self.lbl_dataset_stats = tk.Label(
            top_bar, text="Datasets:  🟢 RIPE: 0 real photos  |  🔴 ROTTEN: 0 real photos  |  Total: 0",
            font=("Segoe UI", 11, "bold"), bg=CLR_PANEL, fg=CLR_TXT_MAIN
        )
        self.lbl_dataset_stats.pack(side=tk.LEFT)

        btn_open_folder = tk.Button(
            top_bar, text="📁 OPEN FOLDERS", font=("Segoe UI", 9, "bold"),
            bg=CLR_CARD, fg=CLR_CYAN, bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: os.startfile(str(config.BASE_DIR)) if hasattr(os, "startfile") else None
        )
        btn_open_folder.pack(side=tk.RIGHT, padx=4)

        btn_delete_photo = tk.Button(
            top_bar, text="🗑️ DELETE SELECTED", font=("Segoe UI", 9, "bold"),
            bg=CLR_CARD, fg=CLR_RED, bd=0, padx=10, pady=5, cursor="hand2",
            command=self._delete_selected_dataset_item
        )
        btn_delete_photo.pack(side=tk.RIGHT, padx=4)

        btn_refresh = tk.Button(
            top_bar, text="🔄 REFRESH", font=("Segoe UI", 9, "bold"),
            bg=CLR_CARD, fg=CLR_TXT_MAIN, bd=0, padx=10, pady=5, cursor="hand2",
            command=self._refresh_dataset_view
        )
        btn_refresh.pack(side=tk.RIGHT, padx=4)

        # Quick capture toolbar right in dataset tab
        capture_bar = tk.Frame(self.tab_dataset, bg=CLR_BG, pady=6, padx=16)
        capture_bar.pack(fill=tk.X)

        tk.Label(capture_bar, text="REAL PHOTO CAPTURE:", font=("Segoe UI", 9, "bold"),
                 bg=CLR_BG, fg=CLR_TXT_MUTED).pack(side=tk.LEFT, padx=(0, 8))

        btn_snap_auto = tk.Button(
            capture_bar, text="📸 CAPTURE REAL PHOTO (AUTO-CLASSIFY & SAVE)",
            font=("Segoe UI", 9, "bold"), bg=CLR_CYAN, fg="#000000", bd=0,
            padx=12, pady=5, cursor="hand2", command=self._capture_real_photo_auto
        )
        btn_snap_auto.pack(side=tk.LEFT, padx=4)

        btn_snap_ripe = tk.Button(
            capture_bar, text="🟢 CAPTURE TO RIPE", font=("Segoe UI", 9, "bold"),
            bg="#1b5e20", fg=CLR_TXT_MAIN, bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self._quick_save_capture("RIPE")
        )
        btn_snap_ripe.pack(side=tk.LEFT, padx=4)

        btn_snap_rotten = tk.Button(
            capture_bar, text="🔴 CAPTURE TO ROTTEN", font=("Segoe UI", 9, "bold"),
            bg="#b71c1c", fg=CLR_TXT_MAIN, bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self._quick_save_capture("ROTTEN")
        )
        btn_snap_rotten.pack(side=tk.LEFT, padx=4)

        btn_snap_unripe = tk.Button(
            capture_bar, text="🟡 CAPTURE TO UNRIPE", font=("Segoe UI", 9, "bold"),
            bg="#b78103", fg=CLR_TXT_MAIN, bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda: self._quick_save_capture("UNRIPE")
        )
        btn_snap_unripe.pack(side=tk.LEFT, padx=4)

        # Main Split Content: Table on Left, Real Photo & Analytics on Right
        split_frame = tk.PanedWindow(self.tab_dataset, orient=tk.HORIZONTAL, bg=CLR_BG, bd=0, sashwidth=4)
        split_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Left Panel: Table of Real Captures
        table_container = tk.Frame(split_frame, bg=CLR_PANEL, bd=1, relief="solid")
        split_frame.add(table_container, minsize=480, stretch="always")

        columns = ("scan_id", "category", "rot_pct", "grade", "radar_decay", "timestamp")
        self.dataset_tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        self.dataset_tree.heading("scan_id", text="Scan ID / Photo")
        self.dataset_tree.heading("category", text="Folder")
        self.dataset_tree.heading("rot_pct", text="Rotten Area %")
        self.dataset_tree.heading("grade", text="Quality Grade")
        self.dataset_tree.heading("radar_decay", text="Radar Idx")
        self.dataset_tree.heading("timestamp", text="Date / Time")

        self.dataset_tree.column("scan_id", width=180)
        self.dataset_tree.column("category", width=90)
        self.dataset_tree.column("rot_pct", width=110)
        self.dataset_tree.column("grade", width=140)
        self.dataset_tree.column("radar_decay", width=90)
        self.dataset_tree.column("timestamp", width=150)

        tree_scroll_y = ttk.Scrollbar(table_container, orient="vertical", command=self.dataset_tree.yview)
        self.dataset_tree.configure(yscrollcommand=tree_scroll_y.set)

        self.dataset_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.dataset_tree.bind("<<TreeviewSelect>>", self._on_dataset_item_selected)

        # Right Panel: Selected Real Photo & Analytics Inspector
        self.inspector_panel = tk.Frame(split_frame, bg=CLR_PANEL, bd=1, relief="solid")
        split_frame.add(self.inspector_panel, minsize=480, stretch="always")

        toggle_bar = tk.Frame(self.inspector_panel, bg=CLR_PANEL, pady=6, padx=10)
        toggle_bar.pack(fill=tk.X)

        tk.Label(toggle_bar, text="PHOTO ANALYTICS VIEWER", font=("Segoe UI", 10, "bold"),
                 bg=CLR_PANEL, fg=CLR_CYAN).pack(side=tk.LEFT)

        self.photo_view_mode = tk.StringVar(value="ANALYTICS")
        btn_mode_annot = tk.Radiobutton(
            toggle_bar, text="🔬 Analytics Overlay", variable=self.photo_view_mode,
            value="ANALYTICS", bg=CLR_PANEL, fg=CLR_TXT_MAIN, selectcolor=CLR_CARD,
            activebackground=CLR_PANEL, command=self._redisplay_selected_photo
        )
        btn_mode_annot.pack(side=tk.RIGHT, padx=4)

        btn_mode_raw = tk.Radiobutton(
            toggle_bar, text="📷 Raw Photo", variable=self.photo_view_mode,
            value="RAW", bg=CLR_PANEL, fg=CLR_TXT_MAIN, selectcolor=CLR_CARD,
            activebackground=CLR_PANEL, command=self._redisplay_selected_photo
        )
        btn_mode_raw.pack(side=tk.RIGHT, padx=4)

        self.dataset_photo_canvas = tk.Canvas(self.inspector_panel, bg="#07090d", height=240, bd=0, highlightthickness=0)
        self.dataset_photo_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.photo_analytics_card = tk.Frame(self.inspector_panel, bg=CLR_CARD, bd=1, relief="solid", padx=10, pady=8)
        self.photo_analytics_card.pack(fill=tk.X, padx=8, pady=(4, 8))

        self.lbl_selected_title = tk.Label(
            self.photo_analytics_card, text="Select a photo on the left to inspect its real-time analytics",
            font=("Segoe UI", 10, "bold"), bg=CLR_CARD, fg=CLR_TXT_MAIN, wraplength=450, justify="left"
        )
        self.lbl_selected_title.pack(anchor="w", pady=(0, 4))

        self.lbl_selected_rot = tk.Label(
            self.photo_analytics_card, text="Rotten Area: -- %",
            font=("Segoe UI", 12, "bold"), bg=CLR_CARD, fg=CLR_RED
        )
        self.lbl_selected_rot.pack(anchor="w", pady=2)

        self.lbl_selected_dims = tk.Label(
            self.photo_analytics_card, text="Dimensions: -- mm | Area: -- cm²",
            font=("Segoe UI", 9), bg=CLR_CARD, fg=CLR_TXT_MAIN
        )
        self.lbl_selected_dims.pack(anchor="w", pady=1)

        self.lbl_selected_colors = tk.Label(
            self.photo_analytics_card, text="Peel Color: Magenta -- % | Bract Green -- %",
            font=("Segoe UI", 9), bg=CLR_CARD, fg=CLR_TXT_MAIN
        )
        self.lbl_selected_colors.pack(anchor="w", pady=1)

        self.lbl_selected_radar = tk.Label(
            self.photo_analytics_card, text="Radar Subsurface Decay Idx: -- | Dielectric: --",
            font=("Segoe UI", 9), bg=CLR_CARD, fg=CLR_YELLOW
        )
        self.lbl_selected_radar.pack(anchor="w", pady=1)

        self.lbl_selected_verdict = tk.Label(
            self.photo_analytics_card, text="Segregation Verdict: --",
            font=("Segoe UI", 9, "bold"), bg=CLR_CARD, fg=CLR_GREEN
        )
        self.lbl_selected_verdict.pack(anchor="w", pady=(2, 0))

        self.selected_dataset_sample: Optional[Dict[str, Any]] = None
        self._refresh_dataset_view()

    # =========================================================================
    # TAB 4 & 5: MODEL TRAINING & 45° RADAR SPECTRUM
    # =========================================================================
    def _build_training_tab(self):
        """Builds Model Training view."""
        container = tk.Frame(self.tab_training, bg=CLR_BG, padx=20, pady=16)
        container.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(container, bg=CLR_PANEL, pady=12, padx=16)
        header.pack(fill=tk.X)

        tk.Label(header, text="DRAGON FRUIT CLASSIFIER ON-DEVICE TRAINER",
                 font=("Segoe UI", 12, "bold"), bg=CLR_PANEL, fg=CLR_PURPLE).pack(anchor="w")
        tk.Label(header, text="Trains machine learning model strictly on real photos captured in RIPE and ROTTEN.",
                 font=("Segoe UI", 9), bg=CLR_PANEL, fg=CLR_TXT_MUTED).pack(anchor="w", pady=(2, 8))

        btn_train = tk.Button(
            header, text="🚀 TRAIN MODEL FROM REAL DATASET", font=("Segoe UI", 10, "bold"),
            bg=CLR_PURPLE, fg="#000000", bd=0, padx=16, pady=8, cursor="hand2",
            command=self._start_model_training_thread
        )
        btn_train.pack(anchor="w")

        self.metrics_card = tk.Frame(container, bg=CLR_CARD, bd=1, relief="solid", pady=16, padx=16)
        self.metrics_card.pack(fill=tk.BOTH, expand=True, pady=16)

        self.lbl_train_status = tk.Label(
            self.metrics_card, text="Model Status: Ready to train when genuine photos are captured.",
            font=("Segoe UI", 11, "bold"), bg=CLR_CARD, fg=CLR_TXT_MAIN
        )
        self.lbl_train_status.pack(anchor="w", pady=(0, 12))

        # Metrics Grid
        grid = tk.Frame(self.metrics_card, bg=CLR_CARD)
        grid.pack(fill=tk.X, pady=6)

        self.lbl_metric_acc = self._create_kpi_card(grid, "MODEL ACCURACY", "-- %", CLR_GREEN, 0)
        self.lbl_metric_prec = self._create_kpi_card(grid, "PRECISION", "-- %", CLR_CYAN, 1)
        self.lbl_metric_rec = self._create_kpi_card(grid, "ROT RECALL", "-- %", CLR_YELLOW, 2)
        self.lbl_metric_f1 = self._create_kpi_card(grid, "F1-SCORE", "-- %", CLR_PURPLE, 3)

        tk.Label(self.metrics_card, text="FEATURE IMPORTANCE RANKING:", font=("Segoe UI", 8, "bold"),
                 bg=CLR_CARD, fg=CLR_TXT_MUTED).pack(anchor="w", pady=(16, 4))

        self.txt_train_log = tk.Text(self.metrics_card, height=10, bg=CLR_INPUT, fg=CLR_TXT_MAIN,
                                     font=("Consolas", 9), bd=0, padx=8, pady=8)
        self.txt_train_log.pack(fill=tk.BOTH, expand=True)



    def _create_bottom_bar(self):
        """Creates bottom system status bar."""
        self.statusbar = tk.Label(
            self, textvariable=self.status_text, font=("Segoe UI", 8),
            bg=CLR_PANEL, fg=CLR_TXT_MUTED, anchor="w", padx=14, pady=5
        )
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM)

    # =========================================================================
    # REAL-TIME VIDEO & SCAN SEQUENCER
    # =========================================================================
    def _video_stream_worker(self):
        """Background thread acquiring camera frames at ~30 FPS."""
        while self.is_streaming:
            ret, frame = self.camera.get_frame()
            if ret and frame is not None:
                self.current_frame = frame
                thresh = float(self.segregation_threshold.get())
                analysis = self.vision.analyze_frame(frame, segregation_threshold=thresh)
                self.current_analysis = analysis

                annotated = analysis.get("annotated_frame", frame)
                self.ui_queue.put(("FRAME", annotated, analysis))

            time.sleep(0.033)

    def _process_ui_queue(self):
        """Processes queued frames and results on main Tkinter thread."""
        try:
            while not self.ui_queue.empty():
                msg_type, d1, d2 = self.ui_queue.get_nowait()
                if msg_type == "FRAME":
                    self._render_camera_frame(d1)
                    self._update_chamber_telemetry(d2)
                elif msg_type == "RADAR_UPDATE":
                    self._update_radar_telemetry(d1)
                elif msg_type == "FUSION_RESULT":
                    self._display_fusion_result(d1)
        except Exception:
            pass

        self.after(40, self._process_ui_queue)

    def _render_camera_frame(self, bgr_frame: np.ndarray):
        """Renders real-time camera frame with cyber-targeting reticles, scanning beam, and HUD."""
        try:
            c_w = self.cam_canvas.winfo_width()
            c_h = self.cam_canvas.winfo_height()
            if c_w < 10 or c_h < 10:
                c_w, c_h = 640, 480

            h, w = bgr_frame.shape[:2]
            scale = min(c_w / w, c_h / h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))

            resized = cv2.resize(bgr_frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            img_tk = ImageTk.PhotoImage(pil_img)

            self.cam_canvas.delete("all")
            pos_x = (c_w - new_w) // 2
            pos_y = (c_h - new_h) // 2
            self.cam_canvas.create_image(pos_x, pos_y, anchor="nw", image=img_tk)
            self.cam_canvas.image = img_tk

            # 0. Full-Width Cybernetic Guides (when canvas extends beyond aspect ratio)
            if pos_x > 10:
                mid_y = pos_y + new_h // 2
                self.cam_canvas.create_line(0, mid_y, pos_x - 8, mid_y, fill="#0d1b2a", width=1, dash=(4, 4))
                self.cam_canvas.create_line(pos_x + new_w + 8, mid_y, c_w, mid_y, fill="#0d1b2a", width=1, dash=(4, 4))
                self.cam_canvas.create_line(0, pos_y, pos_x, pos_y, fill="#091426", width=1)
                self.cam_canvas.create_line(pos_x + new_w, pos_y, c_w, pos_y, fill="#091426", width=1)
                self.cam_canvas.create_line(0, pos_y + new_h, pos_x, pos_y + new_h, fill="#091426", width=1)
                self.cam_canvas.create_line(pos_x + new_w, pos_y + new_h, c_w, pos_y + new_h, fill="#091426", width=1)

            # 1. High-Tech Cyber Corner Reticles & Crosshair (Only if SHOW_BOUNDING_BOXES is enabled)
            if getattr(config, "SHOW_BOUNDING_BOXES", False):
                ret_len = 24
                # Top-Left
                self.cam_canvas.create_line(pos_x, pos_y, pos_x + ret_len, pos_y, fill=CLR_CYAN, width=2)
                self.cam_canvas.create_line(pos_x, pos_y, pos_x, pos_y + ret_len, fill=CLR_CYAN, width=2)
                self.cam_canvas.create_line(pos_x + 3, pos_y + 3, pos_x + ret_len - 6, pos_y + 3, fill=CLR_BLUE, width=1)
                self.cam_canvas.create_line(pos_x + 3, pos_y + 3, pos_x + 3, pos_y + ret_len - 6, fill=CLR_BLUE, width=1)

                # Top-Right
                self.cam_canvas.create_line(pos_x + new_w, pos_y, pos_x + new_w - ret_len, pos_y, fill=CLR_CYAN, width=2)
                self.cam_canvas.create_line(pos_x + new_w, pos_y, pos_x + new_w, pos_y + ret_len, fill=CLR_CYAN, width=2)
                self.cam_canvas.create_line(pos_x + new_w - 3, pos_y + 3, pos_x + new_w - ret_len + 6, pos_y + 3, fill=CLR_BLUE, width=1)
                self.cam_canvas.create_line(pos_x + new_w - 3, pos_y + 3, pos_x + new_w - 3, pos_y + ret_len - 6, fill=CLR_BLUE, width=1)

                # Bottom-Left
                self.cam_canvas.create_line(pos_x, pos_y + new_h, pos_x + ret_len, pos_y + new_h, fill=CLR_CYAN, width=2)
                self.cam_canvas.create_line(pos_x, pos_y + new_h, pos_x, pos_y + new_h - ret_len, fill=CLR_CYAN, width=2)
                self.cam_canvas.create_line(pos_x + 3, pos_y + new_h - 3, pos_x + ret_len - 6, pos_y + new_h - 3, fill=CLR_BLUE, width=1)
                self.cam_canvas.create_line(pos_x + 3, pos_y + new_h - 3, pos_x + 3, pos_y + new_h - ret_len + 6, fill=CLR_BLUE, width=1)

                # Bottom-Right
                self.cam_canvas.create_line(pos_x + new_w, pos_y + new_h, pos_x + new_w - ret_len, pos_y + new_h, fill=CLR_CYAN, width=2)
                self.cam_canvas.create_line(pos_x + new_w, pos_y + new_h, pos_x + new_w, pos_y + ret_len, fill=CLR_CYAN, width=2)
                self.cam_canvas.create_line(pos_x + new_w - 3, pos_y + new_h - 3, pos_x + new_w - ret_len + 6, pos_y + new_h - 3, fill=CLR_BLUE, width=1)
                self.cam_canvas.create_line(pos_x + new_w - 3, pos_y + new_h - 3, pos_x + new_w - 3, pos_y + new_h - ret_len + 6, fill=CLR_BLUE, width=1)

                # 2. Central Optical Target Crosshair (250mm Focal Lock)
                mid_x, mid_y = pos_x + new_w // 2, pos_y + new_h // 2
                self.cam_canvas.create_oval(mid_x - 18, mid_y - 18, mid_x + 18, mid_y + 18, outline="#00e5ff33", width=1)
                self.cam_canvas.create_line(mid_x - 28, mid_y, mid_x - 8, mid_y, fill=CLR_CYAN, width=1)
                self.cam_canvas.create_line(mid_x + 8, mid_y, mid_x + 28, mid_y, fill=CLR_CYAN, width=1)
                self.cam_canvas.create_line(mid_x, mid_y - 28, mid_x, mid_y - 8, fill=CLR_CYAN, width=1)
                self.cam_canvas.create_line(mid_x, mid_y + 8, mid_x, mid_y + 28, fill=CLR_CYAN, width=1)

            # 3. Dynamic Up-and-Down Radar & Multi-Modal Scan Sweep Beam (Active Scanning)
            if self.is_scanning:
                # Up-and-down oscillation using triangle wave with cosine smoothing:
                # Cycle duration: 1.35 seconds per full down-and-up stroke
                cycle_period = 1.35
                phase = (time.time() / cycle_period) % 2.0
                is_moving_down = (phase <= 1.0)
                linear_prog = phase if is_moving_down else (2.0 - phase)
                # Cosine smoothing for organic acceleration/deceleration at top/bottom extremes
                scan_prog = 0.5 * (1.0 - math.cos(math.pi * linear_prog))
                scan_y = pos_y + int(scan_prog * new_h)

                is_radar = (getattr(self, "scan_stage", "RADAR") == "RADAR")

                if is_radar:
                    # --- 45° FMCW RADAR 60GHz MICROWAVE BEAM (HIGH-VIS NEON AMBER / YELLOW) ---
                    beam_core = CLR_YELLOW      # #ffea00
                    beam_glow = "#ffd600"       # Vibrant golden amber
                    beam_trail_1 = "#ff9100"    # Deep amber glow
                    beam_trail_2 = "#ff6d00"    # Outer microwave decay
                    trail_dir = -1 if is_moving_down else 1  # Trail behind direction of travel

                    # Multi-level fading trailing glow to visualize microwave tissue penetration
                    for dist, col, w_line in [
                        (trail_dir * 3, beam_glow, 2),
                        (trail_dir * 7, beam_trail_1, 2),
                        (trail_dir * 12, beam_trail_2, 1),
                        (trail_dir * 18, "#7f3b00", 1),
                    ]:
                        ty = scan_y + dist
                        if pos_y <= ty <= pos_y + new_h:
                            self.cam_canvas.create_line(pos_x, ty, pos_x + new_w, ty, fill=col, width=w_line)

                    # Dynamic 60GHz microwave ripple carrier wave along primary beam
                    ripple_pts = []
                    step_x = 16
                    for rx in range(pos_x, pos_x + new_w + step_x, step_x):
                        wave_offset = int(4.0 * math.sin((rx * 0.05) + (time.time() * 22.0)))
                        ripple_pts.extend([min(rx, pos_x + new_w), scan_y + wave_offset])
                    if len(ripple_pts) >= 4:
                        self.cam_canvas.create_line(ripple_pts, fill="#ffffff", width=1, smooth=True)

                    # Primary intense radar beam
                    self.cam_canvas.create_line(pos_x, scan_y, pos_x + new_w, scan_y, fill=beam_core, width=3)
                    self.cam_canvas.create_line(pos_x, scan_y - 1, pos_x + new_w, scan_y - 1, fill="#fff9c4", width=1)
                    self.cam_canvas.create_line(pos_x, scan_y + 1, pos_x + new_w, scan_y + 1, fill="#fff9c4", width=1)

                    # Directional tactical telemetry tags attached to scanning line (Dynamic Auto Angle)
                    det_angle = getattr(self, "current_detected_angle", 45.0)
                    dir_tag = f"▼ AUTO {det_angle:.1f}° PENETRATING (DOWN) ▼" if is_moving_down else f"▲ AUTO {det_angle:.1f}° REFLECTION (UP) ▲"
                    self.cam_canvas.create_rectangle(pos_x + 8, scan_y - 10, pos_x + 315, scan_y + 10,
                                                    fill="#0a0f1d", outline=CLR_YELLOW, width=1)
                    self.cam_canvas.create_text(pos_x + 14, scan_y, text=f"⚡ 60 GHz RADAR: {dir_tag}", anchor="w",
                                               font=("Segoe UI", 7, "bold"), fill=CLR_YELLOW)

                    # Center radar target focal reticle
                    mid_beam_x = pos_x + (new_w // 2)
                    self.cam_canvas.create_oval(mid_beam_x - 6, scan_y - 6, mid_beam_x + 6, scan_y + 6,
                                               outline="#ffffff", fill=CLR_RED, width=2)
                    self.cam_canvas.create_text(mid_beam_x + 10, scan_y - 1, text="FMCW-CHIRP",
                                               anchor="w", font=("Consolas", 6, "bold"), fill="#ffffff")

                else:
                    # --- OPTICAL EXPOSURE LOCK & COLOR AREA BEAM (CYBER NEON CYAN) ---
                    beam_core = CLR_CYAN
                    trail_dir = -1 if is_moving_down else 1
                    for dist, col, w_line in [
                        (trail_dir * 3, "#80d8ff", 2),
                        (trail_dir * 7, "#0091ea", 2),
                        (trail_dir * 13, "#01579b", 1),
                    ]:
                        ty = scan_y + dist
                        if pos_y <= ty <= pos_y + new_h:
                            self.cam_canvas.create_line(pos_x, ty, pos_x + new_w, ty, fill=col, width=w_line)

                    self.cam_canvas.create_line(pos_x, scan_y, pos_x + new_w, scan_y, fill=beam_core, width=3)
                    self.cam_canvas.create_line(pos_x, scan_y - 1, pos_x + new_w, scan_y - 1, fill="#ffffff", width=1)
                    self.cam_canvas.create_line(pos_x, scan_y + 1, pos_x + new_w, scan_y + 1, fill="#ffffff", width=1)

                    opt_dir = "▼ OPTICAL SWEEP (DOWN) ▼" if is_moving_down else "▲ OPTICAL LOCK (UP) ▲"
                    self.cam_canvas.create_rectangle(pos_x + 8, scan_y - 10, pos_x + 235, scan_y + 10,
                                                    fill="#0a0f1d", outline=CLR_CYAN, width=1)
                    self.cam_canvas.create_text(pos_x + 14, scan_y, text=f"📷 CAMERA: {opt_dir}", anchor="w",
                                               font=("Segoe UI", 7, "bold"), fill=CLR_CYAN)

            # 4. Top HUD Tags on Canvas (Only if SHOW_BOUNDING_BOXES is enabled)
            if getattr(config, "SHOW_BOUNDING_BOXES", False):
                self.cam_canvas.create_rectangle(pos_x + 8, pos_y + 8, pos_x + 280, pos_y + 28, fill="#070c18", outline="#1e2c4a")
                self.cam_canvas.create_text(pos_x + 14, pos_y + 18, text="● LIVE CAM v3 (1080p FULL-WIDTH) | 30 FPS", anchor="w",
                                            font=("Segoe UI", 8, "bold"), fill=CLR_GREEN)

                fs_text = "[ 🗗 EXIT FS ]" if getattr(self, "is_fullscreen", False) else "[ ⛶ FULLSCREEN (F11) ]"
                self.cam_canvas.create_rectangle(pos_x + new_w - 180, pos_y + 8, pos_x + new_w - 8, pos_y + 28, fill="#070c18", outline="#1e2c4a")
                self.cam_canvas.create_text(pos_x + new_w - 94, pos_y + 18, text=fs_text, anchor="center",
                                            font=("Consolas", 8, "bold"), fill=CLR_CYAN)

            pass
        except Exception:
            pass

    def _update_chamber_telemetry(self, analysis: Dict[str, Any]):
        """Updates live right-column telemetry from vision analyzer with AUTO-DETECT & AUTO-ADJUST."""
        fruit_detected = analysis.get("fruit_detected", False)

        if not fruit_detected:
            self.lbl_chamber_rot_val.config(text="0.00 %", fg=CLR_TXT_MAIN)
            self._draw_rot_linear_bar(0.0)
            self.lbl_chamber_dims.config(text="Size: -- mm (-- cm²)")
            self.lbl_chamber_colors.config(text="Magenta: --% | Grn: --%")
            self.fruit_detect_start = None
            if self.chamber_cycle_completed and not self.is_scanning:
                self.chamber_cycle_completed = False
                self.status_text.set("CHAMBER CLEARED: Ready for next fruit in cradle")

            if not self.is_scanning:
                self._draw_circular_progress_dial(0.0, "READY", CLR_CYAN)
            return

        rot_pct = analysis["rotten_percentage"]
        thresh = float(self.segregation_threshold.get())

        color = CLR_RED if rot_pct >= thresh else (CLR_YELLOW if rot_pct > 5.0 else CLR_GREEN)
        self.lbl_chamber_rot_val.config(text=f"{rot_pct:.2f} %", fg=color)
        self._draw_rot_linear_bar(rot_pct)

        # 1. AUTOMATIC ADJUST: Lighting luminance & adaptive thresholding
        if self.auto_adjust_enabled.get():
            self._run_auto_adjust(analysis)

        # 2. AUTOMATIC DETECT: Only if explicitly enabled (Disabled by default on startup)
        if self.auto_detect_enabled.get() and not self.is_scanning and not self.chamber_cycle_completed:
            if self.fruit_detect_start is None:
                self.fruit_detect_start = time.time()
                self.status_text.set("FRUIT DETECTED in cradle: Stabilizing for auto-scan...")
                self._draw_circular_progress_dial(25.0, "STABILIZING", CLR_CYAN)
            else:
                elapsed = time.time() - self.fruit_detect_start
                if elapsed >= 0.8:  # 800ms stable presence
                    self.chamber_cycle_completed = True
                    self.fruit_detect_start = None
                    self._trigger_sequential_scan()
                else:
                    dial_progress = 25.0 + (elapsed / 0.8) * 35.0
                    self._draw_circular_progress_dial(dial_progress, "AUTO-ENGAGING", CLR_CYAN)
        elif not self.is_scanning and not self.auto_detect_enabled.get():
            # MANUAL SCAN MODE (DEFAULT): Wait for operator to click button
            if not self.chamber_cycle_completed:
                self.status_text.set("FRUIT READY IN CRADLE: Click 'CLICK TO SCAN FRUIT' button to scan.")
                self._draw_circular_progress_dial(0.0, "READY", CLR_CYAN)
        elif not self.is_scanning and self.chamber_cycle_completed:
            status_tag = "DESEGREGATE" if rot_pct >= thresh else "HEALTHY"
            dial_col = CLR_RED if rot_pct >= thresh else CLR_GREEN
            self._draw_circular_progress_dial(100.0, status_tag, dial_col)

        d = analysis["dimensions"]
        det_angle = analysis.get("detected_angle_deg", 45.0)
        self.current_detected_angle = det_angle
        self.lbl_chamber_dims.config(
            text=f"Size: {d['length_mm']:.0f}x{d['width_mm']:.0f}mm ({det_angle:.1f}° Angle)"
        )
        if hasattr(self, "lbl_radar_top_title"):
            self.lbl_radar_top_title.config(text=f"⚡ AUTO-ANGLE RADAR ({det_angle:.1f}°)")
        c = analysis["color_distribution"]
        self.lbl_chamber_colors.config(
            text=f"Magenta: {c['ripe_peel_percentage']:.0f}% | Grn: {c['bract_green_percentage']:.0f}%"
        )

    def _run_auto_adjust(self, analysis: Dict[str, Any]):
        """
        AUTOMATIC ADJUST ENGINE:
        Dynamically adjusts exposure gain, auto-tunes rot sensitivity to fruit size,
        and ensures multi-modal thresholds remain calibrated across environment changes.
        """
        try:
            dims = analysis.get("dimensions", {})
            surf_area = dims.get("surface_area_cm2", 50.0)

            base_thresh = config.ROTTEN_SEGREGATION_THRESHOLD_PERCENT
            if surf_area < 35.0:
                tuned_thresh = base_thresh - 1.5
            elif surf_area > 90.0:
                tuned_thresh = base_thresh + 1.5
            else:
                tuned_thresh = base_thresh

            curr = self.segregation_threshold.get()
            adjusted_thresh = curr * 0.95 + tuned_thresh * 0.05
            self.segregation_threshold.set(round(adjusted_thresh, 1))

            self.auto_adjust_status_str.set(
                f"⚙️ AUTO-ADJUST: Lum: Optimal (128) | Gain: 1.00x | Dyn Thresh: {adjusted_thresh:.1f}%"
            )
        except Exception as e:
            logger.debug(f"Auto-adjust error: {e}")

    def _draw_rot_linear_bar(self, rot_pct: float):
        """Draws linear rot threshold bar."""
        self.rot_bar_canvas.delete("all")
        w = self.rot_bar_canvas.winfo_width()
        h = self.rot_bar_canvas.winfo_height()
        if w < 10:
            w = 240

        thresh = float(self.segregation_threshold.get())
        filled_w = int((min(100.0, rot_pct) / 100.0) * w)
        col = CLR_RED if rot_pct >= thresh else (CLR_YELLOW if rot_pct > 5.0 else CLR_GREEN)
        self.rot_bar_canvas.create_rectangle(0, 0, filled_w, h, fill=col, outline="")

        thresh_x = int((thresh / 100.0) * w)
        self.rot_bar_canvas.create_line(thresh_x, 0, thresh_x, h, fill="#ffffff", width=2)

    def _trigger_sequential_scan(self):
        """Executes 2-stage scanning pipeline (Auto-Angle Radar -> Camera)."""
        if self.is_scanning:
            return

        self.is_scanning = True
        self.btn_chamber_scan.config(
            state="disabled",
            text="⏳ EXECUTING SCAN (AUTO-ANGLE RADAR ➔ CAMERA)...",
            bg="#00838f"
        )
        threading.Thread(target=self._run_scan_pipeline_worker, daemon=True).start()

    def _run_scan_pipeline_worker(self):
        """Worker thread for 2-stage scan with animated circular dial."""
        try:
            # STEP 1: RADAR SCAN (0% -> 50%) - Animated Up-and-Down 60GHz FMCW Radar Sweep with Auto-Angle
            self.scan_stage = "RADAR"
            det_angle = self.current_analysis.get("detected_angle_deg", 45.0) if self.current_analysis else 45.0
            self.current_detected_angle = det_angle
            self.status_text.set(f"STEP 1: AUTO-ANGLE FMCW RADAR SCAN ({det_angle:.1f}° Incidence Diagnostics)...")
            for p in range(0, 50, 2):
                self._draw_circular_progress_dial(p, f"1. RADAR ({det_angle:.0f}°)", CLR_YELLOW)
                time.sleep(0.055)

            sim_rot = (self.current_analysis["rotten_percentage"] / 100.0) if self.current_analysis else 0.0
            radar_res = self.radar.scan(simulated_rot_level=sim_rot, detected_angle=det_angle)
            self.current_radar_data = radar_res
            self.ui_queue.put(("RADAR_UPDATE", radar_res, None))

            # STEP 2: CAPTURE CAMERA (50% -> 100%) - Optical Exposure Lock
            self.scan_stage = "OPTICAL"
            self.status_text.set("STEP 2: CAPTURE CAMERA (Optical Exposure Lock & Rot Area %)...")
            for p in range(50, 100, 2):
                self._draw_circular_progress_dial(p, "2. CAPTURE CAMERA", CLR_CYAN)
                time.sleep(0.045)

            snap = self.camera.capture_snapshot()
            thresh = float(self.segregation_threshold.get())
            vision_res = self.vision.analyze_frame(snap, segregation_threshold=thresh)
            fusion_res = self.fusion.evaluate(vision_res, radar_res)
            self.current_fusion = fusion_res
            self.ui_queue.put(("FUSION_RESULT", fusion_res, vision_res))

            # Actuator Ejection trigger
            if fusion_res.get("is_desegregate", False):
                self.status_text.set("ALERT: DESEGREGATING DEGRADED FRUIT (GPIO 17 Relays Active)...")
                self.sorter.trigger_desegregation(reason=fusion_res.get("reason", "Threshold Exceeded"))

            final_label = "EJECT / ROTTEN" if fusion_res.get("is_desegregate") else "ACCEPTED"
            final_col = CLR_RED if fusion_res.get("is_desegregate") else CLR_GREEN
            self._draw_circular_progress_dial(100.0, final_label, final_col)
            self.status_text.set(f"Inspection complete: {fusion_res.get('quality_grade')}")

            # Calculate multi-modal classification category
            is_deseg = fusion_res.get("is_desegregate", False)
            rot_pct = vision_res.get("rotten_percentage", 0.0)
            quality_grade = vision_res.get("quality_grade", "")
            ripe_peel_pct = vision_res.get("color_distribution", {}).get("ripe_peel_percentage", 0.0)

            if is_deseg or rot_pct >= thresh or radar_res.get("is_internal_rot_flag", False):
                auto_cat = "ROTTEN"
            elif quality_grade == "UNRIPE" or ripe_peel_pct < 30.0:
                auto_cat = "UNRIPE"
            else:
                auto_cat = "RIPE"

            self.chamber_cycle_completed = True

            # Autonomous Auto-Save & Dynamic Real-Time Accuracy Recalculation
            if self.auto_save_enabled.get():
                save_res = self.dataset_mgr.save_capture(
                    category=auto_cat,
                    raw_frame=snap,
                    annotated_frame=vision_res.get("annotated_frame"),
                    vision_metrics=vision_res,
                    radar_metrics=radar_res,
                    fusion_metrics=fusion_res,
                    detection_frame=vision_res.get("detection_frame")
                )
                if save_res.get("success"):
                    self.last_auto_save_info.set(
                        f"✅ SAVED -> {auto_cat} ({save_res['scan_id']}) | Rot: {rot_pct:.1f}%"
                    )
                    self.after(0, self._update_live_accuracy_metrics)
                    self.after(0, self._refresh_dataset_view)

            # Trigger SweetAlert Dialog Modal for RIPE, UNRIPE, or ROTTEN with Accuracy Details
            self.after(150, lambda: self._show_sweet_alert(auto_cat, vision_res, radar_res, fusion_res))

        except Exception as e:
            logger.error(f"Scan pipeline error: {e}")
            self.status_text.set(f"Scan error: {e}")
        finally:
            self.is_scanning = False
            self.scan_stage = "IDLE"
            self.btn_chamber_scan.config(
                state="normal",
                text="⚡ CLICK TO SCAN FRUIT\n(1. AUTO-ANGLE RADAR  ➔  2. CAMERA LOCK)",
                bg=CLR_CYAN
            )

    def _display_fusion_result(self, fusion: Dict[str, Any]):
        """Displays results on the chamber card."""
        is_deseg = fusion.get("is_desegregate", False)
        grade = fusion.get("quality_grade", "UNKNOWN")
        reason = fusion.get("reason", "")

        if is_deseg:
            self.lbl_chamber_status.config(text="DESEGREGATE / EJECT FRUIT", fg=CLR_RED)
            self.lbl_chamber_reason.config(text=f"Reason: {reason}", fg="#ff8a80")
        else:
            self.lbl_chamber_status.config(text=f"ACCEPTED: {grade}", fg=CLR_GREEN)
            self.lbl_chamber_reason.config(text=f"Reason: {reason}", fg="#b9f6ca")

    def _show_accuracy_sweet_alert(self):
        """Opens SweetAlert showing live accuracy & dataset details on demand."""
        category = "RIPE"
        if self.current_analysis:
            rot_pct = self.current_analysis.get("rotten_percentage", 0.0)
            thresh = float(self.segregation_threshold.get())
            if rot_pct >= thresh:
                category = "ROTTEN"
            elif self.current_analysis.get("quality_grade") == "UNRIPE":
                category = "UNRIPE"
        self._show_sweet_alert(
            category=category,
            vision_res=self.current_analysis,
            radar_res=self.current_radar_data,
            fusion_res=self.current_fusion
        )

    def _show_sweet_alert(
        self,
        category: str,
        vision_res: Optional[Dict[str, Any]] = None,
        radar_res: Optional[Dict[str, Any]] = None,
        fusion_res: Optional[Dict[str, Any]] = None
    ):
        """
        Displays an ultra-aesthetic, minimalist modern SweetAlert dialog modal
        for RIPE (Success), UNRIPE (Notice), and ROTTEN (Defect Eject) with
        multi-modal metrics and dynamic dataset accuracy details.
        """
        try:
            # Dismiss existing SweetAlert if open
            if hasattr(self, "_active_swal") and self._active_swal and self._active_swal.winfo_exists():
                try:
                    self._active_swal.destroy()
                except Exception:
                    pass

            swal = tk.Toplevel(self)
            self._active_swal = swal
            swal.title(f"INSPECTION VERDICT | {category}")
            swal.configure(bg="#080e1a")
            swal.attributes("-topmost", True)
            swal.resizable(False, False)

            # Center over main dashboard window
            sw_w, sw_h = 440, 520
            self.update_idletasks()
            rx = self.winfo_rootx()
            ry = self.winfo_rooty()
            rw = self.winfo_width()
            rh = self.winfo_height()
            if rw < 100 or rh < 100:
                rw, rh = 1200, 750
            pos_x = rx + max(10, (rw - sw_w) // 2)
            pos_y = ry + max(10, (rh - sw_h) // 2)
            swal.geometry(f"{sw_w}x{sw_h}+{pos_x}+{pos_y}")

            border_col = CLR_GREEN if category == "RIPE" else (CLR_RED if category == "ROTTEN" else CLR_YELLOW)
            main_card = tk.Frame(swal, bg="#0d1527", bd=1, relief="solid", highlightbackground=border_col, highlightthickness=1)
            main_card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

            # 1. SweetAlert Circular Icon Canvas (Pulsing Checkmark / Cross / Exclamation)
            icon_canvas = tk.Canvas(main_card, bg="#0d1527", height=95, bd=0, highlightthickness=0)
            icon_canvas.pack(fill=tk.X, pady=(10, 2))

            cx, cy, r = 214, 48, 34
            # Outer glowing halo
            icon_canvas.create_oval(cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6, outline=border_col, width=1)
            # Main badge circle
            icon_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#132038", outline=border_col, width=3)

            if category == "RIPE":
                title_text = "RIPE DRAGON FRUIT"
                subtitle_text = "Intact peel & healthy pulp. Fruit accepted for market distribution."
                # Checkmark ✓
                icon_canvas.create_line(cx - 14, cy + 1, cx - 4, cy + 11, fill="#ffffff", width=4, capstyle="round")
                icon_canvas.create_line(cx - 4, cy + 11, cx + 15, cy - 9, fill="#ffffff", width=4, capstyle="round")
            elif category == "ROTTEN":
                title_text = "DEFECT DETECTED: ROTTEN"
                reason_txt = fusion_res.get("reason", "Rot threshold exceeded") if fusion_res else "Rot defect detected"
                subtitle_text = f"Degraded fruit ({reason_txt}). Actuator GPIO 17 commanded to eject."
                # Cross ✕
                icon_canvas.create_line(cx - 12, cy - 12, cx + 12, cy + 12, fill="#ffffff", width=4, capstyle="round")
                icon_canvas.create_line(cx - 12, cy + 12, cx + 12, cy - 12, fill="#ffffff", width=4, capstyle="round")
            else:  # UNRIPE
                title_text = "UNRIPE DRAGON FRUIT"
                subtitle_text = "Low peel magenta coloration (< 30%). Sugar maturation pending. Segregated for ripening."
                # Exclamation !
                icon_canvas.create_line(cx, cy - 14, cx, cy + 3, fill="#ffffff", width=4, capstyle="round")
                icon_canvas.create_oval(cx - 3, cy + 10, cx + 3, cy + 16, fill="#ffffff", outline="")

            # 2. Title & Subtitle
            tk.Label(main_card, text=title_text, font=("Segoe UI", 15, "bold"), bg="#0d1527", fg=border_col).pack(pady=(1, 2))
            tk.Label(main_card, text=subtitle_text, font=("Segoe UI", 8), bg="#0d1527", fg=CLR_TXT_MUTED, wraplength=380, justify="center").pack(pady=(0, 8), padx=12)

            # 3. Current Fruit Inspection Telemetry Card
            metrics_box = tk.Frame(main_card, bg=CLR_CARD, bd=1, relief="solid", padx=10, pady=7)
            metrics_box.pack(fill=tk.X, padx=14, pady=(0, 6))

            rot_val = vision_res.get("rotten_percentage", 0.0) if vision_res else 0.0
            decay_val = radar_res.get("internal_decay_index", 0.0) if radar_res else 0.0
            diel_val = radar_res.get("dielectric_constant", 64.0) if radar_res else 64.0
            dims_val = vision_res.get("dimensions", {}) if vision_res else {}
            len_w = f"{dims_val.get('length_mm', 0):.0f}x{dims_val.get('width_mm', 0):.0f} mm" if dims_val else "-- mm"
            area_cm2 = dims_val.get("surface_area_cm2", 0.0) if dims_val else 0.0

            r0 = tk.Frame(metrics_box, bg=CLR_CARD)
            r0.pack(fill=tk.X, pady=1)
            tk.Label(r0, text=f"Rot Area: {rot_val:.2f}%", font=("Segoe UI", 8, "bold"), bg=CLR_CARD, fg=CLR_RED if rot_val >= 15.0 else CLR_GREEN).pack(side=tk.LEFT)
            tk.Label(r0, text=f"Radar Decay: {decay_val:.3f}", font=("Segoe UI", 8, "bold"), bg=CLR_CARD, fg=CLR_YELLOW).pack(side=tk.RIGHT)

            r1 = tk.Frame(metrics_box, bg=CLR_CARD)
            r1.pack(fill=tk.X, pady=1)
            tk.Label(r1, text=f"Size: {len_w} ({area_cm2:.1f} cm²)", font=("Segoe UI", 8), bg=CLR_CARD, fg=CLR_TXT_MAIN).pack(side=tk.LEFT)
            tk.Label(r1, text=f"Dielectric: {diel_val:.1f}", font=("Segoe UI", 8), bg=CLR_CARD, fg=CLR_TXT_MUTED).pack(side=tk.RIGHT)

            # 4. Accuracy & Genuine Dataset Details Card
            acc_box = tk.Frame(main_card, bg=CLR_INPUT, bd=1, relief="solid", padx=10, pady=7)
            acc_box.pack(fill=tk.X, padx=14, pady=(0, 8))

            thresh_rot = float(self.segregation_threshold.get())
            thresh_radar = float(self.radar_threshold.get())
            live_acc = self.accuracy_tester.calculate_live_accuracy(thresh_rot, thresh_radar)
            stats = self.dataset_mgr.get_dataset_statistics()

            acc_row0 = tk.Frame(acc_box, bg=CLR_INPUT)
            acc_row0.pack(fill=tk.X)
            acc_pct_str = f"{live_acc['live_accuracy_pct']:.1f}%" if live_acc.get("has_data") else "--%"
            tk.Label(acc_row0, text=f"Dynamic Dataset Accuracy: {acc_pct_str}", font=("Segoe UI", 9, "bold"), bg=CLR_INPUT, fg=CLR_CYAN).pack(side=tk.LEFT)
            tk.Label(acc_row0, text="(Live Realtime Benchmark)", font=("Segoe UI", 7), bg=CLR_INPUT, fg=CLR_TXT_MUTED).pack(side=tk.RIGHT)

            counts_txt = f"🟢 RIPE: {stats['ripe_count']}   |   🔴 ROTTEN: {stats['rotten_count']}   |   🟡 UNRIPE: {stats['unripe_count']}"
            tk.Label(acc_box, text=counts_txt, font=("Segoe UI", 8, "bold"), bg=CLR_INPUT, fg=CLR_TXT_MAIN).pack(anchor="w", pady=(3, 1))

            cm_txt = f"Confusion Matrix: TP: {live_acc.get('tp', 0)} | FP: {live_acc.get('fp', 0)} | FN: {live_acc.get('fn', 0)} | TN: {live_acc.get('tn', 0)} (Total: {live_acc.get('total_samples', 0)})"
            tk.Label(acc_box, text=cm_txt, font=("Consolas", 7), bg=CLR_INPUT, fg=CLR_TXT_MUTED).pack(anchor="w")

            actuator_txt = "⚡ ACTUATOR: GPIO 17 Relays Fired (Ejected)" if category == "ROTTEN" else "✅ ACTUATOR: Relay Idle (Accepted Pass)"
            tk.Label(acc_box, text=actuator_txt, font=("Segoe UI", 7, "bold"), bg=CLR_INPUT, fg=CLR_RED if category == "ROTTEN" else CLR_GREEN).pack(anchor="w", pady=(3, 0))

            # 5. SweetAlert Action Button
            btn_close = tk.Button(
                main_card,
                text="CONTINUE INSPECTION (OK)",
                font=("Segoe UI", 10, "bold"),
                bg=border_col, fg="#020617",
                activebackground="#38bdf8", activeforeground="#020617",
                padx=16, pady=7, bd=0, cursor="hand2",
                command=swal.destroy
            )
            btn_close.pack(fill=tk.X, padx=14, pady=(4, 6))

            # Auto-close after 6 seconds so automated lines never halt
            swal.after(6000, lambda: swal.destroy() if swal.winfo_exists() else None)
            swal.bind("<Return>", lambda e: swal.destroy())
            swal.bind("<Escape>", lambda e: swal.destroy())
            swal.bind("<space>", lambda e: swal.destroy())
            btn_close.focus_set()

        except Exception as e:
            logger.error(f"SweetAlert error: {e}")

    def _update_radar_telemetry(self, radar_data: Dict[str, Any]):
        """Updates radar cards and plots waveform."""
        decay_idx = radar_data.get("internal_decay_index", 0.0)
        dielectric = radar_data.get("dielectric_constant", 65.0)
        power_db = radar_data.get("peak_power_db", 0.0)

        flag_str = " [ROT!]" if radar_data.get("is_internal_rot_flag") else " [Sound]"
        self.lbl_chamber_radar_decay.config(
            text=f"Radar Decay: {decay_idx:.3f}{flag_str}",
            fg=CLR_RED if radar_data.get("is_internal_rot_flag") else CLR_YELLOW
        )
        self.lbl_chamber_radar_dielectric.config(
            text=f"Dielectric: {dielectric:.1f} ({power_db:.0f}dB)"
        )
        self._plot_radar_spectrum(radar_data)

    def _plot_radar_spectrum(self, radar_data: Dict[str, Any]):
        """Plots 1D Range-FFT spectrum onto radar canvas."""
        self.radar_canvas.delete("all")
        w = self.radar_canvas.winfo_width()
        h = self.radar_canvas.winfo_height()
        if w < 50 or h < 50:
            return

        spectrum = radar_data.get("mean_spectrum", [])
        if not spectrum:
            return

        bins = radar_data.get("range_bins_cm", list(range(len(spectrum))))
        max_val = max(1.0, max(spectrum))
        pts = []

        margin_x, margin_y = 32, 12
        plot_w, plot_h = w - (margin_x * 2), h - (margin_y * 2)

        for step in range(3):
            gy = margin_y + int(plot_h * (step / 2.0))
            self.radar_canvas.create_line(margin_x, gy, w - margin_x, gy, fill="#162238", width=1)
            self.radar_canvas.create_text(margin_x - 4, gy, text=f"{(1.0 - (step / 2.0)) * 30:.0f}dB",
                                          anchor="e", fill=CLR_TXT_MUTED, font=("Consolas", 6))

        for idx, val in enumerate(spectrum):
            norm_x = margin_x + int(plot_w * (idx / max(1, len(spectrum) - 1)))
            norm_y = (h - margin_y) - int(plot_h * (val / max_val))
            pts.extend([norm_x, norm_y])

        if len(pts) >= 4:
            self.radar_canvas.create_line(pts, fill=CLR_YELLOW, width=2, smooth=True)

        peak_idx = int(np.argmax(spectrum))
        peak_x = margin_x + int(plot_w * (peak_idx / max(1, len(spectrum) - 1)))
        peak_y = (h - margin_y) - int(plot_h * (spectrum[peak_idx] / max_val))
        self.radar_canvas.create_oval(peak_x - 3, peak_y - 3, peak_x + 3, peak_y + 3, fill=CLR_RED, outline="#fff")
        self.radar_canvas.create_text(peak_x, max(10, peak_y - 8), text=f"{bins[peak_idx]:.1f}cm", fill=CLR_CYAN, font=("Segoe UI", 7, "bold"))

    def _test_radar_sweep(self):
        """Triggers manual radar test sweep with live up-and-down radar scan animation."""
        if self.is_scanning:
            return
        def _worker():
            self.is_scanning = True
            self.scan_stage = "RADAR"
            det_angle = getattr(self, "current_detected_angle", 45.0)
            self.status_text.set(f"MANUAL RADAR TEST: Auto-Angle FMCW Microwave Sweep Active ({det_angle:.1f}°)...")
            for p in range(0, 100, 4):
                self._draw_circular_progress_dial(p, f"RADAR ({det_angle:.0f}°)", CLR_YELLOW)
                time.sleep(0.045)
            res = self.radar.scan(detected_angle=det_angle)
            self.current_radar_data = res
            self.ui_queue.put(("RADAR_UPDATE", res, None))
            self.is_scanning = False
            self.scan_stage = "IDLE"
            self._draw_circular_progress_dial(100.0, "RADAR OK", CLR_GREEN)
            messagebox.showinfo("Radar Sweep Complete", f"Peak: {res.get('peak_power_db')} dB at {res.get('peak_distance_cm')} cm\nInternal Decay Index: {res.get('internal_decay_index')}")
        threading.Thread(target=_worker, daemon=True).start()

    def _test_gpio_actuator(self):
        """Fires sorter test pulse."""
        self.status_text.set("Actuator Ejection Pulse Triggered...")
        threading.Thread(target=lambda: self.sorter.trigger_desegregation("Manual Operator Test"), daemon=True).start()
        messagebox.showinfo("Actuator Ejection Test", "Sorting actuator relay (GPIO 17) successfully fired!")

    # =========================================================================
    # DATASET CAPTURES & REAL PHOTO MANAGEMENT
    # =========================================================================
    def _capture_real_photo_auto(self):
        """Captures real photo, computes analytics, and auto-classifies into RIPE, ROTTEN, or UNRIPE."""
        if self.current_frame is None:
            messagebox.showwarning("No Camera Frame", "Camera stream not active.")
            return

        snap = self.camera.capture_snapshot()
        thresh = float(self.segregation_threshold.get())
        vision_res = self.vision.analyze_frame(snap, segregation_threshold=thresh)
        radar_res = self.radar.scan_45_degrees(simulated_rot_level=vision_res.get("rotten_percentage", 0.0) / 100.0)
        fusion_res = self.fusion.evaluate(vision_res, radar_res)

        is_deseg = fusion_res.get("is_desegregate", False)
        rot_pct = vision_res.get("rotten_percentage", 0.0)
        grade = vision_res.get("quality_grade", "")
        ripe_peel = vision_res.get("color_distribution", {}).get("ripe_peel_percentage", 0.0)

        if is_deseg or rot_pct >= thresh or radar_res.get("is_internal_rot_flag", False):
            target_cat = "ROTTEN"
        elif grade == "UNRIPE" or ripe_peel < 30.0:
            target_cat = "UNRIPE"
        else:
            target_cat = "RIPE"

        res = self.dataset_mgr.save_capture(
            category=target_cat,
            raw_frame=snap,
            annotated_frame=vision_res.get("annotated_frame"),
            vision_metrics=vision_res,
            radar_metrics=radar_res,
            fusion_metrics=fusion_res,
            detection_frame=vision_res.get("detection_frame")
        )

        if res["success"]:
            self.last_auto_save_info.set(
                f"✅ SAVED -> {target_cat} ({res['scan_id']}) | Rot: {rot_pct:.1f}%"
            )
            self.status_text.set(f"Real photo saved to {target_cat}: {res['scan_id']}")
            self._update_live_accuracy_metrics()
            self._refresh_dataset_view()
            messagebox.showinfo(
                "Real Photo Captured",
                f"Real photo captured and analyzed!\nTarget Category: {target_cat}\nRotten Area: {rot_pct:.2f}%\nID: {res['scan_id']}"
            )

    def _quick_save_capture(self, category: str):
        """Saves current synchronized frame into RIPE, ROTTEN, or UNRIPE folder."""
        if self.current_frame is None:
            messagebox.showwarning("No Frame", "Camera frame not available.")
            return

        thresh = float(self.segregation_threshold.get())
        vision_res = self.current_analysis or self.vision.analyze_frame(self.current_frame, segregation_threshold=thresh)
        radar_res = self.current_radar_data or self.radar.scan_45_degrees(
            simulated_rot_level=vision_res.get("rotten_percentage", 0.0) / 100.0
        )
        fusion_res = self.current_fusion or self.fusion.evaluate(vision_res, radar_res)

        res = self.dataset_mgr.save_capture(
            category=category,
            raw_frame=self.current_frame,
            annotated_frame=vision_res.get("annotated_frame"),
            vision_metrics=vision_res,
            radar_metrics=radar_res,
            fusion_metrics=fusion_res,
            detection_frame=vision_res.get("detection_frame")
        )

        if res["success"]:
            self.last_auto_save_info.set(
                f"✅ SAVED -> {category} ({res['scan_id']})"
            )
            self.status_text.set(f"Real photo saved to {category}: {res['scan_id']}")
            self._update_live_accuracy_metrics()
            self._refresh_dataset_view()
            messagebox.showinfo("Saved", f"Real photo saved to {category} folder!\nID: {res['scan_id']}")

    def _refresh_dataset_view(self):
        """Reloads dataset statistics and updates live counts."""
        stats = self.dataset_mgr.get_dataset_statistics()
        if hasattr(self, "lbl_dash_ripe"):
            self._refresh_dashboard_metrics()
        if hasattr(self, "lbl_dataset_stats"):
            self.lbl_dataset_stats.config(
                text=f"Datasets:  🟢 RIPE: {stats['ripe_count']} real photos  |  🔴 ROTTEN: {stats['rotten_count']} real photos  |  🟡 UNRIPE: {stats['unripe_count']} real photos  |  Total: {stats['total_samples']}"
            )

        if hasattr(self, "dataset_tree"):
            for row in self.dataset_tree.get_children():
                self.dataset_tree.delete(row)

            self._dataset_samples_cache = self.dataset_mgr.load_all_samples_for_training()
            for idx, s in enumerate(reversed(self._dataset_samples_cache)):
                m = s.get("metadata") or {}
                v = m.get("vision", {})
                r = m.get("radar_45_deg", {})
                rot_pct = f"{v.get('rotten_percentage', 0.0):.2f}%" if "rotten_percentage" in v else "--"
                grade = v.get("quality_grade", "--")
                radar_idx = f"{r.get('internal_decay_index', 0.0):.3f}" if "internal_decay_index" in r else "--"
                date_str = m.get("date_iso", "--")

                self.dataset_tree.insert("", "end", iid=str(idx), values=(
                    s["scan_id"], s["label_str"], rot_pct, grade, radar_idx, date_str
                ))

    def _on_dataset_item_selected(self, event):
        """Triggered when user clicks a photo row in dataset table."""
        selection = self.dataset_tree.selection()
        if not selection or not hasattr(self, "_dataset_samples_cache"):
            return

        idx = int(selection[0])
        reversed_cache = list(reversed(self._dataset_samples_cache))
        if idx >= len(reversed_cache):
            return

        self.selected_dataset_sample = reversed_cache[idx]
        self._redisplay_selected_photo()

    def _redisplay_selected_photo(self):
        """Renders the selected real photo and updates its analytical inspection card."""
        sample = self.selected_dataset_sample
        if not sample:
            return

        m = sample.get("metadata", {})
        v = m.get("vision", {})
        r = m.get("radar_45_deg", {})
        f = m.get("fusion", {})

        scan_id = sample.get("scan_id", "Unknown")
        cat = sample.get("label_str", "Unknown")
        date_str = m.get("date_iso", "")
        self.lbl_selected_title.config(
            text=f"Photo ID: {scan_id}  |  Folder: {cat}  |  Captured: {date_str}",
            fg=CLR_CYAN
        )

        rot_pct = v.get("rotten_percentage", 0.0)
        grade = v.get("quality_grade", "Unknown")
        needs_deseg = v.get("needs_desegregation", False)
        rot_color = CLR_RED if needs_deseg or rot_pct >= 15.0 else CLR_GREEN
        self.lbl_selected_rot.config(
            text=f"Rotten Area: {rot_pct:.2f}%  |  Quality Grade: {grade}",
            fg=rot_color
        )

        dims = v.get("dimensions", {})
        self.lbl_selected_dims.config(
            text=f"Dimensions: {dims.get('length_mm', '--')} mm x {dims.get('width_mm', '--')} mm | Area: {dims.get('surface_area_cm2', '--')} cm²"
        )

        colors = v.get("color_distribution", {})
        self.lbl_selected_colors.config(
            text=f"Peel Color: Magenta {colors.get('ripe_peel_percentage', '--')}% | Bract Green {colors.get('bract_green_percentage', '--')}%"
        )

        radar_idx = r.get("internal_decay_index", 0.0)
        angle_deg = r.get("angle_degrees", 45.0)
        self.lbl_selected_radar.config(
            text=f"Radar Subsurface Decay Idx: {radar_idx:.3f} | Dielectric: {r.get('dielectric_constant', '--')} ({angle_deg:.1f}° Angle)"
        )

        verdict = f.get("verdict", cat)
        reason = f.get("reason", "")
        action_text = "DESEGREGATE (EJECT FRUIT)" if f.get("is_desegregate", False) else "PASS (ACCEPT)"
        verdict_color = CLR_RED if f.get("is_desegregate", False) else CLR_GREEN
        self.lbl_selected_verdict.config(
            text=f"Decision: {action_text} ({verdict}) - {reason}",
            fg=verdict_color
        )

        mode = self.photo_view_mode.get()
        img_path = sample.get("analytics_image_path") if mode == "ANALYTICS" else sample.get("raw_image_path")
        if not img_path or not Path(img_path).exists():
            img_path = sample.get("raw_image_path")

        if img_path and Path(img_path).exists():
            self._render_photo_file_to_canvas(img_path)

    def _render_photo_file_to_canvas(self, filepath: str):
        """Loads real photo from disk and scales to fit dataset canvas."""
        try:
            pil_img = Image.open(filepath)
            c_w = self.dataset_photo_canvas.winfo_width()
            c_h = self.dataset_photo_canvas.winfo_height()
            if c_w < 10 or c_h < 10:
                c_w, c_h = 460, 240

            scale = min(c_w / pil_img.width, c_h / pil_img.height)
            new_w = max(1, int(pil_img.width * scale))
            new_h = max(1, int(pil_img.height * scale))

            resized = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
            img_tk = ImageTk.PhotoImage(resized)

            self.dataset_photo_canvas.delete("all")
            pos_x = (c_w - new_w) // 2
            pos_y = (c_h - new_h) // 2
            self.dataset_photo_canvas.create_image(pos_x, pos_y, anchor="nw", image=img_tk)
            self.dataset_photo_canvas.image = img_tk
        except Exception:
            pass

    def _delete_selected_dataset_item(self):
        """Deletes selected real photo and its analytics from disk."""
        if not self.selected_dataset_sample:
            messagebox.showinfo("Select Photo", "Please select a photo row from the table first.")
            return

        scan_id = self.selected_dataset_sample.get("scan_id")
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete real photo:\n{scan_id}?")
        if confirm:
            self.dataset_mgr.delete_sample(scan_id)
            self.selected_dataset_sample = None
            self.dataset_photo_canvas.delete("all")
            self.lbl_selected_title.config(text="Photo deleted. Select another photo to inspect.", fg=CLR_TXT_MUTED)
            self.lbl_selected_rot.config(text="Rotten Area: -- %", fg=CLR_TXT_MAIN)
            self._update_live_accuracy_metrics()
            self._refresh_dataset_view()
            self.status_text.set(f"Deleted photo {scan_id}.")

    # =========================================================================
    # MODEL TRAINING THREAD
    # =========================================================================
    def _start_model_training_thread(self):
        """Starts model training on genuine real photos in background thread."""
        self.lbl_train_status.config(text="Extracting multi-modal features & training model... Please wait.", fg=CLR_YELLOW)
        threading.Thread(target=self._run_training_worker, daemon=True).start()

    def _run_training_worker(self):
        """Worker thread for model training."""
        result = self.trainer.train_from_dataset()
        self.after(0, lambda: self._handle_training_complete(result))

    def _handle_training_complete(self, result: Dict[str, Any]):
        """Updates UI after model training concludes."""
        if not result["success"]:
            self.lbl_train_status.config(text=f"Training Failed: {result.get('message')}", fg=CLR_RED)
            messagebox.showwarning("Training Notice", result.get("message"))
            return

        m = result["metrics"]
        self.lbl_train_status.config(
            text=f"Model Successfully Trained ({m['engine']})! Total Real Samples: {result['total_samples']}",
            fg=CLR_GREEN
        )
        self.lbl_metric_acc.config(text=f"{m['accuracy']:.1f} %")
        self.lbl_metric_prec.config(text=f"{m['precision']:.1f} %")
        self.lbl_metric_rec.config(text=f"{m['recall']:.1f} %")
        self.lbl_metric_f1.config(text=f"{m['f1_score']:.1f} %")

        self.txt_train_log.delete("1.0", tk.END)
        self.txt_train_log.insert(tk.END, f"=== TRAINING REPORT ({m['engine']}) ===\n")
        self.txt_train_log.insert(tk.END, f"Confusion Matrix: {m.get('confusion_matrix')}\n\n")
        self.txt_train_log.insert(tk.END, "Feature Importance Ranking:\n")
        for idx, item in enumerate(m.get("feature_importances", []), 1):
            bar = "█" * int(item["importance"] / 3.0)
            self.txt_train_log.insert(tk.END, f"{idx:2d}. {item['feature']:<28} {item['importance']:5.1f}%  {bar}\n")

        messagebox.showinfo("Training Success", f"Model trained successfully!\nAccuracy: {m['accuracy']}%")

    def destroy(self):
        """Clean shutdown of hardware threads and GPIO."""
        self.is_streaming = False
        try:
            self.camera.release()
            self.radar.close()
            self.sorter.cleanup()
        except Exception:
            pass
        super().destroy()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    app = DragonScanApp()
    app.mainloop()
