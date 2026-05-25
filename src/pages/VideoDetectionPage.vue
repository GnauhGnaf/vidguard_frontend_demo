<template>
  <section class="page-section workbench-heading compact-heading">
    <div>
      <p class="eyebrow">Multimodal detection workbench</p>
      <h1>上传视频，生成组合风险解释。</h1>
    </div>
    <p>用户上传演示视频后，系统展示对应的固定分析结果；交互模拟真实检测流程，报告内容保持预生成。</p>
  </section>

  <section class="page-section compact-workbench">
    <aside class="sample-panel compact-panel">
      <div class="panel-title">
        <span class="kicker">Input</span>
        <h2>上传视频</h2>
      </div>

      <label class="upload-dropzone" :class="{ ready: uploadedFileName }">
        <input type="file" accept="video/*" @change="handleUpload" />
        <span>{{ uploadedFileName || '选择演示视频' }}</span>
        <small>支持 safe / harmful / metaphor 三类演示视频；分析结果为预生成报告。</small>
      </label>

      <div class="upload-hints">
        <span>safe_video</span>
        <span>harmful_video</span>
        <span>metaphor_video</span>
      </div>

      <button class="primary-btn full-width" @click="runDetection" :disabled="running || !uploadedFileName">
        {{ running ? '模型计算中' : '开始检测' }}
      </button>
    </aside>

    <section class="video-stage compact-video-card">
      <div class="stage-header compact-card-header">
        <div>
          <span class="kicker">Preview</span>
          <h2>{{ selected?.title || '等待上传' }}</h2>
        </div>
        <span v-if="showReport" :class="['status-pill', selected.decision]">{{ selected.decision === 'allowed' ? 'Allowed' : 'Blocked' }}</span>
        <span v-else class="status-pill pending">Pending</span>
      </div>

      <video v-if="previewVideo" class="demo-video compact-main-video" :src="previewVideo" controls muted playsinline />
      <div v-else class="video-placeholder compact-main-video upload-empty-state">
        <div>
          <strong>等待上传视频</strong>
          <span>上传后将在这里预览；点击开始检测后显示分析报告。</span>
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

    <aside class="decision-panel compact-report-card">
      <template v-if="showReport">
        <div class="decision-topline compact-decision">
          <span :class="['result-dot', selected.decision]"></span>
          <div>
            <p class="kicker">Decision</p>
            <h2>{{ selected.decision === 'allowed' ? '允许发布' : '建议拦截' }}</h2>
          </div>
        </div>

        <div class="compact-stats">
          <div><span>风险等级</span><strong>{{ levelText }}</strong></div>
          <div><span>置信度</span><strong>{{ percent(selected.confidence) }}</strong></div>
        </div>

        <div class="subsection tight-section">
          <h3>风险类型</h3>
          <div class="tag-row"><span v-for="type in selected.riskTypes" :key="type">{{ type }}</span></div>
        </div>

        <div class="subsection tight-section">
          <h3>信号解释</h3>
          <dl class="signal-list">
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
        </div>

        <div class="subsection tight-section">
          <h3>跨源关系</h3>
          <SceneGraph :relations="selected.relations" />
        </div>

        <div class="subsection tight-section final-report">
          <h3>解释报告</h3>
          <p>{{ selected.explanation }}</p>
          <p><strong>处置建议：</strong>{{ selected.recommendation }}</p>
        </div>
      </template>

      <div v-else class="report-placeholder">
        <span>{{ running ? 'Analyzing' : uploadedFileName ? 'Ready' : 'Empty' }}</span>
        <h2>{{ running ? '模型正在计算' : uploadedFileName ? '等待开始检测' : '尚未上传视频' }}</h2>
        <p>{{ running ? '系统正在模拟多模态模型计算过程，请稍候。' : uploadedFileName ? '点击“开始检测”后，系统会展示该视频对应的预生成分析报告。' : '请先在左侧上传一个演示视频。' }}</p>
      </div>
    </aside>
  </section>

</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import SceneGraph from '../components/SceneGraph.vue'
import { demoCases, detectionSteps } from '../data/demoCases'

const selected = ref(null)
const pendingCase = ref(null)
const uploadedFileName = ref('')
const uploadedVideoUrl = ref('')
const running = ref(false)
const hasReport = ref(false)
const progress = ref(0)
let timer = null

const previewVideo = computed(() => uploadedVideoUrl.value || '')
const showReport = computed(() => Boolean(selected.value && hasReport.value && !running.value))
const subtitleText = computed(() => selected.value?.subtitle || pendingCase.value?.subtitle || '上传视频后自动匹配字幕文案。')
const levelText = computed(() => ({ low: '低', medium: '中', high: '高' }[selected.value?.riskLevel] || selected.value?.riskLevel || '-') )

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
  if (timer) clearInterval(timer)
}

function runDetection() {
  if (!pendingCase.value) return
  running.value = true
  hasReport.value = false
  selected.value = pendingCase.value
  progress.value = 0
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    progress.value += 1
    if (progress.value >= detectionSteps.length) {
      running.value = false
      hasReport.value = true
      progress.value = detectionSteps.length
      clearInterval(timer)
    }
  }, 900)
}

onBeforeUnmount(() => {
  if (uploadedVideoUrl.value) URL.revokeObjectURL(uploadedVideoUrl.value)
  if (timer) clearInterval(timer)
})
</script>
