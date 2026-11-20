# Reference CAD & Datasheets Folder

Place official Physik Instrumente (PI) mechanical reference files here:
- `U-760.step` (or `.stp`) and/or `U-760_datasheet.pdf`
- `U-651.step` (or `.stp`) and/or `U-651_MP136E.pdf`

Once placed here:
1. Run `uv run python scripts/inspect_reference_step.py` to inspect bounding boxes and cylindrical hole features from the STEP files.
2. Update the exact hole coordinates in `params.json`.
3. Re-run `uv run python scripts/generate_adapter.py`, `uv run python scripts/analyze_dynamics.py`, `uv run python scripts/verify_assembly.py`, and `uv run python scripts/render_views.py` to regenerate and re-verify all STEP/STL deliverables.
