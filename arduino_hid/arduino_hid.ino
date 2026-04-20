/*
 * USB HID Auto-Typer — HID-only (no USB drive)
 * Waveshare ESP32-S3-Zero + Arduino + TinyUSB
 * German QWERTZ keyboard layout
 *
 * Upload text via serial (upload_text.py on Mac).
 * Plug into iPad → auto-types after 0.55s.
 *
 * ~400 chars/sec on iPad (paced to prevent crash on long text).
 */

#include <Arduino.h>
#include <USB.h>
#include <USBHID.h>
#include <USBHIDKeyboard.h>
#include <LittleFS.h>

// ============================================================
// USB devices (Serial is created by core when CDCOnBoot=cdc)
// ============================================================
USBHIDKeyboard Keyboard;

// ============================================================
// Config
// ============================================================
#define BOOT_DELAY_MS    550   // delay before auto-typing
#define MAX_TEXT_SIZE   32000   // max storable text (bytes)
#define BOOT_BTN         0     // GPIO0 = BOOT button (pause/resume)
#define DEFAULT_CHAR_DELAY_US  2200   // default µs between keystrokes (~450 chars/sec)
#define MIN_CHAR_DELAY_US       500   // min safe pacing (~2000 cps, unrealistic ceiling)
#define MAX_CHAR_DELAY_US     20000   // max pacing floor (~50 cps)
#define BATCH_SIZE        50   // chars between longer pauses
#define BATCH_PAUSE_MS    15   // ms pause every BATCH_SIZE chars (lets iPad render)
#define DEAD            0x80   // dead key flag — OR'd into modifier, stripped before send

// Runtime-tunable pacing (persisted to /speed.txt)
static uint32_t charDelayUs = DEFAULT_CHAR_DELAY_US;

// ============================================================
// German QWERTZ: ASCII → (modifier, keycode)
// iPad Hardware-Tastatur MUST be set to Deutsch.
// 0x02=Shift, 0x40=AltGr(RAlt), DEAD=dead key+Space
// ============================================================
struct KeyMap {
  uint8_t mod;
  uint8_t key;
};

static const KeyMap ASCII_MAP[128] = {
  // 0x00-0x1F: control characters
  {0,0},{0,0},{0,0},{0,0},{0,0},{0,0},{0,0},{0,0},
  {0,0x2A}, // Backspace
  {0,0x2B}, // Tab
  {0,0x28}, // Enter (LF)
  {0,0},{0,0},
  {0,0x28}, // Enter (CR)
  {0,0},{0,0},
  {0,0},{0,0},{0,0},{0,0},{0,0},{0,0},{0,0},{0,0},
  {0,0},{0,0},{0,0},{0,0},{0,0},{0,0},{0,0},{0,0},
  // 0x20-0x2F
  {0,      0x2C}, // Space
  {0x02,   0x1E}, // !  Shift+1
  {0x02,   0x1F}, // "  Shift+2
  {0,      0x31}, // #
  {0x02,   0x21}, // $  Shift+4
  {0x02,   0x22}, // %  Shift+5
  {0x02,   0x23}, // &  Shift+6
  {0x02,   0x31}, // '  Shift+#
  {0x02,   0x25}, // (  Shift+8
  {0x02,   0x26}, // )  Shift+9
  {0x02,   0x30}, // *  Shift++
  {0,      0x30}, // +
  {0,      0x36}, // ,
  {0,      0x38}, // -  (DE: / position)
  {0,      0x37}, // .
  {0x02,   0x24}, // /  Shift+7
  // 0x30-0x39: digits
  {0,0x27},{0,0x1E},{0,0x1F},{0,0x20},{0,0x21},
  {0,0x22},{0,0x23},{0,0x24},{0,0x25},{0,0x26},
  // 0x3A-0x40
  {0x02,   0x37}, // :  Shift+.
  {0x02,   0x36}, // ;  Shift+,
  {0,      0x64}, // <  ISO key
  {0x02,   0x27}, // =  Shift+0
  {0x02,   0x64}, // >  Shift+<
  {0x02,   0x2D}, // ?  Shift+ß
  {0x40,   0x14}, // @  AltGr+Q
  // 0x41-0x5A: uppercase A-Z (Y↔Z swapped)
  {0x02,0x04},{0x02,0x05},{0x02,0x06},{0x02,0x07},{0x02,0x08},{0x02,0x09},
  {0x02,0x0A},{0x02,0x0B},{0x02,0x0C},{0x02,0x0D},{0x02,0x0E},{0x02,0x0F},
  {0x02,0x10},{0x02,0x11},{0x02,0x12},{0x02,0x13},{0x02,0x14},{0x02,0x15},
  {0x02,0x16},{0x02,0x17},{0x02,0x18},{0x02,0x19},{0x02,0x1A},{0x02,0x1B},
  {0x02,0x1D}, // Y
  {0x02,0x1C}, // Z
  // 0x5B-0x60
  {0x40,      0x25}, // [  AltGr+8
  {0x40,      0x2D}, // \  AltGr+ß
  {0x40,      0x26}, // ]  AltGr+9
  {DEAD,      0x35}, // ^  dead key, then Space
  {0x02,      0x38}, // _  Shift+-
  {DEAD|0x02, 0x2E}, // `  dead key Shift+´, then Space
  // 0x61-0x7A: lowercase a-z (y↔z swapped)
  {0,0x04},{0,0x05},{0,0x06},{0,0x07},{0,0x08},{0,0x09},
  {0,0x0A},{0,0x0B},{0,0x0C},{0,0x0D},{0,0x0E},{0,0x0F},
  {0,0x10},{0,0x11},{0,0x12},{0,0x13},{0,0x14},{0,0x15},
  {0,0x16},{0,0x17},{0,0x18},{0,0x19},{0,0x1A},{0,0x1B},
  {0,0x1D}, // y
  {0,0x1C}, // z
  // 0x7B-0x7F
  {0x40, 0x24}, // {  AltGr+7
  {0x40, 0x64}, // |  AltGr+<
  {0x40, 0x27}, // }  AltGr+0
  {0x40, 0x30}, // ~  AltGr++
  {0,0}         // DEL
};

// ============================================================
// HID typing engine (raw reports for max speed)
// ============================================================
static KeyReport kr;

static void sendKey(uint8_t modifier, uint8_t keycode) {
  kr.modifiers = modifier;
  kr.reserved = 0;
  kr.keys[0] = keycode;
  kr.keys[1] = 0; kr.keys[2] = 0;
  kr.keys[3] = 0; kr.keys[4] = 0; kr.keys[5] = 0;
  Keyboard.sendReport(&kr);
}

static void releaseAllKeys() {
  memset(&kr, 0, sizeof(kr));
  Keyboard.sendReport(&kr);
}

void typeFast(const String &text) {
  uint8_t prevMod = 0xFF, prevKey = 0xFF;
  bool paused = false;
  size_t batch = 0;

  for (size_t i = 0; i < text.length(); i++) {
    // BOOT button: pause/resume toggle
    if (digitalRead(BOOT_BTN) == LOW) {
      releaseAllKeys();
      paused = !paused;
      // Wait for button release (debounce)
      while (digitalRead(BOOT_BTN) == LOW) delay(10);
      delay(50);
      if (paused) {
        // Wait until button pressed again to resume
        while (paused) {
          if (digitalRead(BOOT_BTN) == LOW) {
            paused = false;
            while (digitalRead(BOOT_BTN) == LOW) delay(10);
            delay(50);
          }
          delay(1);
        }
      }
    }

    char c = text[i];
    if (c == '\r') continue;

    // German umlauts + ß (UTF-8: 0xC3 + second byte)
    if ((uint8_t)c == 0xC3 && i + 1 < text.length()) {
      uint8_t mod = 0, key = 0;
      switch ((uint8_t)text[i + 1]) {
        case 0xA4: key = 0x34; break;             // ä
        case 0x84: key = 0x34; mod = 0x02; break;  // Ä
        case 0xB6: key = 0x33; break;             // ö
        case 0x96: key = 0x33; mod = 0x02; break;  // Ö
        case 0xBC: key = 0x2F; break;             // ü
        case 0x9C: key = 0x2F; mod = 0x02; break;  // Ü
        case 0x9F: key = 0x2D; break;             // ß
      }
      i++; // consume second UTF-8 byte
      if (key == 0) continue; // unknown sequence
      if (key == prevKey && mod == prevMod) releaseAllKeys();
      sendKey(mod, key);
      prevMod = mod;
      prevKey = key;
      delayMicroseconds(charDelayUs);
      if (++batch >= BATCH_SIZE) { batch = 0; delay(BATCH_PAUSE_MS); }
      continue;
    }

    if (c < 0 || c > 127) continue; // skip other non-ASCII

    KeyMap km = ASCII_MAP[(uint8_t)c];
    if (km.key == 0 && c != '\n' && c != '\t' && c != '\b') continue;

    bool isDead = (km.mod & DEAD) != 0;
    uint8_t mod = km.mod & ~DEAD;

    // Release before repeating same key
    if (km.key == prevKey && mod == prevMod) {
      releaseAllKeys();
    }

    sendKey(mod, km.key);

    // Dead key (^ `): release, then Space to materialize
    if (isDead) {
      releaseAllKeys();
      delayMicroseconds(charDelayUs);
      sendKey(0, 0x2C);
      batch++;
    }

    prevMod = isDead ? (uint8_t)0 : mod;
    prevKey = isDead ? (uint8_t)0x2C : km.key;

    // Pace output so iPad text rendering keeps up
    delayMicroseconds(charDelayUs);
    if (++batch >= BATCH_SIZE) {
      batch = 0;
      delay(BATCH_PAUSE_MS);
    }
  }
  releaseAllKeys();
}

// ============================================================
// LittleFS text storage
// ============================================================
String loadText() {
  File f = LittleFS.open("/text.txt", "r");
  if (!f) return "";
  String t = f.readString();
  f.close();
  return t;
}

bool saveText(const String &text) {
  File f = LittleFS.open("/text.txt", "w");
  if (!f) return false;
  f.print(text);
  f.close();
  return true;
}

void loadSpeed() {
  File f = LittleFS.open("/speed.txt", "r");
  if (!f) return;
  uint32_t v = f.readString().toInt();
  f.close();
  if (v >= MIN_CHAR_DELAY_US && v <= MAX_CHAR_DELAY_US) charDelayUs = v;
}

bool saveSpeed(uint32_t v) {
  if (v < MIN_CHAR_DELAY_US || v > MAX_CHAR_DELAY_US) return false;
  File f = LittleFS.open("/speed.txt", "w");
  if (!f) return false;
  f.print(v);
  f.close();
  charDelayUs = v;
  return true;
}

// ============================================================
// Serial command handler
// ============================================================
static String serialBuf;
static bool receiving = false;
static String receivedText;

void handleSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    serialBuf += c;

    // Process complete lines
    int nl = serialBuf.indexOf('\n');
    while (nl >= 0) {
      String line = serialBuf.substring(0, nl);
      line.trim();
      serialBuf = serialBuf.substring(nl + 1);

      if (receiving) {
        if (line == "EOF") {
          // Save received text
          if (saveText(receivedText)) {
            Serial.printf("OK:%d\n", receivedText.length());
          } else {
            Serial.println("ERR:SAVE_FAILED");
          }
          receiving = false;
          receivedText = "";
        } else {
          if (receivedText.length() > 0) receivedText += "\n";
          receivedText += line;
        }
      } else if (line == "SAVE") {
        receiving = true;
        receivedText = "";
      } else if (line == "STATUS") {
        String t = loadText();
        Serial.printf("STORED:%d bytes SPEED:%u us\n", t.length(), charDelayUs);
      } else if (line.startsWith("SPEED ")) {
        uint32_t v = line.substring(6).toInt();
        if (saveSpeed(v)) {
          Serial.printf("OK:SPEED:%u us\n", charDelayUs);
        } else {
          Serial.printf("ERR:SPEED_RANGE %u-%u\n", MIN_CHAR_DELAY_US, MAX_CHAR_DELAY_US);
        }
      } else if (line == "TYPE") {
        Serial.println("TYPING...");
        String t = loadText();
        if (t.length() > 0) {
          typeFast(t);
          Serial.printf("DONE:%d chars\n", t.length());
        } else {
          Serial.println("DONE:0 (no text stored)");
        }
      }

      nl = serialBuf.indexOf('\n');
    }
  }
}

// ============================================================
// Setup
// ============================================================
void setup() {
  // BOOT button as pause toggle (internal pull-up)
  pinMode(BOOT_BTN, INPUT_PULLUP);

  // Initialize LittleFS
  if (!LittleFS.begin(true, "/littlefs", 10, "spiffs")) {
    // Format failed — continue anyway
  }
  loadSpeed();

  // Setup USB: HID keyboard (CDC serial auto-started by core)
  Keyboard.begin();
  USB.begin();

  // Wait for host USB enumeration
  delay(BOOT_DELAY_MS);

  // Wake-up: send empty key release so host recognizes keyboard
  releaseAllKeys();
  delay(50);

  // Auto-type stored text
  String text = loadText();
  if (text.length() > 0) {
    typeFast(text);
  }
}

// ============================================================
// Main loop — handle serial commands from Mac
// ============================================================
void loop() {
  handleSerial();
  delay(1);
}
