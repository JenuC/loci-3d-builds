# Manufacturing & Assembly Guide: PI U-760 to U-651 Stage Adapter

This guide covers CNC machining specifications, GD&T tolerances, surface treatment, fastener selection, assembly torque sequences, 3D-printed fit-check guidelines, and the update workflow once official Physik Instrumente (PI) STEP/PDF drawings are added.

---

## 1. CNC Machining & GD&T Specification (Production Aluminum Variant)

- **CAD Deliverable:** `output/u760_to_u651_adapter_aluminum.step`
- **Overall Envelope:** `128.0 × 100.0 × 10.0 mm` (`9.5 mm` main deck + `0.5 mm` raised U-651 mounting pads)
- **Clear Optical Aperture:** `Ø38.0 mm` through-bore with `2.0 mm × 45°` bottom objective chamfer (clears the U-651 `Ø36.0 mm` optical aperture with `1.0 mm` radial margin)

### 1.1 Recommended Alloys

| Alloy | Best For | Notes |
| :--- | :--- | :--- |
| **Al 6061-T6** *(Recommended baseline)* | General CNC machining, matte black anodizing | High specific stiffness, clean anodizing cosmetics, readily available. Stress-relieve or rough-then-finish to hold flatness. |
| **Al MIC-6 Cast Plate** *(Best flatness stability)* | Tightest $\le 10\,\mu\text{m}$ flatness stability | Stress-relieved cast plate resists warping after pocketing. Note: black anodizing on MIC-6 produces a darker grey/charcoal finish rather than deep jet black. |

### 1.2 Critical GD&T Callouts

Establish **Datum A** on the bottom U-760 mating face (`Z = 0.0 mm`) and **Datum B** on the central `Ø38.0 mm` optical bore (or the two `Ø3.0 mm` dowel pin holes):

| Feature | Geometric Tolerance | Requirement / Rationale |
| :--- | :--- | :--- |
| **4× Raised U-651 Mounting Pads** (`Z = 10.0 mm`, `Ø16.0 mm`) | **Flatness $\le 0.010\text{ mm}$ ($10\,\mu\text{m}$)** *(coplanar across all 4 pads)* | Mandatory per PI MP136E U-651 manual to prevent bearing distortion and premature wear. **Fly-cut or surface-grind all 4 pads in a single final setup.** |
| **4× Raised U-651 Mounting Pads** vs. **Datum A** (`Z = 0.0 mm`) | **Parallelism $\le 0.015\text{ mm}$ ($15\,\mu\text{m}$)** | Keeps the U-651 rotation axis orthogonal to the U-760 XY translation plane and optical axis. |
| **Bottom Mounting Face (Datum A)** | **Flatness $\le 0.015\text{ mm}$ ($15\,\mu\text{m}$)** | Prevents rocking and micro-slip on the U-760 moving platform under ultrasonic XY acceleration. |
| **2× Dowel Pin Holes** (`(±54.0, 0.0)`) | **`Ø3.0 mm H7`** (`+0.010 / -0.000 mm`), reamed | Precision repeatable alignment to U-760 (`h6` dowel pins). |
| **4× U-760 & 4× U-651 Clearance Holes** | `Ø4.5 ± 0.1 mm`, counterbore `Ø8.0 ± 0.1 mm × 4.6 ± 0.1 mm` deep | Ensures M4 SHCS heads (`Ø7.0 × 4.0 mm`) sit recessed by `0.6 mm` below both top deck (`Z = 9.5 mm`) and bottom datum (`Z = 0.0 mm`). |
| **Internal Pocket Fillets** | `R3.0 mm` minimum | Machinable with standard `Ø6.0 mm` endmill; avoids sharp stress risers in stiffening ribs. |
| **General Machined Tolerances** | ISO 2768-mK (`±0.1 mm` linear) | Applies to outer profile, `-X` cable relief notch (`14.0 × 4.0 mm`), and lightweighting pockets. |

### 1.3 Surface Finish & Optical Stray-Light Control

- **Coating:** **Matte Black Anodizing per MIL-A-8625 Type II, Class 2** (fine glass-bead blast prior to anodizing to achieve a low-gloss, non-reflective finish that eliminates stray fluorescence/laser reflections on the inverted microscope).
- **Critical Masking / Post-Anodize Notes:**
  1. **PE Protective Earth Ground Boss** (`(-47.5, -18.0)`): **Mask** a `Ø10 mm` spot around the M4 PE ground hole (or apply clear conductive chromate / Alodine MIL-DTL-5541 Type II) so the PE lug achieves a low-resistance (`< 0.1 Ω`) electrical bond to the aluminum body.
  2. **U-651 Pads (`Z = 10.0 mm`) & Datum A (`Z = 0.0 mm`):** Standard Type II anodizing adds `~5–12 µm` uniformly. Either mask the 4 raised pads before anodizing or perform a light precision lap/skim after anodizing, then verify coplanarity $\le 10\,\mu\text{m}$ on a granite surface plate with a `1 µm` dial test indicator.
  3. **Dowel Pin Holes (`Ø3.0 H7`):** Plug/mask before anodizing or ream post-anodize to maintain H7 slip/locating fit.

---

## 2. Fastener BOM & Assembly Torque Sequence

### 2.1 Bill of Materials (Fasteners & Hardware)

| Qty | Description | Spec / Standard | Location | Target Torque |
| :---: | :--- | :--- | :--- | :---: |
| **4** | **M4 × 16 mm** (or **M4 × 18 mm**) Socket Head Cap Screw | ISO 4762 / DIN 912, Grade 12.9 or A2-70 stainless | Bottom-up through adapter into U-651 base (`±37.5, ±27.5`) | **2.1 Nm** *(PI MP136E)* |
| **4** | **M4 × 10 mm** (or **M4 × 12 mm**) Socket Head Cap Screw | ISO 4762 / DIN 912, Grade 12.9 or A2-70 stainless | Top-down through adapter into U-760 platform (`±54.0, ±40.0`) | **2.1 Nm** *(verify vs. U-760 manual)* |
| **2** | **Ø3.0 mm × 8 mm** Precision Dowel Pin | DIN 6325 / ISO 2338, tolerance `h6`, hardened steel | Adapter-to-U-760 alignment (`±54.0, 0.0`) | Slip / light press fit |
| **1** | **M4 × 6 mm** Pan/SHCS + External-Tooth Lock Washer + Ring Terminal | M4 PE Ground Lug | PE ground hole (`-47.5, -18.0`) | **1.2 – 1.5 Nm** |

> **Screw Length Verification Warning:**
> - For **U-651 bottom-up screws**: the adapter seat thickness is `10.0 - 4.6 = 5.4 mm`. An `M4 × 16 mm` screw provides `10.6 mm` of thread engagement into the U-651 base (`M4 × 18 mm` provides `12.6 mm`). Verify the exact maximum permissible thread depth in the official U-651 drawing (`reference/U-651_MP136E.pdf`) before tightening so screws never bottom out against internal stage components.
> - For **U-760 top-down screws**: the adapter seat thickness is `9.5 - 4.6 = 4.9 mm`. An `M4 × 10 mm` screw provides `5.1 mm` of engagement into the U-760 platform (`M4 × 12 mm` provides `7.1 mm`). Verify against the official U-760 manual.

### 2.2 Step-by-Step Assembly Sequence

> **Important:** Because the U-651 mounting screws are installed **bottom-up** through the adapter, you **must** bolt the U-651 onto the adapter *before* mounting the adapter onto the U-760 XY stage.

1. **Clean & Inspect Mating Surfaces:** Wipe the U-651 base, adapter pads, Datum A, and U-760 platform with isopropyl alcohol (IPA) and lint-free wipes. Confirm zero burrs or debris on the 4 raised pads.
2. **Mount U-651 to Adapter (Bottom-Up):**
   - Place the U-651 gently onto the 4 raised mounting pads (`Z = 10.0 mm`) with the U-651 cable exiting toward the **`-X` cable relief notch**.
   - Insert the 4× `M4 × 16` (or `M4 × 18`) SHCS from the underside (`-Z`) of the adapter into the U-651 base.
   - Snug all 4 bolts lightly by hand, then torque in a **star/cross pattern** in two passes (`1.0 Nm`, then final **`2.1 Nm`**) using a calibrated torque driver.
3. **Install Dowel Pins on U-760:** Seat the 2× `Ø3.0 mm h6` dowel pins into the U-760 locating holes (if equipped on your U-760 revision).
4. **Mount Adapter + U-651 Sub-Assembly to U-760 (Top-Down):**
   - Lower the sub-assembly vertically onto the U-760 platform, aligning the `Ø3.0 H7` dowel holes.
   - Insert the 4× `M4` SHCS top-down into the outer counterbores (`±54.0, ±40.0`).
   - Torque in a **star/cross pattern** in two passes to **`2.1 Nm`** (verify against U-760 manual).
   - Confirm all 4 screw heads sit recessed below the `Z = 9.5 mm` deck (zero interference with the U-651 or sample holders).
5. **Cable Strain Relief & PE Grounding:**
   - Route the U-651 motor/encoder cable cleanly through the `-X` relief notch (`14.0 × 4.0 mm`) and secure with a gentle service loop so XY stage motion does not tug on the U-651 connector.
   - Attach the M4 PE protective earth ground ring lug + external-tooth lock washer at `(-47.5, -18.0)` and torque to **`1.2 – 1.5 Nm`**. Verify electrical continuity to chassis ground (`< 0.1 Ω`).
6. **Optical & Travel Dry-Run:** Slowly jog the U-760 across its full `25 × 25 mm` travel and rotate the U-651 through `360°` while checking objective clearance through the `Ø38 mm` aperture and cable clearance.

---

## 3. 3D-Printing Guide (PLA Fit-Check Prototype)

- **CAD Deliverable:** `output/u760_to_u651_adapter_pla_prototype.stl`
- **Prototype Dimensions:** `128.0 × 100.0 × 12.0 mm` (includes `+2.0 mm` extra height, thicker `4.5 mm` ribs, and `+0.25 mm` FDM hole clearance adder)

> [!WARNING]
> **FIT-CHECK & CABLE-ROUTING PROTOTYPE ONLY — DO NOT USE FOR PRODUCTION RUNS.**
> FDM-printed PLA has ~22× lower elastic modulus than aluminum (~3× lower first natural frequency $f_1$), exhibits severe viscoelastic creep under M4 bolt preload (causing fasteners to loosen and excite resonance), and cannot achieve the U-651's mandatory $\le 10\,\mu\text{m}$ mounting flatness specification. Use this print strictly to verify hole alignment, objective clearance, and cable routing on the microscope before ordering CNC aluminum.

### 3.1 Recommended Slicer Settings

| Parameter | Recommended Setting | Rationale |
| :--- | :--- | :--- |
| **Material** | PLA or PLA+ (matte black or grey) | Lowest warping and best dimensional accuracy for rapid fit-checks. |
| **Orientation** | **Bottom face (`Z = 0`) flat on build plate** *(preferred)* — or top face down on glass/PEI if prioritizing top pad flatness | Bottom-down keeps the 4 raised U-651 pads clean without support scars; supports are only needed under the underside pockets if bridging exceeds ~15 mm. |
| **Layer Height** | `0.16 – 0.20 mm` (0.4 mm nozzle) | Good balance of counterbore Z-step accuracy and ~2–3 hour print time. |
| **Perimeters (Walls)** | **5+ perimeters** (`>= 2.0 mm` wall thickness) | Ensures solid plastic around all 8 counterbored M4 holes and dowel bores. |
| **Infill** | **40% – 100% Gyroid** | High isotropic stiffness without pillowing; 40–60% is ample for fit-check. |
| **Top / Bottom Layers** | 5–6 solid layers | Prevents deflection under light hand-tightened bolts. |
| **Bed Adhesion** | 5 mm outer brim (optional) | Prevents corner lift on the `128 × 100 mm` footprint. |
| **Supports** | Touching buildplate only (tree/snug supports for counterbores & deep underside pockets) | Easy removal with clean bolt seats. |

### 3.2 Fit-Check Checklist (Before CNC Release)

1. Remove any support remnants from the 4 bottom-up U-651 counterbores and 4 top-down U-760 counterbores.
2. Dry-fit M4 SHCS screws through all 8 holes (do **not** torque to `2.1 Nm` on PLA — hand-snug only to `~0.4 Nm` to avoid crushing plastic).
3. Verify hole-pattern alignment on both the U-760 platform and U-651 base.
4. Confirm microscope objective clearance through the `Ø38 mm` bore across full XY travel.
5. Confirm U-651 cable routing through the `-X` notch and PE ground lug access.

---

## 4. Updating `params.json` with Official PI Reference Drawings

The current CAD files were generated using baseline datasheet estimates (`params.json` → `_metadata.reference_status`). Once you obtain the official Physik Instrumente STEP models and PDF drawings:

1. **Place reference files in `reference/`:**
   - `reference/U-760.step` (or `.stp`) and/or `reference/U-760_datasheet.pdf`
   - `reference/U-651.step` (or `.stp`) and/or `reference/U-651_MP136E.pdf`
2. **Extract exact feature coordinates from the STEP files:**
   ```powershell
   .venv\Scripts\python.exe scripts\inspect_reference_step.py
   ```
3. **Update `params.json`:**
   - Update `u760_interface.mounting_holes_xy_mm`, `dowel_pin_holes_xy_mm`, `adapter_outer_x_mm`, `adapter_outer_y_mm`, and `platform_mock_aperture_dia_mm`.
   - Update `u651_interface.mounting_holes_xy_mm`, `pe_ground_hole_xy_mm`, `cable_relief_side`, `stage_outer_x_mm`, `stage_outer_y_mm`, and `stage_height_mm`.
   - Set `_metadata.reference_status` to `"verified_against_official_PI_STEP"`.
4. **Regenerate CAD, Engineering Views, Dynamics, and Automated Verification:**
   ```powershell
   .venv\Scripts\python.exe scripts\generate_adapter.py
   .venv\Scripts\python.exe scripts\verify_assembly.py
   .venv\Scripts\python.exe scripts\render_views.py
   .venv\Scripts\python.exe scripts\analyze_dynamics.py
   ```
5. **Review Outputs:**
   - Check `docs/verification_report.md` — confirm **100% PASS** (zero optical aperture obstruction, zero pairwise assembly interference, full M4 SHCS head clearance).
   - Inspect `output/views/adapter_views.png` visually for hole alignment, cable notch clearance, and rib symmetry.
   - Send `output/u760_to_u651_adapter_aluminum.step` and Section 1 GD&T notes to your machine shop.
