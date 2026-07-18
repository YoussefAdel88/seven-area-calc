# SEVEN Area Measurement Calculator

Software to parse DXF files containing enclosed regions labeled with SEVEN building typology,
apply measurement rules from SEVEN Design Standards, and output area calculations in the
official SEVEN Area Template (.xlsx) format.

## Quick Start — Web Interface (Phase 6)

```bash
pip install -r requirements.txt
python -m src.web_server
```

Then open **http://localhost:5000** in your browser. Drag and drop a DXF file, click "Process", and download results.

## Quick Start — Command Line (Phase 5)

```bash
python -m src.cli --input sample.dxf --output results.xlsx
```

## Development

- **Agent Mode Phases:** See `.github/copilot-instructions.md`
- **Configuration:** All SEVEN rules live in `config/*.json` (not hardcoded in source)
- **Tests:** `pytest tests/ -v`

## Input: DXF Format

- Enclosed polygonal regions (hard boundaries)
- Each region labeled with SEVEN typology (FOH, BOH, ISA, etc.)
- Scaled correctly in meters
- Wall thickness differentiation (structural vs. non-structural)

## Output: Excel

- `Area_Template.xlsx` matching SEVEN's official schema
- All cumulative surveys calculated (GLA, GFA, BUA, PA, etc.)
- Validation report (flagged missing details, warnings)

