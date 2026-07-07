import { createRouter, createWebHistory } from 'vue-router'

import { authStore } from '../store/auth'
import AppLayout from '../components/AppLayout.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Dashboard from '../views/Dashboard.vue'
import Documents from '../views/Documents.vue'
import Chat from '../views/Chat.vue'
import StudyPlan from '../views/StudyPlan.vue'
import Mistakes from '../views/Mistakes.vue'
import Statistics from '../views/Statistics.vue'

const routes = [
  { path: '/login', name: 'login', component: Login },
  { path: '/register', name: 'register', component: Register },
  {
    path: '/',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: Dashboard },
      { path: 'documents', name: 'documents', component: Documents },
      { path: 'chat', name: 'chat', component: Chat },
      { path: 'study-plan', name: 'studyPlan', component: StudyPlan },
      { path: 'mistakes', name: 'mistakes', component: Mistakes },
      { path: 'statistics', name: 'statistics', component: Statistics },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !authStore.token) {
    return { name: 'login' }
  }
  if ((to.name === 'login' || to.name === 'register') && authStore.token) {
    return { name: 'dashboard' }
  }
  return true
})

export default router

