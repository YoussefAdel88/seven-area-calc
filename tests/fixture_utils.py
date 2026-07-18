from pathlib import Path

import ezdxf

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)


def fixture_path(filename: str) -> Path:
    return FIXTURE_DIR / filename


def ensure_fixtures() -> None:
    _create_minimal_single_space()
    _create_double_wall_test()
    _create_void_centerline_test()


def _create_minimal_single_space() -> None:
    path = fixture_path("minimal_single_space.dxf")
    if path.exists():
        path.unlink()
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 7
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (2, 0), (2, 2), (0, 2)], close=True)
    text = msp.add_text("RETAIL", dxfattribs={"height": 0.25})
    text.dxf.insert = (1, 1, 0)
    doc.saveas(str(path))


def _create_double_wall_test() -> None:
    path = fixture_path("double_wall_test.dxf")
    if path.exists():
        path.unlink()
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 7
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (2, 0), (2, 2), (0, 2)], close=True)
    msp.add_lwpolyline([(2.4, 0), (4.4, 0), (4.4, 2), (2.4, 2)], close=True)
    t1 = msp.add_text("RETAIL", dxfattribs={"height": 0.25})
    t1.dxf.insert = (1, 1, 0)
    t2 = msp.add_text("FOH", dxfattribs={"height": 0.25})
    t2.dxf.insert = (3.4, 1, 0)
    doc.saveas(str(path))


def _create_void_centerline_test() -> None:
    path = fixture_path("void_centerline_test.dxf")
    if path.exists():
        return
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 7
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (4, 0), (4, 4), (0, 4)], close=True)
    msp.add_lwpolyline([(1, 1), (2, 1), (2, 2), (1, 2)], close=True)
    text = msp.add_text("VOID_MULTI_TENANT", dxfattribs={"height": 0.25})
    text.dxf.insert = (1.5, 1.5, 0)
    outer_text = msp.add_text("FOH", dxfattribs={"height": 0.25})
    outer_text.dxf.insert = (3, 3, 0)
    doc.saveas(str(path))
