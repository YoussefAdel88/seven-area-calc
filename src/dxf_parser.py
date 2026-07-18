import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ezdxf
from shapely.geometry import Point, Polygon


UNIT_SCALE: Dict[int, float] = {
    0: 1.0,   # Unitless, assume meters
    1: 0.0254,
    2: 0.3048,
    4: 0.001,
    5: 0.01,
    6: 0.1,
    7: 1.0,
    8: 1000.0,
    9: 2.54e-8,
    10: 0.0000254,
    11: 0.9144,
    12: 1609.344,
    13: 0.0000000254,
}

LABEL_PATTERN = re.compile(r"\b([A-Z0-9_]+)\b")
TEXT_TYPES = {"TEXT", "MTEXT"}


@dataclass
class Region:
    label: str
    polygon: Polygon
    source_handle: str


class DXFParserError(ValueError):
    pass


def parse_dxf(input_path: str) -> List[Region]:
    """Parse a DXF file and return a list of labeled polygon regions."""
    path = Path(input_path)
    doc = ezdxf.readfile(str(path))
    scale = _get_scale(doc)
    text_entities = _collect_text_entities(doc, scale)
    regions: List[Region] = []

    for entity in doc.modelspace():
        if entity.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            polygon = _polyline_to_polygon(entity, scale)
            label = _find_polygon_label(polygon, text_entities, entity)
            regions.append(Region(label=label, polygon=polygon, source_handle=str(entity.dxf.handle)))
        elif entity.dxftype() == "HATCH":
            polygon = _hatch_to_polygon(entity, scale)
            label = _find_polygon_label(polygon, text_entities, entity)
            regions.append(Region(label=label, polygon=polygon, source_handle=str(entity.dxf.handle)))

    if not regions:
        raise DXFParserError(f"No closed regions found in DXF: {path}")

    return regions


def _get_scale(doc: ezdxf.document.Drawing) -> float:
    units = int(doc.header.get("$INSUNITS", 0))
    return UNIT_SCALE.get(units, 1.0)


def _collect_text_entities(doc: ezdxf.document.Drawing, scale: float) -> List[Tuple[Point, str]]:
    text_items: List[Tuple[Point, str]] = []
    for entity in doc.modelspace():
        if entity.dxftype() in TEXT_TYPES:
            insert = getattr(entity.dxf, "insert", None)
            if insert is None or len(insert) < 2:
                continue
            text = getattr(entity.dxf, "text", None)
            if text is None:
                text = getattr(entity, "text", "")
            label = _extract_label(str(text))
            if not label:
                continue
            text_items.append((Point(insert[0] * scale, insert[1] * scale), label))
    return text_items


def _polyline_to_polygon(entity: Any, scale: float) -> Polygon:
    if entity.dxftype() == "LWPOLYLINE":
        raw_points = list(entity.get_points())
        points = [tuple((point[0] * scale, point[1] * scale)) for point in raw_points]
        closed = bool(entity.closed)
    else:
        raw_points = []
        if hasattr(entity, "points"):
            raw_points = list(entity.points())
        elif hasattr(entity, "vertices"):
            raw_points = [vertex.dxf.location for vertex in entity.vertices()]
        points = [tuple((point[0] * scale, point[1] * scale)) for point in raw_points]
        closed = bool(getattr(entity, "closed", False))

    if not points:
        raise DXFParserError("Encountered a polyline entity without any points.")
    if not closed and points[0] != points[-1]:
        raise DXFParserError("DXF region is not closed. All polygons must be closed for SEVEN measurement.")
    if points[0] != points[-1]:
        points.append(points[0])
    polygon = Polygon(points)
    if not polygon.is_valid or polygon.area == 0:
        raise DXFParserError("DXF region failed to form a valid polygon.")
    return polygon


def _hatch_to_polygon(entity: Any, scale: float) -> Polygon:
    points: List[Tuple[float, float]] = []
    for path in entity.paths:
        edges = getattr(path, "edges", [])
        if not edges:
            continue
        for edge in edges:
            if hasattr(edge, "start") and hasattr(edge, "end"):
                points.append((edge.start[0] * scale, edge.start[1] * scale))
            elif hasattr(edge, "points"):
                points.extend([(pt[0] * scale, pt[1] * scale) for pt in edge.points])
            else:
                raise DXFParserError(
                    f"Unsupported HATCH edge type '{type(edge).__name__}' for SEVEN region extraction."
                )
    if not points:
        raise DXFParserError("HATCH entity did not contain any usable boundary edges.")
    if points[0] != points[-1]:
        points.append(points[0])
    polygon = Polygon(points)
    if not polygon.is_valid or polygon.area == 0:
        raise DXFParserError("HATCH region failed to form a valid polygon.")
    return polygon


def _find_polygon_label(polygon: Polygon, text_entities: List[Tuple[Point, str]], entity: Any) -> str:
    candidate_labels: List[str] = []
    for point, label in text_entities:
        if polygon.contains(point) or polygon.touches(point):
            candidate_labels.append(label)

    if not candidate_labels:
        search_radius = max(0.5, polygon.length * 0.05)
        search_region = polygon.buffer(search_radius)
        for point, label in text_entities:
            if search_region.contains(point):
                candidate_labels.append(label)

    candidate_labels = [label for label in candidate_labels if label]
    if not candidate_labels:
        source = getattr(entity.dxf, "handle", "unknown")
        raise DXFParserError(
            f"Missing region label for polygon entity handle {source}. "
            "Each enclosed region must include a SEVEN typology label like FOH, BOH, ISA, or RETAIL."
        )

    unique_labels = set(candidate_labels)
    if len(unique_labels) > 1:
        # If multiple labels are present, prefer explicit VOID labels (e.g., VOID_SINGLE_TENANT, VOID_MULTI_TENANT)
        void_labels = [l for l in unique_labels if l.startswith('VOID')]
        if len(void_labels) == 1:
            return void_labels[0]
        if len(void_labels) > 1:
            source = getattr(entity.dxf, "handle", "unknown")
            raise DXFParserError(
                f"Multiple conflicting VOID labels found for polygon entity handle {source}: {sorted(void_labels)}."
            )
        # No VOID-specific label: this is an ambiguous labeling error
        source = getattr(entity.dxf, "handle", "unknown")
        raise DXFParserError(
            f"Multiple conflicting labels found for polygon entity handle {source}: {sorted(unique_labels)}."
        )
    return candidate_labels[0]


def _extract_label(text: str) -> Optional[str]:
    if not text:
        return None
    match = LABEL_PATTERN.search(text.upper())
    if match:
        return match.group(1)
    return None
