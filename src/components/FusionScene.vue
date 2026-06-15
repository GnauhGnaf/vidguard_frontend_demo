<template>
  <div class="fs-root" ref="rootRef">
    <!-- Visual row: masked video + current frame graph + cumulative scene graph -->
    <div class="fs-visual-row">
      <div class="fs-video-col">
        <video ref="maskedVideoRef" src="/harmful_masked.mp4" muted loop playsinline
               class="fs-masked-video"></video>
        <span class="fs-frame-badge" ref="frameBadge">frame 1 / 141</span>
      </div>
      <div class="fs-graphs-col">
        <div class="fs-graph-panel">
          <span class="fs-panel-label">当前帧场景图</span>
          <div class="fs-graph-stage" ref="currentStageRef">
            <canvas class="fs-graph-canvas" ref="currentCanvasRef"></canvas>
          </div>
        </div>
        <div class="fs-graph-panel">
          <span class="fs-panel-label">累计场景图</span>
          <div class="fs-graph-stage" ref="cumulativeStageRef">
            <canvas class="fs-graph-canvas" ref="cumulativeCanvasRef"></canvas>
          </div>
        </div>
      </div>
    </div>

    <div class="fs-stage-indicator" ref="stageIndicator">
      <div v-for="i in 6" :key="i" class="fs-stage-dot" :data-stage="i-1"></div>
    </div>
    <div class="fs-stage-label" ref="stageLabel">完整句子</div>

    <div class="fs-main-container" ref="containerRef">
      <canvas ref="canvasRef"></canvas>
    </div>

    <div class="fs-legend" ref="legendRef">
      <span class="fs-legend-item"><span class="fs-legend-dot noun"></span> 名词</span>
      <span class="fs-legend-item"><span class="fs-legend-dot verb"></span> 动词</span>
      <span class="fs-legend-item"><span class="fs-legend-dot adj"></span> 形容词</span>
      <span class="fs-legend-item"><span class="fs-legend-dot danger"></span> 危险实体</span>
    </div>

    <div class="fs-controls">
      <button class="fs-ctrl-btn" :disabled="currentStage <= 0" @click="prevStage">← 上一步</button>
      <button class="fs-ctrl-btn play" :class="{ playing: isAutoPlaying }" @click="toggleAutoPlay">
        {{ isAutoPlaying ? '⏸ 暂停' : '▶ 自动播放' }}
      </button>
      <button class="fs-ctrl-btn" :disabled="currentStage >= totalStages" @click="nextStage">下一步 →</button>
      <button class="fs-ctrl-btn" @click="resetAll">↺ 重置</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

// ── props ────────────────────────────────────────────────────────
const props = defineProps({
  sentence: { type: String, default: 'The man robs the woman using the real gun.' },
  autoPlay: { type: Boolean, default: false }
})

const emit = defineEmits(['stageChange'])

// ── template refs ────────────────────────────────────────────────
const rootRef = ref(null)
const containerRef = ref(null)
const canvasRef = ref(null)
const stageLabel = ref(null)
const legendRef = ref(null)
const stageIndicator = ref(null)
const maskedVideoRef = ref(null)
const frameBadge = ref(null)
const currentStageRef = ref(null)
const currentCanvasRef = ref(null)
const cumulativeStageRef = ref(null)
const cumulativeCanvasRef = ref(null)

// ── state ────────────────────────────────────────────────────────
const currentStage = ref(0)
const totalStages = 5
const isAutoPlaying = ref(false)
let autoPlayTimer = null
let redrawTimer = null
let stage5Phase = 0
let stage5PhaseTimer = null

// ── visual section: frame annotations & cumulative graph ──────────
const TOTAL_FRAMES = 141
const FPS = 24

const frameAnnotations = {}
for (let f = 1; f <= 37; f++) frameAnnotations[f] = ['person1','gun']
for (let f = 38; f <= 51; f++) frameAnnotations[f] = ['gun']
for (let f = 91; f <= 141; f++) frameAnnotations[f] = ['person2']

function getAnnotations(frame) { return frameAnnotations[frame] || [] }

let cumulativePhase = 0
let cumNodes = {}
let cumArrows = []
let cumTransitioning = false

function getCurrentGraph(frame) {
  const ann = getAnnotations(frame)
  const nodes = {}
  const arrows = []
  if (ann.includes('person1') && ann.includes('gun')) {
    nodes['person1'] = { label: 'person1', type: 'entity' }
    nodes['hold']   = { label: 'hold',    type: 'action' }
    nodes['gun']    = { label: 'gun',     type: 'danger' }
    arrows.push({ from: 'person1', to: 'hold' }, { from: 'hold', to: 'gun' })
  } else if (ann.includes('gun') && !ann.includes('person1') && !ann.includes('person2')) {
    nodes['gun'] = { label: 'gun', type: 'danger' }
  } else if (ann.includes('person2')) {
    nodes['person2'] = { label: 'person2', type: 'entity' }
  }
  return { nodes, arrows }
}

function renderCurrentGraph(nodes, arrows) {
  const container = currentStageRef.value
  const canvas = currentCanvasRef.value
  if (!container || !canvas) return
  const curCtx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const rect = container.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  canvas.style.width = rect.width + 'px'
  canvas.style.height = rect.height + 'px'
  curCtx.setTransform(dpr, 0, 0, dpr, 0, 0)

  // Clear old nodes
  container.querySelectorAll('.fs-gnode').forEach(el => el.remove())

  const ids = Object.keys(nodes)
  if (ids.length === 0) { curCtx.clearRect(0, 0, rect.width, rect.height); return }

  // Measure
  const measured = {}
  ids.forEach(id => {
    const def = nodes[id]
    const el = document.createElement('span')
    el.className = 'fs-gnode ' + def.type
    el.textContent = def.label
    el.style.left = '-9999px'
    container.appendChild(el)
    measured[id] = { width: el.offsetWidth, height: el.offsetHeight }
    el.remove()
  })

  const totalW = ids.reduce((s, id) => s + measured[id].width, 0)
  let gap, startX
  if (ids.length <= 1) {
    gap = 0; startX = Math.round((rect.width - totalW) / 2)
  } else {
    gap = Math.round((rect.width - totalW) / (ids.length - 1))
    if (gap < 18) gap = 18
    startX = Math.round((rect.width - (totalW + gap * (ids.length - 1))) / 2)
    if (startX < 4) startX = 4
    const endX = startX + totalW + gap * (ids.length - 1)
    if (endX > rect.width - 4) {
      gap = Math.max(4, Math.floor((rect.width - 8 - totalW) / (ids.length - 1)))
      startX = 4
    }
  }

  const positions = {}
  let cx = startX
  ids.forEach(id => {
    const w = measured[id].width
    positions[id] = { left: cx, top: 10, width: w, height: measured[id].height }
    cx += w + gap
  })

  // Create DOM nodes
  ids.forEach(id => {
    const def = nodes[id]
    const pos = positions[id]
    const el = document.createElement('span')
    el.className = 'fs-gnode ' + def.type
    el.textContent = def.label
    el.style.left = pos.left + 'px'
    el.style.top = pos.top + 'px'
    container.appendChild(el)
  })

  // Draw arrows
  curCtx.clearRect(0, 0, rect.width, rect.height)
  arrows.forEach(arrow => {
    const a = positions[arrow.from], b = positions[arrow.to]
    if (!a || !b) return
    const ax = a.left + a.width/2, ay = a.top + a.height/2
    const bx = b.left + b.width/2, by = b.top + b.height/2
    const dx = bx - ax, dy = by - ay, len = Math.sqrt(dx*dx+dy*dy)
    if (len < 1) return
    const ux = dx/len, uy = dy/len
    const sx = ax + ux*(a.width/2+4), sy = ay + uy*(a.height/2+4)
    const ex = bx - ux*(b.width/2+4), ey = by - uy*(b.height/2+4)

    curCtx.strokeStyle = '#8b949e'; curCtx.lineWidth = 1.5
    curCtx.beginPath(); curCtx.moveTo(sx, sy); curCtx.lineTo(ex, ey); curCtx.stroke()

    const headLen = 8, angle = Math.atan2(ey-sy, ex-sx)
    curCtx.fillStyle = '#8b949e'
    curCtx.beginPath(); curCtx.moveTo(ex, ey)
    curCtx.lineTo(ex-headLen*Math.cos(angle-0.45), ey-headLen*Math.sin(angle-0.45))
    curCtx.lineTo(ex-headLen*Math.cos(angle+0.45), ey-headLen*Math.sin(angle+0.45))
    curCtx.closePath(); curCtx.fill()
  })
}

function measureCumNode(label, type) {
  const el = document.createElement('span')
  el.className = 'fs-gnode ' + type
  el.textContent = label
  el.style.left = '-9999px'; el.style.top = '-9999px'
  cumulativeStageRef.value.appendChild(el)
  const w = el.offsetWidth, h = el.offsetHeight
  el.remove()
  return { w, h }
}

function layoutCumulative(ids, labels, types) {
  const container = cumulativeStageRef.value
  const rect = container.getBoundingClientRect()
  const measured = ids.map((id, i) => ({ id, ...measureCumNode(labels[i], types[i]) }))
  const totalW = measured.reduce((s, m) => s + m.w, 0)
  const n = ids.length
  let gap = n > 1 ? Math.round((rect.width - totalW) / (n - 1)) : 0
  if (gap < 18) gap = 18
  let startX = Math.max(4, Math.round((rect.width - (totalW + gap * (n - 1))) / 2))
  const endX = startX + totalW + gap * (n - 1)
  if (endX > rect.width - 4 && n > 1) {
    gap = Math.max(4, Math.floor((rect.width - 8 - totalW) / (n - 1)))
    startX = 4
  }
  const result = {}
  let cx = startX
  measured.forEach(m => {
    result[m.id] = { label: labels[ids.indexOf(m.id)], type: types[ids.indexOf(m.id)], left: cx, top: 14, width: m.w, height: m.h }
    cx += m.w + gap
  })
  return result
}

function getCumDOMNodeRect(label) {
  const container = cumulativeStageRef.value
  const cr = container.getBoundingClientRect()
  const els = container.querySelectorAll('.fs-gnode')
  for (const el of els) {
    if (el.textContent === label) {
      const r = el.getBoundingClientRect()
      return { left: r.left - cr.left, top: r.top - cr.top, width: r.width, height: r.height }
    }
  }
  return null
}

function drawCumulativeArrows() {
  const canvas = cumulativeCanvasRef.value
  const container = cumulativeStageRef.value
  const cumCtx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const rect = container.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  canvas.style.width = rect.width + 'px'
  canvas.style.height = rect.height + 'px'
  cumCtx.setTransform(dpr, 0, 0, dpr, 0, 0)
  cumCtx.clearRect(0, 0, rect.width, rect.height)

  const labels = ['person1','hold','gun','point','person2']
  const pos = {}
  labels.forEach(l => { const r = getCumDOMNodeRect(l); if (r) pos[l] = r })

  cumArrows.forEach(arrow => {
    const a = pos[arrow.from], b = pos[arrow.to]
    if (!a || !b) return
    const ax = a.left + a.width/2, ay = a.top + a.height/2
    const bx = b.left + b.width/2, by = b.top + b.height/2
    const dx = bx - ax, dy = by - ay, len = Math.sqrt(dx*dx+dy*dy)
    if (len < 1) return
    const ux = dx/len, uy = dy/len
    const sx = ax + ux*(a.width/2+4), sy = ay + uy*(a.height/2+4)
    const ex = bx - ux*(b.width/2+4), ey = by - uy*(b.height/2+4)

    cumCtx.strokeStyle = '#8b949e'; cumCtx.lineWidth = 1.5
    if (arrow.dashed) cumCtx.setLineDash([3, 4]); else cumCtx.setLineDash([])
    cumCtx.beginPath(); cumCtx.moveTo(sx, sy); cumCtx.lineTo(ex, ey); cumCtx.stroke()
    cumCtx.setLineDash([])

    const headLen = 8, angle = Math.atan2(ey-sy, ex-sx)
    cumCtx.fillStyle = '#8b949e'
    cumCtx.beginPath(); cumCtx.moveTo(ex, ey)
    cumCtx.lineTo(ex-headLen*Math.cos(angle-0.45), ey-headLen*Math.sin(angle-0.45))
    cumCtx.lineTo(ex-headLen*Math.cos(angle+0.45), ey-headLen*Math.sin(angle+0.45))
    cumCtx.closePath(); cumCtx.fill()
  })
}

function buildCumulativeDOM() {
  const container = cumulativeStageRef.value
  container.querySelectorAll('.fs-gnode').forEach(el => el.remove())
  Object.entries(cumNodes).forEach(([id, n]) => {
    const el = document.createElement('span')
    el.className = 'fs-gnode ' + n.type
    el.textContent = n.label
    el.style.left = n.left + 'px'
    el.style.top = n.top + 'px'
    if (n.isNew) el.classList.add('new')
    container.appendChild(el)
  })
  drawCumulativeArrows()
}

function initCumulativeBasic() {
  cumNodes = layoutCumulative(
    ['person1','hold','gun'],
    ['person1','hold','gun'],
    ['entity','action','danger']
  )
  cumArrows = [
    { from: 'person1', to: 'hold' },
    { from: 'hold', to: 'gun' },
  ]
  buildCumulativeDOM()
}

function expandCumulative() {
  if (cumTransitioning || cumulativePhase >= 1) return
  cumTransitioning = true
  cumulativePhase = 1

  const container = cumulativeStageRef.value
  const rect = container.getBoundingClientRect()
  const allIds = ['person1','hold','gun','point','person2']
  const allLabels = ['person1','hold','gun','point','person2']
  const allTypes = ['entity','action','danger','action','entity']

  const measured = allIds.map((id, i) => ({ id, ...measureCumNode(allLabels[i], allTypes[i]) }))
  const totalW = measured.reduce((s, m) => s + m.w, 0)
  let gap = Math.round((rect.width - totalW) / 4)
  if (gap < 18) gap = 18
  let startX = Math.max(4, Math.round((rect.width - (totalW + gap * 4)) / 2))
  const endX = startX + totalW + gap * 4
  if (endX > rect.width - 4) {
    gap = Math.max(4, Math.floor((rect.width - 8 - totalW) / 4))
    startX = 4
  }

  const target = {}
  let cx = startX
  measured.forEach(m => {
    target[m.id] = { left: cx, top: 14, width: m.w, height: m.h, label: allLabels[allIds.indexOf(m.id)], type: allTypes[allIds.indexOf(m.id)] }
    cx += m.w + gap
  })

  const newEls = {}
  ;['point','person2'].forEach(id => {
    const t = target[id]
    const el = document.createElement('span')
    el.className = 'fs-gnode ' + t.type
    el.textContent = t.label
    el.style.left = t.left + 'px'
    el.style.top = t.top + 'px'
    el.style.opacity = '0'
    container.appendChild(el)
    newEls[id] = el
  })

  container.querySelectorAll('.fs-gnode').forEach(el => {
    if (newEls[el.textContent]) return
    const id = allIds.find(i => allLabels[allIds.indexOf(i)] === el.textContent)
    if (id && target[id]) {
      el.style.transition = 'left 0.5s ease'
      el.style.left = target[id].left + 'px'
    }
  })

  cumNodes = target
  cumArrows = [
    { from: 'person1', to: 'hold' },
    { from: 'hold', to: 'gun' },
    { from: 'gun', to: 'point', dashed: true },
    { from: 'point', to: 'person2', dashed: true },
  ]

  const duration = 500
  const startTime = performance.now()
  function tick(now) {
    const t = Math.min(1, (now - startTime) / duration)
    Object.values(newEls).forEach(el => { el.style.opacity = Math.min(1, t * 2) })
    drawCumulativeArrows()
    if (t < 1) { requestAnimationFrame(tick) }
    else {
      Object.values(newEls).forEach(el => { el.style.opacity = '1' })
      drawCumulativeArrows()
      cumTransitioning = false
    }
  }
  requestAnimationFrame(tick)
}

function updateForFrame(frame) {
  if (frameBadge.value) frameBadge.value.textContent = `frame ${frame} / ${TOTAL_FRAMES}`
  const cur = getCurrentGraph(frame)
  renderCurrentGraph(cur.nodes, cur.arrows)
  if (frame >= 91 && cumulativePhase < 1) expandCumulative()
}

function resetCumulative() {
  cumulativePhase = 0
  cumTransitioning = false
  cumNodes = {}
  cumArrows = []
  initCumulativeBasic()
}

// ── word definitions ─────────────────────────────────────────────
const tokens = [
  { id: 'the1',   text: 'The',    type: 'filler' },
  { id: 'man',    text: 'man',    type: 'noun'   },
  { id: 'robs',   text: 'robs',   type: 'verb'   },
  { id: 'the2',   text: 'the',    type: 'filler' },
  { id: 'woman',  text: 'woman',  type: 'noun'   },
  { id: 'using',  text: 'using',  type: 'verb'   },
  { id: 'the3',   text: 'the',    type: 'filler' },
  { id: 'real',   text: 'real',   type: 'adj'    },
  { id: 'gun',    text: 'gun',    type: 'noun'   },
]

const sentenceOrder = ['the1','man','robs','the2','woman','using','the3','real','gun']
const chainTopOrder  = ['gun','using','man','robs','woman']

const arrowDefs = {
  3: [
    { from: 'using', to: 'gun'  },
    { from: 'man',   to: 'using'},
    { from: 'man',   to: 'robs'},
    { from: 'robs',  to: 'woman'},
    { from: 'real',  to: 'gun'  },
  ],
}

const vnodeDefs = [
  { id: 'v-person1', label: 'person1', type: 'entity' },
  { id: 'v-hold',    label: 'hold',    type: 'action' },
  { id: 'v-gun',     label: 'gun',     type: 'danger' },
  { id: 'v-point',   label: 'point',   type: 'action' },
  { id: 'v-person2', label: 'person2', type: 'entity' },
]

const visPairs = [
  { from: 'v-person1', to: 'v-hold' },
  { from: 'v-hold',    to: 'v-gun' },
  { from: 'v-gun',     to: 'v-point',   dashed: true },
  { from: 'v-point',   to: 'v-person2', dashed: true },
]
const textPairs = [
  { from: 'using', to: 'gun' },
  { from: 'man',   to: 'using' },
  { from: 'man',   to: 'robs' },
  { from: 'robs',  to: 'woman' },
  { from: 'real',  to: 'gun' },
]
const crossPairs = [
  { v: 'v-gun',     t: 'gun' },
  { v: 'v-person1', t: 'man' },
  { v: 'v-person2', t: 'woman' },
]

const mergeMap = { 'man':'v-person1', 'using':'v-hold', 'gun':'v-gun', 'woman':'v-person2' }
const mainOrder = ['v-person1','v-hold','v-gun','v-point','v-person2']

// ── elements (created imperatively) ──────────────────────────────
let wordEls = {}
let vnodeEls = {}
let ctx = null
let CTN_W = 960

// ── helpers ──────────────────────────────────────────────────────
function wWidth(id) { return wordEls[id]?.offsetWidth || 0 }

function layoutRow(ids, targetGap, y) {
  const widths = ids.map(id => wWidth(id))
  const totalW = widths.reduce((a, b) => a + b, 0) + targetGap * (ids.length - 1)
  const positions = {}
  let x = Math.round((CTN_W - totalW) / 2)
  ids.forEach((id, i) => {
    positions[id] = { left: x, top: y }
    x += widths[i] + targetGap
  })
  return positions
}

function getWordRect(id) {
  const el = wordEls[id]
  if (!el) return null
  const left = parseFloat(el.style.left) || 0
  const top  = parseFloat(el.style.top)  || 0
  const w = el.offsetWidth
  const h = el.offsetHeight
  return { left, top, right: left + w, bottom: top + h, cx: left + w / 2, cy: top + h / 2 }
}

function getVNodeRect(id) {
  const el = vnodeEls[id]
  if (!el) return null
  const left = parseFloat(el.style.left) || 0
  const top  = parseFloat(el.style.top)  || 0
  const w = el.offsetWidth
  const h = el.offsetHeight
  return { left, top, right: left + w, bottom: top + h, cx: left + w/2, cy: top + h/2 }
}

// live rect via getBoundingClientRect — used during CSS transitions
function getWordRectLive(id) {
  const el = wordEls[id]
  if (!el) return null
  const cr = containerRef.value.getBoundingClientRect()
  const r = el.getBoundingClientRect()
  const left = r.left - cr.left, top = r.top - cr.top
  return { left, top, right: left + r.width, bottom: top + r.height, cx: left + r.width / 2, cy: top + r.height / 2 }
}

function getVNodeRectLive(id) {
  const el = vnodeEls[id]
  if (!el) return null
  const cr = containerRef.value.getBoundingClientRect()
  const r = el.getBoundingClientRect()
  const left = r.left - cr.left, top = r.top - cr.top
  return { left, top, right: left + r.width, bottom: top + r.height, cx: left + r.width/2, cy: top + r.height/2 }
}

function getAnyRect(id) {
  if (id.startsWith('v-')) return getVNodeRect(id)
  return getWordRect(id)
}

function rayRectExit(px, py, dx, dy, rect, padding) {
  let tMin = Infinity
  const pad = padding || 0
  const r = { left: rect.left - pad, top: rect.top - pad, right: rect.right + pad, bottom: rect.bottom + pad }
  if (Math.abs(dx) > 1e-9) {
    for (const edgeX of [r.left, r.right]) {
      const t = (edgeX - px) / dx
      if (t > 1e-9) { const y = py + t * dy; if (y >= r.top && y <= r.bottom) tMin = Math.min(tMin, t) }
    }
  }
  if (Math.abs(dy) > 1e-9) {
    for (const edgeY of [r.top, r.bottom]) {
      const t = (edgeY - py) / dy
      if (t > 1e-9) { const x = px + t * dx; if (x >= r.left && x <= r.right) tMin = Math.min(tMin, t) }
    }
  }
  if (tMin === Infinity) return { x: px, y: py }
  return { x: px + tMin * dx, y: py + tMin * dy }
}

// ── canvas & arrow drawing ───────────────────────────────────────
function resizeCanvas() {
  const container = containerRef.value
  const canvas = canvasRef.value
  if (!container || !canvas) return
  CTN_W = container.getBoundingClientRect().width
  const rect = container.getBoundingClientRect()
  canvas.width = rect.width * devicePixelRatio
  canvas.height = rect.height * devicePixelRatio
  canvas.style.width = rect.width + 'px'
  canvas.style.height = rect.height + 'px'
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.scale(devicePixelRatio, devicePixelRatio)
}

function drawOneArrow(fromRect, toRect, dashed) {
  const dx = toRect.cx - fromRect.cx, dy = toRect.cy - fromRect.cy
  const len = Math.sqrt(dx*dx+dy*dy)
  if (len < 1) return
  const ux = dx/len, uy = dy/len
  const start = rayRectExit(fromRect.cx, fromRect.cy, ux, uy, fromRect, -2)
  const end   = rayRectExit(toRect.cx, toRect.cy, -ux, -uy, toRect, -2)
  const headLen = 12

  ctx.strokeStyle = '#8b949e'; ctx.lineWidth = 2
  if (dashed) ctx.setLineDash([3, 5]); else ctx.setLineDash([])
  ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke()
  ctx.setLineDash([])

  ctx.fillStyle = '#8b949e'
  ctx.beginPath(); ctx.moveTo(end.x, end.y)
  ctx.lineTo(end.x - headLen*Math.cos(Math.atan2(end.y-start.y, end.x-start.x) - 0.45), end.y - headLen*Math.sin(Math.atan2(end.y-start.y, end.x-start.x) - 0.45))
  ctx.lineTo(end.x - headLen*Math.cos(Math.atan2(end.y-start.y, end.x-start.x) + 0.45), end.y - headLen*Math.sin(Math.atan2(end.y-start.y, end.x-start.x) + 0.45))
  ctx.closePath(); ctx.fill()
}

function drawBidirectionalArrow(topRect, bottomRect, color) {
  const x1 = topRect.cx, y1 = topRect.bottom + 6
  const x2 = bottomRect.cx, y2 = bottomRect.top - 6
  const dx = x2 - x1, dy = y2 - y1, len = Math.sqrt(dx*dx+dy*dy)
  if (len < 1) return
  const ux = dx/len, uy = dy/len
  const headLen = 10

  ctx.strokeStyle = color; ctx.lineWidth = 1.5
  ctx.setLineDash([4, 4])
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
  ctx.setLineDash([])

  ctx.fillStyle = color
  ctx.beginPath(); ctx.moveTo(x2, y2)
  ctx.lineTo(x2 - headLen*Math.cos(Math.atan2(dy,dx) - 0.45), y2 - headLen*Math.sin(Math.atan2(dy,dx) - 0.45))
  ctx.lineTo(x2 - headLen*Math.cos(Math.atan2(dy,dx) + 0.45), y2 - headLen*Math.sin(Math.atan2(dy,dx) + 0.45))
  ctx.closePath(); ctx.fill()

  ctx.beginPath(); ctx.moveTo(x1, y1)
  ctx.lineTo(x1 + headLen*Math.cos(Math.atan2(dy,dx) - 0.45), y1 + headLen*Math.sin(Math.atan2(dy,dx) - 0.45))
  ctx.lineTo(x1 + headLen*Math.cos(Math.atan2(dy,dx) + 0.45), y1 + headLen*Math.sin(Math.atan2(dy,dx) + 0.45))
  ctx.closePath(); ctx.fill()
}

function drawTextArrows(stage) {
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  const defs = arrowDefs[stage]
  if (!defs) return
  defs.forEach(a => {
    const ra = getWordRect(a.from), rb = getWordRect(a.to)
    if (ra && rb) drawOneArrow(ra, rb, false)
  })
}

function drawTextArrowsLive(stage) {
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  const defs = arrowDefs[stage]
  if (!defs) return
  defs.forEach(a => {
    const ra = getWordRectLive(a.from), rb = getWordRectLive(a.to)
    if (ra && rb) drawOneArrow(ra, rb, false)
  })
}

function drawVisualAndTextArrows() {
  resizeCanvas()
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  visPairs.forEach(p => {
    const a = getVNodeRect(p.from), b = getVNodeRect(p.to)
    if (a && b) drawOneArrow(a, b, p.dashed)
  })
  textPairs.forEach(p => {
    const a = getWordRect(p.from), b = getWordRect(p.to)
    if (a && b) drawOneArrow(a, b, false)
  })
}

function drawLayerArrows() {
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  visPairs.forEach(p => {
    const a = getVNodeRect(p.from), b = getVNodeRect(p.to)
    if (a && b) drawOneArrow(a, b, p.dashed)
  })
  textPairs.forEach(p => {
    const a = getWordRect(p.from), b = getWordRect(p.to)
    if (a && b) drawOneArrow(a, b, false)
  })
}

function drawFusionArrows() {
  drawLayerArrows()
  crossPairs.forEach(pair => {
    const vr = getVNodeRect(pair.v), tr = getWordRect(pair.t)
    if (!vr || !tr) return
    drawBidirectionalArrow(vr, tr, '#58a6ff')
  })
}

function drawMergedArrows() {
  resizeCanvas()
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  ;[
    { from: 'v-person1', to: 'v-hold' },
    { from: 'v-hold',    to: 'v-gun' },
    { from: 'v-gun',     to: 'v-point',   dashed: true },
    { from: 'v-point',   to: 'v-person2', dashed: true },
  ].forEach(p => {
    const a = getVNodeRect(p.from), b = getVNodeRect(p.to)
    if (a && b) drawOneArrow(a, b, p.dashed)
  })
  ;[
    { from: 'v-person1', to: 'robs' },
    { from: 'robs',      to: 'v-person2' },
    { from: 'real',      to: 'v-gun' },
  ].forEach(p => {
    const a = getAnyRect(p.from), b = getAnyRect(p.to)
    if (a && b) drawOneArrow(a, b, false)
  })
}

// ── smooth arrow animation ─────────────────────────────────────
function animateArrows(drawFn, duration) {
  if (redrawTimer) { cancelAnimationFrame(redrawTimer); redrawTimer = null }
  const start = performance.now()
  function tick(now) {
    if (now - start >= duration) { drawFn(); redrawTimer = null; return }
    drawFn()
    redrawTimer = requestAnimationFrame(tick)
  }
  redrawTimer = requestAnimationFrame(tick)
}

// ── UI updates ───────────────────────────────────────────────────
function updateDots(stage) {
  const dots = stageIndicator.value?.querySelectorAll('.fs-stage-dot')
  if (!dots) return
  dots.forEach((dot, i) => {
    dot.classList.remove('active', 'done')
    if (i < stage) dot.classList.add('done')
    if (i === stage) dot.classList.add('active')
  })
}

function updateLabel(text) {
  if (stageLabel.value) stageLabel.value.textContent = text
}

function updateLegend(visible) {
  if (legendRef.value) legendRef.value.classList.toggle('visible', visible)
}

// ── reset stage5 state ───────────────────────────────────────────
function resetStage5Phase() {
  stage5Phase = 0
  if (stage5PhaseTimer) { clearTimeout(stage5PhaseTimer); stage5PhaseTimer = null }
}

// ── stage 4: two-phase cross-source fusion ───────────────────────
function applyStage4TwoPhase() {
  if (stage5PhaseTimer) clearTimeout(stage5PhaseTimer)

  // measure visual nodes
  const vMeasured = {}
  vnodeDefs.forEach(def => {
    const el = vnodeEls[def.id]
    el.classList.remove('hidden')
    el.style.opacity = '1'
    vMeasured[def.id] = el.offsetWidth
  })

  // reset visual node text & style
  vnodeDefs.forEach(def => {
    const el = vnodeEls[def.id]
    el.textContent = def.label
    el.classList.remove('merged')
    el.style.whiteSpace = 'nowrap'
    el.style.fontSize = ''
    el.style.padding = ''
    el.style.lineHeight = ''
    el.style.opacity = '1'
    el.classList.remove('hidden')
  })

  // text: stage 3 chain layout → move to y=110
  const textPosP1 = layoutRow(chainTopOrder, 60, 110)
  const gunCenterP1 = textPosP1['gun'].left + wWidth('gun') / 2
  const realWP1 = wWidth('real')
  textPosP1['real'] = { left: Math.round(gunCenterP1 - realWP1 / 2), top: 200 }

  tokens.forEach(w => {
    wordEls[w.id].classList.add('uniform')
    if (w.type === 'filler') {
      wordEls[w.id].style.opacity = '0'
      wordEls[w.id].style.transform = 'scale(0.7)'
    } else {
      wordEls[w.id].style.opacity = '1'
      wordEls[w.id].style.transform = 'scale(1)'
      wordEls[w.id].classList.remove('default', 'noun', 'verb', 'adj', 'danger', 'fade-out')
      if (w.id === 'gun') wordEls[w.id].classList.add('danger')
      else wordEls[w.id].classList.add(w.type)
    }
  })
  Object.entries(textPosP1).forEach(([id, pos]) => {
    const el = wordEls[id]
    el.style.left = pos.left + 'px'
    el.style.top  = pos.top + 'px'
  })

  // visual: natural row at y=50
  const naturalOrder = ['v-person1','v-hold','v-gun','v-point','v-person2']
  const totalW = naturalOrder.reduce((s, id) => s + vMeasured[id], 0)
  const natGap = Math.max(16, Math.round((CTN_W - totalW) / (naturalOrder.length - 1)))
  const natStartX = Math.round((CTN_W - (totalW + natGap * (naturalOrder.length - 1))) / 2)
  const natY = 50
  let cx = natStartX
  naturalOrder.forEach(id => {
    vnodeEls[id].style.left = cx + 'px'
    vnodeEls[id].style.top = natY + 'px'
    cx += vMeasured[id] + natGap
  })

  vnodeDefs.forEach(def => {
    const el = vnodeEls[def.id]
    el.classList.remove('entity', 'action', 'danger')
    el.classList.add(def.type)
  })

  drawVisualAndTextArrows()
  stage5Phase = 1

  updateDots(4)
  updateLabel('跨源对齐融合 — 视觉场景图')
  updateLegend(true)
  currentStage.value = 4
  emit('stageChange', 4)

  stage5PhaseTimer = setTimeout(() => applyStage4Phase2(), 1800)
}

function applyStage4Phase2() {
  stage5Phase = 2

  const targetT = layoutRow(chainTopOrder, 45, 180)
  const gunCenter = targetT['gun'].left + wWidth('gun') / 2
  const realW = wWidth('real')
  targetT['real'] = { left: Math.round(gunCenter - realW / 2), top: 260 }

  const startT = {}
  ;['gun','using','man','robs','woman','real'].forEach(id => {
    startT[id] = { left: parseFloat(wordEls[id].style.left) || 0, top: parseFloat(wordEls[id].style.top) || 0 }
  })

  const textGunX = targetT['gun'].left + wWidth('gun') / 2
  const textManX = targetT['man'].left + wWidth('man') / 2
  const textWomanX = targetT['woman'].left + wWidth('woman') / 2
  const vMeasured = {}
  vnodeDefs.forEach(def => { vMeasured[def.id] = vnodeEls[def.id].offsetWidth })

  const pointMidX = (textGunX + textWomanX) / 2
  const targetV = {}
  targetV['v-point']   = { left: Math.round(pointMidX - vMeasured['v-point']/2),   top: 20 }
  targetV['v-person1'] = { left: Math.round(textManX - vMeasured['v-person1']/2), top: 80 }
  targetV['v-gun']     = { left: Math.round(textGunX - vMeasured['v-gun']/2),     top: 80 }
  targetV['v-person2'] = { left: Math.round(textWomanX - vMeasured['v-person2']/2), top: 80 }
  const holdMidX = (targetV['v-person1'].left + vMeasured['v-person1']/2 + targetV['v-gun'].left + vMeasured['v-gun']/2)/2
  targetV['v-hold']    = { left: Math.round(holdMidX - vMeasured['v-hold']/2),    top: 80 }

  const startV = {}
  Object.keys(targetV).forEach(id => {
    startV[id] = { left: parseFloat(vnodeEls[id].style.left) || 0, top: parseFloat(vnodeEls[id].style.top) || 0 }
  })

  const allAnimEls = [...Object.keys(targetV).map(id => vnodeEls[id]), ...Object.keys(startT).map(id => wordEls[id])]
  const savedTransitions = allAnimEls.map(el => el.style.transition)
  allAnimEls.forEach(el => el.style.transition = 'none')

  const duration = 800
  const startTime = performance.now()

  function tick(now) {
    const t = Math.min(1, (now - startTime) / duration)
    const e = t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3)/2

    Object.keys(targetV).forEach(id => {
      const s = startV[id], tg = targetV[id]
      vnodeEls[id].style.left = (s.left + (tg.left - s.left) * e) + 'px'
      vnodeEls[id].style.top  = (s.top  + (tg.top  - s.top)  * e) + 'px'
    })
    Object.keys(startT).forEach(id => {
      const s = startT[id], tg = targetT[id]
      wordEls[id].style.left = (s.left + (tg.left - s.left) * e) + 'px'
      wordEls[id].style.top  = (s.top  + (tg.top  - s.top)  * e) + 'px'
    })

    drawLayerArrows()

    if (t < 1) {
      requestAnimationFrame(tick)
    } else {
      Object.keys(targetV).forEach(id => {
        vnodeEls[id].style.left = targetV[id].left + 'px'
        vnodeEls[id].style.top  = targetV[id].top + 'px'
      })
      Object.keys(targetT).forEach(id => {
        wordEls[id].style.left = targetT[id].left + 'px'
        wordEls[id].style.top  = targetT[id].top + 'px'
      })
      allAnimEls.forEach((el, i) => { el.style.transition = savedTransitions[i] })
      drawFusionArrows()
      updateLabel('跨源对齐融合')
    }
  }

  requestAnimationFrame(tick)
}

// ── stage 5: two-phase node merge ────────────────────────────────
function applyStage5Merge() {
  if (stage5PhaseTimer) { clearTimeout(stage5PhaseTimer); stage5PhaseTimer = null }
  stage5Phase = 0
  currentStage.value = 5
  emit('stageChange', 5)

  // Reset visual nodes to original appearance
  vnodeDefs.forEach(def => {
    const el = vnodeEls[def.id]
    el.style.opacity = '1'
    el.classList.remove('hidden', 'merged')
    el.textContent = def.label
    el.style.whiteSpace = 'nowrap'
    el.style.fontSize = ''
    el.style.padding = ''
    el.style.lineHeight = ''
  })

  // Ensure all text nodes are visible
  ;['gun','using','man','robs','woman','real'].forEach(id => {
    wordEls[id].style.opacity = '1'
    wordEls[id].style.transform = 'scale(1)'
    wordEls[id].classList.add('uniform')
  })

  // Record start positions
  const startV = {}
  ;['v-person1','v-hold','v-gun','v-point','v-person2'].forEach(id => {
    startV[id] = { left: parseFloat(vnodeEls[id].style.left) || 0, top: parseFloat(vnodeEls[id].style.top) || 0 }
  })
  const startT = {}
  ;['gun','using','man','robs','woman','real'].forEach(id => {
    startT[id] = { left: parseFloat(wordEls[id].style.left) || 0, top: parseFloat(wordEls[id].style.top) || 0 }
  })

  const mergeTexts = {
    'v-person1': 'person1<br><span class="fs-sub">(man)</span>',
    'v-hold':    'hold<br><span class="fs-sub">(use)</span>',
    'v-gun':     'gun',
    'v-point':   'point',
    'v-person2': 'person2<br><span class="fs-sub">(woman)</span>',
  }

  // Measure merged widths then restore
  const origHTMLs = {}
  vnodeDefs.forEach(def => {
    origHTMLs[def.id] = vnodeEls[def.id].innerHTML
    if (mergeTexts[def.id]) {
      vnodeEls[def.id].innerHTML = mergeTexts[def.id]
      vnodeEls[def.id].classList.add('merged')
    }
  })
  const mergedW = {}
  vnodeDefs.forEach(def => { mergedW[def.id] = vnodeEls[def.id].offsetWidth })
  vnodeDefs.forEach(def => {
    vnodeEls[def.id].innerHTML = origHTMLs[def.id]
    vnodeEls[def.id].classList.remove('merged')
  })

  // Phase 1 targets: converge pairs to midpoint
  const midV = {}
  mainOrder.forEach(id => {
    if (id === 'v-point') {
      midV[id] = { left: startV[id].left, top: 40 }
    } else {
      const tId = Object.keys(mergeMap).find(k => mergeMap[k] === id)
      const midX = Math.round((startV[id].left + (tId ? startT[tId].left : startV[id].left)) / 2)
      midV[id] = { left: midX, top: 120 }
    }
  })

  const midT = {}
  Object.keys(mergeMap).forEach(tId => {
    const vId = mergeMap[tId]
    midT[tId] = { left: midV[vId].left, top: 120 }
  })
  midT['robs'] = { left: startT['robs'].left, top: 115 }
  midT['real'] = { left: startT['real'].left, top: 230 }

  const animVIds = Object.keys(midV)
  const animTIds = Object.keys(midT)
  const allAnimEls = [...animVIds.map(id => vnodeEls[id]), ...animTIds.map(id => wordEls[id])]
  const savedTransitions = allAnimEls.map(el => el.style.transition)
  allAnimEls.forEach(el => el.style.transition = 'none')

  resizeCanvas()
  // Draw first frame immediately so arrows never disconnect from nodes
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  visPairs.forEach(p => {
    const a = getVNodeRect(p.from), b = getVNodeRect(p.to)
    if (a && b) drawOneArrow(a, b, p.dashed)
  })
  textPairs.forEach(p => {
    const a = getWordRect(p.from), b = getWordRect(p.to)
    if (a && b) drawOneArrow(a, b, false)
  })

  const dur1 = 700
  const t0 = performance.now()

  function tick1(now) {
    const t = Math.min(1, (now - t0) / dur1)
    const e = t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3)/2

    animVIds.forEach(id => {
      const s = startV[id], m = midV[id]
      vnodeEls[id].style.left = (s.left + (m.left - s.left) * e) + 'px'
      vnodeEls[id].style.top  = (s.top  + (m.top  - s.top)  * e) + 'px'
    })
    animTIds.forEach(id => {
      const s = startT[id], m = midT[id]
      wordEls[id].style.left = (s.left + (m.left - s.left) * e) + 'px'
      wordEls[id].style.top  = (s.top  + (m.top  - s.top)  * e) + 'px'
    })

    ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
    visPairs.forEach(p => {
      const a = getVNodeRect(p.from), b = getVNodeRect(p.to)
      if (a && b) drawOneArrow(a, b, p.dashed)
    })
    textPairs.forEach(p => {
      const a = getWordRect(p.from), b = getWordRect(p.to)
      if (a && b) drawOneArrow(a, b, false)
    })

    if (t < 1) { requestAnimationFrame(tick1) }
    else { finishPhase1() }
  }

  function finishPhase1() {
    animVIds.forEach(id => {
      vnodeEls[id].style.left = midV[id].left + 'px'
      vnodeEls[id].style.top  = midV[id].top + 'px'
    })
    animTIds.forEach(id => {
      wordEls[id].style.left = midT[id].left + 'px'
      wordEls[id].style.top  = midT[id].top + 'px'
    })

    // Fuse
    vnodeDefs.forEach(def => {
      if (mergeTexts[def.id]) {
        vnodeEls[def.id].innerHTML = mergeTexts[def.id]
        vnodeEls[def.id].classList.add('merged')
      }
    })
    Object.keys(mergeMap).forEach(tId => {
      wordEls[tId].style.opacity = '0'
      wordEls[tId].style.transform = 'scale(0.7)'
    })

    // Gap: keep redrawing all arrows so they stay linked to fused nodes
    const gapStart = performance.now()
    const gapDuration = 400
    function gapTick(now) {
      ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
      ;[
        { from: 'v-person1', to: 'v-hold' },
        { from: 'v-hold',    to: 'v-gun' },
        { from: 'v-gun',     to: 'v-point',   dashed: true },
        { from: 'v-point',   to: 'v-person2', dashed: true },
        { from: 'v-person1', to: 'robs' },
        { from: 'robs',      to: 'v-person2' },
        { from: 'real',      to: 'v-gun' },
      ].forEach(p => {
        const a = getAnyRect(p.from), b = getAnyRect(p.to)
        if (a && b) drawOneArrow(a, b, p.dashed)
      })
      if (now - gapStart < gapDuration) {
        requestAnimationFrame(gapTick)
      } else {
        startPhase2()
      }
    }
    requestAnimationFrame(gapTick)
  }

  function startPhase2() {
    const p2MergedW = {}
    vnodeDefs.forEach(def => { p2MergedW[def.id] = vnodeEls[def.id].offsetWidth })

    const p2StartV = {}
    animVIds.forEach(id => {
      p2StartV[id] = { left: parseFloat(vnodeEls[id].style.left), top: parseFloat(vnodeEls[id].style.top) }
    })
    const p2StartT = {}
    ;['robs','real'].forEach(id => {
      p2StartT[id] = { left: parseFloat(wordEls[id].style.left), top: parseFloat(wordEls[id].style.top) }
    })

    const mainY = 110, mainGap = 26
    const mainTotalW = mainOrder.reduce((s, id) => s + p2MergedW[id], 0) + mainGap * (mainOrder.length - 1)
    const mainStartX = Math.round((CTN_W - mainTotalW) / 2)

    const finalV = {}
    let cx = mainStartX
    mainOrder.forEach(id => {
      finalV[id] = { left: cx, top: mainY }
      cx += p2MergedW[id] + mainGap
    })

    const finalT = {}
    const p1cx = finalV['v-person1'].left + p2MergedW['v-person1'] / 2
    const p2cx = finalV['v-person2'].left + p2MergedW['v-person2'] / 2
    finalT['robs'] = { left: Math.round((p1cx + p2cx)/2 - wWidth('robs')/2), top: 50 }
    const gunCx = finalV['v-gun'].left + p2MergedW['v-gun'] / 2
    finalT['real'] = { left: Math.round(gunCx - wWidth('real')/2), top: 200 }

    const p2AnimVIds = Object.keys(finalV)
    const p2AnimTIds = Object.keys(finalT)

    const dur2 = 700
    const t1 = performance.now()

    function tick2(now) {
      const t = Math.min(1, (now - t1) / dur2)
      const e = t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t + 2, 3)/2

      p2AnimVIds.forEach(id => {
        const s = p2StartV[id], f = finalV[id]
        vnodeEls[id].style.left = (s.left + (f.left - s.left) * e) + 'px'
        vnodeEls[id].style.top  = (s.top  + (f.top  - s.top)  * e) + 'px'
      })
      p2AnimTIds.forEach(id => {
        const s = p2StartT[id], f = finalT[id]
        wordEls[id].style.left = (s.left + (f.left - s.left) * e) + 'px'
        wordEls[id].style.top  = (s.top  + (f.top  - s.top)  * e) + 'px'
      })

      ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
      ;[
        { from: 'v-person1', to: 'v-hold' },
        { from: 'v-hold',    to: 'v-gun' },
        { from: 'v-gun',     to: 'v-point',   dashed: true },
        { from: 'v-point',   to: 'v-person2', dashed: true },
        { from: 'v-person1', to: 'robs' },
        { from: 'robs',      to: 'v-person2' },
        { from: 'real',      to: 'v-gun' },
      ].forEach(p => {
        const a = getAnyRect(p.from), b = getAnyRect(p.to)
        if (a && b) drawOneArrow(a, b, p.dashed)
      })

      if (t < 1) { requestAnimationFrame(tick2) }
      else {
        p2AnimVIds.forEach(id => {
          vnodeEls[id].style.left = finalV[id].left + 'px'
          vnodeEls[id].style.top  = finalV[id].top + 'px'
        })
        p2AnimTIds.forEach(id => {
          wordEls[id].style.left = finalT[id].left + 'px'
          wordEls[id].style.top  = finalT[id].top + 'px'
        })
        allAnimEls.forEach((el, i) => { el.style.transition = savedTransitions[i] })
        drawMergedArrows()
        updateLabel('跨源节点合并')
      }
    }

    requestAnimationFrame(tick2)
    updateLabel('跨源节点合并 — 构建合并中...')
  }

  requestAnimationFrame(tick1)

  updateDots(5)
  updateLabel('跨源节点合并 — 拉近融合中...')
  updateLegend(true)
}

// ── main stage application ───────────────────────────────────────
function applyStage(stage) {
  if (stage < 5) resetStage5Phase()

  wordEls['using'].textContent = stage >= 3 ? 'use' : 'using'

  const visible = {}
  tokens.forEach(w => {
    if (w.type === 'filler' && stage >= 2) visible[w.id] = false
    else if (w.id === 'using' && stage >= 4) visible[w.id] = true
    else visible[w.id] = true
  })

  tokens.forEach(w => {
    const el = wordEls[w.id]
    if (visible[w.id]) {
      el.style.opacity = '1'; el.style.transform = 'scale(1)'
    } else {
      el.style.opacity = '0'; el.style.transform = 'scale(0.7)'
    }
  })

  // Stage-specific layout
  if (stage <= 2) {
    // sentence row
    tokens.forEach(w => { wordEls[w.id].classList.remove('uniform') })
    const positions = layoutRow(sentenceOrder, 16, 120)
    Object.entries(positions).forEach(([id, pos]) => {
      const el = wordEls[id]
      el.style.left = pos.left + 'px'
      el.style.top  = pos.top + 'px'
    })
    // hide visual nodes
    vnodeDefs.forEach(def => {
      vnodeEls[def.id].classList.add('hidden')
      vnodeEls[def.id].style.opacity = '0'
    })
    animateArrows(() => drawTextArrowsLive(stage), 1050)
  } else if (stage === 3) {
    // chain layout
    tokens.forEach(w => { wordEls[w.id].classList.add('uniform') })
    const positions = layoutRow(chainTopOrder, 60, 110)
    const gunCenter = positions['gun'].left + wWidth('gun') / 2
    const realW = wWidth('real')
    positions['real'] = { left: Math.round(gunCenter - realW / 2), top: 200 }
    Object.entries(positions).forEach(([id, pos]) => {
      const el = wordEls[id]
      el.style.left = pos.left + 'px'
      el.style.top  = pos.top + 'px'
    })
    // hide visual nodes
    vnodeDefs.forEach(def => {
      vnodeEls[def.id].classList.add('hidden')
      vnodeEls[def.id].style.opacity = '0'
    })
    animateArrows(() => drawTextArrowsLive(stage), 1100)
  } else if (stage === 4) {
    applyStage4TwoPhase()
    currentStage.value = 4
    emit('stageChange', 4)
    return
  } else {
    // stage 5
    applyStage5Merge()
    return
  }

  // Apply CSS classes to word elements
  tokens.forEach(w => {
    const el = wordEls[w.id]
    el.classList.remove('default', 'noun', 'verb', 'adj', 'danger', 'fade-out')
    if (!visible[w.id]) {
      el.classList.add('fade-out')
    } else if (stage >= 1) {
      if (w.id === 'gun' && stage >= 4) {
        el.classList.add('danger')
      } else {
        el.classList.add(w.type)
      }
    } else {
      el.classList.add('default')
    }
  })

  currentStage.value = stage
  emit('stageChange', stage)

  const labels = [
    '文本输入', '依存句法分析', '三元关系组构建',
    '结构文本场景图', '跨源对齐融合', '跨源节点合并'
  ]
  updateLabel(`Step ${stage + 1}/${totalStages + 1}: ${labels[stage]}`)
  updateDots(stage)
  updateLegend(stage >= 1)
}

// ── navigation ───────────────────────────────────────────────────
function nextStage() {
  if (currentStage.value < totalStages) {
    resetStage5Phase()
    applyStage(currentStage.value + 1)
  }
}

function prevStage() {
  if (currentStage.value > 0) {
    resetStage5Phase()
    applyStage(currentStage.value - 1)
  }
}

function resetAll() {
  stopAutoPlay()
  resetStage5Phase()
  applyStage(0)
}

function toggleAutoPlay() {
  if (isAutoPlaying.value) { stopAutoPlay(); return }
  isAutoPlaying.value = true
  applyStage(0)
  advanceAuto()
}

function stopAutoPlay() {
  isAutoPlaying.value = false
  if (autoPlayTimer) clearTimeout(autoPlayTimer)
  autoPlayTimer = null
}

const stageDurations = [2000, 1500, 1800, 2200, 4000, 3000]

function advanceAuto() {
  if (!isAutoPlaying.value) return
  if (currentStage.value < totalStages) {
    nextStage()
    autoPlayTimer = setTimeout(advanceAuto, stageDurations[currentStage.value])
  } else {
    stopAutoPlay()
  }
}

// ── keyboard ─────────────────────────────────────────────────────
function onKeydown(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); nextStage() }
  if (e.key === 'ArrowLeft') { e.preventDefault(); prevStage() }
  if (e.key === 'r') resetAll()
  if (e.key === 'p') toggleAutoPlay()
}

// ── resize handler ───────────────────────────────────────────────
function onResize() {
  resizeCanvas()
  if (currentStage.value >= 4) {
    if (currentStage.value === 5) {
      // Re-apply merged layout
      const mergeTexts = {
        'v-person1': 'person1<br><span class="fs-sub">(man)</span>',
        'v-hold':    'hold<br><span class="fs-sub">(use)</span>',
        'v-gun':     'gun', 'v-point': 'point',
        'v-person2': 'person2<br><span class="fs-sub">(woman)</span>',
      }
      vnodeDefs.forEach(def => {
        if (mergeTexts[def.id]) {
          vnodeEls[def.id].innerHTML = mergeTexts[def.id]
          vnodeEls[def.id].classList.add('merged')
        }
      })
      ;['man','using','gun','woman'].forEach(id => {
        wordEls[id].style.opacity = '0'
        wordEls[id].style.transform = 'scale(0.7)'
      })
      ;['robs','real'].forEach(id => {
        wordEls[id].style.opacity = '1'
        wordEls[id].style.transform = 'scale(1)'
        wordEls[id].classList.add('uniform')
      })
      const mW = {}
      vnodeDefs.forEach(def => { mW[def.id] = vnodeEls[def.id].offsetWidth })
      const mainY = 110, mainGap = 26
      const mainTotalW = mainOrder.reduce((s, id) => s + mW[id], 0) + mainGap * (mainOrder.length - 1)
      const mainStartX = Math.round((CTN_W - mainTotalW) / 2)
      let cx = mainStartX
      mainOrder.forEach(id => {
        vnodeEls[id].style.left = cx + 'px'
        vnodeEls[id].style.top = mainY + 'px'
        cx += mW[id] + mainGap
      })
      const p1cx = parseFloat(vnodeEls['v-person1'].style.left) + mW['v-person1']/2
      const p2cx = parseFloat(vnodeEls['v-person2'].style.left) + mW['v-person2']/2
      const gunCx = parseFloat(vnodeEls['v-gun'].style.left) + mW['v-gun']/2
      wordEls['robs'].style.left = Math.round((p1cx + p2cx)/2 - wWidth('robs')/2) + 'px'
      wordEls['robs'].style.top = '50px'
      wordEls['real'].style.left = Math.round(gunCx - wWidth('real')/2) + 'px'
      wordEls['real'].style.top = '200px'
      drawMergedArrows()
    } else if (stage5Phase === 1) {
      const textPosP1 = layoutRow(chainTopOrder, 60, 110)
      const gunC = textPosP1['gun'].left + wWidth('gun') / 2
      textPosP1['real'] = { left: Math.round(gunC - wWidth('real') / 2), top: 200 }
      Object.entries(textPosP1).forEach(([id, pos]) => {
        wordEls[id].style.left = pos.left + 'px'
        wordEls[id].style.top  = pos.top + 'px'
      })
      const vMeasured = {}
      vnodeDefs.forEach(def => { vMeasured[def.id] = vnodeEls[def.id].offsetWidth })
      const naturalOrder = ['v-person1','v-hold','v-gun','v-point','v-person2']
      const totalW = naturalOrder.reduce((s, id) => s + vMeasured[id], 0)
      const natGap = Math.max(16, Math.round((CTN_W - totalW) / (naturalOrder.length - 1)))
      const natStartX = Math.round((CTN_W - (totalW + natGap * (naturalOrder.length - 1))) / 2)
      let cx = natStartX
      naturalOrder.forEach(id => {
        vnodeEls[id].style.left = cx + 'px'
        vnodeEls[id].style.top = '50px'
        cx += vMeasured[id] + natGap
      })
      drawVisualAndTextArrows()
    } else {
      const positions = layoutRow(chainTopOrder, 45, 180)
      const gunCenter = positions['gun'].left + wWidth('gun') / 2
      positions['real'] = { left: Math.round(gunCenter - wWidth('real') / 2), top: 260 }
      Object.entries(positions).forEach(([id, pos]) => {
        wordEls[id].style.left = pos.left + 'px'
        wordEls[id].style.top  = pos.top + 'px'
      })
      const textGunX = positions['gun'].left + wWidth('gun') / 2
      const textManX = positions['man'].left + wWidth('man') / 2
      const textWomanX = positions['woman'].left + wWidth('woman') / 2
      const vMeasured = {}
      vnodeDefs.forEach(def => { vMeasured[def.id] = vnodeEls[def.id].offsetWidth })
      const pointMidX = (textGunX + textWomanX) / 2
      const vPositions = {
        'v-point': { left: Math.round(pointMidX - vMeasured['v-point']/2), top: 20 },
      }
      const vY = 80
      vPositions['v-person1'] = { left: Math.round(textManX - vMeasured['v-person1']/2), top: vY }
      vPositions['v-gun']     = { left: Math.round(textGunX - vMeasured['v-gun']/2), top: vY }
      vPositions['v-person2'] = { left: Math.round(textWomanX - vMeasured['v-person2']/2), top: vY }
      const holdMidX = (vPositions['v-person1'].left + vMeasured['v-person1']/2 + vPositions['v-gun'].left + vMeasured['v-gun']/2)/2
      vPositions['v-hold'] = { left: Math.round(holdMidX - vMeasured['v-hold']/2), top: vY }
      Object.entries(vPositions).forEach(([id, pos]) => {
        vnodeEls[id].style.left = pos.left + 'px'
        vnodeEls[id].style.top = pos.top + 'px'
      })
      drawFusionArrows()
    }
  } else {
    drawTextArrows(currentStage.value)
  }
  // Redraw current frame + cumulative graphs
  const video = maskedVideoRef.value
  if (video) {
    const frame = Math.min(TOTAL_FRAMES, Math.floor(video.currentTime * FPS) + 1)
    const cur = getCurrentGraph(frame)
    renderCurrentGraph(cur.nodes, cur.arrows)
  }
  if (cumulativePhase === 0) {
    initCumulativeBasic()
  } else {
    const allIds = ['person1','hold','gun','point','person2']
    const allLabels = ['person1','hold','gun','point','person2']
    const allTypes = ['entity','action','danger','action','entity']
    cumNodes = layoutCumulative(allIds, allLabels, allTypes)
    buildCumulativeDOM()
  }
}

// ── lifecycle ────────────────────────────────────────────────────
onMounted(() => {
  const container = containerRef.value
  const canvas = canvasRef.value
  ctx = canvas.getContext('2d')

  // Create word elements
  tokens.forEach(w => {
    const el = document.createElement('span')
    el.className = 'fs-word default'
    el.textContent = w.text
    el.id = 'word-' + w.id
    el.style.opacity = '0'
    el.style.left = '0px'
    el.style.top = '0px'
    container.appendChild(el)
    wordEls[w.id] = el
  })

  // Create visual node elements
  vnodeDefs.forEach(def => {
    const el = document.createElement('span')
    el.className = 'fs-vnode hidden ' + def.type
    el.textContent = def.label
    el.id = def.id
    el.style.opacity = '0'
    el.style.left = '0px'
    el.style.top = '0px'
    container.appendChild(el)
    vnodeEls[def.id] = el
  })

  resizeCanvas()
  window.addEventListener('resize', onResize)
  document.addEventListener('keydown', onKeydown)

  // Visual section: init cumulative graph + video sync
  const video = maskedVideoRef.value
  if (video) {
    initCumulativeBasic()
    updateForFrame(1)

    video.addEventListener('timeupdate', () => {
      const frame = Math.min(TOTAL_FRAMES, Math.floor(video.currentTime * FPS) + 1)
      if (frame < 10 && cumulativePhase >= 1) resetCumulative()
      updateForFrame(frame)
    })
    video.addEventListener('seeked', () => {
      const frame = Math.min(TOTAL_FRAMES, Math.floor(video.currentTime * FPS) + 1)
      if (frame < 10 && cumulativePhase >= 1) resetCumulative()
      updateForFrame(frame)
    })

    // Auto-play video
    video.play().catch(() => {})
  }

  // Initial render
  nextTick(() => {
    resizeCanvas()
    applyStage(0)
  })

  // Auto-play if requested
  if (props.autoPlay) {
    setTimeout(() => toggleAutoPlay(), 500)
  }
})

onBeforeUnmount(() => {
  stopAutoPlay()
  if (redrawTimer) clearTimeout(redrawTimer)
  if (stage5PhaseTimer) clearTimeout(stage5PhaseTimer)
  window.removeEventListener('resize', onResize)
  document.removeEventListener('keydown', onKeydown)
})

// ── expose ───────────────────────────────────────────────────────
defineExpose({ currentStage, nextStage, prevStage, resetAll, toggleAutoPlay })
</script>

<style>
/* ── Fusion Scene — isolated dark theme ────────────────────────── */
.fs-root {
  --fs-bg: #0d1117;
  --fs-surface: #161b22;
  --fs-border: #30363d;
  --fs-text: #c9d1d9;
  --fs-muted: #8b949e;
  --fs-accent: #58a6ff;
  --fs-success: #3fb950;
  --fs-noun: #ffa657;
  --fs-verb: #79c0ff;
  --fs-adj: #7ee787;
  --fs-danger: #ff4a4a;

  background: transparent;
  border-radius: 14px;
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 640px;
  font-family: 'PingFang SC', 'SF Pro Display', 'Helvetica Neue', sans-serif;
  color: #e6edf3;
  overflow: hidden;
  user-select: none;
}

/* ── visual row (masked video + current + cumulative graphs) ──── */
.fs-visual-row {
  position: absolute; top: 0; left: 0; right: 0; height: 240px;
  display: flex; gap: 10px; padding: 8px 12px;
  border-bottom: 1px solid #21262d;
}
.fs-video-col {
  flex: 0 0 270px; display: flex; flex-direction: column; gap: 4px;
}
.fs-masked-video {
  width: 100%; height: 185px; border-radius: 6px;
  border: 1px solid #30363d; background: #000;
  object-fit: cover;
}
.fs-frame-badge {
  font-size: 10px; color: #8b949e; text-align: center;
}
.fs-graphs-col {
  flex: 1; display: flex; flex-direction: column; gap: 4px;
  min-width: 0;
}
.fs-graph-panel {
  flex: 1; display: flex; flex-direction: column;
}
.fs-panel-label {
  font-size: 10px; color: #8b949e; text-transform: uppercase;
  letter-spacing: 0.06em; margin-bottom: 2px;
}
.fs-graph-stage {
  flex: 1; position: relative; background: rgba(6, 11, 26, 0.35);
  border: 1px solid #21262d; border-radius: 6px; overflow: hidden;
}
.fs-graph-canvas {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; pointer-events: none; z-index: 0;
}
.fs-gnode {
  position: absolute;
  padding: 6px 14px; border-radius: 6px;
  font-size: 15px; font-weight: 600;
  white-space: nowrap; z-index: 1;
  border: 1.5px solid transparent;
}
.fs-gnode.entity  { color: #ffa657; background: rgba(255,166,87,0.10); border-color: rgba(255,166,87,0.35); }
.fs-gnode.action  { color: #79c0ff; background: rgba(121,192,255,0.10); border-color: rgba(121,192,255,0.35); }
.fs-gnode.danger  { color: #ff4a4a; background: rgba(255,74,74,0.15); border-color: rgba(255,74,74,0.5);
                    box-shadow: 0 0 10px rgba(255,74,74,0.2); }

/* ── stage indicators (shifted below visual row) ──────────────── */
.fs-stage-indicator {
  position: absolute; top: 250px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 8px; z-index: 10;
}
.fs-stage-dot {
  width: 28px; height: 3px; border-radius: 2px;
  background: #30363d; transition: all 0.5s ease;
}
.fs-stage-dot.active { background: #58a6ff; box-shadow: 0 0 6px rgba(88,166,255,0.5); }
.fs-stage-dot.done { background: #3fb950; }

.fs-stage-label {
  position: absolute; top: 266px; left: 50%; transform: translateX(-50%);
  font-size: 12px; color: #8b949e; letter-spacing: 0.04em;
  transition: all 0.5s ease; z-index: 10;
  white-space: nowrap;
}

.fs-main-container {
  position: absolute; top: 288px; left: 8px; right: 8px;
  bottom: 52px;
}

.fs-main-container canvas {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; z-index: 1;
}

/* ── word elements ─────────────────────────────────────────────── */
.fs-word {
  position: absolute;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 15px; font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
  transition: left 0.9s cubic-bezier(0.34, 1.56, 0.64, 1),
              top 0.9s cubic-bezier(0.34, 1.56, 0.64, 1),
              background 0.5s ease,
              color 0.5s ease,
              opacity 0.4s ease,
              transform 0.5s ease,
              box-shadow 0.5s ease,
              border-color 0.5s ease;
  z-index: 2;
  border: 1.5px solid transparent;
  text-align: center;
  min-width: 44px;
}
.fs-word.default  { color: #c9d1d9; background: rgba(48,54,61,0.6); border-color: #30363d; }
.fs-word.noun     { color: #ffa657; background: rgba(255,166,87,0.12); border-color: rgba(255,166,87,0.4); }
.fs-word.verb     { color: #79c0ff; background: rgba(121,192,255,0.12); border-color: rgba(121,192,255,0.4); }
.fs-word.adj      { color: #7ee787; background: rgba(126,231,135,0.12); border-color: rgba(126,231,135,0.4); }
.fs-word.danger   { color: #ff4a4a; background: rgba(255,74,74,0.15); border-color: rgba(255,74,74,0.5);
                    box-shadow: 0 0 16px rgba(255,74,74,0.3); animation: fs-pulse-red 1.2s ease-in-out infinite; }
.fs-word.fade-out { opacity: 0; transform: scale(0.7); pointer-events: none; }
.fs-word.uniform  { min-width: 70px; padding: 5px 12px; font-size: 14px; }

@keyframes fs-pulse-red {
  0%, 100% { box-shadow: 0 0 16px rgba(255,74,74,0.3); }
  50%      { box-shadow: 0 0 26px rgba(255,74,74,0.6); }
}

/* ── visual node elements ──────────────────────────────────────── */
.fs-vnode {
  position: absolute;
  padding: 5px 12px; border-radius: 6px;
  font-size: 14px; font-weight: 600;
  white-space: nowrap;
  transition: left 0.7s ease, top 0.7s ease, opacity 0.4s ease;
  border: 1.5px solid transparent;
  z-index: 2; text-align: center;
  min-width: 70px;
}
.fs-vnode.entity  { color: #ffa657; background: rgba(255,166,87,0.10); border-color: rgba(255,166,87,0.35); }
.fs-vnode.action  { color: #79c0ff; background: rgba(121,192,255,0.10); border-color: rgba(121,192,255,0.35); }
.fs-vnode.danger  { color: #ff4a4a; background: rgba(255,74,74,0.15); border-color: rgba(255,74,74,0.5);
                    box-shadow: 0 0 12px rgba(255,74,74,0.25); }
.fs-vnode.hidden  { opacity: 0; transform: scale(0.7); pointer-events: none; }
.fs-vnode.merged  { white-space: normal; line-height: 1.2; font-size: 13px; padding: 5px 10px; }
.fs-sub           { display: block; font-size: 0.72em; opacity: 0.7; font-weight: 400; }

/* ── legend ────────────────────────────────────────────────────── */
.fs-legend {
  position: absolute; bottom: 42px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 18px; font-size: 11px; color: #8b949e;
  opacity: 0; transition: opacity 0.6s ease; z-index: 10;
}
.fs-legend.visible { opacity: 1; }
.fs-legend-item { display: flex; align-items: center; gap: 5px; }
.fs-legend-dot { width: 8px; height: 8px; border-radius: 2px; }
.fs-legend-dot.noun   { background: #ffa657; }
.fs-legend-dot.verb   { background: #79c0ff; }
.fs-legend-dot.adj    { background: #7ee787; }
.fs-legend-dot.danger { background: #ff4a4a; }

/* ── controls ──────────────────────────────────────────────────── */
.fs-controls {
  position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 12px; z-index: 10;
}
.fs-ctrl-btn {
  padding: 6px 18px; border-radius: 6px; border: 1px solid #30363d;
  background: #161b22; color: #c9d1d9;
  font-size: 13px; cursor: pointer; white-space: nowrap;
  transition: all 0.2s ease;
}
.fs-ctrl-btn:hover { border-color: #58a6ff; color: #e6edf3; background: #1c2333; }
.fs-ctrl-btn:disabled { opacity: 0.35; cursor: default; }
.fs-ctrl-btn.play { border-color: #3fb950; color: #3fb950; }
.fs-ctrl-btn.playing { border-color: #d79a45; color: #d79a45; }
</style>
