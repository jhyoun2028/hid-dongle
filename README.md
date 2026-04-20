# USB HID Auto-Typer Dongle

Waveshare ESP32-S3-Zero를 USB 키보드로 만들어,
iPad에 꽂으면 저장된 텍스트를 자동으로 타이핑합니다.

두 가지 펌웨어 버전이 있습니다:

| 버전 | 속도 | 텍스트 업로드 방식 | 난이도 |
|------|------|-------------------|--------|
| **Arduino (권장)** | ~500자/초 | Mac/PC에서 시리얼로 전송 | 중 |
| CircuitPython | ~60자/초 | USB 드라이브에 파일 복사 | 하 |

## 프로젝트 구조

```
Projects_HID/
├── arduino_hid/
│   ├── arduino_hid.ino   ← Arduino 펌웨어 (최고 속도)
│   └── build/            ← 컴파일된 바이너리
├── code.py               ← CircuitPython 펌웨어 (간단 버전)
├── upload_text.py        ← Mac/PC에서 시리얼로 텍스트 업로드
├── save_text.py          ← CircuitPython용 텍스트 저장 스크립트
├── text.txt              ← 타이핑할 텍스트 (샘플)
└── README.md
```

---

# Option A: Arduino 펌웨어 (권장 — 최고 속도)

1ms USB 폴링 + raw HID 리포트로 **~500자/초** 타이핑 속도를 달성합니다.
텍스트는 LittleFS에 저장되어 재부팅해도 유지됩니다.

## A-1. 펌웨어 플래싱

### 준비물
```bash
pip3 install esptool pyserial
```

### 보드를 다운로드 모드로 진입

뾰족한 도구(펜 끝, 이쑤시개 등)를 사용하세요. 버튼이 매우 작습니다.

1. **BOOT 버튼** (왼쪽)을 **누른 상태**에서
2. **RESET 버튼** (오른쪽)을 한번 눌렀다 떼기
3. BOOT 버튼에서 손 떼기

Mac에서 포트 확인:
```bash
ls /dev/cu.usb*
```

### 플래싱 실행

```bash
# 기존 플래시 지우기
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* erase_flash

# Arduino 펌웨어 쓰기 (merged.bin = 부트로더+파티션+앱 통합)
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* write_flash -z 0x0 \
  arduino_hid/build/arduino_hid.ino.merged.bin
```

플래싱 후 보드를 뽑았다가 다시 꽂으면 Arduino 펌웨어로 부팅됩니다.

## A-2. 텍스트 업로드 (Mac에서)

보드를 Mac에 USB로 연결한 상태에서:

```bash
# 클립보드에서 업로드
python3 upload_text.py

# 파일에서 업로드
python3 upload_text.py -f mytext.txt

# 직접 텍스트 지정
python3 upload_text.py -t "Hello, iPad!"

# 저장된 텍스트 확인
python3 upload_text.py --status

# 수동으로 타이핑 트리거
python3 upload_text.py --type
```

## A-3. iPad에서 사용

```
1. iPad에서 텍스트 입력 앱 열기 (메모, Safari 등)
2. 텍스트 입력 필드 터치 (커서 활성화)
3. 보드를 USB-C 케이블로 iPad에 연결
4. ~1.5초 후 자동 타이핑 시작!
```

## A-4. 타이핑 속도 (Arduino)

| 항목 | 값 |
|------|-----|
| USB 폴링 간격 | 1ms (TinyUSB 기본값) |
| 1글자 (일반) | ~1ms (1 USB 리포트) |
| 1글자 (같은 문자 반복) | ~2ms (릴리스 + 키다운) |
| 1000자 | ~2초 |

## A-5. 다시 텍스트 변경하기

보드를 Mac에 꽂으면 USB CDC 시리얼 포트가 나타납니다.
`upload_text.py`로 새 텍스트를 업로드하면 됩니다.
저장된 텍스트는 LittleFS에 보관되어 전원 꺼도 유지됩니다.

> **참고:** Arduino 펌웨어에서는 CIRCUITPY 드라이브가 나타나지 않습니다.
> 텍스트 업로드는 반드시 `upload_text.py` 시리얼 스크립트를 사용하세요.

## A-6. 직접 컴파일하기 (선택사항)

미리 컴파일된 바이너리가 `arduino_hid/build/`에 있으므로
직접 컴파일할 필요는 없습니다. 코드를 수정하고 싶다면:

```bash
# arduino-cli 설치
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh -s -- --dest ~/.local/bin

# ESP32 보드 패키지 설치
~/.local/bin/arduino-cli core install esp32:esp32

# 컴파일
~/.local/bin/arduino-cli compile \
  --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=4M,PartitionScheme=huge_app,PSRAM=enabled,CPUFreq=240,FlashMode=qio" \
  --output-dir arduino_hid/build \
  arduino_hid
```

> **macOS ARM64 참고:** Arduino의 ctags 도구가 x86_64 바이너리라 동작하지 않습니다.
> `~/Library/Arduino15/packages/builtin/tools/ctags/5.8-arduino11/ctags`를
> `exit 0`만 하는 스텁 스크립트로 교체하면 해결됩니다.

---

# Option B: CircuitPython 펌웨어 (간단 버전)

설정이 더 쉽지만 타이핑 속도가 느립니다 (~60자/초).

## B-1. CircuitPython 플래싱

```bash
pip3 install esptool

# 다운로드 모드 진입 (BOOT 누른 채로 RESET 클릭)
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* erase_flash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* write_flash -z 0x0 firmware.bin
```

플래싱 후 **CIRCUITPY** 드라이브가 나타납니다.

## B-2. 라이브러리 설치

`adafruit_hid` 라이브러리가 필요합니다:

1. https://circuitpython.org/libraries 에서 **Bundle** 다운로드
2. ZIP 해제 후 `lib/adafruit_hid/` 폴더를 CIRCUITPY의 `lib/`에 복사

## B-3. 파일 복사

CIRCUITPY 드라이브에 복사:
```bash
cp code.py /Volumes/CIRCUITPY/
cp text.txt /Volumes/CIRCUITPY/
```

## B-4. 텍스트 변경

CIRCUITPY 드라이브의 `text.txt`를 직접 편집하거나:
```bash
cp 새텍스트.txt /Volumes/CIRCUITPY/text.txt
```

## B-5. 타이핑 속도 (CircuitPython)

| 항목 | 값 |
|------|-----|
| USB 폴링 간격 | 8ms (하드코딩, 변경 불가) |
| 1글자 | ~8ms (1 raw HID 리포트) |
| 1000자 | ~16초 |

---

# 문제 해결

### 다운로드 모드 진입이 안 돼요
- 펜 끝이나 이쑤시개로 BOOT/RESET 버튼을 정확히 눌러야 합니다
- 순서: BOOT 누른 채로 → RESET 눌렀다 떼기 → BOOT 떼기
- `ls /dev/cu.usb*`에 새 포트가 나타나면 성공

### 시리얼 포트가 안 보여요 (Arduino)
- 보드가 정상 부팅된 상태여야 합니다 (다운로드 모드 아님)
- `ls /dev/cu.usbmodem*`로 확인
- Mac에서 "시스템 정보 > USB"에서 ESP32-S3 확인

### iPad에서 타이핑이 안 돼요
- 텍스트 입력 필드에 커서가 활성화되어 있는지 확인
- 연결 후 1.5초 기다리기 (USB 열거 시간)
- Arduino: `upload_text.py --status`로 텍스트가 저장되어 있는지 확인
- CircuitPython: CIRCUITPY에 `text.txt` 파일이 있는지 확인

### Arduino에서 CircuitPython으로 돌아가려면
다운로드 모드 진입 후 CircuitPython `.bin` 파일을 다시 플래싱:
```bash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* erase_flash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem* write_flash -z 0x0 firmware.bin
```

---

# 하드웨어 정보

| 항목 | 값 |
|------|-----|
| 보드 | Waveshare ESP32-S3-Zero |
| MCU | ESP32-S3FH4R2 (4MB Flash, 2MB PSRAM) |
| USB | 네이티브 USB OTG (Full-Speed 12Mbps) |
| BOOT 버튼 | GPIO0 (왼쪽, 표면실장) |
| RESET 버튼 | 오른쪽, 표면실장 |
| NeoPixel LED | GPIO21 |
