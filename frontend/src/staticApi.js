// 静态部署模式：用 VITE_STATIC_DATA=1 构建时，拦截所有 /api 请求，改为读取构建时
// 快照到 /api-static 下的静态 JSON 文件（GET），写类请求一律安全空响应（无后端）。
// key 规则必须与 backend/snapshot_static.py 的 api_key 完全一致。

import { withBasePath } from './basePath'

const STATIC = import.meta.env.VITE_STATIC_DATA === '1'
const BASE_URL = import.meta.env.BASE_URL

function apiKey(pathname, searchParams) {
  const path = pathname.replace(/^\/api\//, '')
  const ps = [...searchParams.entries()]
    .filter(([k]) => k !== 'refresh')
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
  const qs = ps.map(([k, v]) => `${k}=${v}`).join('&')
  return (qs ? `${path}__${qs}` : path) + '.json'
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function installStaticApi() {
  if (!STATIC || typeof window === 'undefined') return
  const realFetch = window.fetch.bind(window)

  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : (input && input.url) || ''
    let u
    try { u = new URL(url, window.location.origin) } catch { return realFetch(input, init) }

    // 非本站 /api 请求照常走
    if (u.pathname.indexOf('/api/') !== 0) return realFetch(input, init)

    const method = ((init && init.method) || (typeof input !== 'string' && input && input.method) || 'GET').toUpperCase()

    // 写类请求（POST/PUT/DELETE/...）：静态模式无后端，返回安全空响应，不让页面崩
    if (method !== 'GET') {
      console.warn(`[static] 忽略写请求 ${method} ${u.pathname}（静态部署无后端）`)
      return jsonResponse({ static: true, ok: false })
    }

    // GET：读快照文件；缺失则返回空对象让页面优雅降级
    const fileUrl = withBasePath(BASE_URL, `api-static/${apiKey(u.pathname, u.searchParams)}`)
    try {
      const r = await realFetch(fileUrl)
      if (r.ok) return r
    } catch { /* fall through */ }
    return jsonResponse({})
  }
}
