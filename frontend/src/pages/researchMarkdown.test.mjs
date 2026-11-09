// 调研成稿解析器的纯函数测试。
import assert from 'node:assert/strict'
import test from 'node:test'

import { parseBlocks, parseCitations, parseInline, shortCite, smartJoin } from './researchMarkdown.js'

test('提取引用 id', () => {
  assert.deepEqual(parseCitations('- 结论 [[c1]]'), ['c1'])
  assert.deepEqual(parseCitations('两个来源 [[c7,c12]]'), ['c7', 'c12'])
  assert.deepEqual(parseCitations('无引用'), [])
})

test('引用短标签去掉 c 前缀', () => {
  assert.equal(shortCite('c787'), '787')
  assert.equal(shortCite('787'), '787')
})

test('相邻硬换行合并成一段', () => {
  const blocks = parseBlocks('第一行内容\n第二行内容')
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].type, 'paragraph')
  assert.equal(blocks[0].text, '第一行内容第二行内容')
})

test('中英混排只在英文之间补空格', () => {
  assert.equal(smartJoin(['Claude Code', 'team']), 'Claude Code team')
  assert.equal(smartJoin(['公司', '文化']), '公司文化')
  assert.equal(smartJoin(['公司', 'Anthropic']), '公司Anthropic')
})

test('空行分段', () => {
  const blocks = parseBlocks('第一段\n\n第二段')
  assert.deepEqual(blocks.map(b => b.type), ['paragraph', 'paragraph'])
})

test('标题与引用块', () => {
  const blocks = parseBlocks('## 组织结构\n\n> 引用内容')
  assert.deepEqual(blocks.map(b => b.type), ['heading', 'quote'])
  assert.equal(blocks[0].level, 2)
})

test('无序列表聚成一个列表块', () => {
  const blocks = parseBlocks('- 第一项\n- 第二项\n- 第三项')
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].type, 'list')
  assert.equal(blocks[0].ordered, false)
  assert.deepEqual(blocks[0].items, ['第一项', '第二项', '第三项'])
})

test('有序列表与无序列表分开', () => {
  const blocks = parseBlocks('1. 甲\n2. 乙\n\n- 丙')
  assert.equal(blocks[0].ordered, true)
  assert.equal(blocks[1].ordered, false)
})

test('行内解析：粗体、代码、链接、引用', () => {
  const tokens = parseInline('这是 **重点** 和 `code` 见[官网](https://x.com) [[c3]]')
  const types = tokens.map(t => t.type)
  assert.deepEqual(types, ['text', 'bold', 'text', 'code', 'text', 'link', 'text', 'cite'])
  assert.equal(tokens.find(t => t.type === 'bold').value, '重点')
  assert.equal(tokens.find(t => t.type === 'link').label, '官网')
  assert.deepEqual(tokens.find(t => t.type === 'cite').ids, ['c3'])
})

test('普通方括号不误判为引用', () => {
  const tokens = parseInline('见 [备注] 和 [链接](https://x.com)')
  assert.ok(tokens.every(t => t.type !== 'cite'))
  assert.ok(tokens.some(t => t.type === 'link'))
})

test('行内解析在长文本里保持顺序完整', () => {
  const text = 'A **B** C `D` E [[c1]]'
  const rebuilt = parseInline(text).map(t => {
    if (t.type === 'text') return t.value
    if (t.type === 'bold') return `**${t.value}**`
    if (t.type === 'code') return `\`${t.value}\``
    if (t.type === 'cite') return `[[${t.ids.join(',')}]]`
    return t.label
  }).join('')
  assert.equal(rebuilt, text)
})
