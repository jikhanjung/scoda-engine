# SCODA Desktop Release Guide

이 문서는 SCODA Desktop의 **데이터 수정 → .scoda 패키지 생성 → 릴리스 → 배포** 전체 프로세스를 설명합니다.

SCODA(Self-Contained Data Artifact) 원칙에 따라 각 릴리스는 **불변(immutable)**이며, 버전 번호로 식별됩니다.

---

## 목차

1. [버전 번호 규칙](#버전-번호-규칙)
2. [릴리스 절차](#릴리스-절차)
3. [배포 절차](#배포-절차)
4. [Overlay DB 호환성](#overlay-db-호환성)
5. [검증 및 테스트](#검증-및-테스트)
6. [주의사항](#주의사항)

---

## 버전 번호 규칙

**Semantic Versioning** 방식: `MAJOR.MINOR.PATCH`

| 유형 | 버전 예시 | 변경 내용 | 하위 호환성 |
|------|----------|---------|----------|
| **PATCH** | 1.0.0 → 1.0.1 | 데이터 오류 수정, 타이포 수정 | 유지 |
| **MINOR** | 1.0.0 → 1.1.0 | 데이터 추가, 새 named query 추가 | 유지 |
| **MAJOR** | 1.0.0 → 2.0.0 | 스키마 변경, 테이블 삭제, manifest 구조 변경 | 깨짐 |

---

## 릴리스 절차

### Step 1: 데이터 수정

```bash
# 예: 새 데이터 추가 또는 오류 수정
python3 -c "
import sqlite3
conn = sqlite3.connect('trilobase.db')
cursor = conn.cursor()
# ... SQL 실행 ...
conn.commit()
conn.close()
"
```

### Step 2: 테스트 실행

```bash
# 모든 테스트 통과 확인
pytest tests/ -v

# 결과: 196 passed
```

### Step 3: 버전 번호 업데이트

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('trilobase.db')
cursor = conn.cursor()
cursor.execute(\"UPDATE artifact_metadata SET value = '1.1.0' WHERE key = 'version'\")
from datetime import date
cursor.execute(\"UPDATE artifact_metadata SET value = ? WHERE key = 'created_at'\", (str(date.today()),))
conn.commit()
conn.close()
print('Version updated to 1.1.0')
"
```

### Step 4: .scoda 패키지 생성

```bash
# Trilobase .scoda 패키지 (MCP 도구 정의 포함)
python scripts/create_scoda.py --mcp-tools data/mcp_tools_trilobase.json

# PaleoCore .scoda 패키지 (dependency)
python scripts/create_paleocore_scoda.py
```

### Step 5: 릴리스 패키징

```bash
# 1. Dry-run으로 사전 확인
python scripts/release.py --dry-run

# 2. 실제 릴리스 생성
python scripts/release.py
```

**생성되는 파일:**
```
releases/trilobase-v1.1.0/
├── trilobase.db         # Read-only 복사본 (0444 권한)
├── metadata.json        # 메타데이터 + 출처 + 통계
├── checksums.sha256     # SHA-256 해시
└── README.md            # 사용 안내
```

### Step 6: Git 커밋 및 태깅

```bash
git add trilobase.db
git commit -m "chore: Release v1.1.0 — [수정 내용 요약]"
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main v1.1.0
```

---

## 배포 절차

### Step 1: PyInstaller 빌드

```bash
python scripts/build.py
```

**생성 결과:**
```
dist/
├── ScodaDesktop.exe          # GUI 뷰어 (Windows)
├── ScodaDesktop_mcp.exe      # MCP stdio 서버 (Claude Desktop 전용)
├── trilobase.scoda            # 데이터 패키지
└── paleocore.scoda            # 의존성 패키지
```

**번들링되는 파일:**
- `scoda_engine/` (app.py, mcp_server.py, gui.py, serve.py, scoda_package.py)
- `scoda_engine/templates/`, `scoda_engine/static/`
- `spa/` (Reference Implementation SPA)
- Flask 및 의존성

### Step 2: 배포 파일 준비

```bash
# ZIP 압축
cd dist
zip -r ScodaDesktop-v1.1.0-windows.zip \
  ScodaDesktop.exe ScodaDesktop_mcp.exe \
  trilobase.scoda paleocore.scoda
```

### Step 3: GitHub Release 생성 (선택)

```bash
gh release create v1.1.0 \
  --title "SCODA Desktop v1.1.0" \
  --notes "Release notes here" \
  dist/ScodaDesktop-v1.1.0-windows.zip
```

---

## Overlay DB 호환성

Overlay DB는 사용자의 주석(annotations)을 저장하며, canonical DB 버전과 연동됩니다.

### 호환성 매트릭스

| Canonical 버전 변경 | Overlay DB 처리 | 사용자 주석 보존 |
|------------------|--------------|--------------|
| PATCH (1.0.0 → 1.0.1) | 버전만 업데이트 | 전체 보존 |
| MINOR (1.0.0 → 1.1.0) | 버전만 업데이트 | 전체 보존 |
| MAJOR (1.0.0 → 2.0.0) | 재생성 + 마이그레이션 | entity_name 기반 매칭 |

### entity_name의 역할

```sql
CREATE TABLE user_annotations (
    id INTEGER PRIMARY KEY,
    entity_type TEXT,        -- 'genus', 'family', etc.
    entity_id INTEGER,       -- canonical DB의 ID (버전별로 변경 가능)
    entity_name TEXT,        -- 'Paradoxides' 등 (불변, 릴리스 간 매칭용)
    annotation_type TEXT,
    content TEXT,
    created_at TEXT
);
```

- `entity_id`는 canonical DB 버전마다 달라질 수 있음
- `entity_name`은 불변이므로 Major 버전 업그레이드 시 매칭 가능

---

## 검증 및 테스트

### 릴리스 무결성 검증

```bash
cd releases/trilobase-v1.1.0
sha256sum --check checksums.sha256
cat metadata.json | jq '.version, .sha256'
```

### 실행 파일 테스트

```bash
# GUI 실행
./dist/ScodaDesktop.exe

# 확인 사항:
# - GUI 로그에 "Loaded: trilobase.scoda" 표시
# - "Start Server" 클릭 → 브라우저 자동 오픈
# - http://localhost:8080 접속 확인
# - Manifest 기반 뷰 정상 렌더링
```

### API 테스트

```bash
# Manifest 확인
curl http://localhost:8080/api/manifest | jq '.name'

# Named query 실행
curl 'http://localhost:8080/api/queries/genera_list/execute' | jq '.row_count'

# Composite detail
curl 'http://localhost:8080/api/composite/genus_detail?id=100' | jq '.name'
```

---

## 주의사항

### 불변성 원칙

- **같은 버전 번호로 릴리스 재생성 불가**
  ```
  python scripts/release.py
  # Error: Release directory already exists
  # SCODA immutability principle: cannot overwrite an existing release.
  ```
- 실수로 잘못된 릴리스 생성 시: 디렉토리 삭제 → 버전 증가 → 재릴리스

### 소스 DB 변경

- `scripts/release.py`는 소스 DB에 `sha256` 키를 자동 추가합니다
- 릴리스 후 소스 DB를 커밋하는 것을 잊지 마세요

### .scoda 패키지 구조

```
trilobase.scoda (ZIP)
├── manifest.json          # 패키지 메타데이터
├── data.db                # Canonical SQLite DB
└── mcp_tools.json         # MCP 도구 정의 (선택)
```

### PyInstaller 캐시

```bash
# 빌드 에러 발생 시 캐시 삭제
rm -rf build/ dist/ __pycache__
python scripts/build.py
```

---

## 빠른 참조 (Quick Reference)

```bash
# 1. 데이터 수정 + 테스트
pytest tests/

# 2. 버전 업데이트
python3 -c "
import sqlite3; conn = sqlite3.connect('trilobase.db')
conn.execute(\"UPDATE artifact_metadata SET value = '1.1.0' WHERE key = 'version'\")
conn.commit()
"

# 3. .scoda 패키지 생성
python scripts/create_scoda.py --mcp-tools data/mcp_tools_trilobase.json

# 4. 릴리스 생성
python scripts/release.py

# 5. Git 커밋 + 태그
git add trilobase.db
git commit -m "chore: Release v1.1.0"
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main v1.1.0

# 6. 실행 파일 빌드
python scripts/build.py
```

---

## 관련 문서

- [API_REFERENCE.md](./API_REFERENCE.md) — REST API 레퍼런스
- [MCP_GUIDE.md](./MCP_GUIDE.md) — MCP 서버 사용 가이드
- [HANDOFF.md](./HANDOFF.md) — 프로젝트 현황 및 인수인계
- [SCODA_CONCEPT.md](./SCODA_CONCEPT.md) — SCODA 개념 설명

---

**마지막 업데이트:** 2026-02-14
