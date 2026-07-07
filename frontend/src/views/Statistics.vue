<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">数据统计</h1>
        <p class="page-subtitle">用 ECharts 展示资料数量、错题分布和学习资产沉淀情况。</p>
      </div>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
    </div>

    <div class="kpi-grid">
      <div v-for="item in kpis" :key="item.label" class="kpi-card">
        <div class="kpi-label">{{ item.label }}</div>
        <div class="kpi-value">{{ item.value }}</div>
      </div>
    </div>

    <div class="two-column">
      <div class="panel panel-pad">
        <h2 class="section-title">错题主题分布</h2>
        <div ref="subjectChartRef" class="chart"></div>
      </div>
      <div class="panel panel-pad">
        <h2 class="section-title">知识点薄弱分布</h2>
        <div ref="pointChartRef" class="chart"></div>
      </div>
    </div>

    <div class="panel panel-pad">
      <h2 class="section-title">资料分类数量</h2>
      <div ref="docChartRef" class="chart"></div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

import { getDashboardSummary } from '../api/dashboard'
import { getMistakeStatistics } from '../api/mistakes'

const summary = reactive({
  documents_count: 0,
  chunks_count: 0,
  chat_sessions_count: 0,
  mistakes_count: 0,
  study_plans_count: 0,
  documents_by_category: [],
})
const mistakes = reactive({ by_subject: [], by_knowledge_point: [], total: 0 })

const subjectChartRef = ref()
const pointChartRef = ref()
const docChartRef = ref()
let subjectChart
let pointChart
let docChart

const kpis = computed(() => [
  { label: '文档', value: summary.documents_count },
  { label: 'Chunk', value: summary.chunks_count },
  { label: '会话', value: summary.chat_sessions_count },
  { label: '错题', value: summary.mistakes_count },
  { label: '计划', value: summary.study_plans_count },
])

const load = async () => {
  const [summaryData, mistakeData] = await Promise.all([
    getDashboardSummary(),
    getMistakeStatistics(),
  ])
  Object.assign(summary, summaryData)
  Object.assign(mistakes, mistakeData)
  await nextTick()
  render()
}

const render = () => {
  subjectChart = subjectChart || echarts.init(subjectChartRef.value)
  pointChart = pointChart || echarts.init(pointChartRef.value)
  docChart = docChart || echarts.init(docChartRef.value)

  const subjectData = mistakes.by_subject.length
    ? mistakes.by_subject
    : [{ name: '暂无错题', value: 1 }]
  const pointData = mistakes.by_knowledge_point.length
    ? mistakes.by_knowledge_point
    : [{ name: '暂无知识点', value: 1 }]
  const docData = summary.documents_by_category.length
    ? summary.documents_by_category
    : [{ name: '暂无资料', value: 0 }]

  subjectChart.setOption({
    tooltip: { trigger: 'item' },
    color: ['#4058d6', '#0f9f95', '#d94b5f', '#d99018'],
    series: [{ type: 'pie', radius: '68%', data: subjectData }],
  })

  pointChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 16, top: 20, bottom: 46 },
    xAxis: { type: 'category', data: pointData.map((item) => item.name), axisLabel: { rotate: 22 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'bar',
        data: pointData.map((item) => item.value),
        itemStyle: { color: '#0f9f95', borderRadius: [6, 6, 0, 0] },
      },
    ],
  })

  docChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 16, top: 20, bottom: 36 },
    xAxis: { type: 'category', data: docData.map((item) => item.name) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'bar',
        data: docData.map((item) => item.value),
        itemStyle: { color: '#4058d6', borderRadius: [6, 6, 0, 0] },
      },
    ],
  })
}

const resize = () => {
  subjectChart?.resize()
  pointChart?.resize()
  docChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', resize)
})

onUnmounted(() => {
  window.removeEventListener('resize', resize)
  subjectChart?.dispose()
  pointChart?.dispose()
  docChart?.dispose()
})
</script>

