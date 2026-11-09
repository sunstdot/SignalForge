// 调研成稿的轻量 Markdown 解析。纯函数，便于 node --test 直接测试。

export const CITE_RE = /\[\[((?:c\d+)(?:,c\d+)*)\]\]/g

const CJK = /[一-鿿　-〿＀-￯]/

/** 抽出一段文本里所有的引用 id */
export function parseCitations(markdown) {
  const ids = []
  for (const match of (markdown || '').matchAll(CITE_RE)) {
    ids.push(...match[1].split(',').map(s => s.trim()).filter(Boolean))
  }
  return ids
}

/** 引用 id 显示成短标签：c787 → 787 */
export function shortCite(id) {
  return (id || '').replace(/^c/, '')
}

/**
 * 把换行拼接成一段。
 * 中文之间直接相连，英文/数字之间补空格，避免中文出现多余空隙。
 */
export function smartJoin(lines) {
  return lines.reduce((acc, line) => {
    if (!acc) return line
    const prevChar = acc.slice(-1)
    const nextChar = line.slice(0, 1)
    const needSpace = !CJK.test(prevChar) && !CJK.test(nextChar) && /\S/.test(prevChar) && /\S/.test(nextChar)
    return acc + (needSpace ? ' ' : '') + line
  }, '')
}

const LIST_RE = /^\s*(?:[-*+]|\d+\.)\s+/
const HEADING_RE = /^(#{1,6})\s+(.*)$/

/**
 * 把 markdown 切成块。相邻的正文行合并成一段——模型输出常按固定宽度硬换行，
 * 逐行成段会让整篇看起来全是碎句子。
 */
export function parseBlocks(markdown) {
  const lines = (markdown || '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let buffer = []
  let listItems = null
  let ordered = false

  const flushParagraph = () => {
    if (!buffer.length) return
    blocks.push({ type: 'paragraph', text: smartJoin(buffer) })
    buffer = []
  }
  const flushList = () => {
    if (!listItems) return
    blocks.push({ type: 'list', ordered, items: listItems })
    listItems = null
  }

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '')

    if (!line.trim()) {
      flushParagraph()
      flushList()
      continue
    }

    const heading = line.match(HEADING_RE)
    if (heading) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'heading', level: heading[1].length, text: heading[2] })
      continue
    }

    if (line.trim().startsWith('>')) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'quote', text: line.trim().replace(/^>\s?/, '') })
      continue
    }

    const listMatch = line.match(LIST_RE)
    if (listMatch) {
      flushParagraph()
      const isOrdered = /^\s*\d+\./.test(line)
      if (listItems && ordered !== isOrdered) flushList()
      ordered = isOrdered
      listItems = listItems || []
      listItems.push(line.replace(LIST_RE, ''))
      continue
    }

    // 列表项内的续行（缩进行的普通文本）并入上一条
    if (listItems) {
      listItems[listItems.length - 1] = smartJoin([listItems[listItems.length - 1], line.trim()])
      continue
    }

    buffer.push(line.trim())
  }

  flushParagraph()
  flushList()
  return blocks
}

/**
 * 行内解析：粗体、行内代码、链接、引用标记。
 * 返回 token 数组，交给 React 渲染。
 */
export function parseInline(text) {
  const tokens = []
  // 一次扫描，按出现顺序切出各种行内元素
  const pattern = /(\*\*[^*]+\*\*)|(`[^`]+`)|(\[[^\]]+\]\([^)]+\))|(\[\[(?:c\d+)(?:,c\d+)*\]\])/g
  let cursor = 0
  let match

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      tokens.push({ type: 'text', value: text.slice(cursor, match.index) })
    }
    const raw = match[0]
    if (raw.startsWith('**')) {
      tokens.push({ type: 'bold', value: raw.slice(2, -2) })
    } else if (raw.startsWith('`')) {
      tokens.push({ type: 'code', value: raw.slice(1, -1) })
    } else if (raw.startsWith('[[')) {
      tokens.push({
        type: 'cite',
        ids: match[4].slice(2, -2).split(',').map(s => s.trim()).filter(Boolean),
      })
    } else {
      const link = raw.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
      tokens.push({ type: 'link', label: link[1], href: link[2] })
    }
    cursor = match.index + raw.length
  }

  if (cursor < text.length) {
    tokens.push({ type: 'text', value: text.slice(cursor) })
  }
  return tokens
}
