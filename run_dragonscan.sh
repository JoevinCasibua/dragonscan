#!/bin/bash
# ========================================================
#   DRAGONSCAN v5.2.0 - Raspberry Pi 5 Station Launcher
#   45° FMCW Radar + Camera Module 3 Vision System
# ========================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "  DRAGONSCAN v5.2.0 - STARTING STATION CONTROLLER..."
echo "  Target: Raspberry Pi 5 (8GB) | Bookworm 64-bit"
echo "========================================================"

# 1. Ensure graphical display variables are set (needed for Tkinter GUI)
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi
if [ -z "$WAYLAND_DISPLAY" ]; then
    export WAYLAND_DISPLAY=wayland-0
fi

# Allow local GUI access if xhost is installed
if command -v xhost &> /dev/null; then
    xhost +local: >/dev/null 2>&1 || true
fi

# 2. Check for Python virtual environment or system Python
if [ -d "$SCRIPT_DIR/venv" ] && [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo "[INFO] Activating virtual environment (venv)..."
    source "$SCRIPT_DIR/venv/bin/activate"
    PYTHON_CMD="python3"
elif [ -d "$SCRIPT_DIR/.venv" ] && [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    echo "[INFO] Activating virtual environment (.venv)..."
    source "$SCRIPT_DIR/.venv/bin/activate"
    PYTHON_CMD="python3"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "[ERROR] python3 not found. Run: sudo apt install -y python3"
    exit 1
fi

# 3. Check Serial Port Permissions for Radar (/dev/ttyACM0 or /dev/ttyUSB0)
for port in /dev/ttyACM0 /dev/ttyUSB0; do
    if [ -e "$port" ] && [ ! -r "$port" ]; then
        echo "[WARNING] $port exists but is not readable. Adding current user to dialout group recommended:"
        echo "          sudo usermod -a -G dialout $USER"
    fi
done

# 4. Launch DragonScan GUI
echo "[INFO] Executing DragonScan Desktop Application..."
exec $PYTHON_CMD main.py "$@"
