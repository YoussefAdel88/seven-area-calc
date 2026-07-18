from pathlib import Path
import openpyxl
from src.measurement_engine import compute_survey_area
from src.dxf_parser import Region
from src.excel_writer import write_area_template


def make_region(label: str, xmin: float, ymin: float, size: float) -> Region:
    from shapely.geometry import Polygon
    poly = Polygon([(xmin, ymin), (xmin + size, ymin), (xmin + size, ymin + size), (xmin, ymin + size), (xmin, ymin)])
    return Region(label=label, polygon=poly, source_handle="test")


def test_write_area_template(tmp_path: Path):
    # create sample regions
    retail = make_region("RETAIL", 0, 0, 10)
    atrium = make_region("ATRIUM", 20, 0, 5)

    regions = [retail, atrium]

    gla_res = compute_survey_area(regions, "GLA")
    gfa_res = compute_survey_area(regions, "GFA")

    out_file = tmp_path / "area_output.xlsx"
    write_area_template(str(out_file), [gla_res, gfa_res])

    # load workbook and verify that the GLA line item row (id 32 in template) was written
    wb = openpyxl.load_workbook(str(out_file), data_only=True)
    ws = wb.active

    # find the line item for source_survey == 'GLA' and 'GFA' from config by scanning column B/C
    found_gla = False
    found_gfa = False
    for row in ws.iter_rows(min_row=1, max_row=200, min_col=1, max_col=4):
        rid = row[0].value
        cat = row[1].value
        desc = row[2].value
        val = row[3].value
        # The template places Total Complex GLA at row 41 per schema; we just find any cell where val equals gla_res.area_sqm
        if isinstance(val, (int, float)) and abs(val - gla_res.area_sqm) < 1e-6:
            found_gla = True
        if isinstance(val, (int, float)) and abs(val - gfa_res.area_sqm) < 1e-6:
            found_gfa = True
    assert found_gla, "GLA value not written to Excel"
    assert found_gfa, "GFA value not written to Excel"
