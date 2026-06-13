# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VidGuard Demo — a static frontend showcase for a video content safety detection system, built for a Chinese information security competition (信安大赛). The UI is entirely in Chinese (zh-CN). There is no backend; all detection results are pre-generated demo data simulated with `setInterval` timers.

## Commands

```bash
npm run dev      # Start Vite dev server on port 5173 (all interfaces)
npm run build    # Production build to dist/
npm run preview  # Preview production build
```

No test framework, linter, or formatter is configured.

## Architecture

**Stack**: Vue 3 (Composition API, `<script setup>`) + vue-router + Vite. Plain JavaScript — no TypeScript.

**Routing** (`src/main.js`):
- `/` → `HomePage.vue` — landing/marketing page
- `/video-detection` → `VideoDetectionPage.vue` — interactive detection workbench
- `AigcCompliancePage.vue` exists in `src/pages/` but is **not registered in the router** (unreachable)

**State**: No Vuex/Pinia. All state lives as local `ref()`s in each page component.

**Data layer** (`src/data/demoCases.js`): Exports `detectionSteps`, `demoCases` (3 video scenarios), and `aigcExamples` (2 AIGC scenarios). Each case contains video path, subtitle, signals, entity-relation graph, explanation, and recommendation.

**Video matching**: `VideoDetectionPage.vue` has `pickCaseByFileName()` which pattern-matches the user's uploaded filename against keywords (e.g., "harmful", "metaphor") to select a pre-generated demo case. Detection progress is faked with `setInterval` (~900ms per step).

**Components**: Only one reusable component — `SceneGraph.vue` renders entity-relation graph rows.

**Styling**: Single `styles.css` file with CSS custom properties (warm paper-like theme: cream/brown/sage/amber). Serif typography. Responsive breakpoint at 900px. No CSS framework.

## Demo Assets

Videos and keyframes live in `public/demo-data/`. See `public/demo-data/README.txt` for the asset structure and `sample-result-template.json` for the expected detection result shape. Raw source videos are in `demo_video/`, extracted frames in `tmp_frames/`.

## Notes

- `dist/` is committed to the repo (pre-built output)
- `node_modules/` is committed (no `.gitignore`)
- `echarts` is declared as a dependency but unused in any source file
