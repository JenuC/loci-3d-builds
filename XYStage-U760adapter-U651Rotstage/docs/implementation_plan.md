# CAD Implementation Plan: PI U-760 XY Stage to U-651 Rotational Stage Adapter

## Goal
Design and generate a manufacturing-ready parametric CAD model for a mechanical adapter that mounts a **Physik Instrumente (PI) U-651 Rotational Stage** onto a **PI U-760 PILine® Ultrasonic XY Stage** for an **inverted microscope** setup, optimized for:
1. **Minimal vibration & highest structural natural frequency** (avoiding resonance with the U-760 ultrasonic piezo drive and servo loop).
2. **Shortest XY step-and-settle time** (minimum moving mass and minimum vertical Center-of-Gravity offset).
3. **Full optical clear aperture** ($\ge \varnothing 36\text{ mm}$ matching the U-651 aperture, plus objective clearance) and **minimum Z-stack height**.
4. **Full compliance with PI mounting requirements** (including the U-651's $\le 10\,\mu\text{m}$ mounting flatness specification).

---

## Dynamic Design Principles (Vibration & Settling Time)

To minimize settling time on a high-acceleration PILine® XY stage (`U-760`, up to $100\text{ mm/s}$):
- **Maximize First Natural Frequency ($f_1 \propto \sqrt{k / m}$):** Keep structural modes well above the XY stage's servo bandwidth so closed-loop positioning does not excite adapter bending or rocking modes.
- **Minimize Moving Mass ($m_{\text{adapter}}$):** The U-651 already contributes $\sim 500\text{ g}$ of payload. Every gram saved in the adapter reduces peak inertial force ($F = ma$) and improves step-and-settle speed.
- **Minimize Z-Height & CoG Offset ($h_{\text{CoG}}$):** XY acceleration creates an overturning pitching moment $M = m \cdot a \cdot h_{\text{CoG}}$ on the U-760 linear bearings. A recessed/nested low-profile adapter keeps the U-651 as close to the U-760 bearing plane as microscope objective clearance allows.
- **Eliminate Micro-Slip & Rocking:**
  - Use **raised precision-machined mounting pads** (easier to fly-cut/grind to $\le 10\,\mu\text{m}$ flatness than a full plate face).
  - Use **symmetric rib / isogrid pocketing** around the central $\varnothing 36\text{ mm}$ aperture for high torsional and bending rigidity without excess mass.
  - Provide an integrated **cable routing / strain-relief feature** for the U-651 cable and M4 PE ground lug so trailing cable drag does not inject settling disturbances.

---

## Material Comparison: CNC Aluminum vs. 3D-Printed Polymers (PLA-like)

Once exact geometry is finalized, we will compute exact mass and natural frequency estimates for each option in `docs/material_and_dynamics_comparison.md`. Below is the baseline engineering comparison:

| Property / Criterion | **Al 6061-T6 / 7075-T6 (CNC)** | **Al MIC-6 Cast Plate (CNC)** | **PLA / PLA+ (FDM 3D Print)** | **CF-Nylon / PA12-CF (FDM)** |
| :--- | :--- | :--- | :--- | :--- |
| **Elastic Modulus ($E$)** | $69\text{–}72\text{ GPa}$ | $\sim 71\text{ GPa}$ | $2.5\text{–}3.5\text{ GPa}$ *(~22× lower)* | $6\text{–}10\text{ GPa}$ *(~8× lower)* |
| **Density ($\rho$)** | $2.70\text{–}2.81\text{ g/cm}^3$ | $2.80\text{ g/cm}^3$ | $1.24\text{ g/cm}^3$ | $1.15\text{–}1.25\text{ g/cm}^3$ |
| **Specific Stiffness ($E/\rho$)** | **Very High** ($\sim 25.5$) | **Very High** ($\sim 25.4$) | **Low** ($\sim 2.4$, ~10× lower) | **Moderate** ($\sim 6.5$, ~4× lower) |
| **Relative $f_1$ (Same Geometry)** | **$1.0\times$ (Baseline, highest)** | **$1.0\times$** | **$\sim 0.30\times$ (3× lower $f_1$)** | **$\sim 0.50\times$ (2× lower $f_1$)** |
| **Internal Damping ($\zeta$)** | Low ($\sim 0.001\text{–}0.005$) | Low ($\sim 0.002$) | Higher ($\sim 0.02\text{–}0.05$) | Moderate ($\sim 0.015\text{–}0.03$) |
| **Flatness ($\le 10\,\mu\text{m}$ U-651 req.)** | Achievable (fly-cut / grind) | **Excellent** (stress-relieved) | **Not achievable** (~100–300 µm) | **Not achievable** (~100–250 µm) |
| **Bolt Preload & Creep** | Zero creep; handles M4 (2.1 Nm) & M6 (7.1 Nm) | Zero creep; handles full torque | **Creeps under preload** (bolts loosen, causing vibration) | Mild creep; needs brass/steel inserts |
| **Thermal Expansion (CTE)** | **Matches U-651 Al base** ($\sim 23\,\mu\text{m/m·K}$) | **Matches U-651 Al base** | Mismatch ($\sim 68\,\mu\text{m/m·K}$) | Moderate mismatch |
| **Best Role** | **Production / Final Stage** | **Production (best flatness stability)** | **Rapid fit-check & cable-routing prototype ONLY** | **Light-duty prototype / temporary mount** |

> **Key Takeaway on PLA vs. Aluminum for Settling Time:**
> Although PLA has higher internal material damping than aluminum, its stiffness is **~20–25× lower**, which drops the adapter's first natural frequency by roughly **3×** (for the same Z-height). On a precision XY stage, a low natural frequency combined with bolt-preload creep causes sustained ringing and degrades both settling time and U-651 bearing life (violating the $\le 10\,\mu\text{m}$ flatness spec).
> **Recommended Strategy:** Export a 3D-printable STL (with slightly thicker ribs if needed) for a **$5 same-day PLA fit-check** on the microscope, then CNC-machine the final adapter in **Al 6061-T6 or MIC-6** (with black anodizing to suppress stray microscope light).

---

## Proposed Execution Phases

### Phase 1: Reference Ingestion & Constraint Extraction
- Place the official PI STEP files and/or dimensioned PDF drawings for **U-760** and **U-651** in `reference/`.
- Extract exact coordinates and envelopes:
  - U-760 moving platform mounting hole pattern, thread size, counterbore/clearance, locating pins, and central aperture cutout.
  - U-651 base mounting hole pattern (4× M4 or M6, min 13 mm engagement), outer envelope, $\varnothing 36\text{ mm}$ clear aperture concentricity, cable exit direction, and M4 PE grounding hole location.
  - Microscope objective/condenser vertical clearance envelope.

### Phase 2: Parametric CAD Model Development
- Set up Python CAD toolchain (`build123d` or `cadquery`) in a local virtual environment.
- Create a parameterized CAD generator:
  - `params.json` — Single source of truth for all extracted U-760 / U-651 coordinates, rib thicknesses, aperture diameter, and tolerances.
  - `generate_adapter.py` — Builds the solid model with:
    - Low-profile stepped body & $\ge \varnothing 36\text{ mm}$ central optical aperture.
    - Recessed pocketed/ribbed underside for maximum stiffness-to-weight ratio.
    - Precision raised mounting pads for U-651 ($\le 10\,\mu\text{m}$ flatness callout) and U-760 interface.
    - Counterbored/threaded fastener holes with full wrench/hex-key clearance and zero interference.
    - Cable strain-relief / tie-down slot for the U-651 cable.
    - Material variant flag (`--material aluminum` vs `--material pla-prototype` with adjusted wall/rib thickness & heat-set insert sizing for 3D printing).

### Phase 3: Analytical Vibration & Mass/Stiffness Comparison Report
- Write `analyze_dynamics.py` to compute:
  - Exact CAD volume, adapter mass, center of gravity, and moments of inertia ($I_{xx}, I_{yy}, I_{zz}$).
  - Combined moving mass ($m_{\text{U651}} + m_{\text{adapter}}$) and CoG height above the U-760 platform.
  - First bending/rocking natural frequency estimates comparing **Al 6061-T6**, **Al 7075-T6 / MIC-6**, **PLA**, and **CF-Nylon**.
  - Save report to `docs/material_and_dynamics_comparison.md`.

### Phase 4: Export & Automated Verification
- Export deliverables into `output/`:
  - `u760_to_u651_adapter_aluminum.step` (CNC-ready)
  - `u760_to_u651_adapter_pla_fitcheck.stl` (3D-print fit-check)
  - `assembly_u760_adapter_u651.step` (full stacked assembly using your imported PI STEP models)
  - `views/` — Orthographic and isometric rendered views showing hole alignment and clearances.
- Run automated geometry verification (`verify_assembly.py`):
  - **Boolean interference check** between adapter, U-760 STEP, U-651 STEP, and fastener envelopes ($0.0\text{ mm}^3$ collision).
  - **Concentricity & aperture check** confirming unobstructed $\ge \varnothing 36\text{ mm}$ optical clear path.
  - **Bolt engagement & tool access check** verifying screw lengths do not bottom out or collide with internal U-760/U-651 mechanisms.
