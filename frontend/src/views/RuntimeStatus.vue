<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">运行状态</h1>
        <p class="page-subtitle">核对当前模型、降级模式、数据库和向量索引的真实运行状态。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-alert
      v-if="status.embedding_fallback_active"
      title="Embedding 正在使用显式允许的 hash fallback，结果不能代表语义模型效果。"
      type="warning"
      show-icon
      :closable="false"
    />
    <el-alert
      v-if="status.llm_mode === 'mock'"
      title="LLM 当前为 mock 模式，生成内容是确定性演示模板。"
      type="info"
      show-icon
      :closable="false"
    />

    <div class="status-grid" v-loading="loading">
      <div class="panel panel-pad">
        <h2 class="section-title">Embedding</h2>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="Backend">{{ status.active_embedding_backend || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Model">{{ status.embedding_model || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Dimension">{{ status.embedding_dimension ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="Version">{{ status.embedding_version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Model loaded">
            <el-tag :type="status.embedding_model_loaded ? 'success' : 'info'">
              {{ status.embedding_model_loaded ? 'yes' : 'no' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Fallback">
            <el-tag :type="status.embedding_fallback_active ? 'warning' : 'success'">
              {{ status.embedding_fallback_active ? 'active' : 'inactive' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="panel panel-pad">
        <h2 class="section-title">LLM 与基础设施</h2>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="Provider">{{ status.llm_provider || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Mode">
            <el-tag :type="status.llm_mode === 'mock' ? 'warning' : 'success'">{{ status.llm_mode || '-' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Model">{{ status.llm_model || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Database">
            <el-tag :type="status.database_status === 'ok' ? 'success' : 'danger'">{{ status.database_status || '-' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="pgvector">
            <el-tag :type="status.pgvector_status === 'ok' ? 'success' : 'danger'">{{ status.pgvector_status || '-' }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

import { getRuntimeStatus } from '../api/system'

const loading = ref(false)
const status = reactive({})

const load = async () => {
  loading.value = true
  try {
    Object.assign(status, await getRuntimeStatus())
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 860px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
