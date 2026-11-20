"""Tkinter GUI for editing params.json and running the U-760 to U-651 CAD pipeline.

Launch with:
    uv run python scripts/params_ui.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from PIL import Image, ImageTk

ROOT_DIR = Path(__file__).resolve().parent.parent
PARAMS_PATH = ROOT_DIR / "params.json"
VIEWS_DIR = ROOT_DIR / "output" / "views"
ADAPTER_IMG_PATH = VIEWS_DIR / "adapter_views.png"
DYNAMICS_IMG_PATH = VIEWS_DIR / "material_dynamics_comparison.png"

PIPELINE_SCRIPTS = [
    ("Generate CAD", ROOT_DIR / "scripts" / "generate_adapter.py"),
    ("Analyze Dynamics", ROOT_DIR / "scripts" / "analyze_dynamics.py"),
    ("Verify Assembly", ROOT_DIR / "scripts" / "verify_assembly.py"),
    ("Render Views", ROOT_DIR / "scripts" / "render_views.py"),
]


def _format_value(val: Any) -> str:
    if isinstance(val, (list, dict)):
        return json.dumps(val)
    return str(val)


def _parse_value(text: str, template: Any) -> Any:
    raw = text.strip()
    if isinstance(template, bool):
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        raise ValueError(f"Expected boolean, got {raw!r}")
    if isinstance(template, int):
        return int(raw)
    if isinstance(template, float):
        return float(raw)
    if isinstance(template, (list, dict)):
        parsed = json.loads(raw)
        if not isinstance(parsed, type(template)):
            raise ValueError(f"Expected {type(template).__name__}, got {type(parsed).__name__}")
        return parsed
    return raw


class ScrollableFrame(ttk.Frame):
    """Vertically scrollable ttk.Frame container."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self._win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._win_id, width=e.width),
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class ParamsUI(tk.Tk):
    def __init__(self, params_path: Path = PARAMS_PATH) -> None:
        super().__init__()
        self.params_path = params_path
        self.title("PI U-760 to U-651 Adapter — Parameter & CAD Studio")
        self.geometry("1280x820")
        self.minsize(1024, 680)

        self.data: dict[str, Any] = {}
        # Maps (section, key) or (section, subkey, key) -> (tk.StringVar, template_value)
        self.field_vars: dict[tuple[str, ...], tuple[tk.StringVar, Any]] = {}
        self.material_vars: dict[str, tuple[tk.StringVar, Any]] = {}
        self.current_material_key: str | None = None
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._preview_mode = tk.StringVar(value="adapter")
        self._is_running = False
        self._action_buttons: list[ttk.Button] = []

        self._build_layout()
        self.load_from_disk()
        self.refresh_preview()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        # Top toolbar
        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.pack(fill="x")

        ttk.Label(
            toolbar,
            text="PI U-760 XY → U-651 Rotation Adapter",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side="right")

        self.btn_reload = ttk.Button(btn_frame, text="Reload", command=self.load_from_disk)
        self.btn_save = ttk.Button(btn_frame, text="Save params.json", command=self.save_to_disk)
        self.btn_run_all = ttk.Button(btn_frame, text="Save & Run All", command=self.run_all_pipeline)
        self.btn_reload.pack(side="left", padx=3)
        self.btn_save.pack(side="left", padx=3)
        self.btn_run_all.pack(side="left", padx=(8, 0))
        self._action_buttons.extend([self.btn_reload, self.btn_save, self.btn_run_all])

        # Main horizontal split
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        # Left: Notebook for parameter editing
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)

        self.notebook = ttk.Notebook(left_frame)
        self.notebook.pack(fill="both", expand=True)

        self.tab_interfaces = ScrollableFrame(self.notebook)
        self.tab_variants = ScrollableFrame(self.notebook)
        self.tab_materials = ttk.Frame(self.notebook, padding=8)
        self.tab_raw = ttk.Frame(self.notebook, padding=6)

        self.notebook.add(self.tab_interfaces, text="Optical & Stage Interfaces")
        self.notebook.add(self.tab_variants, text="Adapter Variants")
        self.notebook.add(self.tab_materials, text="Materials")
        self.notebook.add(self.tab_raw, text="Raw JSON")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.raw_text = scrolledtext.ScrolledText(
            self.tab_raw, font=("Consolas", 10), wrap="none", undo=True
        )
        self.raw_text.pack(fill="both", expand=True)

        # Right: Preview + Pipeline controls + Console log
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)

        # Individual step buttons
        step_bar = ttk.LabelFrame(right_frame, text="Pipeline Steps", padding=6)
        step_bar.pack(fill="x", pady=(0, 6))
        for label, script_path in PIPELINE_SCRIPTS:
            b = ttk.Button(
                step_bar,
                text=label,
                command=lambda p=script_path, lbl=label: self._run_single_step(lbl, p),
            )
            b.pack(side="left", padx=3, expand=True, fill="x")
            self._action_buttons.append(b)

        # Preview image panel
        preview_box = ttk.LabelFrame(right_frame, text="Visual Preview", padding=6)
        preview_box.pack(fill="both", expand=True, pady=(0, 6))

        toggle_bar = ttk.Frame(preview_box)
        toggle_bar.pack(fill="x", pady=(0, 4))
        ttk.Radiobutton(
            toggle_bar,
            text="CAD Views (2×2)",
            variable=self._preview_mode,
            value="adapter",
            command=self.refresh_preview,
        ).pack(side="left", padx=4)
        ttk.Radiobutton(
            toggle_bar,
            text="Dynamics & Materials",
            variable=self._preview_mode,
            value="dynamics",
            command=self.refresh_preview,
        ).pack(side="left", padx=4)
        ttk.Button(toggle_bar, text="Refresh", command=self.refresh_preview).pack(side="right")

        self.preview_label = ttk.Label(preview_box, anchor="center", text="No preview image yet.")
        self.preview_label.pack(fill="both", expand=True)
        self.preview_label.bind("<Configure>", lambda _e: self.refresh_preview())

        # Log output panel
        log_box = ttk.LabelFrame(right_frame, text="Pipeline Output", padding=6)
        log_box.pack(fill="both", expand=False)
        self.log_text = scrolledtext.ScrolledText(
            log_box, height=11, font=("Consolas", 9), state="disabled"
        )
        self.log_text.pack(fill="both", expand=True)

        # Status bar
        self.status_var = tk.StringVar(value=f"Loaded: {self.params_path}")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=(8, 3)).pack(
            fill="x", side="bottom"
        )

    # ------------------------------------------------------------------
    # Data Loading & Form Population
    # ------------------------------------------------------------------
    def load_from_disk(self) -> None:
        try:
            self.data = json.loads(self.params_path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Load Error", f"Failed to read {self.params_path}:\n{exc}")
            return

        self.field_vars.clear()
        self._populate_interfaces_tab()
        self._populate_variants_tab()
        self._populate_materials_tab()
        self._sync_raw_text_from_data()
        self.status_var.set(f"Loaded {self.params_path.name} successfully.")
        self._append_log(f"[UI] Loaded {self.params_path}\n")

    def _clear_children(self, widget: tk.Widget) -> None:
        for child in widget.winfo_children():
            child.destroy()

    def _add_section_fields(
        self, parent: ttk.Frame, title: str, section_key: str, mapping: dict[str, Any], prefix: tuple[str, ...]
    ) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=(8, 6))
        frame.pack(fill="x", padx=8, pady=6)
        frame.columnconfigure(1, weight=1)

        for row_idx, (key, val) in enumerate(mapping.items()):
            ttk.Label(frame, text=key, width=32, anchor="w").grid(
                row=row_idx, column=0, sticky="w", padx=(0, 8), pady=2
            )
            var = tk.StringVar(value=_format_value(val))
            entry = ttk.Entry(frame, textvariable=var)
            entry.grid(row=row_idx, column=1, sticky="ew", pady=2)
            self.field_vars[prefix + (key,)] = (var, val)

    def _populate_interfaces_tab(self) -> None:
        container = self.tab_interfaces.inner
        self._clear_children(container)
        self._add_section_fields(container, "Optical Clear Aperture", "optical", self.data["optical"], ("optical",))
        self._add_section_fields(
            container, "PI U-760 XY Stage Interface", "u760_interface", self.data["u760_interface"], ("u760_interface",)
        )
        self._add_section_fields(
            container,
            "PI U-651 Rotation Stage Interface",
            "u651_interface",
            self.data["u651_interface"],
            ("u651_interface",),
        )

    def _populate_variants_tab(self) -> None:
        container = self.tab_variants.inner
        self._clear_children(container)
        for v_key, v_dict in self.data.get("variants", {}).items():
            self._add_section_fields(
                container, f"Variant: {v_key}", v_key, v_dict, ("variants", v_key)
            )

    def _populate_materials_tab(self) -> None:
        self._clear_children(self.tab_materials)
        materials = self.data.get("materials", {})
        mat_keys = list(materials.keys())
        if not mat_keys:
            return

        top = ttk.Frame(self.tab_materials)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Select Material:").pack(side="left", padx=(0, 8))

        self.mat_selector_var = tk.StringVar(value=mat_keys[0])
        combo = ttk.Combobox(top, textvariable=self.mat_selector_var, values=mat_keys, state="readonly", width=26)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", self._on_material_selected)

        self.mat_fields_frame = ttk.LabelFrame(self.tab_materials, text="Material Properties", padding=(10, 8))
        self.mat_fields_frame.pack(fill="x")
        self.mat_fields_frame.columnconfigure(1, weight=1)

        self.current_material_key = None
        self._load_material_fields(mat_keys[0])

    def _commit_current_material(self) -> None:
        if not self.current_material_key or not self.material_vars:
            return
        target = self.data["materials"][self.current_material_key]
        for key, (var, template) in self.material_vars.items():
            target[key] = _parse_value(var.get(), template)

    def _load_material_fields(self, mat_key: str) -> None:
        self._clear_children(self.mat_fields_frame)
        self.material_vars.clear()
        self.current_material_key = mat_key
        mat_dict = self.data["materials"][mat_key]
        self.mat_fields_frame.configure(text=f"Material Properties: {mat_key}")

        for row_idx, (key, val) in enumerate(mat_dict.items()):
            ttk.Label(self.mat_fields_frame, text=key, width=28, anchor="w").grid(
                row=row_idx, column=0, sticky="w", padx=(0, 8), pady=3
            )
            var = tk.StringVar(value=_format_value(val))
            ttk.Entry(self.mat_fields_frame, textvariable=var).grid(
                row=row_idx, column=1, sticky="ew", pady=3
            )
            self.material_vars[key] = (var, val)

    def _on_material_selected(self, _event: Any = None) -> None:
        try:
            self._commit_current_material()
        except Exception as exc:
            messagebox.showerror("Validation Error", f"Invalid value in {self.current_material_key}:\n{exc}")
            if self.current_material_key:
                self.mat_selector_var.set(self.current_material_key)
            return
        self._load_material_fields(self.mat_selector_var.get())

    # ------------------------------------------------------------------
    # Syncing & Saving
    # ------------------------------------------------------------------
    def _collect_form_into_data(self) -> None:
        for path_tuple, (var, template) in self.field_vars.items():
            parsed = _parse_value(var.get(), template)
            cursor = self.data
            for part in path_tuple[:-1]:
                cursor = cursor[part]
            cursor[path_tuple[-1]] = parsed
        self._commit_current_material()

    def _sync_raw_text_from_data(self) -> None:
        self.raw_text.delete("1.0", "end")
        self.raw_text.insert("1.0", json.dumps(self.data, indent=2) + "\n")

    def _on_tab_changed(self, _event: Any = None) -> None:
        current_tab = self.notebook.select()
        if current_tab == str(self.tab_raw):
            try:
                self._collect_form_into_data()
                self._sync_raw_text_from_data()
            except Exception:
                pass

    def save_to_disk(self) -> bool:
        try:
            if self.notebook.select() == str(self.tab_raw):
                self.data = json.loads(self.raw_text.get("1.0", "end"))
                # Re-populate form tabs so they stay in sync with raw edits
                self.field_vars.clear()
                self._populate_interfaces_tab()
                self._populate_variants_tab()
                self._populate_materials_tab()
            else:
                self._collect_form_into_data()
                self._sync_raw_text_from_data()

            self.params_path.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")
            self.status_var.set(f"Saved {self.params_path.name}.")
            self._append_log(f"[UI] Saved {self.params_path}\n")
            return True
        except Exception as exc:
            messagebox.showerror("Save / Validation Error", str(exc))
            return False

    # ------------------------------------------------------------------
    # Pipeline Execution & Preview
    # ------------------------------------------------------------------
    def _set_running(self, running: bool) -> None:
        self._is_running = running
        state = "disabled" if running else "normal"
        for btn in self._action_buttons:
            btn.configure(state=state)

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _run_steps_async(self, steps: list[tuple[str, Path]]) -> None:
        if self._is_running:
            return
        self._set_running(True)

        def worker() -> None:
            all_ok = True
            for label, script_path in steps:
                self.after(0, self.status_var.set, f"Running: {label} ...")
                self.after(0, self._append_log, f"\n=== Running {label} ({script_path.name}) ===\n")
                try:
                    proc = subprocess.run(
                        [sys.executable, str(script_path)],
                        cwd=str(ROOT_DIR),
                        capture_output=True,
                        text=True,
                    )
                    if proc.stdout:
                        self.after(0, self._append_log, proc.stdout)
                    if proc.stderr:
                        self.after(0, self._append_log, proc.stderr)
                    if proc.returncode != 0:
                        all_ok = False
                        self.after(
                            0,
                            self._append_log,
                            f"[ERROR] {label} exited with code {proc.returncode}\n",
                        )
                        break
                except Exception as exc:
                    all_ok = False
                    self.after(0, self._append_log, f"[EXCEPTION] {label}: {exc}\n")
                    break

            final_msg = "Pipeline completed successfully." if all_ok else "Pipeline finished with errors."
            self.after(0, self.status_var.set, final_msg)
            self.after(0, self.refresh_preview)
            self.after(0, self._set_running, False)

        threading.Thread(target=worker, daemon=True).start()

    def _run_single_step(self, label: str, script_path: Path) -> None:
        self._run_steps_async([(label, script_path)])

    def run_all_pipeline(self) -> None:
        if not self.save_to_disk():
            return
        self._run_steps_async(PIPELINE_SCRIPTS)

    def refresh_preview(self) -> None:
        img_path = ADAPTER_IMG_PATH if self._preview_mode.get() == "adapter" else DYNAMICS_IMG_PATH
        if not img_path.exists():
            self.preview_label.configure(image="", text=f"Not found:\n{img_path.name}")
            self._preview_photo = None
            return

        avail_w = max(self.preview_label.winfo_width() - 12, 360)
        avail_h = max(self.preview_label.winfo_height() - 12, 260)
        try:
            with Image.open(img_path) as im:
                im_copy = im.copy()
            im_copy.thumbnail((avail_w, avail_h), Image.Resampling.LANCZOS)
            self._preview_photo = ImageTk.PhotoImage(im_copy)
            self.preview_label.configure(image=self._preview_photo, text="")
        except Exception as exc:
            self.preview_label.configure(image="", text=f"Preview error: {exc}")


def main() -> None:
    app = ParamsUI()
    app.mainloop()


if __name__ == "__main__":
    main()
