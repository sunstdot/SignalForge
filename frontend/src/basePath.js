export function normalizeBasePath(basePath = '/') {
  const trimmed = String(basePath || '/').trim()
  if (!trimmed || trimmed === '/') return '/'
  return `/${trimmed.replace(/^\/+|\/+$/g, '')}/`
}

export function routerBasename(basePath = '/') {
  const normalized = normalizeBasePath(basePath)
  return normalized === '/' ? '/' : normalized.slice(0, -1)
}

export function withBasePath(basePath, path) {
  const normalized = normalizeBasePath(basePath)
  const relative = String(path || '').replace(/^\/+/, '')
  return `${normalized}${relative}`
}
