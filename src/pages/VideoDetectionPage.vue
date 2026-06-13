<template>
  <section class="page-section workbench-heading compact-heading">
    <div>
      <p class="eyebrow">Multimodal detection workbench</p>
      <h1>上传视频，生成组合风险解释。</h1>
    </div>
  </section>

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
          <small>{{ uploadedFileName || '支持 safe / harmful / metaphor 三类演示视频；分析结果为预生成报告。' }}</small>
        </label>


        <button class="primary-btn full-width" @click="runDetection" :disabled="running || !uploadedFileName">
          {{ running ? '模型计算中' : '开始检测' }}
        </button>
      </aside>

      <section class="video-stage compact-video-card preview-column">
        <div class="stage-header compact-card-header">
          <div>
            <span class="kicker">Cross-source graph</span>
            <h2>{{ selected?.title || pendingCase?.title || '等待上传' }}</h2>
          </div>
          <span v-if="showReport" :class="['status-pill', selected.decision]">{{ selected.decision === 'allowed' ? 'Allowed' : 'Blocked' }}</span>
          <span v-else class="status-pill pending">Pending</span>
        </div>

        <div class="top-relation-carousel" :class="{ centered: showReport && activeRelationImages.length }" aria-label="跨源关系图片预览">
          <template v-if="showReport && activeRelationImages.length">
            <figure v-for="image in activeRelationImages" :key="image.src" class="top-relation-image-card">
              <img :src="image.src" :alt="image.alt" />
            </figure>
          </template>
          <div v-else class="top-relation-placeholder">
            <strong>{{ running ? '正在生成跨源关系图' : '等待跨源关系图' }}</strong>
            <span>{{ running ? '检测完成后将在这里展示分析图。' : uploadedFileName ? '点击开始检测后生成并展示对应分析图。' : '上传视频并完成检测后将在这里展示对应分析图。' }}</span>
          </div>
        </div>

        <div class="subtitle-card compact-subtitle">
          <span>字幕 / 文案</span>
          <p>{{ subtitleText }}</p>
        </div>

        <div class="process-row compact-process">
          <div v-for="(step, index) in detectionSteps" :key="step" :class="['process-step', { done: index < progress, current: index === progress && running }]">
            <span>{{ index + 1 }}</span>
            <p>{{ step }}</p>
          </div>
        </div>
      </section>
    </div>

    <section class="decision-panel report-dock">
      <template v-if="showReport">
        <div class="report-content-grid report-content-grid-four">
          <article class="report-block report-summary-column">
            <span class="kicker">Detection report</span>
            <div class="summary-stack">
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
          </article>

          <article class="report-block graph-block relation-placeholder-block">
            <span class="kicker">Cross-source graph</span>
            <h3>跨源关系</h3>
            <div class="relation-empty-placeholder" aria-label="跨源关系占位区域"></div>
          </article>

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
import metaphorRelationImage from '../../demo_video/metaphor_video.png'
import { demoCases, detectionSteps } from '../data/demoCases'

const selected = ref(null)
const pendingCase = ref(null)
const uploadedFileName = ref('')
const uploadedVideoUrl = ref('')
const running = ref(false)
const hasReport = ref(false)
const progress = ref(0)
let timer = null

const relationImageMap = {
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
