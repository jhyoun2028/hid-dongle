#!/usr/bin/env python3
"""
ESP32-S3 Super Mini HID Dongle Case — ultra-thin, snap-fit, no buttons.
python3 case/generate_stl.py
pip3 install numpy manifold3d
"""

import os, sys, struct
import numpy as np

try:
    import manifold3d as m3d
except ImportError:
    print("pip3 install manifold3d"); sys.exit(1)

m3d.set_circular_segments(48)

# ── PCB (ESP32-S3 Super Mini, no pin headers) ──
PCB_L     = 23.0     # mm (long side, USB-C end)
PCB_W     = 18.0     # mm (short side)
PCB_T     = 1.6      # mm — standard dev board PCB thickness

# ── Component clearance above / below PCB ──
# The USB-C receptacle body is the tallest thing on the board (~3mm above
# PCB top). The ESP32 chip is shorter, so COMP_TOP is set by the port.
COMP_TOP  = 3.0      # tallest component above PCB = USB-C body
COMP_BOT  = 0.4      # bare solder pads / castellations below PCB (no headers!)

# ── USB-C receptacle (standard: 8.4 × 2.6, 0.1mm clearance per side) ──
# Mounted ON TOP of the PCB — port bottom = PCB top surface = split plane.
USBC_W    = 8.6      # port width
USBC_H    = 3.0      # port body height above PCB top (matches COMP_TOP)
USBC_OUT  = 1.5      # how far the metal shell protrudes past the PCB edge

# ── Case shell ──
WALL      = 2.4      # shell wall thickness — 6 perimeters at 0.4mm nozzle, well
                     # above any print shop's minimum. Also keeps ≥WALL of
                     # material above the USB-C cutout ceiling.
GAP       = 0.15     # clearance around PCB inside cavity
FILLET    = 1.2      # 3D edge fillet radius
CR        = 2.5      # XY corner radius (pill shape)

# ── Internal press-fit rim ──
# Keep the outer wall intact and use an internal rim on the bottom half.
# The rim STRADDLES the cavity edge: extending RIM_OVERLAP into the bottom
# wall (clean union, watertight) AND RIM_OVERLAP past the cavity edge into
# the top's cavity space (press-fit interference with the top wall's inner
# face). Total interference = 2 * RIM_OVERLAP per side.
RIM_H         = 1.2     # height of the rim
RIM_W         = 0.8     # rim thickness (2 perimeters at 0.4mm nozzle)
RIM_OVERLAP   = 0.1     # into bottom wall (union) and top cavity (interference)

# ── Derived ──
il = PCB_L + GAP * 2          # internal cavity length
iw = PCB_W + GAP * 2          # internal cavity width
el = il + WALL * 2            # external case length
ew = iw + WALL * 2            # external case width
eh = WALL + GAP + COMP_BOT + PCB_T + COMP_TOP + GAP + WALL  # external case height
ir = max(CR - WALL, 0.5)      # internal corner radius
pcb_z = WALL + GAP + COMP_BOT            # PCB bottom z-position
# Split at PCB TOP surface: bottom half cradles the PCB, top half is a lid
# that covers the chip. Port sits exactly at the split plane.
split_z = pcb_z + PCB_T


# ── Geometry helpers ──

def pill_box(l, w, h, cr, fillet):
    """Pill-shaped rounded box (all edges 3D-filleted via minkowski sum)."""
    f = min(fillet, min(l, w, h) / 2 - 0.1)
    core_l = l - 2 * f
    core_w = w - 2 * f
    r = max(0.1, min(cr - f, min(core_l, core_w) / 2 - 0.01))

    inner_l = core_l - 2 * r
    inner_w = core_w - 2 * r
    cs = m3d.CrossSection.square([inner_l, inner_w]).translate([r, r])
    cs_rounded = cs.offset(r, m3d.JoinType.Round)
    core = cs_rounded.extrude(h - 2 * f).translate([0, 0, f])

    sphere = m3d.Manifold.sphere(f, 24)
    return core.minkowski_sum(sphere).translate([f, f, 0])


def flat_rbox(l, w, h, r):
    """XY-only rounded box (flat top/bottom, used for cavities and rims)."""
    r0 = max(0.1, min(r, min(l, w) / 2 - 0.01))
    cs = m3d.CrossSection.square([l - 2*r0, w - 2*r0]).translate([r0, r0])
    return cs.offset(r0, m3d.JoinType.Round).extrude(h)


def rbox_cs(l, w, r):
    """2D rounded rectangle cross-section."""
    r0 = max(0.1, min(r, min(l, w) / 2 - 0.01))
    return m3d.CrossSection.square([l - 2*r0, w - 2*r0]) \
        .translate([r0, r0]).offset(r0, m3d.JoinType.Round)


def box(l, w, h):
    return m3d.Manifold.cube([l, w, h])


# ── Full case (before splitting into top/bottom) ──

def make_full_case():
    outer = pill_box(el, ew, eh, CR, FILLET)

    # Uniform interior cavity around the PCB + components.
    inner = flat_rbox(il, iw, eh - WALL * 2, ir) \
        .translate([WALL, WALL, WALL])

    # NOTE: USB-C cutout is intentionally NOT applied here. Putting it here
    # would make its bottom face coincide with the split plane during trim,
    # producing degenerate geometry / open edges. Instead each half is cut
    # individually after trimming.
    return outer - inner


def usbc_cutout(z_base, height):
    """USB-C slot box: positioned at the USB end, at the requested Z base,
    with extra height to guarantee clean boolean cuts past any trim plane."""
    return box(WALL + USBC_OUT + 2, USBC_W, height) \
        .translate([el - WALL - 1, (ew - USBC_W) / 2, z_base])


# ── Bottom half + internal rim ──

def make_bottom():
    # Keep the bottom at the split plane, then add an internal locating rim
    # so the top nests over it without thinning the outer wall.
    full = make_full_case()
    bottom = full.trim_by_plane([0, 0, -1], -split_z)

    # Build the rim via 2D offsets from the cavity cross-section. This keeps
    # the rim wall a uniform RIM_W thick all the way around the corner —
    # previous two-independent-boxes approach had mismatched inner/outer
    # corner radii, producing thin / asymmetric corners that risked breaking
    # on print.
    cavity_cs = rbox_cs(il, iw, ir).translate([WALL, WALL])
    outer_cs = cavity_cs.offset(RIM_OVERLAP, m3d.JoinType.Round)
    inner_cs = outer_cs.offset(-RIM_W, m3d.JoinType.Round)
    rim_cs = outer_cs - inner_cs
    rim = rim_cs.extrude(RIM_H).translate([0, 0, split_z])

    # Cut the USB-C slot through the upper part of the bottom so the port
    # stays clear after the top is fitted.
    usbc = usbc_cutout(split_z - 0.3, USBC_H + RIM_H + 1.0)
    return (bottom + rim) - usbc


# ── Top half ──

def make_top():
    full = make_full_case()
    top_half = full.trim_by_plane([0, 0, 1], split_z)

    # Carve the USB-C slot through the top half. Cut extends below split_z
    # so the slot's bottom face doesn't coincide with the trim plane.
    top_usbc_cut = usbc_cutout(split_z - 0.5, USBC_H + 1.0)
    top_half = top_half - top_usbc_cut

    # Flip so the open side faces down for printing.
    return top_half.translate([0, 0, -eh]).mirror([0, 0, 1])


# ── STL export ──

def save_stl(manifold, filepath):
    mesh = manifold.to_mesh()
    verts = np.array(mesh.vert_properties)[:, :3]
    tris = np.array(mesh.tri_verts)
    n = len(tris)

    with open(filepath, 'wb') as f:
        f.write(b'ESP32-S3 SuperMini Dongle Case' + b'\0' * 50)
        f.write(struct.pack('<I', n))
        for tri in tris:
            v0, v1, v2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            normal = np.cross(v1 - v0, v2 - v0)
            nl = np.linalg.norm(normal)
            if nl > 1e-10: normal /= nl
            f.write(struct.pack('<3f', *normal))
            f.write(struct.pack('<3f', *v0))
            f.write(struct.pack('<3f', *v1))
            f.write(struct.pack('<3f', *v2))
            f.write(struct.pack('<H', 0))

    print(f"  {filepath}  ({n:,} tris)")


# ── Main ──

def main():
    d = os.path.dirname(os.path.abspath(__file__))
    print(f"Super Mini dongle case: {el:.1f} x {ew:.1f} x {eh:.1f} mm")
    print(f"wall {WALL}mm | fillet {FILLET}mm | rim {RIM_W} x {RIM_H}mm\n")

    print("Bottom...")
    save_stl(make_bottom(), os.path.join(d, "bottom_case.stl"))
    print("Top...")
    save_stl(make_top(), os.path.join(d, "top_case.stl"))
    print("\nDone. 2 parts: bottom + top (press-fit, no glue)")

if __name__ == '__main__':
    main()
