<script setup lang="ts">
// ============================================================
// FileUploader — 拖拽上传区 + 已上传文件标签
// ============================================================
import { ref } from 'vue'
import { uploadFile as uploadFileApi } from '../api'
// === Props ===
// === Emits ===
const emit = defineEmits<{
  uploaded: [result: any]  // 上传完成后通知父组件
}>()

// === 状态 ===
const file = ref<any>(null)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
// === 方法 ===
function handleDrop(e: DragEvent) {
  const rawFile = e.dataTransfer?.files?.[0]
  if (rawFile) uploadFile(rawFile)
}
function handleFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  const rawFile = input.files?.[0]
  if (rawFile) uploadFile(rawFile)
}
async function uploadFile(rawFile: File) {
  uploading.value = true
  try {
    const data = await uploadFileApi(rawFile)  // ← 一行搞定
    file.value = data
    emit('uploaded', data)
  } catch (e: any) {
    console.error(e)
    file.value = null
    
  } finally {
    uploading.value = false
  }
}
// 点击上传区 → 触发隐藏 input
function handleClick() {
  fileInputRef.value?.click()
}

</script>

<template>
  <div class="file-uploader">
    <!-- 拖拽区 -->
     <input
      ref="fileInputRef"
      type="file"
      hidden
      accept=".xlsx,.csv,.pdf"
      @change="handleFileInput"
    />
    <div
      class="upload-zone"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="handleClick"      
    >
      <div class="icon">📂</div>
      <div class="hint">拖拽文件到此处，或点击上传</div>
      <div class="sub">支持 .xlsx  .csv  .pdf（单个文件不超过 50MB）</div>
    </div>

    <!-- 已上传文件标签 -->
    <div v-if="file" class="file-tag">
      <span class="dot"></span>
      <span>{{ file.file_type?.toUpperCase() }}</span>
      <span class="status">已解析 ✓</span>
    </div>
  </div>
</template>

<style scoped>
.file-uploader { padding: 0 18px; }
.upload-zone {
  border: 2px dashed var(--n-border-color);
  border-radius: var(--n-radius);
  padding: 28px;
  text-align: center;
  cursor: pointer;
  transition: all .2s;
}
.upload-zone:hover {
  border-color: var(--n-primary);
  background: #fafbff;
}
.upload-zone .icon { font-size: 32px; margin-bottom: 8px; }
.upload-zone .hint { font-size: 13px; color: var(--n-text-color-2); }
.upload-zone .sub { font-size: 11px; color: var(--n-text-color-3, #9ca3af); margin-top: 4px; }
.file-tag {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
}
.file-tag .dot { width: 8px; height: 8px; background: #22c55e; border-radius: 99px; }
.file-tag .status { margin-left: auto; color: var(--n-text-color-3, #9ca3af); font-size: 11px; }
</style>
