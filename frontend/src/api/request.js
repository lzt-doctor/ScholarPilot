import axios from 'axios'
import { ElMessage } from 'element-plus'

import { authStore } from '../store/auth'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000,
})

request.interceptors.request.use((config) => {
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail || error.message || '请求失败'
    if (status === 401) {
      authStore.clear()
    }
    const message = Array.isArray(detail)
      ? detail[0]?.msg || '参数错误'
      : typeof detail === 'object'
        ? detail.message || detail.code || '请求失败'
        : detail
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default request
