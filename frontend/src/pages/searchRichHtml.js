const PLATFORM_SOURCE_KEYS = {
  instagram: ['instagram', '@instagram', 'Instagram'],
  tiktok: ['tiktok', '@tiktok', 'TikTok'],
  youtube: ['youtube', '@youtube', 'YouTube'],
  reddit: ['reddit', '@reddit', 'Reddit'],
  hn: ['hacker news', 'hn', 'Hacker News'],
  x: ['x', 'X'],
}

function escapeAttr(s) {
  return String(s || '').replace(/"/g, '&quot;')
}

function sourceKey(s) {
  return String(s || '').trim().toLowerCase()
}

function addSource(map, key, url) {
  const k = sourceKey(key)
  if (k && url && !map[k]) map[k] = url
}

export function buildSourceMap(brief) {
  const map = {}
  for (const group of brief?.timeline || []) {
    for (const item of group.items || []) {
      if (!item?.url) continue
      addSource(map, item.who, item.url)
      addSource(map, item.handle, item.url)
      for (const key of PLATFORM_SOURCE_KEYS[item.p] || []) {
        addSource(map, key, item.url)
      }
    }
  }
  return map
}

function linkifySourceText(text, sourceMap) {
  return String(text || '').replace(/(@?[\w.-]+)/g, (token) => {
    const url = sourceMap[sourceKey(token)]
    if (!url) return token
    return `<a class="sf-src-link" href="${escapeAttr(url)}" target="_blank" rel="noopener noreferrer">${token}</a>`
  })
}

export function richHtml(s, sourceMap = {}) {
  if (!s) return ''
  return String(s)
    .replace(/<src>(.*?)<\/src>/gs, (_, text) => `<span class="sf-src">${linkifySourceText(text, sourceMap)}</span>`)
    .replace(/\{b\}/g, '<b>').replace(/\{\/b\}/g, '</b>')
    .replace(/<q>/g, '<span class="sf-q">').replace(/<\/q>/g, '</span>')
    .replace(/<hl>/g, '<span class="sf-hl">').replace(/<\/hl>/g, '</span>')
    .replace(/<num>/g, '<span class="sf-num">').replace(/<\/num>/g, '</span>')
    .replace(/<c>/g, '<span class="sf-mono">').replace(/<\/c>/g, '</span>')
}
