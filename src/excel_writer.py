from pathlib import Path
from typing import Dict, List
import openpyxl
from .config_loader import load_json_config
from src.measurement_engine import MeasurementResult


def write_area_template(output_path: str, measurement_results: List[MeasurementResult]) -> None:
    """Write an Excel file matching the SEVEN area template schema.

    - Loads config/seven_template_schema.json to locate target rows/columns.
    - Writes line item metadata and fills AREAS (sm) column with values from measurement_results
      when the line_item.source_survey matches a computed survey.
    """
    schema = load_json_config("seven_template_schema.json")
    info = schema.get("template_info", {})
    line_items = schema.get("line_items", [])

    out_path = Path(output_path)
    wb = openpyxl.Workbook()
    sheet_name = info.get("sheet_name", "Area Template")
    ws = wb.active
    ws.title = sheet_name

    # Write headers (row numbers are arbitrary; we will place line items at their configured rows)
    for li in line_items:
        row = li.get("row")
        if not row:
            continue
        # Column mapping: ID=A, CATEGORY=B, DESCRIPTION=C, AREAS (sm)=D
        ws.cell(row=row, column=1, value=li.get("id"))
        ws.cell(row=row, column=2, value=li.get("category"))
        ws.cell(row=row, column=3, value=li.get("description"))

    # Build a lookup of survey id -> area value from measurement_results
    survey_map: Dict[str, float] = {mr.survey_id: mr.area_sqm for mr in measurement_results}

    # Fill area values for matching line items
    for li in line_items:
        row = li.get("row")
        if not row:
            continue
        source = li.get("source_survey")
        if source and source in survey_map:
            ws.cell(row=row, column=4, value=survey_map[source])

    # Save workbook
    wb.save(out_path)
