"""简报相关 API"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.briefing_generator import get_briefing_by_date, get_latest_briefing, get_briefing_markdown
from services.llm_client import chat, chat_async
from services.storage import (
    load_category_digest, save_category_digest,
    load_opportunities, save_opportunities,
    load_rdev_opportunities, save_rdev_opportunities,
)

router = APIRouter()


async def _analyze_items_for_opportunities(items, date):
    """对给定 items 批量调用 AI 分析商业机会，返回有机会的条目列表（使用 DeepSeek）"""
    import re, json as _json

    BATCH_SIZE = 10
    all_opps = []

    for batch_start in range(0, len(items), BATCH_SIZE):
        batch = items[batch_start:batch_start + BATCH_SIZE]

        items_text = ""
        for idx, item in enumerate(batch, 1):
            content = (item.get("summary") or item.get("original_content") or "")[:500]
            items_text += (
                f"\n[{idx}] 标题: {item['title']}\n"
                f"    来源: {item['source']} ({item.get('source_type', '')})\n"
                f"    内容: {content}\n"
            )

        prompt = f"""你是一位经验丰富的 AI 产品经理和连续创业者，擅长从技术情报中发现真实可落地的商业机会。

# 开发者背景
- 独立开发者，无团队
- 技术栈：Python / Next.js
- 可接受面向全球或中文市场的产品，无需强行本地化

# 今日情报（{date}，共 {len(batch)} 条）
<ai_intelligence>
{items_text}
</ai_intelligence>

# 分析规则

## 什么情况下有商业机会（has_opportunities: true）
满足以下任一条件：
- 情报中有**具体的技术能力突破**（速度、精度、成本、新能力），能直接支撑一个产品想法
- 某个开源工具/模型的**特定功能**，可以被包装成面向非开发者的付费产品
- **成本骤降**使得此前不可行的商业模式变得可行
快速浏览所有情报，识别以下几类关键信号：
-- **技术跃迁信号**：某项能力出现了质的飞跃（速度、精度、成本、可用性）
-- **能力空白信号**：新模型/工具解锁了此前无法实现的某类功能，在当前市场上，这项技术可以解决哪些行业（如
    -效率工具、开发者工具、内容创作、电商营销等）的痛点？
-- **成本骤降信号**：某类AI能力的使用成本大幅下降，原本不可行的商业模式变得可行
-- **巨头盲区信号**：大公司发布的工具主要服务开发者/企业，但普通用户/中小企业仍未被满足
-- **组合创新信号**：多项技术叠加后，可以创造此前不存在的产品体验
-- **技术降维映射**：这项新技术/新模型/新项目，能大幅降低哪类任务的成本？或者能创造什么以前做不到的交互
    -体验？
-- **聚焦应用层与体验**：摒弃大厂在拼的底层算力和基础模型，将视角聚焦在”应用层”。思考如何通过优秀的前端/
    -客户端 UI 设计、结合 AI Agent 工作流，将这项技术包装成一个用户愿意付费的完整产品。

## 什么情况下没有商业机会（has_opportunities: false）
以下情况直接标记为 false，不要强行生成 idea：
- 纯商业新闻（融资、收购、人事变动）
- 只是某个工具的新版本发布，无实质能力提升
- 学术论文，缺乏工程化路径
- 情报内容过于笼统，找不到**可以直接使用的具体技术**

## 溯源要求（最重要）
**每个 idea 必须能回答：「情报中的哪句话/哪个具体能力，让这个产品现在可行？」**
- 禁止从情报标题联想出与内容无关的产品
- 禁止因为约束里有”中文用户”就强行加上”中文版”
- 如果找不到清晰的技术→产品因果链，设 has_opportunities: false

# 输出格式（严格遵守）

只输出一个 JSON 数组，不要任何解释文字、不要 markdown 代码块。
所有字符串字段必须是单行字符串，不得包含换行符。

[
  {{
    "idx": 1,
    "has_opportunities": true,
    "ideas": [
      {{
        "title": "产品方向名称（30字以内）",
        "trigger": "情报中触发此想法的具体能力或数据点（原文引用或紧密改写，30字以内）",
        "core_insight": "这个技术能力如何直接支撑这个产品，之前为何不可行（60字以内，单行）",
        "product_form": "帮助[目标用户]解决[具体问题]的[产品类型]（单行）",
        "target_users": "用户画像：职业/场景/痛点/付费意愿（40字以内，单行）",
        "mvp_features": ["核心功能1", "核心功能2", "核心功能3"],
        "business_model": "盈利方式及定价（30字以内，单行）",
        "risks": "最大风险（40字以内，单行）",
        "scores": {{
          "pain_point": 4,
          "market_size": 3,
          "tech_timing": 5,
          "buildability": 4
        }}
      }}
    ]
  }}
]

评分标准（1-5 整数）：
- pain_point：痛点真实程度和用户痛苦程度
- market_size：潜在付费用户规模
- tech_timing：技术窗口期，现在做是否是最佳时机
- buildability：独立开发者能否在 1 个月内做出 MVP

没有商业机会的条目：has_opportunities 为 false，ideas 为空数组 []。"""

        try:
            raw = (await chat_async([{"role": "user", "content": prompt}], provider="deepseek")).strip()
            raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            batch_result = _json.loads(match.group(0) if match else raw)

            for entry in batch_result:
                if not entry.get("has_opportunities") or not entry.get("ideas"):
                    continue
                real_idx = batch_start + entry["idx"] - 1
                if real_idx >= len(items):
                    continue
                source_item = items[real_idx]
                for idea in entry["ideas"]:
                    scores = idea.get("scores", {})
                    total = sum(scores.values())
                    all_opps.append({
                        "opportunity_title": idea.get("title", ""),
                        "core_insight": idea.get("core_insight", ""),
                        "product_form": idea.get("product_form", ""),
                        "target_users": idea.get("target_users", ""),
                        "mvp_features": idea.get("mvp_features", []),
                        "business_model": idea.get("business_model", ""),
                        "competitive_barrier": idea.get("competitive_barrier", ""),
                        "risks": idea.get("risks", ""),
                        "scores": scores,
                        "total_score": total,
                        "source_title": source_item["title"],
                        "source": source_item["source"],
                        "source_type": source_item.get("source_type", ""),
                        "source_url": source_item["url"],
                        "item_id": source_item["id"],
                    })  
        except Exception as e:
            print(f"[opportunities] batch {batch_start} failed: {e}")

    return all_opps


class BriefingResponse(BaseModel):
    id: str
    date: str
    items: list
    summary: Optional[str]
    generated_at: str


@router.get("/latest")
async def get_latest():
    """获取最新简报"""
    briefing = get_latest_briefing()
    if not briefing:
        raise HTTPException(status_code=404, detail="No briefing found")
    return briefing


@router.get("/{date}")
async def get_briefing(date: str):
    """获取指定日期的简报"""
    import re
    
    # 验证日期格式
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    briefing = get_briefing_by_date(date)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return briefing


@router.get("/{date}/opportunities")
async def get_opportunities(date: str, refresh: bool = False):
    """获取机会雷达（命中缓存直接返回，否则循环分析直到产出 20 个机会）"""
    import re, json as _json
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format")

    if not refresh:
        cached = load_opportunities(date)
        if cached:
            # 动态计算 remaining，避免老缓存 remaining=0 导致按钮消失
            briefing_for_remaining = get_briefing_by_date(date)
            if briefing_for_remaining:
                analyzed_ids_set = set(cached.get("analyzed_item_ids", []))
                cached["remaining"] = len([i for i in briefing_for_remaining["items"] if i["id"] not in analyzed_ids_set])
            return cached

    briefing = get_briefing_by_date(date)
    if not briefing or not briefing.get("items"):
        raise HTTPException(status_code=404, detail="Briefing not found")

    MIN_OPPS = 20
    BATCH_ITEMS = 20   # 每轮分析 20 条（2 次 AI 调用）
    MAX_ITEMS = 120    # 安全上限，防止超时

    all_items = briefing["items"]
    items_sorted = sorted(all_items, key=lambda x: -x.get("relevance_score", 0))

    all_opps: list = []
    analyzed_items: list = []
    offset = 0

    while len(all_opps) < MIN_OPPS and offset < len(items_sorted) and offset < MAX_ITEMS:
        batch = items_sorted[offset:offset + BATCH_ITEMS]
        batch_opps = await _analyze_items_for_opportunities(batch, date)
        all_opps.extend(batch_opps)
        analyzed_items.extend(batch)
        offset += len(batch)

    # 去重（以 source_url + opportunity_title 为主键）并按总分排序
    seen_keys: set = set()
    deduped = []
    for opp in sorted(all_opps, key=lambda x: -x["total_score"]):
        key = (opp.get("source_url", ""), opp.get("opportunity_title", ""))
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(opp)

    analyzed_ids = [i["id"] for i in analyzed_items]
    remaining_count = len(all_items) - len(analyzed_items)
    result = {"date": date, "opportunities": deduped, "analyzed_item_ids": analyzed_ids, "remaining": remaining_count}
    save_opportunities(date, result)
    return result


@router.post("/{date}/opportunities/search")
async def search_more_opportunities(date: str):
    """从未分析过的情报中搜索新机会，循环直到产出 10 个新机会，合并追加到已有缓存"""
    import re, json as _json
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format")

    briefing = get_briefing_by_date(date)
    if not briefing or not briefing.get("items"):
        raise HTTPException(status_code=404, detail="Briefing not found")

    cached = load_opportunities(date) or {"date": date, "opportunities": [], "analyzed_item_ids": []}
    analyzed_ids = set(cached.get("analyzed_item_ids", []))

    unanalyzed = [i for i in briefing["items"] if i["id"] not in analyzed_ids]
    if not unanalyzed:
        return {**cached, "searched": 0, "remaining": 0, "message": "所有情报均已分析完毕"}

    MIN_NEW_OPPS = 10
    BATCH_ITEMS = 20   # 每轮分析 20 条
    MAX_ITEMS = 80     # 安全上限

    unanalyzed.sort(key=lambda x: -x.get("relevance_score", 0))

    new_opps: list = []
    newly_analyzed: list = []
    offset = 0

    while len(new_opps) < MIN_NEW_OPPS and offset < len(unanalyzed) and offset < MAX_ITEMS:
        batch = unanalyzed[offset:offset + BATCH_ITEMS]
        batch_opps = await _analyze_items_for_opportunities(batch, date)
        new_opps.extend(batch_opps)
        newly_analyzed.extend(batch)
        offset += len(batch)

    # 合并 + 去重（以 source_url + opportunity_title 为主键）
    seen_keys: set = set()
    deduped = []
    for opp in cached["opportunities"] + new_opps:
        key = (opp.get("source_url", ""), opp.get("opportunity_title", ""))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(opp)

    deduped.sort(key=lambda x: -x["total_score"])

    new_analyzed_ids = list(analyzed_ids) + [i["id"] for i in newly_analyzed]
    remaining_count = len(briefing["items"]) - len(new_analyzed_ids)
    result = {
        "date": date,
        "opportunities": deduped,
        "analyzed_item_ids": new_analyzed_ids,
        "remaining": remaining_count,
    }
    save_opportunities(date, result)
    return result


@router.get("/{date}/category-digest")
async def get_category_digest(date: str, refresh: bool = False):
    """获取分类摘要（命中缓存直接返回，否则 AI 生成）"""
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format")

    # 命中缓存
    if not refresh:
        cached = load_category_digest(date)
        if cached:
            return cached

    briefing = get_briefing_by_date(date)
    if not briefing or not briefing.get("items"):
        raise HTTPException(status_code=404, detail="Briefing not found")

    items = briefing["items"]

    # 按大类分组
    def classify(item):
        t = item.get("source_type", "")
        if t in ("arxiv", "paper"):
            return "paper"
        if t in ("repo", "github"):
            return "repo"
        if t == "model":
            return "model"
        return "news"

    groups = {"paper": [], "repo": [], "model": [], "news": []}
    for item in items:
        groups[classify(item)].append(item)

    CATEGORY_LABELS = {
        "paper": "论文",
        "repo": "仓库",
        "model": "模型",
        "news": "资讯",
    }

    result = {"date": date, "categories": {}}

    for cat, cat_items in groups.items():
        if not cat_items:
            result["categories"][cat] = None
            continue

        titles = "\n".join(
            f"- {i['title']}：{(i.get('summary') or '')[:120]}"
            for i in cat_items[:10]
        )
        prompt = (
            f"以下是 {date} 的 AI {CATEGORY_LABELS[cat]}类更新，共 {len(cat_items)} 条：\n\n"
            f"{titles}\n\n"
            "请用 3 句话以内，简洁地总结今天这个类别发生了什么，有哪些值得关注的趋势或亮点。"
            "直接输出总结文字，不要加标题或前缀。"
        )

        try:
            summary = (await chat_async([{"role": "user", "content": prompt}])).strip()
        except Exception as e:
            summary = None
            print(f"[category-digest] {cat} failed: {e}")

        result["categories"][cat] = {
            "summary": summary,
            "count": len(cat_items),
        }

    save_category_digest(date, result)
    return result


@router.post("/{date}/batch-quick-reads")
async def batch_quick_reads(date: str):
    """批量为有摘要的条目生成速读缓存（15条/批，跳过已缓存）"""
    import re as _re, json as _json
    if not _re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format")

    from services.storage import load_quick_reads, save_quick_read
    briefing = get_briefing_by_date(date)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")

    cached = load_quick_reads(date)
    # 有 summary 或 original_content 即可处理，跳过已缓存
    to_process = [
        i for i in briefing["items"]
        if (i.get("summary") or i.get("original_content") or i.get("raw_text"))
        and i["id"] not in cached
    ]

    if not to_process:
        return {"generated": 0, "skipped": len(cached), "message": "all cached"}

    BATCH_SIZE = 15
    generated = 0

    for batch_start in range(0, len(to_process), BATCH_SIZE):
        batch = to_process[batch_start:batch_start + BATCH_SIZE]

        items_text = "\n".join(
            f"[{idx}] 标题：{item['title']}\n    内容：{(item.get('summary') or item.get('original_content') or item.get('raw_text') or '')[:500]}"
            for idx, item in enumerate(batch, 1)
        )

        prompt = f"""以下是 {len(batch)} 篇文章的标题和摘要，请对每篇生成速读总结，输出 JSON 数组（只输出 JSON，不要 markdown 代码块）。

{items_text}

输出格式（每个字段都是单行字符串，不含换行符）：
[
  {{
    "idx": 1,
    "core": "核心内容：2-3句话概括文章",
    "points": ["要点一", "要点二", "要点三"],
    "insight": "最有价值的一个洞察（1句话）"
  }}
]

要求：中文输出，core 和 insight 为单行字符串，points 为字符串数组（3-5条）。"""

        try:
            raw = (await chat_async([{"role": "user", "content": prompt}])).strip()
            # 去掉可能的 markdown 代码块包装
            raw = _re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
            match = _re.search(r'\[.*\]', raw, _re.DOTALL)
            results = _json.loads(match.group(0) if match else raw)

            for r in results:
                real_idx = batch_start + r["idx"] - 1
                if real_idx < len(to_process):
                    item = to_process[real_idx]
                    # 拼接 Markdown（避免 AI 输出多行 JSON 字符串导致解析失败）
                    points_md = "\n".join(f"- {p}" for p in (r.get("points") or []))
                    summary = f"**核心内容**：{r.get('core', '')}\n\n**关键信息**：\n{points_md}\n\n**值得关注**：{r.get('insight', '')}"
                    save_quick_read(date, item["id"], summary)
                    generated += 1
        except Exception as e:
            print(f"[batch-quick-reads] batch {batch_start} failed: {e}")

    return {"generated": generated, "total": len(to_process), "skipped": len(cached)}


async def _analyze_items_for_rdev(items, date):
    """对情报列表进行研发效能机会分析，返回附带 source 信息的 solutions 扁平列表"""
    import re, json as _json

    BATCH_SIZE = 10
    all_solutions = []

    for batch_start in range(0, len(items), BATCH_SIZE):
        batch = items[batch_start:batch_start + BATCH_SIZE]

        items_text = ""
        for idx, item in enumerate(batch, 1):
            content = (item.get("summary") or item.get("original_content") or "")[:400]
            items_text += (
                f"\n[{idx}] 标题: {item['title']}\n"
                f"    来源: {item['source']} ({item.get('source_type', '')})\n"
                f"    内容: {content}\n"
            )

        prompt = f"""# 角色设定

你是一位深度嵌入顶级互联网大厂（拥有大前端、客户端、复杂商业化业务）的 AI 架构师兼技术顾问。你同时具备一线程序员的实战经验（深谙手撕代码、多端联调之苦）和技术管理者的全局视角（关注人效比、业务转化率）。
你深知互联网公司研发团队的真实痛点：冗长的需求评审、繁琐的 UI/组件联调、屎山代码的维护、机械的单测编写、以及永无止境的业务需求。你的任务是从每天的 AI 情报中，**尽可能多地挖掘**可以真正减少程序员”狗屎工作”、无缝切入现有工具链、或用 AI 直接赋能核心业务的落地机会。

# 核心任务

基于以下 AI 情报内容，为**互联网公司研发团队**挖掘 AI 应用落地机会。**每条情报都必须输出至少 1 个机会**，哪怕评分较低也要输出。
核心思考逻辑：**这些 AI 技术进展，哪些可以直接插入程序员的日常工作流，减少重复劳动？哪些可以包装成端侧体验，帮助商业化业务提升转化？**

<ai_intelligence>
{items_text}
</ai_intelligence>

# 分析框架

## STEP 1：情报扫描（信号提取）
快速扫描所有情报，在大脑中将其归类为以下信号（无需输出此步骤的思考过程）：
- ⚡ **开发提速信号**：能让前端切图、组件生成、API 联调、代码 Review 更快的技术。
- 🔍 **认知增强信号**：帮助程序员秒懂复杂系统、历史遗留代码、晦涩技术文档的能力。
- 🤖 **流程自动化信号**：可替代研发链路（如 CI/CD、自动化测试、甚至 PRD 转代码）某环节的 Agent 方案。
- 📈 **业务赋能信号**：能提升商业化产品端侧体验（如动态 UI、智能导购、提升信息流广告CVR、CTR）、或让产品/运营自助生成物料的技术。
- 🧱 **基础设施信号**：降低大模型接入门槛、或提升端侧/浏览器端推理性能的新工具。

## STEP 2：落地机会深度解析
**对每一条情报都必须生成 1-2 个**具体的提效或赋能机会。只有纯商业新闻（如融资、人事变动）且完全无技术内容的情报，才允许 has_solutions 为 false。

# 输出格式（严格遵守）

**只输出一个 JSON 数组，不要任何解释文字、不要 markdown 代码块。**
所有字符串字段必须是单行字符串，不得包含换行符。

[
  {{
    "idx": 1,
    "has_solutions": true,
    "solutions": [
      {{
        "type": "研发提效",
        "source_item_title": "触发此机会的情报标题（原文照抄，单行）",
        "title": "一句话方案名称（20字以内，单行）",
        "trigger": "哪条情报触发了这个机会（30字以内，单行）",
        "scenario": "在[具体场景]中，目前做法是[现有做法]，核心痛点在于[问题所在]（80字以内，单行）",
        "ai_solution": "新技术如何重构这个场景，能力边界在哪里（80字以内，单行）",
        "implementation": "具体集成形态，如VS Code插件/GitLab Webhook/飞书机器人等（60字以内，单行）",
        "audience": ["大前端", "客户端"],
        "impact": "量化预期收益（50字以内，单行）",
        "difficulty": "低",
        "resistance": "在公司内推进的主要阻力（40字以内，单行）",
        "scores": {{
          "efficiency": 8,
          "feasibility": 7,
          "business_impact": 6,
          "overall": 8
        }}
      }}
    ]
  }}
]

规则：
- **每条情报必须有 solutions，has_solutions 默认为 true**
- 仅纯商业/人事新闻（完全无技术内容）才允许 has_solutions: false
- type 只能是”研发提效”或”业务赋能”
- difficulty 只能是”低”、”中”、”高”
- scores 所有字段为 1-10 的整数
- audience 从以下选择：大前端、客户端、后端、测试、产品运营、技术TL
- source_item_title 必须原文照抄情报标题，不得改写或省略

# 严格纪律
- 语言：中文
- 禁止输出正确的废话，必须精确到”利用X模型结合Y工具在Z环节解决具体问题”
- 宁可评分低也要输出，不要遗漏任何有技术含量的情报"""

        try:
            raw = (await chat_async([{"role": "user", "content": prompt}], provider="deepseek")).strip()
            raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            batch_result = _json.loads(match.group(0) if match else raw)

            # 建立标题→item 的查找表，用于按标题纠正 source 归属
            title_to_item = {item["title"]: item for item in items}

            for entry in batch_result:
                if not entry.get("has_solutions") or not entry.get("solutions"):
                    continue
                real_idx = batch_start + entry["idx"] - 1
                if real_idx >= len(items):
                    continue
                fallback_item = items[real_idx]
                for sol in entry["solutions"]:
                    # 优先用 AI 返回的 source_item_title 精确匹配，避免 idx 错位
                    sit = sol.get("source_item_title", "")
                    source_item = title_to_item.get(sit, fallback_item)
                    scores = sol.get("scores", {})
                    all_solutions.append({
                        "type": sol.get("type", "研发提效"),
                        "title": sol.get("title", ""),
                        "trigger": sol.get("trigger", ""),
                        "scenario": sol.get("scenario", ""),
                        "ai_solution": sol.get("ai_solution", ""),
                        "implementation": sol.get("implementation", ""),
                        "audience": sol.get("audience", []),
                        "impact": sol.get("impact", ""),
                        "difficulty": sol.get("difficulty", "中"),
                        "resistance": sol.get("resistance", ""),
                        "scores": scores,
                        "total_score": scores.get("overall", 0),
                        "source_title": source_item["title"],
                        "source": source_item["source"],
                        "source_type": source_item.get("source_type", ""),
                        "source_url": source_item["url"],
                        "item_id": source_item["id"],
                    })
        except Exception as e:  
            print(f"[rdev-opportunities] batch {batch_start} failed: {e}")

    return all_solutions


@router.get("/{date}/rdev-opportunities")
async def get_rdev_opportunities(date: str, refresh: bool = False):
    """获取研发效能机会洞察（命中缓存直接返回，否则 AI 分析）"""
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format")

    if not refresh:
        cached = load_rdev_opportunities(date)
        if cached:
            return cached

    briefing = get_briefing_by_date(date)
    if not briefing or not briefing.get("items"):
        raise HTTPException(status_code=404, detail="Briefing not found")

    # 随机取 40 条，每次覆盖不同内容
    import random as _random
    items = _random.sample(briefing["items"], min(40, len(briefing["items"])))

    all_solutions = await _analyze_items_for_rdev(items, date)

    # 按综合分排序，去重（以 title 为主键）
    seen_titles: set = set()
    deduped = []
    for sol in sorted(all_solutions, key=lambda x: -x["total_score"]):
        if sol["title"] not in seen_titles:
            seen_titles.add(sol["title"])
            deduped.append(sol)

    # top_pick 取综合分最高且难度为"低"的方案，否则取最高分
    top = next((s for s in deduped if s.get("difficulty") == "低"), deduped[0] if deduped else None)
    top_pick = {
        "title": top["title"],
        "why_now": top.get("trigger", ""),
        "mvp_path": top.get("implementation", ""),
        "strategy": "自下而上：先找2-3个极客同学验证，再整理ROI数据推广",
    } if top else None

    result = {
        "date": date,
        "solutions": deduped[:20],
        "top_pick": top_pick,
        "analyzed_count": len(items),
        "analyzed_item_ids": [i["id"] for i in items],
    }
    save_rdev_opportunities(date, result)
    return result


@router.post("/{date}/rdev-opportunities/search")
async def search_more_rdev_opportunities(date: str):
    """从未分析过的情报中搜索新研发效能机会，合并到已有缓存"""
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format")

    briefing = get_briefing_by_date(date)
    if not briefing or not briefing.get("items"):
        raise HTTPException(status_code=404, detail="Briefing not found")

    cached = load_rdev_opportunities(date) or {"date": date, "solutions": [], "top_pick": None, "analyzed_item_ids": []}
    analyzed_ids = set(cached.get("analyzed_item_ids", []))

    # 取未分析过的条目（按相关度排序，每次最多 40 条）
    remaining = [i for i in briefing["items"] if i["id"] not in analyzed_ids]
    remaining.sort(key=lambda x: -x.get("relevance_score", 0))
    to_analyze = remaining[:40]

    if not to_analyze:
        return {**cached, "remaining": 0}

    new_solutions = await _analyze_items_for_rdev(to_analyze, date)

    # 合并 + 去重（以 title 为主键）
    seen_titles: set = set()
    deduped = []
    for sol in cached.get("solutions", []) + new_solutions:
        if sol["title"] not in seen_titles:
            seen_titles.add(sol["title"])
            deduped.append(sol)

    deduped.sort(key=lambda x: -x["total_score"])

    top = next((s for s in deduped if s.get("difficulty") == "低"), deduped[0] if deduped else None)
    top_pick = {
        "title": top["title"],
        "why_now": top.get("trigger", ""),
        "mvp_path": top.get("implementation", ""),
        "strategy": "自下而上：先找2-3个极客同学验证，再整理ROI数据推广",
    } if top else None

    new_analyzed_ids = list(analyzed_ids) + [i["id"] for i in to_analyze]
    result = {
        "date": date,
        "solutions": deduped[:30],
        "top_pick": top_pick,
        "analyzed_count": len(new_analyzed_ids),
        "analyzed_item_ids": new_analyzed_ids,
        "remaining": len(remaining) - len(to_analyze),
    }
    save_rdev_opportunities(date, result)
    return result


@router.get("/{date}/markdown")
async def get_briefing_md(date: str):
    """获取简报的 Markdown 格式"""
    import re

    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=400, detail="Invalid date format")

    markdown = get_briefing_markdown(date)
    return {"markdown": markdown}
