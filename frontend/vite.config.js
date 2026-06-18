import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { cpSync, existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))

// 静态部署模式（VITE_STATIC_DATA=1）：构建后把仓库根的 data/search_cache 拷进 dist/data，
// 这样只部署 dist 也能让前端读取缓存的情报数据，无需后端。
const STATIC_DATA = !!process.env.VITE_STATIC_DATA

function copySearchCache() {
  return {
    name: 'copy-search-cache',
    apply: 'build',
    closeBundle() {
      if (!STATIC_DATA) return
      const src = resolve(__dirname, '../data/search_cache')
      const dest = resolve(__dirname, 'dist/data/search_cache')
      if (existsSync(src)) {
        cpSync(src, dest, { recursive: true })
        console.log(`[static] copied ${src} -> ${dest}`)
      } else {
        console.warn(`[static] ${src} not found; nothing to copy (run a search first)`)
      }
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), copySearchCache()],
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
