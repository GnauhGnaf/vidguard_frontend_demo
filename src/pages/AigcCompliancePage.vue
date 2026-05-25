<template>
  <section class="page-section workbench-heading">
    <div>
      <p class="eyebrow">Generation safety</p>
      <h1>把合规检测放在视频生成之后、发布之前。</h1>
    </div>
    <p>这页展示 AIGC 平台的安全闭环：输入提示词，系统模拟生成结果，若检测到高风险语义则拦截，并提供安全改写建议。</p>
  </section>

  <section class="page-section generation-shell">
    <section class="prompt-panel">
      <div class="card-heading">
        <span class="kicker">Prompt</span>
        <h2>生成意图</h2>
      </div>
      <textarea v-model="prompt" placeholder="请输入视频生成提示词"></textarea>
      <div class="prompt-actions">
        <button class="secondary-btn" @click="loadExample('aigc-risk')">载入高风险示例</button>
        <button class="secondary-btn" @click="loadExample('aigc-safe')">载入合规示例</button>
        <button class="primary-btn" @click="runCheck" :disabled="running">{{ running ? '检测中' : '生成并检测' }}</button>
      </div>

      <div class="generation-flow">
        <div v-for="(item, index) in flow" :key="item" :class="['flow-item', { active: running || index < 4 }]">
          <span>{{ index + 1 }}</span>{{ item }}
        </div>
      </div>
    </section>

    <section class="preview-panel">
      <div class="decision-topline">
        <span :class="['result-dot', current.status === 'allowed' ? 'allowed' : 'blocked']"></span>
        <div>
          <p class="kicker">Compliance decision</p>
          <h2>{{ current.status === 'allowed' ? '合规通过' : '生成结果已拦截' }}</h2>
        </div>
      </div>

      <video v-if="hasVideo(current.video)" class="demo-video compact" :src="current.video" controls muted playsinline />
      <div v-else class="video-placeholder compact">
        <div>
          <strong>生成视频预览占位</strong>
          <span>请替换为真实 AIGC 视频素材：{{ current.video }}</span>
        </div>
      </div>

      <div class="compact-stats">
        <div><span>置信度</span><strong>{{ percent(current.confidence) }}</strong></div>
        <div><span>风险类型</span><strong>{{ current.riskTypes.join(' / ') }}</strong></div>
      </div>
    </section>
  </section>

  <section class="page-section evidence-grid two-col">
    <article class="evidence-card">
      <div class="card-heading">
        <span class="kicker">Semantic graph</span>
        <h2>提示词语义图</h2>
      </div>
      <SceneGraph :relations="current.graph" />
    </article>

    <article class="evidence-card explanation-card">
      <div class="card-heading">
        <span class="kicker">Explanation</span>
        <h2>检测解释</h2>
      </div>
      <p>{{ current.explanation }}</p>
    </article>

    <article v-if="current.rewrite" class="evidence-card rewrite-card wide-row">
      <div class="card-heading">
        <span class="kicker">Rewrite</span>
        <h2>安全改写建议</h2>
      </div>
      <p>{{ current.rewrite }}</p>
      <button class="secondary-btn" @click="prompt = current.rewrite">使用改写提示词</button>
    </article>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import SceneGraph from '../components/SceneGraph.vue'
import { aigcExamples } from '../data/demoCases'

const current = ref(aigcExamples[0])
const prompt = ref(current.value.prompt)
const running = ref(false)
const flow = ['解析提示词', '匹配演示视频', '构建语义场景图', '执行合规检测']

function percent(value) {
  return `${(value * 100).toFixed(2)}%`
}

function hasVideo(path) {
  return path && !path.includes('placeholder')
}

function loadExample(id) {
  current.value = aigcExamples.find((item) => item.id === id) || aigcExamples[0]
  prompt.value = current.value.prompt
}

function runCheck() {
  running.value = true
  setTimeout(() => {
    const riskyWords = ['刀', '害怕', '威胁', '攻击', '暴力']
    const isRisk = riskyWords.some((word) => prompt.value.includes(word))
    current.value = isRisk ? aigcExamples[0] : aigcExamples[1]
    running.value = false
  }, 1800)
}
</script>
