<template>
  <div class="page chat-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">AI 问答</h1>
        <p class="page-subtitle">基于已上传资料进行向量检索，并返回带来源引用的 RAG 回答。</p>
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
                <el-tag size="small" :type="confidenceType(messageConfidence(message))">
                  可信度：{{ confidenceLabel(messageConfidence(message)) }}
                </el-tag>
              </div>
              <div class="mono-block">{{ message.content }}</div>
              <div v-if="message.sources?.length" class="citations">
                <el-collapse>
                  <el-collapse-item title="来源引用" name="sources">
                    <div class="source-list">
                      <div v-for="source in message.sources" :key="sourceKey(source)" class="source-item">
                        <div class="source-meta">
                          <span>{{ source.document_name }} · 第 {{ source.page_number }} 页 · Chunk {{ source.chunk_index }}</span>
                          <span>similarity {{ sourceSimilarity(source) }}</span>
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
          <el-input
            v-model="question"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="输入你的问题，系统会检索 Top-K 文档片段并生成回答"
            @keydown.enter.exact.prevent="ask"
          />
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
const asking = ref(false)
const deletingSessionId = ref(null)
const messageBoxRef = ref()

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
    const result = await sendQuestion({ question: text, session_id: activeSessionId.value })
    activeSessionId.value = result.session_id
    messages.value.push({
      localId: Date.now() + 1,
      role: 'assistant',
      content: result.answer,
      sources: result.sources,
      confidence: result.confidence,
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
  `${source.document_id}-${source.page_number}-${source.chunk_index}-${source.similarity ?? source.score}`
const formatTime = (value) => (value ? new Date(value).toLocaleDateString() : '-')

const sourceSimilarity = (source) => Number(source.similarity ?? source.score ?? 0).toFixed(2)
const messageConfidence = (message) => {
  if (message.confidence) return message.confidence
  const similarities = message.sources?.map((source) => Number(source.similarity ?? source.score ?? 0)) || []
  if (!similarities.length || Math.max(...similarities) < 0.25) return 'low'
  const reliable = similarities.filter((value) => value >= 0.55)
  if (Math.max(...similarities) >= 0.72 && reliable.length >= 2) return 'high'
  if (Math.max(...similarities) >= 0.4 || reliable.length) return 'medium'
  return 'low'
}
const confidenceLabel = (confidence) =>
  ({ high: '高', medium: '中', low: '低' })[confidence] || '低'
const confidenceType = (confidence) =>
  ({ high: 'success', medium: 'warning', low: 'info' })[confidence] || 'info'

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

@media (max-width: 900px) {
  .chat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
