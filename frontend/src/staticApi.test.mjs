import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const src = readFileSync(new URL('./staticApi.js', import.meta.url), 'utf8')

test('static api shim is gated on the build flag and overrides fetch', () => {
  assert.match(src, /import\.meta\.env\.VITE_STATIC_DATA/)
  assert.match(src, /window\.fetch =/)
  assert.match(src, /export function installStaticApi/)
})

test('shim maps GET /api to /api-static snapshot files and stubs writes', () => {
  // only intercepts /api/ paths
  assert.match(src, /\/api\//)
  assert.match(src, /import\s+\{\s*withBasePath\s*\}\s+from\s+'\.\/basePath'/)
  assert.match(src, /const BASE_URL = import\.meta\.env\.BASE_URL/)
  // GET → BASE_URL + /api-static/<key>.json
  assert.match(src, /withBasePath\(BASE_URL, `api-static\/\$\{apiKey\(u\.pathname, u\.searchParams\)\}`\)/)
  // non-GET returns a safe stub (no backend)
  assert.match(src, /method !== 'GET'/)
  // key drops volatile refresh param (must match backend snapshot_static.py)
  assert.match(src, /'refresh'/)
})

test('shim is installed before render in main.jsx', () => {
  const main = readFileSync(new URL('./main.jsx', import.meta.url), 'utf8')
  assert.match(main, /installStaticApi\(\)/)
})
