<template>
  <div class="auth-page">
    <div class="auth-panel">
      <div class="brand-lockup">
        <span class="brand-mark">S</span>
        <span>ScholarPilot</span>
      </div>
      <p class="page-subtitle">登录后进入 Agentic RAG 学术工作台</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="auth-form">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="full-button" @click="submit">
          登录
        </el-button>
      </el-form>

      <div class="auth-link">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Lock, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { authStore } from '../store/auth'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const submit = async () => {
  await formRef.value.validate()
  loading.value = true
  try {
    await authStore.login(form)
    ElMessage.success('欢迎回来')
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-form {
  margin-top: 24px;
}

.full-button {
  width: 100%;
  height: 42px;
}

.auth-link {
  margin-top: 18px;
  text-align: center;
  color: var(--sp-muted);
  font-size: 14px;
}

.auth-link a {
  color: var(--sp-indigo);
  font-weight: 700;
}
</style>

