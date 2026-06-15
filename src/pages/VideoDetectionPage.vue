<template>
  <section class="page-section detection-workstation">
    <div class="workstation-main-row">
      <aside class="sample-panel compact-panel upload-column">
        <div class="panel-title">
          <span class="kicker">Input</span>
          <h2>上传视频</h2>
        </div>

        <label class="upload-dropzone upload-video-dropzone" :class="{ ready: uploadedFileName }">
          <input type="file" accept="video/*" @change="handleUpload" />
          <video v-if="previewVideo" class="upload-preview-video" :src="previewVideo" controls muted playsinline />
          <span v-else>选择演示视频</span>
          <small>{{ uploadedFileName ? '点击重新上传' : '支持 safe / harmful / metaphor 三类演示视频；分析结果为预生成报告。' }}</small>
        </label>

        <div class="caption-box" v-if="uploadedFileName">
          <div class="caption-box-header">
            <div>
              <span class="kicker">Caption</span>
              <h2>字幕文案</h2>
            </div>
            <button class="caption-edit-btn" :class="{ editing: isEditingCaption }"
                    @click="toggleCaptionEdit">
              {{ isEditingCaption ? '完成' : '编辑' }}
            </button>
          </div>
          <textarea v-if="isEditingCaption" class="caption-textarea" v-model="captionText"
                    rows="3" placeholder="输入或修改字幕文案…"></textarea>
          <p v-else class="caption-preview">{{ captionText }}</p>
        </div>

        <button class="primary-btn full-width" @click="runDetection" :disabled="running || !uploadedFileName">
          {{ running ? '模型计算中' : '开始检测' }}
        </button>

        <!-- Detection report summary below upload -->
        <div v-if="showReport" class="upload-summary">
          <span class="kicker">Detection report</span>
          <div class="upload-summary-stack">
            <div class="summary-decision-row">
              <span :class="['result-dot', selected.decision]"></span>
              <strong>{{ selected.decision === 'allowed' ? '允许发布' : '建议拦截' }}</strong>
            </div>
            <div>
              <span>置信度</span>
              <strong>{{ percent(selected.confidence) }}</strong>
            </div>
            <div>
              <span>风险类型</span>
              <strong>{{ selected.riskTypes.join(' / ') }}</strong>
            </div>
          </div>
        </div>
      </aside>

      <section class="video-stage compact-video-card preview-column">
        <div class="stage-header compact-card-header">
          <div>
            <span class="kicker">Cross-Source Scene Graph</span>
            <h2>跨源场景图</h2>
          </div>
          <span v-if="showReport" :class="['status-pill', selected.decision]">{{ selected.decision === 'allowed' ? 'Allowed' : 'Blocked' }}</span>
          <span v-else-if="running && detectionPhase === 'text_ready'" class="status-pill pending">Building</span>
          <span v-else-if="running" class="status-pill pending">Processing</span>
          <span v-else class="status-pill pending">Pending</span>
        </div>

        <!-- Empty: no video uploaded -->
        <div v-if="!uploadedFileName && !running" class="fusion-placeholder">
          <span>Empty</span>
          <h2>尚未上传视频</h2>
          <p>请先在上方上传一个演示视频。</p>
        </div>

        <!-- Ready: uploaded but not started -->
        <div v-else-if="!running && !showReport" class="fusion-placeholder">
          <span>Ready</span>
          <h2>等待开始检测</h2>
          <p>点击"开始检测"后，右侧将展示跨源场景图。</p>
        </div>

        <!-- Scene building phase: 3-panel visual loading + text area loading -->
        <div v-else-if="running && detectionPhase === 'scene_building'" class="scene-building-view">
          <div class="sb-visual-row">
            <div class="sb-video-col">
              <div class="sb-video-placeholder">
                <span class="sb-dot-pulse"></span>
                <span>视频帧分析中</span>
              </div>
              <span class="sb-frame-badge">对各关键帧进行实体分割与跨帧追踪...</span>
            </div>
            <div class="sb-graphs-col">
              <div class="sb-graph-panel">
                <span class="sb-panel-label">当前帧场景图</span>
                <div class="sb-graph-stage sb-graph-waiting">
                  <span class="sb-dot-pulse"></span>
                  <span>视觉场景图分析中</span>
                </div>
              </div>
              <div class="sb-graph-panel">
                <span class="sb-panel-label">累计场景图</span>
                <div class="sb-graph-stage sb-graph-waiting">
                  <span class="sb-dot-pulse"></span>
                  <span>视觉场景图分析中</span>
                </div>
              </div>
            </div>
          </div>
          <div class="sb-stage-indicator">
            <div v-for="i in 4" :key="i" class="sb-stage-dot"></div>
          </div>
          <div class="sb-stage-label">视觉场景图构建中 — 文本场景图构建中</div>
          <div class="sb-main-container">
            <div class="sb-text-loading">
              <span class="sb-dot-pulse"></span>
              <span>文本场景图分析中</span>
            </div>
          </div>
          <div class="sb-legend">
            <span class="sb-legend-item"><span class="sb-legend-dot noun"></span> 名词</span>
            <span class="sb-legend-item"><span class="sb-legend-dot verb"></span> 动词</span>
          </div>
          <div class="sb-bottom-bar">
            <span class="sb-dot-pulse"></span>
            <span>视觉通道处理中 — 文本通道处理中</span>
          </div>
        </div>

        <!-- Text ready onward: show FusionScene with loading overlay on visual row -->
        <div v-else-if="(pendingCase || selected)?.id === 'literal-risk'" class="fusion-scene-wrapper">
          <FusionScene
            :ref="(el) => fusionRef = el"
            :sentence="(selected || pendingCase)?.subtitle || ''"
            class="fusion-scene-widget"
          />
          <div v-if="!sceneGraphsReady" class="visual-loading-overlay">
            <div class="vlo-video-col">
              <div class="vlo-video-placeholder">
                <span class="sb-dot-pulse"></span>
                <span>视频帧分析中</span>
              </div>
              <span class="vlo-frame-badge">对各关键帧进行实体分割与跨帧追踪...</span>
            </div>
            <div class="vlo-graphs-col">
              <div class="vlo-graph-panel">
                <span class="vlo-panel-label">当前帧场景图</span>
                <div class="vlo-graph-stage">
                  <span class="sb-dot-pulse"></span>
                  <span>视觉场景图分析中</span>
                </div>
              </div>
              <div class="vlo-graph-panel">
                <span class="vlo-panel-label">累计场景图</span>
                <div class="vlo-graph-stage">
                  <span class="sb-dot-pulse"></span>
                  <span>视觉场景图分析中</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="(pendingCase || selected)?.id === 'metaphor-risk'" class="fusion-scene-wrapper">
          <MetaphorFusionScene
            :ref="(el) => fusionRef = el"
            :sentence="(selected || pendingCase)?.subtitle || ''"
            class="fusion-scene-widget"
          />
          <div v-if="!sceneGraphsReady" class="visual-loading-overlay">
            <div class="vlo-video-col">
              <div class="vlo-video-placeholder">
                <span class="sb-dot-pulse"></span>
                <span>视频帧分析中</span>
              </div>
              <span class="vlo-frame-badge">对各关键帧进行实体分割与跨帧追踪...</span>
            </div>
            <div class="vlo-graphs-col">
              <div class="vlo-graph-panel">
                <span class="vlo-panel-label">当前帧场景图</span>
                <div class="vlo-graph-stage">
                  <span class="sb-dot-pulse"></span>
                  <span>视觉场景图分析中</span>
                </div>
              </div>
              <div class="vlo-graph-panel">
                <span class="vlo-panel-label">累计场景图</span>
                <div class="vlo-graph-stage">
                  <span class="sb-dot-pulse"></span>
                  <span>视觉场景图分析中</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="fusion-scene-wrapper">
          <SafeFusionScene
            :ref="(el) => fusionRef = el"
            :sentence="(selected || pendingCase)?.subtitle || ''"
            class="fusion-scene-widget"
          />
          <div v-if="!sceneGraphsReady" class="visual-loading-overlay">
            <div class="vlo-video-col">
              <div class="vlo-video-placeholder">
                <span class="sb-dot-pulse"></span>
                <span>视频帧分析中</span>
              </div>
              <span class="vlo-frame-badge">对各关键帧进行实体分割与跨帧追踪...</span>
            </div>
            <div class="vlo-graphs-col">
              <div class="vlo-graph-panel">
                <span class="vlo-panel-label">当前帧场景图</span>
                <div class="vlo-graph-stage">
                  <span class="sb-dot-pulse"></span>
                  <span>视觉场景图分析中</span>
                </div>
              </div>
              <div class="vlo-graph-panel">
                <span class="vlo-panel-label">累计场景图</span>
                <div class="vlo-graph-stage">
                  <span class="sb-dot-pulse"></span>
                  <span>视觉场景图分析中</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section class="decision-panel report-dock">
      <template v-if="showReport">
        <div class="report-content-grid report-content-grid-two">
          <article class="report-block signal-block">
            <span class="kicker">Signals</span>
            <h3>多模态信号解释</h3>
            <dl class="signal-list report-signal-list">
              <div>
                <dt>视频</dt>
                <dd>{{ selected.visualSignal }}</dd>
              </div>
              <div>
                <dt>字幕</dt>
                <dd>{{ selected.textSignal }}</dd>
              </div>
              <div>
                <dt>组合</dt>
                <dd>{{ selected.fusionSignal }}</dd>
              </div>
            </dl>
          </article>

          <article class="report-block final-report action-block">
            <span class="kicker">Explanation</span>
            <h3>解释与处置建议</h3>
            <p>{{ selected.explanation }}</p>
            <p><strong>处置建议：</strong>{{ selected.recommendation }}</p>
          </article>
        </div>
      </template>

      <div v-else-if="running" class="report-placeholder report-dock-placeholder detection-progress">
        <span class="dp-phase-badge">{{ currentPhaseBadge }}</span>
        <h2>{{ currentPhaseTitle }}</h2>
        <p>{{ currentPhaseDesc }}</p>
        <!-- Timeline: only show from cross_source onwards -->
        <div v-if="timelineSteps.some(s => s.active || s.done)" class="dp-timeline">
          <div class="dp-step" v-for="step in timelineSteps" :key="step.phase"
               :class="{ done: step.done, active: step.active }">
            <span class="dp-step-dot"></span>
            <span class="dp-step-label">{{ step.label }}</span>
          </div>
        </div>
      </div>

      <div v-else class="report-placeholder report-dock-placeholder">
        <span>{{ uploadedFileName ? 'Ready' : 'Empty' }}</span>
        <h2>{{ uploadedFileName ? '等待开始检测' : '尚未上传视频' }}</h2>
        <p>{{ uploadedFileName ? '点击"开始检测"后，下方将展示风险结论、信号解释、关系链路和处置建议。' : '请先在上方上传一个演示视频。' }}</p>
      </div>
    </section>
  </section>

</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import metaphorRelationImage from '../../demo_video/metaphor_keyframe.jpg'
import safeKeyframeImage from '../../demo_video/safe_keyframe.jpg'
import harmfulKeyframe1 from '../../demo_video/harmful_keyframe_1.jpg'
import harmfulKeyframe2 from '../../demo_video/harmful_keyframe_2.jpg'
import FusionScene from '../components/FusionScene.vue'
import MetaphorFusionScene from '../components/MetaphorFusionScene.vue'
import SafeFusionScene from '../components/SafeFusionScene.vue'
import { demoCases, detectionSteps } from '../data/demoCases'

const selected = ref(null)
const pendingCase = ref(null)
const uploadedFileName = ref('')
const uploadedVideoUrl = ref('')
const running = ref(false)
const hasReport = ref(false)
const progress = ref(0)
const captionText = ref('')
const isEditingCaption = ref(false)
let timer = null

// ── Multi-phase detection state ────────────────────────────────────
const detectionPhase = ref('idle')
// 'idle' | 'scene_building' | 'text_ready' | 'cross_source' |
// 'inference' | 'verdict' | 'archiving' | 'feedback' | 'complete'
const sceneGraphsReady = ref(false)
let phaseTimers = []
let fusionRef = null
let fusionStageTimer = null

function stopFusionAdvance() {
  if (fusionStageTimer) {
    clearTimeout(fusionStageTimer)
    fusionStageTimer = null
  }
}

function advanceFusionTo(targetStage, delayPerStep = 1200) {
  stopFusionAdvance()
  const step = () => {
    if (!fusionRef || !running.value) return
    if (fusionRef.currentStage >= targetStage) {
      fusionStageTimer = null
      return
    }
    fusionRef.nextStage()
    fusionStageTimer = setTimeout(step, delayPerStep)
  }
  fusionStageTimer = setTimeout(step, 400)
}

// Watch: text scene graph auto-plays stages 0→3 when component mounts
watch(() => detectionPhase.value, (phase) => {
  if (phase === 'text_ready') {
    nextTick(() => advanceFusionTo(3, 1200))
  }
})


// ── Bottom panel phase display ─────────────────────────────────────
const phaseInfoMap = {
  scene_building: { badge: '准备中', title: '正在构建多源场景图', desc: '视觉通道正在对各关键帧进行实体分割、跨帧追踪与交互关系提取；文本通道正在对关联文本进行句法解析与语义三元组抽取。' },
  text_ready:    { badge: '准备中', title: '正在构建多源场景图', desc: '文本场景图已构建完成，正在等待视觉通道完成实体追踪与场景图生成。' },
  cross_source:  { badge: '准备中', title: '正在进行跨源图对齐与融合', desc: '将视觉对象查询与文本实体嵌入映射到共享语义空间，执行双向特征投影与图补全，合并为统一场景图。' },
  inference:     { badge: 'Phase 1/4', title: '正在进行图级意图推理', desc: '通过多轮消息传递聚合邻居节点与关系边信息，捕捉视频中的持续行为与动态变化，推断内容意图。' },
  verdict:       { badge: 'Phase 2/4', title: '正在进行违规判定', desc: '基于融合场景图的语义表示，经池化与分类器处理，判定内容是否违规及具体违规类别。' },
  archiving:     { badge: 'Phase 3/4', title: '正在进行结果分类归档与管理', desc: '根据判定结果将内容存入安全记录库或高风险模式库，形成按违规类别索引的高危场景图语义组合记录。' },
  feedback:      { badge: 'Phase 4/4', title: '正在进行结果反馈与可解释性展示', desc: '汇总检测结果与推理路径，生成基于跨源意图检测的可解释性报告与处置建议。' },
  complete:      { badge: 'Done', title: '检测完成', desc: '' },
  idle:          { badge: '', title: '', desc: '' },
}

const timelineSteps = computed(() => {
  const order = ['inference', 'verdict', 'archiving', 'feedback']
  const labels = {
    inference: '图级意图推理',
    verdict: '违规判定',
    archiving: '分类归档',
    feedback: '结果反馈',
  }
  const currentIdx = order.indexOf(detectionPhase.value)

  return order.map((p, i) => ({
    phase: p,
    label: labels[p],
    done: detectionPhase.value === 'complete' || (currentIdx >= 0 && currentIdx > i),
    active: currentIdx === i,
  }))
})

const currentPhaseBadge = computed(() => phaseInfoMap[detectionPhase.value]?.badge || '')
const currentPhaseTitle = computed(() => phaseInfoMap[detectionPhase.value]?.title || '')
const currentPhaseDesc = computed(() => phaseInfoMap[detectionPhase.value]?.desc || '')

function toggleCaptionEdit() {
  isEditingCaption.value = !isEditingCaption.value
}

const relationImageMap = {
  'safe-video': [
    { src: safeKeyframeImage, alt: '合规样本关键帧分析图' }
  ],
  'literal-risk': [
    { src: harmfulKeyframe1, alt: '显性违规关键帧分析图 1' },
    { src: harmfulKeyframe2, alt: '显性违规关键帧分析图 2' }
  ],
  'metaphor-risk': [
    { src: metaphorRelationImage, alt: '隐喻风险跨源关系分析图' }
  ]
}

const previewVideo = computed(() => uploadedVideoUrl.value || '')
const showReport = computed(() => Boolean(selected.value && hasReport.value && !running.value))
const subtitleText = computed(() => selected.value?.subtitle || pendingCase.value?.subtitle || '上传视频后自动匹配字幕文案。')
const levelText = computed(() => ({ low: '低', medium: '中', high: '高' }[selected.value?.riskLevel] || selected.value?.riskLevel || '-') )
const activeRelationImages = computed(() => relationImageMap[(selected.value || pendingCase.value)?.id] || [])

function percent(value) {
  return `${(value * 100).toFixed(2)}%`
}

function pickCaseByFileName(name) {
  const normalized = name.toLowerCase()
  if (normalized.includes('harmful') || normalized.includes('rob') || normalized.includes('gun')) {
    return demoCases.find((item) => item.id === 'literal-risk') || demoCases[1]
  }
  if (normalized.includes('metaphor') || normalized.includes('door') || normalized.includes('e40ccb6')) {
    return demoCases.find((item) => item.id === 'metaphor-risk') || demoCases[2]
  }
  return demoCases.find((item) => item.id === 'safe-video') || demoCases[0]
}

function handleUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (uploadedVideoUrl.value) URL.revokeObjectURL(uploadedVideoUrl.value)
  uploadedFileName.value = file.name
  uploadedVideoUrl.value = URL.createObjectURL(file)
  pendingCase.value = pickCaseByFileName(file.name)
  captionText.value = pendingCase.value?.subtitle || ''
  isEditingCaption.value = false
  selected.value = null
  hasReport.value = false
  running.value = false
  progress.value = 0
  detectionPhase.value = 'idle'
  sceneGraphsReady.value = false
  if (timer) clearTimeout(timer)
  phaseTimers.forEach(t => clearTimeout(t))
  phaseTimers = []
}

function runDetection() {
  if (!pendingCase.value) return
  running.value = true
  hasReport.value = false
  selected.value = null
  sceneGraphsReady.value = false
  detectionPhase.value = 'scene_building'
  progress.value = 0
  if (timer) clearTimeout(timer)
  stopFusionAdvance()
  phaseTimers.forEach(t => clearTimeout(t))
  phaseTimers = []

  // Phase schedule — absolute ms from detection start
  const addPhase = (phase, ms) => {
    const t = setTimeout(() => {
      if (!running.value) return
      detectionPhase.value = phase
      if (phase === 'cross_source') {
        sceneGraphsReady.value = true
        if (fusionRef) {
          stopFusionAdvance()
          while (fusionRef.currentStage < 3) fusionRef.nextStage()
          advanceFusionTo(5, 3000)
        }
      }
      if (phase === 'complete') {
        selected.value = pendingCase.value
        running.value = false
        hasReport.value = true
        progress.value = detectionSteps.length
      }
    }, ms)
    phaseTimers.push(t)
  }

  addPhase('text_ready', 2500)
  addPhase('cross_source', 10000)
  addPhase('inference', 13000)
  addPhase('verdict', 15000)
  addPhase('archiving', 17000)
  addPhase('feedback', 18500)
  addPhase('complete', 20000)
}

onBeforeUnmount(() => {
  if (uploadedVideoUrl.value) URL.revokeObjectURL(uploadedVideoUrl.value)
  if (timer) clearTimeout(timer)
  stopFusionAdvance()
  phaseTimers.forEach(t => clearTimeout(t))
})
</script>

<style scoped>
/* Override grid: narrower upload column, taller row */
.workstation-main-row {
  grid-template-columns: 250px minmax(620px, 1fr) !important;
  min-height: calc(100vh - 200px) !important;
}

/* Shrink upload dropzone */
.upload-video-dropzone {
  min-height: 160px !important;
}
.upload-video-dropzone span {
  font-size: 18px !important;
}
.upload-preview-video {
  max-height: 140px !important;
}

/* Detection report summary inside upload column */
.upload-summary {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(247,242,232,.72);
}
.upload-summary .kicker {
  display: block;
  margin-bottom: 8px;
}
.upload-summary-stack {
  display: grid;
  gap: 6px;
}
.upload-summary-stack > div {
  padding: 6px 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(251,247,239,.72);
}
.upload-summary-stack span:not(.result-dot) {
  display: block;
  color: var(--muted);
  font-size: 11px;
  margin-bottom: 2px;
}
.upload-summary-stack strong {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
}
.summary-decision-row {
  position: relative;
  padding-left: 28px !important;
}
.summary-decision-row .result-dot {
  position: absolute;
  left: 8px;
  top: 50%;
  margin-top: -6px;
}

/* 2-column report grid */
.report-content-grid-two {
  grid-template-columns: 1fr 1fr !important;
}
.report-content-grid-two .report-block {
  height: auto;
  min-height: 200px;
}

/* Constrain workstation row: right column dictates height, left follows */
.workstation-main-row {
  min-height: 0 !important;
}
.upload-column, .preview-column {
  height: auto !important;
}

/* Fusion placeholder before detection */
.fusion-placeholder {
  flex: 1; display: flex; flex-direction: column; justify-content: center;
  align-items: center; text-align: center; padding: 28px;
  border: 1px dashed var(--line-strong); border-radius: 18px;
  background: #f1e8dc; color: var(--muted); margin-top: 4px;
}
.fusion-placeholder h2 { margin: 8px 0 4px; font-size: 18px; color: var(--ink); }
.fusion-placeholder p { font-size: 13px; max-width: 360px; line-height: 1.5; }

/* FusionScene wrapper + loading overlay over visual row */
.fusion-scene-wrapper {
  position: relative;
  flex: 0 0 auto;
  height: 620px;
  margin-top: 4px;
}
.visual-loading-overlay {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 240px;
  background: #0d1117;
  z-index: 20;
  border-radius: 14px 14px 0 0;
  display: flex;
  gap: 10px;
  padding: 8px 12px;
  pointer-events: none;
}
.vlo-video-col {
  flex: 0 0 270px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.vlo-video-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #8b949e;
  font-size: 13px;
}
.vlo-frame-badge {
  font-size: 10px;
  color: #8b949e;
  text-align: center;
}
.vlo-graphs-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.vlo-graph-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.vlo-panel-label {
  font-size: 10px;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 2px;
}
.vlo-graph-stage {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #161b22;
  border: 1px solid #21262d;
  border-radius: 6px;
  color: #8b949e;
  font-size: 13px;
}

/* Compact panel title */
.compact-panel .panel-title h2 {
  font-size: 20px !important;
}
.compact-panel .panel-title {
  margin-bottom: 6px !important;
}
.full-width {
  margin-top: 8px !important;
}

/* Caption / subtitle box */
.caption-box {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(251,247,239,.72);
}
.caption-box-header {
  display: flex; justify-content: space-between; align-items: start;
  margin-bottom: 6px;
}
.caption-box-header h2 {
  font-size: 20px; margin: 4px 0 0;
}
.caption-edit-btn {
  font-size: 11px; padding: 3px 12px; border-radius: 8px;
  border: 1px solid var(--line-strong); background: var(--paper);
  color: var(--ink); cursor: pointer; transition: .15s ease;
}
.caption-edit-btn.editing {
  background: var(--ink); color: var(--paper); border-color: var(--ink);
}
.caption-textarea {
  width: 100%; resize: vertical; min-height: 64px;
  padding: 8px 10px; border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--paper-soft);
  color: var(--ink); font-size: 13px; line-height: 1.5;
  outline: none; font-family: inherit;
}
.caption-preview {
  margin: 0; padding: 6px 0;
  font-size: 13px; line-height: 1.5; color: var(--ink);
  white-space: pre-wrap; word-break: break-word;
}

/* ── Scene building view (matches FusionScene vertical layout) ──── */
.scene-building-view {
  flex: 0 0 auto;
  height: 620px;
  position: relative;
  background: #0d1117;
  border-radius: 14px;
  margin-top: 4px;
  overflow: hidden;
  font-family: 'PingFang SC', 'SF Pro Display', 'Helvetica Neue', sans-serif;
  color: #e6edf3;
  user-select: none;
}

/* ── Visual row (same as mfs-visual-row: top 0, height 240px) ─── */
.sb-visual-row {
  position: absolute; top: 0; left: 0; right: 0; height: 240px;
  display: flex; gap: 10px; padding: 8px 12px;
  border-bottom: 1px solid #21262d;
}
.sb-video-col {
  flex: 0 0 270px; display: flex; flex-direction: column; gap: 4px;
}
.sb-video-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #161b22; border-radius: 6px;
  border: 1px solid #30363d;
  color: #8b949e; font-size: 13px;
}
.sb-frame-badge {
  font-size: 10px; color: #8b949e; text-align: center;
}
.sb-graphs-col {
  flex: 1; display: flex; flex-direction: column; gap: 4px;
  min-width: 0;
}
.sb-graph-panel {
  flex: 1; display: flex; flex-direction: column;
}
.sb-panel-label {
  font-size: 10px; color: #8b949e; text-transform: uppercase;
  letter-spacing: 0.06em; margin-bottom: 2px;
}
.sb-graph-stage {
  flex: 1; position: relative; background: #161b22;
  border: 1px solid #21262d; border-radius: 6px;
}
.sb-graph-waiting {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; font-size: 13px; color: #8b949e;
}

/* ── Stage indicator dots ─ */
.sb-stage-indicator {
  position: absolute; top: 250px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 8px; z-index: 10;
}
.sb-stage-dot {
  width: 28px; height: 3px; border-radius: 2px;
  background: #30363d; transition: all 0.5s ease;
}
.sb-stage-label {
  position: absolute; top: 266px; left: 50%; transform: translateX(-50%);
  font-size: 12px; color: #8b949e; letter-spacing: 0.04em;
  z-index: 10; white-space: nowrap;
}

/* ── Main container ─ */
.sb-main-container {
  position: absolute; top: 288px; left: 8px; right: 8px;
  height: 280px;
}
.sb-text-loading {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; align-items: center; justify-content: center;
  gap: 10px; font-size: 16px; color: #8b949e;
}

/* ── Legend ─ */
.sb-legend {
  position: absolute; bottom: 42px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 18px; font-size: 11px; color: #8b949e;
  z-index: 10;
}
.sb-legend-item { display: flex; align-items: center; gap: 5px; }
.sb-legend-dot { width: 8px; height: 8px; border-radius: 2px; }
.sb-legend-dot.noun { background: #ffa657; }
.sb-legend-dot.verb { background: #79c0ff; }

/* ── Bottom status bar ─ */
.sb-bottom-bar {
  position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: #8b949e;
  z-index: 10; white-space: nowrap;
}

/* Keep the global animated dot and done dot */
.sb-dot-pulse {
  width: 8px; height: 8px; border-radius: 50%;
  background: #58a6ff;
  flex-shrink: 0;
  animation: sb-pulse 1.2s ease-in-out infinite;
}
@keyframes sb-pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}
.sb-dot-done {
  width: 8px; height: 8px; border-radius: 50%;
  background: #3fb950;
  flex-shrink: 0;
}

/* ── Bottom panel detection progress ─────────────────────────────── */
.detection-progress {
  align-items: flex-start !important;
  text-align: left !important;
}
.detection-progress h2 {
  font-size: 18px !important;
  margin: 6px 0 4px !important;
  color: var(--ink) !important;
}
.detection-progress p {
  font-size: 13px !important;
  max-width: 600px !important;
  line-height: 1.6 !important;
}
.dp-phase-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  background: rgba(88,166,255,0.15);
  color: #58a6ff;
  border: 1px solid rgba(88,166,255,0.3);
  margin-bottom: 4px;
}
.dp-timeline {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
  width: 100%;
}
.dp-step {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--muted);
  opacity: 0.5;
  transition: all 0.4s ease;
}
.dp-step.done {
  opacity: 0.85;
  color: var(--ink);
}
.dp-step.active {
  opacity: 1;
  color: var(--ink);
  font-weight: 600;
}
.dp-step-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--muted);
  flex-shrink: 0;
  transition: all 0.4s ease;
}
.dp-step.done .dp-step-dot { background: #3fb950; }
.dp-step.active .dp-step-dot {
  background: #58a6ff;
  box-shadow: 0 0 6px rgba(88,166,255,0.6);
  animation: sb-pulse 1.2s ease-in-out infinite;
}
</style>
