<script setup lang="ts">
// ============================================================
// App — 顶栏 + QaView 布局
// ============================================================
import QaView from './views/QaView.vue'
</script>

<template>
  <div class="app-shell">
    <header class="top-bar">
      <span class="logo">🧠 Unified QA</span>
      <span class="badge">v2</span>
    </header>
    <QaView />
  </div>
</template>

<style>
/* === 全局变量 === */
:root {
  --n-color: #fff;
  --n-color-embedded: #f5f6fa;
  --n-border-color: #e8eaef;
  --n-text-color: #1f2937;
  --n-text-color-2: #6b7280;
  --n-primary: #5b6af0;
  --n-primary-light: #eef0ff;
  --n-radius: 10px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app {
  height: 100%;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--n-text-color);
  background: var(--n-color-embedded);
}
</style>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.top-bar {
  height: 52px;
  background: var(--n-color);
  border-bottom: 1px solid var(--n-border-color);
  display: flex;
  align-items: center;
  padding: 0 22px;
  gap: 10px;
  flex-shrink: 0;
}
.logo { font-size: 18px; font-weight: 700; color: var(--n-primary); }
.badge {
  font-size: 11px;
  background: var(--n-primary-light);
  color: var(--n-primary);
  padding: 2px 8px;
  border-radius: 99px;
  font-weight: 500;
}
</style>
