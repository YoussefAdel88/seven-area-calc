import argparse
from pathlib import Path
import json

from .validators import validate_dwg_file, DWGValidationError
from .dxf_parser import parse_dxf
from .measurement_engine import compute_survey_area
from .excel_writer import write_area_template


def main():
    parser = argparse.ArgumentParser(description="SEVEN Area Measurement CLI")
    parser.add_argument("--input", "-i", required=True, help="Input DXF file path")
    parser.add_argument("--validate", action="store_true", help="Run DWG validators before processing")
    parser.add_argument("--surveys", help="Comma-separated survey IDs to compute (default: GLA,GFA,BUA)")
    parser.add_argument("--export", "-o", help="Output Excel file path (optional)")
    parser.add_argument("--wall-thickness", type=float, default=0.3, help="Default wall thickness in meters")

    args = parser.parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}")
        return

    if args.validate:
        try:
            ok, msgs = validate_dwg_file(str(input_path))
        except DWGValidationError as e:
            print(f"Validation error: {e}")
            return
        if not ok:
            print("Validation FAILED. Messages:")
            for m in msgs:
                print(f" - {m}")
            print("Fix the DXF and re-run. Stopping.")
            return
        print("Validation passed.")

    # Parse DXF
    print(f"Parsing DXF: {input_path}")
    regions = parse_dxf(str(input_path))
    print(f"Found {len(regions)} regions:")
    for r in regions:
        print(f" - {r.label}: area={r.polygon.area:.3f} m2 (handle {r.source_handle})")

    surveys = ["GLA", "GFA", "BUA"]
    if args.surveys:
        surveys = [s.strip().upper() for s in args.surveys.split(",") if s.strip()]

    results = []
    for s in surveys:
        res = compute_survey_area(regions, s, wall_thickness_m=args.wall_thickness)
        print(f"Survey {s}: {res.area_sqm:.3f} m2")
        results.append(res)

    if args.export:
        out = Path(args.export)
        write_area_template(str(out), results)
        print(f"Excel exported: {out}")
    else:
        # save to default filename in same folder as input
        default_out = input_path.with_suffix("")
        outname = input_path.with_name(input_path.stem + "_area_output.xlsx")
        write_area_template(str(outname), results)
        print(f"Excel exported: {outname}")


if __name__ == "__main__":
    main()
