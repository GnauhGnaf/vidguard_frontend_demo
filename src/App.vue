<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/" aria-label="VidGuard 首页">
        <span class="brand-mark">V</span>
        <span class="brand-text">VidGuard</span>
      </RouterLink>
      <nav class="nav-links" aria-label="主导航">
        <RouterLink to="/">概览</RouterLink>
        <RouterLink to="/video-detection">检测工作台</RouterLink>
      </nav>
    </header>

    <main>
      <RouterView />
    </main>
  </div>
</template>
