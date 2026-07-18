from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry

from .config_loader import build_part_lookup, build_rule_lookup

PARTS = build_part_lookup()
RULES = build_rule_lookup()


@dataclass
class RuleApplicationResult:
    polygon: Polygon
    rule_id: str
    offset_distance_m: Optional[float]
    offset_rule: str


def get_measurement_rule(rule_id: str) -> Dict[str, Any]:
    if rule_id not in RULES:
        raise KeyError(f"Measurement rule '{rule_id}' is not defined in configuration.")
    return RULES[rule_id]


def classify_wall_segments(polygons: Sequence[Union[Polygon, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Detect shared boundaries, double walls, and exterior walls among regions."""
    processed: List[Polygon] = []
    for polygon in polygons:
        if isinstance(polygon, Polygon):
            processed.append(polygon)
        elif hasattr(polygon, "polygon"):
            processed.append(getattr(polygon, "polygon"))
        elif hasattr(polygon, "geometry"):
            processed.append(getattr(polygon, "geometry"))
        else:
            raise TypeError("classify_wall_segments expects Polygon objects or objects with a 'polygon' attribute.")

    shared_boundaries: List[Dict[str, Any]] = []
    double_walls: List[Dict[str, Any]] = []
    exterior_walls: List[Dict[str, Any]] = []
    interior_candidates = set()

    for i in range(len(processed)):
        for j in range(i + 1, len(processed)):
            boundary_i = processed[i].boundary
            boundary_j = processed[j].boundary
            shared = boundary_i.intersection(boundary_j)
            if shared.length > 1e-6:
                shared_boundaries.append(
                    {
                        "polygons": (i, j),
                        "length_m": shared.length,
                        "geometry": shared,
                    }
                )
                interior_candidates.add(i)
                interior_candidates.add(j)
            else:
                gap = boundary_i.distance(boundary_j)
                if gap <= 0.5 and _boundaries_are_nearly_parallel(processed[i], processed[j]):
                    double_walls.append(
                        {
                            "polygons": (i, j),
                            "gap_m": gap,
                            "geometry": LineString([
                                processed[i].boundary.interpolate(0.5 * processed[i].boundary.length),
                                processed[j].boundary.interpolate(0.5 * processed[j].boundary.length),
                            ]),
                        }
                    )
                    interior_candidates.add(i)
                    interior_candidates.add(j)

    for index in range(len(processed)):
        if index not in interior_candidates:
            exterior_walls.append({"polygon_index": index})

    return {
        "shared_boundaries": shared_boundaries,
        "double_walls": double_walls,
        "exterior_walls": exterior_walls,
    }


def _boundaries_are_nearly_parallel(poly_a: Polygon, poly_b: Polygon) -> bool:
    a_minx, a_miny, a_maxx, a_maxy = poly_a.bounds
    b_minx, b_miny, b_maxx, b_maxy = poly_b.bounds
    x_overlap = min(a_maxx, b_maxx) - max(a_minx, b_minx)
    y_overlap = min(a_maxy, b_maxy) - max(a_miny, b_miny)
    return (x_overlap > 0.5 and y_overlap < 1.0) or (y_overlap > 0.5 and x_overlap < 1.0)


def apply_measurement_rule(
    polygon: Polygon,
    rule_id: str,
    wall_thickness_m: Optional[float] = None,
) -> RuleApplicationResult:
    rule = get_measurement_rule(rule_id)
    offset_m = _determine_offset_distance(rule, wall_thickness_m)
    offset_rule = rule.get("offset_rule", rule.get("measure_to", "unknown"))

    if offset_m is None or offset_m == 0:
        return RuleApplicationResult(polygon=polygon, rule_id=rule_id, offset_distance_m=offset_m, offset_rule=offset_rule)

    buffer_distance = -offset_m
    offset_polygon = polygon.buffer(buffer_distance, resolution=16)
    # If the offset reduces the polygon to empty (e.g., offset equals half the min dimension),
    # return the result with an empty polygon rather than raising. Tests expect the offset distance
    # and rule to be returned even if the geometry collapses to nothing.
    if offset_polygon.is_empty:
        empty_poly = Polygon()
        return RuleApplicationResult(polygon=empty_poly, rule_id=rule_id, offset_distance_m=offset_m, offset_rule=offset_rule)
    if not isinstance(offset_polygon, Polygon):
        offset_polygon = Polygon(offset_polygon)
    return RuleApplicationResult(polygon=offset_polygon, rule_id=rule_id, offset_distance_m=offset_m, offset_rule=offset_rule)


def _determine_offset_distance(rule: Dict[str, Any], wall_thickness_m: Optional[float]) -> Optional[float]:
    distance = rule.get("offset_distance_mm")
    if isinstance(distance, (int, float)):
        return float(distance) / 1000.0

    if isinstance(distance, str):
        if "half" in distance and wall_thickness_m is not None:
            return wall_thickness_m / 2.0
        return None

    if rule.get("measure_to") == "centerline" and wall_thickness_m is not None:
        return wall_thickness_m / 2.0

    max_thickness = rule.get("max_thickness_to_boundary_mm")
    if max_thickness is not None:
        if wall_thickness_m is None:
            return float(max_thickness) / 1000.0
        return min(wall_thickness_m, float(max_thickness) / 1000.0)

    return None


def get_void_rule_id_for_label(label: str) -> str:
    normalized = label.strip().upper()
    if normalized == "VOID_SINGLE_TENANT":
        return "void_single_tenant"
    if normalized == "VOID_MULTI_TENANT":
        return "void_multi_tenant"
    raise KeyError(f"Unknown void label '{label}'. Expected VOID_SINGLE_TENANT or VOID_MULTI_TENANT.")
