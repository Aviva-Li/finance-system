<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearToken } from '../state'

const route = useRoute()
const router = useRouter()

const menus = [
  { name: 'dashboard', label: '仪表盘', icon: 'Odometer' },
  { name: 'transactions', label: '流水记录', icon: 'Tickets' },
  { name: 'accounts', label: '账户管理', icon: 'Wallet' },
  { name: 'allocation', label: '七账户分配', icon: 'PieChart' },
  { name: 'categories', label: '收支分类', icon: 'PriceTag' },
  { name: 'reports', label: '统计报表', icon: 'TrendCharts' },
  { name: 'settings', label: '系统设置', icon: 'Setting' },
]

const title = computed(() => (route.meta.title as string) || '个人理财账本')

function logout() {
  clearToken()
  router.replace({ name: 'login' })
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">¥</div>
        <div>
          <div class="brand-name">理财账本</div>
          <div class="brand-sub">跨设备同步</div>
        </div>
      </div>
      <nav class="nav">
        <router-link v-for="m in menus" :key="m.name" :to="{ name: m.name }" class="nav-item">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </router-link>
      </nav>
      <div class="side-foot">
        <div>数据存储于本机 SQLite</div>
        <div>局域网多端可用</div>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="page-title">{{ title }}</div>
        <div class="top-actions">
          <span class="date-hint">{{ new Date().toLocaleDateString('zh-CN') }}</span>
          <el-button text @click="logout">
            <el-icon class="btn-icon"><SwitchButton /></el-icon>
            退出
          </el-button>
        </div>
      </header>

      <nav class="mobile-tabs">
        <router-link v-for="m in menus" :key="m.name" :to="{ name: m.name }" class="tab">
          {{ m.label }}
        </router-link>
      </nav>

      <main>
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 216px;
  flex: 0 0 216px;
  background: #253531;
  color: #dfe8e4;
  padding: 22px 14px 18px;
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px 22px;
}

.brand-logo {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 17px;
  color: #d8ece3;
}

.brand-name {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 0.5px;
}

.brand-sub {
  font-size: 11px;
  color: #93a8a0;
  margin-top: 2px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  color: #c3d2cc;
  text-decoration: none;
  font-size: 14px;
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.nav-item.router-link-active {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.side-foot {
  margin-top: auto;
  padding: 12px 10px 0;
  font-size: 11px;
  line-height: 1.8;
  color: #7f948d;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.main {
  flex: 1;
  min-width: 0;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid var(--line);
}

.page-title {
  font-size: 17px;
  font-weight: 600;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.date-hint {
  font-size: 13px;
  color: var(--muted);
}

.btn-icon {
  margin-right: 4px;
}

.mobile-tabs {
  display: none;
}

@media (max-width: 820px) {
  .layout {
    display: block;
  }

  .sidebar {
    display: none;
  }

  .topbar {
    padding: 12px 14px;
  }

  .page-title {
    font-size: 16px;
  }

  .date-hint {
    display: none;
  }

  .mobile-tabs {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding: 10px 12px;
    background: #fff;
    border-bottom: 1px solid var(--line);
    position: sticky;
    top: 57px;
    z-index: 9;
    scrollbar-width: none;
  }

  .mobile-tabs::-webkit-scrollbar {
    display: none;
  }

  .tab {
    flex: 0 0 auto;
    padding: 7px 14px;
    border-radius: 999px;
    background: #f1f4f3;
    color: #51625d;
    font-size: 13px;
    text-decoration: none;
    white-space: nowrap;
  }

  .tab.router-link-active {
    background: var(--primary);
    color: #fff;
  }
}
</style>
