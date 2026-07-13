<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">首页总览</h1>
        <p class="page-subtitle">查看知识库、RAG 问答、学习计划和错题复盘的整体状态。</p>
      </div>
      <el-button type="primary" :icon="Upload" @click="$router.push('/documents')">
        上传资料
      </el-button>
    </div>

    <div class="kpi-grid">
      <div v-for="item in kpis" :key="item.label" class="kpi-card">
        <div class="kpi-label">{{ item.label }}</div>
        <div class="kpi-value">{{ item.value }}</div>
      </div>
    </div>

    <div class="two-column">
      <div class="panel panel-pad">
        <h2 class="section-title">最近上传资料</h2>
        <el-table :data="summary.recent_documents" empty-text="暂无资料">
          <el-table-column prop="filename" label="文件名" min-width="180" />
          <el-table-column prop="category" label="分类" width="130" />
          <el-table-column label="上传时间" width="190">
            <template #default="{ row }">{{ formatTime(row.upload_time) }}</template>
          </el-table-column>
        </el-table>
      </div>

      <div class="panel panel-pad">
        <h2 class="section-title">资料分类</h2>
        <div ref="docChartRef" class="chart"></div>
      </div>
    </div>

    <div class="two-column">
      <div class="panel panel-pad">
        <h2 class="section-title">RAG 演示路径</h2>
        <el-steps :active="3" finish-status="success" align-center>
          <el-step title="上传 PDF" />
          <el-step title="解析切分" />
          <el-step title="向量检索" />
          <el-step title="引用回答" />
        </el-steps>
      </div>

      <div class="panel panel-pad">
        <h2 class="section-title">错题学科分布</h2>
        <div ref="mistakeChartRef" class="chart small-chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { init, use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

import { getDashboardSummary } from '../api/dashboard'

use([BarChart, PieChart, GridComponent, TooltipComponent, CanvasRenderer])

const summary = reactive({
  documents_count: 0,
  chunks_count: 0,
  chat_sessions_count: 0,
  mistakes_count: 0,
  study_plans_count: 0,
  recent_documents: [],
  mistakes_by_subject: [],
  documents_by_category: [],
})

const docChartRef = ref()
const mistakeChartRef = ref()
let docChart
let mistakeChart

const kpis = computed(() => [
  { label: '资料数量', value: summary.documents_count },
  { label: '切分 Chunk', value: summary.chunks_count },
  { label: '问答会话', value: summary.chat_sessions_count },
  { label: '错题记录', value: summary.mistakes_count },
  { label: '学习计划', value: summary.study_plans_count },
])

const load = async () => {
  const data = await getDashboardSummary()
  Object.assign(summary, data)
  await nextTick()
  renderCharts()
}

const renderCharts = () => {
  docChart = docChart || init(docChartRef.value)
  mistakeChart = mistakeChart || init(mistakeChartRef.value)

  docChart.setOption({
    tooltip: { trigger: 'item' },
    color: ['#4058d6', '#0f9f95', '#d99018', '#6b7a99'],
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        data: summary.documents_by_category.length
          ? summary.documents_by_category
          : [{ name: '暂无资料', value: 1 }],
      },
    ],
  })

  mistakeChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 34, right: 12, top: 18, bottom: 34 },
    xAxis: { type: 'category', data: summary.mistakes_by_subject.map((item) => item.name) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'bar',
        data: summary.mistakes_by_subject.map((item) => item.value),
        itemStyle: { color: '#d94b5f', borderRadius: [6, 6, 0, 0] },
      },
    ],
  })
}

const formatTime = (value) => (value ? new Date(value).toLocaleString() : '-')
const resize = () => {
  docChart?.resize()
  mistakeChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', resize)
})

onUnmounted(() => {
  window.removeEventListener('resize', resize)
  docChart?.dispose()
  mistakeChart?.dispose()
})
</script>

<style scoped>
.small-chart {
  height: 220px;
}
</style>
