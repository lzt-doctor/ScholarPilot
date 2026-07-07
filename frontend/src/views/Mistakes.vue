<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">错题分析</h1>
        <p class="page-subtitle">MistakeAnalysisAgent 自动总结错因和知识点，沉淀复盘数据。</p>
      </div>
      <el-button :icon="Refresh" @click="loadAll">刷新</el-button>
    </div>

    <div class="two-column">
      <div class="panel panel-pad">
        <h2 class="section-title">记录错题</h2>
        <el-form label-position="top" :model="form">
          <el-form-item label="学科/主题">
            <el-input v-model="form.subject" placeholder="例如：算法 / 深度学习 / 数据库" />
          </el-form-item>
          <el-form-item label="题目">
            <el-input v-model="form.question_text" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="我的答案">
            <el-input v-model="form.user_answer" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="正确答案">
            <el-input v-model="form.correct_answer" type="textarea" :rows="2" />
          </el-form-item>
          <el-button type="primary" :loading="loading" :icon="DocumentAdd" @click="submit">
            保存并分析
          </el-button>
        </el-form>
      </div>

      <div class="panel panel-pad">
        <h2 class="section-title">统计概览</h2>
        <div class="kpi-card stat-total">
          <div class="kpi-label">错题总数</div>
          <div class="kpi-value">{{ statistics.total }}</div>
        </div>
        <el-divider />
        <el-tag
          v-for="item in statistics.by_knowledge_point"
          :key="item.name"
          class="point-tag"
          type="warning"
          effect="plain"
        >
          {{ item.name }} × {{ item.value }}
        </el-tag>
      </div>
    </div>

    <div class="panel panel-pad">
      <h2 class="section-title">错题记录</h2>
      <el-table :data="mistakes" empty-text="暂无错题">
        <el-table-column prop="subject" label="主题" width="120" />
        <el-table-column prop="question_text" label="题目" min-width="220" show-overflow-tooltip />
        <el-table-column prop="error_reason" label="错因" min-width="260" />
        <el-table-column prop="knowledge_point" label="知识点" width="160" />
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { DocumentAdd, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { createMistake, getMistakeStatistics, listMistakes } from '../api/mistakes'

const form = reactive({
  subject: '',
  question_text: '',
  user_answer: '',
  correct_answer: '',
})
const mistakes = ref([])
const loading = ref(false)
const statistics = reactive({ by_subject: [], by_knowledge_point: [], total: 0 })

const loadAll = async () => {
  const [records, stats] = await Promise.all([listMistakes(), getMistakeStatistics()])
  mistakes.value = records
  Object.assign(statistics, stats)
}

const submit = async () => {
  if (!form.subject || !form.question_text || !form.user_answer || !form.correct_answer) {
    ElMessage.warning('请完整填写错题信息')
    return
  }
  loading.value = true
  try {
    await createMistake(form)
    Object.assign(form, { subject: '', question_text: '', user_answer: '', correct_answer: '' })
    ElMessage.success('错题已分析')
    await loadAll()
  } finally {
    loading.value = false
  }
}

const formatTime = (value) => (value ? new Date(value).toLocaleString() : '-')

onMounted(loadAll)
</script>

<style scoped>
.stat-total {
  box-shadow: none;
}

.point-tag {
  margin: 0 8px 8px 0;
}
</style>

