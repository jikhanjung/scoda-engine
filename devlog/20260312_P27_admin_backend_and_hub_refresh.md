# P27: Admin Backend + Animation Export + Hub Refresh

**날짜**: 2026-03-12

## 배경

현재 SCODA Engine의 편집 기능(P21 CRUD framework)은 개인 사용자의 overlay DB 기반 편집에 한정. 관리자가 소스 데이터를 업로드하고 패키지에 반영하는 서버 측 백엔드가 필요. 또한 Animation 내보내기와 Hub 실시간 갱신 기능을 추가하여 운영 편의성을 높인다.

## 기능 목록

### 1. Admin Backend — Profile 관리 서버

관리자가 소스 txt 파일을 업로드하여 classification profile로 변환·등록하는 서버 측 기능.

- **신규 Profile 추가**: 업로드된 txt → 파싱 → 새 profile로 DB에 등록
- **Addendum (기존 profile에 덧붙이기)**: comprehensive하지 않은 treatment를 기존 profile의 addendum으로 병합
- 기존 P21 CRUD framework는 개인 사용자 overlay 편집 용도로 유지
- Admin backend는 canonical DB 직접 편집 권한을 가진 별도 모드

**미결 사항**:
- 개인 편집(overlay)과 관리자 편집(canonical)의 권한 경계
- txt 파싱 로직의 범용화 가능성 (도메인별 파서 플러그인?)
- Addendum 병합 전략: 덮어쓰기 vs 추가만 vs 충돌 해결

### 2. Animation → 동영상 다운로드

Tree Chart의 morph animation을 동영상 파일로 내보내기.

- Canvas 프레임을 캡처하여 WebM/MP4로 인코딩
- MediaRecorder API 또는 canvas.captureStream() 활용
- 다운로드 버튼 UI (toolbar 또는 animation controls 영역)
- 해상도·프레임레이트 옵션 (선택)

### 3. Hub Refresh 버튼

서버 재시작 없이 Hub에서 새 .scoda 패키지를 확인·다운로드·로드.

- **scoda-server (Docker)**: API 엔드포인트 또는 관리 UI 버튼
- **ScodaDesktop (GUI)**: Tkinter GUI에 Refresh 버튼 추가
- Hub index 재조회 → 새 버전 감지 → 다운로드 → PackageRegistry 갱신
- 현재 로드된 패키지의 hot-reload 또는 안내 후 재로드

## 우선순위

1. Hub Refresh 버튼 (영향 범위 작음, 운영 즉시 유용)
2. Animation 동영상 다운로드 (프론트엔드 단독 기능)
3. Admin Backend (설계 검토 필요, 도메인 의존성 높음)
