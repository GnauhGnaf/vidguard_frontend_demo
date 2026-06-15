<template>
  <div class="app-shell">
    <NeuralBackground />
    <header class="topbar">
      <RouterLink class="brand" to="/" aria-label="VidGuard 首页">
        <span class="brand-mark">V</span>
        <span class="brand-text">VidGuard</span>
      </RouterLink>
      <nav class="nav-links" aria-label="主导航">
        <RouterLink to="/">概览</RouterLink>
        <RouterLink to="/video-detection">检测工作台</RouterLink>
        <RouterLink to="/guide">使用指南</RouterLink>
      </nav>
      <RouterLink class="topbar-user" to="/profile" aria-label="个人中心">
        <span class="topbar-avatar">演</span>
      </RouterLink>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import NeuralBackground from './components/NeuralBackground.vue'
</script>
