from pathlib import Path
from typing import List, Tuple
import ezdxf

from .config_loader import load_measurement_rules


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
    "double_wall_centerline": ["DOUBLE_WALL"],
    "curtain_wall_exterior": ["CURTAIN_WALL", "CURTAIN"],
    "non_structural_projection": ["NON_STRUCTURAL_PROJECTION", "PROJECTION_NON_STRUCTURAL", "BALCONY", "CANOPY"],
    "structural_projection": ["STRUCTURAL_PROJECTION", "PILASTER", "FIN"],
    "internal_wall_shared": ["SHARED_WALL", "DEMISING_WALL"],
    "void_single_tenant": ["VOID_SINGLE_TENANT"],
    "void_multi_tenant": ["VOID_MULTI_TENANT"],
    "double_wall_centerline": ["DOUBLE_WALL", "CAVITY"]
}


def validate_dwg_file(path: str) -> Tuple[bool, List[str]]:
    """Validate a DXF/DWG (pre-converted to DXF) for mandatory drawing details.

    Returns (is_valid, messages). Raises DWGValidationError on fatal problems.
    """
    p = Path(path)
    if not p.exists():
        raise DWGValidationError(f"DXF file not found: {path}")

    doc = ezdxf.readfile(str(p))
    text_labels = _collect_text_labels(doc)

    rules_data = load_measurement_rules()
    messages: List[str] = []
    is_valid = True

    # For each measurement rule that requires DWG detail, ensure at least one of the required tokens exists
    for rule in rules_data.get("measurement_rules", []):
        if rule.get("mandatory_dwg_detail"):
            rid = rule.get("id")
            required_tokens = RULE_REQUIRED_TAGS.get(rid, [])
            if not required_tokens:
                # If no mapping, skip
                continue
            found = False
            for token in required_tokens:
                for lab in text_labels:
                    if token in lab:
                        found = True
                        break
                if found:
                    break
            if not found:
                is_valid = False
                messages.append(f"Missing mandatory DWG detail for rule '{rid}'. Expected token(s): {required_tokens}")

    return is_valid, messages
