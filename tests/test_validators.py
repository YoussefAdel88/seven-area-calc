from pathlib import Path
import ezdxf
from src.validators import validate_dwg_file, DWGValidationError
from tests.fixture_utils import fixture_path


def test_validator_fails_when_missing_wall_tags(tmp_path: Path):
    # Use existing double_wall_test fixture which does NOT include explicit DOUBLE_WALL token
    fx = fixture_path("double_wall_test.dxf")
    valid, msgs = validate_dwg_file(str(fx))
    assert not valid
    assert any("double_wall_centerline" in m for m in msgs)


def test_validator_passes_with_explicit_tags(tmp_path: Path):
    # Create a temporary DXF with explicit tags to satisfy validators
    p = tmp_path / "tagged.dxf"
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 7
    msp = doc.modelspace()
    # simple polygon
    msp.add_lwpolyline([(0, 0), (2, 0), (2, 2), (0, 2)], close=True)
    # Add required tokens
    tokens = ["DOUBLE_WALL", "CURTAIN_WALL", "SHARED_WALL", "NON_STRUCTURAL_PROJECTION", "STRUCTURAL_PROJECTION", "DEMISING_WALL", "VOID_SINGLE_TENANT", "VOID_MULTI_TENANT"]
    y = 0.5
    for tok in tokens:
        tx = msp.add_text(tok, dxfattribs={"height": 0.15})
        tx.dxf.insert = (0.5, y, 0)
        y += 0.2
    doc.saveas(str(p))

    valid, msgs = validate_dwg_file(str(p))
    assert valid
    assert msgs == []
