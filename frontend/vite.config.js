import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 前端端口可在 backend/config.txt 中配置 FRONTEND_PORT
// 后端 API 地址在 backend/config.txt 中配置 FRONTEND_API_TARGET
const FRONTEND_PORT = 3000
const API_TARGET = 'http://127.0.0.1:5000'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: FRONTEND_PORT,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})
