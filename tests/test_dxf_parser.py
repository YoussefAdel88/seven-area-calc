import os
from pathlib import Path

import pytest
import ezdxf

from src.dxf_parser import DXFParserError, parse_dxf
from tests.fixture_utils import ensure_fixtures, fixture_path


def test_parse_minimal_single_space():
    ensure_fixtures()
    path = fixture_path("minimal_single_space.dxf")
    regions = parse_dxf(str(path))

    assert len(regions) == 1
    region = regions[0]
    assert region.label == "RETAIL"
    assert region.polygon.area == pytest.approx(4.0)
    coords = list(region.polygon.exterior.coords)
    assert coords[0] == coords[-1]
    assert coords[0] == (0.0, 0.0)


def test_missing_label_raises(tmp_path: Path):
    path = tmp_path / "missing_label.dxf"
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (1, 0), (1, 1), (0, 1)], close=True)
    doc.saveas(str(path))

    with pytest.raises(DXFParserError, match="Missing region label"):
        parse_dxf(str(path))
