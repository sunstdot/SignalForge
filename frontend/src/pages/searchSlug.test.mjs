import assert from 'node:assert/strict'
import test from 'node:test'

import { slugify } from './searchSlug.js'

test('slugify keeps readable prefixes and distinguishes mixed-language topics', () => {
  assert.match(slugify('OpenAI'), /^openai-[0-9a-f]{8}$/)
  assert.match(slugify('openAI相关的信息'), /^openai-[0-9a-f]{8}$/)
  assert.match(slugify('大模型推理成本'), /^topic-[0-9a-f]{8}$/)
  assert.notEqual(slugify('OpenAI'), slugify('openAI相关的信息'))
})
