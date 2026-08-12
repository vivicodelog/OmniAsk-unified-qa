// ============================================================
// useFileUpload — 文件上传逻辑封装
// ============================================================

import { ref } from 'vue'

export function useFileUpload() {
  // === 状态 ===
  // const file = ref<...>(null)      上传结果
  // const uploading = ref(false)     上传中

  // === 方法 ===
  // async function upload(file: File): Promise<void>
  //   1. 构建 FormData
  //   2. POST /api/upload
  //   3. 更新 file + uploading

  return {
    // file,
    // uploading,
    // upload,
  }
}
