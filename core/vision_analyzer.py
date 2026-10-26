"""
Vision Analysis Engine for DragonScan.
Performs high-precision segmentation, size measurement, color quantification,
skin texture inspection, and exact percentage calculation of rotten dragon fruit peel.
"""

import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional
import config
from core.yolo_detector import YoloDetector

class VisionAnalyzer:
    """
    Analyzes dragon fruit images for:
    - Geometric metrics: Length (mm), Width (mm), Aspect Ratio, Area (cm²), Circularity
    - Color segmentation: Ripe Magenta %, Bract Green %, Rot/Necrosis %
    - Skin texture & lesion mapping: Defect count, roughness, lesion distribution
    - Rotten Area Percentage: High-precision calculation and segregation decision
    - YOLOv11 / COCO Deep Learning Object Detection integration
    """
    def __init__(self, pixels_per_mm: float = config.PIXELS_PER_MM):
        self.pixels_per_mm = pixels_per_mm
        self.yolo = YoloDetector(config.YOLO_MODEL_NAME)

    def analyze_frame(self, bgr_image: np.ndarray, segregation_threshold: float = config.ROTTEN_SEGREGATION_THRESHOLD_PERCENT) -> Dict[str, Any]:
        """
        Executes end-to-end vision inspection on a BGR image frame.
        """
        h, w = bgr_image.shape[:2]
        hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2LAB)
        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)

        # 1. Segment Total Dragon Fruit Body from Background
        fruit_mask, fruit_contour, bbox = self._segment_fruit_body(bgr_image, hsv)
        fruit_pixel_count = int(np.count_nonzero(fruit_mask))

        if fruit_pixel_count < 1500 or fruit_contour is None:
            # No fruit detected on the stage
            return {
                "fruit_detected": False,
                "message": "No dragon fruit detected on scanning stage",
                "annotated_frame": bgr_image.copy(),
                "rotten_percentage": 0.0,
                "needs_desegregation": False,
                "metrics": {}
            }

        # 2. Precise Geometric Metrics (Size, Dimensions)
        size_metrics = self._calculate_dimensions(fruit_contour, fruit_pixel_count)

        # 3. Color Space Quantification (Ripe Peel, Bracts, Rotten Areas)
        color_metrics, ripe_mask, bract_mask, rot_mask = self._analyze_colors(hsv, fruit_mask)

        # 4. Skin Texture and Lesion Analysis
        skin_metrics = self._analyze_skin_texture(gray, fruit_mask, rot_mask)

        # 5. Exact Rotten Percentage & Severity Calculation
        rotten_pixels = int(np.count_nonzero(rot_mask))
        rotten_percentage = round((rotten_pixels / max(1, fruit_pixel_count)) * 100.0, 2)
        
        # 6. Deep Learning YOLO Detection (COCO / YOLOv11)
        yolo_res = self.yolo.detect_fruit(bgr_image, conf_threshold=config.YOLO_CONFIDENCE_THRESHOLD)

        # Desegregation trigger
        needs_desegregation = bool(rotten_percentage >= segregation_threshold)

        # Ripeness determination based on peel coverage
        # Fresh vine dragon fruits have green scales/bracts covering 30-60% of surface area;
        # visible magenta/pink peel >= 18.0% indicates harvest maturity (RIPE).
        ripe_coverage_pct = color_metrics["ripe_peel_percentage"]
        is_ripe = bool(ripe_coverage_pct >= 18.0 and not needs_desegregation)
        is_unripe = bool(ripe_coverage_pct < 18.0 and not needs_desegregation)

        quality_grade = "GRADE A (PRISTINE)"
        if needs_desegregation:
            quality_grade = "REJECT / DESEGREGATE"
        elif rotten_percentage >= 5.0 or ripe_coverage_pct < 70.0:
            quality_grade = "GRADE B (MARKETABLE)"

        # 7. Generate Live Annotated Frame (Clean, without boxes) & Detection Photo Frame (With Object Detection)
        annotated_frame = self._draw_annotations(
            bgr_image.copy(), fruit_contour, bbox, rot_mask, ripe_mask,
            size_metrics, rotten_percentage, segregation_threshold, needs_desegregation, quality_grade,
            yolo_res, force_detection_boxes=False
        )

        detection_frame = self._draw_annotations(
            bgr_image.copy(), fruit_contour, bbox, rot_mask, ripe_mask,
            size_metrics, rotten_percentage, segregation_threshold, needs_desegregation, quality_grade,
            yolo_res, force_detection_boxes=True
        )

        return {
            "fruit_detected": True,
            "quality_grade": quality_grade,
            "is_ripe": is_ripe,
            "is_unripe": is_unripe,
            "needs_desegregation": needs_desegregation,
            "rotten_percentage": rotten_percentage,
            "segregation_threshold": segregation_threshold,
            "dimensions": size_metrics,
            "detected_angle_deg": size_metrics.get("detected_angle_deg", 45.0),
            "color_distribution": color_metrics,
            "skin_texture": skin_metrics,
            "yolo_detection": yolo_res,
            "masks": {
                "fruit_mask": fruit_mask,
                "rot_mask": rot_mask,
                "ripe_mask": ripe_mask,
                "bract_mask": bract_mask
            },
            "annotated_frame": annotated_frame,
            "detection_frame": detection_frame,
            "feature_vector": self._compile_feature_vector(size_metrics, color_metrics, skin_metrics, rotten_percentage)
        }

    def _segment_fruit_body(self, bgr: np.ndarray, hsv: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray], Tuple[int, int, int, int]]:
        """Segments the dragon fruit silhouette from background scanning bed or outdoor foliage."""
        h, w = bgr.shape[:2]
        cx, cy = w // 2, h // 2

        # Dragon fruit has distinctive saturation and color compared to neutral scanning tray
        s_channel = hsv[:, :, 1]
        v_channel = hsv[:, :, 2]
        
        # Fruit pixels typically have S > 30 and V > 25
        _, sat_mask = cv2.threshold(s_channel, 35, 255, cv2.THRESH_BINARY)
        _, val_mask = cv2.threshold(v_channel, 20, 255, cv2.THRESH_BINARY)
        combined = cv2.bitwise_and(sat_mask, val_mask)

        # Morphological opening and closing to clean noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=3)
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=2)

        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return np.zeros(bgr.shape[:2], dtype=np.uint8), None, (0, 0, 0, 0)

        largest_contour = max(contours, key=cv2.contourArea)
        bbox = cv2.boundingRect(largest_contour)

        # Detect outdoor background bleed (when classical mask merges with surrounding orchard vines & ground)
        if bbox[2] >= w * 0.70 and bbox[3] >= h * 0.70:
            # 0. High-Fidelity Prior: Ultralytics YOLO Object Detection Gate
            try:
                if hasattr(self, "yolo") and self.yolo and self.yolo.is_loaded:
                    yolo_prior = self.yolo.detect_fruit(bgr, conf_threshold=0.10)
                    if yolo_prior.get("detected") and yolo_prior.get("bbox"):
                        yx, yy, yw, yh = yolo_prior["bbox"]
                        if yw < w * 0.95 or yh < h * 0.95:
                            roi_hsv = hsv[yy:yy+yh, yx:yx+yw]
                            roi_green = cv2.inRange(roi_hsv, (20, 35, 40), (95, 255, 255))
                            roi_tips1 = cv2.inRange(roi_hsv, (135, 30, 40), (179, 255, 255))
                            roi_tips2 = cv2.inRange(roi_hsv, (0, 35, 40), (15, 255, 255))
                            roi_cand = cv2.bitwise_or(roi_green, cv2.bitwise_or(roi_tips1, roi_tips2))
                            roi_ground = cv2.inRange(roi_hsv, (12, 0, 130), (33, 190, 255))
                            roi_cand[roi_ground > 0] = 0
                            k_y = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
                            roi_closed = cv2.morphologyEx(roi_cand, cv2.MORPH_CLOSE, k_y, iterations=2)
                            y_conts, _ = cv2.findContours(roi_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            if y_conts:
                                best_y_c = max(y_conts, key=cv2.contourArea)
                                if cv2.contourArea(best_y_c) > 4000:
                                    fruit_mask = np.zeros((h, w), dtype=np.uint8)
                                    fruit_mask[yy:yy+yh, yx:yx+yw] = roi_closed
                                    best_y_c_global = best_y_c + np.array([[[yx, yy]]])
                                    return fruit_mask, best_y_c_global, (yx, yy, yw, yh)
            except Exception:
                pass

            # 1. Color spectrum separation (fruit lime green & magenta tips vs dark stem & bright soil)
            try:
                ground_mask = cv2.inRange(hsv, (12, 0, 130), (33, 190, 255))
                stem_mask = cv2.inRange(hsv, (28, 135, 20), (38, 255, 125))

                fruit_green = cv2.inRange(hsv, (22, 35, 45), (85, 255, 255))
                fruit_tips = cv2.inRange(hsv, (135, 40, 40), (179, 255, 255))
                fruit_tips2 = cv2.inRange(hsv, (0, 50, 40), (12, 255, 255))
                fruit_cand = cv2.bitwise_or(fruit_green, cv2.bitwise_or(fruit_tips, fruit_tips2))
                fruit_cand[ground_mask > 0] = 0
                fruit_cand[stem_mask > 0] = 0

                k_spec = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
                spec_opened = cv2.morphologyEx(fruit_cand, cv2.MORPH_OPEN, k_spec, iterations=2)
                spec_closed = cv2.morphologyEx(spec_opened, cv2.MORPH_CLOSE, k_spec, iterations=3)

                cand_contours, _ = cv2.findContours(spec_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                best_spec_c = None
                best_spec_score = -1
                for c in cand_contours:
                    c_area = cv2.contourArea(c)
                    if c_area < 5000:
                        continue
                    cbx, cby, cbw, cbh = cv2.boundingRect(c)
                    left_factor = 0.5 if cbx < 30 else 1.0
                    M = cv2.moments(c)
                    if M["m00"] > 0:
                        dist = np.hypot(int(M["m10"] / M["m00"]) - cx, int(M["m01"] / M["m00"]) - cy)
                        score = c_area * (1.0 / (1.0 + (dist / 400.0))) * left_factor
                        if score > best_spec_score:
                            best_spec_score = score
                            best_spec_c = c

                if best_spec_c is not None:
                    bx, by, bw, bh = cv2.boundingRect(best_spec_c)
                    pad_r = min(w - (bx + bw), 30)
                    pad_y = min(h - (by + bh), 25)
                    pad_t = min(by, 25)
                    final_bbox = (bx, max(0, by - pad_t), bw + pad_r, bh + pad_y + pad_t)
                    fruit_mask = np.zeros((h, w), dtype=np.uint8)
                    cv2.drawContours(fruit_mask, [best_spec_c], -1, 255, -1)
                    fruit_mask = cv2.morphologyEx(fruit_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
                    return fruit_mask, best_spec_c, final_bbox
            except Exception:
                pass

            # 2. Second attempt: Downscaled GrabCut center saliency
            try:
                small_w = 320
                scale_gc = small_w / float(w)
                small_h = int(h * scale_gc)
                small_bgr = cv2.resize(bgr, (small_w, small_h), interpolation=cv2.INTER_LINEAR)

                center_rect = (int(small_w * 0.18), int(small_h * 0.18), int(small_w * 0.64), int(small_h * 0.64))
                gc_mask = np.zeros((small_h, small_w), np.uint8)
                bgdModel = np.zeros((1, 65), np.float64)
                fgdModel = np.zeros((1, 65), np.float64)
                cv2.grabCut(small_bgr, gc_mask, center_rect, bgdModel, fgdModel, 2, cv2.GC_INIT_WITH_RECT)
                fg_mask_small = np.where((gc_mask == 2) | (gc_mask == 0), 0, 1).astype("uint8")
                fg_mask = cv2.resize(fg_mask_small, (w, h), interpolation=cv2.INTER_NEAREST)

                fg_contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                best_c = None
                min_dist = float("inf")
                for c in fg_contours:
                    if cv2.contourArea(c) > 5000:
                        M = cv2.moments(c)
                        if M["m00"] > 0:
                            dist = np.hypot(int(M["m10"] / M["m00"]) - cx, int(M["m01"] / M["m00"]) - cy)
                            if dist < min_dist:
                                min_dist = dist
                                best_c = c
                if best_c is not None:
                    fruit_mask = np.zeros((h, w), dtype=np.uint8)
                    cv2.drawContours(fruit_mask, [best_c], -1, 255, -1)
                    fruit_mask = cv2.morphologyEx(fruit_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
                    return fruit_mask, best_c, cv2.boundingRect(best_c)
            except Exception:
                pass

        fruit_mask = np.zeros(bgr.shape[:2], dtype=np.uint8)
        cv2.drawContours(fruit_mask, [largest_contour], -1, 255, -1)
        fruit_mask = cv2.morphologyEx(fruit_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        return fruit_mask, largest_contour, bbox

    def _calculate_dimensions(self, contour: np.ndarray, pixel_area: int) -> Dict[str, float]:
        """Calculates precise physical dimensions in millimeters and centimeters."""
        # Minimum area bounding box (oriented rectangle for true length & width)
        rect = cv2.minAreaRect(contour)
        (center_x, center_y), (dim_w, dim_h), angle = rect
        
        major_axis_px = max(dim_w, dim_h)
        minor_axis_px = min(dim_w, dim_h)

        length_mm = major_axis_px / self.pixels_per_mm
        width_mm = minor_axis_px / self.pixels_per_mm
        aspect_ratio = length_mm / max(1.0, width_mm)

        perimeter_px = cv2.arcLength(contour, True)
        perimeter_mm = perimeter_px / self.pixels_per_mm

        area_mm2 = pixel_area / (self.pixels_per_mm ** 2)
        area_cm2 = area_mm2 / 100.0

        # Circularity index: 4 * pi * Area / (Perimeter^2)
        circularity = (4.0 * np.pi * pixel_area) / max(1.0, perimeter_px ** 2)

        # Auto-Detect Dynamic Radar Incidence Angle based on fruit 3D pose, orientation, and cradle centroid offset
        norm_rot = abs(float(angle)) % 90.0
        offset_factor = (center_x - 640.0) / 640.0
        tilt_factor = (norm_rot - 45.0) * 0.16
        auto_angle_deg = round(float(np.clip(45.0 + (offset_factor * 8.0) + tilt_factor, 28.0, 62.0)), 1)

        return {
            "length_mm": round(length_mm, 1),
            "width_mm": round(width_mm, 1),
            "aspect_ratio": round(aspect_ratio, 2),
            "perimeter_mm": round(perimeter_mm, 1),
            "surface_area_cm2": round(area_cm2, 2),
            "circularity": round(circularity, 3),
            "detected_angle_deg": auto_angle_deg
        }

    def _analyze_colors(self, hsv: np.ndarray, fruit_mask: np.ndarray) -> Tuple[Dict[str, float], np.ndarray, np.ndarray, np.ndarray]:
        """Quantifies peel color distribution and isolates necrotic rot regions."""
        total_fruit_pixels = max(1, np.count_nonzero(fruit_mask))

        # 1. Ripe Magenta/Pink Peel (HSV Hue 140-180 and Hue 0-10)
        mask_ripe1 = cv2.inRange(hsv, np.array(config.RIPE_COLOR_LOWER), np.array(config.RIPE_COLOR_UPPER))
        mask_ripe2 = cv2.inRange(hsv, np.array(config.RIPE_COLOR_LOWER_SECONDARY), np.array(config.RIPE_COLOR_UPPER_SECONDARY))
        mask_ripe = cv2.bitwise_or(mask_ripe1, mask_ripe2)
        mask_ripe = cv2.bitwise_and(mask_ripe, fruit_mask)

        # 2. Bracts / Scales (Yellow-Green Hue 35-85)
        mask_bract = cv2.inRange(hsv, np.array(config.BRACT_COLOR_LOWER), np.array(config.BRACT_COLOR_UPPER))
        mask_bract = cv2.bitwise_and(mask_bract, fruit_mask)

        # 3. Rotten / Necrotic / Sunken Brown / Dark Decay
        # Brown/olive rot
        mask_rot1 = cv2.inRange(hsv, np.array(config.ROT_COLOR_LOWER_1), np.array(config.ROT_COLOR_UPPER_1))
        # Black / dark necrotic lesions
        mask_rot2 = cv2.inRange(hsv, np.array(config.ROT_COLOR_LOWER_2), np.array(config.ROT_COLOR_UPPER_2))
        mask_rot = cv2.bitwise_or(mask_rot1, mask_rot2)
        # Exclude green bracts from rot
        mask_rot = cv2.bitwise_and(mask_rot, cv2.bitwise_not(mask_bract))
        mask_rot = cv2.bitwise_and(mask_rot, fruit_mask)

        # Exclude orchard ground soil and cactus vines from rot false-positives
        ground_dirt = cv2.inRange(hsv, (10, 0, 115), (35, 190, 255))
        stem_vines = cv2.inRange(hsv, (28, 110, 20), (38, 255, 125))
        mask_rot[ground_dirt > 0] = 0
        mask_rot[stem_vines > 0] = 0

        # Morphological clean up on rot mask to eliminate isolated single-pixel noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_rot = cv2.morphologyEx(mask_rot, cv2.MORPH_OPEN, kernel, iterations=1)

        # Apical floral remnant filter: Suppress dried blossom / perianth remnants at extreme distal tips
        # Healthy unripe and ripe dragon fruits retain brown dry blossom remnants at the apical calyx.
        # Genuine pericarp rot (Anthracnose / Bipolaris) forms sunken lesions on the body, not slender apical tips.
        rot_conts, _ = cv2.findContours(mask_rot.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        fruit_conts, _ = cv2.findContours(fruit_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if fruit_conts and rot_conts:
            main_f_c = max(fruit_conts, key=cv2.contourArea)
            fx, fy, fw, fh = cv2.boundingRect(main_f_c)
            fcx, fcy = fx + (fw / 2.0), fy + (fh / 2.0)
            max_extent = max(fw, fh) / 2.0

            for rc in rot_conts:
                rc_area = cv2.contourArea(rc)
                if rc_area < 20:
                    cv2.drawContours(mask_rot, [rc], -1, 0, -1)
                    continue
                rx, ry, rw, rh = cv2.boundingRect(rc)
                rcx, rcy = rx + (rw / 2.0), ry + (rh / 2.0)
                dist_from_center = np.hypot(rcx - fcx, rcy - fcy)
                aspect_ratio = max(rw, rh) / max(1.0, min(rw, rh))

                # If the brown feature is located at the extreme peripheral apex (> 80% radius)
                # and is slender/elongated (aspect > 2.0) or small relative to total fruit (< 3.5%),
                # it is an apical floral remnant rather than active necrotic pericarp decay.
                if dist_from_center > (0.78 * max_extent) and (aspect_ratio >= 2.0 or rc_area < (0.035 * total_fruit_pixels)):
                    cv2.drawContours(mask_rot, [rc], -1, 0, -1)

        ripe_pixels = np.count_nonzero(mask_ripe)
        bract_pixels = np.count_nonzero(mask_bract)
        rot_pixels = np.count_nonzero(mask_rot)

        color_metrics = {
            "ripe_peel_percentage": round((ripe_pixels / total_fruit_pixels) * 100.0, 2),
            "bract_green_percentage": round((bract_pixels / total_fruit_pixels) * 100.0, 2),
            "necrotic_rot_percentage": round((rot_pixels / total_fruit_pixels) * 100.0, 2),
        }

        return color_metrics, mask_ripe, mask_bract, mask_rot

    def _analyze_skin_texture(self, gray: np.ndarray, fruit_mask: np.ndarray, rot_mask: np.ndarray) -> Dict[str, Any]:
        """Extracts surface roughness, defect lesion contours, and skin uniformity."""
        # Calculate Laplacian variance on fruit area for surface roughness
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        fruit_pixels_gray = gray[fruit_mask > 0]
        roughness_score = float(np.var(laplacian[fruit_mask > 0])) if fruit_pixels_gray.size > 0 else 0.0

        # Find distinct rotten lesion patches
        rot_contours, _ = cv2.findContours(rot_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant_lesions = [c for c in rot_contours if cv2.contourArea(c) > 25]
        lesion_count = len(significant_lesions)

        max_lesion_area_mm2 = 0.0
        if significant_lesions:
            max_c = max(significant_lesions, key=cv2.contourArea)
            max_lesion_area_mm2 = float(cv2.contourArea(max_c) / (self.pixels_per_mm ** 2))

        # Skin color uniformity standard deviation
        skin_uniformity_std = float(np.std(fruit_pixels_gray)) if fruit_pixels_gray.size > 0 else 0.0

        return {
            "roughness_variance": round(roughness_score, 2),
            "lesion_count": lesion_count,
            "max_lesion_area_mm2": round(max_lesion_area_mm2, 2),
            "skin_uniformity_std": round(skin_uniformity_std, 2)
        }

    def _draw_annotations(
        self,
        canvas: np.ndarray,
        contour: np.ndarray,
        bbox: Tuple[int, int, int, int],
        rot_mask: np.ndarray,
        ripe_mask: np.ndarray,
        dims: Dict[str, float],
        rotten_pct: float,
        threshold: float,
        needs_desegregate: bool,
        grade: str,
        yolo_res: Optional[Dict[str, Any]] = None,
        force_detection_boxes: bool = False
    ) -> np.ndarray:
        """Renders dynamic high-precision HUD overlays, YOLO detection boxes, and rotten zone markers."""
        # 1. Highlight Dragon Fruit Boundary (Matrix Cyan-Lime contour with subtle glow)
        cv2.drawContours(canvas, [contour], -1, (255, 230, 0), 2)

        # 2. Overlay Rotten Lesions with luminous translucent red/orange thermal blend
        if np.count_nonzero(rot_mask) > 0:
            red_overlay = canvas.copy()
            red_overlay[rot_mask > 0] = (0, 30, 255)  # Vibrant Crimson/Orange
            cv2.addWeighted(red_overlay, 0.45, canvas, 0.55, 0, canvas)

            # Draw glowing contours around each significant rotten patch
            rot_contours, _ = cv2.findContours(rot_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in rot_contours:
                if cv2.contourArea(c) > 25:
                    cv2.drawContours(canvas, [c], -1, (0, 69, 255), 2)
                    if getattr(config, "SHOW_DEFECT_BOXES", False):
                        rx, ry, rw, rh = cv2.boundingRect(c)
                        tl = 8
                        cv2.line(canvas, (rx, ry), (rx + tl, ry), (0, 140, 255), 2)
                        cv2.line(canvas, (rx, ry), (rx, ry + tl), (0, 140, 255), 2)
                        cv2.line(canvas, (rx + rw, ry + rh), (rx + rw - tl, ry + rh), (0, 140, 255), 2)
                        cv2.line(canvas, (rx + rw, ry + rh), (rx + rw, ry + rh - tl), (0, 140, 255), 2)

        # 3. Object Detection Photo Mode: Render Clear Bounding Box & Detection Tag for Dataset Storage
        if force_detection_boxes:
            use_yolo_box = False
            if yolo_res and yolo_res.get("detected") and yolo_res.get("bbox"):
                yx, yy, yw, yh = yolo_res["bbox"]
                fx, fy, fw, fh = bbox
                # Compute Intersection over Area
                ix1, iy1 = max(yx, fx), max(yy, fy)
                ix2, iy2 = min(yx + yw, fx + fw), min(yy + yh, fy + fh)
                inter_area = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                fruit_area = max(1, fw * fh)
                if (inter_area / fruit_area) >= 0.15 or (inter_area / max(1, yw * yh)) >= 0.25:
                    use_yolo_box = True

            if use_yolo_box:
                yx, yy, yw, yh = yolo_res["bbox"]
                cv2.rectangle(canvas, (yx, yy), (yx + yw, yy + yh), (255, 0, 200), 2)
                yolo_badge = f"DRAGON FRUIT | YOLOv11: {yolo_res.get('confidence', 0)}%"
                cv2.putText(canvas, yolo_badge, (yx, max(24, yy - 8)),
                            cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 0, 200), 2)
            else:
                x, y, w, h = bbox
                box_col = (0, 230, 255) if not needs_desegregate else (0, 50, 255)
                cv2.rectangle(canvas, (x, y), (x + w, y + h), box_col, 2)
                cv2.putText(canvas, f"DRAGON FRUIT ({dims['surface_area_cm2']:.1f} cm2)",
                            (x, max(24, y - 8)), cv2.FONT_HERSHEY_DUPLEX, 0.55, box_col, 2)

            tag_col = (0, 40, 255) if needs_desegregate else (0, 230, 118)
            tag_txt = "REJECT / DESEGREGATE" if needs_desegregate else f"ACCEPTED ({grade})"
            cv2.putText(canvas, f"DETECTION: {tag_txt} | ROT: {rotten_pct:.2f}%", (24, 38),
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, tag_col, 2)
            return canvas

        # Live Display Mode (Clean, respecting config toggles)
        x, y, w, h = bbox
        if getattr(config, "SHOW_TARGET_RETICLES", False):
            corner_len = min(24, w // 4, h // 4)
            box_col = (0, 230, 255) if not needs_desegregate else (0, 50, 255)
            # Top-Left
            cv2.line(canvas, (x, y), (x + corner_len, y), box_col, 2)
            cv2.line(canvas, (x, y), (x, y + corner_len), box_col, 2)
            # Top-Right
            cv2.line(canvas, (x + w, y), (x + w - corner_len, y), box_col, 2)
            cv2.line(canvas, (x + w, y), (x + w - corner_len, y), box_col, 2)
            # Bottom-Left
            cv2.line(canvas, (x, y + h), (x + corner_len, y + h), box_col, 2)
            cv2.line(canvas, (x, y + h), (x, y + h - corner_len), box_col, 2)
            # Bottom-Right
            cv2.line(canvas, (x + w, y + h), (x + w - corner_len, y + h), box_col, 2)
            cv2.line(canvas, (x + w, y + h), (x + w, y + h - corner_len), box_col, 2)

            target_pill_y = max(24, y - 10)
            cv2.putText(canvas, f"TARGET: DRAGON FRUIT ({dims['surface_area_cm2']:.1f} cm2)",
                        (x, target_pill_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 255), 1)

        # Center Optical Target Crosshair (Optional)
        if getattr(config, "SHOW_CROSSHAIR", False):
            cx, cy = x + w // 2, y + h // 2
            cv2.circle(canvas, (cx, cy), 10, (0, 255, 255), 1)
            cv2.line(canvas, (cx - 16, cy), (cx + 16, cy), (0, 255, 255), 1)
            cv2.line(canvas, (cx, cy - 16), (cx, cy + 16), (0, 255, 255), 1)

        # 4. YOLO Deep Learning Box & Badge (Disabled by default to remove bounding boxes)
        if getattr(config, "SHOW_YOLO_BOX", False) and yolo_res and yolo_res.get("detected") and yolo_res.get("bbox"):
            yx, yy, yw, yh = yolo_res["bbox"]
            cv2.rectangle(canvas, (yx, yy), (yx + yw, yy + yh), (255, 0, 200), 2)
            yolo_badge = f"DRAGON FRUIT | YOLOv11: {yolo_res.get('confidence', 0)}%"
            cv2.putText(canvas, yolo_badge, (yx, max(20, yy - 8)),
                        cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 0, 200), 1)

        # 5. Translucent Cyber-HUD Box on Video Frame (Disabled by default; all telemetry is in dashboard HUD)
        if getattr(config, "SHOW_HUD_BOX", False):
            overlay_hud = canvas.copy()
            hud_w = 420
            hud_h = 75
            cv2.rectangle(overlay_hud, (12, 12), (12 + hud_w, 12 + hud_h), (8, 14, 28), -1)
            cv2.addWeighted(overlay_hud, 0.65, canvas, 0.35, 0, canvas)
            cv2.rectangle(canvas, (12, 12), (12 + hud_w, 12 + hud_h), (0, 229, 255), 1)

            tag_col = (0, 40, 255) if needs_desegregate else (0, 230, 118)
            tag_txt = "DESEGREGATE / EJECT" if needs_desegregate else f"ACCEPTED ({grade})"
            cv2.putText(canvas, f"STATUS: {tag_txt}", (22, 36),
                        cv2.FONT_HERSHEY_DUPLEX, 0.58, tag_col, 2)

            rot_col = (0, 40, 255) if rotten_pct >= threshold else (0, 240, 255)
            cv2.putText(canvas, f"ROT AREA: {rotten_pct:.2f}% (Limit: {threshold:.1f}%) | {dims['length_mm']:.0f}x{dims['width_mm']:.0f}mm",
                        (22, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.48, rot_col, 1)

        return canvas

    def _compile_feature_vector(self, dims: Dict[str, float], colors: Dict[str, float], skin: Dict[str, Any], rot_pct: float) -> list:
        """Compiles tabular numeric feature vector for model training."""
        return [
            dims["length_mm"],
            dims["width_mm"],
            dims["aspect_ratio"],
            dims["surface_area_cm2"],
            dims["circularity"],
            colors["ripe_peel_percentage"],
            colors["bract_green_percentage"],
            colors["necrotic_rot_percentage"],
            skin["roughness_variance"],
            skin["lesion_count"],
            skin["max_lesion_area_mm2"],
            skin["skin_uniformity_std"],
            rot_pct
        ]
