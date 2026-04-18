# Social Publisher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "📕 发小红书" button to the 机会雷达 header that generates 5-slide Xiaohongshu content for top-3 opportunities and displays it in a copyable preview modal.

**Architecture:** New `backend/services/social_poster.py` with a platform strategy dict → new `backend/routers/social.py` with `POST /api/social/{platform}/generate` → frontend button + `XiaohongshuModal` in `BriefingPage.jsx`. Cache results in `data/social_posts/{platform}/{date}.json`.

**Tech Stack:** Python/FastAPI (backend), React/JSX (frontend), Wanqing OpenAI-compat client for AI generation, file-based JSON storage.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/services/storage.py` | Add `SOCIAL_POSTS_DIR`, `load_social_post`, `save_social_post` |
| Create | `backend/services/social_poster.py` | Platform strategy dict + `_generate_xiaohongshu` + `generate_social_post` |
| Create | `backend/routers/social.py` | `POST /api/social/{platform}/generate` endpoint |
| Modify | `backend/main.py` | Register social router |
| Modify | `frontend/src/pages/BriefingPage.jsx` | Add `XiaohongshuModal` component + button + state in `OpportunityRadar` |

---

## Task 1: Add social post storage to storage.py

**Files:**
- Modify: `backend/services/storage.py`

- [ ] **Step 1: Add `SOCIAL_POSTS_DIR` and storage functions**

Open `backend/services/storage.py`. After the `RDEV_DIR` block (around line 206), add:

```python
# ───────────────────────── 社交媒体内容缓存 ─────────────────────────

SOCIAL_POSTS_DIR = DATA_DIR / "social_posts"
SOCIAL_POSTS_DIR.mkdir(parents=True, exist_ok=True)


def load_social_post(date: str, platform: str) -> Optional[Dict]:
    path = SOCIAL_POSTS_DIR / platform / f"{date}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_social_post(date: str, platform: str, data: Dict):
    platform_dir = SOCIAL_POSTS_DIR / platform
    platform_dir.mkdir(parents=True, exist_ok=True)
    path = platform_dir / f"{date}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 2: Verify storage functions work**

From the `backend/` directory, run:
```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/backend
python -c "
from services.storage import save_social_post, load_social_post
save_social_post('2026-04-18', 'xiaohongshu', {'test': True})
result = load_social_post('2026-04-18', 'xiaohongshu')
assert result == {'test': True}, f'Expected test dict, got {result}'
print('storage OK')
"
```
Expected output: `storage OK`

- [ ] **Step 3: Clean up test file**

```bash
rm /Users/shitaosun/Project/AI-Anything/token-burn/data/social_posts/xiaohongshu/2026-04-18.json
```

- [ ] **Step 4: Commit**

```bash
git add backend/services/storage.py
git commit -m "feat: add social post storage functions to storage.py"
```

---

## Task 2: Create social_poster.py service

**Files:**
- Create: `backend/services/social_poster.py`

- [ ] **Step 1: Create the service file**

Create `backend/services/social_poster.py` with full content:

```python
"""社交媒体内容生成服务 - 支持多平台策略扩展"""
import json as _json
import re
from datetime import datetime
from typing import Dict, List


def _generate_xiaohongshu(date: str, top3_opps: List[Dict]) -> Dict:
    """为 top-3 商业机会生成小红书图集文案（5张图/机会）"""
    from services.chinese_briefer import get_wanqing_client, get_wanqing_app_id, _get_model
    client = get_wanqing_client()
    app_id = get_wanqing_app_id(_get_model())

    results = []
    for opp in top3_opps:
        opp_json = _json.dumps({
            "opportunity_title": opp.get("opportunity_title", ""),
            "core_insight": opp.get("core_insight", ""),
            "product_form": opp.get("product_form", ""),
            "target_users": opp.get("target_users", ""),
            "mvp_features": opp.get("mvp_features", []),
            "business_model": opp.get("business_model", ""),
            "competitive_barrier": opp.get("competitive_barrier", ""),
            "risks": opp.get("risks", ""),
            "total_score": opp.get("total_score", 0),
        }, ensure_ascii=False)

        prompt = f"""你是一位大厂前端 TL（技术负责人），同时是活跃的独立开发者，在小红书运营「AI 情报挖掘商业机会」账号。

根据以下 AI 商业洞察，生成一篇小红书图集（5张图）的文案。

# 商业机会数据
{opp_json}

# 输出格式
只输出 JSON，不要任何解释文字和 markdown 代码块：
{{
  "slides": [
    {{
      "slide": 1,
      "role": "封面图",
      "headline": "封面大标题（从下方两种中选一）",
      "subtitle": "具体产品方向（20字内，口语化）"
    }},
    {{
      "slide": 2,
      "role": "痛点与市场",
      "body": "🎯 目标用户：...\\n😩 核心痛点：...\\n📊 市场机会：..."
    }},
    {{
      "slide": 3,
      "role": "MVP功能与壁垒",
      "body": "🛠 核心功能：...\\n💰 商业模式：...\\n🏰 竞争壁垒：..."
    }},
    {{
      "slide": 4,
      "role": "TL私房话",
      "body": "以「作为前端开发」开头，口语化，评价技术实现难度和天数，给独立开发者建议，100字内"
    }},
    {{
      "slide": 5,
      "role": "引流钩子",
      "body": "以上内容由我的自研 AI 情报系统全自动生成。想看今天剩下的商业洞察？在评论区回复【洞察】，后台发给你完整版文档 / 邀请你进内测群。"
    }}
  ]
}}

# 要求
- 封面大标题必须从这两个中选一：
  「今天 AI 帮我挖到了 1 个搞钱盲区 💰」
  「大厂前端TL：今天系统扫了100篇AI论文，发现这个细分市场还是蓝海」
- 图4 必须以"作为前端开发"开头，口语化，需提到预计实现天数
- 图5 引流钩子直接用模板原文，不要改动
- body 字段内用 \\n 分隔行（转义的 \\n，不是实际换行）
- 文字简洁有力，小红书"少即是多"风格"""

        try:
            completion = client.chat.completions.create(
                model=app_id,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = completion.choices[0].message.content.strip()
            raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            parsed = _json.loads(match.group(0) if match else raw)
            results.append({
                "opportunity_title": opp.get("opportunity_title", ""),
                "total_score": opp.get("total_score", 0),
                "slides": parsed.get("slides", []),
            })
        except Exception as e:
            print(f"[social_poster] xiaohongshu gen failed for '{opp.get('opportunity_title')}': {e}")
            results.append({
                "opportunity_title": opp.get("opportunity_title", ""),
                "total_score": opp.get("total_score", 0),
                "slides": [],
            })

    return {
        "platform": "xiaohongshu",
        "date": date,
        "generated_at": datetime.now().isoformat(),
        "top3": results,
    }


# ─── 平台策略注册表 ────────────────────────────────────────────────
# 添加新平台：新增生成函数，在此注册即可，路由层无需改动

PLATFORM_GENERATORS = {
    "xiaohongshu": _generate_xiaohongshu,
    # "jike": _generate_jike,
    # "twitter": _generate_twitter,
}


def generate_social_post(date: str, platform: str, top3_opps: List[Dict]) -> Dict:
    """调度到对应平台的内容生成器"""
    generator = PLATFORM_GENERATORS.get(platform)
    if not generator:
        raise ValueError(f"Unsupported platform: {platform}. Supported: {list(PLATFORM_GENERATORS.keys())}")
    return generator(date, top3_opps)
```

- [ ] **Step 2: Verify the module imports correctly**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/backend
python -c "
from services.social_poster import generate_social_post, PLATFORM_GENERATORS
assert 'xiaohongshu' in PLATFORM_GENERATORS
print('social_poster import OK, platforms:', list(PLATFORM_GENERATORS.keys()))
"
```
Expected: `social_poster import OK, platforms: ['xiaohongshu']`

- [ ] **Step 3: Commit**

```bash
git add backend/services/social_poster.py
git commit -m "feat: add social_poster service with xiaohongshu platform strategy"
```

---

## Task 3: Create social router and register in main.py

**Files:**
- Create: `backend/routers/social.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create `backend/routers/social.py`**

```python
"""社交媒体内容生成 API"""
import re
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services.storage import load_opportunities, load_social_post, save_social_post
from services.social_poster import generate_social_post, PLATFORM_GENERATORS

router = APIRouter()


@router.post("/{platform}/generate")
async def generate_platform_post(
    platform: str,
    date: str = Query(..., description="日期，格式 YYYY-MM-DD"),
    refresh: bool = Query(False, description="强制重新生成，忽略缓存"),
):
    """为指定平台生成当日 top-3 商业机会的社交媒体内容"""
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

    if platform not in PLATFORM_GENERATORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform '{platform}'. Supported: {list(PLATFORM_GENERATORS.keys())}"
        )

    if not refresh:
        cached = load_social_post(date, platform)
        if cached:
            return cached

    opp_data = load_opportunities(date)
    if not opp_data or not opp_data.get("opportunities"):
        raise HTTPException(
            status_code=400,
            detail=f"No opportunities found for {date}. Generate 机会雷达 first."
        )

    all_opps = sorted(opp_data["opportunities"], key=lambda x: -x.get("total_score", 0))
    top3 = all_opps[:3]

    result = generate_social_post(date, platform, top3)
    save_social_post(date, platform, result)
    return result
```

- [ ] **Step 2: Register router in `backend/main.py`**

In `main.py`, find line 25:
```python
from routers import briefing, dates, experiments, content
```

Change it to:
```python
from routers import briefing, dates, experiments, content, social
```

Then after line 65 (`app.include_router(content.router, ...)`), add:
```python
app.include_router(social.router, prefix="/api/social", tags=["social"])
```

- [ ] **Step 3: Verify the server starts**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/backend
python -c "
from main import app
routes = [r.path for r in app.routes]
assert any('/api/social' in r for r in routes), f'social route missing, routes: {routes}'
print('router registered OK')
"
```
Expected: `router registered OK`

- [ ] **Step 4: Test the endpoint (requires running server)**

Start the backend if not running, then:
```bash
curl -s -X POST "http://localhost:8001/api/social/xiaohongshu/generate?date=2026-04-16" | python3 -m json.tool | head -30
```
Expected: JSON with `platform`, `date`, `generated_at`, `top3` (array of 3 items, each with `slides` array of 5).

If you get `400 No opportunities found`, first visit `http://localhost:5174` and load the opportunities for that date.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/social.py backend/main.py
git commit -m "feat: add social router POST /api/social/{platform}/generate"
```

---

## Task 4: Add XiaohongshuModal component to BriefingPage.jsx

**Files:**
- Modify: `frontend/src/pages/BriefingPage.jsx`

The modal is a standalone function component added to this file (before the `OpportunityRadar` function).

- [ ] **Step 1: Add XiaohongshuModal component**

In `BriefingPage.jsx`, find the line `function OpportunityRadar(` (around line 339). Insert the following **before** it:

```jsx
function XiaohongshuModal({ result, onClose }) {
  const [activeTab, setActiveTab] = useState(0)
  const [copiedSlide, setCopiedSlide] = useState(null)
  const [copiedAll, setCopiedAll] = useState(false)

  const top3 = result?.top3 || []
  const current = top3[activeTab] || {}
  const slides = current.slides || []

  function slideText(slide) {
    if (slide.role === '封面图') {
      return `${slide.headline}\n${slide.subtitle || ''}`
    }
    return slide.body || ''
  }

  function handleCopySlide(idx) {
    const text = slideText(slides[idx])
    navigator.clipboard.writeText(text).then(() => {
      setCopiedSlide(idx)
      setTimeout(() => setCopiedSlide(null), 1500)
    })
  }

  function handleCopyAll() {
    const text = slides.map(s =>
      `【${s.role}】\n${slideText(s)}`
    ).join('\n\n')
    navigator.clipboard.writeText(text).then(() => {
      setCopiedAll(true)
      setTimeout(() => setCopiedAll(false), 1500)
    })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
        style={{ maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: '#f3f4f6' }}>
          <div className="flex items-center gap-2">
            <span className="text-base">📕</span>
            <span className="text-sm font-bold" style={{ color: '#111' }}>小红书内容</span>
            <span className="text-xs px-2 py-0.5 rounded-full border"
              style={{ color: '#ff2442', borderColor: '#fecdd3', background: '#fff0f2' }}>
              Top 3 机会
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyAll}
              className="text-xs px-3 py-1.5 rounded-lg border font-medium transition-all"
              style={{ color: '#374151', borderColor: '#e5e7eb', background: copiedAll ? '#f0fdf4' : '#f9fafb' }}>
              {copiedAll ? '✓ 已复制' : '复制全部文案'}
            </button>
            <button onClick={onClose} className="text-lg leading-none" style={{ color: '#9ca3af' }}>✕</button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b px-5" style={{ borderColor: '#f3f4f6', flexShrink: 0 }}>
          {top3.map((opp, i) => (
            <button
              key={i}
              onClick={() => setActiveTab(i)}
              className="text-xs py-2.5 mr-4 border-b-2 transition-colors"
              style={{
                borderColor: activeTab === i ? '#ff2442' : 'transparent',
                color: activeTab === i ? '#ff2442' : '#9ca3af',
                fontWeight: activeTab === i ? 600 : 400,
                marginBottom: -1,
              }}>
              {`① ② ③`[i * 2]} {opp.opportunity_title?.slice(0, 10)}
            </button>
          ))}
        </div>

        {/* Slides */}
        <div className="overflow-y-auto px-5 py-4" style={{ flex: 1 }}>
          {slides.map((slide, idx) => (
            <div key={idx} className="rounded-xl border mb-3 overflow-hidden"
              style={{ borderColor: idx === 0 ? '#fecdd3' : '#e5e7eb' }}>
              <div className="flex items-center justify-between px-3 py-2"
                style={{
                  background: idx === 0
                    ? 'linear-gradient(135deg, #ff2442, #ff6b6b)'
                    : '#f9fafb',
                }}>
                <span className="text-xs font-semibold"
                  style={{ color: idx === 0 ? 'white' : '#374151' }}>
                  图 {slide.slide} · {slide.role}
                </span>
                <button
                  onClick={() => handleCopySlide(idx)}
                  className="text-xs px-2 py-0.5 rounded transition-all"
                  style={{
                    border: `1px solid ${idx === 0 ? 'rgba(255,255,255,0.5)' : '#e5e7eb'}`,
                    color: idx === 0 ? 'white' : '#6b7280',
                    background: 'transparent',
                  }}>
                  {copiedSlide === idx ? '✓ 已复制' : '复制'}
                </button>
              </div>
              <div className="px-4 py-3" style={{ background: 'white' }}>
                {slide.role === '封面图' ? (
                  <>
                    <p className="text-xs font-semibold mb-1" style={{ color: '#111' }}>{slide.headline}</p>
                    <p className="text-xs" style={{ color: '#6b7280' }}>{slide.subtitle}</p>
                  </>
                ) : (
                  <p className="text-xs leading-relaxed whitespace-pre-line" style={{ color: '#374151' }}>
                    {(slide.body || '').replace(/\\n/g, '\n')}
                  </p>
                )}
              </div>
            </div>
          ))}

          {slides.length === 0 && (
            <p className="text-sm text-center py-8" style={{ color: '#9ca3af' }}>内容生成失败，请重试</p>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/BriefingPage.jsx
git commit -m "feat: add XiaohongshuModal component to BriefingPage"
```

---

## Task 5: Add publishing state and 小红书 button to OpportunityRadar

**Files:**
- Modify: `frontend/src/pages/BriefingPage.jsx`

- [ ] **Step 1: Add state variables to OpportunityRadar**

In `OpportunityRadar`, find the existing state declarations (lines ~340-342):
```jsx
const [current, setCurrent] = useState(0)
const [saved, setSaved] = useState(new Set())
const [skipped, setSkipped] = useState(new Set())
```

Add two more lines immediately after:
```jsx
const [publishing, setPublishing] = useState(false)
const [xhsResult, setXhsResult] = useState(null)
```

- [ ] **Step 2: Add handlePublishXhs function**

After the `handleSkip` function (around line 392), add:

```jsx
async function handlePublishXhs() {
  setPublishing(true)
  try {
    const res = await fetch(`/api/social/xiaohongshu/generate?date=${date}`, { method: 'POST' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    setXhsResult(data)
  } catch (e) {
    console.error('xiaohongshu generate failed:', e)
  } finally {
    setPublishing(false)
  }
}
```

- [ ] **Step 3: Add the button to the toolbar**

In the toolbar `<div className="flex items-center gap-3">` (around line 413), insert the 小红书 button **before** the "搜索机会" button:

```jsx
<button
  onClick={handlePublishXhs}
  disabled={publishing || loading}
  className="text-xs px-3 py-1.5 rounded border font-medium transition-all disabled:opacity-40"
  style={{
    color: '#ff2442',
    borderColor: '#ff2442',
    backgroundColor: publishing ? '#fff0f2' : '#fff',
  }}>
  {publishing
    ? <span className="flex items-center gap-1.5">
        <span style={{ animation: 'pulse 1s ease-in-out infinite' }}>●</span>
        生成中...
      </span>
    : '📕 发小红书'}
</button>
```

- [ ] **Step 4: Render the modal**

After the closing `</div>` of the main `OpportunityRadar` return block (after the last `</div>` before the closing of the function's return), add the modal render. Find the end of the return statement — the last `</div>` that closes the outer `<div className="px-6 py-4 border-b"` — and change it from:

```jsx
    </div>
  )
}
```

to:

```jsx
    </div>

    {xhsResult && (
      <XiaohongshuModal result={xhsResult} onClose={() => setXhsResult(null)} />
    )}
  )
}
```

Wait — the return must be wrapped in a Fragment since we're adding a sibling. Change the return block structure:

Find:
```jsx
  return (
    <div className="px-6 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
```

Change to:
```jsx
  return (
    <>
    <div className="px-6 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
```

And find the last `</div>` closing the main div at the bottom of the return (the one that closes `<div className="px-6 py-4 border-b"`):
```jsx
    </div>
  )
```

Change to:
```jsx
    </div>
    {xhsResult && (
      <XiaohongshuModal result={xhsResult} onClose={() => setXhsResult(null)} />
    )}
    </>
  )
```

- [ ] **Step 5: Verify the frontend compiles**

```bash
cd /Users/shitaosun/Project/AI-Anything/token-burn/frontend
pnpm run build 2>&1 | tail -20
```
Expected: build completes with no errors (warnings are OK).

- [ ] **Step 6: Manual smoke test**

1. Start backend: `cd backend && uvicorn main:app --reload --port 8001`
2. Start frontend: `cd frontend && pnpm dev`
3. Open `http://localhost:5174`, navigate to today's briefing
4. Scroll to 机会雷达 section
5. Confirm "📕 发小红书" button appears in the header toolbar
6. Click it → button shows "● 生成中..." 
7. After 20-40s, modal opens with 3 tabs and 5 slides each
8. Click "复制" on a slide → button shows "✓ 已复制" briefly
9. Click "复制全部文案" → copies all 5 slides of current tab
10. Click outside modal or ✕ → modal closes

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/BriefingPage.jsx
git commit -m "feat: add 小红书 publish button and preview modal to 机会雷达"
```

---

## Self-Review Checklist

### Spec coverage
- [x] "📕 发小红书" button in header toolbar → Task 5 Step 3
- [x] Generates top-3 by total_score → Task 3 router takes `[:3]` after sort
- [x] 5-slide format per spec → Task 2 prompt
- [x] Saves to `data/social_posts/xiaohongshu/{date}.json` → Task 1 + Task 3 Step 1
- [x] Preview modal with tabs → Task 4
- [x] Per-slide copy buttons → Task 4 `handleCopySlide`
- [x] Copy-all button → Task 4 `handleCopyAll`
- [x] Caching (no re-gen on second click) → Task 3 router cache check
- [x] Extensible for 即刻/Twitter → `PLATFORM_GENERATORS` dict in social_poster.py

### Type consistency
- `generate_social_post(date, platform, top3_opps)` defined in Task 2, called in Task 3 ✓
- `load_social_post(date, platform)` / `save_social_post(date, platform, data)` defined in Task 1, used in Task 3 ✓
- `result.top3[n].slides[n].role` / `.headline` / `.subtitle` / `.body` used consistently in Task 4 ✓
- `XiaohongshuModal` props `{ result, onClose }` defined in Task 4, consumed in Task 5 ✓
