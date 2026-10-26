# DragonScan v5.2.0: Raspberry Pi 5 Dragon Fruit Inspection & Desegregation Station

**DragonScan** is a multi-modal desktop and edge inspection system engineered for the **Raspberry Pi 5 (8GB)**. It solves the critical agricultural problem where dragon fruit peel appears normal externally, yet the internal flesh has undergone soft, translucent, or microbial degradation.

The system enforces a **sequential 2-stage scanning pipeline**:
1. **Stage 1: 45° FMCW Radar Subsurface Scan (Infineon BGT60TR13C 60 GHz)**: Measures dielectric permittivity, water absorption, and flesh firmness beneath the peel.
2. **Stage 2: Optical Camera Capture (Raspberry Pi Camera Module 3)**: Quantifies peel color (Ripe Magenta vs Bract Green vs Necrotic Rot), geometric size (Length, Width, Surface Area mm²/cm²), skin roughness, and **precise percentage of rotten peel area**.
3. **Automated Desegregation**: If the rotten percentage exceeds the configured threshold (default 15.0%) or internal radar decay is flagged, the system commands the Raspberry Pi 5 GPIO actuator to physically sort out/eject the degraded fruit.
4. **On-Device Model Training**: Train machine learning models directly inside the desktop GUI using experimental captures saved in [`RIPE/`](file:///c:/Users/paul/Documents/dragonfruit/RIPE) and [`ROTTEN/`](file:///c:/Users/paul/Documents/dragonfruit/ROTTEN).

---

## 🛠️ Hardware Bill of Materials (Raspberry Pi 5 Setup)
- **Raspberry Pi 5 (8GB RAM)**: Edge controller running Raspberry Pi OS Bookworm (64-bit).
- **Raspberry Pi Camera Module 3**: Wide/Standard with locked focus and exposure.
- **Pi 5 Camera Cable (22-pin to 15-pin mini CSI)**: Specific cable for Pi 5 CSI port.
- **Infineon Radar Kit (BGT60TR13C, 60 GHz FMCW)**: Connected via USB-C to Pi 5 USB 3.0 port.
- **Physical 45° Fixed Sensor Rig**: Frame holding radar sensor at 45° angle of incidence and camera vertically at 250 mm height.
- **Raspberry Pi Active Cooler**: Maintains temperature during real-time 30 FPS processing.
- **27W USB-C Power Supply**: Provides stable 5.1V / 5A for Pi 5 and attached sensors.
- **Sorting Actuator / Relay (GPIO 17)**: Connected to pneumatic solenoid or diverter arm.

---

## 🚀 Quick Start Guide

> [!TIP]
> **Complete Terminal Guide**: For a dedicated terminal setup and execution walkthrough on Raspberry Pi OS Bookworm, see the comprehensive guide: [RASPBERRY_PI_5_RUN_GUIDE.md](file:///c:/Users/paul/Documents/dragonfruit/RASPBERRY_PI_5_RUN_GUIDE.md).

### 1. Installation on Raspberry Pi 5 (Bookworm)
Open terminal on your Raspberry Pi 5 desktop:
```bash
# Update system packages
sudo apt update && sudo apt install -y python3-picamera2 python3-libgpiod python3-pil python3-tk python3-serial python3-opencv python3-numpy

# Clone / Navigate to dragonfruit directory
cd ~/dragonfruit

# Install required Python packages
pip install -r requirements.txt --break-system-packages
```

### 2. Launching Desktop Application
```bash
chmod +x run_dragonscan.sh
./run_dragonscan.sh
```
*(On Windows/Mac/Linux PCs without sensors connected, DragonScan automatically engages high-fidelity FMCW radar and camera simulations so you can test and build datasets instantly!)*

---

## 📊 Core Features & Operational Guide

### 1. Real-Time Vision & Rot Percentage Calculation
- **Color Segmentation**:
  - Healthy Ripe Magenta Peel: $H \in [140, 180]$ & $[0, 10]$
  - Bracts / Scales: $H \in [35, 85]$ (Yellow-Green)
  - Necrotic / Sunken Brown / Black Rot: $H \in [10, 30]$ & Low $V$ Dark Decay
- **Precise Rotten Percentage**:
  $$\text{Rotten Percentage (\%)} = \left( \frac{\text{Area of Necrotic Pixels}}{\text{Total Fruit Silhouette Area}} \right) \times 100$$
- **Geometric Dimensions**:
  - Length and Width calculated in millimeters using fixed optical ratio ($4.2 \text{ px/mm}$).
  - Surface Area calculated in $\text{cm}^2$.

### 2. Autonomous Cockpit (100% FULL-SCREEN CAMERA WITH FLOATING HUD OVERLAY)
The entire application operates inside an **ULTRA-AESTHETIC EDGE-TO-EDGE CAMERA COCKPIT** with a **FLOATING GLASSMORPHIC HUD OVERLAY** and **ONE BUTTON ONLY: `'CAPTURE FRUIT'`**:

- **Real-Time Full-Screen Camera**:
  - **100% Canvas Immersion**: Camera feed commands 100% full width and full height of the display.
  - **Floating Cyber HUD Overlay**: The circular system state dial, verdict status, rotten area %, linear neon threshold bar, and 45° FMCW radar oscilloscope float as a sleek glassmorphic overlay directly on the bottom of the video feed.
  - **F11 / `[ ⛶ FULLSCREEN ]`**: Toggles borderless full-screen inspection mode.
  - **Escape**: Instantly exits full-screen mode back to windowed layout.
  - **Double-Click Video Feed**: Toggles true full-screen camera view directly with touch or mouse.
  - **`[ 🔲 EXPAND CAMERA ]`**: Hides/shows the floating HUD overlay for 100% unobstructed camera vision.
  - **Cybernetic Targeting Reticles**: Dual glowing corner brackets, 250mm optical target crosshair, dynamic laser sweep animation during scans, and live on-canvas telemetry badges.

- **Click `CAPTURE FRUIT` (or Auto-Detect when fruit rests in cradle)**:
  - **STEP 1: 45° FMCW RADAR SCAN** (0%–50% on radial dial): Fires 64 chirps from Infineon BGT60TR13C 60 GHz radar, measures dielectric constant and subsurface internal decay index ($D$).
  - **STEP 2: CAPTURE CAMERA** (50%–100% on radial dial): Camera locks optical exposure, runs color segmentation, calculates precise rotten percentage, executes multi-modal fusion grading, automatically ejects degraded fruit via GPIO 17, and auto-saves genuine photo + telemetry.
  - **SweetAlert Modal Popup**: Pops up an ultra-aesthetic SweetAlert dialog displaying the category verdict (`RIPE` ✓, `UNRIPE` !, or `ROTTEN` ✕), sensor metrics, and live dynamic accuracy telemetry.

1. **🟢 AUTOMATIC DETECT (Optical & Radar Presence Tracking)**:
   - When a dragon fruit is placed into the cradle, the camera and radar detect its silhouette and echo.
   - The system stabilizes for 0.8 seconds and automatically triggers the sequential 2-stage scan without needing to click the button.
   - When the fruit is removed, the chamber automatically resets and rearms for the next fruit!

2. **💾 AUTOMATIC SAVE (Structured Subfolder Triaging)**:
   - Every scanned fruit is automatically triaged into [`RIPE/`](file:///c:/Users/paul/Documents/dragonfruit/RIPE), [`ROTTEN/`](file:///c:/Users/paul/Documents/dragonfruit/ROTTEN), or [`UNRIPE/`](file:///c:/Users/paul/Documents/dragonfruit/UNRIPE).
   - In each category, files are cleanly organized into 3 dedicated subfolders:
     - `original/`: Untouched, pristine raw camera photo (`<scan_id>_original.png`).
     - `detection/`: The photo with full object detection annotations, YOLO box, fruit contour, and rot zones (`<scan_id>_detection.png`).
     - `json/`: Full analytical JSON telemetry record (`<scan_id>.json`).
   - Zero fake or static photos generated.

3. **⚙️ AUTOMATIC ADJUST (Adaptive Calibration & Dynamic Tuning)**:
   - **Auto-Exposure / Lighting Adaptation**: Continuously computes luminance within the fruit silhouette and balances contrast gain.
   - **Dynamic Threshold Calibration**: Auto-adjusts rot threshold based on fruit surface area (scaling for small vs large dragon fruits) and compensates for baseline radar drift.
   - **Real-Time Dynamic Accuracy Recalculation**: Live accuracy percentage, dataset counts, and confusion matrix (TP, FP, FN, TN) are automatically re-evaluated in $< 5\text{ ms}$ on every scan.

4. **✨ MINIMALIST MODERN SWEETALERT DIALOG (ACCURACY BUTTON REMOVED)**:
   - Clunky manual accuracy buttons have been completely eliminated from the cockpit.
   - Dynamic accuracy metrics, confusion matrices, and genuine sample counts are computed live and automatically presented inside the **SweetAlert Dialog** modal on scan completion.

---

## 📁 Project Directory Structure
```
dragonfruit/
├── config.py                 # Core hardware parameters, thresholds, and color bounds
├── main.py                   # Desktop application launcher
├── requirements.txt          # Dependencies list
├── PROJECT DETAILS.md        # Original project specifications
├── hardware/
│   ├── camera_controller.py  # Picamera2 (Cam Module 3) + OpenCV fallback + Simulation
│   ├── radar_controller.py   # Infineon 60GHz FMCW Radar 45° incidence controller
│   └── gpio_sorter.py        # Raspberry Pi 5 RP1 GPIO 17 sorting actuator driver
├── core/
│   ├── accuracy_tester.py    # Real-time dynamic accuracy benchmark & confusion matrix engine
│   ├── vision_analyzer.py    # Color, size, skin texture & rot % engine (YOLO badge)
│   ├── yolo_detector.py      # Pretrained deep learning model loader & fallback
│   ├── fusion_classifier.py  # 45° FMCW Radar + Camera multi-modal decision logic
│   ├── dataset_manager.py    # Subfolder dataset organizer (original, detection, json)
│   └── model_trainer.py      # Feature extraction, model training and evaluation
├── gui/
│   └── dashboard.py          # Unified Scanning Chamber, Radar, Auto-Save & Live Accuracy Cockpit
├── yolo11n.pt                # Pretrained YOLOv11 deep learning neural network weights
├── RIPE/                     # Ripe dataset: original/ (raw), detection/ (YOLO/boxes), json/
├── ROTTEN/                   # Rotten dataset: original/ (raw), detection/ (YOLO/boxes), json/
└── UNRIPE/                   # Unripe dataset: original/ (raw), detection/ (YOLO/boxes), json/
```
