<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink to="/" class="brand">
        <span class="brand-dot"></span>
        <span>求职避坑核验</span>
      </RouterLink>
      <nav class="app-nav">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/analyze">开始核验</RouterLink>
        <RouterLink to="/batch">批量模式</RouterLink>
        <RouterLink to="/phrases">话术词库</RouterLink>
        <RouterLink to="/subject-check">签约方核验</RouterLink>
      </nav>
    </header>

    <main class="app-main">
      <RouterView />
    </main>

    <footer class="app-footer">
      <p class="footer-stages">投递前静态筛查 · 求职过程中主体监测 · 事后证据留存</p>
      <p>本结果基于公开信息自动分析，仅供参考，不构成对任何企业的事实认定或法律判断。</p>
    </footer>
  </div>
</template>
