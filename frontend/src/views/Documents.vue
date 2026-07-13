<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">文档管理</h1>
        <p class="page-subtitle">上传 PDF 后进行解析、切分和向量索引，并记录可追溯的模型版本与索引状态。</p>
      </div>
      <el-button :icon="Refresh" @click="loadDocuments">刷新</el-button>
    </div>

    <div class="panel panel-pad">
      <div class="upload-row">
        <el-input v-model="category" placeholder="资料分类，如 AI / 软件工程 / 算法" clearable />
        <el-upload
          :show-file-list="false"
          accept=".pdf"
          :http-request="handleUpload"
          :disabled="uploading"
        >
          <el-button type="primary" :loading="uploading" :icon="Upload">
            上传 PDF
          </el-button>
        </el-upload>
      </div>
    </div>

    <div class="panel panel-pad">
      <h2 class="section-title">已上传文档</h2>
      <el-table :data="documents" v-loading="loading" empty-text="暂无文档">
        <el-table-column prop="filename" label="文件名" min-width="220" />
        <el-table-column prop="category" label="分类" width="140" />
        <el-table-column label="索引状态" width="130">
          <template #default="{ row }">
            <el-tag :type="indexStatusType(row.indexing_status)" size="small">
              {{ indexStatusLabel(row.indexing_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Embedding" min-width="230">
          <template #default="{ row }">
            <div class="model-cell">{{ row.embedding_model }}</div>
            <small class="muted">dim {{ row.embedding_dimension }} · v{{ row.embedding_version }}</small>
          </template>
        </el-table-column>
        <el-table-column label="摘要" min-width="260">
          <template #default="{ row }">
            <span class="muted">{{ row.summary || '暂无摘要' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="190">
          <template #default="{ row }">{{ formatTime(row.upload_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" :icon="View" @click="openDetail(row.id)">查看</el-button>
            <el-button
              text
              type="warning"
              :icon="RefreshRight"
              :loading="reindexingId === row.id"
              @click="reindex(row)"
            >重新索引</el-button>
            <el-button text type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="detailVisible" title="文档切分详情" width="760px">
      <div v-if="detail">
        <h3 class="detail-title">{{ detail.filename }}</h3>
        <p class="muted">{{ detail.summary }}</p>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="索引状态">{{ indexStatusLabel(detail.indexing_status) }}</el-descriptions-item>
          <el-descriptions-item label="Embedding 维度">{{ detail.embedding_dimension }}</el-descriptions-item>
          <el-descriptions-item label="模型">{{ detail.embedding_model }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ detail.embedding_version }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <el-timeline>
          <el-timeline-item
            v-for="chunk in detail.chunks"
            :key="chunk.id"
            :timestamp="`第 ${chunk.page_number} 页 / Chunk ${chunk.chunk_index}`"
          >
            <strong>{{ chunk.section_title || '资料片段' }}</strong>
            <p class="chunk-text">{{ chunk.chunk_text }}</p>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Delete, Refresh, RefreshRight, Upload, View } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  deleteDocument,
  getDocument,
  listDocuments,
  reindexDocument,
  uploadDocument,
} from '../api/documents'

const documents = ref([])
const detail = ref(null)
const detailVisible = ref(false)
const loading = ref(false)
const uploading = ref(false)
const category = ref('未分类')
const reindexingId = ref(null)

const loadDocuments = async () => {
  loading.value = true
  try {
    documents.value = await listDocuments()
  } finally {
    loading.value = false
  }
}

const handleUpload = async ({ file, onSuccess, onError }) => {
  uploading.value = true
  try {
    await uploadDocument(file, category.value || '未分类')
    ElMessage.success('上传与索引完成')
    onSuccess()
    await loadDocuments()
  } catch (error) {
    onError(error)
  } finally {
    uploading.value = false
  }
}

const openDetail = async (id) => {
  detail.value = await getDocument(id)
  detailVisible.value = true
}

const remove = async (row) => {
  await ElMessageBox.confirm(`确定删除 ${row.filename}？`, '删除文档', { type: 'warning' })
  await deleteDocument(row.id)
  ElMessage.success('已删除')
  await loadDocuments()
}

const reindex = async (row) => {
  reindexingId.value = row.id
  try {
    await reindexDocument(row.id)
    ElMessage.success('重新索引完成')
    await loadDocuments()
  } finally {
    reindexingId.value = null
  }
}

const indexStatusLabel = (value) =>
  ({
    pending: '等待中',
    processing: '处理中',
    ready: '可检索',
    failed: '失败',
    requires_reindex: '需重新索引',
  })[value] || value || '未知'
const indexStatusType = (value) =>
  ({ ready: 'success', processing: 'warning', failed: 'danger', requires_reindex: 'warning' })[value] || 'info'

const formatTime = (value) => (value ? new Date(value).toLocaleString() : '-')

onMounted(loadDocuments)
</script>

<style scoped>
.upload-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.detail-title {
  margin: 0 0 6px;
}

.chunk-text {
  margin: 8px 0 0;
  color: #344054;
  line-height: 1.7;
  white-space: pre-wrap;
}

.model-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 720px) {
  .upload-row {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
