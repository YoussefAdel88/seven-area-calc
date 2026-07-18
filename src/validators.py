from pathlib import Path
from typing import List, Tuple
import ezdxf

from .config_loader import load_measurement_rules
from .dxf_parser import parse_dxf
from .geometry_engine import classify_wall_segments


class DWGValidationError(Exception):
    pass


def _collect_text_labels(doc: ezdxf.document.Drawing) -> List[str]:
    labels = []
    for e in doc.modelspace():
        t = e.dxftype()
        if t in ("TEXT", "MTEXT"):
            text = getattr(e.dxf, "text", None)
            if text is None:
                try:
                    text = getattr(e, "text", "")
                except Exception:
                    text = ""
            if text:
                labels.append(str(text).upper())
    return labels


# Map measurement rule IDs to required DWG tag tokens (heuristic mapping)
RULE_REQUIRED_TAGS = {
    "exterior_wall_with_adjacent_common": ["SHARED_WALL", "WALL_SHARED"],
    "double_wall_centerline": ["DOUBLE_WALL", "CAVITY"],
    "curtain_wall_exterior": ["CURTAIN_WALL", "CURTAIN"],
    "non_structural_projection": ["NON_STRUCTURAL_PROJECTION", "PROJECTION_NON_STRUCTURAL", "BALCONY", "CANOPY"],
    "structural_projection": ["STRUCTURAL_PROJECTION", "PILASTER", "FIN"],
    "internal_wall_shared": ["SHARED_WALL", "DEMISING_WALL"],
    "void_single_tenant": ["VOID_SINGLE_TENANT"],
    "void_multi_tenant": ["VOID_MULTI_TENANT"]
}


def validate_dwg_file(path: str) -> Tuple[bool, List[str]]:
    """Validate a DXF/DWG (pre-converted to DXF) for mandatory drawing details.

    Returns (is_valid, messages). Uses geometry heuristics to relax strict token requirements where possible.
    Raises DWGValidationError on fatal problems.
    """
    p = Path(path)
    if not p.exists():
        raise DWGValidationError(f"DXF file not found: {path}")

    # collect text tokens
    doc = ezdxf.readfile(str(p))
    text_labels = _collect_text_labels(doc)

    # parse regions and compute geometry-based heuristics
    try:
        regions = parse_dxf(str(p))
    except Exception:
        regions = []
    classification = {"shared_boundaries": [], "double_walls": [], "exterior_walls": []}
    if regions:
        classification = classify_wall_segments([r.polygon for r in regions])

    rules_data = load_measurement_rules()
    errors: List[str] = []
    warnings: List[str] = []

    # For each measurement rule that requires DWG detail, ensure at least one of the required tokens exists
    for rule in rules_data.get("measurement_rules", []):
        if not rule.get("mandatory_dwg_detail"):
            continue
        rid = rule.get("id")
        required_tokens = RULE_REQUIRED_TAGS.get(rid, [])
        # if no token mapping, skip strict check but warn
        if not required_tokens:
            warnings.append(f"No DWG token mapping for rule '{rid}'; ensure drawing contains required detail.")
            continue
        # check for explicit token in text labels
        found_token = False
        for lab in text_labels:
            for token in required_tokens:
                if token in lab:
                    found_token = True
                    break
            if found_token:
                break
        if found_token:
            continue
        # attempt heuristics for specific rules
        heuristic_ok = False
        if rid == "double_wall_centerline":
            if classification.get("double_walls"):
                heuristic_ok = True
                warnings.append(f"Heuristic: detected double wall geometry; treating '{rid}' as satisfied (no explicit token found).")
        if rid in ("internal_wall_shared", "exterior_wall_with_adjacent_common"):
            if classification.get("shared_boundaries"):
                heuristic_ok = True
                warnings.append(f"Heuristic: detected shared boundary geometry; treating '{rid}' as satisfied (no explicit token found).")
        # curtain wall and projections cannot be robustly detected from simple polygons — warn but do not error
        if rid in ("curtain_wall_exterior", "non_structural_projection", "structural_projection"):
            warnings.append(f"Missing explicit token(s) for rule '{rid}'. Unable to heuristically detect; CAD should label this feature.")
            heuristic_ok = False
        # final decision
        if not heuristic_ok:
            errors.append(f"Missing mandatory DWG detail for rule '{rid}'. Expected token(s): {required_tokens}")

    # Construct messages
    messages: List[str] = []
    messages.extend(errors)
    for w in warnings:
        messages.append(f"WARNING: {w}")

    is_valid = len(errors) == 0
    return is_valid, messages
