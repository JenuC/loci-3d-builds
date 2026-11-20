"""Utility to inspect reference STEP files in reference/ and extract hole coordinates.

Scans reference/*.step and reference/*.stp (or explicit CLI paths) using build123d.import_step,
prints bounding boxes and volumes, and lists deduplicated cylindrical face centers, axes, and
diameters for rapid extraction of official PI U-760 / U-651 hole patterns.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from build123d import GeomType, import_step

ROOT_DIR = Path(__file__).resolve().parent.parent
REFERENCE_DIR = ROOT_DIR / "reference"


def _axis_label(dx: float, dy: float, dz: float) -> str:
    if abs(dz) > 0.99:
        return "Z"
    if abs(dx) > 0.99:
        return "X"
    if abs(dy) > 0.99:
        return "Y"
    return f"({dx:.2f},{dy:.2f},{dz:.2f})"


def inspect_step_file(step_path: Path, round_tol: float = 0.05) -> None:
    print("=" * 80)
    print(f"File: {step_path}")
    shape = import_step(str(step_path))
    bb = shape.bounding_box()
    print(
        f"Bounding Box (mm): "
        f"min=({bb.min.X:.3f}, {bb.min.Y:.3f}, {bb.min.Z:.3f})  "
        f"max=({bb.max.X:.3f}, {bb.max.Y:.3f}, {bb.max.Z:.3f})  "
        f"size=({bb.size.X:.3f}, {bb.size.Y:.3f}, {bb.size.Z:.3f})"
    )
    try:
        print(f"Volume (mm^3): {shape.volume:.3f}")
    except Exception:
        pass

    cylinders: dict[tuple[str, float, float, float], dict[str, float | str]] = {}
    for face in shape.faces():
        if face.geom_type != GeomType.CYLINDER:
            continue
        try:
            radius = float(face.radius)
            dia = 2.0 * radius
            axis = face.axis_of_rotation
            loc = axis.position
            d = axis.direction
            axis_lbl = _axis_label(float(d.X), float(d.Y), float(d.Z))

            # Project center to plane orthogonal to axis for deduplication of split cylinders
            if axis_lbl == "Z":
                c1, c2 = float(loc.X), float(loc.Y)
            elif axis_lbl == "X":
                c1, c2 = float(loc.Y), float(loc.Z)
            elif axis_lbl == "Y":
                c1, c2 = float(loc.X), float(loc.Z)
            else:
                c1, c2 = float(loc.X), float(loc.Y)

            key = (
                axis_lbl,
                round(dia / round_tol) * round_tol,
                round(c1 / round_tol) * round_tol,
                round(c2 / round_tol) * round_tol,
            )
            if key not in cylinders:
                cylinders[key] = {
                    "axis": axis_lbl,
                    "dia": dia,
                    "x": float(loc.X),
                    "y": float(loc.Y),
                    "z": float(loc.Z),
                }
        except Exception:
            continue

    sorted_cyls = sorted(
        cylinders.values(),
        key=lambda c: (str(c["axis"]), float(c["dia"]), float(c["x"]), float(c["y"])),
    )

    print(f"Unique cylindrical features found: {len(sorted_cyls)}")
    if sorted_cyls:
        print(f"  {'Axis':<10} {'Dia (mm)':>10} {'Center X':>11} {'Center Y':>11} {'Center Z':>11}")
        print("  " + "-" * 57)
        for c in sorted_cyls:
            print(
                f"  {str(c['axis']):<10} {float(c['dia']):>10.3f} "
                f"{float(c['x']):>11.3f} {float(c['y']):>11.3f} {float(c['z']):>11.3f}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect reference STEP files for hole coordinates.")
    parser.add_argument("files", nargs="*", type=Path, help="Optional explicit STEP file paths")
    args = parser.parse_args()

    if args.files:
        step_files = args.files
    else:
        step_files = sorted(
            [
                p
                for p in REFERENCE_DIR.iterdir()
                if p.is_file() and p.suffix.lower() in {".step", ".stp"}
            ]
            if REFERENCE_DIR.exists()
            else []
        )

    if not step_files:
        print(f"No .step / .stp files found in {REFERENCE_DIR}.")
        print("Add official PI U-760 / U-651 STEP files to reference/ and re-run this script.")
        return

    for p in step_files:
        inspect_step_file(p)


if __name__ == "__main__":
    main()
