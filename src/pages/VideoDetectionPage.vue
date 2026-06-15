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
          <span v-else class="status-pill pending">Pending</span>
        </div>

        <!-- Before detection: placeholder -->
        <div v-if="!showReport" class="fusion-placeholder">
          <span>{{ running ? 'Analyzing' : uploadedFileName ? 'Ready' : 'Empty' }}</span>
          <h2>{{ running ? '模型正在计算' : uploadedFileName ? '等待开始检测' : '尚未上传视频' }}</h2>
          <p>{{ running ? '系统正在进行多模态模型计算，请稍候。' : uploadedFileName ? '点击"开始检测"后，右侧将展示跨源场景图。' : '请先在上方上传一个演示视频。' }}</p>
        </div>

        <!-- Detection done: show FusionScene animation -->
        <FusionScene
          v-else-if="(pendingCase || selected)?.id === 'literal-risk'"
          :sentence="(selected || pendingCase)?.subtitle || ''"
          class="fusion-scene-widget"
        />

        <MetaphorFusionScene
          v-else-if="(pendingCase || selected)?.id === 'metaphor-risk'"
          :sentence="(selected || pendingCase)?.subtitle || ''"
          class="fusion-scene-widget"
        />

        <SafeFusionScene
          v-else
          :sentence="(selected || pendingCase)?.subtitle || ''"
          class="fusion-scene-widget"
        />
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

      <div v-else class="report-placeholder report-dock-placeholder">
        <span>{{ running ? 'Analyzing' : uploadedFileName ? 'Ready' : 'Empty' }}</span>
        <h2>{{ running ? '模型正在计算' : uploadedFileName ? '等待开始检测' : '尚未上传视频' }}</h2>
        <p>{{ running ? '系统正在进行多模态模型计算，请稍候。' : uploadedFileName ? '点击“开始检测”后，下方将展示风险结论、信号解释、关系链路和处置建议。' : '请先在上方上传一个演示视频。' }}</p>
      </div>
    </section>
  </section>

</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
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
  if (timer) clearTimeout(timer)
}

function runDetection() {
  if (!pendingCase.value) return
  running.value = true
  hasReport.value = false
  selected.value = null
  progress.value = 0
  if (timer) clearTimeout(timer)

  const totalDuration = 9000 + Math.random() * 6000
  const weights = [1, 3, 2, 4, 5]
  const totalWeight = weights.reduce((sum, weight) => sum + weight, 0)
  const stageDurations = weights.map((weight) => totalDuration * weight / totalWeight)

  function advanceStage() {
    const currentStage = progress.value
    if (currentStage >= detectionSteps.length) {
      selected.value = pendingCase.value
      running.value = false
      hasReport.value = true
      progress.value = detectionSteps.length
      timer = null
      return
    }

    timer = setTimeout(() => {
      progress.value += 1
      advanceStage()
    }, stageDurations[currentStage])
  }

  advanceStage()
}

onBeforeUnmount(() => {
  if (uploadedVideoUrl.value) URL.revokeObjectURL(uploadedVideoUrl.value)
  if (timer) clearTimeout(timer)
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

/* Taller FusionScene widget */
.fusion-scene-widget {
  flex: 0 0 auto;
  height: 620px;
  margin-top: 4px;
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
</style>
