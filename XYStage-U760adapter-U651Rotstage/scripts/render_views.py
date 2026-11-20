"""Render orthographic and 3D isometric engineering views of the U-760 to U-651 adapter.

Reads:
  - output/u760_to_u651_adapter_aluminum.step
  - output/assembly_u760_adapter_u651.step

Outputs:
  - output/views/adapter_views.png (2x2 figure, 180 DPI):
      1. Top View (+Z) — Aluminum adapter
      2. Bottom View (-Z) — Aluminum adapter (underside ribs & pockets)
      3. Front Elevation (+Y) — Stacked assembly (U-760 -> Adapter -> U-651)
      4. 3D Isometric View — Shaded Poly3DCollection of aluminum adapter
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Headless rendering backend

import matplotlib.pyplot as plt
import numpy as np
from build123d import Shape, Solid, import_step
from matplotlib.collections import LineCollection, PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

REPO_ROOT = Path(__file__).resolve().parent.parent
PARAMS_PATH = REPO_ROOT / "params.json"
OUTPUT_DIR = REPO_ROOT / "output"
VIEWS_DIR = OUTPUT_DIR / "views"
OUT_PNG = VIEWS_DIR / "adapter_views.png"

TESS_TOLERANCE = 0.15
EDGE_SAMPLES = 24


def tessellate_triangles(shape: Shape, tolerance: float = TESS_TOLERANCE) -> np.ndarray:
    """Return an (N, 3, 3) float array of triangle vertices for a build123d shape."""
    verts, tris = shape.tessellate(tolerance)
    if not verts or not tris:
        return np.zeros((0, 3, 3), dtype=float)
    v_arr = np.array([[v.X, v.Y, v.Z] for v in verts], dtype=float)
    t_arr = np.array(tris, dtype=int)
    return v_arr[t_arr]


def sample_edge_polylines(shape: Shape, n_samples: int = EDGE_SAMPLES) -> list[np.ndarray]:
    """Sample all edges of a shape into 3D polyline arrays for crisp orthographic lines."""
    polylines: list[np.ndarray] = []
    for edge in shape.edges():
        length = getattr(edge, "length", 0.0)
        if length < 1e-4:
            continue
        # Use 2 points for straight edges, more for curved edges
        gt_attr = getattr(edge, "geom_type", "")
        geom_type = str(gt_attr() if callable(gt_attr) else gt_attr).upper()
        if "LINE" in geom_type:
            ts = (0.0, 1.0)
        else:
            steps = max(8, min(n_samples, int(length * 1.5)))
            ts = np.linspace(0.0, 1.0, steps)
        pts = []
        for t in ts:
            p = edge.position_at(float(t))
            pts.append((p.X, p.Y, p.Z))
        polylines.append(np.array(pts, dtype=float))
    return polylines


def render_ortho_z(
    ax: plt.Axes,
    tris_3d: np.ndarray,
    polylines_3d: list[np.ndarray],
    view: str,
    title: str,
    params: dict,
) -> None:
    """Render Top (+Z) or Bottom (-Z) orthographic view with Z-shaded faces and crisp edges."""
    if tris_3d.shape[0] > 0:
        # Compute face normals to keep only faces visible from +Z or -Z
        v0, v1, v2 = tris_3d[:, 0], tris_3d[:, 1], tris_3d[:, 2]
        normals = np.cross(v1 - v0, v2 - v0)
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        nz = (normals / norms)[:, 2]
        z_mean = tris_3d[:, :, 2].mean(axis=1)

        if view == "top":
            mask = nz > 0.05
            order = np.argsort(z_mean[mask])  # Painter's algorithm: low Z first, high Z on top
            sel_tris = tris_3d[mask][order]
            sel_z = z_mean[mask][order]
            polys_2d = sel_tris[:, :, [0, 1]]
        else:
            # Bottom view (-Z): looking up at the underside (flip X so left/right matches physical flip)
            mask = nz < -0.05
            order = np.argsort(-z_mean[mask])  # High Z first, Z=0 bottom face on top
            sel_tris = tris_3d[mask][order]
            sel_z = z_mean[mask][order]
            polys_2d = sel_tris[:, :, [0, 1]].copy()
            polys_2d[:, :, 0] *= -1.0

        z_min, z_max = float(tris_3d[:, :, 2].min()), float(tris_3d[:, :, 2].max())
        z_span = max(z_max - z_min, 1e-6)
        norm_z = np.clip((sel_z - z_min) / z_span, 0.0, 1.0)

        # Clean metallic blue-grey palette distinguishing deck, raised pads, and recessed pockets
        cmap = plt.get_cmap("Blues") if view == "top" else plt.get_cmap("GnBu_r")
        face_colors = cmap(0.20 + 0.55 * norm_z)
        face_colors[:, 3] = 0.92

        pc = PolyCollection(polys_2d, facecolors=face_colors, edgecolors="none", antialiaseds=False)
        ax.add_collection(pc)

    # Overlay crisp edge wireframe
    segs = []
    for pl in polylines_3d:
        xy = pl[:, [0, 1]].copy()
        if view == "bottom":
            xy[:, 0] *= -1.0
        segs.append(xy)
    lc = LineCollection(segs, colors="#1b263b", linewidths=0.55, alpha=0.85)
    ax.add_collection(lc)

    # Subtle key annotations
    outer_x = float(params["u760_interface"]["adapter_outer_x_mm"])
    outer_y = float(params["u760_interface"]["adapter_outer_y_mm"])
    ap_dia = float(params["optical"]["adapter_clear_aperture_dia_mm"])

    ax.annotate(
        f"Ø{ap_dia:.0f} mm\nClear Aperture",
        xy=(0.0, 0.0),
        ha="center",
        va="center",
        fontsize=7.5,
        fontweight="bold",
        color="#0d1b2a",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#415a77", alpha=0.85),
    )

    if view == "top":
        ax.annotate(
            "-X Cable\nNotch",
            xy=(-outer_x / 2.0 + 2.0, 0.0),
            xytext=(-outer_x / 2.0 - 15.0, -20.0),
            fontsize=7,
            color="#9b2226",
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#9b2226", lw=0.9),
            ha="center",
        )
        ax.set_xlabel("X (mm)")
    else:
        ax.set_xlabel("-X (mm)  [Bottom View]")

    ax.set_ylabel("Y (mm)")
    ax.set_title(title, fontsize=10.5, fontweight="bold", pad=8)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-outer_x * 0.68, outer_x * 0.68)
    ax.set_ylim(-outer_y * 0.68, outer_y * 0.68)
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)


def render_elevation_y(
    ax: plt.Axes,
    asm_shape: Shape,
    al_height_mm: float,
    title: str,
) -> None:
    """Render Front/Side Elevation (+Y view, X-Z plane) of the stacked assembly."""
    solids: list[Solid] = list(asm_shape.solids()) if hasattr(asm_shape, "solids") else []
    solids.sort(key=lambda s: 0.5 * (s.bounding_box().min.Z + s.bounding_box().max.Z))

    palette = [
        ("#8d99ae", "#2b2d42", "U-760 XY Stage (Mock)"),
        ("#457b9d", "#1d3557", "Adapter (Al 6061-T6)"),
        ("#e9c46a", "#8a5a00", "U-651 Rotation Stage (Mock)"),
    ]

    x_min_all, x_max_all = 1e9, -1e9
    z_min_all, z_max_all = 1e9, -1e9

    for idx, solid in enumerate(solids):
        bb = solid.bounding_box()
        x_min_all = min(x_min_all, bb.min.X)
        x_max_all = max(x_max_all, bb.max.X)
        z_min_all = min(z_min_all, bb.min.Z)
        z_max_all = max(z_max_all, bb.max.Z)

        z_mid = 0.5 * (bb.min.Z + bb.max.Z)
        if z_mid < 0.0:
            fc, ec, label = palette[0]
        elif z_mid <= al_height_mm + 0.5:
            fc, ec, label = palette[1]
        else:
            fc, ec, label = palette[2]

        tris = tessellate_triangles(solid, TESS_TOLERANCE)
        if tris.shape[0] > 0:
            # Project onto X-Z plane, painter-sorted by Y
            y_mean = tris[:, :, 1].mean(axis=1)
            order = np.argsort(-y_mean)
            polys_xz = tris[order][:, :, [0, 2]]
            pc = PolyCollection(
                polys_xz,
                facecolors=fc,
                edgecolors="none",
                alpha=0.85,
                antialiaseds=False,
            )
            ax.add_collection(pc)

        polylines = sample_edge_polylines(solid)
        segs_xz = [pl[:, [0, 2]] for pl in polylines]
        lc = LineCollection(segs_xz, colors=ec, linewidths=0.45, alpha=0.75)
        ax.add_collection(lc)

        # Dummy patch for legend
        ax.fill([], [], facecolor=fc, edgecolor=ec, label=f"{label} (Z: {bb.min.Z:.0f}..{bb.max.Z:.0f} mm)")

    # Reference Z-level guidelines
    for z_val, z_lbl in ((0.0, "Z=0 (U-760 Datum)"), (al_height_mm, f"Z={al_height_mm:.0f} (U-651 Base)")):
        ax.axhline(z_val, color="#d62828", linestyle=":", linewidth=0.8, alpha=0.75)
        ax.text(
            x_max_all + 2.5,
            z_val,
            z_lbl,
            va="center",
            ha="left",
            fontsize=7,
            color="#d62828",
        )

    ax.set_title(title, fontsize=10.5, fontweight="bold", pad=8)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Z (mm)")
    ax.set_aspect("equal", adjustable="box")
    x_pad = max((x_max_all - x_min_all) * 0.25, 22.0)
    z_pad = max((z_max_all - z_min_all) * 0.25, 10.0)
    ax.set_xlim(x_min_all - x_pad * 0.5, x_max_all + x_pad * 1.45)
    ax.set_ylim(z_min_all - z_pad, z_max_all + z_pad)
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)
    ax.legend(loc="lower left", fontsize=7, framealpha=0.9)


def render_isometric_3d(ax, tris_3d: np.ndarray, title: str) -> None:
    """Render a 3D isometric shaded mesh using Poly3DCollection with Lambertian lighting."""
    if tris_3d.shape[0] > 0:
        v0, v1, v2 = tris_3d[:, 0], tris_3d[:, 1], tris_3d[:, 2]
        normals = np.cross(v1 - v0, v2 - v0)
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        unit_n = normals / norms

        # Directional key light + ambient fill for crisp metallic contrast
        light_dir = np.array([0.45, -0.55, 0.70])
        light_dir /= np.linalg.norm(light_dir)
        intensity = 0.35 + 0.65 * np.clip(np.abs(unit_n @ light_dir), 0.0, 1.0)

        base_rgb = np.array([0.36, 0.55, 0.74])  # Anodized slate-blue aluminum tone
        colors = np.zeros((tris_3d.shape[0], 4), dtype=float)
        colors[:, :3] = np.clip(intensity[:, None] * base_rgb[None, :] * 1.15, 0.0, 1.0)
        colors[:, 3] = 1.0

        poly3d = Poly3DCollection(
            tris_3d,
            facecolors=colors,
            edgecolors=(0.10, 0.15, 0.22, 0.12),
            linewidths=0.15,
        )
        ax.add_collection3d(poly3d)

        mins = tris_3d.reshape(-1, 3).min(axis=0)
        maxs = tris_3d.reshape(-1, 3).max(axis=0)
        center = 0.5 * (mins + maxs)
        half_span = 0.55 * float(np.max(maxs - mins))

        ax.set_xlim(center[0] - half_span, center[0] + half_span)
        ax.set_ylim(center[1] - half_span, center[1] + half_span)
        ax.set_zlim(center[2] - half_span * 0.45, center[2] + half_span * 0.45)
        ax.set_box_aspect((1.0, 1.0, 0.45))

    ax.view_init(elev=30, azim=-55)
    ax.set_xlabel("X (mm)", fontsize=8, labelpad=4)
    ax.set_ylabel("Y (mm)", fontsize=8, labelpad=4)
    ax.set_zlabel("Z (mm)", fontsize=8, labelpad=2)
    ax.tick_params(labelsize=7)
    ax.set_title(title, fontsize=10.5, fontweight="bold", pad=6)


def main() -> int:
    al_step = OUTPUT_DIR / "u760_to_u651_adapter_aluminum.step"
    asm_step = OUTPUT_DIR / "assembly_u760_adapter_u651.step"

    for path in (PARAMS_PATH, al_step, asm_step):
        if not path.exists():
            print(f"[ERROR] Required file not found: {path}", file=sys.stderr)
            return 1

    with PARAMS_PATH.open("r", encoding="utf-8") as fh:
        params = json.load(fh)

    al_shape = import_step(str(al_step))
    asm_shape = import_step(str(asm_step))

    al_tris = tessellate_triangles(al_shape, TESS_TOLERANCE)
    al_polylines = sample_edge_polylines(al_shape, EDGE_SAMPLES)
    al_height = float(params["variants"]["aluminum"]["total_height_mm"])

    fig = plt.figure(figsize=(14, 10.5), dpi=180)
    fig.suptitle(
        "PI U-760 XY Stage to U-651 Rotation Stage Adapter — Engineering Views (Al 6061-T6)",
        fontsize=13,
        fontweight="bold",
        y=0.975,
    )

    ax_top = fig.add_subplot(2, 2, 1)
    render_ortho_z(
        ax_top,
        al_tris,
        al_polylines,
        view="top",
        title="Top View (+Z) — Raised U-651 Pads, Dowels & U-760 Counterbores",
        params=params,
    )

    ax_bot = fig.add_subplot(2, 2, 2)
    render_ortho_z(
        ax_bot,
        al_tris,
        al_polylines,
        view="bottom",
        title="Bottom View (-Z) — Stiffening Ribs, Pockets & U-651 Counterbores",
        params=params,
    )

    ax_elev = fig.add_subplot(2, 2, 3)
    render_elevation_y(
        ax_elev,
        asm_shape,
        al_height_mm=al_height,
        title="Front Elevation (+Y) — Stacked Assembly Z-Profile",
    )

    ax_iso = fig.add_subplot(2, 2, 4, projection="3d")
    render_isometric_3d(
        ax_iso,
        al_tris,
        title="3D Isometric View — CNC Aluminum Adapter",
    )

    plt.tight_layout(rect=(0.0, 0.0, 1.0, 0.955))
    VIEWS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=180)
    plt.close(fig)

    print(f"Rendered 2x2 engineering views to: {OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
