<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { setToken } from '../state'

const route = useRoute()
const router = useRouter()
const password = ref('')
const loading = ref(false)

async function login() {
  if (!password.value) {
    ElMessage.warning('请输入访问密码')
    return
  }
  loading.value = true
  try {
    const res = await api.login(password.value)
    setToken(res.token)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.replace(redirect)
  } catch (e: any) {
    ElMessage.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="logo">¥</div>
      <h1>个人理财账本</h1>
      <p class="sub">输入访问密码，开始记录你的资金</p>

      <el-input
        v-model="password"
        type="password"
        size="large"
        show-password
        placeholder="访问密码"
        @keyup.enter="login"
      />

      <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="login">
        进入系统
      </el-button>

      <div class="hint">
        <div>首次使用默认密码：<b>123456</b>（登录后可在「系统设置」修改）</div>
        <div>同一 WiFi 下，手机 / 其他电脑用本机局域网地址即可访问。</div>
      </div>
    </div>
    <div class="foot">数据保存在本机 SQLite · 不经过任何第三方服务器</div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: radial-gradient(circle at 20% 0%, #e6efe9 0%, #f4f6f5 45%, #f4f6f5 100%);
}

.login-card {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 34px 30px 28px;
  box-shadow: 0 20px 50px rgba(38, 48, 45, 0.07);
  text-align: center;
}

.logo {
  width: 52px;
  height: 52px;
  margin: 0 auto 16px;
  border-radius: 15px;
  background: #253531;
  color: #d8ece3;
  font-size: 26px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

h1 {
  margin: 0 0 6px;
  font-size: 21px;
  font-weight: 650;
}

.sub {
  margin: 0 0 24px;
  color: var(--muted);
  font-size: 13px;
}

.login-btn {
  width: 100%;
  margin-top: 16px;
}

.hint {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px dashed var(--line);
  color: var(--muted);
  font-size: 12px;
  line-height: 1.9;
  text-align: left;
}

.hint b {
  color: var(--text);
}

.foot {
  margin-top: 22px;
  color: #96a49f;
  font-size: 12px;
}
</style>
