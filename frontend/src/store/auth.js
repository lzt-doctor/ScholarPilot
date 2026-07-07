import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

import { login as loginApi, me as meApi, register as registerApi } from '../api/auth'

const tokenKey = 'scholarpilot_token'

export const authStore = reactive({
  token: localStorage.getItem(tokenKey) || '',
  user: null,
  setToken(token) {
    this.token = token
    localStorage.setItem(tokenKey, token)
  },
  clear() {
    this.token = ''
    this.user = null
    localStorage.removeItem(tokenKey)
  },
  async login(payload) {
    const result = await loginApi(payload)
    this.setToken(result.access_token)
    await this.fetchMe()
  },
  async register(payload) {
    await registerApi(payload)
    ElMessage.success('注册成功，请登录')
  },
  async fetchMe() {
    if (!this.token) return null
    this.user = await meApi()
    return this.user
  },
})

