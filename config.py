"""
Configuration settings for DragonScan Raspberry Pi 5 Desktop Application.
Supports Camera Module 3 and Hi-Link HLK-LD6002 (ANDAR ADTE2104 V2.0) 60GHz FMCW Radar.
"""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATASET_RIPE_DIR = BASE_DIR / "RIPE"
DATASET_ROTTEN_DIR = BASE_DIR / "ROTTEN"
DATASET_UNRIPE_DIR = BASE_DIR / "UNRIPE"
MODELS_DIR = BASE_DIR

# Ensure dataset directories exist
DATASET_RIPE_DIR.mkdir(parents=True, exist_ok=True)
DATASET_ROTTEN_DIR.mkdir(parents=True, exist_ok=True)
DATASET_UNRIPE_DIR.mkdir(parents=True, exist_ok=True)

# Application Information
APP_NAME = "DragonScan v5.2.0 - FMCW Radar & Vision Segregation"
APP_VERSION = "5.2.0-SOVEREIGN"

# Camera Hardware Configuration (Logitech C270 HD Webcam via USB)
CAMERA_MODEL = "Logitech C270 HD Webcam (USB)"
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30
CAMERA_INDEX = 0          # Default USB camera device index (/dev/video0 or DirectShow index 0)
CAMERA_FOURCC = "MJPG"    # MJPG enables smooth 30 FPS 720p on Logitech C270 USB 2.0
USE_PICAMERA2 = False     # False for USB webcam (Logitech C270); True only for Raspberry Pi CSI ribbon cameras
CAMERA_EXPOSURE_LOCKED = True
CAMERA_WHITE_BALANCE_LOCKED = True

# YOLO Deep Learning Configuration (YOLOv11 / COCO / Dragonfruit weights)
USE_YOLO_IF_AVAILABLE = True
YOLO_MODEL_NAME = "yolo11n.pt"  # Pretrained YOLOv11 nano or coco.pt / custom model
YOLO_CONFIDENCE_THRESHOLD = 0.35

# Scanning Automation Settings
AUTO_SCAN_ON_STARTUP = False       # If False, do NOT auto scan on startup; require user to click button first
AUTO_SAVE_ON_STARTUP = True        # Auto-save dataset records when scan button is executed

# Video Overlay Display Settings (Set to False to remove all on-screen boxes)
SHOW_BOUNDING_BOXES = False       # Master toggle: remove all bounding boxes and reticle boxes
SHOW_YOLO_BOX = False             # Set to False to remove YOLO bounding box and label badge
SHOW_DEFECT_BOXES = False         # Set to False to remove corner bracket boxes around defect patches
SHOW_TARGET_RETICLES = False      # Set to False to remove corner reticle brackets around fruit target
SHOW_HUD_BOX = False              # Set to False to remove embedded top-left HUD box on camera frame
SHOW_CROSSHAIR = False            # Set to False to remove center crosshair on camera frame

# Radar Hardware Configuration (Hi-Link HLK-LD6002 / ANDAR ADTE2104 V2.0 60 GHz FMCW)
RADAR_SENSOR_MODEL = "HLK-LD6002"       # Hi-Link HLK-LD6002 (VERC V1.0) on ANDAR ADTE2104 V2.0
RADAR_AUTO_ANGLE_DETECTION = True       # Automatically detect radar incidence angle from fruit orientation & position
RADAR_DEFAULT_ANGLE_DEGREES = 45.0      # Baseline nominal angle fallback
RADAR_ANGLE_DEGREES = 45.0              # Legacy alias
RADAR_FREQUENCY_GHZ = 60.0
RADAR_NUM_CHIRPS = 64
RADAR_SAMPLES_PER_CHIRP = 128
RADAR_BANDWIDTH_MHZ = 4000.0            # 4 GHz sweep (58-62 GHz)
RADAR_PORT = "/dev/ttyUSB0"             # Linux/Pi USB port for HLK-LD6002 UART bridge (or /dev/ttyACM0, COM on Windows)
RADAR_BAUDRATE = 115200                 # Standard HLK-LD6002 UART baud rate (115200 or 256000)
RADAR_TIMEOUT_SEC = 2.0
RADAR_SIMULATION_MODE = False            # Mandate physical 60GHz radar hardware first! (Only falls back if disconnected)

# Physical Calibration (Pixel to Millimeter ratio)
# Standard scanning distance ~25 cm -> ~4.2 pixels per mm
PIXELS_PER_MM = 4.2

# Segregation Decision Thresholds
# Fruit is flagged for DESEGREGATION / SORT OUT if rotten area >= threshold
ROTTEN_SEGREGATION_THRESHOLD_PERCENT = 15.0  # Grade A: <5%, Grade B (Marketable): 5-15%, Reject/Rotten: >=15%
RADAR_INTERNAL_ROTTEN_THRESHOLD = 0.35      # If internal moisture/decay index >= 0.35, Flag rot

# Weighting for multi-modal fusion
WEIGHT_VISION = 0.65
WEIGHT_RADAR = 0.35

# Color Space Calibration for Dragon Fruit (H: 0-180, S: 0-255, V: 0-255 in OpenCV)
# Healthy Ripe Dragon Fruit Peel (Magenta / Bright Pink / Red)
RIPE_COLOR_LOWER = (140, 50, 50)
RIPE_COLOR_UPPER = (179, 255, 255)
RIPE_COLOR_LOWER_SECONDARY = (0, 70, 70)  # Lower hue red wrap
RIPE_COLOR_UPPER_SECONDARY = (10, 255, 255)

# Bracts / Scales (Yellow-Green)
BRACT_COLOR_LOWER = (35, 40, 40)
BRACT_COLOR_UPPER = (85, 255, 255)

# Rotten / Necrotic / Sunken Brown / Black peel lesions
ROT_COLOR_LOWER_1 = (10, 50, 20)
ROT_COLOR_UPPER_1 = (30, 200, 100)  # Brown / dark yellow-brown decay
ROT_COLOR_LOWER_2 = (0, 0, 10)
ROT_COLOR_UPPER_2 = (180, 255, 65)  # Dark necrotic black / dark grey rot
