<script setup lang="ts">
// ============================================================
// DataPreview — 数据预览表格，支持多 sheet 切换
// ============================================================

import { computed } from 'vue'

// === Props ===
const props = defineProps<{
  sheets: any[]        // SheetInfo 列表
  activeSheet: string   // 当前选中 sheet 名
}>()

// === Emits ===
const emit = defineEmits<{
  selectSheet: [sheetName: string]
}>()

const currentSheet = computed(() => {
  return props.sheets.find(s => s.name === props.activeSheet)
})
// === 计算属性 ===
  // 根据 activeSheet 返回列名数组
const columns = computed(() => currentSheet.value?.columns ?? [])

  // 根据 activeSheet 返回数据行（最多 100 行）
const rows = computed(() => currentSheet.value?.data ?? [])

  // 返回当前 sheet 总行数
const rowCount = computed(() => currentSheet.value?.row_count ?? 0)
</script>

<template>
  <div class="data-preview">
    <div class="preview-header">
      <span>Sheet:</span>
      <select
        :value="activeSheet"
        @change="emit('selectSheet', ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="s in sheets" :key="s.name" :value="s.name">
          {{ s.name }}
        </option>
      </select>
      <span class="row-count">{{ rowCount }} 行</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th v-for="col in columns" :key="col">{{ col }}</th>
          </tr>
        </thead>
        <tbody>
          
          <tr v-for="(row, i) in rows" :key="i">
            <td v-for="col in columns" :key="col">{{ row[col] }}</td>
          </tr>
         
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.data-preview {
  margin: 12px 18px 18px;
  border: 1px solid var(--n-border-color);
  border-radius: var(--n-radius);
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--n-border-color);
  font-size: 12px;
  color: var(--n-text-color-2);
}
.preview-header select {
  border: 1px solid var(--n-border-color);
  border-radius: 4px;
  padding: 3px 6px;
  font-size: 12px;
}
.row-count { margin-left: auto; }
.table-wrap {
  flex: 1;
  overflow: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
th {
  position: sticky;
  top: 0;
  background: #f9fafb;
  padding: 6px 10px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--n-border-color);
  white-space: nowrap;
}
td {
  padding: 5px 10px;
  border-bottom: 1px solid #f3f4f6;
  white-space: nowrap;
}
tr:hover td { background: #fafbff; }
</style>
