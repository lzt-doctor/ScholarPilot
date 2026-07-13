<template>
  <el-container class="app-shell">
    <el-aside class="sidebar" width="248px">
      <div class="sidebar-brand">
        <span class="brand-mark">S</span>
        <div>
          <div class="brand-title">ScholarPilot</div>
          <div class="brand-caption">Traceable RAG Workspace</div>
        </div>
      </div>

      <el-menu :default-active="$route.path" router class="side-menu">
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>首页总览</span>
        </el-menu-item>
        <el-menu-item index="/documents">
          <el-icon><FolderOpened /></el-icon>
          <span>文档管理</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 问答</span>
        </el-menu-item>
        <el-menu-item index="/study-plan">
          <el-icon><Calendar /></el-icon>
          <span>学习计划</span>
        </el-menu-item>
        <el-menu-item index="/mistakes">
          <el-icon><CircleCloseFilled /></el-icon>
          <span>错题分析</span>
        </el-menu-item>
        <el-menu-item index="/statistics">
          <el-icon><TrendCharts /></el-icon>
          <span>数据统计</span>
        </el-menu-item>
        <el-menu-item index="/runtime">
          <el-icon><Monitor /></el-icon>
          <span>运行状态</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div>
          <strong>ScholarPilot</strong>
          <span class="topbar-subtitle">可追溯学术文档 RAG 系统</span>
        </div>
        <div class="topbar-user">
          <el-icon><User /></el-icon>
          <span>{{ authStore.user?.username || 'Applicant' }}</span>
          <el-button :icon="SwitchButton" text @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Calendar,
  ChatDotRound,
  CircleCloseFilled,
  DataBoard,
  FolderOpened,
  Monitor,
  SwitchButton,
  TrendCharts,
  User,
} from '@element-plus/icons-vue'

import { authStore } from '../store/auth'

const router = useRouter()

onMounted(() => {
  if (!authStore.user && authStore.token) {
    authStore.fetchMe().catch(() => authStore.clear())
  }
})

const logout = () => {
  authStore.clear()
  router.push('/login')
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--sp-bg);
}

.sidebar {
  background: #ffffff;
  border-right: 1px solid var(--sp-line);
}

.sidebar-brand {
  height: 74px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  border-bottom: 1px solid var(--sp-line);
}

.brand-title {
  font-size: 18px;
  font-weight: 800;
}

.brand-caption {
  margin-top: 3px;
  color: var(--sp-muted);
  font-size: 12px;
}

.side-menu {
  border-right: none;
  padding: 10px 8px;
}

.side-menu :deep(.el-menu-item) {
  height: 44px;
  border-radius: 8px;
  margin: 4px 0;
  color: #41506a;
}

.side-menu :deep(.el-menu-item.is-active) {
  color: var(--sp-indigo);
  background: rgba(64, 88, 214, 0.09);
  font-weight: 700;
}

.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid var(--sp-line);
  backdrop-filter: blur(10px);
}

.topbar-subtitle {
  margin-left: 12px;
  color: var(--sp-muted);
  font-size: 13px;
}

.topbar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #3d4b63;
}

.content {
  padding: 24px;
}

@media (max-width: 860px) {
  .sidebar {
    width: 76px !important;
  }

  .sidebar-brand div,
  .side-menu :deep(.el-menu-item span),
  .topbar-subtitle {
    display: none;
  }

  .topbar-user > span {
    display: none;
  }

  .topbar {
    padding: 0 12px;
  }
}
</style>
