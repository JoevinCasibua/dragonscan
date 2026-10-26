"""
DragonScan - Raspberry Pi 5 Multi-Modal Dragon Fruit Inspection & Desegregation Station.
Main Application Entry Point.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
from gui.dashboard import DragonScanApp

def main():
    # Setup structured logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger("DragonScan")
    logger.info(f"Starting {config.APP_NAME}...")
    logger.info(f"Datasets: RIPE={config.DATASET_RIPE_DIR}, ROTTEN={config.DATASET_ROTTEN_DIR}")

    app = DragonScanApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user. Exiting cleanly...")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

if __name__ == "__main__":
    main()
