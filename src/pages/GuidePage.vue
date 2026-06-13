<template>
  <section class="page-section workbench-heading compact-heading">
    <div>
      <p class="eyebrow">User guide</p>
      <h1>如何使用 VidGuard 检测系统</h1>
    </div>
    <p>本指南将帮助您快速上手 VidGuard 视频内容安全检测系统，了解从上传视频到解读报告的完整流程。</p>
  </section>

  <section class="page-section guide-steps">
    <div v-for="(step, index) in steps" :key="step.title" class="guide-step-card">
      <div class="guide-step-number">{{ index + 1 }}</div>
      <div class="guide-step-body">
        <h3>{{ step.title }}</h3>
        <p>{{ step.description }}</p>
        <ul v-if="step.tips" class="guide-tips">
          <li v-for="tip in step.tips" :key="tip">{{ tip }}</li>
        </ul>
      </div>
    </div>
  </section>

  <section class="page-section guide-report-section">
    <div class="guide-report-header">
      <span class="kicker">Report guide</span>
      <h2>如何解读检测报告</h2>
    </div>
    <div class="guide-report-grid">
      <div class="guide-report-item">
        <h3>风险等级</h3>
        <p>系统将风险分为<strong>低</strong>、<strong>中</strong>、<strong>高</strong>三级。低风险内容通常可安全发布，高风险内容建议拦截处理。</p>
      </div>
      <div class="guide-report-item">
        <h3>信号解释</h3>
        <p>报告分别展示视频信号、字幕信号和组合信号的分析结果。组合信号是系统的核心能力——它推理视频与字幕联合后的<strong>真实意图</strong>。</p>
      </div>
      <div class="guide-report-item">
        <h3>跨源场景图</h3>
        <p>以实体-关系图的形式展示视频中的视觉实体与字幕语义之间的关联，帮助理解系统如何从多模态信息中推导风险。</p>
      </div>
      <div class="guide-report-item">
        <h3>处置建议</h3>
        <p>系统会根据分析结果给出具体的处置建议，包括是否允许发布、需要人工复审或直接拦截等。</p>
      </div>
    </div>
  </section>

  <section class="page-section guide-faq">
    <div class="guide-report-header">
      <span class="kicker">FAQ</span>
      <h2>常见问题</h2>
    </div>
    <div class="faq-list">
      <div v-for="(item, index) in faqs" :key="index" class="faq-item" :class="{ open: openFaq === index }">
        <button class="faq-question" @click="toggleFaq(index)">
          <span>{{ item.q }}</span>
          <span class="faq-arrow">{{ openFaq === index ? '−' : '+' }}</span>
        </button>
        <div v-if="openFaq === index" class="faq-answer">
          <p>{{ item.a }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

const openFaq = ref(null)

function toggleFaq(index) {
  openFaq.value = openFaq.value === index ? null : index
}

const steps = [
  {
    title: '上传视频',
    description: '在检测工作台页面，点击上传区域选择本地视频文件。系统支持 MP4 等常见视频格式。',
    tips: [
      '演示模式下，文件名包含 "safe" 将匹配安全示例',
      '文件名包含 "harmful" 将匹配直接违规示例',
      '文件名包含 "metaphor" 将匹配隐喻型违规示例'
    ]
  },
  {
    title: '查看字幕匹配',
    description: '上传视频后，系统会根据视频自动匹配对应的字幕/文案内容。字幕是多模态分析的重要组成部分，系统会同时理解视觉内容和文本语义。'
  },
  {
    title: '开始检测',
    description: '点击"开始检测"按钮，系统将依次执行 5 个分析阶段：视觉特征提取、字幕语义解析、跨源场景图构建、多模态融合推理、合规决策生成。',
    tips: [
      '每个阶段约耗时 900ms，总计约 4.5 秒',
      '检测过程中可观察进度条的实时变化'
    ]
  },
  {
    title: '解读报告',
    description: '检测完成后，右侧面板将展示完整的分析报告，包括风险等级、置信度、风险类型标签、信号解释、跨源场景图和处置建议。'
  }
]

const faqs = [
  {
    q: 'VidGuard 与传统视频审核有什么区别？',
    a: '传统审核通常分别分析视频画面和文本，而 VidGuard 将视频与字幕作为整体进行联合推理，能够捕捉到单独分析任一模态都无法发现的隐喻型违规意图。'
  },
  {
    q: '支持哪些视频格式？',
    a: '演示版本支持 MP4 格式。实际部署版本将支持 MP4、AVI、MOV 等主流视频格式。'
  },
  {
    q: '什么是跨源场景图？',
    a: '跨源场景图是 VidGuard 的核心技术，它将视频中的视觉实体与字幕中的语义实体进行关联，构建统一的知识图谱，从而理解视频与字幕组合后产生的深层含义。'
  }
]
</script>
