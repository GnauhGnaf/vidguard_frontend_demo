<template>
  <div class="mfs-root" ref="rootRef">
    <!-- Visual row: masked video + current frame graph + cumulative scene graph -->
    <div class="mfs-visual-row">
      <div class="mfs-video-col">
        <video ref="maskedVideoRef" src="/safe_masked.mp4" muted loop playsinline
               class="mfs-masked-video"></video>
        <span class="mfs-frame-badge" ref="frameBadge">frame 1 / 141</span>
      </div>
      <div class="mfs-graphs-col">
        <div class="mfs-graph-panel">
          <span class="mfs-panel-label">当前帧场景图</span>
          <div class="mfs-graph-stage" ref="currentStageRef">
            <canvas class="mfs-graph-canvas" ref="currentCanvasRef"></canvas>
          </div>
        </div>
        <div class="mfs-graph-panel">
          <span class="mfs-panel-label">累计场景图</span>
          <div class="mfs-graph-stage" ref="cumulativeStageRef">
            <canvas class="mfs-graph-canvas" ref="cumulativeCanvasRef"></canvas>
          </div>
        </div>
      </div>
    </div>

    <div class="mfs-stage-indicator" ref="stageIndicator">
      <div v-for="i in 6" :key="i" class="mfs-stage-dot" :data-stage="i-1"></div>
    </div>
    <div class="mfs-stage-label" ref="stageLabel">完整句子</div>

    <div class="mfs-main-container" ref="containerRef">
      <canvas ref="canvasRef"></canvas>
    </div>

    <div class="mfs-legend" ref="legendRef">
      <span class="mfs-legend-item"><span class="mfs-legend-dot noun"></span> 名词</span>
      <span class="mfs-legend-item"><span class="mfs-legend-dot verb"></span> 动词</span>
    </div>

    <div class="mfs-controls">
      <button class="mfs-ctrl-btn" :disabled="currentStage <= 0" @click="prevStage">← 上一步</button>
      <button class="mfs-ctrl-btn play" :class="{ playing: isAutoPlaying }" @click="toggleAutoPlay">
        {{ isAutoPlaying ? '⏸ 暂停' : '▶ 自动播放' }}
      </button>
      <button class="mfs-ctrl-btn" :disabled="currentStage >= totalStages" @click="nextStage">下一步 →</button>
      <button class="mfs-ctrl-btn" @click="resetAll">↺ 重置</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { sceneData } from '../data/safe_scene_graph.js'

const props = defineProps({
  sentence: { type: String, default: 'The woman drinks water using the bottle' },
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

let cumulativePhase = 0
let cumNodes = {}
let cumArrows = []
let cumTransitioning = false

function getCurrentGraph(frame) {
  const data = sceneData[frame]
  if (!data) return { nodes: {}, arrows: [] }
  return { nodes: data.nodes, arrows: data.arrows }
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

  container.querySelectorAll('.mfs-gnode').forEach(el => el.remove())

  const ids = Object.keys(nodes)
  if (ids.length === 0) { curCtx.clearRect(0, 0, rect.width, rect.height); return }

  const measured = {}
  ids.forEach(id => {
    const def = nodes[id]
    const el = document.createElement('span')
    el.className = 'mfs-gnode ' + def.type
    el.textContent = def.label
    el.style.left = '-9999px'
    container.appendChild(el)
    measured[id] = { width: el.offsetWidth, height: el.offsetHeight }
    el.remove()
  })

  // Same layout as cumulative: 5 base nodes on row 1, drink on row 2
  const hasDrink = ids.includes('drink')
  const baseIds = ['person1', 'touch', 'bottle', 'contain', 'water'].filter(id => ids.includes(id))

  const positions = {}

  function layoutOneRow(rowIds, y) {
    const rowW = rowIds.reduce((s, id) => s + measured[id].width, 0)
    let gap, startX
    if (rowIds.length <= 1) {
      gap = 0; startX = Math.round((rect.width - rowW) / 2)
    } else {
      gap = Math.round((rect.width - rowW) / (rowIds.length - 1))
      if (gap < 18) gap = 18
      startX = Math.round((rect.width - (rowW + gap * (rowIds.length - 1))) / 2)
      if (startX < 4) startX = 4
    }
    let cx = startX
    rowIds.forEach(id => {
      positions[id] = { left: cx, top: y, width: measured[id].width, height: measured[id].height }
      cx += measured[id].width + gap
    })
  }

  layoutOneRow(baseIds, 14)
  if (hasDrink) layoutOneRow(['drink'], 56)

  ids.forEach(id => {
    const def = nodes[id]
    const pos = positions[id]
    const el = document.createElement('span')
    el.className = 'mfs-gnode ' + def.type
    el.textContent = def.label
    el.style.left = pos.left + 'px'
    el.style.top = pos.top + 'px'
    container.appendChild(el)
  })

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
  el.className = 'mfs-gnode ' + type
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
  const startX = Math.max(4, Math.round((rect.width - (totalW + gap * (n - 1))) / 2))
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
  const els = container.querySelectorAll('.mfs-gnode')
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

  const pos = {}
  Object.keys(cumNodes).forEach(l => { const r = getCumDOMNodeRect(l); if (r) pos[l] = r })

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
    cumCtx.beginPath(); cumCtx.moveTo(sx, sy); cumCtx.lineTo(ex, ey); cumCtx.stroke()

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
  container.querySelectorAll('.mfs-gnode').forEach(el => el.remove())
  Object.entries(cumNodes).forEach(([id, n]) => {
    const el = document.createElement('span')
    el.className = 'mfs-gnode ' + n.type
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
    ['person1', 'touch', 'bottle', 'contain', 'water'],
    ['person1', 'touch', 'bottle', 'contain', 'water'],
    ['entity', 'action', 'entity', 'action', 'entity']
  )
  cumArrows = [
    { from: 'person1', to: 'touch' },
    { from: 'touch',   to: 'bottle' },
    { from: 'bottle',  to: 'contain' },
    { from: 'contain', to: 'water' },
  ]
  buildCumulativeDOM()
}

function expandCumulative() {
  if (cumTransitioning || cumulativePhase >= 1) return
  cumTransitioning = true
  cumulativePhase = 1

  const container = cumulativeStageRef.value
  const rect = container.getBoundingClientRect()

  // Row 1: 5 base nodes
  const row1Ids = ['person1', 'touch', 'bottle', 'contain', 'water']
  const row1Labels = ['person1', 'touch', 'bottle', 'contain', 'water']
  const row1Types = ['entity', 'action', 'entity', 'action', 'entity']
  const row1Measured = row1Ids.map((id, i) => ({ id, ...measureCumNode(row1Labels[i], row1Types[i]) }))
  const row1W = row1Measured.reduce((s, m) => s + m.w, 0)
  let gap1 = Math.round((rect.width - row1W) / (row1Ids.length - 1))
  if (gap1 < 18) gap1 = 18

  // Row 2: drink node
  const drinkM = measureCumNode('drink', 'action')

  const target = {}

  // Layout row 1 at top: 14
  const startX1 = Math.max(4, Math.round((rect.width - (row1W + gap1 * (row1Ids.length - 1))) / 2))
  let cx = startX1
  row1Measured.forEach(m => {
    target[m.id] = { left: cx, top: 14, width: m.w, height: m.h, label: row1Labels[row1Ids.indexOf(m.id)], type: row1Types[row1Ids.indexOf(m.id)] }
    cx += m.w + gap1
  })

  // Layout row 2: drink centered, below row 1
  const row2Y = 56
  target['drink'] = { left: Math.max(4, Math.round((rect.width - drinkM.w) / 2)), top: row2Y, width: drinkM.w, height: drinkM.h, label: 'drink', type: 'action' }

  const newEls = {}
  ;['drink'].forEach(id => {
    const t = target[id]
    const el = document.createElement('span')
    el.className = 'mfs-gnode ' + t.type
    el.textContent = t.label
    el.style.left = t.left + 'px'
    el.style.top = t.top + 'px'
    el.style.opacity = '0'
    container.appendChild(el)
    newEls[id] = el
  })

  container.querySelectorAll('.mfs-gnode').forEach(el => {
    if (newEls[el.textContent]) return
    const allLabels = ['person1', 'touch', 'bottle', 'contain', 'water', 'drink']
    const allIds = ['person1', 'touch', 'bottle', 'contain', 'water', 'drink']
    const id = allIds.find(i => allLabels[allIds.indexOf(i)] === el.textContent)
    if (id && target[id]) {
      el.style.transition = 'left 0.5s ease'
      el.style.left = target[id].left + 'px'
      el.style.top = target[id].top + 'px'
    }
  })

  cumNodes = target
  cumArrows = [
    { from: 'person1', to: 'touch' },
    { from: 'touch',   to: 'bottle' },
    { from: 'bottle',  to: 'contain' },
    { from: 'contain', to: 'water' },
    { from: 'person1', to: 'drink' },
    { from: 'drink',   to: 'water' },
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
  if (frame >= 53 && cumulativePhase < 1) expandCumulative()
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
  { id: 'woman',  text: 'woman',  type: 'noun'   },
  { id: 'drinks', text: 'drinks', type: 'verb'   },
  { id: 'water',  text: 'water',  type: 'noun'   },
  { id: 'using',  text: 'using',  type: 'verb'   },
  { id: 'the2',   text: 'the',    type: 'filler' },
  { id: 'bottle', text: 'bottle', type: 'noun'   },
]

const sentenceOrder = ['the1', 'woman', 'drinks', 'water', 'using', 'the2', 'bottle']
const chainTopOrder = ['bottle', 'using', 'woman', 'drinks', 'water']

const arrowDefs = {
  3: [
    { from: 'woman',  to: 'drinks' },
    { from: 'drinks', to: 'water'  },
    { from: 'using',  to: 'bottle' },
    { from: 'woman',  to: 'using'  },
  ],
}

const vnodeDefs = [
  { id: 'v-person1', label: 'person1', type: 'entity' },
  { id: 'v-touch',   label: 'touch',   type: 'action' },
  { id: 'v-bottle',  label: 'bottle',  type: 'entity' },
  { id: 'v-contain', label: 'contain', type: 'action' },
  { id: 'v-water',   label: 'water',   type: 'entity' },
  { id: 'v-drink',   label: 'drink',   type: 'action' },
]

const visPairs = [
  { from: 'v-person1', to: 'v-touch' },
  { from: 'v-touch',   to: 'v-bottle' },
  { from: 'v-bottle',  to: 'v-contain' },
  { from: 'v-contain', to: 'v-water' },
  { from: 'v-person1', to: 'v-drink' },
  { from: 'v-drink',   to: 'v-water' },
]
const textPairs = [
  { from: 'woman',  to: 'drinks' },
  { from: 'drinks', to: 'water'  },
  { from: 'using',  to: 'bottle' },
  { from: 'woman',  to: 'using'  },
]
const crossPairs = [
  { v: 'v-person1', t: 'woman'  },
  { v: 'v-touch',   t: 'using'  },
  { v: 'v-bottle',  t: 'bottle' },
  { v: 'v-water',   t: 'water'  },
  { v: 'v-drink',   t: 'drinks' },
]

const mergeMap = { 'woman': 'v-person1', 'using': 'v-touch', 'bottle': 'v-bottle', 'water': 'v-water', 'drinks': 'v-drink' }
const mainOrder = ['v-person1', 'v-touch', 'v-bottle', 'v-contain', 'v-drink', 'v-water']

// ── elements ─────────────────────────────────────────────────────
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
  const w = el.offsetWidth, h = el.offsetHeight
  return { left, top, right: left + w, bottom: top + h, cx: left + w / 2, cy: top + h / 2 }
}

function getVNodeRect(id) {
  const el = vnodeEls[id]
  if (!el) return null
  const left = parseFloat(el.style.left) || 0
  const top  = parseFloat(el.style.top)  || 0
  const w = el.offsetWidth, h = el.offsetHeight
  return { left, top, right: left + w, bottom: top + h, cx: left + w/2, cy: top + h/2 }
}

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

function drawOneArrow(fromRect, toRect, dashed, color) {
  const dx = toRect.cx - fromRect.cx, dy = toRect.cy - fromRect.cy
  const len = Math.sqrt(dx*dx+dy*dy)
  if (len < 1) return
  const ux = dx/len, uy = dy/len
  const start = rayRectExit(fromRect.cx, fromRect.cy, ux, uy, fromRect, -2)
  const end   = rayRectExit(toRect.cx, toRect.cy, -ux, -uy, toRect, -2)
  const headLen = 12
  const c = color || '#8b949e'

  ctx.strokeStyle = c; ctx.lineWidth = 2
  if (dashed) ctx.setLineDash([3, 5]); else ctx.setLineDash([])
  ctx.beginPath(); ctx.moveTo(start.x, start.y); ctx.lineTo(end.x, end.y); ctx.stroke()
  ctx.setLineDash([])

  ctx.fillStyle = c
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
    if (a && b) drawOneArrow(a, b, false)
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
    if (a && b) drawOneArrow(a, b, false)
  })
  textPairs.forEach(p => {
    const a = getWordRect(p.from), b = getWordRect(p.to)
    if (a && b) drawOneArrow(a, b, false)
  })
}

function drawFusionArrows() {
  drawLayerArrows()
  const entityIds = new Set(vnodeDefs.filter(d => d.type === 'entity').map(d => d.id))
  crossPairs.forEach(pair => {
    if (!entityIds.has(pair.v)) return  // only nouns get bidirectional alignment arrows
    const vr = getVNodeRect(pair.v), tr = getWordRect(pair.t)
    if (!vr || !tr) return
    drawBidirectionalArrow(vr, tr, '#58a6ff')
  })
}

function drawMergedArrows() {
  resizeCanvas()
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  ;[
    { from: 'v-person1', to: 'v-touch' },
    { from: 'v-touch',   to: 'v-bottle' },
    { from: 'v-bottle',  to: 'v-contain' },
    { from: 'v-contain', to: 'v-water' },
    { from: 'v-person1', to: 'v-drink' },
    { from: 'v-drink',   to: 'v-water' },
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
  const dots = stageIndicator.value?.querySelectorAll('.mfs-stage-dot')
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

  const vMeasured = {}
  vnodeDefs.forEach(def => {
    const el = vnodeEls[def.id]
    el.classList.remove('hidden')
    el.style.opacity = '1'
    vMeasured[def.id] = el.offsetWidth
  })

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
  tokens.forEach(w => {
    wordEls[w.id].classList.add('uniform')
    if (w.type === 'filler') {
      wordEls[w.id].style.opacity = '0'
      wordEls[w.id].style.transform = 'scale(0.7)'
    } else {
      wordEls[w.id].style.opacity = '1'
      wordEls[w.id].style.transform = 'scale(1)'
      wordEls[w.id].classList.remove('default', 'noun', 'verb', 'danger', 'fade-out')
      wordEls[w.id].classList.add(w.type)
    }
  })
  Object.entries(textPosP1).forEach(([id, pos]) => {
    const el = wordEls[id]
    el.style.left = pos.left + 'px'
    el.style.top  = pos.top + 'px'
  })

  // visual: cumulative layout — row1 (5 base nodes), row2 (drink)
  const row1Ids = ['v-person1', 'v-touch', 'v-bottle', 'v-contain', 'v-water']
  const row1W = row1Ids.reduce((s, id) => s + vMeasured[id], 0)
  const row1Gap = Math.max(16, Math.round((CTN_W - row1W) / (row1Ids.length - 1)))
  const row1StartX = Math.round((CTN_W - (row1W + row1Gap * (row1Ids.length - 1))) / 2)
  const row1Y = 14
  let r1cx = row1StartX
  row1Ids.forEach(id => {
    vnodeEls[id].style.left = r1cx + 'px'
    vnodeEls[id].style.top = row1Y + 'px'
    r1cx += vMeasured[id] + row1Gap
  })
  // drink centered on row 2
  const drinkY = 56
  vnodeEls['v-drink'].style.left = Math.round((CTN_W - vMeasured['v-drink']) / 2) + 'px'
  vnodeEls['v-drink'].style.top = drinkY + 'px'

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

  const startT = {}
  ;['bottle', 'using', 'woman', 'drinks', 'water'].forEach(id => {
    startT[id] = { left: parseFloat(wordEls[id].style.left) || 0, top: parseFloat(wordEls[id].style.top) || 0 }
  })

  const textWomanX = targetT['woman'].left + wWidth('woman') / 2
  const textBottleX = targetT['bottle'].left + wWidth('bottle') / 2
  const textWaterX = targetT['water'].left + wWidth('water') / 2
  const textUsingX = targetT['using'].left + wWidth('using') / 2
  const textDrinksX = targetT['drinks'].left + wWidth('drinks') / 2
  const vMeasured = {}
  vnodeDefs.forEach(def => { vMeasured[def.id] = vnodeEls[def.id].offsetWidth })

  const vY = 80
  const containMidX = (textBottleX + textWaterX) / 2
  const targetV = {}
  // Row: bottle — touch — person1 — drink — water
  targetV['v-bottle']  = { left: Math.round(textBottleX - vMeasured['v-bottle']/2),  top: vY }
  targetV['v-touch']   = { left: Math.round(textUsingX - vMeasured['v-touch']/2),    top: vY }
  targetV['v-person1'] = { left: Math.round(textWomanX - vMeasured['v-person1']/2),  top: vY }
  targetV['v-drink']   = { left: Math.round(textDrinksX - vMeasured['v-drink']/2),   top: vY }
  targetV['v-water']   = { left: Math.round(textWaterX - vMeasured['v-water']/2),    top: vY }
  // contain above, centered between bottle and water
  targetV['v-contain'] = { left: Math.round(containMidX - vMeasured['v-contain']/2), top: 30 }

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

// ── stage 5: vertical pull + node merge ──────────────────────────
function applyStage5Merge() {
  if (stage5PhaseTimer) { clearTimeout(stage5PhaseTimer); stage5PhaseTimer = null }
  stage5Phase = 0
  currentStage.value = 5
  emit('stageChange', 5)

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

  ;['bottle', 'using', 'woman', 'drinks', 'water'].forEach(id => {
    wordEls[id].style.opacity = '1'
    wordEls[id].style.transform = 'scale(1)'
    wordEls[id].classList.add('uniform')
  })

  // Record start positions (keep X, only animate Y)
  const startV = {}
  ;['v-person1', 'v-touch', 'v-bottle', 'v-contain', 'v-drink', 'v-water'].forEach(id => {
    startV[id] = { left: parseFloat(vnodeEls[id].style.left) || 0, top: parseFloat(vnodeEls[id].style.top) || 0 }
  })
  const startT = {}
  ;['bottle', 'using', 'woman', 'drinks', 'water'].forEach(id => {
    startT[id] = { left: parseFloat(wordEls[id].style.left) || 0, top: parseFloat(wordEls[id].style.top) || 0 }
  })

  const mergeTexts = {
    'v-person1': 'person1<br><span class="mfs-sub">(woman)</span>',
    'v-touch':   'touch<br><span class="mfs-sub">(using)</span>',
    'v-drink':   'drink<br><span class="mfs-sub">(drinks)</span>',
  }

  const origHTMLs = {}
  vnodeDefs.forEach(def => {
    origHTMLs[def.id] = vnodeEls[def.id].innerHTML
    if (mergeTexts[def.id]) {
      vnodeEls[def.id].innerHTML = mergeTexts[def.id]
      vnodeEls[def.id].classList.add('merged')
    }
  })
  vnodeDefs.forEach(def => {
    vnodeEls[def.id].innerHTML = origHTMLs[def.id]
    vnodeEls[def.id].classList.remove('merged')
  })

  // Single row + contain above (moves down same distance as row)
  const mainRowY = 120, containY = 70
  const mainRowV = ['v-person1', 'v-touch', 'v-bottle', 'v-drink', 'v-water']
  const mainRowT = ['bottle', 'using', 'woman', 'drinks', 'water']
  const animVIds = [...mainRowV]
  const animTIds = [...mainRowT]
  const allAnimEls = [...mainRowV.map(id => vnodeEls[id]), vnodeEls['v-contain'], ...mainRowT.map(id => wordEls[id])]
  const savedTransitions = allAnimEls.map(el => el.style.transition)
  allAnimEls.forEach(el => el.style.transition = 'none')

  resizeCanvas()
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  visPairs.forEach(p => {
    const a = getVNodeRect(p.from), b = getVNodeRect(p.to)
    if (a && b) drawOneArrow(a, b, false)
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

    mainRowV.forEach(id => {
      vnodeEls[id].style.left = startV[id].left + 'px'
      vnodeEls[id].style.top  = (startV[id].top + (mainRowY - startV[id].top) * e) + 'px'
    })
    // contain stays above
    vnodeEls['v-contain'].style.left = startV['v-contain'].left + 'px'
    vnodeEls['v-contain'].style.top  = (startV['v-contain'].top + (containY - startV['v-contain'].top) * e) + 'px'
    mainRowT.forEach(id => {
      wordEls[id].style.left = startT[id].left + 'px'
      wordEls[id].style.top  = (startT[id].top + (mainRowY - startT[id].top) * e) + 'px'
    })

    ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
    visPairs.forEach(p => {
      const a = getVNodeRect(p.from), b = getVNodeRect(p.to)
      if (a && b) drawOneArrow(a, b, false)
    })
    textPairs.forEach(p => {
      const a = getWordRect(p.from), b = getWordRect(p.to)
      if (a && b) drawOneArrow(a, b, false)
    })

    if (t < 1) { requestAnimationFrame(tick1) }
    else { finishMerge() }
  }

  function finishMerge() {
    mainRowV.forEach(id => {
      vnodeEls[id].style.left = startV[id].left + 'px'
      vnodeEls[id].style.top  = mainRowY + 'px'
    })
    vnodeEls['v-contain'].style.left = startV['v-contain'].left + 'px'
    vnodeEls['v-contain'].style.top  = containY + 'px'
    mainRowT.forEach(id => {
      wordEls[id].style.left = startT[id].left + 'px'
      wordEls[id].style.top  = mainRowY + 'px'
    })

    // Fuse: text fades into visual nodes
    vnodeDefs.forEach(def => {
      if (mergeTexts[def.id]) {
        vnodeEls[def.id].innerHTML = mergeTexts[def.id]
        vnodeEls[def.id].classList.add('merged')
      }
    })
    // bottle and water: same name, keep as is (but mergeText handles them)
    // contain: no text counterpart, stays as contain

    // Fade out all text tokens
    ;['bottle', 'using', 'woman', 'drinks', 'water'].forEach(tId => {
      wordEls[tId].style.opacity = '0'
      wordEls[tId].style.transform = 'scale(0.7)'
    })

    allAnimEls.forEach((el, i) => { el.style.transition = savedTransitions[i] })

    // Redraw merged arrows
    setTimeout(() => {
      ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
      ;[
        { from: 'v-person1', to: 'v-touch' },
        { from: 'v-touch',   to: 'v-bottle' },
        { from: 'v-bottle',  to: 'v-contain' },
        { from: 'v-contain', to: 'v-water' },
        { from: 'v-person1', to: 'v-drink' },
        { from: 'v-drink',   to: 'v-water' },
      ].forEach(p => {
        const a = getAnyRect(p.from), b = getAnyRect(p.to)
        if (a && b) drawOneArrow(a, b, false)
      })
    }, 50)

    updateLabel('跨源节点合并')
  }

  requestAnimationFrame(tick1)

  updateDots(5)
  updateLabel('跨源节点合并 — 上下拉近融合中...')
  updateLegend(true)
}

// ── main stage application ───────────────────────────────────────
function applyStage(stage) {
  if (stage < 5) resetStage5Phase()

  const visible = {}
  tokens.forEach(w => {
    if (w.type === 'filler' && stage >= 2) visible[w.id] = false
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

  if (stage <= 1) {
    tokens.forEach(w => { wordEls[w.id].classList.remove('uniform') })
    const positions = layoutRow(sentenceOrder, 16, 120)
    Object.entries(positions).forEach(([id, pos]) => {
      const el = wordEls[id]
      el.style.left = pos.left + 'px'
      el.style.top  = pos.top + 'px'
    })
    vnodeDefs.forEach(def => {
      vnodeEls[def.id].classList.add('hidden')
      vnodeEls[def.id].style.opacity = '0'
    })
    animateArrows(() => drawTextArrowsLive(stage), 1050)
  } else if (stage === 2) {
    tokens.forEach(w => { wordEls[w.id].classList.add('uniform') })
    const positions = layoutRow(chainTopOrder, 60, 110)
    Object.entries(positions).forEach(([id, pos]) => {
      const el = wordEls[id]
      el.style.left = pos.left + 'px'
      el.style.top  = pos.top + 'px'
    })
    vnodeDefs.forEach(def => {
      vnodeEls[def.id].classList.add('hidden')
      vnodeEls[def.id].style.opacity = '0'
    })
  } else if (stage === 3) {
    // 结构文本场景图 — maintain chain layout, visual nodes still hidden
    tokens.forEach(w => { wordEls[w.id].classList.add('uniform') })
    const positions = layoutRow(chainTopOrder, 60, 110)
    Object.entries(positions).forEach(([id, pos]) => {
      const el = wordEls[id]
      el.style.left = pos.left + 'px'
      el.style.top  = pos.top + 'px'
    })
    vnodeDefs.forEach(def => {
      vnodeEls[def.id].classList.add('hidden')
      vnodeEls[def.id].style.opacity = '0'
    })
    animateArrows(() => drawTextArrowsLive(3), 800)
  } else if (stage === 4) {
    applyStage4TwoPhase()
    currentStage.value = 4
    emit('stageChange', 4)
    return
  } else {
    applyStage5Merge()
    return
  }

  tokens.forEach(w => {
    const el = wordEls[w.id]
    el.classList.remove('default', 'noun', 'verb', 'danger', 'fade-out')
    if (!visible[w.id]) {
      el.classList.add('fade-out')
    } else if (stage >= 1) {
      el.classList.add(w.type)
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
      const mergeTexts = {
        'v-person1': 'person1<br><span class="mfs-sub">(woman)</span>',
        'v-touch':   'touch<br><span class="mfs-sub">(using)</span>',
        'v-drink':   'drink<br><span class="mfs-sub">(drinks)</span>',
      }
      vnodeDefs.forEach(def => {
        if (mergeTexts[def.id]) {
          vnodeEls[def.id].innerHTML = mergeTexts[def.id]
          vnodeEls[def.id].classList.add('merged')
        }
      })
      ;['bottle', 'using', 'woman', 'drinks', 'water'].forEach(id => {
        wordEls[id].style.opacity = '0'
        wordEls[id].style.transform = 'scale(0.7)'
      })
      drawMergedArrows()
    } else if (stage5Phase === 1) {
      const textPosP1 = layoutRow(chainTopOrder, 60, 110)
      Object.entries(textPosP1).forEach(([id, pos]) => {
        wordEls[id].style.left = pos.left + 'px'
        wordEls[id].style.top  = pos.top + 'px'
      })
      const vMeasured = {}
      vnodeDefs.forEach(def => { vMeasured[def.id] = vnodeEls[def.id].offsetWidth })
      // visual: cumulative layout — row1 (5 base nodes), row2 (drink)
      const row1Ids = ['v-person1', 'v-touch', 'v-bottle', 'v-contain', 'v-water']
      const row1W = row1Ids.reduce((s, id) => s + vMeasured[id], 0)
      const row1Gap = Math.max(16, Math.round((CTN_W - row1W) / (row1Ids.length - 1)))
      const row1StartX = Math.round((CTN_W - (row1W + row1Gap * (row1Ids.length - 1))) / 2)
      const row1Y = 14
      let r1cx = row1StartX
      row1Ids.forEach(id => {
        vnodeEls[id].style.left = r1cx + 'px'
        vnodeEls[id].style.top = row1Y + 'px'
        r1cx += vMeasured[id] + row1Gap
      })
      vnodeEls['v-drink'].style.left = Math.round((CTN_W - vMeasured['v-drink']) / 2) + 'px'
      vnodeEls['v-drink'].style.top = '56px'
      drawVisualAndTextArrows()
    } else {
      const positions = layoutRow(chainTopOrder, 45, 180)
      Object.entries(positions).forEach(([id, pos]) => {
        wordEls[id].style.left = pos.left + 'px'
        wordEls[id].style.top  = pos.top + 'px'
      })
      const textWomanX = positions['woman'].left + wWidth('woman') / 2
      const textBottleX = positions['bottle'].left + wWidth('bottle') / 2
      const textWaterX = positions['water'].left + wWidth('water') / 2
      const textUsingX = positions['using'].left + wWidth('using') / 2
      const textDrinksX = positions['drinks'].left + wWidth('drinks') / 2
      const vMeasured = {}
      vnodeDefs.forEach(def => { vMeasured[def.id] = vnodeEls[def.id].offsetWidth })
      const containMidX = (textBottleX + textWaterX) / 2
      const vY = 80
      const vPositions = {
        'v-bottle':  { left: Math.round(textBottleX - vMeasured['v-bottle']/2),  top: vY },
        'v-touch':   { left: Math.round(textUsingX - vMeasured['v-touch']/2),    top: vY },
        'v-person1': { left: Math.round(textWomanX - vMeasured['v-person1']/2),  top: vY },
        'v-drink':   { left: Math.round(textDrinksX - vMeasured['v-drink']/2),   top: vY },
        'v-water':   { left: Math.round(textWaterX - vMeasured['v-water']/2),    top: vY },
        'v-contain': { left: Math.round(containMidX - vMeasured['v-contain']/2), top: 30 },
      }
      Object.entries(vPositions).forEach(([id, pos]) => {
        vnodeEls[id].style.left = pos.left + 'px'
        vnodeEls[id].style.top = pos.top + 'px'
      })
      drawFusionArrows()
    }
  } else {
    drawTextArrows(currentStage.value)
  }
  const video = maskedVideoRef.value
  if (video) {
    const frame = Math.min(TOTAL_FRAMES, Math.floor(video.currentTime * FPS) + 1)
    const cur = getCurrentGraph(frame)
    renderCurrentGraph(cur.nodes, cur.arrows)
  }
  if (cumulativePhase === 0) {
    initCumulativeBasic()
  } else {
    const container = cumulativeStageRef.value
    const rect = container.getBoundingClientRect()
    // Row 1: 5 base nodes
    const row1Ids = ['person1', 'touch', 'bottle', 'contain', 'water']
    const row1Labels = ['person1', 'touch', 'bottle', 'contain', 'water']
    const row1Types = ['entity', 'action', 'entity', 'action', 'entity']
    const row1Measured = row1Ids.map((id, i) => ({ id, ...measureCumNode(row1Labels[i], row1Types[i]) }))
    const row1W = row1Measured.reduce((s, m) => s + m.w, 0)
    let gap1 = Math.round((rect.width - row1W) / (row1Ids.length - 1))
    if (gap1 < 18) gap1 = 18
    cumNodes = {}
    const startX1 = Math.max(4, Math.round((rect.width - (row1W + gap1 * (row1Ids.length - 1))) / 2))
    let cx = startX1
    row1Measured.forEach(m => {
      cumNodes[m.id] = { left: cx, top: 14, width: m.w, height: m.h, label: row1Labels[row1Ids.indexOf(m.id)], type: row1Types[row1Ids.indexOf(m.id)] }
      cx += m.w + gap1
    })
    // Row 2: drink centered
    const drinkM = measureCumNode('drink', 'action')
    const row2Y = 56
    cumNodes['drink'] = { left: Math.max(4, Math.round((rect.width - drinkM.w) / 2)), top: row2Y, width: drinkM.w, height: drinkM.h, label: 'drink', type: 'action' }
    buildCumulativeDOM()
  }
}

// ── lifecycle ────────────────────────────────────────────────────
onMounted(() => {
  const container = containerRef.value
  const canvas = canvasRef.value
  ctx = canvas.getContext('2d')

  tokens.forEach(w => {
    const el = document.createElement('span')
    el.className = 'mfs-word default'
    el.textContent = w.text
    el.id = 'mfs-word-' + w.id
    el.style.opacity = '0'
    el.style.left = '0px'
    el.style.top = '0px'
    container.appendChild(el)
    wordEls[w.id] = el
  })

  vnodeDefs.forEach(def => {
    const el = document.createElement('span')
    el.className = 'mfs-vnode hidden ' + def.type
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

    video.play().catch(() => {})
  }

  nextTick(() => {
    resizeCanvas()
    applyStage(0)
  })

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

defineExpose({ currentStage, nextStage, prevStage, resetAll, toggleAutoPlay })
</script>

<style>
/* ── Safe Fusion Scene — isolated dark theme ───────────────── */
.mfs-root {
  --mfs-bg: #0d1117;
  --mfs-surface: #161b22;
  --mfs-border: #30363d;
  --mfs-text: #c9d1d9;
  --mfs-muted: #8b949e;
  --mfs-accent: #58a6ff;
  --mfs-success: #3fb950;
  --mfs-noun: #ffa657;
  --mfs-verb: #79c0ff;
  --mfs-danger: #ff4a4a;

  background: var(--mfs-bg);
  border-radius: 14px;
  position: relative;
  width: 100%;
  height: 620px;
  font-family: 'PingFang SC', 'SF Pro Display', 'Helvetica Neue', sans-serif;
  color: #e6edf3;
  overflow: hidden;
  user-select: none;
}

/* ── visual row ────────────────────────────────────────────────── */
.mfs-visual-row {
  position: absolute; top: 0; left: 0; right: 0; height: 240px;
  display: flex; gap: 10px; padding: 8px 12px;
  border-bottom: 1px solid #21262d;
}
.mfs-video-col {
  flex: 0 0 270px; display: flex; flex-direction: column; gap: 4px;
}
.mfs-masked-video {
  width: 100%; height: 185px; border-radius: 6px;
  border: 1px solid #30363d; background: #000;
  object-fit: cover;
}
.mfs-frame-badge {
  font-size: 10px; color: #8b949e; text-align: center;
}
.mfs-graphs-col {
  flex: 1; display: flex; flex-direction: column; gap: 4px;
  min-width: 0;
}
.mfs-graph-panel {
  flex: 1; display: flex; flex-direction: column;
}
.mfs-panel-label {
  font-size: 10px; color: #8b949e; text-transform: uppercase;
  letter-spacing: 0.06em; margin-bottom: 2px;
}
.mfs-graph-stage {
  flex: 1; position: relative; background: #161b22;
  border: 1px solid #21262d; border-radius: 6px;
}
.mfs-graph-canvas {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; pointer-events: none; z-index: 0;
}
.mfs-gnode {
  position: absolute;
  display: flex; align-items: center;
  padding: 6px 14px; border-radius: 6px;
  font-size: 15px; font-weight: 600; line-height: 1;
  white-space: nowrap; z-index: 1;
  border: 1.5px solid transparent;
}
.mfs-gnode.entity  { color: #ffa657; background: rgba(255,166,87,0.10); border-color: rgba(255,166,87,0.35); }
.mfs-gnode.action  { color: #79c0ff; background: rgba(121,192,255,0.10); border-color: rgba(121,192,255,0.35); }

/* ── stage indicators ──────────────────────────────────────────── */
.mfs-stage-indicator {
  position: absolute; top: 250px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 8px; z-index: 10;
}
.mfs-stage-dot {
  width: 28px; height: 3px; border-radius: 2px;
  background: #30363d; transition: all 0.5s ease;
}
.mfs-stage-dot.active { background: #58a6ff; box-shadow: 0 0 6px rgba(88,166,255,0.5); }
.mfs-stage-dot.done { background: #3fb950; }

.mfs-stage-label {
  position: absolute; top: 266px; left: 50%; transform: translateX(-50%);
  font-size: 12px; color: #8b949e; letter-spacing: 0.04em;
  transition: all 0.5s ease; z-index: 10;
  white-space: nowrap;
}

.mfs-main-container {
  position: absolute; top: 288px; left: 8px; right: 8px;
  height: 280px;
}

.mfs-main-container canvas {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; z-index: 1;
}

/* ── word elements ─────────────────────────────────────────────── */
.mfs-word {
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
.mfs-word.default  { color: #c9d1d9; background: rgba(48,54,61,0.6); border-color: #30363d; }
.mfs-word.noun     { color: #ffa657; background: rgba(255,166,87,0.12); border-color: rgba(255,166,87,0.4); }
.mfs-word.verb     { color: #79c0ff; background: rgba(121,192,255,0.12); border-color: rgba(121,192,255,0.4); }
.mfs-word.fade-out { opacity: 0; transform: scale(0.7); pointer-events: none; }
.mfs-word.uniform  { min-width: 70px; padding: 5px 12px; font-size: 14px; }

/* ── visual node elements ──────────────────────────────────────── */
.mfs-vnode {
  position: absolute;
  padding: 5px 12px; border-radius: 6px;
  font-size: 14px; font-weight: 600;
  white-space: nowrap;
  transition: left 0.7s ease, top 0.7s ease, opacity 0.4s ease;
  border: 1.5px solid transparent;
  z-index: 2; text-align: center;
  min-width: 70px;
}
.mfs-vnode.entity  { color: #ffa657; background: rgba(255,166,87,0.10); border-color: rgba(255,166,87,0.35); }
.mfs-vnode.action  { color: #79c0ff; background: rgba(121,192,255,0.10); border-color: rgba(121,192,255,0.35); }
.mfs-vnode.hidden  { opacity: 0; transform: scale(0.7); pointer-events: none; }
.mfs-vnode.merged  { white-space: normal; line-height: 1.2; font-size: 13px; padding: 5px 10px; }
.mfs-sub           { display: block; font-size: 0.72em; opacity: 0.7; font-weight: 400; }

/* ── legend ────────────────────────────────────────────────────── */
.mfs-legend {
  position: absolute; bottom: 42px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 18px; font-size: 11px; color: #8b949e;
  opacity: 0; transition: opacity 0.6s ease; z-index: 10;
}
.mfs-legend.visible { opacity: 1; }
.mfs-legend-item { display: flex; align-items: center; gap: 5px; }
.mfs-legend-dot { width: 8px; height: 8px; border-radius: 2px; }
.mfs-legend-dot.noun   { background: #ffa657; }
.mfs-legend-dot.verb   { background: #79c0ff; }

/* ── controls ──────────────────────────────────────────────────── */
.mfs-controls {
  position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 12px; z-index: 10;
}
.mfs-ctrl-btn {
  padding: 6px 18px; border-radius: 6px; border: 1px solid #30363d;
  background: #161b22; color: #c9d1d9;
  font-size: 13px; cursor: pointer; white-space: nowrap;
  transition: all 0.2s ease;
}
.mfs-ctrl-btn:hover { border-color: #58a6ff; color: #e6edf3; background: #1c2333; }
.mfs-ctrl-btn:disabled { opacity: 0.35; cursor: default; }
.mfs-ctrl-btn.play { border-color: #3fb950; color: #3fb950; }
.mfs-ctrl-btn.playing { border-color: #d79a45; color: #d79a45; }
</style>
