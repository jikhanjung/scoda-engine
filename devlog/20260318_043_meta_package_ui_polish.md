# 043. Meta-Package UI 개선 및 버그 수정

**날짜:** 2026-03-18
**유형:** fix + feat
**관련:** #042 (meta-package 구현)

---

## 버그 수정

### manifest 응답에서 kind 필드 누락
- `response_model=ManifestResponse`가 meta-package 전용 필드(`kind`, `meta_tree`, `package_bindings`)를 필터링
- **수정:** meta-package일 때 `JSONResponse`로 직접 반환하여 모델 필터링 우회

### composite-tree API 404
- meta 엔드포인트(`/meta/tree`, `/meta/bindings`, `/meta/composite-tree`)가 catch-all 라우트 `/{entity_name}/{entity_id}` 뒤에 등록되어 매칭 안 됨
- **수정:** meta 엔드포인트를 catch-all 앞으로 이동

### 프론트엔드 DOM 요소 탐색 실패
- `getElementById('main-content')` → 실제로는 class (`container-fluid main-content`)
- `document.body`에 fallback → body.innerHTML 덮어쓰기로 전체 페이지 파괴
- **수정:** 기존 `.view-container`를 숨기고 새 meta 컨테이너를 sibling으로 추가

## 기능 개선

### Top-level 패키지 자동 진입
- `GET /` 접속 시 dependency를 분석하여 top-level 패키지 판별
- top-level이 1개면 자동 리다이렉트 (paleobase → `/paleobase/`)
- top-level이 여럿이면 landing에 top-level만 표시
- 다른 패키지의 dependency로 등장하는 패키지는 landing에서 숨김

### D3 Radial Tree (Darwin tree-of-life 스타일)
- 텍스트 목록 → D3.js radial tree 시각화 전환
- meta 노드: 밝은 배경 rect (`#f0f0f0`) + 2줄 표시 (rank 위, name 아래)
- 패키지 노드: 파란 원 (record count log 스케일 크기) + 클릭으로 패키지 이동
- 비활성 Phylum: 작은 회색 원
- taxon name uppercase first 표시 (`BRACHIOPODA` → `Brachiopoda`)
- 줌/팬 지원
- Brownian motion 애니메이션 (maxDrift=12px, damping=0.99, jitter=0.02)

### Landing page
- meta-package 카드에 META 배지 + member packages 표시
- top-level 패키지만 표시 (dependency인 패키지 숨김)

## 변경 파일

| 파일 | 변경 |
|------|------|
| `scoda_engine/app.py` | manifest JSONResponse, meta 라우트 순서 수정, top-level 자동 리다이렉트 |
| `scoda_engine/static/js/app.js` | D3 radial tree, brownian motion, upperFirst, 패키지 노드 크기 |
| `scoda_engine/templates/landing.html` | top-level 필터링, displayPackages |
