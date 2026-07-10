# 044. Registry 반복 스캔 시 temp-dir 누수 수정

**날짜:** 2026-07-10
**유형:** fix
**관련:** #035 (P29 Multi-Package Serving), Hub sync
**커밋:** `d052e13`

---

## 증상

장기 실행 프로덕션 서버에서 `/tmp/scoda_*/data.db` 임시 디렉토리가 무한정 누적.
약 3.5개월간 **2.9G / 3198개 디렉토리**가 쌓임.

## 원인

### 1차 원인 — `Registry.scan()`의 인스턴스 미정리

`PackageRegistry.scan()`이 `self._packages`를 덮어쓰며 재구축할 때, 기존에 열려
있던 `ScodaPackage` 인스턴스를 닫지 않았다. 각 `ScodaPackage`는 `.scoda` ZIP을
temp dir에 추출해 두는데, 참조가 교체되면서 그 temp dir이 고아가 됨.

주기적 Hub sync(`SCODA_HUB_SYNC`, 일 1회)가 실행마다 `scan()`을 2회 호출 →
하루 약 `2 × N`개(N = 패키지 수)의 temp dir 누수.

### 2차 원인 (가중) — per-instance `atexit.register`

각 `ScodaPackage`가 생성 시 `atexit.register(self.close)`를 호출했다. 이것이
모든 인스턴스를 프로세스 생명주기 내내 atexit 레지스트리에 고정(pin)하여 GC를
막았고, 결과적으로 고아 인스턴스의 어떤 정리 경로도 동작하지 못하게 만듦.

## 수정

**파일:** `core/scoda_engine_core/scoda_package.py` (+44 / −6)

1. **`scan()` 원자적 교체**: 로컬 dict에 새 레지스트리를 빌드한 뒤 원자적으로
   swap. 동시에 실행되는 `get_db()`가 절반만 빌드된 레지스트리를 보지 않도록
   보장. swap 이후 **이전 패키지들의 temp dir을 close**.
   - 진행 중인 sqlite 연결은 영향 없음 — Linux에서는 열린 fd가 unlink 후에도
     연결이 닫힐 때까지 유지되므로 in-flight 쿼리가 안전하게 완료됨.
2. **per-instance `atexit.register(self.close)` 제거** — ref-pinning 누수 제거.
3. **`ScodaPackage.__del__` 추가** — GC 시점 정리 안전망.
4. **`PackageRegistry.close_all()`를 atexit에 1회 등록** — 프로세스 종료 시
   보유 중인 패키지 일괄 정리.

## 검증

3개 패키지, 7회 반복 스캔 → temp dir 3개 유지(수정 전이라면 21개).
재스캔 후 `get_db()` 정상 동작, `close_all()` 호출 → temp dir 0개.
