# Timeline 빈 데이터 스텝 무한 루프 수정

**날짜:** 2026-03-14
**작업 번호:** 034

## 증상

Timeline play 시 데이터가 없는 시대 코드(예: 해당 시대에 genus가 0건인 스텝)에 도달하면:
- 같은 `timeline_value`로 API 요청이 초당 수십 회 무한 반복
- 트리가 변하지 않음
- 브라우저 성능 저하

graptobase 패키지에서 발견. Graptolite는 Cambrian~Devonian에만 분포하는데
timeline axis에 Permian~Recent까지 포함되어 빈 스텝이 다수 존재했음.

## 원인

`static/js/app.js` — `morphToStep()` 함수:

```javascript
// line 1252-1253 (수정 전)
inst.root = inst.fullRoot;
if (!inst.root) return;  // ← currentIdx 갱신 없이 return

// line 1267-1268 (수정 전)
const compareRoot = inst.fullRoot;
if (!compareRoot) return;  // ← currentIdx 갱신 없이 return
```

`currentIdx`는 정상 완료 시 animation callback 내부(line 1302)에서만 갱신됨.
빈 데이터로 early return하면 `currentIdx`가 그대로 유지되어
`playTimeline()`의 `while` 루프가 동일한 `nextIdx`를 무한 반복 계산.

```javascript
// playTimeline — 무한 루프 발생 구조
while (playing) {
    const nextIdx = currentIdx + dir;  // currentIdx가 안 변하므로 항상 같은 값
    await morphToStep(currentIdx, nextIdx, speed);  // 빈 데이터 → early return
    // currentIdx 여전히 동일 → 다음 iteration에서 같은 호출 반복
}
```

## 수정

### `morphToStep()` — base root가 null일 때

```javascript
if (!inst.root) {
    currentIdx = toIdx;
    updateScrubber();
    return;
}
```

빈 스텝을 건너뛰고 다음 스텝으로 진행.

### `morphToStep()` — compare root가 null일 때

```javascript
if (!compareRoot) {
    currentIdx = toIdx;
    updateScrubber();
    inst.root = inst._morphBaseRoot;
    inst.buildQuadtree(inst.root);
    inst._morphing = false;
    inst.transform = inst.computeFitTransform();
    d3.select(inst.canvas).call(inst.zoom.transform, inst.transform);
    inst.render();
    return;
}
```

`currentIdx`를 갱신하여 루프 진행 + 마지막 유효 트리(base)를 표시.

### `loadStep()` — root가 null일 때 캔버스 clear

```javascript
if (!inst.root) {
    inst._morphing = false;
    if (inst.ctx) { inst.ctx.clearRect(0, 0, inst.canvas.width, inst.canvas.height); }
    inst.render();
    return;
}
```

scrubber로 빈 스텝을 직접 선택했을 때 이전 트리가 잔류하지 않도록 캔버스 초기화.

## 수정 파일

- `scoda_engine/static/js/app.js` — `morphToStep()`, `loadStep()`

## 테스트

- 303 tests 전부 통과
- graptobase timeline play 정상 동작 확인
