import assert from 'node:assert/strict'
import test from 'node:test'

import { normalizeBasePath, routerBasename, withBasePath } from './basePath.js'

test('normalizeBasePath normalizes root-like values to slash', () => {
  assert.equal(normalizeBasePath(), '/')
  assert.equal(normalizeBasePath('/'), '/')
})

test('normalizeBasePath wraps project paths with single leading and trailing slashes', () => {
  assert.equal(normalizeBasePath('token-burn'), '/token-burn/')
  assert.equal(normalizeBasePath('/token-burn/'), '/token-burn/')
})

test('routerBasename returns root slash for root and no trailing slash for project paths', () => {
  assert.equal(routerBasename(), '/')
  assert.equal(routerBasename('/token-burn/'), '/token-burn')
})

test('withBasePath joins root and project paths without duplicate slashes', () => {
  assert.equal(withBasePath('/', 'data/search_cache/history.json'), '/data/search_cache/history.json')
  assert.equal(withBasePath('/token-burn/', '/data/search_cache/history.json'), '/token-burn/data/search_cache/history.json')
})
