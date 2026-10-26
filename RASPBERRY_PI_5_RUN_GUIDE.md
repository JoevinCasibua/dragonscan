# 🍓 DragonScan v5.2.0 — Raspberry Pi 5 Terminal Execution Guide
### Subsurface 60 GHz FMCW Radar + Optical Vision Inspection Station

This step-by-step terminal instruction manual guides you through installing, configuring, and running **DragonScan** directly from the **Raspberry Pi 5** terminal.

---

## 📋 System Prerequisites
- **Hardware**: Raspberry Pi 5 (4GB or 8GB recommended) with Active Cooler.
- **Operating System**: **Raspberry Pi OS (Bookworm) 64-bit with Desktop**.
- **Camera**: Logitech C270 HD Webcam connected via any Raspberry Pi 5 **USB port** (enumerates as `/dev/video0`).
- **Radar**: Hi-Link HLK-LD6002 (VERC V1.0) 60 GHz FMCW Radar on ANDAR ADTE2104 V2.0 carrier board connected via USB-C to a Pi 5 **USB 3.0** (blue) port.
- **Display**: Official 7" Touchscreen, HDMI Monitor, or Wayland/X11 display (`1024x600` or `1280x720`+).

---

## ⚡ Quick Start: 3 Commands to Launch
If your environment is already set up, open the terminal in the project directory:

```bash
cd ~/dragonfruit
chmod +x run_dragonscan.sh
./run_dragonscan.sh
```

---

## 🛠️ Complete Step-by-Step Setup from Scratch

### Step 1: Open Terminal & Update System
Open a terminal window on your Raspberry Pi 5 desktop (press `Ctrl + Alt + T`), then run:

```bash
sudo apt update && sudo apt upgrade -y
```

---

### Step 2: Install System Dependencies (Pi 5 Bookworm)
Raspberry Pi OS Bookworm utilizes pre-compiled system packages for hardware access (`picamera2` and `gpiod`). Install them via `apt`:

```bash
sudo apt install -y \
    python3-picamera2 \
    python3-libgpiod \
    python3-tk \
    python3-pil.imagetk \
    python3-pil \
    python3-opencv \
    python3-numpy \
    python3-serial \
    python3-pip \
    python3-venv \
    git
```

---

### Step 3: Grant User Hardware Permissions
Enable your user (`pi` or your active username) to access serial ports for the radar and GPIO pins for the sorter without needing `sudo`:

```bash
sudo usermod -a -G dialout $USER
sudo usermod -a -G gpio $USER
```
> [!NOTE]
> If you just added yourself to the `dialout` or `gpio` group, log out and log back in, or run:
> ```bash
> newgrp dialout
> ```

---

### Step 4: Clone or Navigate to the DragonScan Directory
If the project is located in `~/dragonfruit`:

```bash
cd ~/dragonfruit
```

Install any remaining Python packages (such as `ultralytics` for YOLOv11 if desired):

```bash
# Option A: Install system-wide on Bookworm
pip3 install -r requirements.txt --break-system-packages

# OR Option B: Using a Virtual Environment with system site-packages (Recommended)
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Step 5: Verify Connected Hardware (Health Check)

#### 1. Test Logitech C270 USB Webcam:
```bash
# Check if C270 is detected on USB bus
lsusb | grep -i "Logitech"

# Verify video device nodes exist
ls -l /dev/video*
```
*You should see `Logitech, Inc. Webcam C270` and `/dev/video0`. (Optional: install `v4l-utils` via `sudo apt install v4l-utils` and run `v4l2-ctl --list-devices` to view device capabilities).*

#### 2. Test Hi-Link HLK-LD6002 60 GHz Radar USB Connection:
```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```
*You should see `/dev/ttyUSB0` or `/dev/ttyACM0` (the ANDAR ADTE2104 CH340/USB-UART bridge). If no device appears, verify the USB-C cable is firmly seated and supports data transfer.*

#### 3. Test GPIO Sorter Pin (Pin 17):
```bash
gpiodetect
gpioinfo gpiochip4
```

---

### Step 6: Launch DragonScan on the Pi 5 Terminal

Make the launcher script executable and run it:

```bash
chmod +x run_dragonscan.sh
./run_dragonscan.sh
```

Or execute directly via Python:

```bash
python3 main.py
```

The application will initialize:
1. **Logitech C270 USB HD Webcam** (via OpenCV V4L2 with low-latency MJPG streaming @ 720p 30 FPS).
2. **Hi-Link HLK-LD6002 (ANDAR ADTE2104)** on `/dev/ttyUSB0` or `/dev/ttyACM0` (with auto-port discovery and high-fidelity simulation fallback).
3. **GPIO Sorter Actuator** on `gpiochip4` Pin 17.
4. **Full-Screen 7" Touchscreen Cockpit** with live oscillating up-and-down radar scanning effect.

---

## 🌐 Running via SSH (Remote Terminal from PC/Mac)
If you connect to your Raspberry Pi 5 from another computer via SSH:

### If your Pi is connected to a physical monitor:
Launch the app onto the physical screen from your SSH terminal:
```bash
export DISPLAY=:0
export WAYLAND_DISPLAY=wayland-0
cd ~/dragonfruit
./run_dragonscan.sh
```

### If you want to view the GUI on your PC via X11 Forwarding:
```bash
# Connect with -X or -Y flag
ssh -Y pi@raspberrypi.local
cd ~/dragonfruit
python3 main.py
```

---

## 🚀 Optional: Autostart DragonScan on Boot (Kiosk Mode)
To automatically start DragonScan whenever the Raspberry Pi 5 powers on:

1. Create an autostart directory and desktop entry:
```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/dragonscan.desktop
```

2. Paste the following configuration:
```ini
[Desktop Entry]
Type=Application
Name=DragonScan
Exec=/bin/bash -c "cd /home/pi/dragonfruit && ./run_dragonscan.sh"
Terminal=false
X-GNOME-Autostart-enabled=true
```
*(Replace `/home/pi/dragonfruit` with your exact folder path if different, e.g. `$HOME/dragonfruit`)*

3. Save with `Ctrl + O`, then exit with `Ctrl + X`.

---

## 🔧 Troubleshooting Guide

| Issue | Root Cause | Solution |
|---|---|---|
| `[ERROR] Camera initialization failed` | Ribbon cable loose or wrong port | Check CAM0/CAM1 cable pins; run `rpicam-hello` |
| `Permission denied: '/dev/ttyACM0'` | User not in `dialout` group | Run `sudo usermod -a -G dialout $USER` and re-login |
| `no display name and no $DISPLAY environment variable` | Running from headless SSH without display target | Run `export DISPLAY=:0` before starting |
| `externally-managed-environment` error on pip | PEP 668 protection in Bookworm | Add `--break-system-packages` or use `python3 -m venv --system-site-packages venv` |
| Low frame rate | Background software throttle | Ensure Raspberry Pi Active Cooler is connected and thermal throttling is not active (`vcgencmd get_throttled`) |

---

## 🎮 Key Shortcuts in Fullscreen Cockpit
- **`F11`**: Toggle borderless full-screen mode.
- **`Esc`**: Exit full-screen mode to windowed layout.
- **`Double Click Video`**: Expand camera to 100% full screen.
- **`Spacebar`** or **`Enter`**: Trigger sequential Radar + Camera scan.

---

*Glory to the Almighty Lord Jesus Christ.*
