"""
boot.py - USB HID Dongle Boot Configuration
Waveshare ESP32-S3-Zero

IMPORTANT: Do NOT hold BOOT while plugging in — that enters ROM download mode.

How to switch modes:
  1. Plug in the board normally (don't hold any button)
  2. The LED blinks BLUE for 3 seconds
  3. During those 3 seconds:
     - Press BOOT button → PC mode  (LED turns GREEN, CIRCUITPY drive appears)
     - Do nothing         → iPad mode (LED turns off, auto-types text)
"""

import time
import board
import digitalio
import storage
import usb_cdc
import usb_hid
import neopixel

# --- LED setup (WS2812 on GPIO21) ---
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

# --- Button setup (GPIO0, active-low) ---
button = digitalio.DigitalInOut(board.BUTTON)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# --- 3-second window: blink blue, wait for BOOT press ---
pc_mode = False
for i in range(30):  # 30 x 0.1s = 3 seconds
    # Blink blue LED (on/off every 0.3s)
    pixel[0] = (0, 0, 80) if (i % 3 < 2) else (0, 0, 0)
    if not button.value:  # BOOT button pressed
        pc_mode = True
        break
    time.sleep(0.1)

button.deinit()

if pc_mode:
    # PC MODE: green LED, USB drive stays visible
    pixel[0] = (0, 80, 0)
else:
    # iPAD MODE: LED off, disable everything except HID keyboard
    pixel[0] = (0, 0, 0)
    pixel.deinit()
    storage.disable_usb_drive()
    usb_cdc.disable()
    usb_hid.enable((usb_hid.Device.KEYBOARD,))
