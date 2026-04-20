# AGENTS.md — HID-Dongle-Project

## Project Overview

USB HID Auto-Typer Dongle for Waveshare ESP32-S3-Zero. Plug into iPad → auto-types stored text.
Two firmware variants: Arduino (fast, ~360 chars/sec) and CircuitPython (simple, ~125 chars/sec).

## Architecture

```
arduino_hid/
  arduino_hid.ino       # Arduino firmware (C++, TinyUSB + LittleFS) — single file
  build/                 # Pre-compiled binaries (.merged.bin)
code.py                  # CircuitPython firmware (raw HID reports)
boot.py                  # CircuitPython boot config (PC/iPad mode switch via BOOT button)
upload_text.py           # Host tool: serial text upload to Arduino firmware (cross-platform)
save_text.py             # Host tool: clipboard → CIRCUITPY drive (Windows only)
firmware.bin             # CircuitPython base firmware for ESP32-S3
case/
  generate_stl.py        # Python STL generator (manifold3d) — parametric pill-shaped case
  dongle_case.scad       # OpenSCAD source — preview/manual export
  *.stl                  # Generated: top_case, bottom_case, button
  preview_full.png       # Render preview
case copy/               # Backup of case/ — DO NOT MODIFY
bin/                     # Empty (reserved)
text.txt                 # Sample text payload
test800.txt              # ~800 char test payload
dongle_hack/             # Unrelated vendor firmware — DO NOT MODIFY
oh-my-openagent/         # Separate project — DO NOT MODIFY
```

## Build & Flash Commands

### Prerequisites
```bash
pip3 install esptool pyserial
pip3 install numpy manifold3d matplotlib   # for case/generate_stl.py only
```

### Arduino Firmware

Compile (optional — pre-built binary in `arduino_hid/build/`):
```bash
arduino-cli compile \
  --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=4M,PartitionScheme=huge_app,PSRAM=enabled,CPUFreq=240,FlashMode=qio" \
  --output-dir arduino_hid/build \
  arduino_hid
```

Flash (board must be in download mode — hold BOOT, press RESET, release BOOT):
```bash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* erase_flash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* write_flash -z 0x0 \
  arduino_hid/build/arduino_hid.ino.merged.bin
```

### CircuitPython Firmware
```bash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* erase_flash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* write_flash -z 0x0 firmware.bin
```
Then copy `code.py`, `boot.py`, `text.txt` to the CIRCUITPY drive.

### Host Tools
```bash
python3 upload_text.py                # Upload clipboard to dongle (serial)
python3 upload_text.py -f file.txt    # Upload from file
python3 upload_text.py -t "text"      # Upload literal text
python3 upload_text.py --status       # Check stored text size
python3 upload_text.py --type         # Trigger typing manually
python3 save_text.py                  # Windows: clipboard → CIRCUITPY/text.txt
```

### 3D Case Generation
```bash
python3 case/generate_stl.py          # Generates bottom_case.stl, top_case.stl, button.stl
```
Or open `case/dongle_case.scad` in OpenSCAD for preview (no logo emboss in SCAD version).

## Testing

No test suite. Verification is manual:
1. Flash firmware → `upload_text.py --status` (confirm bytes stored)
2. Plug into iPad with text field focused → observe auto-typing
3. Use `test800.txt` as a repeatable test payload

## Serial Protocol (Arduino ↔ upload_text.py)

Baud: 115200. Line-based commands over USB CDC serial:
```
Host → Board:  SAVE\n<text lines>\nEOF\n    → Board replies: OK:<bytes>\n or ERR:SAVE_FAILED\n
Host → Board:  STATUS\n                     → Board replies: STORED:<bytes> bytes\n
Host → Board:  TYPE\n                        → Board replies: TYPING...\n then DONE:<chars> chars\n
```
Text is accumulated line-by-line between SAVE and EOF. ASCII only.

## Code Style — Arduino (.ino)

- **Single file**: All code in `arduino_hid.ino`, no header files
- **Section separators**: `// ====...====` banners (full line width) between logical sections
- **Header comment**: `/* ... */` block at top — purpose, board, speed
- **Function ordering**: helpers (sendKey, releaseAllKeys) → business logic (typeFast) → storage (loadText, saveText) → serial handler → setup() → loop()
- **Constants**: `#define` for config (`BOOT_DELAY_MS`, `MAX_TEXT_SIZE`, `BOOT_BTN`)
- **Naming**: `camelCase` functions (`typeFast`, `sendKey`), `PascalCase` types (`KeyMap`, `KeyReport`), `UPPER_CASE` constants, `ALL_CAPS` arrays (`ASCII_MAP`)
- **Variables**: `static` for file-scoped globals; no Hungarian notation
- **Indentation**: 2 spaces, K&R braces (opening brace on same line)
- **Comments**: Inline `//` for non-obvious logic; section banners for structure
- **Error handling**: Fail-open — LittleFS format failure → continue, missing text → skip typing
- **No dynamic allocation**: Use `String` class but never `new`/`malloc`
- **Raw HID**: Always use raw `KeyReport` + `sendReport()` — never high-level keyboard APIs
- **Implicit release**: Next keydown replaces previous key; explicit release only for repeated chars

## Code Style — Python (Host Tools)

- **Docstrings**: Module-level docstring with usage examples, top of every file
- **Section separators**: `# ----------...---------- #` full-width comment lines
- **Naming**: `snake_case` functions/variables, `UPPER_CASE` constants
- **Imports**: Standard library first, then conditional third-party:
  ```python
  try:
      import serial
  except ImportError:
      print("[Error] pyserial not installed. Run: pip3 install pyserial")
      sys.exit(1)
  ```
- **Entry point**: `if __name__ == "__main__": main()`
- **CLI**: `argparse` for all command-line tools
- **Error messages**: Prefixed `[Error]`, `[Info]`, `[Done]`, `[Status]` print statements
- **Error exits**: `sys.exit(1)` after printing `[Error]` message
- **Serial**: 115200 baud, 3s timeout, always `ser.close()` after use
- **Encoding**: ASCII for serial data (`errors="replace"`), UTF-8 for file I/O
- **Cross-platform**: `upload_text.py` auto-detects ports (macOS `/dev/cu.usbmodem*`, Linux `/dev/ttyACM*`, Windows via `serial.tools.list_ports`)

## Code Style — CircuitPython (code.py, boot.py)

- **Flat procedural**: No classes, no argparse — top-level script flow
- **Data tables**: Use `# fmt: off` / `# fmt: on` around large lookup dicts (`CHAR_MAP`)
- **Infinite sleep**: `while True: time.sleep(60)` for idle/error states
- **HID device discovery**: Iterate `usb_hid.devices` matching `usage_page=0x01, usage=0x06`
- **Raw reports**: `bytearray(8)` for HID keyboard reports, `kbd.send_report()`

## Code Style — 3D Case (case/)

- **Two implementations**: `generate_stl.py` (Python, full features + logo emboss) and `dongle_case.scad` (OpenSCAD, preview only)
- **Parametric constants**: `UPPER_CASE` at module top (`PCB_L`, `WALL`, `FILLET`, `BTN_STEM`)
- **Derived constants**: Computed from parameters, prefixed `_` in SCAD (`_el`, `_iw`), bare names in Python (`el`, `iw`)
- **Geometry helpers**: Small functions (`pill_box`, `flat_rbox`, `cyl`) — composable CSG primitives
- **STL export**: Binary STL with raw triangle packing (no external STL library)
- **Dependencies**: `manifold3d` for CSG, `matplotlib` for font path extraction (logo emboss)
- **`case copy/`**: Manual backup — DO NOT MODIFY. Edit `case/` only.

## Hardware Constants

| Constant | Value | Notes |
|----------|-------|-------|
| Board | Waveshare ESP32-S3-Zero | ESP32-S3FH4R2 |
| Flash | 4MB | LittleFS partition for Arduino |
| PSRAM | 2MB | Enabled in Arduino build |
| USB | Full-Speed 12Mbps | Native USB OTG |
| BOOT button | GPIO0 | Active-low, internal pull-up |
| NeoPixel LED | GPIO21 | WS2812, used in boot.py only |
| Serial baud | 115200 | Arduino CDC serial |
| Boot delay | 550ms | Arduino auto-type delay |
| Max text | 32000 bytes | Arduino LittleFS limit |

## Key Design Decisions

1. **Raw HID reports** over high-level APIs — both firmwares skip `layout.write()` for speed
2. **Implicit key release** — next keydown replaces previous; explicit release only for repeated chars
3. **LittleFS** (Arduino) vs **USB drive** (CircuitPython) for text storage
4. **BOOT button** doubles as pause/resume toggle during typing (Arduino)
5. **ASCII-only** — both firmwares map ASCII 0x00–0x7F to US keyboard HID keycodes; no Unicode
6. **Fail-open** — firmware continues on storage errors rather than halting

## Common Pitfalls

- macOS ARM64: Arduino `ctags` is x86_64 — replace with stub script if compile fails
- Download mode entry: BOOT+RESET sequence with tiny SMD buttons — use a pointed tool
- CircuitPython USB polling is hardcoded at 8ms — cannot be changed
- `upload_text.py` sends ASCII-only; non-ASCII chars silently replaced with `?`
- After flashing Arduino firmware, CIRCUITPY drive disappears — use serial for text upload
- Serial protocol is line-based — `\r` in text payload will be stripped by `.trim()`
