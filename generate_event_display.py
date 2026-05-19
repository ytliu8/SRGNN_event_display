"""
Generate .html — extends v1 with click-to-expand DOM detail panel.
Clicking an Upgrade PMT in the main 3D plot opens a zoomed-in view of that
DOM's individual PMTs, color-coded by status, with orientation cones.

This file builds the per-event data; the HTML/CSS/JS template lives in
`event_display_template.py`.
"""
import argparse
import os
import sys
sys.path.insert(0, "/storage/home/yml5822/work/graphnet/SRGNN")

import json
import numpy as np
from scipy.spatial import cKDTree
import plotly.graph_objects as go
from event_display import load_results, load_geometry, plot_event_3d
from symbol_shapes import _build_bubble_trail
from event_display_template import build_html

_parser = argparse.ArgumentParser(description="Generate SRGNN/vanilla event display HTML")
_parser.add_argument(
    "--SRGNN",
    action="store_true",
    dest="srgnn",
    help="Include all inactive PMT positions and BCE prediction scores. "
         "Default is vanilla: only active-hit PMT positions are shown.",
)
_args = _parser.parse_args()
SRGNN = _args.srgnn

results_path = "/storage/home/yml5822/work/graphnet_work/SRGNN/Step1_cls_100k_IC91_nue.pkl"
output_path = (
    "/storage/home/yml5822/work/graphnet/SRGNN/event_display/output/SRGNN_event_display_nue.html"
    if SRGNN else
    "/storage/home/yml5822/work/graphnet/SRGNN/event_display/output/event_display_nue.html"
)
pmt_geometry_path = "/storage/group/dfc13/default/ymliu5822/upgrade/pmt_geometry_IC91.npy"
print(f"Mode: {'SRGNN (with inactive PMTs + BCE scores)' if SRGNN else 'vanilla (active hits only)'}")

# ── Numpy-safe JSON converter ──────────────────────────────────────────────
def convert(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert(v) for v in obj]
    return obj

# ── Load data ──────────────────────────────────────────────────────────────
print("Loading results...")
data = load_results(results_path)
event_results = data["event_results"]
event_keys = list(event_results.keys())[:100]

print("Loading geometry...")
ic86_geo, ic93_geo, _ = load_geometry()
# Exclude strings 87 and 92 from the 3D display.
# ic93_geo uses 0-based string numbering (feature string = geo string + 1),
# so feature strings {87, 92} correspond to geo strings {86, 91}.
ic93_geo = ic93_geo[~np.isin(ic93_geo[:, 3].astype(int), [86, 91])]

# ── Load pmt_geometry.npy and group PMTs by (string, dom_number) ─────────
# Columns: [string, dom_number, pmt_number, x, y, z, pmt_dir_x, pmt_dir_y, pmt_dir_z]
print("Loading PMT geometry from pmt_geometry.npy...")
geo_table = np.load(pmt_geometry_path)
# Exclude strings 87 and 92 (and any of their PMTs) from the 3D event display
EXCLUDED_STRINGS = {87, 92}
_keep_mask = ~np.isin(geo_table[:, 0].astype(int), list(EXCLUDED_STRINGS))
geo_table = geo_table[_keep_mask]
geo_xyz = geo_table[:, 3:6]       # xyz for KDTree matching
geo_orient = geo_table[:, 6:9]    # true PMT orientations
geo_strings = geo_table[:, 0].astype(int)
geo_dom_nums = geo_table[:, 1].astype(int)
geo_pmt_nums = geo_table[:, 2].astype(int)

pmt_tree = cKDTree(geo_xyz)

# Build lookup: (string, dom_number, pmt_number) -> geo row index
pmt_key_to_geo_idx = {}
for i in range(len(geo_table)):
    pmt_key_to_geo_idx[(geo_strings[i], geo_dom_nums[i], geo_pmt_nums[i])] = i

# Group PMTs into DOMs by (string, dom_number)
from collections import defaultdict
dom_groups = defaultdict(list)  # (string, dom_number) -> [geo_row_index, ...]
for i in range(len(geo_table)):
    dom_groups[(geo_strings[i], geo_dom_nums[i])].append(i)

# Build structured DOM list
doms = []
pmt_to_dom = {}  # geo row index -> dom_id
for (string, dom_num), pmt_idxs in sorted(dom_groups.items()):
    dom_id = len(doms)
    n = len(pmt_idxs)
    center = geo_xyz[pmt_idxs].mean(axis=0)
    if n == 24:
        dom_type = "mDOM"
    elif n == 2:
        dom_type = "D-Egg"
    elif n == 1:
        dom_type = "PDOM"
    else:
        dom_type = f"other({n})"
    doms.append({
        "dom_id": dom_id,
        "pmt_indices": pmt_idxs,
        "pmt_numbers": [int(geo_pmt_nums[i]) for i in pmt_idxs],
        "center": center,
        "n_pmts": n,
        "dom_type": dom_type,
        "string": int(string),
        "dom_number": int(dom_num),
    })
    for pi in pmt_idxs:
        pmt_to_dom[pi] = dom_id

# Build serializable DOM geometry for the HTML
all_doms_data = []
for dom in doms:
    center = dom["center"]
    pmt_idxs = dom["pmt_indices"]
    pmt_xyz = geo_xyz[pmt_idxs]
    rel_xyz = pmt_xyz - center  # relative positions in meters

    # Use real PMT orientations from the geometry table
    orientations = geo_orient[pmt_idxs]

    all_doms_data.append({
        "dom_id": dom["dom_id"],
        "center": [round(float(c), 3) for c in center],
        "dom_type": dom["dom_type"],
        "n_pmts": dom["n_pmts"],
        "string": dom["string"],
        "dom_number": dom["dom_number"],
        "pmt_numbers": dom["pmt_numbers"],
        "pmt_global_indices": pmt_idxs,
        # Convert to cm for the detail view
        "pmt_rel_cm": [[round(float(v * 100), 2) for v in row] for row in rel_xyz],
        "pmt_orient": [[round(float(v), 4) for v in row] for row in orientations],
    })

n_mdom = sum(1 for d in doms if d['dom_type'] == 'mDOM')
n_degg = sum(1 for d in doms if d['dom_type'] == 'D-Egg')
n_pdom = sum(1 for d in doms if d['dom_type'] == 'PDOM')
n_other = sum(1 for d in doms if d['dom_type'] not in ('mDOM', 'D-Egg', 'PDOM'))
print(f"  {len(doms)} DOMs: {n_mdom} mDOM, {n_degg} D-Egg, {n_pdom} PDOM, {n_other} other")

# ── Per-event: build plots + DOM status data ───────────────────────────────
events_info = []
events_plotly_json = {}
dom_event_data = {}  # { event_no_str: { dom_id_str: { pmt_status: [...], pmt_preds: [...] } } }
pmt_event_data = {}  # { event_no_str: { active: [[x,y,z,pred], ...], inactive: [[x,y,z,pred], ...] } }
# Vertex coords per event — used by client-side JS to rebuild the diamond
# with per-axis half-extents that compensate for the scene's axis aspect in
# the zoom view, so the diamond looks identical in both views.
vertex_info = {}
VERTEX_BASE_SIZE = 12.0  # full-view diamond half-extent (meters)

THRESHOLDS = [0.3, 0.7, 0.9]

for eno in event_keys:
    evt = event_results[eno]
    zen_deg = np.degrees(evt["zenith"]) if not np.isnan(evt["zenith"]) else float("nan")
    azi_deg = np.degrees(evt["azimuth"]) if not np.isnan(evt.get("azimuth", float("nan"))) else float("nan")
    pid_val = evt.get("pid", float("nan"))
    info = {
        "event_no": int(eno),
        "energy": round(float(evt["energy"]), 1),
        "zenith": round(float(zen_deg), 1),
        "azimuth": round(float(azi_deg), 1),
        "pid": int(pid_val) if not np.isnan(pid_val) else 0,
        "ic86_hits": int(evt["ic86_hits"].shape[0]),
        "upgrade_hits": int(evt["active_pmt_xyz"].shape[0]),
        "inactive_pmts": int(evt["inactive_pmt_xyz"].shape[0]),
    }
    events_info.append(info)

    # ── Build 3D plot ──
    fig, _ = plot_event_3d(evt, ic86_geo, ic93_geo, geo_xyz)

    # ── Interaction vertex (cyan dot with yellow outline, 2 sizes bigger
    # than the active-PMT dots) ──
    vx = evt.get("vertex_x", float("nan"))
    vy = evt.get("vertex_y", float("nan"))
    vz = evt.get("vertex_z", float("nan"))
    if not (np.isnan(vx) or np.isnan(vy) or np.isnan(vz)):
        vertex_info[str(eno)] = [float(vx), float(vy), float(vz)]
        fig.add_trace(go.Scatter3d(
            x=[float(vx)], y=[float(vy)], z=[float(vz)],
            mode='markers',
            marker=dict(
                symbol='square',
                size=7,                          # active dots are size 5
                color='#ffff00',                 # bright yellow (uniform)
                line=dict(color='#ffff00', width=0),
            ),
            name='Vertex',
            legendgroup='vertex',
            showlegend=True,
            hovertemplate=(
                f'Vertex<br>x={float(vx):.1f}'
                f'<br>y={float(vy):.1f}'
                f'<br>z={float(vz):.1f}<extra></extra>'
            ),
        ))

        # ── Neutrino direction (thin dashed magenta line through vertex) ──
        # IceCube convention: zenith/azimuth describe the *arrival* direction
        # (where the ν came FROM). The propagation unit vector is the
        # opposite: -(sinθ cosφ, sinθ sinφ, cosθ).
        zen = evt.get("zenith", float("nan"))
        azi = evt.get("azimuth", float("nan"))
        if not (np.isnan(zen) or np.isnan(azi)):
            sz_, cz_ = np.sin(zen), np.cos(zen)
            sa_, ca_ = np.sin(azi), np.cos(azi)
            dir_x, dir_y, dir_z = -sz_ * ca_, -sz_ * sa_, -cz_
            L = 800.0  # half-length (m) — long enough to span the detector
            x0, x1 = float(vx) - L * dir_x, float(vx) + L * dir_x
            y0, y1 = float(vy) - L * dir_y, float(vy) + L * dir_y
            z0, z1 = float(vz) - L * dir_z, float(vz) + L * dir_z

            nu_hover = (
                f'ν direction<br>zenith={np.degrees(zen):.1f}°'
                f'<br>azimuth={np.degrees(azi):.1f}°<extra></extra>'
            )
            fig.add_trace(go.Scatter3d(
                x=[x0, x1], y=[y0, y1], z=[z0, z1],
                mode='lines',
                line=dict(color='#ff00ff', width=2, dash='dot'),
                name='Neutrino direction', legendgroup='nu_dir',
                showlegend=True, hovertemplate=nu_hover,
            ))

    # ── Match event PMTs to geo table indices using (string, dom, pmt) keys ──
    # Active PMTs
    active_global = []
    act_strings = evt.get("active_pmt_strings", np.array([]))
    act_doms = evt.get("active_pmt_dom_numbers", np.array([]))
    act_pmts = evt.get("active_pmt_pmt_numbers", np.array([]))
    for s, d, p in zip(act_strings, act_doms, act_pmts):
        gi = pmt_key_to_geo_idx.get((int(s), int(d), int(p)), -1)
        active_global.append(gi)

    # Inactive PMTs (only sampled in SRGNN mode)
    inactive_global = []
    inactive_preds_arr = np.array([])
    active_preds_arr_raw = np.array([])
    if SRGNN:
        inact_strings = evt.get("inactive_pmt_strings", np.array([]))
        inact_doms = evt.get("inactive_pmt_dom_numbers", np.array([]))
        inact_pmts = evt.get("inactive_pmt_pmt_numbers", np.array([]))
        for s, d, p in zip(inact_strings, inact_doms, inact_pmts):
            gi = pmt_key_to_geo_idx.get((int(s), int(d), int(p)), -1)
            inactive_global.append(gi)

        inactive_preds_arr = evt.get("inactive_pmt_preds", np.array([]))
        active_preds_arr_raw = evt.get("active_pmt_preds", np.array([]))

    # PMT prediction scores (continuous BCE scores) — empty in vanilla
    inactive_preds = inactive_preds_arr
    active_preds = active_preds_arr_raw

    # ── Per-event PMT positions + predictions + orientations for dynamic threshold ──
    # Each entry: [x, y, z, pred, ox, oy, oz, dom_id]
    # In vanilla mode there are no predictions, so we fix pred=1.0 for active
    # PMTs (above any threshold) and skip inactive PMTs entirely.
    if SRGNN:
        active_pred_iter = list(active_preds_arr_raw)
    else:
        active_pred_iter = [1.0] * len(active_global)

    evt_active_pmts = []
    for gi, pred in zip(active_global, active_pred_iter):
        if gi >= 0:
            x, y, z = geo_xyz[gi]
            ox, oy, oz = geo_orient[gi]
            did = pmt_to_dom.get(int(gi), -1)
            evt_active_pmts.append([round(float(x), 2), round(float(y), 2),
                                    round(float(z), 2), round(float(pred), 4),
                                    round(float(ox), 4), round(float(oy), 4), round(float(oz), 4),
                                    int(did)])
    evt_inactive_pmts = []
    if SRGNN:
        for gi, pred in zip(inactive_global, inactive_preds_arr):
            if gi >= 0:
                x, y, z = geo_xyz[gi]
                ox, oy, oz = geo_orient[gi]
                did = pmt_to_dom.get(int(gi), -1)
                evt_inactive_pmts.append([round(float(x), 2), round(float(y), 2),
                                          round(float(z), 2), round(float(pred), 4),
                                          round(float(ox), 4), round(float(oy), 4), round(float(oz), 4),
                                          int(did)])
    pmt_event_data[str(eno)] = {"active": evt_active_pmts, "inactive": evt_inactive_pmts}

    # ── Inject customdata into Upgrade traces (via plotly figure object) ──
    active_set = set(int(g) for g in active_global)
    inactive_set = set(int(g) for g in inactive_global)

    for trace in fig.data:
        name = trace.name or ""
        if name in ("Upgrade PMT Hits (true)", "Inactive Upgrade PMTs") or name.startswith("Inactive (thr=") or name.startswith("Active (thr="):
            # Access x/y/z as numpy arrays from the plotly trace object
            tx = np.array(trace.x, dtype=float)
            ty = np.array(trace.y, dtype=float)
            tz = np.array(trace.z, dtype=float)
            if len(tx) == 0:
                continue
            trace_xyz = np.column_stack([tx, ty, tz])
            # Filter out any NaN/Inf rows before KDTree query
            finite_mask = np.isfinite(trace_xyz).all(axis=1)
            customdata = [[-1, -1]] * len(trace_xyz)
            if finite_mask.any():
                _, match_idx = pmt_tree.query(trace_xyz[finite_mask])
                finite_indices = np.where(finite_mask)[0]
                for fi, mi in zip(finite_indices, match_idx):
                    customdata[fi] = [int(mi), pmt_to_dom.get(int(mi), -1)]
            trace.customdata = customdata

    # Serialize via JSON (handles binary encoding properly)
    fig_json = json.loads(fig.to_json())
    events_plotly_json[str(eno)] = fig_json

    # ── Build per-DOM status for this event ──
    # Collect all DOMs that participate in this event
    involved_dom_ids = set()
    for gi in active_global:
        if int(gi) in pmt_to_dom:
            involved_dom_ids.add(pmt_to_dom[int(gi)])
    for gi in inactive_global:
        if int(gi) in pmt_to_dom:
            involved_dom_ids.add(pmt_to_dom[int(gi)])

    # Build global index -> prediction score maps (only meaningful in SRGNN mode)
    inactive_pred_map = {}
    active_pred_map = {}
    if SRGNN:
        if len(inactive_preds) > 0 and len(inactive_global) == len(inactive_preds):
            for gi, pred in zip(inactive_global, inactive_preds):
                inactive_pred_map[int(gi)] = float(pred)
        if len(active_preds) > 0 and len(active_global) == len(active_preds):
            for gi, pred in zip(active_global, active_preds):
                active_pred_map[int(gi)] = float(pred)

    evt_dom_statuses = {}
    for dom_id in involved_dom_ids:
        dom = doms[dom_id]
        pmt_idxs = dom["pmt_indices"]
        roles = []      # 'active', 'inactive', or 'absent'
        preds = []      # BCE confidence score, -1 for absent
        for pi in pmt_idxs:
            if pi in active_set:
                roles.append("active")
                preds.append(round(active_pred_map.get(pi, 1.0), 4))
            elif pi in inactive_set:
                roles.append("inactive")
                preds.append(round(inactive_pred_map.get(pi, 0.0), 4))
            else:
                roles.append("absent")
                preds.append(-1.0)

        n_active = sum(1 for r in roles if r == "active")
        n_inactive_total = sum(1 for r in roles if r == "inactive")
        n_absent = sum(1 for r in roles if r == "absent")

        evt_dom_statuses[str(dom_id)] = {
            "pmt_role": roles,
            "pmt_preds": preds,
            "n_active": n_active,
            "n_inactive_total": n_inactive_total,
            "n_absent": n_absent,
        }

    dom_event_data[str(eno)] = evt_dom_statuses

# ── Build HTML ─────────────────────────────────────────────────────────────
print("Writing HTML...")

events_info.sort(key=lambda x: x["energy"])

rows_html = ""
for i, info in enumerate(events_info):
    eno = info["event_no"]
    hidden_style = ' style="display:none"' if i >= 10 else ''
    inactive_cell = (
        f'      <td class="inactive">{info["inactive_pmts"]}</td>\n'
        if SRGNN else ""
    )
    rows_html += f"""    <tr data-event="{eno}" data-pid="{info['pid']}" data-abs-pid="{abs(info['pid'])}" onclick="showEvent('{eno}')" class="{'selected' if i == 0 else ''}"{hidden_style}>
      <td class="evt-num">{eno}</td>
      <td class="energy">{info['energy']}</td>
      <td class="pid">{info['pid']}</td>
      <td class="zenith">{info['zenith']}</td>
      <td class="azimuth">{info['azimuth']}</td>
      <td class="hits">{info['ic86_hits']}</td>
      <td class="upgrade">{info['upgrade_hits']}</td>
{inactive_cell}      <td class="link-icon">&#x25BC;</td>
    </tr>
"""

all_figures_json = json.dumps(events_plotly_json)
all_doms_json = json.dumps(all_doms_data)
dom_event_json = json.dumps(dom_event_data)
pmt_event_json = json.dumps(pmt_event_data)
vertex_info_json = json.dumps(vertex_info)
first_event = str(events_info[0]["event_no"])
total_pages_initial = max(1, (len(events_info) + 9) // 10)

html = build_html(
    results_path=results_path,
    events_info=events_info,
    rows_html=rows_html,
    all_figures_json=all_figures_json,
    all_doms_json=all_doms_json,
    dom_event_json=dom_event_json,
    pmt_event_json=pmt_event_json,
    vertex_info_json=vertex_info_json,
    vertex_base_size=VERTEX_BASE_SIZE,
    first_event=first_event,
    total_pages_initial=total_pages_initial,
    srgnn=SRGNN,
)

with open(output_path, "w") as f:
    f.write(html)

print(f"Done! Saved to {output_path}")
