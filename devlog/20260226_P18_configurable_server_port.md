# P18 — GUI 서버 포트 설정 및 자동 탐색

**Date:** 2026-02-26

## 배경

Windows Hyper-V가 활성화된 환경에서 TCP 포트 범위를 예약하여, 하드코딩된 8080 포트에
서버가 바인딩할 수 없는 문제가 발생한다.

```
ERROR: [Errno 13] error while attempting to bind on address ('127.0.0.1', 8080):
[winerror 10013] 액세스 권한에 의해 숨겨진 소켓에 액세스를 시도했습니다
```

`netsh interface ipv4 show excludedportrange protocol=tcp` 결과, 8080이
Hyper-V 예약 범위 8041-8140에 포함되어 있음을 확인.

## 목표

1. GUI Controls 영역에 포트 입력 필드 추가
2. Start Server 시 포트 사용 가능 여부를 사전 검증
3. 사용 불가 시 사용자에게 자동 탐색 제안, 찾은 포트를 설정에 저장
4. 다음 실행부터 저장된 포트를 기본값으로 사용

## 설계

### 1. 포트 입력 UI

Controls 섹션의 Start/Stop 버튼 위에 `Port:` 라벨 + Entry 위젯 추가.

- 기본값: `ScodaDesktop.cfg`의 `port` 값 (없으면 8080)
- 서버 실행 중에는 Entry를 `disabled` 상태로 전환

### 2. 포트 가용성 검증

`start_server()` 진입 시, 서버 프로세스 시작 **전에** `socket.bind()` 테스트로 확인.

```python
import socket

def _check_port_available(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
        return True
    except OSError:
        return False
```

이 방식은 Hyper-V 예약 포트, 다른 프로세스 점유 모두 감지한다.

### 3. 자동 포트 탐색 + 사용자 확인

포트 사용 불가 시 흐름:

1. `messagebox.askyesno()` — "Port {N} is not available. Find an available port automatically?"
2. Yes → `_find_available_port(start+1, 65535)` — 순차 탐색
3. 찾으면 → Entry 업데이트 + `ScodaDesktop.cfg`에 `port` 키 저장 + 서버 시작 진행
4. 못 찾으면 → 에러 메시지, 서버 시작 중단
5. No → 서버 시작 중단

### 4. 설정 저장

기존 `ScodaDesktop.cfg` (JSON) 활용. Hub SSL fallback에서 이미 `_load_settings()` /
`_save_settings()` + `self._settings` 딕셔너리 패턴이 구현되어 있다.

```json
{
  "ssl_noverify": false,
  "port": 8341
}
```

초기화 시: `self.port = self._settings.get("port", 8080)`

### 5. subprocess 모드 포트 전달

`app.py`의 `__main__` 블록에 `--port` CLI 인자 추가.
GUI → subprocess 호출 시 `--port {self.port}` 전달.

`serve.py`도 동일하게 `--port` 인자 추가하여 CLI 직접 실행 시에도 포트 지정 가능.

## 수정 파일

| 파일 | 작업 |
|------|------|
| `scoda_engine/gui.py` | Port Entry 위젯, 검증 로직, 설정 저장, subprocess `--port` 전달 |
| `scoda_engine/app.py` | `__main__`에 `--port` argparse 인자 추가 |
| `scoda_engine/serve.py` | `--port` argparse 인자 추가, 하드코딩 8080 제거 |

## 기존 코드 활용

- `_get_settings_path()`, `_load_settings()`, `_save_settings()` — 재사용 (신규 키 `port` 추가만)
- `self._settings` 딕셔너리 — `ssl_noverify`와 동일 패턴
- `_update_status()` — 포트 Entry 활성/비활성 전환 추가

## 검증 항목

- [ ] 포트 번호 범위 검증 (1024-65535)
- [ ] 사용 불가 포트로 시작 시 다이얼로그 표시 확인
- [ ] 자동 탐색 후 설정 파일에 포트 저장 확인
- [ ] 다음 실행 시 저장된 포트가 Entry 기본값으로 표시 확인
- [ ] subprocess 모드에서 `--port` 정상 전달 확인
- [ ] threaded 모드 (frozen)에서 `self.port` 반영 확인
- [ ] 기존 테스트 276개 통과
