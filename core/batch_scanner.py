"""
DragonScan Batch Scanning & Accuracy Designation Engine.
Scans all authentic field photos from Oct 14, processes them through the
Vision Analyzer, 45° FMCW Radar Diagnostics, and Multi-Modal Fusion Classifier,
designates them into the sovereign dataset categories (RIPE, ROTTEN, UNRIPE),
and executes a comprehensive Accuracy Benchmark.
"""

import sys
import time
import json
import logging
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pillow_heif
pillow_heif.register_heif_opener()
from PIL import Image
import numpy as np
import cv2

import config
from core.vision_analyzer import VisionAnalyzer
from core.fusion_classifier import FusionClassifier
from core.dataset_manager import DatasetManager
from core.accuracy_tester import AccuracyTester
from hardware.radar_controller import RadarController

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DragonScan.BatchScanner")

def scan_and_designate_oct14(target_dir: Path = None):
    if target_dir is None:
        target_dir = ROOT_DIR / "Oct 14"

    logger.info(f"Target scan directory: {target_dir}")
    files = sorted([p for p in target_dir.glob("*.*") if p.suffix.lower() in [".heic", ".jpg", ".jpeg", ".png"]])
    logger.info(f"Found {len(files)} photos to scan and designate.")

    analyzer = VisionAnalyzer()
    fusion = FusionClassifier()
    dataset_mgr = DatasetManager()
    radar = RadarController()
    accuracy_tester = AccuracyTester()

    scan_records = []
    category_counts = {"RIPE": 0, "ROTTEN": 0, "UNRIPE": 0}
    start_time = time.time()

    for idx, f in enumerate(files, 1):
        t0 = time.time()
        try:
            # 1. Load photo (support HEIC via pillow-heif or OpenCV)
            im = Image.open(f)
            w, h = im.size
            scale = 1280.0 / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            im_resized = im.resize((new_w, new_h), Image.Resampling.BILINEAR)

            rgb = np.array(im_resized)
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            # 2. Vision inspection
            thresh = config.ROTTEN_SEGREGATION_THRESHOLD_PERCENT
            vision_res = analyzer.analyze_frame(bgr, segregation_threshold=thresh)

            # 3. 45° FMCW Radar subsurface diagnostics
            rot_pct = float(vision_res.get("rotten_percentage", 0.0))
            sim_rot = rot_pct / 100.0
            radar_res = radar.scan_45_degrees(simulated_rot_level=sim_rot)

            # 4. Multi-modal fusion
            fusion_res = fusion.evaluate(vision_res, radar_res)

            # 5. Designation logic matching DragonScan edge controller
            is_deseg = bool(fusion_res.get("is_desegregate", False))
            quality_grade = vision_res.get("quality_grade", "")
            ripe_peel_pct = float(vision_res.get("color_distribution", {}).get("ripe_peel_percentage", 0.0))
            bract_green_pct = float(vision_res.get("color_distribution", {}).get("bract_green_percentage", 0.0))

            if not vision_res.get("fruit_detected", False):
                designated_cat = "UNRIPE"
            elif is_deseg or rot_pct >= thresh or radar_res.get("is_internal_rot_flag", False):
                designated_cat = "ROTTEN"
            elif quality_grade == "UNRIPE" or ripe_peel_pct < 30.0:
                designated_cat = "UNRIPE"
            else:
                designated_cat = "RIPE"

            category_counts[designated_cat] += 1
            custom_id = f"OCT14_{f.stem}"

            # 6. Save into dedicated dataset triad
            save_res = dataset_mgr.save_capture(
                category=designated_cat,
                raw_frame=bgr,
                annotated_frame=vision_res.get("annotated_frame"),
                vision_metrics=vision_res,
                radar_metrics=radar_res,
                fusion_metrics=fusion_res,
                detection_frame=vision_res.get("detection_frame"),
                custom_scan_id=custom_id
            )

            latency_ms = round((time.time() - t0) * 1000, 1)

            scan_records.append({
                "scan_id": custom_id,
                "filename": f.name,
                "designated_category": designated_cat,
                "quality_grade": fusion_res.get("quality_grade"),
                "confidence_percent": fusion_res.get("confidence_percent"),
                "rotten_percentage": rot_pct,
                "ripe_peel_percentage": ripe_peel_pct,
                "bract_green_percentage": bract_green_pct,
                "is_desegregate": is_deseg,
                "dimensions": vision_res.get("dimensions", {}),
                "verdict": fusion_res.get("verdict"),
                "reason": fusion_res.get("reason"),
                "latency_ms": latency_ms
            })

            if idx % 10 == 0 or idx == len(files):
                logger.info(f"Progress: [{idx}/{len(files)}] Scanned {f.name} -> {designated_cat} (Rot: {rot_pct:.1f}%, Conf: {fusion_res.get('confidence_percent')}%, {latency_ms}ms)")

        except Exception as e:
            logger.error(f"Error scanning {f.name}: {e}")

    total_time = round(time.time() - start_time, 2)
    logger.info(f"Batch scanning completed in {total_time}s. Designations: {category_counts}")

    # 7. Execute Accuracy Benchmark on the complete dataset
    logger.info("Executing comprehensive accuracy benchmark across dataset...")
    live_acc = accuracy_tester.calculate_live_accuracy()
    deep_benchmark = accuracy_tester.run_benchmark()
    dataset_stats = dataset_mgr.get_dataset_statistics()

    summary_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_scanned": len(files),
        "total_time_seconds": total_time,
        "designation_breakdown": category_counts,
        "dataset_statistics": dataset_stats,
        "live_accuracy": live_acc,
        "benchmark": deep_benchmark,
        "records": scan_records
    }

    # Save summary report to JSON
    report_path = ROOT_DIR / "Oct 14_ACCURACY_SCAN_REPORT.json"
    with open(report_path, "w", encoding="utf-8") as rf:
        json.dump(summary_report, rf, indent=2)

    logger.info(f"Accuracy scan report saved to {report_path}")
    return summary_report

if __name__ == "__main__":
    scan_and_designate_oct14()
