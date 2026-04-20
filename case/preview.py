#!/usr/bin/env python3
"""
Render an isometric PNG preview of the case.
python3 case/preview.py
pip3 install numpy manifold3d matplotlib
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from generate_stl import make_bottom, make_top, make_full_case, el, ew, eh


def tri_array(manifold):
    mesh = manifold.to_mesh()
    verts = np.array(mesh.vert_properties)[:, :3]
    tris = np.array(mesh.tri_verts)
    return verts[tris]  # shape (n, 3, 3)


def face_shading(tris, light_dir=np.array([0.4, 0.4, 1.0])):
    light_dir = light_dir / np.linalg.norm(light_dir)
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    normals = np.cross(v1 - v0, v2 - v0)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.where(lengths > 1e-10, normals / lengths, normals)
    brightness = np.clip((normals @ light_dir) * 0.6 + 0.5, 0.25, 1.0)
    return brightness


def draw(ax, manifold, color=(0.35, 0.55, 0.85), offset=(0, 0, 0)):
    tris = tri_array(manifold)
    tris = tris + np.array(offset)
    shade = face_shading(tris)
    colors = np.zeros((len(tris), 4))
    colors[:, 0] = color[0] * shade
    colors[:, 1] = color[1] * shade
    colors[:, 2] = color[2] * shade
    colors[:, 3] = 1.0
    coll = Poly3DCollection(tris, facecolors=colors, edgecolors=(0, 0, 0, 0.08), linewidths=0.25)
    ax.add_collection3d(coll)


def setup_ax(ax, title):
    ax.set_title(title, fontsize=11, pad=6)
    ax.set_box_aspect((el, ew, eh))
    ax.view_init(elev=28, azim=-55)
    ax.set_axis_off()
    pad = 3
    ax.set_xlim(-pad, el + pad)
    ax.set_ylim(-pad, ew + pad)
    ax.set_zlim(-pad, eh + pad)


def main():
    here = os.path.dirname(os.path.abspath(__file__))

    fig = plt.figure(figsize=(12, 5), dpi=150, facecolor='white')

    # ── Panel 1: closed case (top sitting on bottom) ──
    ax1 = fig.add_subplot(1, 3, 1, projection='3d')
    closed = make_full_case()
    draw(ax1, closed, color=(0.45, 0.6, 0.9))
    setup_ax(ax1, f"Closed  ·  {el:.1f} × {ew:.1f} × {eh:.1f} mm")

    # ── Panel 2: exploded view (top floated above bottom) ──
    ax2 = fig.add_subplot(1, 3, 2, projection='3d')
    bottom = make_bottom()
    top = make_top()
    # top is already flipped (open side down) by make_top()
    # Re-flip so we can stack it in the exploded view
    top_upright = top.mirror([0, 0, 1]).translate([0, 0, eh])
    draw(ax2, bottom, color=(0.45, 0.6, 0.9))
    draw(ax2, top_upright, color=(0.55, 0.7, 0.95), offset=(0, 0, 4))
    ax2.set_title("Exploded (snap-fit)", fontsize=11, pad=6)
    ax2.set_box_aspect((el, ew, eh + 4))
    ax2.view_init(elev=22, azim=-55)
    ax2.set_axis_off()
    pad = 3
    ax2.set_xlim(-pad, el + pad)
    ax2.set_ylim(-pad, ew + pad)
    ax2.set_zlim(-pad, eh + 4 + pad)

    # ── Panel 3: bottom half alone (shows snap rim) ──
    ax3 = fig.add_subplot(1, 3, 3, projection='3d')
    draw(ax3, bottom, color=(0.45, 0.6, 0.9))
    setup_ax(ax3, "Bottom  ·  press-fit rim")

    fig.suptitle("ESP32-S3 Super Mini HID Dongle Case", fontsize=13, y=0.97)
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    out = os.path.join(here, "preview_full.png")
    fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"Wrote {out}")


if __name__ == '__main__':
    main()
