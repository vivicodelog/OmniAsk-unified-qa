// ============================================================
// api — 后端 API 封装。所有 HTTP 请求统一走这里。
// ============================================================

const BASE = '/api'

// === 通用请求 ===
async function request(path: string, options?: RequestInit): Promise<any> {
  const res = await fetch(`${BASE}${path}`, options)
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || data.detail || '请求失败')
  return data
}

// === 上传文件 ===
export function uploadFile(file: File): Promise<{
  session_id: string
  file_type: string
  sheets: { name: string; columns: string[]; row_count: number; data: any[] }[]
}> {
  const fd = new FormData()
  fd.append('file', file)
  return request('/upload', { method: 'POST', body: fd })
}

// === 发送问题 ===
export function chat(sessionId: string, question: string): Promise<{
  question: any          // 反问问题，命名容易和请求参数 question 混
  need_clarify: any      // 应是 boolean
  sql: string            // need_clarify 时这三个字段其实没有
  data: any[]
  chart_type: string
}>
 {
  return request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question }),
  })
}
