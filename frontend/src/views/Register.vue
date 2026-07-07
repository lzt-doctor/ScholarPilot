<template>
  <div class="auth-page">
    <div class="auth-panel">
      <div class="brand-lockup">
        <span class="brand-mark">S</span>
        <span>创建 ScholarPilot 账号</span>
      </div>
      <p class="page-subtitle">用于保存资料库、问答历史、错题和学习计划</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="auth-form">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" :prefix-icon="Message" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="full-button" @click="submit">
          注册
        </el-button>
      </el-form>

      <div class="auth-link">
        已有账号？
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Lock, Message, User } from '@element-plus/icons-vue'

import { authStore } from '../store/auth'

const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', email: '', password: '' })

const rules = {
  username: [{ required: true, min: 3, message: '用户名至少 3 位', trigger: 'blur' }],
  email: [{ required: true, type: 'email', message: '请输入有效邮箱', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }],
}

const submit = async () => {
  await formRef.value.validate()
  loading.value = true
  try {
    await authStore.register(form)
    router.push('/login')
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

