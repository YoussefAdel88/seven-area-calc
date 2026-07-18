from shapely.geometry import Polygon
from src.measurement_engine import compute_survey_area
from src.dxf_parser import Region


def make_region(label: str, xmin: float, ymin: float, size: float) -> Region:
    poly = Polygon([(xmin, ymin), (xmin + size, ymin), (xmin + size, ymin + size), (xmin, ymin + size), (xmin, ymin)])
    return Region(label=label, polygon=poly, source_handle="test")


def test_compute_gla_and_gfa_simple():
    # Create two regions: RETAIL (10x10 = 100 m2) and ATRIUM (5x10 = 50 m2)
    retail = make_region("RETAIL", 0, 0, 10)
    atrium = make_region("ATRIUM", 20, 0, 5)

    regions = [retail, atrium]

    # GLA should include RETAIL (per config), but not ATRIUM
    gla_res = compute_survey_area(regions, "GLA")
    assert gla_res.area_sqm == 100.0
    assert gla_res.breakdown.get("RETAIL") == 100.0

    # GFA should include GLA + FOH (ATRIUM is FOH/part of FOH in our config mapping)
    gfa_res = compute_survey_area(regions, "GFA")
    # RETAIL 100 + ATRIUM 25 -> 125 total
    assert gfa_res.area_sqm == 125.0
    assert gfa_res.breakdown.get("RETAIL") == 100.0
    assert gfa_res.breakdown.get("ATRIUM") == 25.0
