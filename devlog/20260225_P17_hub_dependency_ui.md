# P17: Hub Dependency UI 표시 + 다운로드 확인 다이얼로그

**Date:** 2026-02-25

---

## 배경

Hub 패키지 목록에서 dependency 정보가 보이지 않아 사용자가 패키지 간 의존 관계를 파악할 수 없다.
다운로드 시 `resolve_download_order()`로 dependency를 자동 해석하지만, 뭘 같이 받는지 사전 확인이 없다.
두 가지를 모두 추가한다.

## 변경 파일

- `scoda_engine/gui.py` — UI 변경 (2곳)

## 변경 내용

### 1. Listbox 항목에 dependency 표시

**`_refresh_hub_listbox()` 메서드 수정**

현재 포맷:
```
 [NEW] trilobase  v0.2.2  (5.3 MB)
 [UPD] trilobase  v0.1.0 -> v0.2.2  (5.3 MB)
```

변경 후:
```
 [NEW] trilobase  v0.2.2  (5.3 MB)  [requires: paleocore]
 [UPD] trilobase  v0.1.0 -> v0.2.2  (5.3 MB)  [requires: paleocore]
```

- `hub_entry.get("dependencies", {})` 에서 키 목록 추출
- dependency가 없으면 suffix 없음
- dependency가 있으면 ` [requires: dep1, dep2]` 추가

### 2. 다운로드 전 확인 다이얼로그

**`_start_hub_download()` 메서드 수정**

Download/Download All 클릭 후, 백그라운드 스레드 시작 **전에**:
1. 각 item에 대해 `resolve_download_order()` 호출하여 전체 다운로드 목록 산출
2. `messagebox.askyesno()` 확인창 표시:
   ```
   Download Confirmation

   trilobase v0.2.2 (5.3 MB)
   + paleocore v0.1.3 (2.1 MB)  [dependency]

   Total: 2 package(s), 7.4 MB

   Proceed with download?
   ```
3. 사용자가 No 선택 시 다운로드 취소
4. dependency 없이 단일 패키지만 받는 경우에도 확인창 표시 (패키지명, 버전, 크기 확인)

## 구현 세부사항

- `_format_size()` 메서드 재사용 (이미 존재)
- `resolve_download_order()`는 메인 스레드에서 호출 (Hub index는 이미 메모리에 있으므로 네트워크 없음, 즉시 반환)
- 확인 다이얼로그는 메인 스레드에서 `messagebox.askyesno()` 사용 (기존 패턴)

## Verification

```bash
pytest tests/test_hub_client.py -v
pytest tests/ -v
```

GUI 수동 테스트:
- Hub 패키지 목록에서 dependency 있는 패키지에 `[requires: ...]` 표시 확인
- Download 클릭 시 확인 다이얼로그에 dependency 포함 패키지 목록 표시 확인
- No 클릭 시 다운로드 취소 확인
- Download All 클릭 시에도 동일하게 확인 다이얼로그 동작 확인
