<template>
  <section class="page-section profile-header">
    <div class="profile-user-card">
      <div class="profile-avatar">{{ user.name.charAt(0) }}</div>
      <div class="profile-info">
        <h1>{{ user.name }}</h1>
        <p>注册于 {{ user.registerDate }} · 累计使用 {{ user.daysUsed }} 天</p>
      </div>
    </div>
  </section>

  <section class="page-section profile-stats">
    <div class="profile-stats-grid">
      <div class="profile-stat-item">
        <strong>{{ user.totalDetections }}</strong>
        <span>总检测次数</span>
      </div>
      <div class="profile-stat-item">
        <strong>{{ user.blocked }}</strong>
        <span>拦截次数</span>
      </div>
      <div class="profile-stat-item">
        <strong>{{ user.allowed }}</strong>
        <span>通过次数</span>
      </div>
      <div class="profile-stat-item">
        <strong>{{ user.blockRate }}</strong>
        <span>拦截率</span>
      </div>
    </div>
  </section>

  <section class="page-section profile-history">
    <div class="profile-section-header">
      <span class="kicker">History</span>
      <h2>检测历史</h2>
    </div>

    <div class="history-list">
      <div v-for="record in history" :key="record.id" class="history-item">
        <div class="history-main">
          <div class="history-name">
            <strong>{{ record.fileName }}</strong>
            <span :class="['status-pill', record.decision]">{{ record.decision === 'allowed' ? 'Allowed' : 'Blocked' }}</span>
          </div>
          <div class="history-meta">
            <span>{{ record.date }}</span>
            <span>·</span>
            <span>风险等级：{{ record.riskLevel }}</span>
            <span>·</span>
            <span>置信度：{{ record.confidence }}</span>
          </div>
          <p class="history-summary">{{ record.summary }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const user = {
  name: '演示用户',
  registerDate: '2026 年 3 月',
  daysUsed: 84,
  totalDetections: 47,
  blocked: 12,
  allowed: 35,
  blockRate: '25.53%'
}

const history = [
  {
    id: 1,
    fileName: 'metaphor_door_video.mp4',
    date: '2026-06-03 14:22',
    decision: 'blocked',
    riskLevel: '高',
    confidence: '94.18%',
    summary: '视频画面为正常室内场景，但字幕"打开那扇门"在上下文中构成隐喻型违规意图，系统通过跨源推理识别出潜在风险。'
  },
  {
    id: 2,
    fileName: 'harmful_rob_scene.mp4',
    date: '2026-06-02 09:15',
    decision: 'blocked',
    riskLevel: '高',
    confidence: '97.62%',
    summary: '视频画面直接包含暴力行为场景，字幕内容与画面一致，系统判定为高风险违规内容。'
  },
  {
    id: 3,
    fileName: 'safe_travel_vlog.mp4',
    date: '2026-06-01 16:48',
    decision: 'allowed',
    riskLevel: '低',
    confidence: '98.35%',
    summary: '旅游 vlog 内容，画面与字幕均为正常旅行记录，未检测到违规信号。'
  },
  {
    id: 4,
    fileName: 'safe_cooking_video.mp4',
    date: '2026-05-30 11:30',
    decision: 'allowed',
    riskLevel: '低',
    confidence: '96.71%',
    summary: '美食制作视频，画面展示烹饪过程，字幕为食谱说明，内容安全合规。'
  },
  {
    id: 5,
    fileName: 'metaphor_symbolic.mp4',
    date: '2026-05-28 20:05',
    decision: 'blocked',
    riskLevel: '中',
    confidence: '87.43%',
    summary: '视频使用象征性画面配合暗示性文案，系统识别出跨源语义冲突，判定存在中等风险。'
  }
]
</script>
