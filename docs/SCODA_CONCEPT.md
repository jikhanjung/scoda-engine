# Trilobase as a SCODA
## Reframing Trilobase as a Self-Contained Data Artifact

---

## Purpose of This Document

This document describes **Trilobase** through the lens of **SCODA (Self-Contained Data Artifact)**.

It does **not** replace the technical README or database schema documentation.
Instead, it clarifies:

- What Trilobase *is* as a distributed knowledge object
- What responsibilities it takes (and deliberately avoids)
- How it should be used, extended, and cited

---

## What Trilobase Is (as a SCODA)

**Trilobase is a versioned, authoritative snapshot of trilobite genus-level taxonomy,
distributed as a self-contained data artifact.**

In SCODA terms:

- Trilobase is **not a service**
- Trilobase is **not a continuously synchronized database**
- Trilobase *is* a **reference artifact** representing the state of taxonomic knowledge at a given time

---

## Core Mapping: Trilobase → SCODA

| SCODA Component | Trilobase Implementation |
|----------------|--------------------------|
| Data | SQLite database containing taxonomic tables |
| Identity | Project name + semantic version |
| Semantics | Database schema, rank hierarchy, synonym relations |
| Provenance | Source literature (Jell & Adrain 2002; Adrain 2011) |
| Integrity | Immutable release artifacts; versioned updates |

---

## Immutability and Versioning

Each released version of Trilobase:

- Is treated as **read-only**
- Represents a *curated snapshot* of taxonomic interpretation
- Can be cited, archived, and reproduced

Any modification to the canonical data results in:

- A **new version**
- A **new SCODA artifact**
- An explicit update in provenance

This mirrors how taxonomic opinions evolve through publication,
not through silent mutation.

---

## Local Use and Extension

When a user opens Trilobase locally:

- The base artifact remains immutable
- Local changes are limited to:
  - Notes
  - Annotations
  - Alternative interpretations
  - Links to additional literature

These local extensions:

- Do **not** overwrite canonical taxonomy
- Are not automatically synchronized
- Exist as personal overlays

---

## Multiple Interpretations and "Sensu" Concepts

Taxonomic disagreement is an expected condition.

Trilobase supports this by allowing:

- Multiple taxonomic **concepts** to coexist
- Each concept to be explicitly labeled (e.g., *sensu Adrain, 2011*)
- Each assertion to be traceable to a source reference

The default distributed artifact may select one
**recommended concept set**, while preserving alternatives.

---

## Upgrades and Data Evolution

Updates to Trilobase occur through:

1. Curation and review
2. Generation of a new SCODA artifact
3. Explicit distribution of the new version

Users may choose when (or whether) to upgrade.

There is no implicit synchronization across installations.

---

## What Trilobase Explicitly Does Not Do

As a SCODA, Trilobase intentionally avoids:

- Real-time collaborative editing
- Automatic merge of conflicting interpretations
- Centralized live APIs as the primary interface
- Silent modification of historical data

These are features of *services*, not *artifacts*.

---

## Why This Matters

Treating Trilobase as a SCODA ensures:

- Scientific accountability
- Reproducibility of analyses
- Transparent evolution of taxonomic knowledge
- Clear separation between authoritative data and personal reasoning

In short:

> **Trilobase is not a database you connect to.  
> It is a knowledge object you open.**

---

## SCODA Engine: The Runtime Ecosystem

.scoda 패키지는 데이터 아티팩트이다. 이 아티팩트를 **열고, 탐색하고, 서빙하는** 소프트웨어가 **SCODA Engine**이다.

### 정의

> **SCODA Engine은 .scoda 패키지를 로드하여 Web UI, REST API, MCP 엔드포인트를 통해 데이터를 제공하는 런타임이다.**

Engine은 데이터를 생성하지 않는다. 패키지 안의 데이터를 **읽고, 쿼리하고, 시각화**하는 것이 역할이다.

### 제품 구조

| 제품 | 대상 | 설명 |
|------|------|------|
| **SCODA Desktop** | 개인 사용자 | 로컬 실행, tkinter GUI, 단일 패키지, overlay 지원 |
| **SCODA Server** | 기관/공개 서비스 | 멀티 유저, 인증, 스케일링 (미래) |

두 제품은 같은 Engine 코어를 공유한다:

- .scoda 패키지 로더 (`scoda_package.py`)
- Generic Viewer (manifest 기반 자동 렌더링)
- REST API (`/api/query/`, `/api/composite/`)
- MCP 서버 (stdio/SSE)

Desktop과 Server의 차이는 **배포 형태와 접근 제어**이며, 데이터 처리 로직은 동일하다.

### 관련 개념

| 이름 | 역할 |
|------|------|
| **.scoda** | 패키지 포맷 (SQLite DB + manifest + overlay) |
| **SCODA Engine** | .scoda를 서빙하는 런타임 (Desktop / Server) |
| **SCODA Hub** | 패키지 레지스트리/저장소 (미래 구상) |

### SCODA는 아티팩트이고 Engine은 도구이다

SCODA 개념의 핵심은 **데이터와 소프트웨어의 분리**이다:

- .scoda 패키지는 Engine 없이도 SQLite 파일로서 독립적으로 존재한다
- Engine은 패키지를 편리하게 탐색하는 **도구**일 뿐, 데이터의 일부가 아니다
- 같은 .scoda 패키지를 Desktop에서 열든 Server에서 서빙하든 데이터는 동일하다

---

## Status

This document defines the **conceptual role** of Trilobase within the SCODA framework.

The SCODA Engine ecosystem — including Desktop, Server, and Hub — is described
as part of the broader runtime architecture that serves SCODA artifacts.

Implementation details, runtime behavior, and contribution workflows
are defined in separate technical documents.
