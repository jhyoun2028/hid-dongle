"""
code.py - USB HID Auto-Typer (FAST version)
Waveshare ESP32-S3-Zero + CircuitPython

SPEED OPTIMIZATION: Uses raw HID reports instead of layout.write().
Instead of 2 reports per char (keydown + keyup), we send only 1 report
per char — the next char's keydown implicitly releases the previous key.
This doubles throughput: ~125 chars/sec at 8ms polling.

For repeated characters (e.g. "aa"), an empty release report is inserted.
"""

import time
import usb_hid

# --------------------------------------------------------------------------- #
#  Find the HID keyboard device
# --------------------------------------------------------------------------- #
kbd = None
for dev in usb_hid.devices:
    if dev.usage_page == 0x01 and dev.usage == 0x06:
        kbd = dev
        break

if kbd is None:
    # Fallback: try first device
    if usb_hid.devices:
        kbd = usb_hid.devices[0]
    else:
        while True:
            time.sleep(60)

# --------------------------------------------------------------------------- #
#  US keyboard layout: char → (modifier_byte, keycode)
#  Modifier bits: 0x00=none, 0x02=LeftShift
# --------------------------------------------------------------------------- #
SHIFT = 0x02

# fmt: off
CHAR_MAP = {
    'a': (0, 0x04), 'b': (0, 0x05), 'c': (0, 0x06), 'd': (0, 0x07),
    'e': (0, 0x08), 'f': (0, 0x09), 'g': (0, 0x0A), 'h': (0, 0x0B),
    'i': (0, 0x0C), 'j': (0, 0x0D), 'k': (0, 0x0E), 'l': (0, 0x0F),
    'm': (0, 0x10), 'n': (0, 0x11), 'o': (0, 0x12), 'p': (0, 0x13),
    'q': (0, 0x14), 'r': (0, 0x15), 's': (0, 0x16), 't': (0, 0x17),
    'u': (0, 0x18), 'v': (0, 0x19), 'w': (0, 0x1A), 'x': (0, 0x1B),
    'y': (0, 0x1C), 'z': (0, 0x1D),
    'A': (SHIFT, 0x04), 'B': (SHIFT, 0x05), 'C': (SHIFT, 0x06), 'D': (SHIFT, 0x07),
    'E': (SHIFT, 0x08), 'F': (SHIFT, 0x09), 'G': (SHIFT, 0x0A), 'H': (SHIFT, 0x0B),
    'I': (SHIFT, 0x0C), 'J': (SHIFT, 0x0D), 'K': (SHIFT, 0x0E), 'L': (SHIFT, 0x0F),
    'M': (SHIFT, 0x10), 'N': (SHIFT, 0x11), 'O': (SHIFT, 0x12), 'P': (SHIFT, 0x13),
    'Q': (SHIFT, 0x14), 'R': (SHIFT, 0x15), 'S': (SHIFT, 0x16), 'T': (SHIFT, 0x17),
    'U': (SHIFT, 0x18), 'V': (SHIFT, 0x19), 'W': (SHIFT, 0x1A), 'X': (SHIFT, 0x1B),
    'Y': (SHIFT, 0x1C), 'Z': (SHIFT, 0x1D),
    '1': (0, 0x1E), '2': (0, 0x1F), '3': (0, 0x20), '4': (0, 0x21),
    '5': (0, 0x22), '6': (0, 0x23), '7': (0, 0x24), '8': (0, 0x25),
    '9': (0, 0x26), '0': (0, 0x27),
    '!': (SHIFT, 0x1E), '@': (SHIFT, 0x1F), '#': (SHIFT, 0x20), '$': (SHIFT, 0x21),
    '%': (SHIFT, 0x22), '^': (SHIFT, 0x23), '&': (SHIFT, 0x24), '*': (SHIFT, 0x25),
    '(': (SHIFT, 0x26), ')': (SHIFT, 0x27),
    '\n': (0, 0x28),   # Enter
    '\t': (0, 0x2B),   # Tab
    ' ':  (0, 0x2C),   # Space
    '-':  (0, 0x2D), '=':  (0, 0x2E), '[':  (0, 0x2F), ']':  (0, 0x30),
    '\\': (0, 0x31), ';':  (0, 0x33), "'":  (0, 0x34), '`':  (0, 0x35),
    ',':  (0, 0x36), '.':  (0, 0x37), '/':  (0, 0x38),
    '_':  (SHIFT, 0x2D), '+':  (SHIFT, 0x2E), '{':  (SHIFT, 0x2F), '}':  (SHIFT, 0x30),
    '|':  (SHIFT, 0x31), ':':  (SHIFT, 0x33), '"':  (SHIFT, 0x34), '~':  (SHIFT, 0x35),
    '<':  (SHIFT, 0x36), '>':  (SHIFT, 0x37), '?':  (SHIFT, 0x38),
}
# fmt: on

# --------------------------------------------------------------------------- #
#  Read text file
# --------------------------------------------------------------------------- #
try:
    with open("/text.txt", "r") as f:
        text = f.read()
except OSError:
    text = ""

if not text:
    while True:
        time.sleep(60)

# --------------------------------------------------------------------------- #
#  Wait for iPad USB enumeration
# --------------------------------------------------------------------------- #
time.sleep(1)

# --------------------------------------------------------------------------- #
#  FAST type using raw HID reports
#
#  Key trick: each new keydown report implicitly releases the previous key,
#  so we only need 1 report per character (instead of 2).
#  Exception: repeated characters need an empty release in between.
# --------------------------------------------------------------------------- #
report = bytearray(8)
empty = bytearray(8)
prev_mod = -1
prev_key = -1

for ch in text:
    entry = CHAR_MAP.get(ch)
    if entry is None:
        continue  # Skip unmapped characters

    mod, key = entry

    # If same keycode+modifier as previous, must release first
    if key == prev_key and mod == prev_mod:
        kbd.send_report(empty)

    report[0] = mod    # Modifier byte
    report[1] = 0      # Reserved
    report[2] = key    # Keycode
    report[3] = 0
    report[4] = 0
    report[5] = 0
    report[6] = 0
    report[7] = 0
    kbd.send_report(report)

    prev_mod = mod
    prev_key = key

# Final release
kbd.send_report(empty)

# --------------------------------------------------------------------------- #
#  Done — idle forever
# --------------------------------------------------------------------------- #
while True:
    time.sleep(60)
