<template>
  <canvas ref="canvasRef" class="neural-bg"></canvas>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const canvasRef = ref(null)

const NODE_COUNT = 3500
const CONNECTION_DIST = 160
const ROTATE_SPEED = 0.00025

let animId = null
let nodes = []
let connections = []
let angleY = 0
let w = 0, h = 0

function createNodes() {
  nodes = []
  // Sphere radius: big enough to fill viewport when projected
  const radius = Math.max(w, h) * 0.85
  for (let i = 0; i < NODE_COUNT; i++) {
    // Uniform volumetric distribution in a sphere (cbrt for uniform density)
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    const r = radius * Math.cbrt(Math.random())
    nodes.push({
      x: Math.cos(theta) * Math.sin(phi) * r,
      y: Math.sin(theta) * Math.sin(phi) * r,
      z: Math.cos(phi) * r,
      baseR: 0.6 + Math.random() * 1.6,
      pulse: Math.random() * Math.PI * 2,
      pulseSpeed: 0.006 + Math.random() * 0.028,
    })
  }
}

function buildConnections() {
  connections = []
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x
      const dy = nodes[i].y - nodes[j].y
      const dz = nodes[i].z - nodes[j].z
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz)
      if (dist < CONNECTION_DIST) {
        connections.push({ a: i, b: j, dist })
      }
    }
  }
}

function rotateY(x, z, angle) {
  return {
    x: x * Math.cos(angle) - z * Math.sin(angle),
    z: x * Math.sin(angle) + z * Math.cos(angle),
  }
}

function draw(ctx) {
  ctx.clearRect(0, 0, w, h)

  const cx = w / 2
  const cy = h / 2
  const projected = nodes.map(n => {
    const rot = rotateY(n.x, n.z, angleY)
    return {
      sx: cx + rot.x,
      sy: cy + n.y,
      depth: rot.z,
    }
  })

  // Draw connections
  for (const c of connections) {
    const pa = projected[c.a]
    const pb = projected[c.b]
    const avgDepth = (pa.depth + pb.depth) / 2
    const depthNorm = Math.max(0, Math.min(1, (avgDepth + 1800) / 3600))
    const alpha = 0.06 + depthNorm * 0.16
    ctx.beginPath()
    ctx.moveTo(pa.sx, pa.sy)
    ctx.lineTo(pb.sx, pb.sy)
    ctx.strokeStyle = `rgba(59,130,246,${alpha.toFixed(3)})`
    ctx.lineWidth = 0.25 + depthNorm * 0.4
    ctx.stroke()
  }

  // Draw nodes
  for (let i = 0; i < nodes.length; i++) {
    const p = projected[i]
    const n = nodes[i]
    const depthNorm = Math.max(0, Math.min(1, (p.depth + 1800) / 3600))
    const pulse = Math.sin(n.pulse) * 0.35 + 0.65
    const r = n.baseR * pulse * (0.6 + depthNorm * 0.6)
    const alpha = 0.15 + depthNorm * 0.55

    // Glow
    const glow = ctx.createRadialGradient(p.sx, p.sy, 0, p.sx, p.sy, r * 4)
    glow.addColorStop(0, `rgba(59,130,246,${(alpha * 0.6).toFixed(3)})`)
    glow.addColorStop(0.4, `rgba(6,182,212,${(alpha * 0.2).toFixed(3)})`)
    glow.addColorStop(1, 'rgba(6,182,212,0)')
    ctx.beginPath()
    ctx.arc(p.sx, p.sy, r * 4, 0, Math.PI * 2)
    ctx.fillStyle = glow
    ctx.fill()

    // Core
    ctx.beginPath()
    ctx.arc(p.sx, p.sy, r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(96,165,250,${(alpha * 0.75).toFixed(3)})`
    ctx.fill()
  }
}

function resize() {
  const canvas = canvasRef.value
  if (!canvas) return
  w = window.innerWidth
  h = window.innerHeight
  canvas.width = w
  canvas.height = h
  createNodes()
  buildConnections()
}

function animate() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  angleY += ROTATE_SPEED
  for (const n of nodes) {
    n.pulse += n.pulseSpeed
  }
  draw(ctx)
  animId = requestAnimationFrame(animate)
}

onMounted(() => {
  resize()
  animate()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animId)
  window.removeEventListener('resize', resize)
})
</script>

<style scoped>
.neural-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: #060b1a;
}
</style>
