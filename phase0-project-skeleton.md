# Phase 0 Deliverables Checklist

## What to Create in Your New GitHub Repo

Create a **new, empty GitHub repository** (e.g., `seven-area-calc`) and add these files:

### 1. Copy into `.github/`
```
.github/
└── copilot-instructions.md    ← Copy phase0-copilot-instructions.md to here
```

### 2. Create `config/` folder with these 4 JSON seed files

Use the values provided in the JSON export you already have (`seven_area_rules.json`). Split it into these four files:

#### **a) `config/seven_parts.json`**
All building typology definitions (FOH, BOH, ISA, GLA subtypes, etc.).  
**Source:** SEVEN_PDF_§2 (Definitions table) + Sections 4.3.5–4.3.14

**Structure:**
```json
{
  "parts": [
    {
      "id": "BOH",
      "name": "Back of House",
      "description": "...",
      "included_in_surveys": ["GFA", "BUA"],
      "wall_measurement_rule": "interior_face_max_200mm",
      "source": "SEVEN_PDF_§4.3.6"
    },
    ...
  ]
}
```

#### **b) `config/seven_cumulative_surveys.json`**
All survey types and their constituent parts: GLA, GFA, BUA, PA, PC, FAR, PR, ONEA, OFEA.  
**Source:** SEVEN_PDF_§2.1 (Definitions table) + §4.3

**Structure:**
```json
{
  "surveys": [
    {
      "id": "GLA",
      "name": "Gross Leasable Area",
      "description": "Area in exclusive tenant occupation/beneficial use...",
      "parts": ["F&B", "RETAIL", "CINEMA", "ISA", ...],
      "excludes": ["BOH", "FOH_circulation", ...],
      "formula": "SUM(leasable_parts)",
      "source": "SEVEN_PDF_§4.3.4"
    },
    {
      "id": "GFA",
      "name": "Gross Floor Area",
      "description": "All internal occupiable floor area, basement→roof...",
      "parts": ["GLA", "FOH", "BOH", "wall_areas_not_in_GLA"],
      "formula": "GLA + FOH + BOH + (walls - walls_in_GLA)",
      "ratio_denominator": "PA",  // FAR = GFA / PA
      "source": "SEVEN_PDF_§4.3.7"
    },
    ...
  ]
}
```

#### **c) `config/seven_measurement_rules.json`**
Boundary condition lookups + void measurement rules.  
**Source:** SEVEN_PDF_§4.4 (General Methodology) + Figures 4.2–4.12, 4.59

**Structure:**
```json
{
  "measurement_rules": [
    {
      "id": "exterior_wall_no_common_area",
      "condition": "Exterior wall with no shared common area beyond it",
      "offset_rule": "interior_face",
      "offset_distance_mm": 0,
      "description": "Measure to interior face of exterior wall",
      "source": "SEVEN_PDF_§4.4.1_Figure_4.2",
      "mandatory_dwg_detail": false
    },
    {
      "id": "exterior_wall_with_curtain_wall",
      "condition": "Exterior wall with curtain wall facade",
      "offset_rule": "interior_face",
      "offset_distance_mm": 0,
      "description": "Curtain wall thickness not added to area",
      "source": "SEVEN_PDF_§4.4.3_Figure_4.5",
      "mandatory_dwg_detail": true,
      "note": "DXF must show curtain wall as separate line/element"
    },
    ...
  ],
  "void_measurement_rules": [
    {
      "id": "void_single_tenant",
      "void_type": "Shaft serving single tenant",
      "measure_to": "interior_face",
      "max_thickness_to_boundary_mm": 200,
      "description": "Voids/shafts inside or serving a tenant → interior face, max 200mm to common boundary",
      "source": "SEVEN_PDF_§4.4_p.59_Figures_4.10-4.12"
    },
    {
      "id": "void_gfa_aggregation",
      "void_type": "Shaft for building-wide GFA aggregation",
      "measure_to": "centerline",
      "description": "When counting void spaces for GFA calculations, use centerline",
      "source": "SEVEN_PDF_Figure_4.59_p.68"
    }
  ]
}
```

#### **d) `config/seven_template_schema.json`**
Maps output data to the official SEVEN Area Template (.xlsx) cell locations and formulas.  
**Source:** `0DMQL00-DLVR-00-SEV-PM-TEM-00026_00_Area_Template.xlsx` (the official template)

**Structure:**
```json
{
  "template_info": {
    "document_code": "0DMQL00-DLVR-00-SEV-PM-TEM-00026_00",
    "sheet_name": "Area Template",
    "header_row": 11,
    "data_start_row": 12,
    "columns": [
      {"name": "ID", "col": "A", "type": "integer"},
      {"name": "CATEGORY", "col": "B", "type": "string"},
      {"name": "DESCRIPTION", "col": "C", "type": "string"},
      {"name": "AREAS (sm)", "col": "D", "type": "float"},
      {"name": "TITLE DEED", "col": "E", "type": "string"},
      {"name": "T/D EXTENSION", "col": "F", "type": "string"}
    ]
  },
  "line_items": [
    {
      "id": 1,
      "category": "LAND + OUT OF PLOT DEVELOPMENT",
      "description": "Land Area",
      "source_survey": "PA",
      "formula": "=Plot_Area"
    },
    {
      "id": 2,
      "category": "LAND + OUT OF PLOT DEVELOPMENT",
      "description": "Out of Plot Development",
      "source_survey": "OFEA",
      "formula": "=Out_of_Plot_External_Area"
    },
    ...
  ]
}
```

### 3. Create root files

#### **a) `requirements.txt`**
```
ezdxf==1.0.0
shapely==2.0.0
openpyxl==3.10.0
pytest==7.4.0
pytest-cov==4.1.0
```

#### **b) `README.md`** (minimal, Phase 0)
```markdown
# SEVEN Area Measurement Calculator

Software to parse DXF files containing enclosed regions labeled with SEVEN building typology,
apply measurement rules from SEVEN Design Standards, and output area calculations in the
official SEVEN Area Template (.xlsx) format.

## Quick Start (After Phases 1–5)

```bash
pip install -r requirements.txt
python -m src.cli --input sample.dxf --output results.xlsx
```

## Development

- **Agent Mode Phases:** See `.github/copilot-instructions.md`
- **Configuration:** All SEVEN rules live in `config/*.json` (not hardcoded in source)
- **Tests:** `pytest tests/ -v`

## Documentation

- `.github/copilot-instructions.md` — Full mandate + workflow
- `ARCHITECTURE.md` — Design rationale (written Phase 1)
- `config/` — Machine-readable SEVEN rules

## Input: DXF Format

- Enclosed polygonal regions (hard boundaries)
- Each region labeled with SEVEN typology (FOH, BOH, ISA, etc.)
- Scaled correctly in meters
- Wall thickness differentiation (structural vs. non-structural)

See `.github/copilot-instructions.md` for full mandatory/optional detail list.

## Output: Excel

- `Area_Template.xlsx` matching SEVEN's official schema
- All cumulative surveys calculated (GLA, GFA, BUA, PA, etc.)
- Validation report (flagged missing details, warnings)

---

**Status:** Phase 0 (config + skeleton). Phases 1–5 in development via Agent Mode.
```

#### **c) `ARCHITECTURE.md`** (Phase 0, placeholder)
```markdown
# Architecture Overview

*To be completed after Phase 1 closes.*

## Current Status (Phase 0)

- Configuration structure defined (`config/`)
- Testing strategy outlined
- Mandatory vs. optional DWG details documented

## Design Principles

1. **Rules as Data**: All SEVEN measurement logic lives in `config/*.json`, not hardcoded Python.
2. **Boundary Condition Lookup**: Wall type (structural/non-structural, exterior/interior) determines offset rule at runtime.
3. **Synthetic Testing**: All tests use generated DXF fixtures until real project files are available.
4. **Fail Loud, Not Silent**: Missing mandatory DWG details → hard error + recovery action.

## Modules (To be filled in Phase 1)

- `dxf_parser.py` — Read .dxf, extract polygons
- `geometry_engine.py` — Apply boundary rules
- `area_calculator.py` — Rollup to GLA/GFA/BUA
- `excel_writer.py` — Output template .xlsx
- `validators.py` — DWG compliance checks

---

*Updates as each phase closes.*
```

#### **d) `.gitignore`** (standard Python)
```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/
ENV/
env/
.vscode/
.idea/
*.xlsx
*.dxf
!tests/fixtures/*.dxf
```

---

## Checklist: Before Pushing to GitHub

- [ ] Created new, empty repo (e.g., `seven-area-calc`)
- [ ] Created `.github/` folder with `copilot-instructions.md`
- [ ] Created `config/` folder with:
  - [ ] `seven_parts.json`
  - [ ] `seven_cumulative_surveys.json`
  - [ ] `seven_measurement_rules.json`
  - [ ] `seven_template_schema.json`
- [ ] Created root files:
  - [ ] `requirements.txt`
  - [ ] `README.md`
  - [ ] `ARCHITECTURE.md`
  - [ ] `.gitignore`
- [ ] Created `src/` folder (empty, ready for Phase 1)
- [ ] Created `tests/` folder (empty, ready for Phase 1)
- [ ] Committed and pushed to GitHub
- [ ] Opened repo in Copilot (VS Code / JetBrains)

---

## Next Step: Phase 1 Prompt

Once pushed, you're ready for Agent Mode Phase 1. The prompt will be:

```
[Phase 1 Prompt — DXF Parser]
You are an Agent Mode session for the SEVEN Area Measurement calculator project.
Your task is to build the DXF parsing + geometry engine foundation.

Reference: .github/copilot-instructions.md
Config files: config/*.json

Phase output:
1. src/dxf_parser.py — Read .dxf files, extract polygons + labels
2. src/geometry_engine.py — Classify walls, detect voids, apply boundary rules
3. tests/fixtures/minimal_single_space.dxf — Synthetic test DXF
4. tests/test_dxf_parser.py — Unit tests
5. tests/test_geometry_engine.py — Unit tests

Success: pytest tests/test_dxf_parser.py tests/test_geometry_engine.py -v passes all tests

[Full prompt follows...]
```

**Don't start Phase 1 until Phase 0 is pushed.**
```

