"""
save_text.py - 클립보드 텍스트를 CIRCUITPY 보드에 저장하는 Windows 스크립트

사용법:
    1. 저장할 텍스트를 클립보드에 복사 (Ctrl+C)
    2. 이 스크립트 실행: python save_text.py
    3. CIRCUITPY 드라이브의 text.txt에 자동 저장됨

필요 패키지: pip install pyperclip
"""

import os
import sys
import string

def find_circuitpy_drive():
    """CIRCUITPY 드라이브 문자를 자동 탐지합니다."""
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if not os.path.exists(drive):
            continue
        # CIRCUITPY 드라이브에는 boot_out.txt 파일이 존재합니다
        if os.path.isfile(os.path.join(drive, "boot_out.txt")):
            return drive
        # 또는 드라이브 이름이 CIRCUITPY인지 확인
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.kernel32.GetVolumeInformationW(
                drive, buf, 256, None, None, None, None, 0
            )
            if buf.value == "CIRCUITPY":
                return drive
        except Exception:
            pass
    return None


def main():
    # --- pyperclip 임포트 ---
    try:
        import pyperclip
    except ImportError:
        print("[오류] pyperclip 패키지가 설치되지 않았습니다.")
        print("       설치 명령어: pip install pyperclip")
        sys.exit(1)

    # --- 클립보드에서 텍스트 읽기 ---
    try:
        text = pyperclip.paste()
    except Exception as e:
        print(f"[오류] 클립보드를 읽을 수 없습니다: {e}")
        sys.exit(1)

    if not text or not text.strip():
        print("[오류] 클립보드가 비어 있습니다. 먼저 텍스트를 복사하세요 (Ctrl+C).")
        sys.exit(1)

    # --- CIRCUITPY 드라이브 찾기 ---
    drive = find_circuitpy_drive()
    if drive is None:
        print("[오류] CIRCUITPY 드라이브를 찾을 수 없습니다.")
        print("       보드가 PC 모드로 연결되어 있는지 확인하세요.")
        print("       (BOOT 버튼을 누른 상태로 USB 케이블 연결)")
        sys.exit(1)

    # --- text.txt에 저장 ---
    file_path = os.path.join(drive, "text.txt")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print(f"[오류] 파일 저장 실패: {e}")
        sys.exit(1)

    char_count = len(text)
    line_count = text.count("\n") + 1
    print(f"[완료] 텍스트가 저장되었습니다!")
    print(f"       경로: {file_path}")
    print(f"       글자 수: {char_count:,}자 / {line_count}줄")
    print()
    print("이제 보드를 iPad에 연결하면 자동으로 텍스트가 입력됩니다.")


if __name__ == "__main__":
    main()
