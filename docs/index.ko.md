# SCODA Engine

**Self-Contained Data Artifact를 위한 런타임**

---

SCODA Engine은 `.scoda` 데이터 패키지를 위한 범용 뷰어 및 서버입니다. 매니페스트 기반 웹 UI, REST API, MCP(Model Context Protocol) 서버를 제공하며, 도메인 전용 코드가 전혀 없습니다.

## SCODA란?

**SCODA(Self-Contained Open Data Artifact)**는 과학 데이터를 불변의 버전화된 아티팩트로 배포하기 위한 패키지 포맷입니다. `.scoda` 파일은 데이터, 스키마, 메타데이터, UI 정의를 하나의 자기완결적 ZIP 아카이브로 묶습니다.

> **SCODA 패키지는 연결하는 데이터베이스가 아니라, 여는 지식 객체입니다.**

## 주요 기능

- **도메인 코드 제로** — 모든 도메인 로직은 `.scoda` 패키지에서 제공
- **매니페스트 기반 UI** — 뷰, 테이블, 트리, 상세 모달이 패키지 매니페스트에서 자동 생성
- **Named Queries** — 패키지 내부에 저장된 SQL을 이름으로 실행
- **3-DB 아키텍처** — Canonical(불변) + Overlay(사용자 주석) + Dependency(공유 데이터)
- **MCP 서버** — Model Context Protocol을 통한 LLM 통합 (stdio/SSE)
- **SCODA Hub** — 패키지 검색 및 다운로드를 위한 정적 레지스트리
- **독립 실행 빌드** — PyInstaller EXE (Windows), 설치 불필요

## 빠른 시작

### 설치

```bash
git clone https://github.com/jikhanjung/scoda-engine.git
cd scoda-engine
pip install -e ./core
pip install -e ".[dev]"
```

### 서버 실행

```bash
# 웹 서버
python -m scoda_engine.serve

# 특정 .scoda 패키지 지정
python -m scoda_engine.serve --scoda-path /path/to/data.scoda

# GUI 컨트롤 패널
python launcher_gui.py
```

### 테스트 실행

```bash
pytest tests/
```

## 문서

### 개념

- [SCODA 개념](SCODA_CONCEPT.md) — SCODA의 정의와 Trilobase를 통한 예시
- [아키텍처 요약](SCODA_Concept_and_Architecture_Summary.md) — 상태 기반 지식 시스템으로서의 SCODA
- [백서](SCODA_WHITEPAPER.md) — 전체 사양: 패키지 포맷, 매니페스트, 뷰어, MCP
- [Stable UID 스키마](SCODA_Stable_UID_Schema_v0.2.md) — 패키지 간 엔티티 식별

### 가이드

- [API 레퍼런스](API_REFERENCE.md) — REST API 엔드포인트 및 사용법
- [MCP 가이드](MCP_GUIDE.md) — MCP 서버 설정 및 도구 레퍼런스
- [Hub Manifest 사양](HUB_MANIFEST_SPEC.md) — Hub 레지스트리 스키마 및 워크플로우
- [릴리스 가이드](RELEASE_GUIDE.md) — 빌드, 패키징, 릴리스 프로세스

## 아키텍처 개요

```
┌─────────────────────────────────────────────┐
│              SCODA Desktop                   │
│                                              │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │   GUI    │ │  FastAPI  │ │ MCP Server  │  │
│  │(tkinter) │ │  Server   │ │ (stdio/SSE) │  │
│  └────┬─────┘ └────┬─────┘ └──────┬──────┘  │
│       └──────┬──────┘──────────────┘         │
│              ↓                                │
│     ┌────────────────┐                        │
│     │ scoda_package   │  PackageRegistry      │
│     └───────┬────────┘                        │
│             ↓                                 │
│  ┌──────────────────────────────────┐         │
│  │    SQLite (3-DB ATTACH)          │         │
│  │  main: data.db (canonical, R/O) │         │
│  │  overlay: overlay.db (user, R/W)│         │
│  │  dep: dependency.db (infra, R/O)│         │
│  └──────────────────────────────────┘         │
└─────────────────────────────────────────────┘
```

## 라이선스

SCODA Engine은 오픈소스입니다. 자세한 내용은 [GitHub 저장소](https://github.com/jikhanjung/scoda-engine)를 참조하세요.
