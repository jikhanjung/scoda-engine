# 011 — Navbar 타이틀 구조 변경 (패키지명 메인 타이틀 승격)

**Date**: 2026-02-23
**Status**: WIP (uncommitted)
**Files changed**: `scoda_engine/templates/index.html`, `scoda_engine/static/js/app.js`

## Summary

Navbar 헤더의 타이틀 표시 구조를 변경하여, `.scoda` 패키지명이 메인 타이틀로 표시되고
"SCODA Desktop"이 서브타이틀로 내려가도록 개선.

## Changes

### `scoda_engine/templates/index.html`
- 기존 `navbar-pkg-name` (small 태그, 보조 텍스트) 제거
- `navbar-brand` 내부를 `#navbar-title` (메인 타이틀) + `#navbar-subtitle` (서브타이틀) 구조로 분리
- 초기 상태: 타이틀 = "SCODA Desktop", 서브타이틀 = 빈 값

### `scoda_engine/static/js/app.js`
- `loadManifest()` 에서 패키지 로드 시:
  - `#navbar-title` ← `패키지명 v버전` (메인 타이틀로 승격)
  - `#navbar-subtitle` ← `SCODA Desktop` (서브타이틀로 이동)
  - `document.title` ← `패키지명 v버전` (브라우저 탭 타이틀도 동기화)

## Motivation

패키지를 열었을 때 사용자가 현재 어떤 데이터를 보고 있는지 한눈에 파악할 수 있도록
패키지명을 가장 눈에 띄는 위치(navbar 메인 타이틀)에 표시. 브라우저 탭에서도 패키지명이
보이도록 `document.title`도 함께 업데이트.
