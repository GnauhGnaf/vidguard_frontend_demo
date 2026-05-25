<template>
  <section class="home-hero page-section">
    <p class="eyebrow">VidGuard / Video safety infrastructure</p>
    <div class="hero-grid">
      <div>
        <h1>把视频和字幕一起理解，再判断它是否安全。</h1>
        <p class="hero-subtitle">VidGuard 面向 AIGC 生成视频与真实视频审核，用时空场景图与字幕上下文捕捉跨帧、跨源、隐喻型违规意图，并给出可解释的合规结论。</p>
        <div class="hero-actions">
          <RouterLink class="primary-btn" to="/video-detection">进入检测工作台</RouterLink>
        </div>
      </div>
      <div class="thesis-card">
        <span>Core claim</span>
        <strong>不是分别看视频和字幕，而是推理二者组合后产生的真实意图。</strong>
      </div>
    </div>
  </section>

  <section class="page-section narrative-strip">
    <article>
      <span>01</span>
      <h2>视频与字幕进入系统</h2>
      <p>上传视频并输入字幕，系统同时读取视觉线索和文本上下文。</p>
    </article>
    <article>
      <span>02</span>
      <h2>构建跨源场景图</h2>
      <p>追踪视觉实体，解析字幕意图，并对齐二者之间的互补或冲突关系。</p>
    </article>
    <article>
      <span>03</span>
      <h2>给出合规决策</h2>
      <p>输出风险等级、跨源关系链路和可执行的处置建议。</p>
    </article>
  </section>


  <section class="page-section metrics-strip">
    <div><strong>2000+</strong><span>视频样本</span></div>
    <div><strong>32K+</strong><span>视频帧</span></div>
    <div><strong>7 类</strong><span>违规内容</span></div>
    <div><strong>97.62%</strong><span>Unsafe-VidGraph F1</span></div>
  </section>
</template>
