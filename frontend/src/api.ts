// ============================================================
// api — 后端 API 封装。所有 HTTP 请求统一走这里。
// ============================================================

const BASE = '/api'

// === 通用请求（泛型：让每个接口声明自己的返回类型）===
async function request<T = any>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options)
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || data.detail || '请求失败')
  return data as T
}

// === 上传结果（判别联合：靠 file_type 区分 Excel 表格 vs PDF 文档）===
export interface SheetPreview {
  name: string
  columns: string[]
  row_count: number
  data: any[]
}

export interface ExcelUploadResult {
  session_id: string
  file_type: 'xlsx' | 'csv'
  sheets: SheetPreview[]
}

export interface PdfUploadResult {
  session_id: string
  file_type: 'pdf'
  page_count: number
  text_blocks: number
  images: number
}

export type UploadResult = ExcelUploadResult | PdfUploadResult

// === 上传文件 ===
export function uploadFile(file: File): Promise<UploadResult> {
  const fd = new FormData()
  fd.append('file', file)
  return request<UploadResult>('/upload', { method: 'POST', body: fd })
}

// === 聊天结果（判别联合：靠 answer_type / need_clarify / error 区分四种形态）===
export interface SourceHit {
  page: number
  bbox: [number, number, number, number]  // PDF 坐标 (x0,y0,x1,y1)，左下原点，y 向上
  text: string
}

export interface TextAnswer {
  answer_type: 'text'
  answer: string
  sources: SourceHit[]
}

export interface ChartAnswer {
  answer_type: 'chart'
  sql: string
  data: any[]
  chart_type: string
}

export interface ClarifyAnswer {
  answer_type: 'clarify'
  question: string
}

export interface ErrorAnswer {
  answer_type: 'error'
  error: string
}

export type ChatResult = TextAnswer | ChartAnswer | ClarifyAnswer | ErrorAnswer

// === 发送问题 ===
export function chat(sessionId: string, question: string): Promise<ChatResult> {
  return request<ChatResult>('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question }),
  })
}
