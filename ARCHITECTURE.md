# Architecture Overview

*To be completed after Phase 1 closes.*

## Current Status (Phase 0)

- Configuration structure defined (`config/`)
- Testing strategy outlined
- Mandatory vs. optional DWG details documented

## Design Principles

1. **Rules as Data**: All SEVEN measurement logic lives in `config/*.json`, not hardcoded Python.
2. **Boundary Condition Lookup**: Wall type determines offset rule at runtime.
3. **Synthetic Testing**: All tests use generated DXF fixtures until real project files are available.
4. **Fail Loud, Not Silent**: Missing mandatory DWG details → hard error + recovery action.

