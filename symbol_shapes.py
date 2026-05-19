import numpy as np
import plotly.graph_objects as go


def _build_3d_diamond(cx, cy, cz, size=12.0):
    """Plotly Mesh3d arrays for a 6-spiked 3D diamond (jack-star) centered at
    (cx, cy, cz). Spikes point along ±x, ±y, ±z at distance `size` (meters);
    inner cube half-edge = size / 3.5. 14 vertices, 24 triangular faces.

    Shape is view-independent because the mesh is a true 3D polytope built
    in data coordinates — it stays the same diamond whether the scene shows
    the full IC86+Upgrade volume or zooms to the Upgrade region.

    Vertex order (used by the client-side rebuild for per-view axis scaling):
      0..5  spike apexes: +x, -x, +y, -y, +z, -z
      6..13 inner cube corners, indexed 6 + (sx*4 + sy*2 + sz)
            where s* = 0 for +, 1 for -.
    """
    inner = size / 3.5
    apex = np.array([
        [ size, 0, 0], [-size, 0, 0],
        [0,  size, 0], [0, -size, 0],
        [0, 0,  size], [0, 0, -size],
    ], dtype=float)
    cube = np.array([
        [ inner,  inner,  inner],  # 6: +++
        [ inner,  inner, -inner],  # 7: ++-
        [ inner, -inner,  inner],  # 8: +-+
        [ inner, -inner, -inner],  # 9: +--
        [-inner,  inner,  inner],  # 10: -++
        [-inner,  inner, -inner],  # 11: -+-
        [-inner, -inner,  inner],  # 12: --+
        [-inner, -inner, -inner],  # 13: ---
    ], dtype=float)

    def ci(sx, sy, sz):
        return 6 + (sx * 4 + sy * 2 + sz)

    tri_i, tri_j, tri_k = [], [], []

    def _pyramid(apex_idx, base):
        for k in range(4):
            tri_i.append(apex_idx)
            tri_j.append(base[k])
            tri_k.append(base[(k + 1) % 4])

    # Each spike: apex connected to the 4 cube corners sharing its sign.
    _pyramid(0, [ci(0, 0, 0), ci(0, 0, 1), ci(0, 1, 1), ci(0, 1, 0)])  # +x
    _pyramid(1, [ci(1, 0, 0), ci(1, 1, 0), ci(1, 1, 1), ci(1, 0, 1)])  # -x
    _pyramid(2, [ci(0, 0, 0), ci(0, 0, 1), ci(1, 0, 1), ci(1, 0, 0)])  # +y
    _pyramid(3, [ci(0, 1, 0), ci(1, 1, 0), ci(1, 1, 1), ci(0, 1, 1)])  # -y
    _pyramid(4, [ci(0, 0, 0), ci(1, 0, 0), ci(1, 1, 0), ci(0, 1, 0)])  # +z
    _pyramid(5, [ci(0, 0, 1), ci(0, 1, 1), ci(1, 1, 1), ci(1, 0, 1)])  # -z

    verts = np.vstack([apex, cube]) + np.array([cx, cy, cz])
    return verts[:, 0], verts[:, 1], verts[:, 2], tri_i, tri_j, tri_k


# Bubble-trail defaults (Dalí "Galatea of the Spheres" style)
N_BUBBLES = 11
BUBBLE_SPACING = 1.2   # meters between spheres
BUBBLE_SIZES = [8.0, 7.0, 6.0, 5.2, 4.4, 3.6, 2.8, 2.1, 1.5, 1.0, 0.5]
BUBBLE_ALPHAS = [0.92, 0.82, 0.72, 0.60, 0.48, 0.37, 0.27, 0.18, 0.11, 0.06, 0.02]


def _build_bubble_trail(geo_indices, base_rgb, name,
                        geo_xyz, geo_orient, pmt_to_dom,
                        legendgroup=None, showlegend=False, visible=True,
                        n_bubbles=N_BUBBLES, bubble_spacing=BUBBLE_SPACING,
                        bubble_sizes=BUBBLE_SIZES, bubble_alphas=BUBBLE_ALPHAS):
    """Build a Scatter3d trace: dissolving sphere trail along PMT orientation."""
    all_x, all_y, all_z = [], [], []
    all_sizes, all_colors, all_customdata = [], [], []
    for gi in geo_indices:
        if gi < 0:
            continue
        x, y, z = geo_xyz[gi]
        odx, ody, odz = geo_orient[gi]
        dom_id = pmt_to_dom.get(int(gi), -1)
        for s in range(1, n_bubbles):
            d = s * bubble_spacing
            all_x.append(float(x + odx * d))
            all_y.append(float(y + ody * d))
            all_z.append(float(z + odz * d))
            all_sizes.append(bubble_sizes[s])
            all_colors.append(
                f'rgba({base_rgb[0]},{base_rgb[1]},{base_rgb[2]},{bubble_alphas[s]:.2f})')
            all_customdata.append([int(gi), dom_id])
    if not all_x:
        return None
    kwargs = dict(
        x=all_x, y=all_y, z=all_z,
        mode='markers',
        marker=dict(size=all_sizes, color=all_colors,
                    line=dict(width=0)),
        customdata=all_customdata,
        name=name,
        showlegend=showlegend,
        hoverinfo='skip',
    )
    if legendgroup:
        kwargs['legendgroup'] = legendgroup
    if visible != True:
        kwargs['visible'] = visible
    return go.Scatter3d(**kwargs)
