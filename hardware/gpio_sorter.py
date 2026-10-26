"""
Raspberry Pi 5 GPIO Sorting & Desegregation Actuator Controller.
Controls physical pneumatic diverter / relay / servo to segregate rotten dragon fruit.
Supports libgpiod / RPi.GPIO on Raspberry Pi 5 and software simulation on other platforms.
"""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class GpioSorterController:
    """
    Manages physical segregation gate / actuator.
    Triggers when a dragon fruit exceeds the rotten percentage threshold.
    """
    def __init__(self, pin: int = 17, pulse_duration: float = 0.8):
        self.pin = pin
        self.pulse_duration = pulse_duration
        self.backend = "SIMULATION"
        self.is_active = False
        self._chip = None
        self._line = None

    def initialize(self) -> bool:
        """Initialize GPIO pin using gpiod (recommended on Pi 5 / Bookworm) or fallback."""
        # 1. Try gpiod (Raspberry Pi 5 Bookworm standard)
        try:
            import gpiod
            self._chip = gpiod.Chip('gpiochip4')  # Raspberry Pi 5 RP1 chip is gpiochip4
            self._line = self._chip.get_line(self.pin)
            self._line.request(consumer="dragonscan_sorter", type=gpiod.LINE_REQ_DIR_OUT)
            self._line.set_value(0)
            self.backend = "GPIOD"
            logger.info(f"GpioSorter initialized via gpiod on pin {self.pin} (RP1).")
            return True
        except (ImportError, Exception) as e:
            logger.debug(f"gpiod not available: {e}")

        # 2. Try RPi.GPIO (Legacy fallback)
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, GPIO.LOW)
            self.backend = "RPI_GPIO"
            logger.info(f"GpioSorter initialized via RPi.GPIO on pin {self.pin}.")
            return True
        except (ImportError, Exception) as e:
            logger.debug(f"RPi.GPIO not available: {e}")

        # 3. Simulation mode for desktop development
        self.backend = "SIMULATION"
        logger.info("GpioSorter initialized in Software Simulation Mode.")
        return True

    def trigger_desegregation(self, reason: str = "Rotten Threshold Exceeded") -> bool:
        """
        Activates sorting actuator to push/eject degraded fruit into rotten bin.
        """
        self.is_active = True
        logger.warning(f"[ACTUATOR TRIGGERED] Desegregating fruit! Reason: {reason}")
        
        try:
            if self.backend == "GPIOD" and self._line:
                self._line.set_value(1)
                time.sleep(self.pulse_duration)
                self._line.set_value(0)
            elif self.backend == "RPI_GPIO":
                import RPi.GPIO as GPIO
                GPIO.output(self.pin, GPIO.HIGH)
                time.sleep(self.pulse_duration)
                GPIO.output(self.pin, GPIO.LOW)
            else:
                # Simulation delay
                time.sleep(0.1)
                
            self.is_active = False
            return True
        except Exception as e:
            logger.error(f"Error during sorter actuation: {e}")
            self.is_active = False
            return False

    def cleanup(self):
        """Release GPIO pins."""
        if self.backend == "GPIOD" and self._line:
            try:
                self._line.release()
            except Exception:
                pass
        elif self.backend == "RPI_GPIO":
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass
        self.is_active = False
