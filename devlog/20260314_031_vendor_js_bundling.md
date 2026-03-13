# 031 — JS/CSS 라이브러리 로컬 내장 (오프라인 지원)

**날짜**: 2026-03-14

## 배경

ScodaDesktop은 인터넷이 안 되는 환경에서도 사용할 수 있어야 한다.
기존에는 D3.js, Bootstrap 등을 CDN에서 로드하고 있어 오프라인 시 UI가 깨지거나 트리 차트가 로드되지 않았다.

## 변경 내용

### 내장된 라이브러리 (`static/vendor/`)

| 파일 | 버전 | 크기 | 용도 |
|------|------|------|------|
| `d3.v7.min.js` | 7.x | 274K | Tree chart 렌더링 |
| `bootstrap.min.css` | 5.3.0 | 228K | UI 프레임워크 |
| `bootstrap.bundle.min.js` | 5.3.0 | 79K | Modal, dropdown 등 |
| `bootstrap-icons/bootstrap-icons.css` | 1.10.0 | 94K | 아이콘 |
| `bootstrap-icons/fonts/bootstrap-icons.woff2` | 1.10.0 | 119K | 아이콘 폰트 |
| `bootstrap-icons/fonts/bootstrap-icons.woff` | 1.10.0 | 161K | 아이콘 폰트 (fallback) |

### 제거

- `webm-writer@1.0.0` CDN 참조 제거 — 원래 CDN URL(`/dist/webm-writer.js`)이 존재하지 않는 경로였음. 코드에서 `typeof WebMWriter === 'undefined'` 체크 후 `MediaRecorder` fallback으로 동작하고 있었으므로 실질적 영향 없음.

### 수정 파일

| 파일 | 변경 |
|------|------|
| `scoda_engine/templates/index.html` | CDN 4개 → `/static/vendor/` 로컬 경로 |
| `scoda_engine/static/js/tree_chart.js` | D3.js lazy load URL → `/static/vendor/d3.v7.min.js` |

### PyInstaller

`ScodaDesktop.spec`의 `datas`에 `('scoda_engine', 'scoda_engine')`이 디렉토리 전체를 포함하므로 `static/vendor/`도 자동 포함. 별도 수정 불필요.

## 테스트

- 303 tests 통과
