"""Parametric CAD generator for PI U-760 XY Stage to PI U-651 Rotation Stage Adapter.

Reads all dimensions from params.json (single source of truth) and generates:
  - output/u760_to_u651_adapter_aluminum.step
  - output/u760_to_u651_adapter_aluminum.stl
  - output/u760_to_u651_adapter_pla_prototype.step
  - output/u760_to_u651_adapter_pla_prototype.stl
  - output/assembly_u760_adapter_u651.step
  - output/geometry_metrics.json

Coordinate convention:
  - Z = 0.0 mm : Adapter bottom face (mates with PI U-760 moving platform top).
  - Z = top_deck_z : Main body top deck (9.5 mm Al / 11.5 mm PLA).
  - Z = total_height_mm : Top of 4 raised U-651 precision mounting pads (10.0 mm Al / 12.0 mm PLA).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    BuildSketch,
    Circle,
    Compound,
    Cylinder,
    Face,
    Locations,
    Mode,
    Part,
    Plane,
    Rectangle,
    RectangleRounded,
    Sketch,
    chamfer,
    export_step,
    export_stl,
    extrude,
    fillet,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
PARAMS_PATH = ROOT_DIR / "params.json"
OUTPUT_DIR = ROOT_DIR / "output"

BOSS_DIA_MM = 14.0
PE_GROUND_BOSS_DIA_MM = 10.0
PE_GROUND_PILOT_DIA_MM = 3.3
CABLE_SLOT_FILLET_MM = 1.5


def load_params(path: Path = PARAMS_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _fillet_face_corners(face: Face, radius: float) -> Face:
    """Fillet sharp 2D corners of a pocket face, with per-vertex fallback."""
    if radius <= 0:
        return face
    # Try whole-face fillet first
    for r in (radius, min(radius, 2.0)):
        try:
            res = fillet(face.vertices(), radius=r)
            if res.is_valid:
                return res
        except Exception:
            continue

    # Per-vertex fallback: iterate over original vertex coordinates
    cur = face
    orig_coords = [(float(v.X), float(v.Y)) for v in face.vertices()]
    for cx, cy in orig_coords:
        matches = [
            v for v in cur.vertices() if math.hypot(float(v.X) - cx, float(v.Y) - cy) < 1e-3
        ]
        if not matches:
            continue
        for r in (radius, min(radius, 2.0)):
            try:
                cand = fillet(matches[0], radius=r)
                if cand.is_valid:
                    cur = cand
                    break
            except Exception:
                continue
    return cur


def _fillet_pocket_sketch(sketch: Sketch, radius: float) -> Sketch:
    """Apply 2D corner fillets to every face in the pocket sketch."""
    if radius <= 0:
        return sketch
    filleted_faces = [_fillet_face_corners(f, radius) for f in sketch.faces()]
    return Sketch(filleted_faces)


def build_adapter(params: dict[str, Any], variant_name: str) -> Part:
    """Build the parametric adapter solid for the requested variant."""
    optical = params["optical"]
    u760 = params["u760_interface"]
    u651 = params["u651_interface"]
    var = params["variants"][variant_name]

    outer_x: float = float(u760["adapter_outer_x_mm"])
    outer_y: float = float(u760["adapter_outer_y_mm"])
    corner_r: float = float(u760["corner_fillet_mm"])

    total_h: float = float(var["total_height_mm"])
    pad_proud_h: float = float(u651["mounting_pad_proud_height_mm"])
    top_deck_z: float = total_h - pad_proud_h
    top_deck_t: float = float(var["top_deck_thickness_mm"])
    pocket_depth: float = top_deck_z - top_deck_t

    outer_wall: float = float(var["outer_wall_thickness_mm"])
    collar_wall: float = float(var["aperture_collar_wall_mm"])
    rib_w: float = float(var["rib_width_mm"])
    pocket_r: float = float(var["pocket_fillet_mm"])
    fdm_adder: float = float(var["fdm_clearance_adder_mm"])

    aperture_dia: float = float(optical["adapter_clear_aperture_dia_mm"]) + fdm_adder
    aperture_chamfer: float = float(optical["bottom_objective_chamfer_mm"])

    u760_holes: list[list[float]] = u760["mounting_holes_xy_mm"]
    u760_clr_dia: float = float(u760["hole_clearance_dia_mm"]) + fdm_adder
    u760_cb_dia: float = float(u760["counterbore_dia_mm"]) + fdm_adder
    u760_cb_depth: float = float(u760["counterbore_depth_mm"])

    dowel_holes: list[list[float]] = u760["dowel_pin_holes_xy_mm"]
    dowel_dia: float = float(u760["dowel_pin_dia_mm"]) + fdm_adder

    u651_holes: list[list[float]] = u651["mounting_holes_xy_mm"]
    u651_clr_dia: float = float(u651["hole_clearance_dia_mm"]) + fdm_adder
    u651_cb_dia: float = float(u651["counterbore_dia_mm"]) + fdm_adder
    u651_cb_depth: float = float(u651["counterbore_depth_mm"])
    pad_dia: float = float(u651["mounting_pad_dia_mm"])

    cable_w: float = float(u651["cable_slot_width_mm"])
    cable_d: float = float(u651["cable_slot_depth_mm"])
    pe_xy: list[float] = u651["pe_ground_hole_xy_mm"]
    pe_dia: float = PE_GROUND_PILOT_DIA_MM + fdm_adder

    # 1. Base 2D profile with corner fillets and -X cable strain-relief notch
    with BuildSketch(Plane.XY) as base_profile:
        RectangleRounded(outer_x, outer_y, radius=corner_r)
        # Subtract cable slot notch on -X edge centered at (-outer_x/2, 0)
        with Locations((-outer_x / 2.0, 0.0)):
            RectangleRounded(
                cable_d * 2.0,
                cable_w,
                radius=min(CABLE_SLOT_FILLET_MM, cable_d * 0.45, cable_w * 0.45),
                mode=Mode.SUBTRACT,
            )

    # 2. Underside lightweighting pocket 2D layout
    inner_x = outer_x - 2.0 * outer_wall
    inner_y = outer_y - 2.0 * outer_wall
    inner_r = max(corner_r - outer_wall, 1.5)

    # Diagonal rib angle passing from (0,0) through U-651 holes and toward U-760 corners
    diag_angle_deg = math.degrees(math.atan2(abs(u651_holes[0][1]), abs(u651_holes[0][0])))
    diag_len = math.hypot(outer_x, outer_y)

    with BuildSketch(Plane.XY) as pocket_sketch:
        RectangleRounded(inner_x, inner_y, radius=inner_r)

        # Keep solid outer wall around the -X cable relief cutout
        with Locations((-outer_x / 2.0, 0.0)):
            Rectangle(
                (cable_d + outer_wall) * 2.0,
                cable_w + 2.0 * outer_wall,
                mode=Mode.SUBTRACT,
            )

        # Keep solid central optical collar
        Circle(radius=aperture_dia / 2.0 + collar_wall, mode=Mode.SUBTRACT)

        # Keep solid bosses around all fastener and dowel holes
        with Locations([(x, y) for x, y in u760_holes]):
            Circle(radius=BOSS_DIA_MM / 2.0, mode=Mode.SUBTRACT)
        with Locations([(x, y) for x, y in u651_holes]):
            Circle(radius=BOSS_DIA_MM / 2.0, mode=Mode.SUBTRACT)
        with Locations([(x, y) for x, y in dowel_holes]):
            Circle(radius=BOSS_DIA_MM / 2.0, mode=Mode.SUBTRACT)
        with Locations([(pe_xy[0], pe_xy[1])]):
            Circle(radius=PE_GROUND_BOSS_DIA_MM / 2.0, mode=Mode.SUBTRACT)

        # Symmetric orthogonal ribs (X-axis and Y-axis)
        Rectangle(outer_x, rib_w, mode=Mode.SUBTRACT)
        Rectangle(rib_w, outer_y, mode=Mode.SUBTRACT)

        # Symmetric diagonal ribs connecting central collar -> U-651 bosses -> U-760 bosses
        Rectangle(diag_len, rib_w, rotation=diag_angle_deg, mode=Mode.SUBTRACT)
        Rectangle(diag_len, rib_w, rotation=-diag_angle_deg, mode=Mode.SUBTRACT)

    # Fillet pocket corners in 2D for CNC endmill manufacturability
    pocket_faces = _fillet_pocket_sketch(pocket_sketch.sketch, pocket_r)

    # 3. Assemble 3D solid
    with BuildPart() as adapter:
        # Extrude main body from Z = 0 to Z = top_deck_z
        extrude(base_profile.sketch, amount=top_deck_z)

        # Add 4 raised precision-machined circular mounting pads for U-651 (Z = top_deck_z .. total_h)
        with Locations([(x, y, top_deck_z) for x, y in u651_holes]):
            Cylinder(
                radius=pad_dia / 2.0,
                height=pad_proud_h,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.ADD,
            )

        # Subtract underside lightweighting pockets (Z = 0 .. pocket_depth)
        if pocket_depth > 0.0:
            extrude(pocket_faces, amount=pocket_depth, mode=Mode.SUBTRACT)

        # Central optical clear aperture through-bore (full Z span from -1.0 to total_h + 1.0)
        with Locations((0.0, 0.0, -1.0)):
            Cylinder(
                radius=aperture_dia / 2.0,
                height=total_h + 2.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        # 2.0 mm 45-degree objective clearance chamfer on bottom edge (Z = 0) of central bore
        bore_bottom_edges = [
            e
            for e in adapter.edges()
            if abs(e.center().Z) < 1e-3
            and abs(math.hypot(e.center().X, e.center().Y)) < 1e-3
            and abs(e.radius - aperture_dia / 2.0) < 0.2
        ]
        if bore_bottom_edges and aperture_chamfer > 0.0:
            chamfer(bore_bottom_edges, length=aperture_chamfer)

        # U-760 mounting holes: M4 clearance through-hole + top-down counterbore
        with Locations([(x, y, 0.0) for x, y in u760_holes]):
            Cylinder(
                radius=u760_clr_dia / 2.0,
                height=total_h + 2.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )
        with Locations([(x, y, top_deck_z - u760_cb_depth) for x, y in u760_holes]):
            Cylinder(
                radius=u760_cb_dia / 2.0,
                height=u760_cb_depth + pad_proud_h + 1.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        # U-760 locating dowel pin through-holes
        with Locations([(x, y, 0.0) for x, y in dowel_holes]):
            Cylinder(
                radius=dowel_dia / 2.0,
                height=total_h + 2.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        # U-651 mounting holes: M4 clearance through-hole + bottom-up counterbore
        with Locations([(x, y, 0.0) for x, y in u651_holes]):
            Cylinder(
                radius=u651_clr_dia / 2.0,
                height=total_h + 2.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )
            Cylinder(
                radius=u651_cb_dia / 2.0,
                height=u651_cb_depth,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        # PE ground M4 tap-pilot hole
        with Locations([(pe_xy[0], pe_xy[1], 0.0)]):
            Cylinder(
                radius=pe_dia / 2.0,
                height=total_h + 2.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

    part = adapter.part
    part.label = f"Adapter_{variant_name}"
    return part


def build_assembly(params: dict[str, Any], adapter_al: Part) -> Compound:
    """Build stacked datasheet-envelope mock assembly: U-760 + Aluminum Adapter + U-651."""
    optical = params["optical"]
    u760 = params["u760_interface"]
    u651 = params["u651_interface"]
    al_h = float(params["variants"]["aluminum"]["total_height_mm"])

    u760_t = float(u760["platform_mock_thickness_mm"])
    u760_bore = float(u760["platform_mock_aperture_dia_mm"])

    u651_x = float(u651["stage_outer_x_mm"])
    u651_y = float(u651["stage_outer_y_mm"])
    u651_h = float(u651["stage_height_mm"])
    u651_bore = float(optical["u651_clear_aperture_dia_mm"])

    # U-760 Platform Mock: 150 x 120 x 18 mm, Z = -18.0 .. 0.0 mm
    with BuildPart() as u760_bp:
        with BuildSketch(Plane.XY.offset(-u760_t)) as sk:
            RectangleRounded(150.0, 120.0, radius=4.0)
            Circle(radius=u760_bore / 2.0, mode=Mode.SUBTRACT)
        extrude(sk.sketch, amount=u760_t)
    u760_mock = u760_bp.part
    u760_mock.label = "U760_Platform_Mock"

    # U-651 Stage Mock: 95 x 71 x 14 mm, Z = 10.0 .. 24.0 mm
    with BuildPart() as u651_bp:
        with BuildSketch(Plane.XY.offset(al_h)) as sk:
            RectangleRounded(u651_x, u651_y, radius=4.0)
            Circle(radius=u651_bore / 2.0, mode=Mode.SUBTRACT)
        extrude(sk.sketch, amount=u651_h)
    u651_mock = u651_bp.part
    u651_mock.label = "U651_Stage_Mock"

    adapter_copy = Part(adapter_al.wrapped)
    adapter_copy.label = "Adapter_Aluminum"

    return Compound(
        label="U760_Adapter_U651_Assembly",
        children=[u760_mock, adapter_copy, u651_mock],
    )


def compute_metrics(part: Part, params: dict[str, Any], variant_name: str) -> dict[str, Any]:
    """Extract volume, bounding box, center of mass, validity, and material masses."""
    vol_mm3 = float(part.volume)
    bb = part.bounding_box()
    com = part.center()
    is_valid = bool(part.is_valid)

    mass_by_mat: dict[str, float] = {}
    for mat_key, mat_info in params["materials"].items():
        density = float(mat_info["density_kg_m3"])
        # volume in m^3 = vol_mm3 * 1e-9
        mass_by_mat[mat_key] = round(vol_mm3 * 1e-9 * density, 6)

    return {
        "variant": variant_name,
        "label": params["variants"][variant_name]["label"],
        "is_valid": is_valid,
        "volume_mm3": round(vol_mm3, 3),
        "bounding_box_mm": {
            "min": [round(float(bb.min.X), 4), round(float(bb.min.Y), 4), round(float(bb.min.Z), 4)],
            "max": [round(float(bb.max.X), 4), round(float(bb.max.Y), 4), round(float(bb.max.Z), 4)],
            "size": [round(float(bb.size.X), 4), round(float(bb.size.Y), 4), round(float(bb.size.Z), 4)],
        },
        "center_of_mass_mm": [
            round(float(com.X), 4),
            round(float(com.Y), 4),
            round(float(com.Z), 4),
        ],
        "mass_kg_by_material": mass_by_mat,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PI U-760 to U-651 adapter CAD models.")
    parser.add_argument("--params", type=Path, default=PARAMS_PATH, help="Path to params.json")
    parser.add_argument("--outdir", type=Path, default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    params = load_params(args.params)
    args.outdir.mkdir(parents=True, exist_ok=True)

    metrics: dict[str, Any] = {}
    built_parts: dict[str, Part] = {}

    for variant_name in ("aluminum", "pla_prototype"):
        print(f"Building variant: {variant_name} ...")
        part = build_adapter(params, variant_name)
        built_parts[variant_name] = part

        step_path = args.outdir / f"u760_to_u651_adapter_{variant_name}.step"
        stl_path = args.outdir / f"u760_to_u651_adapter_{variant_name}.stl"

        step_path.unlink(missing_ok=True)
        stl_path.unlink(missing_ok=True)
        export_step(part, str(step_path))
        export_stl(part, str(stl_path))

        m = compute_metrics(part, params, variant_name)
        metrics[variant_name] = m
        print(
            f"  -> valid={m['is_valid']}, volume={m['volume_mm3']:.2f} mm^3, "
            f"bbox={m['bounding_box_mm']['size']} mm, CoG={m['center_of_mass_mm']} mm"
        )
        print(f"  -> exported {step_path.name} and {stl_path.name}")

    print("Building stacked assembly (U-760 mock + Aluminum adapter + U-651 mock) ...")
    assembly = build_assembly(params, built_parts["aluminum"])
    asm_path = args.outdir / "assembly_u760_adapter_u651.step"
    asm_path.unlink(missing_ok=True)
    export_step(assembly, str(asm_path))
    print(f"  -> exported {asm_path.name}")

    metrics_path = args.outdir / "geometry_metrics.json"
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"  -> exported {metrics_path.name}")


if __name__ == "__main__":
    main()
