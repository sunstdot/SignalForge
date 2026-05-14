# 引导式实验想法生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在「生成实验想法」按钮上增加引导模式——用户可以输入方向提示，AI 顺着提示生成想法；同时保留无提示的直接生成模式。

**Architecture:** 将现有单按钮替换为分割按钮（左侧直接生成、右侧箭头弹出面板）。后端 `generate-ideas/item` 接口新增可选字段 `user_hint`，非空时追加到 prompt。前端在 `ContentCard` 组件内新增 `popoverOpen` 状态和 `GuidedIdeaPopover` 局部组件。

**Tech Stack:** React (useState, useEffect, useRef), FastAPI, Tailwind CSS（已有 utility classes）

---

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `backend/routers/experiments.py` | 修改：`generate-ideas/item` 接口新增 `user_hint` 字段并注入 prompt |
| `frontend/src/pages/BriefingPage.jsx` | 修改：`ContentCard` 组件替换按钮为分割按钮，新增 `GuidedIdeaPopover` 局部组件 |

---

### Task 1: 后端支持 `user_hint` 字段

**Files:**
- Modify: `backend/routers/experiments.py:167-251`（`generate_ideas_for_item` 函数）

- [ ] **Step 1: 在 `generate_ideas_for_item` 函数中读取 `user_hint`**

找到 `backend/routers/experiments.py` 第 167 行的 `generate_ideas_for_item` 函数，在读取 `source_type` 之后添加对 `user_hint` 的读取：

```python
@router.post("/generate-ideas/item")
async def generate_ideas_for_item(request: dict):
    """针对单条简报内容生成产品思路，返回结构化的产品概念"""
    item = request.get("item")
    if not item:
        raise HTTPException(status_code=400, detail="Item required")

    user_hint = (request.get("user_hint") or "").strip()   # ← 新增这一行

    title = item.get("title", "")
    # ... 其余不变
```

- [ ] **Step 2: 在 prompt 末尾条件追加用户提示段落**

找到 `generate_ideas_for_item` 函数中 `prompt = f"""...` 字符串的结尾（`只输出 JSON 数组，不要其他文字。格式示例：` 段落之前），在 prompt 变量赋值完成后、调用 AI 之前插入：

```python
    if user_hint:
        prompt += f"\n\n用户方向提示（请优先围绕此方向生成想法，但仍需结合文章内容）:\n{user_hint}"
```

完整修改后的函数结构（只展示变化区域）：

```python
    prompt = f"""你是一个帮助技术人员发掘实践机会的助手。基于以下文章内容，生成 2-3 个具体可执行的实验想法。
...（原有 prompt 内容不变）...
只输出 JSON 数组，不要其他文字。格式示例：
[
  {{
    "title": "...",
    ...
  }}
]
"""

    if user_hint:
        prompt += f"\n\n用户方向提示（请优先围绕此方向生成想法，但仍需结合文章内容）:\n{user_hint}"

    from services.llm_client import chat_async
    # ... 其余不变
```

- [ ] **Step 3: 手动验证后端接口**

启动后端后运行：
```bash
curl -X POST http://localhost:8000/api/experiments/generate-ideas/item \
  -H "Content-Type: application/json" \
  -d '{"item":{"id":"test","title":"Test","summary":"Test summary","url":"http://example.com","source":"test","source_type":"news"},"user_hint":"关注 agent 工具调用方向"}'
```
预期：返回 JSON，其中 ideas 内容与方向相关；无报错。

- [ ] **Step 4: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add backend/routers/experiments.py
git commit -m "feat: add user_hint support to generate-ideas/item endpoint"
```

---

### Task 2: 前端 — 分割按钮 + Popover 组件

**Files:**
- Modify: `frontend/src/pages/BriefingPage.jsx:682-897`（`ContentCard` 组件）

#### Step 2.1 — 新增状态和修改 `generateIdeas`

- [ ] **Step 1: 在 `ContentCard` 中新增 `popoverOpen` 状态**

找到 `ContentCard` 函数顶部的 state 声明区（第 683-690 行附近），新增：

```jsx
const [popoverOpen, setPopoverOpen] = useState(false)
```

最终 state 声明区如下（展示全部，方便核对）：
```jsx
const [genState, setGenState] = useState('idle') // idle | loading | selecting | done | error
const [genError, setGenError] = useState('')
const [savedCount, setSavedCount] = useState(0)
const [generatedIdeas, setGeneratedIdeas] = useState(null)
const [quickSummary, setQuickSummary] = useState(cachedSummary || null)
const [quickState, setQuickState] = useState(cachedSummary ? 'done' : 'idle')
const [collapsed, setCollapsed] = useState(false)
const [popoverOpen, setPopoverOpen] = useState(false)   // ← 新增
```

- [ ] **Step 2: 修改 `generateIdeas` 函数，接受可选 `hint` 参数**

将现有 `generateIdeas` 函数（第 732-753 行）替换为：

```jsx
async function generateIdeas(hint = '') {
  setPopoverOpen(false)
  setGenState('loading')
  setGenError('')
  try {
    const body = { item }
    if (hint) body.user_hint = hint
    const res = await fetch('/api/experiments/generate-ideas/item', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.detail || `HTTP ${res.status}`)
    }
    const data = await res.json()
    setGeneratedIdeas(data.ideas || [])
    setGenState('selecting')
  } catch (e) {
    console.error('[生成实验想法] 失败:', e.message)
    setGenError(e.message)
    setGenState('error')
  }
}
```

#### Step 2.2 — 添加 `GuidedIdeaPopover` 局部组件

- [ ] **Step 3: 在 `ContentCard` 函数内（`return` 语句之前）添加 `GuidedIdeaPopover` 局部组件**

在 `saveSelectedIdeas` 函数之后、`return (` 之前插入：

```jsx
function GuidedIdeaPopover({ onGenerate, onClose }) {
  const [hint, setHint] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    function handleKey(e) { if (e.key === 'Escape') onClose() }
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('keydown', handleKey)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose])

  return (
    <div ref={ref} style={{
      position: 'absolute', bottom: '36px', right: '0',
      width: '240px', zIndex: 50,
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '12px',
      boxShadow: '0 8px 24px rgba(0,0,0,0.3)'
    }}>
      <div className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
        ✏️ 输入你的想法方向（可选）
      </div>
      <textarea
        autoFocus
        value={hint}
        onChange={e => setHint(e.target.value)}
        placeholder="例如：想探索 agent 工具调用的边界…"
        rows={2}
        className="w-full text-xs rounded px-2 py-1.5 resize-none"
        style={{
          border: '1px solid var(--border)',
          background: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          outline: 'none'
        }}
      />
      <div className="flex gap-2 mt-2">
        <button
          onClick={() => onGenerate(hint)}
          className="flex-1 text-xs py-1.5 rounded border transition-colors"
          style={{ color: 'var(--accent-purple, #a78bfa)', borderColor: 'var(--accent-purple, #a78bfa)', background: 'transparent' }}
        >
          引导生成
        </button>
        <button
          onClick={() => onGenerate('')}
          className="flex-1 text-xs py-1.5 rounded border transition-colors"
          style={{ color: 'var(--text-muted)', borderColor: 'var(--border)', background: 'transparent' }}
        >
          直接生成
        </button>
      </div>
    </div>
  )
}
```

> **注意**：`GuidedIdeaPopover` 是定义在 `ContentCard` 函数体内部的局部组件，因此可以直接调用 `generateIdeas` —— 但为了明确接口，这里通过 `onGenerate` prop 传入，保持解耦。

#### Step 2.3 — 替换 JSX 中的按钮

- [ ] **Step 4: 替换「生成实验想法」按钮区域的 JSX**

找到 `{/* 生成实验想法 */}` 注释（第 855 行附近），将从注释到 `{/* 想法选择弹窗 */}` 结束之间的整个区域替换为：

```jsx
{/* 生成实验想法 */}
{genState === 'done' ? (
  <Link to="/experiments/ideas"
    className="text-sm px-2 py-1 rounded border"
    style={{ color: 'var(--accent-green)', borderColor: 'var(--accent-green)' }}>
    查看想法 ({savedCount})
  </Link>
) : (
  <div style={{ position: 'relative' }}>
    {/* 分割按钮 */}
    <div className="flex" style={{ border: '1px solid var(--border)', borderRadius: '5px', overflow: 'visible' }}>
      {/* 左侧：直接生成 */}
      <button
        onClick={genState === 'error' ? () => setGenState('idle') : () => generateIdeas('')}
        disabled={genState === 'loading' || genState === 'selecting'}
        className="text-sm px-2 py-1 transition-colors disabled:opacity-50"
        title={genState === 'error' ? genError : ''}
        style={{
          color: genState === 'error' ? '#dc2626' : 'var(--text-muted)',
          borderRight: '1px solid var(--border)',
          background: 'transparent',
          borderTop: 'none', borderBottom: 'none', borderLeft: 'none'
        }}
      >
        {genState === 'loading' ? '⏳ 生成中...'
          : genState === 'error' ? '生成失败（重试）'
          : '生成实验想法'}
      </button>
      {/* 右侧：弹出引导面板 */}
      <button
        onClick={() => setPopoverOpen(o => !o)}
        disabled={genState === 'loading' || genState === 'selecting' || genState === 'error'}
        className="text-xs px-1.5 py-1 transition-colors disabled:opacity-30"
        style={{
          color: popoverOpen ? 'var(--accent-purple, #a78bfa)' : 'var(--text-muted)',
          background: popoverOpen ? 'rgba(167,139,250,0.08)' : 'transparent',
          border: 'none'
        }}
      >
        ▲
      </button>
    </div>
    {/* 引导面板 */}
    {popoverOpen && (
      <GuidedIdeaPopover
        onGenerate={generateIdeas}
        onClose={() => setPopoverOpen(false)}
      />
    )}
  </div>
)}

{/* 想法选择弹窗 */}
{genState === 'selecting' && generatedIdeas && (
  <IdeasSelectModal
    ideas={generatedIdeas}
    sourceTitle={item.title}
    onConfirm={saveSelectedIdeas}
    onCancel={() => { setGeneratedIdeas(null); setGenState('idle') }}
  />
)}
```

#### Step 2.4 — 确认 import

- [ ] **Step 5: 确认 `useRef` 已导入**

在文件顶部找到 React import，确保包含 `useRef`：

```jsx
import { useState, useEffect, useRef, useCallback } from 'react'
```

如果缺少 `useRef`，补充进去。

#### Step 2.5 — 验证

- [ ] **Step 6: 启动前端，验证交互**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/frontend
pnpm dev
```

验证清单：
1. 默认状态：按钮显示为「生成实验想法 | ▲」分割形态
2. 点击左侧：立即显示「⏳ 生成中...」，右侧箭头变灰不可点
3. 点击右侧 ▲：面板向上弹出，包含 textarea + 两个按钮
4. 面板内点击「引导生成」：面板关闭，进入生成中状态
5. 面板内点击「直接生成」：同左侧点击行为
6. 按 ESC 或点击面板外：面板关闭，回到 idle 状态
7. 生成出错时：点击左侧显示「生成失败（重试）」，右侧箭头不可用

- [ ] **Step 7: Commit**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn
git add frontend/src/pages/BriefingPage.jsx
git commit -m "feat: add guided idea generation with split button and popover"
```
