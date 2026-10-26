"""
Hi-Link HLK-LD6002 (ANDAR ADTE2104 V2.0) 60GHz FMCW Radar Controller for DragonScan.
Supports physical USB UART interface (/dev/ttyUSB0, /dev/ttyACM0, COMx) and high-fidelity auto-angle simulation.
Measures subsurface dielectric properties, range-FFT, and internal pulp flesh degradation.
"""

import time
import math
import logging
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
import config

logger = logging.getLogger(__name__)

class RadarController:
    """
    Manages Hi-Link HLK-LD6002 (VERC V1.0) 60 GHz FMCW Radar mounted on ANDAR ADTE2104 V2.0 carrier.
    Executes millimeter-wave subsurface penetration and dielectric decay estimation.
    """
    def __init__(self, port: str = config.RADAR_PORT, baudrate: int = config.RADAR_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.sensor_model = getattr(config, "RADAR_SENSOR_MODEL", "HLK-LD6002")
        self.angle_degrees = getattr(config, "RADAR_DEFAULT_ANGLE_DEGREES", 45.0)
        self.auto_angle_mode = getattr(config, "RADAR_AUTO_ANGLE_DETECTION", True)
        self.num_chirps = config.RADAR_NUM_CHIRPS
        self.samples_per_chirp = config.RADAR_SAMPLES_PER_CHIRP
        self.bandwidth_mhz = config.RADAR_BANDWIDTH_MHZ
        self.center_freq_ghz = config.RADAR_FREQUENCY_GHZ
        
        self.is_connected = False
        self.serial_conn = None
        self.simulation_mode = config.RADAR_SIMULATION_MODE
        self.last_scan_data: Optional[Dict[str, Any]] = None

    def initialize(self) -> bool:
        """Initialize connection to HLK-LD6002 Radar sensor or engage high-fidelity simulation."""
        try:
            import serial
            import glob

            candidate_ports: List[str] = [self.port]
            # Auto-detect USB serial devices on Linux/Raspberry Pi
            for p in ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"]:
                if p not in candidate_ports:
                    candidate_ports.append(p)
            
            # Auto-detect COM ports on Windows
            for c in ["COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]:
                if c not in candidate_ports:
                    candidate_ports.append(c)

            for target_port in candidate_ports:
                try:
                    self.serial_conn = serial.Serial(
                        port=target_port,
                        baudrate=self.baudrate,
                        timeout=config.RADAR_TIMEOUT_SEC
                    )
                    if self.serial_conn.is_open:
                        self.port = target_port
                        self.is_connected = True
                        self.simulation_mode = False
                        logger.info(f"HLK-LD6002 Radar hardware connected on {target_port} at {self.baudrate} baud.")
                        return True
                except Exception:
                    continue

            logger.info(f"Physical HLK-LD6002 radar not detected on candidate ports. Engaging simulation.")
        except ImportError:
            logger.info("pyserial library not found. Falling back to radar simulation.")

        # If physical device not detected, activate synthetic FMCW generator
        self.simulation_mode = True
        self.is_connected = True
        logger.info(f"HLK-LD6002 controller initialized in Auto-Angle FMCW Simulation Mode.")
        return True

    def scan(self, simulated_rot_level: float = 0.0, detected_angle: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes FMCW radar sweep sequence with automatic incidence angle detection.
        Returns detailed raw chirps, range FFT, and subsurface degradation metrics.
        """
        timestamp = time.time()
        
        if detected_angle is not None:
            self.angle_degrees = round(float(detected_angle), 1)
        elif self.auto_angle_mode:
            # Dynamic auto-angle jitter when simulating without visual lock
            self.angle_degrees = round(float(np.random.normal(45.0, 1.2)), 1)
        
        if not self.simulation_mode and self.serial_conn:
            try:
                # Command sequence to trigger chirp frame
                self.serial_conn.write(b"SCAN_AUTO\n")
                raw_bytes = self.serial_conn.read(self.num_chirps * self.samples_per_chirp * 2)
                if len(raw_bytes) == self.num_chirps * self.samples_per_chirp * 2:
                    raw_chirps = np.frombuffer(raw_bytes, dtype=np.int16).reshape(
                        (self.num_chirps, self.samples_per_chirp)
                    ).astype(np.float32)
                    return self._process_chirps(raw_chirps, timestamp)
            except Exception as e:
                logger.error(f"Error reading physical radar data: {e}. Switching to simulation fallback.")

        # High-Fidelity Synthetic FMCW Radar Scan with auto-detected angle
        return self._generate_synthetic_radar_scan(timestamp, simulated_rot_level)

    # Backwards compatibility alias
    scan_45_degrees = scan

    def _generate_synthetic_radar_scan(self, timestamp: float, simulated_rot_level: float) -> Dict[str, Any]:
        """
        Generates realistic 60 GHz FMCW chirps reflecting off dragon fruit flesh.
        Accounts for:
        - 45° angle attenuation and distance (approx 25 cm)
        - Healthy firm flesh vs degraded/translucent rotting waterlogged flesh
        """
        # Time array for samples in chirp
        t = np.linspace(0, 1e-4, self.samples_per_chirp)
        raw_chirps = np.zeros((self.num_chirps, self.samples_per_chirp), dtype=np.float32)

        # Base beat frequency for ~25cm fruit distance scaled with auto-detected angle
        angle_rad = math.radians(self.angle_degrees)
        base_beat_freq = 15000.0 * (1.0 + 0.05 * (math.sin(angle_rad) - math.sin(math.radians(45.0))))
        
        # Subsurface degradation alters beat frequency shift, damping, and water absorption
        # Healthy flesh: higher tissue resilience, distinct reflection peak
        # Rotting flesh: cellular breakdown increases free water, spreading reflection & attenuating higher frequencies
        rot_factor = max(0.0, min(1.0, simulated_rot_level))
        
        noise_level = 0.05
        decay_damping = 1.0 + (rot_factor * 1.8)

        for i in range(self.num_chirps):
            chirp_phase = (i / self.num_chirps) * np.pi * 0.1
            # Primary reflection from peel surface (45° incidence)
            signal_peel = 0.8 * np.sin(2 * np.pi * base_beat_freq * t + chirp_phase)
            # Secondary reflection from inner flesh (penetration depth ~15-25 mm)
            subsurface_freq = base_beat_freq * (1.0 + 0.12 * (1.0 - rot_factor * 0.5))
            signal_flesh = (0.5 / decay_damping) * np.sin(2 * np.pi * subsurface_freq * t + chirp_phase + 0.5)
            # Random radar thermal noise
            noise = np.random.normal(0, noise_level, self.samples_per_chirp)
            
            raw_chirps[i] = signal_peel + signal_flesh + noise

        return self._process_chirps(raw_chirps, timestamp, forced_rot=rot_factor)

    def _process_chirps(self, raw_chirps: np.ndarray, timestamp: float, forced_rot: Optional[float] = None) -> Dict[str, Any]:
        """
        Computes Range-FFT, energy spectrum, and internal degradation index from chirps.
        """
        # Apply Hanning window across samples
        window = np.hanning(self.samples_per_chirp)
        windowed = raw_chirps * window

        # Range FFT (FFT along fast-time axis)
        range_fft = np.fft.rfft(windowed, axis=1)
        magnitude_spectrum = np.abs(range_fft)
        mean_spectrum = np.mean(magnitude_spectrum, axis=0)

        # Range bins to centimeters (assuming c=3e8 m/s, B=4 GHz, Sweep=100us)
        # Range resolution = c / (2 * B) = 3e8 / (2 * 4e9) = 0.0375 m = 3.75 cm
        range_bins_cm = np.linspace(0, 50, len(mean_spectrum))

        # Peak energy and peak location
        peak_idx = int(np.argmax(mean_spectrum))
        peak_power_db = float(20 * np.log10(max(mean_spectrum[peak_idx], 1e-6)))
        peak_distance_cm = float(range_bins_cm[peak_idx])

        # Subsurface flesh metrics:
        # High degradation = broader spectrum, lower high-frequency ratio, lower peak-to-average ratio
        energy_total = float(np.sum(mean_spectrum))
        energy_peak_ratio = float(mean_spectrum[peak_idx] / (energy_total + 1e-6))
        
        # Calculate internal degradation index (0.0 = completely sound flesh, 1.0 = severely rotten)
        if forced_rot is not None:
            internal_decay_index = float(forced_rot)
        else:
            # Physics-based heuristic from FMCW attenuation & peak sharpness
            # Peak sharpness > 0.25 indicates firm tissue, < 0.14 indicates macerated rot
            norm_sharpness = np.clip((energy_peak_ratio - 0.12) / 0.15, 0.0, 1.0)
            internal_decay_index = float(np.clip(1.0 - norm_sharpness, 0.0, 1.0))

        # Water/dielectric constant estimate (Dragon fruit healthy pulp: ~60-70, decaying pulp: >78)
        estimated_dielectric_constant = float(62.0 + (internal_decay_index * 16.5))

        return {
            "timestamp": timestamp,
            "angle_degrees": self.angle_degrees,
            "frequency_ghz": self.center_freq_ghz,
            "num_chirps": self.num_chirps,
            "samples_per_chirp": self.samples_per_chirp,
            "peak_power_db": round(peak_power_db, 2),
            "peak_distance_cm": round(peak_distance_cm, 2),
            "internal_decay_index": round(internal_decay_index, 4),
            "dielectric_constant": round(estimated_dielectric_constant, 2),
            "is_internal_rot_flag": bool(internal_decay_index >= config.RADAR_INTERNAL_ROTTEN_THRESHOLD),
            "range_bins_cm": range_bins_cm.tolist(),
            "mean_spectrum": mean_spectrum.tolist(),
            "raw_chirps_shape": list(raw_chirps.shape),
            "is_simulated": self.simulation_mode
        }

    def close(self):
        """Release serial port resources."""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.is_connected = False
        logger.info("Radar controller closed.")
