# SEVEN Area Measurement Software — Copilot Agent Instructions

**Document Version:** 0.1  
**Last Updated:** 2026-07-18  
**Applies To:** All coding phases in this repository

---

## 📋 Core Mandate

This software parses DXF files (or DWG pre-converted to DXF via ODA File Converter) containing enclosed regions labeled with SEVEN building typology codes, then:

1. **Validates DWG drafting detail** against mandatory/optional checklist
2. **Applies boundary-offset rules** (wall thickness, void measurement, exterior facade logic)
3. **Calculates cumulative area surveys** (GLA, GFA, BUA) using hard-coded formulas
4. **Exports results** as `Area_Template.xlsx` matching SEVEN's official template schema exactly

**Non-negotiable:** All SEVEN measurement logic lives in JSON config files (not hardcoded into Python). The parsing/geometry engine is generic; the SEVEN rules are **data**, not code.

---

## 🔧 Technology Stack

- **Language:** Python 3.11+
- **DXF Parser:** `ezdxf` (https://github.com/mozman/ezdxf)
- **Geometry:** `shapely` (polygon/boundary operations)
- **Excel Output:** `openpyxl` (match SEVEN template cell-by-cell)
- **Testing:** `pytest` with synthetic DXF fixtures

**External Tool (not Python):**
- **ODA File Converter** (optional, for .dwg → .dxf): https://www.opendesign.com/guestfiles/oda_file_converter  
  Pre-processing step only; not called from Python. Engineer runs manually or via shell script if native .dwg is provided.

---

## 📂 Repository Structure

```
seven-area-calc/
├── .github/
│   └── copilot-instructions.md          ← This file
├── config/
│   ├── seven_parts.json                 ← Building typology defs (FOH, BOH, ISA, etc.)
│   ├── seven_cumulative_surveys.json    ← Area rollup formulas (GLA, GFA, BUA, PA, etc.)
│   ├── seven_measurement_rules.json     ← Boundary conditions + offset lookups
│   └── seven_template_schema.json       ← Excel output column/row mappings
├── src/
│   ├── dxf_parser.py                    ← Read .dxf, extract polygons + labels
│   ├── geometry_engine.py               ← Apply boundary rules, detect voids, classify walls
│   ├── area_calculator.py               ← Rollup boundaries → GLA/GFA/BUA
│   ├── excel_writer.py                  ← Output SEVEN template .xlsx
│   ├── validators.py                    ← Check DWG detail compliance
│   └── __init__.py
├── tests/
│   ├── fixtures/
│   │   ├── minimal_single_space.dxf     ← Synthetic test DXF: one BOH region
│   │   ├── complex_layout.dxf           ← Synthetic test DXF: GFA = GLA+FOH+BOH mix
│   │   └── void_and_wall_tests.dxf      ← Synthetic test DXF: void measurement edge cases
│   ├── test_dxf_parser.py
│   ├── test_geometry_engine.py
│   ├── test_area_calculator.py
│   ├── test_excel_writer.py
│   └── test_validators.py
├── requirements.txt
├── README.md
└── ARCHITECTURE.md                      ← Design rationale (written after Phase 0)
```

---

## 🎯 Hard-Coded Data: The Rules-as-JSON Pattern

**This is the magic.** Every SEVEN rule lives in `config/`, not scattered in source code.

### `config/seven_parts.json`
Defines the **building typology** (your "Parts" in the notes). Example:

```json
{
  "parts": [
    {
      "id": "BOH",
      "name": "Back of House",
      "description": "Staff-only areas: offices, lobbies, amenities, circulation",
      "included_in_surveys": ["GFA", "BUA"],
      "wall_measurement_rule": "interior_face_max_200mm",
      "source": "SEVEN_PDF_§4.3.6"
    },
    {
      "id": "FOH",
      "name": "Front of House",
      "description": "Guest-accessible areas: public realm, guest facilities",
      "included_in_surveys": ["GLA", "GFA", "BUA"],
      "wall_measurement_rule": "interior_face_max_200mm",
      "source": "SEVEN_PDF_§4.3.5"
    },
    ...
  ]
}
```

### `config/seven_cumulative_surveys.json`
Defines the **Cumulative Area Survey types** (your "Regions"). Example:

```json
{
  "surveys": [
    {
      "id": "GLA",
      "name": "Gross Leasable Area",
      "parts": ["RETAIL", "F&B", "CINEMA", "ISA", ...],
      "formula": "SUM(parts where not ExcludedPerSection4.X)",
      "source": "SEVEN_PDF_§4.3.4"
    },
    {
      "id": "GFA",
      "name": "Gross Floor Area",
      "parts": ["GLA", "FOH", "BOH", "wall_areas_not_in_GLA"],
      "formula": "GLA + FOH + BOH + (walls - walls_in_GLA)",
      "source": "SEVEN_PDF_§4.3.7"
    },
    ...
  ]
}
```

### `config/seven_measurement_rules.json`
Defines **how to measure each wall condition** (boundary offsets, void logic).

```json
{
  "measurement_rules": [
    {
      "condition": "exterior_wall_no_common_area",
      "offset_rule": "interior_face",
      "description": "Exterior wall with no shared common area beyond it",
      "source": "SEVEN_PDF_§4.4.1_Figure_4.2"
    },
    {
      "condition": "exterior_wall_with_facade_element",
      "offset_rule": "interior_face_plus_non_structural_projection_thickness",
      "description": "Exterior wall with non-structural projection (e.g., balcony)",
      "source": "SEVEN_PDF_§4.4.2_Figure_4.3",
      "mandatory_dwg_detail": true,
      "note": "DXF must differentiate structural vs. non-structural projections"
    },
    ...
  ],
  "void_measurement_rules": [
    {
      "void_type": "shaft_serving_single_tenant",
      "measure_to": "interior_face",
      "max_thickness_to_common": "200mm",
      "source": "SEVEN_PDF_§4.4_Figure_4.10"
    },
    {
      "void_type": "shaft_for_gfa_aggregation",
      "measure_to": "centerline",
      "source": "SEVEN_PDF_Figure_4.59"
    }
  ]
}
```

---

## ✅ Mandatory vs. Optional DWG Details

**Mandatory** (software throws an error if missing or ambiguous; engineer must redraw):

| Detail | Why | Location |
|--------|-----|----------|
| **Enclosed regions with hard boundaries** | Algorithm needs closed polygons | Every space |
| **Region labels (FOH, BOH, ISA, etc.)** | Algorithm needs typology tags | Every polygon |
| **Wall type differentiation** (structural vs. non-structural) | Boundary offset rules depend on it | All exterior + shared walls |
| **Double-wall thickness drawn** | Void measurement = centerline of double walls; drawing only a line makes centerline ambiguous | Shared walls between two areas |
| **Void/shaft explicit classification** | Measurement changes if shaft serves one tenant (interior-face) vs. building-wide (centerline) | All voids (Figure 4.10 vs. 4.59) |
| **Parking floor boundary** (if present) | Parking included in BUA but excluded from GFA; boundary must be explicit | Parking levels (if any) |
| **Non-structural projection flags** | GFA excludes them (§4.4.2); GLA includes them (§4.3.4) | All balconies, canopies, overhangs |
| **Layer/entity color coding** | Fast visual audit of regions; reduces parsing mismatches | N/A if labels unambiguous |

**Optional** (software ignores; won't error if missing):

| Detail | Reason |
|--------|--------|
| MEP/structural grid lines | Informational only; algorithm only needs boundary polygons |
| Dimension annotations | Informational; software calculates from geometry |
| Section markers, reference clouds | Informational |
| Finished surface details (wood, tile, etc.) | Informational; doesn't change area |
| Architectural plans with furnishing | Informational; algorithm only reads polygons |

**Conditionally Mandatory** (depends on survey type):

- **Non-structural projections**: Mandatory (draw as separate polygon) for **BUA** calculations. Optional for **GFA** (they'll be excluded anyway, so the code will just flag and exclude them rather than error). Flagged for engineer review but not a hard stop if missing.

---

## 🔍 Validation & Error Messages

When a **mandatory detail is missing or ambiguous**, the tool outputs:

```
ERROR [DXF_VALIDATION] Line 145, Layer "FOH_Ground":
  Missing detail: "Wall type differentiation"
  Region boundary cannot be correctly offset without knowing if bounding wall is
  structural (centerline measurement) or non-structural (interior-face measurement).
  Required by: SEVEN_PDF_§4.4.1
  Action: Redraw with structural vs. non-structural differentiation and re-import.
```

When an **optional detail is missing** (e.g., dimension annotations):

```
WARNING [DXF_VALIDATION] Layer "BOH_Ground":
  Optional detail missing: "Dimension annotations"
  Proceeding without visual audit layer. Areas calculated from DXF geometry alone.
  This is OK — all metrics will be correct. Just won't have legacy dimension layer for cross-check.
```

When an **unresolved conflict** in SEVEN rules is hit (void measurement ambiguity):

```
UNCERTAIN [VOID_MEASUREMENT] Layer "Void_01", serves multiple tenants.
  SEVEN_PDF_§4.4 (p.59) says: interior-face, max 200mm to common boundary.
  SEVEN_PDF_Figure_4.59 (p.68) says: centerline for GFA aggregation.
  
  Assumption used: centerline (GFA mode).
  
  If this shaft is for a single tenant only, redraw label as "VOID_SINGLE_TENANT"
  and re-import to use interior-face rule instead.
  
  Source conflict: SEVEN_PDF_§4.4_vs_Figure_4.59 (flagged for SEVEN review)
```

---

## 🧪 Testing Strategy

Each Agent mode phase creates a dedicated test file. Example test structure:

```python
# tests/test_geometry_engine.py

import pytest
from src.geometry_engine import apply_boundary_rules
from src.config_loader import load_measurement_rules

def test_exterior_wall_interior_face_offset():
    """Exterior wall with no adjacent common area → interior-face rule applies."""
    rule = load_measurement_rules()["exterior_wall_no_common_area"]
    polygon = ...  # synthetic 100mm thick exterior wall
    result = apply_boundary_rules(polygon, rule)
    assert result.offset_applied == "interior_face"
    assert result.area_before == pytest.approx(1000, rel=0.01)  # m²

def test_void_centerline_vs_interior_face():
    """Void serving multiple tenants (GFA) vs. single tenant (GLA) → different measurements."""
    ...
```

Each phase's PR includes a `pytest` run. Required: **all tests green before merge**.

---

## 📊 Config File Ownership & Updates

- **Phases 1–3:** Use `config/*.json` as-is (read-only in those phases).
- **Phase 5:** If real DWG testing reveals a SEVEN rule was misinterpreted, update `config/*.json` and re-run Phase 5 validation.
- **After Phase 5:** If you discover a rule ambiguity or typo in SEVEN's PDF, document it in `config/*.json` as a `"flag"` field with a reference, then notify SEVEN. Do not guess or "fix" the rule — flag it, escalate, and ship with a warning in the validation step.

---

## 🚀 Agent Mode Workflow

**Each phase opens a fresh Agent Mode session.** Instructions:

1. **Copy this file** into the repo as `.github/copilot-instructions.md` before starting.
2. **Open the repo** in Copilot (VS Code / JetBrains integration).
3. **Start Agent Mode** (slash command: `/plan` or IDE menu).
4. **Paste the phase prompt** (provided after Phase 0 closes).
5. **Let Agent review/edit**, then create a PR.
6. **You review the diff**; ask questions or request changes in the PR.
7. **Once approved, merge.** Agent auto-detects and starts Phase N+1.

---

## ⚠️ Unresolved Questions (Flag for SEVEN Before Phase 1)

These four items from the PDF analysis remain **unconfirmed**. Before Phase 1 closes, confirm with SEVEN:

1. **Void Measurement Conflict (§4.4 vs Figure 4.59):** Interior-face (p.59) or centerline (p.68)?  
   → **Interim decision (Phase 1):** Assume centerline for GFA; add a DXF label override (`VOID_SINGLE_TENANT`) if interior-face is needed.

2. **Non-structural Projections in GFA:**  
   → **Interim decision (Phase 1):** Exclude from GFA (per §4.4.2), but warn if they're present.

3. **"Diagram" in FOH Definitions:** Appears to be a typo for "Atrium" or "Internal Covered Public Realm."  
   → **Interim decision (Phase 1):** Accept either label in DXF; map both to `ATRIUM` typology internally.

4. **Parking Floor Boundary:** GFA excludes parking; BUA includes it. DXF must explicitly flag parking levels.  
   → **Interim decision (Phase 1):** Require a `PARKING` label on parking-level polygons; error if ambiguous.

---

## 📖 Reference Files (In This Repo)

- `SEVEN_PDF_0DMQL00-DLVR-00-SEV-PM-GUD-00016_Rev00_Aug2025.pdf` — Source document (reference only, not executable)
- `0DMQL00-DLVR-00-SEV-PM-TEM-00026_00_Area_Template.xlsx` — Official output template (defines schema)
- `SEVEN_Area_Measurement_Rules.json` — Full extracted rules (for auditing; see `config/` for the active data)

---

## 🎯 Success Criteria (Phase 5 Exit Gates)

- ✅ All unit tests pass (`pytest tests/ -v`)
- ✅ Synthetic DXF fixtures parse and calculate without errors
- ✅ Excel output matches SEVEN template schema exactly (row/column alignment, formulas)
- ✅ DWG validator flags all mandatory missing details; ignores optional ones
- ✅ Real project DXF (provided late Phase 1/early Phase 2) parses + calculates correctly
- ✅ Generated `.xlsx` passes SEVEN's template validation (if such a validator exists; confirm with SEVEN)

---

**Questions during execution?** Reference this file and the `config/` JSON files, not the original PDF. The JSON is authoritative (because it's compiled from the PDF and remains machine-readable).

