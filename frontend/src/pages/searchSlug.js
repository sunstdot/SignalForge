function topicHash(s) {
  let h = 5381
  for (const ch of String(s || 'topic')) {
    h = (Math.imul(h, 33) + ch.codePointAt(0)) >>> 0
  }
  return h.toString(16).padStart(8, '0')
}

export function slugify(s) {
  const raw = String(s || 'topic').trim().toLowerCase() || 'topic'
  const prefix = raw.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'topic'
  return `${prefix}-${topicHash(raw)}`
}
