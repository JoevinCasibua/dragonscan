"""
Multi-Modal Fusion Classifier for DragonScan.
Fuses 45-degree FMCW Radar internal subsurface scan with Optical Camera vision inspection.
Solves internal flesh translucency/decay undetectable by optical camera alone.
"""

import logging
from typing import Dict, Any, Tuple
import config

logger = logging.getLogger(__name__)

class FusionClassifier:
    """
    Fuses:
    - 45° FMCW Radar: Subsurface flesh dielectric, water absorption, internal decay index
    - Optical Camera: Peel color distribution, fruit dimensions, skin texture, rotten area %
    Produces final segregation verdict and quality grading.
    """
    def __init__(self, weight_vision: float = config.WEIGHT_VISION, weight_radar: float = config.WEIGHT_RADAR):
        self.weight_vision = weight_vision
        self.weight_radar = weight_radar

    def evaluate(self, vision_results: Dict[str, Any], radar_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes sequential fusion evaluation.
        """
        if not vision_results.get("fruit_detected", False):
            return {
                "verdict": "NO_FRUIT",
                "quality_grade": "N/A",
                "is_desegregate": False,
                "confidence_percent": 0.0,
                "reason": "Scanning bed empty or fruit not positioned properly",
                "radar_decay_index": radar_results.get("internal_decay_index", 0.0),
                "exterior_rot_percentage": 0.0,
                "composite_defect_index": 0.0
            }

        exterior_rot_pct = float(vision_results.get("rotten_percentage", 0.0))
        radar_decay_index = float(radar_results.get("internal_decay_index", 0.0))
        is_radar_rot = bool(radar_results.get("is_internal_rot_flag", False))
        
        # Normalized exterior rot (0.0 to 1.0)
        norm_vision_rot = min(1.0, exterior_rot_pct / 100.0)
        
        # Multi-modal weighted defect index
        composite_defect_index = (norm_vision_rot * self.weight_vision) + (radar_decay_index * self.weight_radar)
        composite_defect_percentage = round(composite_defect_index * 100.0, 2)

        # Segregation conditions
        vision_desegregate = bool(exterior_rot_pct >= vision_results.get("segregation_threshold", config.ROTTEN_SEGREGATION_THRESHOLD_PERCENT))
        radar_desegregate = is_radar_rot
        composite_desegregate = bool(composite_defect_percentage >= 18.0)

        must_desegregate = vision_desegregate or radar_desegregate or composite_desegregate

        # Identify primary defect etiology
        reasons = []
        if vision_desegregate and radar_desegregate:
            reasons.append("Severe Compound Decay (Both Subsurface Pulp & Peel Rot)")
            verdict = "ROTTEN_SYSTEMIC"
        elif radar_desegregate and not vision_desegregate:
            reasons.append("Internal Subsurface Flesh Degradation / Translucency (Detected via 45 deg FMCW Radar)")
            verdict = "ROTTEN_INTERNAL"
        elif vision_desegregate and not radar_desegregate:
            reasons.append(f"Surface Peel Necrosis / Sunken Lesions ({exterior_rot_pct:.1f}% >= Threshold)")
            verdict = "ROTTEN_SURFACE"
        elif vision_results.get("is_unripe", False):
            reasons.append("Immature green bracts and peel (Unripe)")
            verdict = "UNRIPE"
        else:
            reasons.append("Healthy sound fruit with firm flesh and vibrant peel")
            verdict = "RIPE"

        # Quality Grade determination
        if must_desegregate:
            quality_grade = "REJECT / DESEGREGATE"
            confidence = min(99.4, 75.0 + (composite_defect_index * 25.0))
        elif exterior_rot_pct > 4.0 or radar_decay_index > 0.22:
            quality_grade = "GRADE B (MARKETABLE)"
            confidence = 88.5
        elif vision_results.get("is_unripe", False):
            quality_grade = "UNRIPE (STORE FOR RIPENING)"
            confidence = 92.0
        else:
            quality_grade = "GRADE A (PRISTINE RIPE)"
            confidence = 96.5

        return {
            "verdict": verdict,
            "quality_grade": quality_grade,
            "is_desegregate": must_desegregate,
            "confidence_percent": round(confidence, 1),
            "reason": " | ".join(reasons),
            "exterior_rot_percentage": exterior_rot_pct,
            "radar_decay_index": radar_decay_index,
            "composite_defect_percentage": composite_defect_percentage,
            "metrics_breakdown": {
                "vision_rot_pct": exterior_rot_pct,
                "radar_decay_idx": radar_decay_index,
                "radar_dielectric_constant": radar_results.get("dielectric_constant", 65.0),
                "length_mm": vision_results.get("dimensions", {}).get("length_mm", 0.0),
                "width_mm": vision_results.get("dimensions", {}).get("width_mm", 0.0),
                "ripe_peel_pct": vision_results.get("color_distribution", {}).get("ripe_peel_percentage", 0.0),
                "bract_green_pct": vision_results.get("color_distribution", {}).get("bract_green_percentage", 0.0)
            }
        }
