# Automated CAD Verification Report: PI U-760 to U-651 Adapter

- **Overall Status:** **FAIL** (12/15 checks passed)
- **Generated:** `2026-11-20 21:12:33 UTC`
- **Parameter Source:** `params.json` (`reference_status`: `datasheet_baseline_placeholders`)
- **Verified Artifacts:**
  - `output/u760_to_u651_adapter_aluminum.step`
  - `output/u760_to_u651_adapter_pla_prototype.step`
  - `output/assembly_u760_adapter_u651.step`

---

## Verification Summary

| Status | Category | Check | Measured Value | Requirement |
| :---: | :--- | :--- | :--- | :--- |
| PASS | a. Solid Validity | Adapter (aluminum) solid validity & volume | solids=1, valid=True, vol=75042.50 mm³ | >= 1 valid solid, volume > 0 mm³ |
| PASS | a. Solid Validity | Adapter (pla_prototype) solid validity & volume | solids=1, valid=True, vol=96053.63 mm³ | >= 1 valid solid, volume > 0 mm³ |
| PASS | b. Bounding Box Accuracy | Adapter (aluminum) X × Y × Z envelope | 128.000 × 100.000 × 10.000 mm (Z: 0.000..10.000 mm; max err 0.0000 mm) | 128.00 × 100.00 × 10.00 mm (±0.05 mm) |
| PASS | b. Bounding Box Accuracy | Adapter (pla_prototype) X × Y × Z envelope | 128.000 × 100.000 × 12.000 mm (Z: 0.000..12.000 mm; max err 0.0000 mm) | 128.00 × 100.00 × 12.00 mm (±0.05 mm) |
| **FAIL** | c. Clear Optical Aperture | Ø36.0 mm beam path through Adapter (aluminum) | 3562.566069 mm³ | 0.0 mm³ (Ø36.0 mm, Z = -25..+35 mm) |
| **FAIL** | c. Clear Optical Aperture | Ø36.0 mm beam path through Adapter (pla_prototype) | 4580.442089 mm³ | 0.0 mm³ (Ø36.0 mm, Z = -25..+35 mm) |
| **FAIL** | c. Clear Optical Aperture | Ø36.0 mm beam path through Full Assembly (U-760 + Adapter + U-651) | 3562.566069 mm³ | 0.0 mm³ (Ø36.0 mm, Z = -25..+35 mm) |
| PASS | d. Assembly Interference | Assembly component solid count | 3 solids | >= 3 solids (U-760, Adapter, U-651) |
| PASS | d. Assembly Interference | U-760 Stage (Mock) vs. Adapter (Aluminum) | 0.000000 mm³ | 0.0 mm³ (zero collision) |
| PASS | d. Assembly Interference | U-760 Stage (Mock) vs. U-651 Stage (Mock) | 0.000000 mm³ | 0.0 mm³ (zero collision) |
| PASS | d. Assembly Interference | Adapter (Aluminum) vs. U-651 Stage (Mock) | 0.000000 mm³ | 0.0 mm³ (zero collision) |
| PASS | e. Fastener Head Clearance | U-760 top-down M4 SHCS heads (aluminum) | head top Z = 8.90 mm (deck 9.50 mm, recess 0.60 mm), max interference = 0.000000 mm³ | Z_top <= 9.50 mm & 0.0 mm³ interference (4× Ø7.0×4.0 mm) |
| PASS | e. Fastener Head Clearance | U-651 bottom-up M4 SHCS heads (aluminum) | head bottom Z = 0.60 mm (datum 0.00 mm, recess 0.60 mm), max interference = 0.000000 mm³ | Z_bottom >= 0.00 mm & 0.0 mm³ interference (4× Ø7.0×4.0 mm) |
| PASS | e. Fastener Head Clearance | U-760 top-down M4 SHCS heads (pla_prototype) | head top Z = 10.90 mm (deck 11.50 mm, recess 0.60 mm), max interference = 0.000000 mm³ | Z_top <= 11.50 mm & 0.0 mm³ interference (4× Ø7.0×4.0 mm) |
| PASS | e. Fastener Head Clearance | U-651 bottom-up M4 SHCS heads (pla_prototype) | head bottom Z = 0.60 mm (datum 0.00 mm, recess 0.60 mm), max interference = 0.000000 mm³ | Z_bottom >= 0.00 mm & 0.0 mm³ interference (4× Ø7.0×4.0 mm) |

---

## Assembly Solid Breakdown

| Component | Z Range (mm) | Volume (mm³) |
| :--- | :---: | :---: |
| U-760 Stage (Mock) | `-18.00` to `+0.00` | `265846.94` |
| Adapter (Aluminum) | `+0.00` to `+10.00` | `75042.50` |
| U-651 Stage (Mock) | `+10.00` to `+24.00` | `79987.45` |

---

## Re-Verification Workflow (Official PI STEP Files)

The current verification ran against `params.json` (`reference_status`: `datasheet_baseline_placeholders`). Once official Physik Instrumente (PI) mechanical STEP files and PDF drawings are available:

1. Place the official PI files into `reference/`:
   - `reference/U-760.step` (and/or `U-760_datasheet.pdf`)
   - `reference/U-651.step` (and/or `U-651_MP136E.pdf`)
2. Inspect the STEP geometry and extract exact hole coordinates:
   ```powershell
   .venv\Scripts\python.exe scripts\inspect_reference_step.py
   ```
3. Update `u760_interface`, `u651_interface`, and `_metadata.reference_status` in `params.json`.
4. Regenerate all CAD exports, views, and re-run automated verification:
   ```powershell
   .venv\Scripts\python.exe scripts\generate_adapter.py
   .venv\Scripts\python.exe scripts\verify_assembly.py
   .venv\Scripts\python.exe scripts\render_views.py
   ```
5. Confirm `docs/verification_report.md` reports **PASS** on all checks (especially clear optical aperture, zero pairwise solid interference against the real PI STEP models, and recessed M4 SHCS head clearance) before releasing to CNC machining.
