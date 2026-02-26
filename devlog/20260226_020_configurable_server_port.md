# 020 — GUI 서버 포트 설정 및 자동 탐색 (P18)

**Date:** 2026-02-26

## 배경

Windows Hyper-V 활성화 환경에서 TCP 포트 예약 범위(8041-8140)에 기본 포트 8080이
포함되어 서버 바인딩 실패 (`WinError 10013`).

## 변경 내용

### `scoda_engine/gui.py`

- Controls 섹션에 **Port 입력 필드** 추가 (Start/Stop 버튼 위)
- `start_server()` 진입 시 포트 검증 추가:
  - 포트 번호 범위 검증 (1024-65535)
  - `socket.bind()` 테스트로 사전 가용성 확인
  - 사용 불가 시 "자동 탐색?" 다이얼로그 표시
  - 찾은 포트를 `ScodaDesktop.cfg`에 `port` 키로 저장
- 서버 실행 중 포트 Entry 비활성화
- subprocess 모드에서 `--port` 인자 전달
- 신규 메서드: `_check_port_available()`, `_find_available_port()`, `_save_port()`

### `scoda_engine/app.py`

- `__main__` 블록에 `--port` argparse 인자 추가

### `scoda_engine/serve.py`

- `--port` argparse 인자 추가, 하드코딩 8080 제거
- `open_browser()` 포트 파라미터화

## 설정 저장 형식

기존 `ScodaDesktop.cfg` (JSON) 재사용:

```json
{
  "ssl_noverify": false,
  "port": 8341
}
```

## 테스트

- 기존 276개 테스트 전체 통과
