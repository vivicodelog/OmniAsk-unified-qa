<script setup lang="ts">
// ============================================================
// QaView — 主页面。状态、事件处理在这儿写。
// ============================================================

import { ref, computed } from 'vue'
import FileUploader from '../components/FileUploader.vue'
import DataPreview from '../components/DataPreview.vue'
import PdfViewer from '../components/PdfViewer.vue'
import ChatPanel from '../components/ChatPanel.vue'
import type { UploadResult, SheetPreview, SourceHit } from '../api'

// === 状态 ===
const sessionId = ref('')
const uploadedFile = ref<UploadResult | null>(null)
const activeSheet = ref('')
const sources = ref<SourceHit[]>([])

// === 计算属性 ===
// 靠 file_type 判别：pdf 走 PdfViewer，否则走 DataPreview
const isPdf = computed(() => uploadedFile.value?.file_type === 'pdf')

const sheets = computed<SheetPreview[]>(() => {
  const f = uploadedFile.value
  return f && f.file_type !== 'pdf' ? f.sheets : []
})

// === 方法 ===
function handleUploaded(result: UploadResult) {
  sessionId.value = result.session_id
  uploadedFile.value = result
  // PDF 没有 sheet 概念，清空；Excel 默认选中第一个 sheet
  activeSheet.value = result.file_type !== 'pdf' ? result.sheets[0]?.name ?? '' : ''
  sources.value = []   // 换文件清空旧高亮
}

function handleSelectSheet(sheetName: string) {
  activeSheet.value = sheetName
}

function handleSources(s: SourceHit[]) {
  sources.value = s
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

      <div class="section-title">{{ isPdf ? '📄 PDF 预览' : '📊 数据预览' }}</div>
      <PdfViewer
        v-if="isPdf"
        :session-id="sessionId"
        :sources="sources"
      />
      <DataPreview
        v-else
        :sheets="sheets"
        :active-sheet="activeSheet"
        @select-sheet="handleSelectSheet"
      />
    </aside>

    <!-- 右栏 -->
    <main class="right-panel">
      <ChatPanel
        :session-id="sessionId"
        @sources="handleSources"
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
