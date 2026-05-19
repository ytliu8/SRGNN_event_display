# SRGNN Event Display

Interactive 3D HTML event display for IceCube + Upgrade events processed by the
Super-Resolution GNN (SRGNN). Each event renders as a Plotly 3D scene with
IC86 DOM hits, Upgrade PMT hits, the interaction vertex, the neutrino
direction, and (in SRGNN mode) the model's per-PMT activity predictions.
Clicking any Upgrade PMT opens a zoomed DOM panel showing the individual PMTs
of that DOM color-coded by status.

## Files

- **`generate_event_display.py`** — Main entry point. Loads SRGNN inference
  results + detector geometry, builds per-event Plotly figures and per-DOM
  status data, then writes a self-contained HTML file to `output/`.
  Two modes:
  - *vanilla* (default): only true active-hit Upgrade PMTs are shown.
  - *SRGNN* (`--SRGNN`): also shows inactive PMTs with continuous BCE
    prediction scores, plus a threshold slider in the HTML page.

- **`event_display_template.py`** — Returns the full HTML document as a
  string (CSS, JS, Plotly client-side logic, threshold slider, DOM detail
  panel). `build_html(...)` is called once at the end of
  `generate_event_display.py`.

- **`symbol_shapes.py`** — Small geometry helpers used by the template /
  generator:
  - `_build_3d_diamond(...)` — vertex marker (octahedron Mesh3d).
  - `_build_bubble_trail(...)` — Dalí-style dissolving sphere trail along
    each PMT's orientation vector, used for the active/inactive PMT glow.

- **`output/`** — Generated HTML files land here:
  - `event_display_numu.html` (vanilla)
  - `SRGNN_event_display_numu.html` (with `--SRGNN`)

The generator also imports from the parent SRGNN package:
`event_display.py` (in `/storage/home/yml5822/work/graphnet/SRGNN/`) provides
`load_results`, `load_geometry`, and `plot_event_3d`.

## Environment

This script does **not** require GraphNeT itself — it only needs:

- `numpy`
- `scipy`
- `plotly`

Install in any Python ≥3.8 environment:

```bash
pip install numpy scipy plotly
```

That said, **if a GraphNeT environment is already set up on your machine, the
script runs directly inside it with no extra setup** — Plotly, NumPy, and
SciPy all ship with GraphNeT. Just activate your existing GraphNeT conda /
venv and run.

Quick sanity check:

```bash
python -c "import plotly, numpy, scipy; print('ok')"
```

## Running

From the `event_display/` directory (or anywhere — paths inside the script
are absolute):

```bash
# Vanilla: only active-hit PMTs
python generate_event_display.py

# SRGNN: includes inactive PMTs and BCE prediction scores
python generate_event_display.py --SRGNN
```

Output is written to `output/`. Open the HTML file directly in a browser.
The first 100 events from the results pickle are rendered.

## Input Data Structure

The script reads three input files. The paths are hard-coded near the top of
`generate_event_display.py` — edit them to point at your own files.

### 1. SRGNN results pickle — `results_path`

Default: `/storage/home/yml5822/work/graphnet_work/SRGNN/Step1_cls_100k_IC91_numu.pkl`

A pickled dict with the structure:

```python
{
    "event_results": {
        <event_no:int>: {
            # Truth
            "energy":        float,            # GeV
            "zenith":        float,            # radians (arrival direction)
            "azimuth":       float,            # radians
            "pid":           int,              # PDG code
            "vertex_x":      float,            # meters
            "vertex_y":      float,
            "vertex_z":      float,

            # IC86 hits — array of (x, y, z, ...) per pulse
            "ic86_hits":     np.ndarray,       # shape (N_ic86, >=3)

            # Active Upgrade PMT hits (truth-level "on" PMTs)
            "active_pmt_xyz":          np.ndarray,  # (N_active, 3)
            "active_pmt_strings":      np.ndarray,  # (N_active,) int
            "active_pmt_dom_numbers":  np.ndarray,  # (N_active,) int
            "active_pmt_pmt_numbers":  np.ndarray,  # (N_active,) int
            "active_pmt_preds":        np.ndarray,  # (N_active,) float, BCE — SRGNN mode only

            # Inactive Upgrade PMTs sampled by the model (SRGNN mode only)
            "inactive_pmt_xyz":          np.ndarray,  # (N_inactive, 3)
            "inactive_pmt_strings":      np.ndarray,
            "inactive_pmt_dom_numbers":  np.ndarray,
            "inactive_pmt_pmt_numbers":  np.ndarray,
            "inactive_pmt_preds":        np.ndarray,  # (N_inactive,) float, BCE
        },
        ...
    }
}
```

The `(string, dom_number, pmt_number)` triplets are used as keys to look up
each PMT's xyz + orientation in the geometry table below.

### 2. PMT geometry — `pmt_geometry_path`

Default: `/storage/group/dfc13/default/ymliu5822/upgrade/pmt_geometry_IC91.npy`

A NumPy array of shape `(N_pmts, 9)` with columns:

```
[ string, dom_number, pmt_number, x, y, z, pmt_dir_x, pmt_dir_y, pmt_dir_z ]
```

Strings 87 and 92 are filtered out at load time. The script auto-classifies
DOMs by PMT count: 24 → mDOM, 2 → D-Egg, 1 → PDOM.

### 3. Detector geometry (loaded by `load_geometry()` in the parent module)

Three NumPy arrays under
`/storage/group/dfc13/default/ymliu5822/upgrade/`:

- `coord_str_OM_IC86.npy`  — shape `(5160, 5)`: `x, y, z, string, om`
- `coord_str_OM_IC93.npy`  — shape `(11439, 5)`: `x, y, z, string, om` (uses
  0-based string numbering; feature string = geo string + 1)
- `ICU_PMT_pos.npy`        — shape `(10218, 3)`: `x, y, z` for each Upgrade
  PMT

These are the standard IceCube/Upgrade geometry arrays already used elsewhere
in the SRGNN repo.

## Customization

Common knobs in `generate_event_display.py`:

- `event_keys = list(event_results.keys())[:100]` — change `100` to render
  more / fewer events.
- `THRESHOLDS = [0.3, 0.7, 0.9]` — discrete thresholds pre-rendered into the
  3D scene (the slider then interpolates).
- `VERTEX_BASE_SIZE = 12.0` — half-extent of the vertex diamond in meters.
- `EXCLUDED_STRINGS = {87, 92}` — strings hidden from the display.
- `output_path` — where the HTML file is written.
