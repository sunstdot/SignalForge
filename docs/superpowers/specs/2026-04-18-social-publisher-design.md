# Social Publisher — Design Spec

**Date:** 2026-04-18  
**Scope:** 小红书内容生成，可扩展至即刻、Twitter

---

## Overview

在"机会雷达"头部工具栏加一个"📕 发小红书"按钮。点击后 AI 从当日 top-3 商业机会中生成符合小红书图集格式的 5 张图文案，展示在预览 Modal 中，用户可逐张或一次性复制。内容同时缓存到 `data/social_posts/xiaohongshu/{date}.json`。

架构以"平台策略字典"为扩展点，未来加即刻/Twitter 只需加一个函数 + 一条注册记录。

---

## Backend

### New: `backend/services/social_poster.py`

```
generate_social_post(date, platform, top3_opps) -> dict
```

内部维护平台策略字典：

```python
PLATFORM_GENERATORS = {
    "xiaohongshu": _generate_xiaohongshu,
    # "jike": _generate_jike,
    # "twitter": _generate_twitter,
}
```

`_generate_xiaohongshu(date, top3_opps)` 使用 Claude API（与 `briefing.py` 相同的 client），对每个 opportunity 生成 5 张图的文案，返回结构化 JSON。

**Prompt 策略（小红书）：**
- 角色：大厂前端 TL，每天用 AI 情报系统扫描技术趋势
- 封面图（图1）：大标题 + 副标题，用"今天 AI 帮我挖到了 1 个搞钱盲区 💰"句式，副标题为具体产品方向
- 图2（痛点与市场）：目标用户 + 核心痛点 + 市场规模，emoji 分点
- 图3（MVP功能与壁垒）：核心功能 + 商业模式 + 竞争壁垒，简洁可读
- 图4（TL私房话）：以"作为前端开发"开头，评价技术实现难度，给独立开发者建议，口语化
- 图5（引流钩子）：固定模板，引导评论区回复【洞察】

返回格式：
```json
{
  "platform": "xiaohongshu",
  "date": "2026-04-18",
  "generated_at": "ISO timestamp",
  "top3": [
    {
      "opportunity_title": "...",
      "total_score": 20,
      "slides": [
        { "slide": 1, "role": "封面图", "headline": "...", "subtitle": "..." },
        { "slide": 2, "role": "痛点与市场", "body": "..." },
        { "slide": 3, "role": "MVP功能与壁垒", "body": "..." },
        { "slide": 4, "role": "TL私房话", "body": "..." },
        { "slide": 5, "role": "引流钩子", "body": "..." }
      ]
    }
  ]
}
```

### New: `backend/routers/social.py`

**Endpoint:**
```
POST /api/social/{platform}/generate?date=YYYY-MM-DD
```

流程：
1. 校验 platform 是否在 `PLATFORM_GENERATORS` 中，否则返回 400
2. 读取 `data/opportunities/{date}.json`，按 `total_score` 降序取 top 3
3. 如果 `data/social_posts/{platform}/{date}.json` 已存在且无 `?refresh=true`，直接返回缓存
4. 调用 `generate_social_post()`
5. 保存到 `data/social_posts/{platform}/{date}.json`
6. 返回生成内容

**错误处理：**
- 当日 opportunities 不存在 → 400，提示先生成机会雷达
- platform 不支持 → 400

### `backend/services/storage.py` 新增

```python
load_social_post(date, platform) -> Optional[dict]
save_social_post(date, platform, data: dict)
```

路径：`data/social_posts/{platform}/{date}.json`

### `backend/main.py`

注册新路由：
```python
from routers import social
app.include_router(social.router, prefix="/api")
```

---

## Frontend

### Button — `BriefingPage.jsx` `OpportunityRadar` 组件

在头部工具栏 `<div className="flex items-center gap-3">` 中，"搜索机会"按钮之前插入：

```jsx
<button onClick={handlePublishXhs} disabled={publishing || loading}
  style={{ color: '#ff2442', borderColor: '#ff2442', background: publishing ? '#fff0f2' : '#fff' }}>
  {publishing ? '生成中...' : '📕 发小红书'}
</button>
```

新增状态：
- `publishing: boolean`
- `xhsResult: object | null`（生成结果，驱动 Modal 展示）

`handlePublishXhs` 逻辑：
1. 设 `publishing = true`
2. `POST /api/social/xiaohongshu/generate?date={date}`
3. 成功 → `setXhsResult(data)`，Modal 自动弹出
4. 失败 → console.error（后续可加 toast）
5. 最终 `publishing = false`

### New: `XiaohongshuModal` 组件（同文件内）

Props: `result: object, onClose: () => void`

结构：
- **Header**：标题 + "复制全部文案" 按钮 + 关闭按钮
- **Tabs**：3 个 tab 对应 top-3 机会，显示机会名称
- **Slides list**：5 个卡片，封面图用红色渐变 header，其余灰色
  - 每个卡片右上角"复制"按钮，点击后变"✓ 已复制"并 1.5s 后恢复
- "复制全部文案"：将当前 tab 的 5 张图文案拼成纯文本复制到剪贴板

**复制逻辑**（单张）：`navigator.clipboard.writeText(slideText)`

**复制全部**：将 5 张 slides 的 role + 内容拼接为 markdown 格式字符串

---

## Data Storage

```
data/
└── social_posts/
    ├── xiaohongshu/
    │   └── YYYY-MM-DD.json
    ├── jike/          ← 未来
    │   └── ...
    └── twitter/       ← 未来
        └── ...
```

---

## Extensibility

加新平台（以即刻为例）：
1. `social_poster.py`：新增 `_generate_jike()` 函数，注册到 `PLATFORM_GENERATORS["jike"]`
2. `BriefingPage.jsx`：新增"即刻"按钮，调用同一端点 `/api/social/jike/generate`
3. 复用同一个通用 Modal 组件，或为即刻定制 Modal（即刻是长文，格式不同）

后端无需改动其他任何文件。

---

## Out of Scope

- 直接发布到小红书 API（需官方资质，手动复制粘贴）
- 生成配套图片（仅文案）
- 多语言版本
