from typing import Dict, List
from shapely.geometry import Polygon
from .config_loader import load_json_config, build_part_lookup
from .geometry_engine import apply_measurement_rule
from .dxf_parser import Region


def _load_surveys() -> Dict[str, Dict]:
    data = load_json_config("seven_cumulative_surveys.json")
    if not isinstance(data, dict) or "surveys" not in data:
        raise ValueError("Invalid surveys configuration: missing 'surveys'.")
    return {s["id"]: s for s in data["surveys"]}


SURVEYS = _load_surveys()
PARTS_LOOKUP = build_part_lookup()


class MeasurementResult:
    def __init__(self, survey_id: str, area_sqm: float, breakdown: Dict[str, float]):
        self.survey_id = survey_id
        self.area_sqm = area_sqm
        self.breakdown = breakdown

    def to_dict(self):
        return {"survey_id": self.survey_id, "area_sqm": self.area_sqm, "breakdown": self.breakdown}


def compute_survey_area(regions: List[Region], survey_id: str, wall_thickness_m: float = 0.3) -> MeasurementResult:
    """Compute the area for a given cumulative survey (GLA/GFA/BUA) based on regions provided.

    - Regions whose label matches a part listed in the survey's `parts` array are included.
    - VOID regions are adjusted using the measurement rules via geometry_engine.apply_measurement_rule.
    - Returns a MeasurementResult containing numeric area and per-part breakdown.
    """
    if survey_id not in SURVEYS:
        raise KeyError(f"Unknown survey id '{survey_id}' in configuration.")
    survey = SURVEYS[survey_id]
    parts = set(survey.get("parts", []))

    breakdown: Dict[str, float] = {}
    total_area = 0.0

    for region in regions:
        label = region.label.strip().upper()
        # VOID handling: adjust per void rule
        if label.startswith("VOID"):
            # Map VOID label to rule id convention in config
            if label == "VOID_SINGLE_TENANT":
                rule_id = "void_single_tenant"
            elif label == "VOID_MULTI_TENANT":
                rule_id = "void_multi_tenant"
            else:
                # default to multi-tenant centerline behavior
                rule_id = "void_multi_tenant"
            result = apply_measurement_rule(region.polygon, rule_id, wall_thickness_m=wall_thickness_m)
            area = result.polygon.area if result.polygon and not result.polygon.is_empty else 0.0
            breakdown.setdefault(label, 0.0)
            breakdown[label] += area
            # Void areas are typically excluded from tenant GLA but may be included in GFA depending on survey
            if survey_id in ("GFA", "BUA") and result.offset_rule == "centerline":
                total_area += area
            # if interior_face for GLA, include for GLA
            if survey_id == "GLA" and result.offset_rule == "interior_face":
                total_area += area
            continue

        # Normal parts: include if the part id is listed in the survey parts
        include = False
        if label in parts:
            include = True
        else:
            # If the part definition says this part is included in the requested survey, include it
            part_def = PARTS_LOOKUP.get(label)
            if part_def:
                included_in = part_def.get("included_in_surveys", []) or []
                if survey_id in included_in:
                    include = True

        if include:
            a = region.polygon.area
            breakdown.setdefault(label, 0.0)
            breakdown[label] += a
            total_area += a

    return MeasurementResult(survey_id=survey_id, area_sqm=total_area, breakdown=breakdown)
