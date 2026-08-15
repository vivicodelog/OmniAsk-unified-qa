<script setup lang="ts">
// ============================================================
// QaView — 主页面。状态、事件处理在这儿写。
// ============================================================

import { ref, computed } from 'vue'
import FileUploader from '../components/FileUploader.vue'
import DataPreview from '../components/DataPreview.vue'
import ChatPanel from '../components/ChatPanel.vue'

// === 状态 ===
const sessionId = ref('')
const uploadedFile = ref<any>(null)
const activeSheet = ref('')
const uploading = ref(false)


// === 计算属性 ===
const sheets = computed(() => {
  return uploadedFile.value?.sheets ?? []  
})

// === 方法 ===
function handleUploaded(result: any) {
  sessionId.value = result.session_id
  uploadedFile.value = result
  activeSheet.value = result.sheets?.[0]?.name ?? ''
}


function handleSelectSheet(sheetName: string) {
  activeSheet.value = sheetName
}

</script>

<template>
  <div class="qa-view">
    <!-- 左栏 -->
    <aside class="left-panel">
      <div class="section-title">📁 文件上传</div>
      <FileUploader
        @uploaded="handleUploaded"
      />

      <div class="section-title">📊 数据预览</div>
      <DataPreview
        :sheets="sheets"
        :active-sheet="activeSheet"
        @select-sheet="handleSelectSheet"
      />
    </aside>

    <!-- 右栏 -->
    <main class="right-panel">
      <ChatPanel
        :session-id="sessionId"
      />
    </main>
  </div>
</template>

<style scoped>
.qa-view {
  display: flex;
  height: 100%;
  overflow: hidden;
}
.left-panel {
  width: 34%;
  min-width: 340px;
  max-width: 460px;
  border-right: 1px solid var(--n-border-color);
  display: flex;
  flex-direction: column;
  background: var(--n-color);
  overflow-y: auto;
}
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--n-color-embedded);
}
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-2);
  text-transform: uppercase;
  letter-spacing: .5px;
  padding: 16px 18px 8px;
}
</style>
