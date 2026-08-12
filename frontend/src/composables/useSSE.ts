// ============================================================
// useSSE — SSE 流式解析（v2 预留，v1 先用普通 POST）
// ============================================================

import { ref } from 'vue'

export function useSSE() {
  // === 状态 ===
  // const streaming = ref(false)    是否正在流式接收

  // === 方法 ===
  // async function connect(url: string, onChunk: (text: string) => void): Promise<void>
  //   1. fetch + ReadableStream
  //   2. 逐行解析 "data:" 前缀
  //   3. 更新 streaming

  return {
    // streaming,
    // connect,
  }
}
