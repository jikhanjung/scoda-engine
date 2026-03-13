# 029 — Tree 노드 라벨 폰트 크기 단축키

## 작업 내용

`tree_chart.js` 툴바 초기화 블록에 `keydown` 이벤트 리스너 추가.

- `[` — 폰트 크기 축소 (textScale - 0.1)
- `]` — 폰트 크기 확대 (textScale + 0.1)

기존 버튼(`.tc-text-smaller` / `.tc-text-larger`)과 동일한 `applyTextScale()` 함수를 호출하므로
범위 제한(0.3 ~ 5.0), sync 콜백(`onTextScaleSync`) 모두 동일하게 동작함.

입력 필드(`INPUT`, `TEXTAREA`) 포커스 중에는 단축키가 발동하지 않도록 guard 추가.

## 변경 파일

- `scoda_engine/static/js/tree_chart.js` — keyHandler 7줄 추가 (line ~1220)
