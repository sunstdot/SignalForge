// 引用标记解析与阶段标签的纯函数测试，不依赖 DOM。
import assert from 'node:assert/strict'
import test from 'node:test'

// 与 ResearchPage.jsx 中的解析规则保持一致
const CITE_RE = /\[\[((?:c\d+)(?:,c\d+)*)\]\]/g

function parseCitations(markdown) {
  const ids = []
  for (const match of (markdown || '').matchAll(CITE_RE)) {
    ids.push(...match[1].split(',').map(s => s.trim()))
  }
  return ids
}

test('解析单个引用', () => {
  assert.deepEqual(parseCitations('- 员工约 2500 人 [[c1]]'), ['c1'])
})

test('解析一行内的多个引用', () => {
  assert.deepEqual(
    parseCitations('- 两个来源都提到扩张 [[c7,c12]]'),
    ['c7', 'c12'],
  )
})

test('解析多行多引用且去重交给调用方', () => {
  const md = '- a [[c1]]\n- b [[c2]]\n- c [[c1]]'
  assert.deepEqual(parseCitations(md), ['c1', 'c2', 'c1'])
})

test('没有引用时返回空数组', () => {
  assert.deepEqual(parseCitations('纯文字段落，没有角标'), [])
  assert.deepEqual(parseCitations(''), [])
})

test('不把普通方括号误判为引用', () => {
  assert.deepEqual(parseCitations('这是 [链接](https://x.example) 和 [备注]'), [])
})

test('非法 id 不匹配', () => {
  assert.deepEqual(parseCitations('[[x1]] [[c]] [[C2]]'), [])
})
