# 045. 뷰어 타이틀 통일 + OpenGraph 메타태그 + v0.3.7

**날짜:** 2026-07-10
**유형:** feat + chore

---

## 변경

### 뷰어 타이틀 통일

`scoda_engine/templates/index.html`의 `<title>`을 `SCODA Desktop` →
`SCODA Engine`으로 변경. Navbar/Landing의 "Powered by {engine_name}" 표기 및
저장소 명칭과 일치시킴.

### OpenGraph 메타태그 추가

뷰어를 링크로 공유할 때 소셜/메신저 미리보기가 정상 표시되도록 OG 태그 추가:

```html
<meta property="og:title" content="SCODA Engine">
<meta property="og:description" content="Generic viewer and server for .scoda data packages">
<meta property="og:type" content="website">
```

### 버전 업 (v0.3.5 → v0.3.7)

| 파일 | 변경 |
|------|------|
| `pyproject.toml` | `version = "0.3.7"` |
| `scoda_engine/__init__.py` | `__version__ = "0.3.7"` |
| `deploy/docker-compose.yml` | 이미지 태그 `scoda-server:0.3.7` |

0.3.7에 포함되는 코드 변경: #044 temp-dir 누수 수정 + 본 OG/타이틀 변경.

> **0.3.6 건너뜀:** 배포 시점에 `honestjung/scoda-server:0.3.6` 태그가 이미
> Docker Hub에 게시(2026-03-26 빌드)되어 프로덕션 컨테이너로 가동 중임을 확인.
> 해당 이미지는 본 변경(누수 수정·OG)을 포함하지 않는 3개월 전 빌드였다.
> 게시된 가변 태그를 덮어쓰지 않기 위해 릴리스 버전을 0.3.6 → **0.3.7**로 조정.
> (커밋 이력상 0.3.6 범프가 한 번 등장하나, 실제 릴리스는 0.3.7.)
