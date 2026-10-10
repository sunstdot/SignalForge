import assert from 'node:assert/strict'
import test from 'node:test'

import { buildSourceMap, richHtml } from './searchRichHtml.js'

test('richHtml renders source markers as links from timeline source URLs', () => {
  const brief = {
    timeline: [{
      items: [
        {
          p: 'x',
          who: '@FinanceYF5',
          handle: '@FinanceYF5',
          url: 'https://x.com/FinanceYF5/status/1',
        },
      ],
    }],
  }

  const html = richHtml(
    'OpenAI 芯片<src>@FinanceYF5</src>',
    buildSourceMap(brief),
  )

  assert.match(html, /<span class="sf-src">/)
  assert.match(html, /<a class="sf-src-link" href="https:\/\/x\.com\/FinanceYF5\/status\/1"/)
  assert.match(html, />@FinanceYF5<\/a>/)
})

test('source map links platform aliases when source marker names a platform', () => {
  const brief = {
    timeline: [{
      items: [
        {
          p: 'instagram',
          who: 'Instagram',
          url: 'https://www.instagram.com/reel/example/',
        },
      ],
    }],
  }

  const html = richHtml(
    '成本讨论<src>@instagram</src>',
    buildSourceMap(brief),
  )

  assert.match(html, /href="https:\/\/www\.instagram\.com\/reel\/example\/"/)
  assert.match(html, />@instagram<\/a>/)
})
