<script setup lang="ts">
// ============================================================
// PdfViewer — PDF 预览 + 溯源高亮（vue-pdf-embed 渲染）
// ============================================================

import { ref, shallowRef, watch, nextTick } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
import type { PDFDocumentProxy } from 'pdfjs-dist'
import type { SourceHit } from '../api'

const props = defineProps<{
  sessionId: string
  sources: SourceHit[]
}>()

const viewerRef = ref<HTMLDivElement | null>(null)
// 用 shallowRef：PDFDocumentProxy 是 pdf.js 实例，不能被 Vue 的 Proxy 深度代理，
// 否则 getPage() 内部访问 #私有字段会报 "Cannot read from private field"
const doc = shallowRef<PDFDocumentProxy | null>(null)

function onLoaded(d: PDFDocumentProxy) {
  doc.value = d
}

// 命令式高亮：往 vue-pdf-embed 每页容器里塞半透明框（第三方组件内部，只能操作 DOM）
async function drawHighlights() {
  clearHighlights()
  if (!doc.value || !props.sources.length || !viewerRef.value) return
  const pageEls = viewerRef.value.querySelectorAll<HTMLElement>('.vue-pdf-embed__page')
  for (const src of props.sources) {
    const pageEl = pageEls[src.page - 1]
    const canvas = pageEl?.querySelector('canvas')
    if (!pageEl || !canvas) {
      console.log('[高亮] 跳过', { page: src.page, hasPageEl: !!pageEl, hasCanvas: !!canvas })
      continue
    }
    // 缩放比 = canvas 渲染宽度 / PDF 原始宽度（vue-pdf-embed 按容器宽度缩放）
    const page = await doc.value.getPage(src.page)   // getPage 返回 Promise，先 await
    const viewport = page.getViewport({ scale: 1 })
    const scale = canvas.clientWidth / viewport.width
    const [x0, y0, x1, y1] = src.bbox
    const box = document.createElement('div')
    box.className = 'qa-highlight'
    // PyMuPDF bbox 已是左上原点(y向下)，与 CSS 一致，直接乘 scale，无需翻转
    box.style.left = `${x0 * scale}px`
    box.style.top = `${y0 * scale}px`
    box.style.width = `${(x1 - x0) * scale}px`
    box.style.height = `${(y1 - y0) * scale}px`
    pageEl.appendChild(box)
    console.log('[高亮] 已画', { page: src.page, canvasW: canvas.clientWidth, pdfW: viewport.width, scale, left: box.style.left, top: box.style.top, width: box.style.width, height: box.style.height })
  }
}

function clearHighlights() {
  viewerRef.value?.querySelectorAll('.qa-highlight').forEach(el => el.remove())
}

async function onRendered() {
  await drawHighlights()
}

// 新答案的 sources 变化 → 重绘（文档可能已渲染，nextTick 等 DOM 稳定）
watch(() => props.sources, () => { nextTick(drawHighlights) })
</script>

<template>
  <div class="pdf-viewer" ref="viewerRef">
    <VuePdfEmbed
      :source="`/api/file/${props.sessionId}`"
      @loaded="onLoaded"
      @rendered="onRendered"
    />
  </div>
</template>

<style scoped>
.pdf-viewer {
  margin: 12px 18px 18px;
  border: 1px solid var(--n-border-color);
  border-radius: var(--n-radius);
  flex: 1;
  overflow-y: auto;
  background: #525659;
  padding: 16px;
}
/* 每页容器作为高亮框的定位上下文 */
.pdf-viewer :deep(.vue-pdf-embed__page) {
  position: relative;
}
.pdf-viewer :deep(.qa-highlight) {
  position: absolute;
  background: rgba(255, 200, 0, 0.35);
  border: 1px solid rgba(255, 150, 0, 0.8);
  pointer-events: none;
}
</style>
