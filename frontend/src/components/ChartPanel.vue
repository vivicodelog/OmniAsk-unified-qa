<script setup lang="ts">
// ============================================================
// ChartPanel — ECharts 图表渲染，根据 chart_type 切换
// ============================================================

import { ref, computed } from 'vue'

// === Props ===
const props = defineProps<{
  chartType: string    // "pie" | "line" | "bar" | "scatter" | "table"
  data: any[]          // 查询结果数据
  sql: string          // 生成的 SQL（供展示）
}>()

// === 状态 ===
const sqlVisible = ref(false)
const chartRef = ref<HTMLDivElement | null>(null)

// === 计算属性 ===
const columnKeys = computed(() => {
  // 根据 data 返回列名数组
  if (props.data.length === 0) return []
  return Object.keys(props.data[0])
})


// === 方法 ===
function toggleSql() {
  sqlVisible.value = !sqlVisible.value
}
</script>

<template>
  <div class="chart-panel">
    <!-- SQL 可折叠区 -->
    <div class="sql-toggle" @click="toggleSql">
      <span>📋 查看 SQL {{ sqlVisible ? '▾' : '▸' }}</span>
    </div>
    <div v-if="sqlVisible" class="sql-block">
      {{ sql }}
    </div>

    <!-- 图表区 -->
    <div class="chart-container" ref="chartRef">
      <!-- ECharts 渲染到这里 -->
    </div>

    <!-- 结果表格 -->
    <div class="result-table" v-if="data.length">
      <table>
        <thead>
          <tr>
            <th v-for="key in columnKeys" :key="key">{{ key }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in data" :key="i">
            <td v-for="key in columnKeys" :key="key">{{ row[key] }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.chart-panel { margin-top: 8px; }
.sql-toggle {
  font-size: 12px;
  color: var(--n-primary);
  cursor: pointer;
  user-select: none;
  margin-bottom: 6px;
}
.sql-block {
  background: #1e293b;
  color: #e2e8f0;
  border-radius: 6px;
  padding: 10px 14px;
  font-family: "Fira Code", Consolas, monospace;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  margin-bottom: 8px;
}
.chart-container {
  height: 260px;
  background: var(--n-color);
  border: 1px solid var(--n-border-color);
  border-radius: var(--n-radius);
}
.result-table {
  margin-top: 8px;
  border: 1px solid var(--n-border-color);
  border-radius: var(--n-radius);
  overflow: hidden;
}
.result-table table { width: 100%; border-collapse: collapse; font-size: 12px; }
.result-table th { background: #f9fafb; padding: 6px 10px; text-align: left; font-weight: 600; border-bottom: 1px solid var(--n-border-color); }
.result-table td { padding: 4px 10px; border-bottom: 1px solid #f3f4f6; }
</style>
