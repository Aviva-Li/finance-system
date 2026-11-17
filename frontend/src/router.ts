import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { session } from './state'
import AppLayout from './layout/AppLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('./views/LoginView.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', redirect: '/dashboard' },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('./views/DashboardView.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'transactions',
        name: 'transactions',
        component: () => import('./views/TransactionsView.vue'),
        meta: { title: '流水记录' },
      },
      {
        path: 'accounts',
        name: 'accounts',
        component: () => import('./views/AccountsView.vue'),
        meta: { title: '账户管理' },
      },
      {
        path: 'allocation',
        name: 'allocation',
        component: () => import('./views/AllocationView.vue'),
        meta: { title: '七账户分配' },
      },
      {
        path: 'categories',
        name: 'categories',
        component: () => import('./views/CategoriesView.vue'),
        meta: { title: '收支分类' },
      },
      {
        path: 'reports',
        name: 'reports',
        component: () => import('./views/ReportsView.vue'),
        meta: { title: '统计报表' },
      },
      {
        path: 'settings',
        name: 'settings',
        component: () => import('./views/SettingsView.vue'),
        meta: { title: '系统设置' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 未登录一律回登录页（防止局域网其他人直接打开）
router.beforeEach((to) => {
  if (to.name !== 'login' && !session.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && session.token) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
