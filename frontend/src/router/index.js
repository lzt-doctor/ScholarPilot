import { createRouter, createWebHistory } from 'vue-router'

import { authStore } from '../store/auth'


const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
  { path: '/register', name: 'register', component: () => import('../views/Register.vue') },
  {
    path: '/',
    component: () => import('../components/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'documents', name: 'documents', component: () => import('../views/Documents.vue') },
      { path: 'chat', name: 'chat', component: () => import('../views/Chat.vue') },
      { path: 'study-plan', name: 'studyPlan', component: () => import('../views/StudyPlan.vue') },
      { path: 'mistakes', name: 'mistakes', component: () => import('../views/Mistakes.vue') },
      { path: 'statistics', name: 'statistics', component: () => import('../views/Statistics.vue') },
      { path: 'runtime', name: 'runtime', component: () => import('../views/RuntimeStatus.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !authStore.token) return { name: 'login' }
  if ((to.name === 'login' || to.name === 'register') && authStore.token) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
