<template>
  <div class="page chat-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">AI 问答</h1>
        <p class="page-subtitle">对学术文档执行可配置检索，返回编号引用、证据强度和实际运行元数据。</p>
      </div>
      <el-button :icon="Refresh" @click="loadSessions">刷新会话</el-button>
    </div>

    <div class="chat-grid">
      <div class="panel panel-pad session-panel">
        <h2 class="section-title">问答会话</h2>
        <el-button type="primary" plain class="new-session" @click="newSession">新建会话</el-button>
        <div class="session-list">
          <div
            v-for="session in sessions"
            :key="session.id"
            :class="['session-item', { active: session.id === activeSessionId }]"
          >
            <button class="session-select" @click="selectSession(session.id)">
              <span>{{ session.title }}</span>
              <small>{{ formatTime(session.created_at) }}</small>
            </button>
            <el-button
              class="session-delete"
              :icon="Delete"
              :loading="deletingSessionId === session.id"
              circle
              text
              title="删除对话"
              aria-label="删除对话"
              @click.stop="confirmDeleteSession(session)"
            />
          </div>
        </div>
      </div>

      <div class="panel chat-panel">
        <div class="messages" ref="messageBoxRef">
          <div v-if="messages.length === 0" class="empty-chat">
            上传资料后提问，例如“这篇论文的核心贡献是什么？”
          </div>
          <div
            v-for="message in messages"
            :key="message.localId || message.id"
            :class="['message', message.role]"
          >
            <div class="bubble">
              <div v-if="message.role === 'assistant'" class="answer-meta">
                <el-tag size="small" :type="evidenceType(messageEvidence(message))">
                  证据强度：{{ evidenceLabel(messageEvidence(message)) }}
                </el-tag>
                <el-tag size="small" :type="citationType(message.citation_validity)">
                  引用{{ citationLabel(message.citation_validity) }}
                </el-tag>
                <el-tag v-if="message.runtime_metadata" size="small" type="info">
                  {{ message.runtime_metadata.retrieval_mode }} · {{ message.runtime_metadata.llm_mode }}
                </el-tag>
              </div>
              <div class="mono-block">{{ message.content }}</div>
              <div v-if="message.sources?.length" class="citations">
                <el-collapse>
                  <el-collapse-item title="来源引用" name="sources">
                    <div class="source-list">
                      <div v-for="(source, index) in message.sources" :key="sourceKey(source)" class="source-item">
                        <div class="source-meta">
                          <span>[{{ index + 1 }}] {{ source.document_name }} · 第 {{ source.page_number }} 页 · Chunk {{ source.chunk_index }}</span>
                          <span>{{ sourceScoreSummary(source) }}</span>
                        </div>
                        <div v-if="source.lexical_rank || source.vector_rank" class="source-ranks muted">
                          lexical rank {{ source.lexical_rank ?? '-' }} · vector rank {{ source.vector_rank ?? '-' }}
                        </div>
                        <div class="muted">{{ source.chunk_text }}</div>
                      </div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </div>
        </div>

        <div class="ask-bar">
          <div class="ask-inputs">
            <el-segmented v-model="retrievalMode" :options="retrievalOptions" />
            <el-input
              v-model="question"
              type="textarea"
              :rows="3"
              resize="none"
              placeholder="输入问题；证据不足时系统不会调用大模型"
              @keydown.enter.exact.prevent="ask"
            />
          </div>
          <el-button type="primary" :loading="asking" :icon="Promotion" @click="ask">
            发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { Delete, Promotion, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { deleteChatSession, getChatHistory, getChatSessions, sendQuestion } from '../api/chat'

const sessions = ref([])
const messages = ref([])
const activeSessionId = ref(null)
const question = ref('')
const retrievalMode = ref('hybrid')
const asking = ref(false)
const deletingSessionId = ref(null)
const messageBoxRef = ref()
const retrievalOptions = [
  { label: 'Hybrid', value: 'hybrid' },
  { label: 'HNSW', value: 'hnsw' },
  { label: 'Exact', value: 'exact' },
  { label: 'BM25', value: 'bm25' },
]

const loadSessions = async () => {
  sessions.value = await getChatSessions()
}

const loadHistory = async () => {
  if (!activeSessionId.value) {
    messages.value = []
    return
  }
  messages.value = await getChatHistory({ session_id: activeSessionId.value })
  await scrollToBottom()
}

const selectSession = async (id) => {
  activeSessionId.value = id
  await loadHistory()
}

const newSession = () => {
  activeSessionId.value = null
  messages.value = []
  question.value = ''
}

const confirmDeleteSession = async (session) => {
  try {
    await ElMessageBox.confirm(
      `确定删除对话「${session.title}」吗？删除后该会话的历史消息也会一起清除。`,
      '删除对话',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      },
    )
  } catch (error) {
    return
  }

  deletingSessionId.value = session.id
  try {
    await deleteChatSession(session.id)
    if (activeSessionId.value === session.id) {
      newSession()
    }
    await loadSessions()
    ElMessage.success('对话已删除')
  } finally {
    deletingSessionId.value = null
  }
}

const ask = async () => {
  const text = question.value.trim()
  if (!text) {
    ElMessage.warning('请输入问题')
    return
  }

  messages.value.push({ localId: Date.now(), role: 'user', content: text })
  question.value = ''
  asking.value = true
  await scrollToBottom()

  try {
    const result = await sendQuestion({
      question: text,
      session_id: activeSessionId.value,
      retrieval_mode: retrievalMode.value,
    })
    activeSessionId.value = result.session_id
    messages.value.push({
      localId: Date.now() + 1,
      role: 'assistant',
      content: result.answer,
      sources: result.sources,
      evidence_strength: result.evidence_strength,
      confidence: result.confidence,
      citation_validity: result.citation_validity,
      cited_source_ids: result.cited_source_ids,
      runtime_metadata: result.runtime_metadata,
    })
    await loadSessions()
    await scrollToBottom()
  } finally {
    asking.value = false
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messageBoxRef.value) {
    messageBoxRef.value.scrollTop = messageBoxRef.value.scrollHeight
  }
}

const sourceKey = (source) =>
  `${source.source_id ?? source.document_id}-${source.page_number}-${source.chunk_index}`
const formatTime = (value) => (value ? new Date(value).toLocaleDateString() : '-')

const formatScore = (value) => (value === null || value === undefined ? '-' : Number(value).toFixed(3))
const sourceScoreSummary = (source) => {
  const parts = []
  if (source.similarity !== null && source.similarity !== undefined) {
    parts.push(`similarity ${formatScore(source.similarity)}`)
  }
  if (source.fused_score !== null && source.fused_score !== undefined) {
    parts.push(`fused ${formatScore(source.fused_score)}`)
  }
  if (source.lexical_score !== null && source.lexical_score !== undefined) {
    parts.push(`BM25 ${formatScore(source.lexical_score)}`)
  }
  return parts.join(' · ') || 'score -'
}
const messageEvidence = (message) => {
  if (message.evidence_strength) return message.evidence_strength
  if (message.confidence) return message.confidence
  const similarities = message.sources?.map((source) => Number(source.relevance_score ?? source.similarity ?? source.score ?? 0)) || []
  if (!similarities.length || Math.max(...similarities) < 0.25) return 'low'
  const reliable = similarities.filter((value) => value >= 0.55)
  if (Math.max(...similarities) >= 0.72 && reliable.length >= 2) return 'high'
  if (Math.max(...similarities) >= 0.4 || reliable.length) return 'medium'
  return 'low'
}
const evidenceLabel = (value) => ({ high: '高', medium: '中', low: '低' })[value] || '低'
const evidenceType = (value) =>
  ({ high: 'success', medium: 'warning', low: 'info' })[value] || 'info'
const citationLabel = (value) => (value === true ? '已校验' : value === false ? '未通过校验' : '未记录')
const citationType = (value) => (value === true ? 'success' : value === false ? 'danger' : 'info')

onMounted(loadSessions)
</script>

<style scoped>
.chat-grid {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
  min-height: calc(100vh - 160px);
}

.session-panel {
  align-self: start;
}

.new-session {
  width: 100%;
  margin-bottom: 12px;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-item {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 34px;
  align-items: center;
  gap: 4px;
  padding: 6px 6px 6px 10px;
  border: 1px solid var(--sp-line);
  border-radius: 8px;
  background: #fff;
  color: var(--sp-ink);
}

.session-item.active {
  border-color: rgba(64, 88, 214, 0.45);
  background: rgba(64, 88, 214, 0.08);
}

.session-select {
  min-width: 0;
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.session-delete {
  justify-self: end;
  color: var(--sp-muted);
}

.session-delete:hover {
  color: #d03050;
}

.session-select span,
.session-select small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-select small {
  margin-top: 4px;
  color: var(--sp-muted);
}

.chat-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages {
  flex: 1;
  min-height: 440px;
  max-height: calc(100vh - 282px);
  overflow-y: auto;
  padding: 22px;
}

.empty-chat {
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--sp-muted);
  text-align: center;
}

.message {
  display: flex;
  margin-bottom: 14px;
}

.message.user {
  justify-content: flex-end;
}

.bubble {
  max-width: min(760px, 88%);
  padding: 14px 16px;
  border-radius: 8px;
  border: 1px solid var(--sp-line);
  background: #fff;
}

.message.user .bubble {
  color: #fff;
  background: var(--sp-indigo);
  border-color: var(--sp-indigo);
}

.citations {
  margin-top: 12px;
}

.answer-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.ask-bar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 104px;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid var(--sp-line);
  background: #fbfcff;
}

.ask-inputs {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-ranks {
  margin: -2px 0 8px;
  font-size: 12px;
}

@media (max-width: 900px) {
  .chat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
