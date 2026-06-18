import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./SearchPage.jsx', import.meta.url), 'utf8')

test('SearchPage starts empty and searches via the brief endpoint', () => {
  // no static sample brief — data comes from the backend
  assert.doesNotMatch(source, /searchBriefData/)
  assert.match(source, /\/api\/search\/brief/)
  // async job + polling
  assert.match(source, /\/api\/search\/brief\/\$\{jid\}/)
  assert.match(source, /status === 'idle'/)
  assert.match(source, /status === 'running'/)
})

test('SearchPage renders the brief dashboard sections when done', () => {
  assert.match(source, /status === 'done' && brief/)
  for (const sec of ['综合简报', '关键模式', '让我深入', '情报时间线']) {
    assert.match(source, new RegExp(sec))
  }
  for (const panel of ['概览', '平台分布', 'Top Voices', '数据缺口说明']) {
    assert.match(source, new RegExp(panel))
  }
})

test('SearchPage keeps only the topic in the browser, brief lives server-side', () => {
  // browser stores just the topic string + the in-flight job ref — never the brief blob
  assert.match(source, /sessionStorage\.setItem\('sf_topic'/)
  assert.match(source, /sessionStorage\.setItem\('sf_job'/)
  assert.doesNotMatch(source, /sessionStorage\.setItem\('sf_brief'/)
})

test('SearchPage restores on mount: resume job or refetch cached brief from server', () => {
  assert.match(source, /useEffect/)
  assert.match(source, /sessionStorage\.getItem\('sf_job'\)/)
  assert.match(source, /sessionStorage\.getItem\('sf_topic'\)/)
  // refetch cached brief file from the backend by topic
  assert.match(source, /\/api\/search\/brief\?topic=/)
  assert.match(source, /pollJob\(jid, token, t\)/)
})

test('SearchPage shows search history and opens a cached record', () => {
  assert.match(source, /\/api\/search\/history/)
  assert.match(source, /搜索记录/)
  // clicking a record reads the cached brief file (no re-run)
  assert.match(source, /openCached/)
  assert.match(source, /\/api\/search\/brief\?topic=/)
  // title returns to the history home
  assert.match(source, /goHome/)
})

test('SearchPage has a static (backend-free) data mode', () => {
  // build flag gate
  assert.match(source, /import\.meta\.env\.VITE_STATIC_DATA/)
  // static mode reads cached JSON files under /data/search_cache instead of /api
  assert.match(source, /\/data\/search_cache\/history\.json/)
  assert.match(source, /\/data\/search_cache\/briefs\//)
  // slugify so a topic maps to its cached brief file
  assert.match(source, /slugify/)
})

test('SearchPage supports all six platforms and guards unknown ones', () => {
  for (const p of ['reddit', 'youtube', 'tiktok', 'instagram']) {
    assert.match(source, new RegExp(`${p}:`))
  }
  assert.match(source, /const PF = /)  // safe platform accessor
})
