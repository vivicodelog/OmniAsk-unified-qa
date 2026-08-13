<script setup lang="ts">
// ============================================================
// ChartPanel — ECharts 图表渲染，根据 chart_type 切换
// ============================================================

import { ref, computed } from 'vue'
// ECharts 按需引入（tree-shaking，只打包用到的图表类型）
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, LineChart, BarChart, ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  PieChart, LineChart, BarChart, ScatterChart,
  GridComponent, TooltipComponent, LegendComponent,
])

// === Props ===
const props = defineProps<{
  chartType: string    // "pie" | "line" | "bar" | "scatter" | "table"
  data: any[]          // 查询结果数据
  sql: string          // 生成的 SQL（供展示）
}>()

// === 状态 ===
const sqlVisible = ref(false)

// === 计算属性 ===
const columnKeys = computed(() => {
  if (props.data.length === 0) return []
  return Object.keys(props.data[0])
})

// 数据 → ECharts option 的映射。
// 约定：查询结果第一列是「分类/名称」，第二列是「数值」。
// 这符合后端 NL2SQL 生成 GROUP BY 查询的常见形态（如 `SELECT 地区, SUM(销售额)`）。
const option = computed(() => {
  if (!props.data?.length) return null
  const keys = Object.keys(props.data[0])
  const labelKey = keys[0]
  const valueKey = keys[1] ?? keys[0]   // 只有一列时退化，仍能画

  const labels = props.data.map(r => r[labelKey])
  const values = props.data.map(r => r[valueKey])

  switch (props.chartType) {
    case 'pie':
      return {
        tooltip: { trigger: 'item' },
        legend: { bottom: 0 },
        series: [{
          type: 'pie',
          radius: ['40%', '68%'],
          center: ['50%', '45%'],
          data: props.data.map(r => ({ name: r[labelKey], value: r[valueKey] })),
          label: { formatter: '{b}: {d}%' },
        }],
      }

    case 'line':
      return {
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', data: labels, boundaryGap: false },
        yAxis: { type: 'value' },
        series: [{ type: 'line', data: values, smooth: true, areaStyle: { opacity: 0.08 } }],
      }

    case 'bar':
      return {
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', data: labels, axisLabel: { interval: 0, rotate: labels.length > 6 ? 30 : 0 } },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: values, barMaxWidth: 40 }],
      }

    case 'scatter':
      return {
        tooltip: { trigger: 'item' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'value', name: labelKey },
        yAxis: { type: 'value', name: valueKey },
        series: [{
          type: 'scatter',
          data: props.data.map(r => [r[labelKey], r[valueKey]]),
          symbolSize: 10,
        }],
      }

    default: // "table" 或未知类型 → 不画图，只展示下方表格
      return null
  }
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
    <div class="chart-container">
      <VChart
        v-if="option"
        class="chart"
        :option="option"
        autoresize
      />
      <div v-else class="chart-empty">表格型结果，见下方数据</div>
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
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.chart { width: 100%; height: 100%; }
.chart-empty {
  font-size: 13px;
  color: var(--n-text-color-2);
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
