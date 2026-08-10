import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))
const viteConfig = readFileSync(new URL('../vite.config.js', import.meta.url), 'utf8')
const appSource = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8')

test('static build refreshes API snapshots before Vite copies them', () => {
  const script = pkg.scripts['build:static']

  assert.match(script, /snapshot_static\.py/)
  assert.ok(script.indexOf('snapshot_static.py') < script.indexOf('vite build'))
  assert.match(script, /VITE_STATIC_DATA=1 vite build/)
})

test('pages build refreshes snapshots, enables static data, sets base path, and runs vite after snapshot', () => {
  const script = pkg.scripts['build:pages']

  assert.equal(typeof script, 'string')
  assert.match(script, /python3 \.\.\/backend\/snapshot_static\.py/)
  assert.match(script, /VITE_STATIC_DATA=1/)
  assert.match(script, /VITE_BASE_PATH=\/SignalForge\//)
  assert.match(script, /vite build/)
  assert.ok(script.indexOf('snapshot_static.py') < script.indexOf('vite build'))
})

test('vite config reads VITE_BASE_PATH and exposes it as Vite base', () => {
  assert.match(viteConfig, /const BASE_PATH = process\.env\.VITE_BASE_PATH \|\| '\/'/)
  assert.match(viteConfig, /base:\s*BASE_PATH/)
})

test('App uses routerBasename with Vite BASE_URL and passes basename to Router', () => {
  assert.match(appSource, /import\s+\{\s*routerBasename\s*\}\s+from\s+'\.\/basePath'/)
  assert.match(appSource, /const basename = routerBasename\(import\.meta\.env\.BASE_URL\)/)
  assert.match(appSource, /<Router\s+basename=\{basename\}>/)
})
