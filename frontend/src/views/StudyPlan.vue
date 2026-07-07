<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">学习计划</h1>
        <p class="page-subtitle">由 StudyPlannerAgent 根据目标、基础和时间投入生成阶段化计划。</p>
      </div>
    </div>

    <div class="two-column">
      <div class="panel panel-pad">
        <h2 class="section-title">生成新计划</h2>
        <el-form label-position="top" :model="form">
          <el-form-item label="学习目标">
            <el-input
              v-model="form.goal"
              type="textarea"
              :rows="4"
              placeholder="例如：8 周内完成 RAG、向量数据库和 FastAPI 项目复盘，为 AI 方向研究生面试做准备"
            />
          </el-form-item>
          <el-form-item label="当前基础">
            <el-input
              v-model="form.background"
              type="textarea"
              :rows="3"
              placeholder="可填写课程背景、项目经验、薄弱点"
            />
          </el-form-item>
          <div class="form-row">
            <el-form-item label="周期（周）">
              <el-input-number v-model="form.weeks" :min="1" :max="52" />
            </el-form-item>
            <el-form-item label="每周小时">
              <el-input-number v-model="form.hours_per_week" :min="1" :max="80" />
            </el-form-item>
          </div>
          <el-button type="primary" :loading="loading" :icon="MagicStick" @click="generate">
            生成计划
          </el-button>
        </el-form>
      </div>

      <div class="panel panel-pad">
        <h2 class="section-title">最新计划</h2>
        <div v-if="latestPlan" class="mono-block">{{ latestPlan.plan_content }}</div>
        <el-empty v-else description="暂无学习计划" />
      </div>
    </div>

    <div class="panel panel-pad">
      <h2 class="section-title">历史计划</h2>
      <el-timeline>
        <el-timeline-item
          v-for="plan in plans"
          :key="plan.id"
          :timestamp="formatTime(plan.created_at)"
        >
          <strong>{{ plan.goal }}</strong>
          <p class="mono-block history-plan">{{ plan.plan_content }}</p>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { generateStudyPlan, listStudyPlans } from '../api/studyPlan'

const form = reactive({
  goal: '',
  background: '',
  weeks: 8,
  hours_per_week: 10,
})
const plans = ref([])
const loading = ref(false)
const latestPlan = computed(() => plans.value[0])

const load = async () => {
  plans.value = await listStudyPlans()
}

const generate = async () => {
  if (!form.goal.trim()) {
    ElMessage.warning('请填写学习目标')
    return
  }
  loading.value = true
  try {
    await generateStudyPlan(form)
    ElMessage.success('计划已生成')
    await load()
  } finally {
    loading.value = false
  }
}

const formatTime = (value) => (value ? new Date(value).toLocaleString() : '-')

onMounted(load)
</script>

<style scoped>
.form-row {
  display: flex;
  gap: 18px;
}

.history-plan {
  max-height: 180px;
  overflow: auto;
}

@media (max-width: 720px) {
  .form-row {
    flex-direction: column;
  }
}
</style>

