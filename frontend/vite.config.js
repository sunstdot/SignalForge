import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { cpSync, existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))

// 静态部署模式（VITE_STATIC_DATA=1）：构建后把仓库根的 data/search_cache 拷进 dist/data，
// 这样只部署 dist 也能让前端读取缓存的情报数据，无需后端。
const STATIC_DATA = !!process.env.VITE_STATIC_DATA
const BASE_PATH = process.env.VITE_BASE_PATH || '/'

function copyStaticData() {
  const copy = (rel, dest) => {
    const src = resolve(__dirname, rel)
    const to = resolve(__dirname, dest)
    if (existsSync(src)) {
      cpSync(src, to, { recursive: true })
      console.log(`[static] copied ${src} -> ${to}`)
    } else {
      console.warn(`[static] ${src} not found; skipped`)
    }
  }
  return {
    name: 'copy-static-data',
    apply: 'build',
    closeBundle() {
      if (!STATIC_DATA) return
      // 情报搜索缓存（SearchPage 直接读 /data/search_cache）
      copy('../data/search_cache', 'dist/data/search_cache')
      // 其余页面的 API 快照（fetch 拦截器读 /api-static），由 snapshot_static.py 生成
      copy('../data/static_snapshot', 'dist/api-static')
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  base: BASE_PATH,
  plugins: [react(), copyStaticData()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
