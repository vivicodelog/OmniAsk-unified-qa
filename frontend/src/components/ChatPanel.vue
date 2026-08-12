<script setup lang="ts">
// ============================================================
// ChatPanel — 对话面板。消息列表 + 输入框。
// ============================================================

import { ref } from 'vue'
import ChartPanel from './ChartPanel.vue'

import { chat } from '../api'
// === Props ===
const props = defineProps<{
  sessionId: string
}>()
// === Emits ===

// === 状态 ===
const messages = ref<any[]>([])
const question = ref('')
const loading = ref(false)
const scrollRef = ref<HTMLDivElement | null>(null)

// === 方法 ===
async function handleSend() {
  if (!question.value.trim()) return
  // 1. 用户消息上屏
  messages.value.push({ role: 'user', content: question.value })  
  const q = question.value
  question.value = ''   // 清空输入框
  // 2. 调 API
  loading.value = true
  try {
    const data = await chat(props.sessionId, q)
    // 3. AI 消息上屏
    messages.value.push({
      role: 'ai',
      content: data.sql,       // 先展示 SQL，v2 再改成自然语言
      sql: data.sql,
      data: data.data,
      chartType: data.chart_type,
    })
  } catch (e: any) {
    messages.value.push({ role: 'ai', content: `出错了：${e.message}` })
  } finally {
    loading.value = false
  }
}

</script>

<template>
  <div class="chat-panel">
    <!-- 消息流 -->
    <div class="chat-stream" ref="scrollRef">
      <div v-if="messages.length === 0 " class="empty-hint">
        <p>👋 上传文件后，在这里向 AI 提问</p>
        <p class="example">例如：各产品销量占比是多少？</p>
      </div>      
      <div v-for="(msg, i) in messages" :key="i"
           :class="['msg', msg.role]">
        <div class="bubble">{{ msg.content }}</div>
        <ChartPanel
          v-if="msg.chartType"
          :chart-type="msg.chartType"
          :data="msg.data"
          :sql="msg.sql"
        />
      </div>  
      <!-- 加载态 -->
      <div v-if="loading" class="msg ai"><div class="bubble typing">...</div></div>
    </div>

    <!-- 输入栏 -->
    <div class="input-bar">
      <input
        v-model="question"
        type="text"
        placeholder="输入你的问题，如：各区域销售额趋势如何？"
        @keyup.enter="handleSend"
      />
      <button @click="handleSend">发送 →</button>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.chat-stream {
  flex: 1;
  overflow-y: auto;
  padding: 18px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.empty-hint {
  text-align: center;
  color: var(--n-text-color-2);
  margin-top: 120px;
}
.empty-hint p { font-size: 15px; }
.empty-hint .example { font-size: 12px; color: var(--n-text-color-3, #9ca3af); margin-top: 6px; }

/* 消息气泡 */
.msg { display: flex; flex-direction: column; max-width: 92%; }
.msg.user { align-self: flex-end; }
.msg.ai   { align-self: flex-start; }
.msg .bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}
.msg.user .bubble {
  background: var(--n-primary); color: #fff; border-bottom-right-radius: 4px;
}
.msg.ai .bubble {
  background: var(--n-color); border: 1px solid var(--n-border-color); border-bottom-left-radius: 4px;
}
.msg .typing { animation: blink 1.4s infinite; }
@keyframes blink { 0%,100%{opacity:.2} 50%{opacity:1} }

/* 输入栏 */
.input-bar {
  border-top: 1px solid var(--n-border-color);
  background: var(--n-color);
  padding: 14px 22px;
  display: flex;
  gap: 10px;
  align-items: center;
}
.input-bar input {
  flex: 1;
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  outline: none;
  transition: border .2s;
}
.input-bar input:focus { border-color: var(--n-primary); }
.input-bar button {
  background: var(--n-primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
}
.input-bar button:hover { opacity: .9; }
</style>
