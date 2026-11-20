import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue')
  },
  {
    path: '/analyze',
    name: 'analyze',
    component: () => import('../views/AnalyzeView.vue')
  },
  {
    path: '/batch',
    name: 'batch',
    component: () => import('../views/BatchView.vue')
  },
  {
    path: '/report/:id?',
    name: 'report',
    component: () => import('../views/ReportView.vue')
  }
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})
