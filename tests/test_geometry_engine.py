import pytest

from src.dxf_parser import parse_dxf
from src.geometry_engine import apply_measurement_rule, classify_wall_segments, get_void_rule_id_for_label
from tests.fixture_utils import ensure_fixtures, fixture_path


def test_double_wall_centerline_detection():
    ensure_fixtures()
    regions = parse_dxf(str(fixture_path("double_wall_test.dxf")))
    assert len(regions) == 2

    classification = classify_wall_segments([region.polygon for region in regions])
    assert len(classification["double_walls"]) == 1
    assert classification["double_walls"][0]["gap_m"] == pytest.approx(0.4, abs=1e-3)
    assert classification["shared_boundaries"] == []
    assert len(classification["exterior_walls"]) == 0


def test_void_centerline_selection():
    ensure_fixtures()
    regions = parse_dxf(str(fixture_path("void_centerline_test.dxf")))
    void_region = next((region for region in regions if region.label.startswith("VOID")), None)
    assert void_region is not None

    multi_rule_id = get_void_rule_id_for_label(void_region.label)
    assert multi_rule_id == "void_multi_tenant"

    result = apply_measurement_rule(void_region.polygon, multi_rule_id, wall_thickness_m=0.3)
    assert result.offset_rule == "centerline"
    assert result.offset_distance_m == pytest.approx(0.15, abs=1e-6)

    single_rule_id = get_void_rule_id_for_label("VOID_SINGLE_TENANT")
    single_result = apply_measurement_rule(void_region.polygon, single_rule_id, wall_thickness_m=0.3)
    assert single_result.offset_rule == "interior_face"
    assert single_result.offset_distance_m == pytest.approx(0.2, abs=1e-6)
