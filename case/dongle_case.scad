/*
 * ESP32-S3-Zero HID Dongle Case — Final Prototype
 * Waveshare ESP32-S3-Zero (pin legs clipped, yellow housing retained)
 *
 * Size: 26.6 x 21.1 x 9.4 mm (pill-shaped, 3D filleted)
 * Print: 0.4mm nozzle / 0.2mm layer / 20% infill / no support / black PLA
 *
 * Features:
 *  - BOOT pinhole only (1.5mm, SIM ejector accessible)
 *  - USB-C port opening
 *  - Press-fit snap rim
 *
 * Usage:
 *  1. Set RENDER_PART below
 *  2. F6 (render) → F7 (export STL)
 *
 * Note: "logi" deboss engraving only available via generate_stl.py
 */

$fn = 64;

RENDER_PART = "preview"; // "preview" | "bottom" | "top" | "assembled"

// ── PCB (Waveshare ESP32-S3-Zero) ──
PCB_L     = 23.5;    // mm
PCB_W     = 18.0;
PCB_T     = 1.0;

// ── Component clearance from PCB surface ──
COMP_TOP  = 2.8;     // ESP32 chip ~2.5mm + margin
COMP_BOT  = 2.5;     // pin legs clipped, yellow housing ~2.5mm remains

// ── USB-C connector ──
USBC_W    = 9.2;
USBC_H    = 3.4;
USBC_OUT  = 1.3;     // protrusion past PCB edge

// ── Case ──
WALL      = 1.8;     // sturdier wall for reliable FDM printing
GAP       = 0.15;    // tight fit tolerance
CR        = 2.5;     // corner radius (pill shape)

// ── Snap rim ──
RIM_H     = 1.2;
RIM_W     = 0.8;
RIM_GAP   = 0.12;

// ── BOOT button pinhole only ──
BOOT_X    = 5.5;     // from USB end
BOOT_Y    = 2.0;     // from left edge
BTN_D     = 1.5;     // SIM ejector size

// ── Derived ──
_il    = PCB_L + GAP * 2;
_iw    = PCB_W + GAP * 2;
_el    = _il + WALL * 2;
_ew    = _iw + WALL * 2;
_eh    = WALL + GAP + COMP_BOT + PCB_T + COMP_TOP + GAP + WALL;
_ir    = max(CR - WALL, 0.5);
_pcb_z = WALL + GAP + COMP_BOT;
_split = _pcb_z + PCB_T / 2;

echo(str("Case: ", _el, " x ", _ew, " x ", _eh, " mm"));

function _cx(from_usb) = _el - WALL - GAP - from_usb;
function _cy(from_left) = WALL + GAP + from_left;

// ── Primitives ──

module rbox(l, w, h, r) {
    r0 = max(0.1, min(r, min(l, w) / 2 - 0.01));
    hull()
        for (x = [r0, l - r0])
            for (y = [r0, w - r0])
                translate([x, y, 0])
                    cylinder(r = r0, h = h);
}

// ── Full enclosed case (pre-split) ──

module full_case() {
    difference() {
        rbox(_el, _ew, _eh, CR);

        translate([WALL, WALL, WALL])
            rbox(_il, _iw, _eh - WALL * 2, _ir);

        translate([_el - WALL - 1, (_ew - USBC_W) / 2, _pcb_z - 0.3])
            cube([WALL + USBC_OUT + 2, USBC_W, USBC_H]);

        translate([_cx(BOOT_X), _cy(BOOT_Y), _eh - WALL - 1])
            cylinder(d = BTN_D, h = WALL + 2);
    }

    _sh = COMP_BOT + GAP;
    _sw = 1.0;

    translate([WALL + 1, WALL, WALL])
        cube([_il - 2, _sw, _sh]);
    translate([WALL + 1, _ew - WALL - _sw, WALL])
        cube([_il - 2, _sw, _sh]);
    translate([WALL, WALL + _sw, WALL])
        cube([_sw, _iw - _sw * 2, _sh]);
}

// ── Bottom case ──

module bottom_case() {
    difference() {
        union() {
            intersection() {
                full_case();
                cube([_el + 1, _ew + 1, _split]);
            }

            difference() {
                translate([WALL + RIM_GAP, WALL + RIM_GAP, _split])
                    rbox(_il - RIM_GAP * 2, _iw - RIM_GAP * 2,
                         RIM_H, max(_ir - RIM_GAP, 0.3));
                translate([WALL + RIM_GAP + RIM_W, WALL + RIM_GAP + RIM_W, _split - 0.1])
                    rbox(_il - RIM_GAP * 2 - RIM_W * 2, _iw - RIM_GAP * 2 - RIM_W * 2,
                         RIM_H + 1, max(_ir - RIM_GAP - RIM_W, 0.2));
            }
        }

        translate([_el - WALL - 1, (_ew - USBC_W) / 2, _pcb_z - 0.3])
            cube([WALL + USBC_OUT + 2, USBC_W, USBC_H + RIM_H + 2]);
    }
}

// ── Top case (assembly position) ──

module _top_assembled() {
    intersection() {
        full_case();
        translate([0, 0, _split])
            cube([_el + 1, _ew + 1, _eh]);
    }
}

// ── Top case (flipped for printing) ──

module top_case() {
    translate([0, 0, _eh - _split])
        mirror([0, 0, 1])
            _top_assembled();
}

// ── Assembly preview ──

module assembled() {
    color("DimGray", 0.9) bottom_case();
    color("DarkSlateGray", 0.85) _top_assembled();
}

// ── Render ──

if (RENDER_PART == "preview") {
    bottom_case();
    translate([0, _ew + 5, 0]) top_case();
}
else if (RENDER_PART == "bottom") { bottom_case(); }
else if (RENDER_PART == "top") { top_case(); }
else if (RENDER_PART == "assembled") { assembled(); }
