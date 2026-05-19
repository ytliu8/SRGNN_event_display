"""
HTML template for the SRGNN event display.

`build_html()` returns the full HTML document as a string, given the
serialized event data produced by `generate_event_display.py`.
"""
import os


def build_html(
    *,
    results_path,
    events_info,
    rows_html,
    all_figures_json,
    all_doms_json,
    dom_event_json,
    pmt_event_json,
    vertex_info_json,
    vertex_base_size,
    first_event,
    total_pages_initial,
    srgnn=False,
):
    inactive_th = "<th>Added Inactive PMTs</th>" if srgnn else ""
    bce_slider_html = (
        """  <div id="thr-control">
    <label>BCE confidence:</label>
    <input type="range" id="thr-slider" min="0" max="1" step="0.01" value="0.50"
           oninput="onThrChange(this.value)">
    <input type="number" id="thr-value" min="0" max="1" step="0.01" value="0.50"
           onchange="onThrChange(this.value)">
    <span id="thr-counts"></span>
  </div>"""
        if srgnn else ""
    )
    click_hint = (
        "Click any Upgrade PMT marker (green, white, red, or gray) to inspect the DOM detail below. "
        "The magenta line shows the neutrino direction through the vertex."
        if srgnn else
        "Click any Upgrade PMT marker to inspect the DOM detail below. "
        "The magenta line shows the neutrino direction through the vertex."
    )
    page_subtitle_action = (
        "Click row for event, click Upgrade PMT for DOM detail"
        if srgnn else
        "Click row for event"
    )
    srgnn_js_flag = "true" if srgnn else "false"
    body_class = "srgnn-mode" if srgnn else "vanilla-mode"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SRGNN Event Display</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #000000 0%, #050510 40%, #0a0a14 70%, #000000 100%);
    background-attachment: fixed;
    color: #ccd6f6;
    padding: 40px 20px;
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
  }}
  body::before {{
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
      radial-gradient(ellipse 600px 400px at 20% 20%, rgba(0, 200, 255, 0.04) 0%, transparent 70%),
      radial-gradient(ellipse 500px 500px at 80% 70%, rgba(100, 50, 255, 0.04) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
  }}
  h1 {{
    position: relative; z-index: 1;
    text-align: center;
    color: #00d4ff;
    margin-bottom: 8px;
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-shadow: 0 0 20px rgba(0, 212, 255, 0.3), 0 0 60px rgba(0, 212, 255, 0.1);
  }}
  .subtitle {{
    position: relative; z-index: 1;
    text-align: center;
    color: #5a7a9e;
    margin-bottom: 35px;
    font-size: 0.9rem;
    letter-spacing: 0.5px;
  }}
  table {{
    position: relative; z-index: 1;
    width: 100%;
    max-width: 1050px;
    margin: 0 auto;
    border-collapse: separate;
    border-spacing: 0;
    background: rgba(8, 8, 16, 0.9);
    border-radius: 12px;
    overflow: hidden;
    box-shadow:
      0 0 1px rgba(0, 212, 255, 0.3),
      0 4px 30px rgba(0, 0, 0, 0.5),
      inset 0 1px 0 rgba(0, 212, 255, 0.08);
    border: 1px solid rgba(0, 212, 255, 0.12);
    backdrop-filter: blur(10px);
  }}
  thead th {{
    background: rgba(12, 12, 20, 0.95);
    color: #00d4ff;
    padding: 16px 20px;
    text-align: left;
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    border-bottom: 1px solid rgba(0, 212, 255, 0.15);
  }}
  tbody tr {{
    cursor: pointer;
    transition: all 0.2s ease;
    border-bottom: 1px solid rgba(30, 60, 100, 0.3);
  }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{
    background: rgba(0, 212, 255, 0.06);
    box-shadow: inset 3px 0 0 #00d4ff;
  }}
  tbody tr.selected {{
    background: rgba(0, 212, 255, 0.1);
    box-shadow: inset 3px 0 0 #00d4ff;
  }}
  tbody td {{
    padding: 14px 20px;
    font-size: 0.95rem;
    font-variant-numeric: tabular-nums;
  }}
  td.evt-num {{
    color: #00d4ff;
    font-weight: 700;
    font-family: 'Courier New', monospace;
    font-size: 1rem;
  }}
  td.energy {{ color: #ffa857; }}
  td.zenith {{ color: #64ffda; }}
  td.azimuth {{ color: #64d2ff; }}
  td.pid {{ color: #f7c873; font-family: 'Courier New', monospace; }}
  td.hits {{ color: #7ee787; }}
  td.upgrade {{ color: #ff6b81; }}
  td.inactive {{ color: #c792ea; }}
  td.link-icon {{
    color: rgba(0, 212, 255, 0.25);
    font-size: 1.1rem;
    transition: all 0.2s;
  }}
  tbody tr:hover td.link-icon,
  tbody tr.selected td.link-icon {{
    color: #00d4ff;
    text-shadow: 0 0 8px rgba(0, 212, 255, 0.5);
  }}

  #viewer-section {{
    position: relative; z-index: 1;
    max-width: 1150px;
    margin: 30px auto 0;
  }}
  #viewer-title {{
    color: #00d4ff;
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }}
  #plot-container {{
    width: 100%;
    height: 880px;
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 10px;
    overflow: hidden;
    background: #000;
  }}
  .click-hint {{
    color: #5a7a9e;
    font-size: 0.85rem;
    margin-top: 8px;
    letter-spacing: 0.3px;
  }}

  /* DOM detail panel */
  #dom-detail-section {{
    position: relative; z-index: 1;
    max-width: 1150px;
    margin: 30px auto 0;
    display: none;
    animation: fadeIn 0.3s ease;
  }}
  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  #dom-detail-title {{
    color: #00d4ff;
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }}
  #dom-info {{
    background: rgba(8, 8, 16, 0.9);
    border: 1px solid rgba(0, 212, 255, 0.12);
    border-radius: 10px;
    padding: 16px 24px;
    margin-bottom: 14px;
    font-size: 0.92rem;
    line-height: 1.7;
    backdrop-filter: blur(10px);
  }}
  #dom-info .label {{ color: #5a7a9e; }}
  #dom-info .val {{ font-weight: 600; }}
  #dom-info .val-hit {{ color: #69d2a0; }}
  #dom-info .val-inactive {{ color: #888; }}
  #dom-info .val-predicted {{ color: #ff6b81; }}
  #dom-info .val-absent {{ color: #444; }}
  #dom-detail-container {{
    width: 100%;
    height: 550px;
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 10px;
    overflow: hidden;
    background: #000;
  }}

  .footer {{
    position: relative; z-index: 1;
    text-align: center;
    color: #2a4a6b;
    margin-top: 28px;
    font-size: 0.8rem;
    letter-spacing: 1px;
  }}

  /* Threshold control */
  #thr-control {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    padding: 10px 16px;
    background: rgba(8, 8, 16, 0.9);
    border: 1px solid rgba(0, 212, 255, 0.12);
    border-radius: 8px;
    backdrop-filter: blur(10px);
  }}
  #thr-control label {{
    color: #00d4ff;
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    white-space: nowrap;
  }}
  #thr-slider {{
    flex: 1;
    max-width: 300px;
    accent-color: #00d4ff;
    height: 6px;
    -webkit-appearance: none;
    appearance: none;
    background: linear-gradient(to right, #1a3550 0%, #00d4ff 50%, #1a3550 100%);
    border: 1px solid rgba(0, 212, 255, 0.4);
    border-radius: 4px;
    outline: none;
    box-shadow: 0 0 6px rgba(0, 212, 255, 0.25);
  }}
  #thr-slider::-webkit-slider-thumb {{
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #00d4ff;
    border: 2px solid #08131f;
    cursor: pointer;
    box-shadow: 0 0 8px rgba(0, 212, 255, 0.7);
  }}
  #thr-slider::-moz-range-thumb {{
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #00d4ff;
    border: 2px solid #08131f;
    cursor: pointer;
    box-shadow: 0 0 8px rgba(0, 212, 255, 0.7);
  }}
  #thr-slider::-moz-range-track {{
    height: 6px;
    background: linear-gradient(to right, #1a3550 0%, #00d4ff 50%, #1a3550 100%);
    border-radius: 4px;
  }}
  #thr-value {{
    width: 60px;
    background: rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 4px;
    color: #00d4ff;
    font-size: 0.95rem;
    font-weight: 600;
    text-align: center;
    padding: 4px;
    font-family: 'Courier New', monospace;
  }}
  #thr-counts {{
    color: #5a7a9e;
    font-size: 0.85rem;
    margin-left: 8px;
  }}
  #thr-counts .act {{ color: #00ff66; font-weight: 600; }}
  #thr-counts .inact {{ color: #ff2060; font-weight: 600; }}

  #pid-filter-control {{
    position: relative; z-index: 1;
    max-width: 1050px;
    margin: 0 auto 14px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    background: rgba(8, 8, 16, 0.9);
    border: 1px solid rgba(0, 212, 255, 0.12);
    border-radius: 8px;
    backdrop-filter: blur(10px);
  }}
  #pid-filter-control label {{
    color: #00d4ff;
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    white-space: nowrap;
  }}
  #pid-filter {{
    background: rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 4px;
    color: #00d4ff;
    font-size: 0.9rem;
    font-weight: 600;
    padding: 5px 10px;
    font-family: 'Courier New', monospace;
    cursor: pointer;
  }}
  #pid-filter-count {{
    color: #5a7a9e;
    font-size: 0.85rem;
    margin-left: 8px;
  }}

  #pagination-control {{
    position: relative; z-index: 1;
    max-width: 1050px;
    margin: 14px auto 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 10px 16px;
    background: rgba(8, 8, 16, 0.9);
    border: 1px solid rgba(0, 212, 255, 0.12);
    border-radius: 8px;
    backdrop-filter: blur(10px);
  }}
  #pagination-control button {{
    background: rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 4px;
    color: #00d4ff;
    font-size: 0.9rem;
    font-weight: 600;
    padding: 6px 14px;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    cursor: pointer;
    transition: all 0.2s;
  }}
  #pagination-control button:hover:not(:disabled) {{
    background: rgba(0, 212, 255, 0.15);
    box-shadow: 0 0 8px rgba(0, 212, 255, 0.3);
  }}
  #pagination-control button:disabled {{
    opacity: 0.3;
    cursor: not-allowed;
  }}
  #pagination-control #page-info {{
    color: #5a7a9e;
    font-size: 0.9rem;
    font-variant-numeric: tabular-nums;
    min-width: 140px;
    text-align: center;
  }}
  #pagination-control #page-info .current {{
    color: #00d4ff;
    font-weight: 700;
  }}
  #pagination-control input#page-jump {{
    width: 55px;
    background: rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 4px;
    color: #00d4ff;
    font-size: 0.9rem;
    font-weight: 600;
    text-align: center;
    padding: 5px;
    font-family: 'Courier New', monospace;
  }}
</style>
</head>
<body class="{body_class}">

<h1>SRGNN Event Display</h1>
<p class="subtitle">{os.path.basename(results_path)} &mdash; Total Events: {len(events_info)} &mdash; {page_subtitle_action}</p>

<div id="pid-filter-control">
  <label>Filter by |PID|:</label>
  <select id="pid-filter" onchange="applyPidFilter()">
    <option value="all">All</option>
    <option value="12">12 (&nu;<sub>e</sub>)</option>
    <option value="14">14 (&nu;<sub>&mu;</sub>)</option>
    <option value="16">16 (&nu;<sub>&tau;</sub>)</option>
  </select>
  <span id="pid-filter-count"></span>
</div>

<table>
  <thead>
    <tr>
      <th>Event ID</th>
      <th>Energy (GeV)</th>
      <th>PID</th>
      <th>Zenith (&deg;)</th>
      <th>Azimuth (&deg;)</th>
      <th>IC86 Hits</th>
      <th>Upgrade Hits</th>
      {inactive_th}
      <th></th>
    </tr>
  </thead>
  <tbody>
{rows_html}  </tbody>
</table>

<div id="pagination-control">
  <button id="first-page" onclick="goToPage(1)" disabled>&laquo; First</button>
  <button id="prev-page" onclick="goToPage(currentPage - 1)" disabled>&lsaquo; Prev</button>
  <span id="page-info">Page <span class="current" id="current-page">1</span> of <span id="total-pages">{total_pages_initial}</span></span>
  <button id="next-page" onclick="goToPage(currentPage + 1)">Next &rsaquo;</button>
  <button id="last-page" onclick="goToPage(totalPages)">Last &raquo;</button>
  <span style="color: #5a7a9e; font-size: 0.85rem; margin-left: 12px;">Jump to:</span>
  <input type="number" id="page-jump" min="1" max="{total_pages_initial}" value="1"
         onchange="goToPage(parseInt(this.value, 10))">
</div>

<div id="viewer-section">
  <div id="viewer-title">3D Display &mdash; Event {first_event}</div>
  <p class="click-hint">{click_hint}</p>
{bce_slider_html}
  <div id="plot-container"></div>
</div>

<div id="dom-detail-section">
  <div id="dom-detail-title">DOM Detail</div>
  <div id="dom-info"></div>
  <div id="dom-detail-container"></div>
</div>

<p class="footer">Generated by SRGNN Event Display</p>

<script>
var SRGNN_MODE = {srgnn_js_flag};
var ALL_FIGURES = {all_figures_json};
var ALL_DOMS = {all_doms_json};
var DOM_EVENT_DATA = {dom_event_json};
var PMT_EVENT_DATA = {pmt_event_json};
var VERTEX_INFO = {vertex_info_json};
var VERTEX_BASE_SIZE = {vertex_base_size};
var currentEvent = null;
var currentDomId = null;
var baseTraceCount = 0;
var currentView = 'full';  // 'full' | 'zoom' — tracks active Plotly view button
var PAGE_SIZE = 10;
var currentPage = 1;
var totalPages = {total_pages_initial};

// ── Vertex diamond: per-view axis-compensating size ──────────────────────
// Scene aspectmode='data' locks its aspectratio at page load (from the
// initial full-detector ranges, which are a cube). When the "Zoom to
// Upgrade" button later relayouts only the axis ranges, per-axis visual
// scaling diverges: 1 m along z no longer covers the same pixels as 1 m
// along x/y, so a symmetric mesh built in data coords stretches in the
// horizontal axes. To keep the diamond visually cubic AND the same
// on-screen size across views, rebuild the 14 mesh vertices with per-
// axis half-extents proportional to each axis's range fraction relative
// to the full-view range — so visual_extent_k = size_k / range_k stays
// constant in pixels.
function getViewSpans(viewName) {{
  var fig = ALL_FIGURES[currentEvent];
  if (!fig || !fig.layout || !fig.layout.updatemenus) return null;
  var needle = (viewName === 'zoom') ? 'Zoom' : 'Full';
  for (var i = 0; i < fig.layout.updatemenus.length; i++) {{
    var menu = fig.layout.updatemenus[i];
    for (var j = 0; j < menu.buttons.length; j++) {{
      var btn = menu.buttons[j];
      if (btn.label && btn.label.indexOf(needle) >= 0) {{
        var a = btn.args[0];
        var xr = a['scene.xaxis.range'], yr = a['scene.yaxis.range'], zr = a['scene.zaxis.range'];
        if (!xr || !yr || !zr) return null;
        return {{ x: xr[1] - xr[0], y: yr[1] - yr[0], z: zr[1] - zr[0] }};
      }}
    }}
  }}
  return null;
}}
function findVertexTraceIndex() {{
  var plotEl = document.getElementById('plot-container');
  if (!plotEl.data) return -1;
  for (var i = 0; i < plotEl.data.length; i++) {{
    var t = plotEl.data[i];
    if (t && t.name === 'Vertex' && t.type === 'mesh3d') return i;
  }}
  return -1;
}}
function applyDiamondForView(viewName) {{
  var plotEl = document.getElementById('plot-container');
  var vi = findVertexTraceIndex();
  if (vi < 0 || !currentEvent) return;
  var v = VERTEX_INFO[currentEvent];
  if (!v) return;
  var full = getViewSpans('full');
  var view = getViewSpans(viewName);
  var sx = VERTEX_BASE_SIZE, sy = VERTEX_BASE_SIZE, sz = VERTEX_BASE_SIZE;
  if (full && view) {{
    sx = VERTEX_BASE_SIZE * view.x / full.x;
    sy = VERTEX_BASE_SIZE * view.y / full.y;
    sz = VERTEX_BASE_SIZE * view.z / full.z;
  }}
  var vx = v[0], vy = v[1], vz = v[2];
  // Vertex order matches Python _build_3d_diamond (6 spike apexes + 8 inner
  // cube corners = 14 vertices). Inner cube half-edge = size / 3.5 per axis.
  // 0..5  apexes: +x, -x, +y, -y, +z, -z
  // 6..13 cube corners, index 6 + (sx*4 + sy*2 + sz) with s* = 0 for +
  var ix = sx / 3.5, iy = sy / 3.5, iz = sz / 3.5;
  var x = [
    vx + sx, vx - sx, vx,      vx,      vx,      vx,
    vx + ix, vx + ix, vx + ix, vx + ix, vx - ix, vx - ix, vx - ix, vx - ix
  ];
  var y = [
    vy,      vy,      vy + sy, vy - sy, vy,      vy,
    vy + iy, vy + iy, vy - iy, vy - iy, vy + iy, vy + iy, vy - iy, vy - iy
  ];
  var z = [
    vz,      vz,      vz,      vz,      vz + sz, vz - sz,
    vz + iz, vz - iz, vz + iz, vz - iz, vz + iz, vz - iz, vz + iz, vz - iz
  ];
  Plotly.restyle(plotEl, {{ x: [x], y: [y], z: [z] }}, [vi]);
}}

// Dynamic status -> color mapping (computed from slider threshold)
var STATUS_COLORS = {{
  'hit':        '#00ff66',   // active PMT with pred >= thr (true positive)
  'hit_below':  '#ffffff',   // active PMT with pred < thr (false negative)
  'predicted':  '#ff0066',   // inactive PMT with pred >= thr (predicted active)
  'inactive':   '#8c8ca0'    // inactive PMT with pred < thr (gray)
}};

var STATUS_LABELS = {{
  'hit':        'Active (pred≥thr)',
  'hit_below':  'Active (pred<thr)',
  'predicted':  'Inactive pred (≥thr)',
  'inactive':   'Inactive (pred<thr)'
}};

function showEvent(eventId) {{
  document.querySelectorAll('tbody tr').forEach(function(r) {{ r.classList.remove('selected'); }});
  var row = document.querySelector('tr[data-event="' + eventId + '"]');
  if (row) row.classList.add('selected');

  document.getElementById('viewer-title').textContent = '3D Display \\u2014 Event ' + eventId;

  // Hide DOM detail when switching events
  document.getElementById('dom-detail-section').style.display = 'none';
  currentDomId = null;

  var fig = ALL_FIGURES[eventId];
  if (fig) {{
    fig.layout.paper_bgcolor = '#000';
    fig.layout.plot_bgcolor = '#000';
    if (fig.layout.scene) {{
      fig.layout.scene.bgcolor = '#000';
    }}
    fig.layout.font = fig.layout.font || {{}};
    fig.layout.font.color = '#ccd6f6';

    // Make legend text slightly larger and bold
    fig.layout.legend = fig.layout.legend || {{}};
    fig.layout.legend.font = fig.layout.legend.font || {{}};
    fig.layout.legend.font.size = 14;
    fig.layout.legend.font.color = '#ccd6f6';
    fig.layout.legend.font.family = '"Segoe UI", Tahoma, sans-serif';
    fig.layout.legend.font.weight = 700;

    // Hide the static "Inactive (thr=" / "Active (thr=" and their bubble trails
    // from the legend — we show those dynamically via the slider below.
    // The "Neutrino direction" magenta line trace is preserved as-is so it
    // shows up in the legend with its own toggle.
    for (var ti = 0; ti < fig.data.length; ti++) {{
      var tn = fig.data[ti].name || "";
      if (tn.indexOf("Inactive (thr=") === 0 || tn.indexOf("Active (thr=") === 0 ||
          tn.indexOf("Orient (inactive pred)") === 0 || tn.indexOf("Orient (active)") === 0) {{
        fig.data[ti].showlegend = false;
      }}
    }}

    Plotly.react('plot-container', fig.data, fig.layout, {{responsive: true}});
    baseTraceCount = fig.data.length;

    // Attach click handler for DOM drill-down
    var plotEl = document.getElementById('plot-container');
    plotEl.removeAllListeners && plotEl.removeAllListeners('plotly_click');
    plotEl.on('plotly_click', function(data) {{
      var pt = data.points[0];
      if (pt.customdata && pt.customdata.length >= 2) {{
        var domId = pt.customdata[1];
        if (domId >= 0) {{
          showDomDetail(domId);
        }}
      }}
    }});

    // Track view changes from the Plotly updatemenu buttons so the vertex
    // diamond can be re-sized to match the new axis aspect.
    plotEl.removeAllListeners && plotEl.removeAllListeners('plotly_buttonclicked');
    plotEl.on('plotly_buttonclicked', function(data) {{
      var label = (data && data.button && data.button.label) || '';
      if (label.indexOf('Zoom') >= 0) {{
        currentView = 'zoom';
      }} else if (label.indexOf('Full') >= 0) {{
        currentView = 'full';
      }} else {{
        return;
      }}
      setTimeout(function() {{ applyDiamondForView(currentView); }}, 0);
    }});
  }}

  document.getElementById('viewer-section').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  currentEvent = eventId;

  // Apply current threshold
  applyThreshold();
}}

function onThrChange(val) {{
  val = parseFloat(val);
  if (isNaN(val)) return;
  val = Math.max(0, Math.min(1, val));
  document.getElementById('thr-slider').value = val;
  document.getElementById('thr-value').value = val.toFixed(2);
  applyThreshold();
}}

// Build bubble trail arrays for a set of PMTs
// pmts: array of [x,y,z,pred,ox,oy,oz], rgb: [r,g,b]
var B_N = 11, B_SP = 1.2;
var B_SZ  = [8.0, 7.0, 6.0, 5.2, 4.4, 3.6, 2.8, 2.1, 1.5, 1.0, 0.5];
var B_AL  = [0.92, 0.82, 0.72, 0.60, 0.48, 0.37, 0.27, 0.18, 0.11, 0.06, 0.02];

function buildBubbleTrace(pmts, rgb, name, legendgroup) {{
  var bx=[], by=[], bz=[], bs=[], bc=[];
  for (var i = 0; i < pmts.length; i++) {{
    var p = pmts[i];
    for (var s = 1; s < B_N; s++) {{
      var d = s * B_SP;
      bx.push(p[0] + p[4]*d);
      by.push(p[1] + p[5]*d);
      bz.push(p[2] + p[6]*d);
      bs.push(B_SZ[s]);
      bc.push('rgba(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ',' + B_AL[s].toFixed(2) + ')');
    }}
  }}
  if (bx.length === 0) return null;
  return {{
    type: 'scatter3d', mode: 'markers',
    x: bx, y: by, z: bz,
    marker: {{ size: bs, color: bc, line: {{ width: 0 }} }},
    name: name, legendgroup: legendgroup, showlegend: false, hoverinfo: 'skip',
  }};
}}

function applyThreshold() {{
  // SRGNN: read the slider; vanilla: there is no slider, treat thr=0 so all
  // active PMTs (pred=1.0) classify as "above threshold".
  var thr;
  if (SRGNN_MODE) {{
    var thrEl = document.getElementById('thr-value');
    if (!thrEl) return;
    thr = parseFloat(thrEl.value);
    if (isNaN(thr)) return;
  }} else {{
    thr = 0;
  }}
  if (!currentEvent) return;

  var plotEl = document.getElementById('plot-container');
  if (!plotEl.data) return;

  // Read the live camera state before any changes
  var savedCamera = null;
  if (plotEl._fullLayout && plotEl._fullLayout.scene && plotEl._fullLayout.scene._scene &&
      plotEl._fullLayout.scene._scene.getCamera) {{
    savedCamera = plotEl._fullLayout.scene._scene.getCamera();
  }} else if (plotEl.layout && plotEl.layout.scene && plotEl.layout.scene.camera) {{
    savedCamera = JSON.parse(JSON.stringify(plotEl.layout.scene.camera));
  }}

  var pmtData = PMT_EVENT_DATA[currentEvent];
  if (!pmtData) return;

  var actAbove = pmtData.active.filter(function(p) {{ return p[3] >= thr; }});
  var actBelow = pmtData.active.filter(function(p) {{ return p[3] < thr; }});
  var inactAbove = pmtData.inactive.filter(function(p) {{ return p[3] >= thr; }});

  // Update counts display (SRGNN only — vanilla has no thr-counts element)
  if (SRGNN_MODE) {{
    var counts = document.getElementById('thr-counts');
    if (counts) {{
      counts.innerHTML =
        'Active: <span class="act">' + actAbove.length + '</span> / ' + pmtData.active.length +
        ' &nbsp; Inactive: <span class="inact">' + inactAbove.length + '</span> / ' + pmtData.inactive.length;
    }}
  }}

  // Build new dynamic traces — we render ALL active PMTs here (both above
  // and below threshold) so that we can hide the base "Upgrade PMT Hits"
  // traces entirely.  This eliminates depth-fighting between the base
  // open-circle trace and the solid overlay at certain camera angles.
  var newTraces = [];

  // Active PMTs ABOVE threshold — solid filled green circles
  if (actAbove.length > 0) {{
    var actName = SRGNN_MODE
      ? ('Active (conf≥' + thr.toFixed(2) + ')')
      : 'Active PMT Hits';
    var actHover = SRGNN_MODE
      ? ('Active pred≥' + thr.toFixed(2) +
         '<br>x=%{{x:.1f}}<br>y=%{{y:.1f}}<br>z=%{{z:.1f}}<extra></extra>')
      : 'Active PMT<br>x=%{{x:.1f}}<br>y=%{{y:.1f}}<br>z=%{{z:.1f}}<extra></extra>';
    newTraces.push({{
      type: 'scatter3d', mode: 'markers',
      x: actAbove.map(function(p) {{ return p[0]; }}),
      y: actAbove.map(function(p) {{ return p[1]; }}),
      z: actAbove.map(function(p) {{ return p[2]; }}),
      customdata: actAbove.map(function(p) {{ return [0, p[7]]; }}),
      marker: {{ size: 5, color: '#00ff66', opacity: 1.0,
                symbol: 'circle',
                line: {{ color: '#20ff80', width: 1 }} }},
      name: actName,
      legendgroup: 'upgrade_hits',
      showlegend: true,
      hovertemplate: actHover,
    }});
    // Bubble trail for active PMTs above threshold (orientation cones)
    var actBubbles = buildBubbleTrace(actAbove, [0, 255, 102], 'Orient (active)', 'upgrade_hits');
    if (actBubbles) newTraces.push(actBubbles);
  }}

  // Active PMTs BELOW threshold — solid filled white circles (SRGNN only; in
  // vanilla every active PMT is above the thr=0 threshold so this list is empty).
  if (SRGNN_MODE && actBelow.length > 0) {{
    newTraces.push({{
      type: 'scatter3d', mode: 'markers',
      x: actBelow.map(function(p) {{ return p[0]; }}),
      y: actBelow.map(function(p) {{ return p[1]; }}),
      z: actBelow.map(function(p) {{ return p[2]; }}),
      customdata: actBelow.map(function(p) {{ return [0, p[7]]; }}),
      marker: {{ size: 6, color: '#ffffff', opacity: 1.0,
                symbol: 'circle',
                line: {{ color: '#ffffff', width: 1 }} }},
      name: 'Active (conf<' + thr.toFixed(2) + ')',
      legendgroup: 'upgrade_hits',
      showlegend: false,
      hovertemplate: 'Active pred<' + thr.toFixed(2) +
        '<br>x=%{{x:.1f}}<br>y=%{{y:.1f}}<br>z=%{{z:.1f}}<extra></extra>',
    }});
  }}

  // Inactive predicted PMTs (SRGNN only — vanilla has no inactive data and
  // we never show grey inactive dots).
  if (SRGNN_MODE && inactAbove.length > 0) {{
    newTraces.push({{
      type: 'scatter3d', mode: 'markers',
      x: inactAbove.map(function(p) {{ return p[0]; }}),
      y: inactAbove.map(function(p) {{ return p[1]; }}),
      z: inactAbove.map(function(p) {{ return p[2]; }}),
      customdata: inactAbove.map(function(p) {{ return [0, p[7]]; }}),
      marker: {{ size: 5, color: '#ff0066', opacity: 0.95,
                line: {{ color: 'rgba(255,255,255,0.4)', width: 1 }} }},
      name: 'Inactive pred (conf≥' + thr.toFixed(2) + ')',
      legendgroup: 'inactive_pred',
      showlegend: true,
      hovertemplate: 'Inactive pred≥' + thr.toFixed(2) +
        '<br>x=%{{x:.1f}}<br>y=%{{y:.1f}}<br>z=%{{z:.1f}}<extra></extra>',
    }});
    var inactBubbles = buildBubbleTrace(inactAbove, [255, 50, 70], 'Orient (inactive pred)', 'inactive_pred');
    if (inactBubbles) newTraces.push(inactBubbles);
  }}

  // Copy base traces but hide the original "Upgrade PMT Hits (true)" trace
  // (replaced by our dynamic red-filled overlay above). In vanilla we ALSO
  // hide "Inactive Upgrade PMTs" so no grey dots appear.
  var baseTraces = [];
  for (var i = 0; i < baseTraceCount; i++) {{
    var t = JSON.parse(JSON.stringify(plotEl.data[i]));
    var tn = t.name || "";
    if (tn === "Upgrade PMT Hits (true)") {{
      t.visible = false;
    }} else if (!SRGNN_MODE && tn === "Inactive Upgrade PMTs") {{
      t.visible = false;
    }}
    baseTraces.push(t);
  }}
  var allTraces = baseTraces.concat(newTraces);

  // Bake the saved camera into the layout so Plotly.react does a single
  // atomic render with no intermediate auto-scale flicker
  var layout = JSON.parse(JSON.stringify(plotEl.layout));
  if (savedCamera) {{
    layout.scene = layout.scene || {{}};
    layout.scene.camera = savedCamera;
  }}

  Plotly.react(plotEl, allTraces, layout);

  // Re-apply per-axis diamond sizing for the active view, since Plotly.react
  // rewrites the vertex trace back to its baked (full-view) coordinates.
  applyDiamondForView(currentView);

  // If DOM detail view is open, re-render it with the new threshold
  // (pass skipScroll=true so the page doesn't jump down to the DOM detail
  // panel every time the user moves the BCE slider — we want to stay in
  // the event 3D view while scrubbing the threshold).
  var detailSection = document.getElementById('dom-detail-section');
  if (currentDomId !== null && detailSection && detailSection.style.display !== 'none') {{
    showDomDetail(currentDomId, true);
  }}
}}

function showDomDetail(domId, skipScroll) {{
  var dom = ALL_DOMS[domId];
  if (!dom) return;
  currentDomId = domId;

  var evtData = DOM_EVENT_DATA[currentEvent];
  var domStatus = evtData ? evtData[String(domId)] : null;

  // Read current slider threshold (vanilla mode has no slider — use 0 so all
  // active PMTs (pred=1.0) classify as 'hit').
  var thrEl = document.getElementById('thr-value');
  var thr = thrEl ? parseFloat(thrEl.value) : 0;
  if (isNaN(thr)) thr = SRGNN_MODE ? 0.5 : 0;

  // ── Build detail 3D plot ──
  var rel = dom.pmt_rel_cm;   // [[dx,dy,dz], ...] in cm
  var orient = dom.pmt_orient; // [[ox,oy,oz], ...]
  var n = dom.n_pmts;

  var roles = domStatus ? domStatus.pmt_role : [];
  var preds = domStatus ? domStatus.pmt_preds : [];

  // Compute dynamic per-PMT status based on slider threshold
  function statusFor(i) {{
    var role = roles[i] || 'absent';
    if (role === 'absent') return 'absent';
    var p = preds[i];
    if (role === 'active') {{
      return (p >= thr) ? 'hit' : 'hit_below';
    }}
    // role === 'inactive'
    return (p >= thr) ? 'predicted' : 'inactive';
  }}

  var statuses = [];
  for (var i = 0; i < n; i++) statuses.push(statusFor(i));

  // Running counts for info panel
  var nHit = 0, nHitBelow = 0, nPredicted = 0, nInactive = 0, nAbsent = 0;
  for (var i = 0; i < n; i++) {{
    var st = statuses[i];
    if (st === 'hit') nHit++;
    else if (st === 'hit_below') nHitBelow++;
    else if (st === 'predicted') nPredicted++;
    else if (st === 'inactive') nInactive++;
    else nAbsent++;
  }}

  // ── Info panel ──
  var infoHtml = '<span class="label">DOM Type:</span> <span class="val">' + dom.dom_type + '</span>';
  infoHtml += ' &nbsp;|&nbsp; <span class="label">String:</span> <span class="val">' + dom.string + '</span>';
  infoHtml += ' &nbsp;|&nbsp; <span class="label">DOM #:</span> <span class="val">' + dom.dom_number + '</span>';
  infoHtml += ' &nbsp;|&nbsp; <span class="label">PMTs:</span> <span class="val">' + dom.n_pmts + '</span>';
  infoHtml += ' &nbsp;|&nbsp; <span class="label">DOM Position:</span> <span class="val">(' +
    dom.center[0].toFixed(1) + ', ' + dom.center[1].toFixed(1) + ', ' + dom.center[2].toFixed(1) + ') m</span>';
  if (domStatus) {{
    var thrStr = thr.toFixed(2);
    infoHtml += '<br>';
    infoHtml += '<span class="label">Hit (pred≥' + thrStr + '):</span> <span class="val val-hit">' + nHit + '</span>';
    infoHtml += ' &nbsp;|&nbsp; <span class="label">Predicted active (pred≥' + thrStr + '):</span> <span class="val val-predicted">' + nPredicted + '</span>';
    infoHtml += ' &nbsp;|&nbsp; <span class="label">Inactive (pred&lt;' + thrStr + '):</span> <span class="val val-inactive">' + nInactive + '</span>';
  }}
  document.getElementById('dom-info').innerHTML = infoHtml;

  // Hovertexts
  var pmtNums = dom.pmt_numbers || [];
  var hovertexts = [];
  for (var i = 0; i < n; i++) {{
    var st = statuses[i];
    var pmtLabel = (pmtNums.length > i) ? pmtNums[i] : i;
    var ht = 'PMT #' + pmtLabel + '<br>Status: ' + (STATUS_LABELS[st] || st);
    if (preds[i] !== undefined && preds[i] >= 0) {{
      ht += '<br>Pred score: ' + preds[i].toFixed(4);
    }}
    ht += '<br>Dir: (' + orient[i][0].toFixed(3) + ', ' + orient[i][1].toFixed(3) + ', ' + orient[i][2].toFixed(3) + ')';
    hovertexts.push(ht);
  }}

  var traces = [];

  // Group PMTs by status for legend — skip "absent" (not sampled in this event)
  var statusGroups = {{}};
  for (var i = 0; i < n; i++) {{
    var st = statuses[i];
    if (st === 'absent') continue;
    if (!statusGroups[st]) statusGroups[st] = {{ x:[], y:[], z:[], hover:[], color: STATUS_COLORS[st] || '#333' }};
    statusGroups[st].x.push(rel[i][0]);
    statusGroups[st].y.push(rel[i][1]);
    statusGroups[st].z.push(rel[i][2]);
    statusGroups[st].hover.push(hovertexts[i]);
  }}

  // Keep stable legend order
  var orderedStatuses = ['hit', 'hit_below', 'predicted', 'inactive'];
  orderedStatuses.forEach(function(st) {{
    var g = statusGroups[st];
    if (!g || g.x.length === 0) return;
    traces.push({{
      type: 'scatter3d',
      mode: 'markers',
      x: g.x, y: g.y, z: g.z,
      marker: {{ size: 7, color: g.color, opacity: 0.95,
                line: {{ color: '#fff', width: 0.5 }} }},
      name: STATUS_LABELS[st] || st,
      legendgroup: 'st_' + st,
      hovertext: g.hover,
      hoverinfo: 'text',
    }});
  }});

  // Bubble trail (Dalí "Galatea of the Spheres" style) — shown for all
  // participating PMTs (hit, hit_below, predicted, inactive) with their
  // directionality.
  var nBubbles = 9;
  var bubbleSpacing = (dom.dom_type === 'D-Egg') ? 4.5 : 3.0;  // cm
  var bubbleSizes  = [0, 10.0, 8.0, 6.2, 4.8, 3.6, 2.6, 1.8, 1.0];
  var bubbleAlphas = [0, 0.95, 0.82, 0.68, 0.54, 0.40, 0.28, 0.18, 0.10];

  function hexToRgb(hex) {{
    return [parseInt(hex.slice(1,3),16), parseInt(hex.slice(3,5),16), parseInt(hex.slice(5,7),16)];
  }}

  // Group bubbles by status (including 'inactive' so gray dots have direction)
  var bubbleGroups = {{}};
  for (var i = 0; i < n; i++) {{
    var st = statuses[i];
    if (st === 'absent') continue;
    if (!bubbleGroups[st]) bubbleGroups[st] = {{ x:[], y:[], z:[], sizes:[], colors:[] }};
    var rgb = hexToRgb(STATUS_COLORS[st] || '#333333');
    var ox = orient[i][0], oy = orient[i][1], oz = orient[i][2];
    for (var s = 1; s < nBubbles; s++) {{
      var d = s * bubbleSpacing;
      bubbleGroups[st].x.push(rel[i][0] + ox * d);
      bubbleGroups[st].y.push(rel[i][1] + oy * d);
      bubbleGroups[st].z.push(rel[i][2] + oz * d);
      bubbleGroups[st].sizes.push(bubbleSizes[s]);
      bubbleGroups[st].colors.push('rgba(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ',' + bubbleAlphas[s].toFixed(2) + ')');
    }}
  }}
  orderedStatuses.forEach(function(st) {{
    var bg = bubbleGroups[st];
    if (!bg || bg.x.length === 0) return;
    traces.push({{
      type: 'scatter3d',
      mode: 'markers',
      x: bg.x, y: bg.y, z: bg.z,
      marker: {{ size: bg.sizes, color: bg.colors, line: {{ width: 0 }} }},
      name: 'Orient (' + (STATUS_LABELS[st] || st) + ')',
      legendgroup: 'st_' + st,
      showlegend: false,
      hoverinfo: 'skip',
    }});
  }});

  // Reference sphere wireframe (approximate with lines)
  // For mDOM radius ~16cm, D-Egg ~25cm
  var sphereR = (dom.dom_type === 'D-Egg') ? 25 : 16;
  var circleTraces = [];
  var nPts = 60;
  // XY circle (equator)
  var cxr = [], cyr = [], czr = [];
  for (var i = 0; i <= nPts; i++) {{
    var theta = 2 * Math.PI * i / nPts;
    cxr.push(sphereR * Math.cos(theta));
    cyr.push(sphereR * Math.sin(theta));
    czr.push(0);
  }}
  traces.push({{
    type: 'scatter3d', mode: 'lines',
    x: cxr, y: cyr, z: czr,
    line: {{ color: 'rgba(0,212,255,0.15)', width: 2 }},
    showlegend: false, hoverinfo: 'skip', name: '',
  }});
  // XZ circle
  var cxr2 = [], cyr2 = [], czr2 = [];
  for (var i = 0; i <= nPts; i++) {{
    var theta = 2 * Math.PI * i / nPts;
    cxr2.push(sphereR * Math.cos(theta));
    cyr2.push(0);
    czr2.push(sphereR * Math.sin(theta));
  }}
  traces.push({{
    type: 'scatter3d', mode: 'lines',
    x: cxr2, y: cyr2, z: czr2,
    line: {{ color: 'rgba(0,212,255,0.15)', width: 2 }},
    showlegend: false, hoverinfo: 'skip', name: '',
  }});
  // YZ circle
  var cxr3 = [], cyr3 = [], czr3 = [];
  for (var i = 0; i <= nPts; i++) {{
    var theta = 2 * Math.PI * i / nPts;
    cxr3.push(0);
    cyr3.push(sphereR * Math.cos(theta));
    czr3.push(sphereR * Math.sin(theta));
  }}
  traces.push({{
    type: 'scatter3d', mode: 'lines',
    x: cxr3, y: cyr3, z: czr3,
    line: {{ color: 'rgba(0,212,255,0.15)', width: 2 }},
    showlegend: false, hoverinfo: 'skip', name: '',
  }});

  var axRange = sphereR * 1.4;
  var layout = {{
    paper_bgcolor: '#000',
    plot_bgcolor: '#000',
    font: {{ color: '#ccd6f6' }},
    title: {{
      text: dom.dom_type + '  String ' + dom.string + ', DOM #' + dom.dom_number +
        '  DOM Position: (' + dom.center[0].toFixed(1) + ', ' + dom.center[1].toFixed(1) + ', ' + dom.center[2].toFixed(1) + ') m',
      font: {{ size: 14, color: '#00d4ff' }}
    }},
    scene: {{
      bgcolor: '#000',
      xaxis: {{ title: 'x (cm)', range: [-axRange, axRange], showspikes: false, color: '#8899bb' }},
      yaxis: {{ title: 'y (cm)', range: [-axRange, axRange], showspikes: false, color: '#8899bb' }},
      zaxis: {{ title: 'z (cm)', range: [-axRange, axRange], showspikes: false, color: '#8899bb' }},
      aspectmode: 'cube',
      camera: {{ eye: {{ x: 1.5, y: 1.5, z: 1.0 }} }},
    }},
    legend: {{
      x: 0.01, y: 0.99, font: {{ size: 11 }},
      bgcolor: 'rgba(0,0,0,0.5)',
    }},
    margin: {{ l: 0, r: 0, t: 50, b: 0 }},
  }};

  Plotly.react('dom-detail-container', traces, layout, {{ responsive: true }});

  var detailSection = document.getElementById('dom-detail-section');
  detailSection.style.display = 'block';
  document.getElementById('dom-detail-title').textContent =
    'DOM Detail \\u2014 ' + dom.dom_type + ' (String ' + dom.string + ', DOM #' + dom.dom_number + ')';

  if (!skipScroll) {{
    detailSection.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}
}}

function getFilteredRows() {{
  var sel = document.getElementById('pid-filter').value;
  var rows = document.querySelectorAll('tbody tr');
  var filtered = [];
  rows.forEach(function(r) {{
    var absPid = parseInt(r.getAttribute('data-abs-pid'), 10);
    var match = (sel === 'all') || (absPid === parseInt(sel, 10));
    if (match) filtered.push(r);
  }});
  return filtered;
}}

function renderPage() {{
  var filtered = getFilteredRows();
  var allRows = document.querySelectorAll('tbody tr');
  totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  if (currentPage > totalPages) currentPage = totalPages;
  if (currentPage < 1) currentPage = 1;

  // Hide everything first
  allRows.forEach(function(r) {{ r.style.display = 'none'; }});

  // Show only rows for the current page of the filtered set
  var start = (currentPage - 1) * PAGE_SIZE;
  var end = start + PAGE_SIZE;
  for (var i = start; i < end && i < filtered.length; i++) {{
    filtered[i].style.display = '';
  }}

  // Update controls
  document.getElementById('current-page').textContent = currentPage;
  document.getElementById('total-pages').textContent = totalPages;
  document.getElementById('page-jump').value = currentPage;
  document.getElementById('page-jump').max = totalPages;
  document.getElementById('first-page').disabled = (currentPage <= 1);
  document.getElementById('prev-page').disabled = (currentPage <= 1);
  document.getElementById('next-page').disabled = (currentPage >= totalPages);
  document.getElementById('last-page').disabled = (currentPage >= totalPages);

  document.getElementById('pid-filter-count').textContent =
    filtered.length + ' / ' + allRows.length + ' events';
}}

function goToPage(p) {{
  if (isNaN(p)) return;
  p = Math.max(1, Math.min(totalPages, p));
  currentPage = p;
  renderPage();
}}

function applyPidFilter() {{
  currentPage = 1;
  renderPage();

  // If the currently selected event is hidden, switch to first visible
  var selectedRow = document.querySelector('tbody tr.selected');
  if (selectedRow && selectedRow.style.display === 'none') {{
    var filtered = getFilteredRows();
    if (filtered.length > 0) {{
      showEvent(filtered[0].getAttribute('data-event'));
    }}
  }}
}}

// Initialize pagination immediately - script is after table so DOM elements exist
try {{ applyPidFilter(); }} catch(e) {{ console.error('Pagination init error:', e); }}

// Load first event once all resources are ready
window.addEventListener('load', function() {{
  try {{ applyPidFilter(); }} catch(e) {{ console.error('Pagination reapply error:', e); }}
  showEvent('{first_event}');
}});
</script>

</body>
</html>
"""
