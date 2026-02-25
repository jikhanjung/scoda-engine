# 020 — EXE 및 GUI 윈도우 아이콘 적용

**Date:** 2026-02-25

## 배경

`ScodaDesktop.png` 아이콘 이미지가 준비되었으나, PyInstaller EXE와 tkinter GUI 윈도우에 적용되지 않은 상태.

## 변경 내용

### 1. ScodaDesktop.ico 멀티 사이즈 변환

- 256x256 PNG → ICO 변환 (Pillow 사용)
- 4개 표준 사이즈 포함: 16x16, 32x32, 48x48, 256x256
- Windows 탐색기/작업표시줄에서 정상 표시를 위해 멀티 사이즈 필수

### 2. PyInstaller EXE 아이콘 (`ScodaDesktop.spec`)

- ScodaDesktop.exe, ScodaMCP.exe 모두 `icon='ScodaDesktop.ico'` 설정
- `datas`에 `('ScodaDesktop.ico', '.')` 추가 (onefile 빌드 시 `_MEIPASS`에 포함)

### 3. tkinter GUI 윈도우/작업표시줄 아이콘 (`scoda_engine/gui.py`)

- `_set_window_icon()` 메서드 추가
- `root.iconbitmap()`으로 윈도우 좌상단 + 작업표시줄 아이콘 설정
- Frozen 환경: `sys._MEIPASS`에서 ico 로드
- Dev 환경: 프로젝트 루트에서 ico 로드
- `from pathlib import Path` import 추가

## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `ScodaDesktop.ico` | 멀티 사이즈 ICO (16/32/48/256) |
| `ScodaDesktop.spec` | 두 EXE에 `icon=` 설정 + datas에 ico 번들 |
| `scoda_engine/gui.py` | `_set_window_icon()` 메서드 추가 |
