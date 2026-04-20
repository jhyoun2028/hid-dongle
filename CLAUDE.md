# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **See also: [AGENTS.md](AGENTS.md)** — contains exhaustive build commands, per-language code style, hardware constants, and design rationale. Treat AGENTS.md as the source of truth for style details; this file captures the "big picture" only.

## What this repo is

USB HID Auto-Typer Dongle firmware for the **Waveshare ESP32-S3-Zero**. When the dongle is plugged into an iPad (or any USB host), it enumerates as a USB keyboard and auto-types a pre-stored text payload. Two independent firmware variants coexist in the repo:

| Variant | Language | Storage | Speed | Upload path |
|---|---|---|---|---|
| **Arduino** (preferred) | C++ (TinyUSB) | LittleFS | ~500 char/s | Host → serial (`upload_text.py`) |
| **CircuitPython** | Python | CIRCUITPY drive | ~60 char/s | Copy `text.txt` onto USB mass-storage |

Both firmwares share the same core trick: **raw HID reports** (`KeyReport` / `bytearray(8)` + `sendReport()`) instead of high-level keyboard APIs, with **implicit key release** (next keydown replaces previous; explicit release only needed to repeat the same character). They map ASCII 0x00–0x7F to US-layout HID keycodes via a hand-built lookup table; there is no Unicode support.

## Repository layout (what's live vs. frozen)

```
arduino_hid/arduino_hid.ino    # Arduino firmware — single .ino file, all code here
arduino_hid/build/              # Pre-compiled .merged.bin (flash directly, no compile needed)
code.py, boot.py                # CircuitPython firmware
firmware.bin                    # CircuitPython base firmware for the ESP32-S3
upload_text.py                  # Host tool — serial protocol client (macOS/Linux/Windows)
save_text.py                    # Host tool — clipboard → CIRCUITPY (Windows only)
case/                           # 3D-printable enclosure (parametric, Python + OpenSCAD)
case copy/                      # Frozen backup — DO NOT MODIFY
dongle_hack/                    # Unrelated vendor firmware — DO NOT MODIFY
oh-my-openagent/                # Separate project living in this tree — DO NOT MODIFY
```

When working in this repo, edits should almost always target `arduino_hid/`, `code.py`/`boot.py`, the host `.py` tools, or `case/`. The `case copy/`, `dongle_hack/`, and `oh-my-openagent/` trees are intentionally out of scope.

## Serial protocol (Arduino ↔ upload_text.py)

Line-based over USB CDC at **115200 baud**. This is the only interface into the Arduino firmware once flashed — the CIRCUITPY drive does not appear under the Arduino build.

```
SAVE\n<line1>\n<line2>\n...EOF\n   → OK:<bytes>\n  | ERR:SAVE_FAILED\n
STATUS\n                            → STORED:<bytes> bytes\n
TYPE\n                              → TYPING...\n  then  DONE:<chars> chars\n
```

Payload is ASCII-only; non-ASCII characters are silently replaced with `?`, and `\r` is stripped by `trim()`. Any change to the firmware's serial handler must be mirrored in `upload_text.py` and vice versa.

## Commands

### Flash the Arduino firmware (no compile needed)
Board must be in download mode first: **hold BOOT, tap RESET, release BOOT.**
```bash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* erase_flash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* write_flash -z 0x0 \
  arduino_hid/build/arduino_hid.ino.merged.bin
```

### Compile the Arduino firmware (only if `.ino` changed)
```bash
arduino-cli compile \
  --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=4M,PartitionScheme=huge_app,PSRAM=enabled,CPUFreq=240,FlashMode=qio" \
  --output-dir arduino_hid/build \
  arduino_hid
```
On macOS ARM64 the bundled Arduino `ctags` is an x86_64 binary and will fail — replace `~/Library/Arduino15/packages/builtin/tools/ctags/5.8-arduino11/ctags` with a stub that just `exit 0`s.

### Flash CircuitPython firmware
```bash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* erase_flash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* write_flash -z 0x0 firmware.bin
# then copy code.py, boot.py, text.txt to the CIRCUITPY drive that appears
```

### Host tools
```bash
python3 upload_text.py                 # clipboard → dongle
python3 upload_text.py -f file.txt     # file → dongle
python3 upload_text.py -t "literal"    # literal text → dongle
python3 upload_text.py --status        # query stored bytes
python3 upload_text.py --type          # trigger typing remotely
```

### 3D case
```bash
python3 case/generate_stl.py           # produces bottom_case.stl, top_case.stl, button.stl
```
Requires `numpy manifold3d matplotlib`. `case/dongle_case.scad` is a preview-only OpenSCAD variant without logo embossing.

## Testing

There is **no automated test suite**. Verification is manual and hardware-in-the-loop:

1. Flash firmware, then `python3 upload_text.py --status` to confirm the board is enumerated on serial and bytes are stored.
2. Use `test800.txt` (≈800 chars) as a repeatable typing payload.
3. Plug into an iPad with a text field focused; observe auto-typing ≈1.5 s after enumeration.

If you cannot physically test a change, say so explicitly rather than claiming the change is verified.

## Things to know before changing code

- **Single-file Arduino firmware.** All C++ lives in `arduino_hid/arduino_hid.ino`. Function order (helpers → business logic → storage → serial handler → `setup()` → `loop()`) and `// ===...===` section banners are intentional — preserve them.
- **No dynamic allocation in firmware.** The Arduino side uses `String` but never `new`/`malloc`. Max text payload is `MAX_TEXT_SIZE` = 32000 bytes (LittleFS limit).
- **Raw HID is non-negotiable.** Both firmwares deliberately bypass `layout.write()` / high-level keyboard APIs for throughput. Don't "simplify" them into high-level calls.
- **Fail-open firmware.** LittleFS format failure → continue; missing text → skip typing. Don't add halt-on-error paths.
- **CircuitPython USB polling is hardcoded at 8 ms** — this is the root cause of the speed gap vs. Arduino's 1 ms, and it cannot be changed from Python.
- **BOOT button (GPIO0)** doubles as a pause/resume toggle during typing on the Arduino firmware.
- **`case copy/` is a frozen backup.** Edit `case/` only.
