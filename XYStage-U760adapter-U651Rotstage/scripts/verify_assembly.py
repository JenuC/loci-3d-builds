"""Automated geometric verification for the PI U-760 to U-651 Stage Adapter.

Checks performed:
  a. Solid validity (is_valid and positive volume for aluminum & PLA variants)
  b. Bounding box accuracy (X, Y, Z match params.json within 0.05 mm)
  c. Clear optical aperture check (Ø36 mm cylinder from Z=-25 to Z=+35 mm has 0.0 mm^3 intersection)
  d. Assembly interference check (pairwise solid intersections in full assembly == 0.0 mm^3)
  e. Fastener head clearance check (M4 SHCS Ø7.0 x 4.0 mm heads recessed in U-760 & U-651 counterbores)

Writes a structured Markdown verification report to docs/verification_report.md.
Exits with code 0 if all checks pass, 1 if any check fails.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from build123d import Align, Cylinder, Location, Shape, Solid, import_step

REPO_ROOT = Path(__file__).resolve().parent.parent
PARAMS_PATH = REPO_ROOT / "params.json"
OUTPUT_DIR = REPO_ROOT / "output"
REPORT_PATH = REPO_ROOT / "docs" / "verification_report.md"

BBOX_TOL_MM = 0.05
VOL_TOL_MM3 = 1e-4  # Numerical tolerance for 3D boolean intersection noise (mm^3)

# ISO 4762 / DIN 912 M4 Socket Head Cap Screw nominal head envelope
M4_HEAD_DIA_MM = 7.0
M4_HEAD_HEIGHT_MM = 4.0
SEAT_CLEARANCE_EPS_MM = 0.02  # Axial offset off seat face to avoid coplanar tangency


@dataclass
class CheckResult:
    category: str
    name: str
    passed: bool
    measured: str
    requirement: str
    details: str = ""


def _is_shape_valid(shape: Shape) -> bool:
    attr = getattr(shape, "is_valid", False)
    return bool(attr() if callable(attr) else attr)


def _extract_solids(shape: Shape | None) -> list[Solid]:
    if shape is None:
        return []
    if isinstance(shape, Solid):
        return [shape]
    if hasattr(shape, "solids"):
        return list(shape.solids())
    if isinstance(shape, Iterable):
        solids: list[Solid] = []
        for item in shape:
            solids.extend(_extract_solids(item))
        return solids
    return []


def _bboxes_disjoint(shape_a: Shape, shape_b: Shape, margin: float = 1e-5) -> bool:
    bb_a = shape_a.bounding_box()
    bb_b = shape_b.bounding_box()
    return (
        bb_a.max.X < bb_b.min.X - margin
        or bb_b.max.X < bb_a.min.X - margin
        or bb_a.max.Y < bb_b.min.Y - margin
        or bb_b.max.Y < bb_a.min.Y - margin
        or bb_a.max.Z < bb_b.min.Z - margin
        or bb_b.max.Z < bb_a.min.Z - margin
    )


def intersection_volume(shape_a: Shape, shape_b: Shape) -> float:
    """Return 3D boolean intersection volume (mm^3) between two shapes.

    Filters the intersection result strictly to 3D solids so tangent/coplanar
    face contact (which has zero 3D interference volume) evaluates to 0.0 mm^3.
    """
    if _bboxes_disjoint(shape_a, shape_b):
        return 0.0
    common = shape_a.intersect(shape_b)
    solids = _extract_solids(common)
    return float(sum(abs(s.volume) for s in solids))


def label_assembly_solids(solids: list[Solid], al_height_mm: float) -> list[tuple[str, Solid]]:
    """Assign human-readable labels to solids in the stacked assembly by Z-centroid."""
    indexed = []
    for idx, solid in enumerate(solids):
        bb = solid.bounding_box()
        z_mid = 0.5 * (bb.min.Z + bb.max.Z)
        indexed.append((z_mid, bb, idx, solid))
    indexed.sort(key=lambda item: item[0])

    labeled: list[tuple[str, Solid]] = []
    counts = {"U-760": 0, "Adapter": 0, "U-651": 0}
    for z_mid, bb, _idx, solid in indexed:
        if z_mid < 0.0:
            counts["U-760"] += 1
            suffix = f" #{counts['U-760']}" if counts["U-760"] > 1 else ""
            name = f"U-760 Stage (Mock){suffix}"
        elif z_mid <= al_height_mm + 0.5:
            counts["Adapter"] += 1
            suffix = f" #{counts['Adapter']}" if counts["Adapter"] > 1 else ""
            name = f"Adapter (Aluminum){suffix}"
        else:
            counts["U-651"] += 1
            suffix = f" #{counts['U-651']}" if counts["U-651"] > 1 else ""
            name = f"U-651 Stage (Mock){suffix}"
        labeled.append((name, solid))
    return labeled


def run_verification() -> tuple[list[CheckResult], dict]:
    if not PARAMS_PATH.exists():
        raise FileNotFoundError(f"Missing parameters file: {PARAMS_PATH}")

    with PARAMS_PATH.open("r", encoding="utf-8") as fh:
        params = json.load(fh)

    step_paths = {
        "aluminum": OUTPUT_DIR / "u760_to_u651_adapter_aluminum.step",
        "pla_prototype": OUTPUT_DIR / "u760_to_u651_adapter_pla_prototype.step",
        "assembly": OUTPUT_DIR / "assembly_u760_adapter_u651.step",
    }

    missing = [str(p) for p in step_paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required STEP output file(s). Run scripts/generate_adapter.py first:\n  - "
            + "\n  - ".join(missing)
        )

    shapes = {key: import_step(str(path)) for key, path in step_paths.items()}
    results: list[CheckResult] = []
    summary_meta: dict = {
        "reference_status": params.get("_metadata", {}).get("reference_status", "unknown"),
        "variants": {},
        "assembly_solids": [],
    }

    # ------------------------------------------------------------------
    # (a) Solid validity & positive volume
    # ------------------------------------------------------------------
    for var_key in ("aluminum", "pla_prototype"):
        shape = shapes[var_key]
        solids = _extract_solids(shape)
        valid_flags = [_is_shape_valid(s) for s in solids]
        total_vol = float(sum(abs(s.volume) for s in solids))
        passed = len(solids) >= 1 and all(valid_flags) and total_vol > 0.0
        summary_meta["variants"][var_key] = {
            "solid_count": len(solids),
            "volume_mm3": total_vol,
        }
        results.append(
            CheckResult(
                category="a. Solid Validity",
                name=f"Adapter ({var_key}) solid validity & volume",
                passed=passed,
                measured=f"solids={len(solids)}, valid={all(valid_flags) if solids else False}, vol={total_vol:.2f} mm³",
                requirement=">= 1 valid solid, volume > 0 mm³",
            )
        )

    # ------------------------------------------------------------------
    # (b) Bounding box accuracy (within 0.05 mm of params.json)
    # ------------------------------------------------------------------
    expected_x = float(params["u760_interface"]["adapter_outer_x_mm"])
    expected_y = float(params["u760_interface"]["adapter_outer_y_mm"])

    for var_key in ("aluminum", "pla_prototype"):
        shape = shapes[var_key]
        expected_z = float(params["variants"][var_key]["total_height_mm"])
        bb = shape.bounding_box()
        dx = abs(bb.size.X - expected_x)
        dy = abs(bb.size.Y - expected_y)
        dz = abs(bb.size.Z - expected_z)
        max_err = max(dx, dy, dz)
        passed = max_err <= BBOX_TOL_MM
        summary_meta["variants"][var_key]["bbox"] = (
            float(bb.size.X),
            float(bb.size.Y),
            float(bb.size.Z),
            float(bb.min.Z),
            float(bb.max.Z),
        )
        results.append(
            CheckResult(
                category="b. Bounding Box Accuracy",
                name=f"Adapter ({var_key}) X × Y × Z envelope",
                passed=passed,
                measured=(
                    f"{bb.size.X:.3f} × {bb.size.Y:.3f} × {bb.size.Z:.3f} mm "
                    f"(Z: {bb.min.Z:.3f}..{bb.max.Z:.3f} mm; max err {max_err:.4f} mm)"
                ),
                requirement=f"{expected_x:.2f} × {expected_y:.2f} × {expected_z:.2f} mm (±{BBOX_TOL_MM:.2f} mm)",
            )
        )

    # ------------------------------------------------------------------
    # (c) Clear optical aperture check (Ø36.0 mm, Z = -25..+35 mm)
    # ------------------------------------------------------------------
    ap_dia = float(params["optical"]["u651_clear_aperture_dia_mm"])
    z_min_ap = -25.0
    z_max_ap = 35.0
    aperture_cyl = Cylinder(
        radius=ap_dia / 2.0,
        height=z_max_ap - z_min_ap,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    ).move(Location((0.0, 0.0, z_min_ap)))

    for target_key, label in (
        ("aluminum", "Adapter (aluminum)"),
        ("pla_prototype", "Adapter (pla_prototype)"),
        ("assembly", "Full Assembly (U-760 + Adapter + U-651)"),
    ):
        vol = intersection_volume(shapes[target_key], aperture_cyl)
        passed = vol <= VOL_TOL_MM3
        results.append(
            CheckResult(
                category="c. Clear Optical Aperture",
                name=f"Ø{ap_dia:.1f} mm beam path through {label}",
                passed=passed,
                measured=f"{vol:.6f} mm³",
                requirement=f"0.0 mm³ (Ø{ap_dia:.1f} mm, Z = {z_min_ap:+.0f}..{z_max_ap:+.0f} mm)",
            )
        )

    # ------------------------------------------------------------------
    # (d) Assembly pairwise interference check
    # ------------------------------------------------------------------
    al_height = float(params["variants"]["aluminum"]["total_height_mm"])
    asm_solids = _extract_solids(shapes["assembly"])
    labeled_solids = label_assembly_solids(asm_solids, al_height)

    for name, solid in labeled_solids:
        bb = solid.bounding_box()
        summary_meta["assembly_solids"].append(
            {
                "name": name,
                "volume_mm3": float(abs(solid.volume)),
                "z_range": (float(bb.min.Z), float(bb.max.Z)),
            }
        )

    results.append(
        CheckResult(
            category="d. Assembly Interference",
            name="Assembly component solid count",
            passed=len(labeled_solids) >= 3,
            measured=f"{len(labeled_solids)} solids",
            requirement=">= 3 solids (U-760, Adapter, U-651)",
        )
    )

    for i in range(len(labeled_solids)):
        for j in range(i + 1, len(labeled_solids)):
            name_i, solid_i = labeled_solids[i]
            name_j, solid_j = labeled_solids[j]
            vol = intersection_volume(solid_i, solid_j)
            passed = vol <= VOL_TOL_MM3
            results.append(
                CheckResult(
                    category="d. Assembly Interference",
                    name=f"{name_i} vs. {name_j}",
                    passed=passed,
                    measured=f"{vol:.6f} mm³",
                    requirement="0.0 mm³ (zero collision)",
                )
            )

    # ------------------------------------------------------------------
    # (e) Fastener head clearance check (M4 SHCS Ø7.0 x 4.0 mm)
    # ------------------------------------------------------------------
    u760_holes = params["u760_interface"]["mounting_holes_xy_mm"]
    u760_cb_depth = float(params["u760_interface"]["counterbore_depth_mm"])
    u651_holes = params["u651_interface"]["mounting_holes_xy_mm"]
    u651_cb_depth = float(params["u651_interface"]["counterbore_depth_mm"])
    pad_proud = float(params["u651_interface"]["mounting_pad_proud_height_mm"])

    for var_key in ("aluminum", "pla_prototype"):
        shape = shapes[var_key]
        total_h = float(params["variants"][var_key]["total_height_mm"])
        top_deck_z = total_h - pad_proud

        # 1. U-760 top-down counterbores
        u760_seat_z = top_deck_z - u760_cb_depth
        u760_head_top_z = u760_seat_z + M4_HEAD_HEIGHT_MM
        u760_max_vol = 0.0
        for hx, hy in u760_holes:
            head_cyl = Cylinder(
                radius=M4_HEAD_DIA_MM / 2.0,
                height=M4_HEAD_HEIGHT_MM - SEAT_CLEARANCE_EPS_MM,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            ).move(Location((float(hx), float(hy), u760_seat_z + SEAT_CLEARANCE_EPS_MM)))
            u760_max_vol = max(u760_max_vol, intersection_volume(shape, head_cyl))

        u760_passed = (u760_head_top_z <= top_deck_z + 1e-6) and (u760_max_vol <= VOL_TOL_MM3)
        results.append(
            CheckResult(
                category="e. Fastener Head Clearance",
                name=f"U-760 top-down M4 SHCS heads ({var_key})",
                passed=u760_passed,
                measured=(
                    f"head top Z = {u760_head_top_z:.2f} mm (deck {top_deck_z:.2f} mm, "
                    f"recess {top_deck_z - u760_head_top_z:.2f} mm), "
                    f"max interference = {u760_max_vol:.6f} mm³"
                ),
                requirement=f"Z_top <= {top_deck_z:.2f} mm & 0.0 mm³ interference (4× Ø{M4_HEAD_DIA_MM:.1f}×{M4_HEAD_HEIGHT_MM:.1f} mm)",
            )
        )

        # 2. U-651 bottom-up counterbores
        u651_seat_z = u651_cb_depth
        u651_head_bot_z = u651_seat_z - M4_HEAD_HEIGHT_MM
        u651_max_vol = 0.0
        for hx, hy in u651_holes:
            head_cyl = Cylinder(
                radius=M4_HEAD_DIA_MM / 2.0,
                height=M4_HEAD_HEIGHT_MM - SEAT_CLEARANCE_EPS_MM,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            ).move(Location((float(hx), float(hy), u651_head_bot_z)))
            u651_max_vol = max(u651_max_vol, intersection_volume(shape, head_cyl))

        u651_passed = (u651_head_bot_z >= -1e-6) and (u651_max_vol <= VOL_TOL_MM3)
        results.append(
            CheckResult(
                category="e. Fastener Head Clearance",
                name=f"U-651 bottom-up M4 SHCS heads ({var_key})",
                passed=u651_passed,
                measured=(
                    f"head bottom Z = {u651_head_bot_z:.2f} mm (datum 0.00 mm, "
                    f"recess {u651_head_bot_z:.2f} mm), "
                    f"max interference = {u651_max_vol:.6f} mm³"
                ),
                requirement=f"Z_bottom >= 0.00 mm & 0.0 mm³ interference (4× Ø{M4_HEAD_DIA_MM:.1f}×{M4_HEAD_HEIGHT_MM:.1f} mm)",
            )
        )

    return results, summary_meta


def write_report(results: list[CheckResult], meta: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    overall = "PASS" if passed_count == total_count else "FAIL"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: list[str] = [
        "# Automated CAD Verification Report: PI U-760 to U-651 Adapter",
        "",
        f"- **Overall Status:** **{overall}** ({passed_count}/{total_count} checks passed)",
        f"- **Generated:** `{timestamp}`",
        f"- **Parameter Source:** `params.json` (`reference_status`: `{meta['reference_status']}`)",
        "- **Verified Artifacts:**",
        "  - `output/u760_to_u651_adapter_aluminum.step`",
        "  - `output/u760_to_u651_adapter_pla_prototype.step`",
        "  - `output/assembly_u760_adapter_u651.step`",
        "",
        "---",
        "",
        "## Verification Summary",
        "",
        "| Status | Category | Check | Measured Value | Requirement |",
        "| :---: | :--- | :--- | :--- | :--- |",
    ]

    for r in results:
        badge = "PASS" if r.passed else "**FAIL**"
        lines.append(
            f"| {badge} | {r.category} | {r.name} | {r.measured} | {r.requirement} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Assembly Solid Breakdown",
            "",
            "| Component | Z Range (mm) | Volume (mm³) |",
            "| :--- | :---: | :---: |",
        ]
    )

    for comp in meta["assembly_solids"]:
        z0, z1 = comp["z_range"]
        lines.append(
            f"| {comp['name']} | `{z0:+.2f}` to `{z1:+.2f}` | `{comp['volume_mm3']:.2f}` |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Re-Verification Workflow (Official PI STEP Files)",
            "",
            "The current verification ran against `params.json` (`reference_status`: "
            f"`{meta['reference_status']}`). Once official Physik Instrumente (PI) mechanical "
            "STEP files and PDF drawings are available:",
            "",
            "1. Place the official PI files into `reference/`:",
            "   - `reference/U-760.step` (and/or `U-760_datasheet.pdf`)",
            "   - `reference/U-651.step` (and/or `U-651_MP136E.pdf`)",
            "2. Inspect the STEP geometry and extract exact hole coordinates:",
            "   ```powershell",
            "   .venv\\Scripts\\python.exe scripts\\inspect_reference_step.py",
            "   ```",
            "3. Update `u760_interface`, `u651_interface`, and `_metadata.reference_status` in `params.json`.",
            "4. Regenerate all CAD exports, views, and re-run automated verification:",
            "   ```powershell",
            "   .venv\\Scripts\\python.exe scripts\\generate_adapter.py",
            "   .venv\\Scripts\\python.exe scripts\\verify_assembly.py",
            "   .venv\\Scripts\\python.exe scripts\\render_views.py",
            "   ```",
            "5. Confirm `docs/verification_report.md` reports **PASS** on all checks (especially "
            "clear optical aperture, zero pairwise solid interference against the real PI STEP "
            "models, and recessed M4 SHCS head clearance) before releasing to CNC machining.",
            "",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    try:
        results, meta = run_verification()
    except Exception as exc:
        print(f"[ERROR] Verification aborted: {exc}", file=sys.stderr)
        return 1

    write_report(results, meta)

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    for r in results:
        tag = "PASS" if r.passed else "FAIL"
        print(f"[{tag}] {r.category} | {r.name}: {r.measured}")

    print(f"\nVerification complete: {passed_count}/{total_count} passed.")
    print(f"Report written to: {REPORT_PATH}")
    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
