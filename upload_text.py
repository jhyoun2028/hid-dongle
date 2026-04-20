"""
upload_text.py — Upload text to the ESP32-S3 HID dongle via serial.

Usage:
    python3 upload_text.py                 # Upload from clipboard
    python3 upload_text.py -f file.txt     # Upload from file
    python3 upload_text.py -t "some text"  # Upload literal text
    python3 upload_text.py --type          # Trigger typing manually
    python3 upload_text.py --status        # Check stored text size
    python3 upload_text.py --speed 3500    # Set µs-per-char pacing (500–20000)
"""

import sys
import glob
import time
import argparse

def find_serial_port():
    """Auto-detect the ESP32-S3 serial port."""
    # macOS
    ports = glob.glob("/dev/cu.usbmodem*")
    if ports:
        return ports[0]
    # Linux
    ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    if ports:
        return ports[0]
    # Windows
    import serial.tools.list_ports
    for p in serial.tools.list_ports.comports():
        if "USB" in p.description or "ESP" in p.description:
            return p.device
    return None

def main():
    parser = argparse.ArgumentParser(description="Upload text to HID dongle")
    parser.add_argument("-f", "--file", help="Read text from file")
    parser.add_argument("-t", "--text", help="Use literal text")
    parser.add_argument("-p", "--port", help="Serial port (auto-detected)")
    parser.add_argument("--type", action="store_true", help="Trigger typing")
    parser.add_argument("--status", action="store_true", help="Check status")
    parser.add_argument("--speed", type=int, help="Set µs-per-char pacing (500–20000)")
    args = parser.parse_args()

    try:
        import serial
    except ImportError:
        print("[Error] pyserial not installed. Run: pip3 install pyserial")
        sys.exit(1)

    # Find port
    port = args.port or find_serial_port()
    if not port:
        print("[Error] No serial port found. Is the board plugged in?")
        sys.exit(1)

    print(f"[Info] Using port: {port}")

    ser = serial.Serial(port, 115200, timeout=3)
    time.sleep(0.5)  # Wait for connection
    ser.reset_input_buffer()

    if args.status:
        ser.write(b"STATUS\n")
        time.sleep(0.5)
        resp = ser.read(ser.in_waiting).decode(errors="replace").strip()
        print(f"[Status] {resp}")
        ser.close()
        return

    if args.speed is not None:
        ser.write(f"SPEED {args.speed}\n".encode())
        time.sleep(0.5)
        resp = ser.read(ser.in_waiting).decode(errors="replace").strip()
        print(f"[Speed] {resp}")
        ser.close()
        return

    if args.type:
        ser.write(b"TYPE\n")
        time.sleep(0.5)
        resp = ser.read(ser.in_waiting).decode(errors="replace").strip()
        print(f"[Type] {resp}")
        # Wait for DONE
        start = time.time()
        while time.time() - start < 60:
            if ser.in_waiting:
                line = ser.readline().decode(errors="replace").strip()
                print(f"[Type] {line}")
                if "DONE" in line:
                    break
        ser.close()
        return

    # Get text to upload
    text = None
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        # Clipboard
        try:
            import pyperclip
            text = pyperclip.paste()
        except ImportError:
            try:
                import subprocess
                text = subprocess.run(
                    ["pbpaste"], capture_output=True, text=True
                ).stdout
            except Exception:
                print("[Error] No text source. Use -f, -t, or install pyperclip")
                sys.exit(1)

    if not text or not text.strip():
        print("[Error] No text to upload.")
        sys.exit(1)

    print(f"[Info] Uploading {len(text)} characters...")

    # Send SAVE command + text + EOF
    ser.write(b"SAVE\n")
    time.sleep(0.1)
    ser.write(text.encode("utf-8"))
    ser.write(b"\nEOF\n")
    ser.flush()

    # Wait for response
    time.sleep(1)
    resp = ser.read(ser.in_waiting).decode(errors="replace").strip()
    print(f"[Response] {resp}")

    if resp.startswith("OK:"):
        saved_len = resp.split(":")[1]
        print(f"[Done] {saved_len} bytes saved to dongle.")
        print("       Unplug and connect to iPad to auto-type!")
    else:
        print("[Warning] Unexpected response. Text may not have saved.")

    ser.close()

if __name__ == "__main__":
    main()
