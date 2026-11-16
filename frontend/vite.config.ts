import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发环境：前端 5173，后端 8000。
// /api 统一代理到本机后端，手机/其他电脑访问 http://主机IP:5173 也能正常调接口。
// 以后把前端部署到服务器时，可用环境变量 VITE_API_BASE 指定后端地址。
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
