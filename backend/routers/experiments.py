"""实验和想法相关 API"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from services.experiments import (
    get_experiment_ideas, get_experiment_idea_by_id, create_experiment_idea,
    update_idea_status, delete_idea, get_ideas_stats,
    get_experiments, get_experiment_by_id, create_experiment,
    update_experiment, delete_experiment,
    get_experiment_logs, add_experiment_log
)
from services.briefing_generator import get_briefing_by_date
from services.llm_client import chat_async

router = APIRouter()


# ============== 实验想法相关 ==============

class CreateIdeaRequest(BaseModel):
    content_id: str = ""
    title: str
    description: str
    difficulty: str = "medium"
    estimated_days: int = 7
    tags: List[str] = []
    status: str = "pending"
    priority: float = 0
    briefing_date: str = ""
    source_type: str = ""
    source_title: str = ""
    source_url: str = ""


@router.get("/ideas")
async def list_ideas(status: Optional[str] = Query(None)):
    """获取实验想法列表"""
    ideas = get_experiment_ideas(status)
    return {"ideas": ideas}


@router.get("/ideas/stats")
async def ideas_stats():
    """获取想法统计"""
    return get_ideas_stats()


@router.get("/ideas/{idea_id}")
async def get_idea(idea_id: str):
    """获取单个想法"""
    idea = get_experiment_idea_by_id(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.post("/ideas")
async def create_idea(request: CreateIdeaRequest):
    """创建实验想法"""
    idea = create_experiment_idea(request.dict())
    return idea


@router.put("/ideas/{idea_id}/status")
async def update_idea(idea_id: str, request: dict):
    """更新想法状态"""
    status = request.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Status required")
    
    idea = update_idea_status(idea_id, status)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.delete("/ideas/{idea_id}")
async def remove_idea(idea_id: str):
    """删除想法"""
    success = delete_idea(idea_id)
    if not success:
        raise HTTPException(status_code=404, detail="Idea not found")
    return {"message": "Idea deleted"}


# ============== AI 生成想法 ==============

@router.post("/generate-ideas")
async def generate_ideas(request: dict):
    """基于简报内容生成实验想法"""
    date = request.get("date")
    if not date:
        raise HTTPException(status_code=400, detail="Date required")
    
    # 获取简报
    briefing = get_briefing_by_date(date)
    if not briefing or not briefing.get("items"):
        raise HTTPException(status_code=404, detail="No briefing found")
    
    # 筛选高相关性内容
    items = briefing["items"]
    papers = [i for i in items if i.get("source_type") == "arxiv"][:2]
    repos = [i for i in items if i.get("source_type") in ["repo", "github"]][:2]
    news = [i for i in items if i.get("source_type") in ["rss", "smolai", "news"]][:2]
    
    items_to_process = papers + repos + news
    generated = []
    
    for item in items_to_process:
        try:
            if not item.get("summary"):
                continue

            source_type = item.get("source_type", "news")
            if source_type == "arxiv":
                prompt = _get_paper_prompt(item)
            elif source_type in ["repo", "github"]:
                prompt = _get_repo_prompt(item)
            else:
                prompt = _get_news_prompt(item)

            content = await chat_async(
                [{"role": "user", "content": prompt}],
                system_prompt="你是一个专业的实验设计助手，帮助用户从内容中提取可实践的实验想法。只输出指定格式的内容。",
            )
            parsed = _parse_idea_response(content, item)
            
            if parsed:
                idea = create_experiment_idea({
                    "content_id": item["id"],
                    "title": parsed["title"],
                    "description": parsed["description"],
                    "difficulty": parsed["difficulty"],
                    "estimated_days": parsed["days"],
                    "tags": parsed["tags"],
                    "status": "pending",
                    "priority": item.get("relevance_score", 0),
                    "briefing_date": date,
                    "source_type": source_type,
                    "source_title": item["title"],
                    "source_url": item["url"]
                })
                generated.append(idea)
                
        except Exception as e:
            print(f"Failed to generate idea for {item.get('title', 'unknown')}: {e}")
            # 创建备用想法
            fallback = _create_fallback_idea(item, date)
            if fallback:
                idea = create_experiment_idea(fallback)
                generated.append(idea)
    
    return {"ideas": generated, "count": len(generated)}


@router.post("/generate-ideas/item")
async def generate_ideas_for_item(request: dict):
    """针对单条简报内容生成产品思路，返回结构化的产品概念"""
    item = request.get("item")
    if not item:
        raise HTTPException(status_code=400, detail="Item required")

    user_hint = (request.get("user_hint") or "").strip()[:500]

    title = item.get("title", "")
    content = (
        item.get("chinese_summary")
        or item.get("summary")
        or item.get("original_content")
        or item.get("raw_text")
        or ""
    )
    source = item.get("source", "")
    url = item.get("url", "")
    source_type = item.get("source_type", "news")
    chinese_insights = item.get("chinese_insights", [])

    insights_text = "\n".join(f"- {i}" for i in chinese_insights) if chinese_insights else ""

    prompt = f"""你是一个帮助技术人员发掘实践机会的助手。基于以下文章内容，生成 2-3 个具体可执行的实验想法。

文章标题: {title}
来源: {source}
链接: {url}
内容摘要:
{content}
{f"关键洞察:{chr(10)}{insights_text}" if insights_text else ""}

对每个想法，请用 JSON 数组格式输出，每个元素包含以下字段：
- title: 想法标题（20字以内）
- why: 这个想法为什么从该文章产生，和文章哪些内容有关（2-3句话）
- value: 这个想法的技术或业务价值（2-3句话）
- help: 对你个人/团队的具体帮助是什么（1-2句话）
- difficulty: easy / medium / hard
- estimated_days: 预计需要几天（数字）
- tags: 相关标签列表（2-4个）

只输出 JSON 数组，不要其他文字。格式示例：
[
  {{
    "title": "...",
    "why": "...",
    "value": "...",
    "help": "...",
    "difficulty": "medium",
    "estimated_days": 5,
    "tags": ["标签1", "标签2"]
  }}
]
"""

    if user_hint:
        prompt += f"\n\n用户方向提示（请优先围绕此方向生成想法，但仍需结合文章内容）:\n{user_hint}"

    import json as _json

    try:
        raw = (await chat_async([{"role": "user", "content": prompt}])).strip()

        # 尝试解析 JSON
        import re
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            ideas = _json.loads(match.group(0))
        else:
            ideas = _json.loads(raw)

        return {
            "ideas": ideas,
            "source_title": title,
            "source_url": url,
            "source": source
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)[:200]}")


def _get_paper_prompt(item):
    return f"""基于以下论文，设计一个可复现的实验想法：

标题: {item['title']}
摘要: {item['summary']}

要求：
1. 标题简洁（20字以内）
2. 描述包含：核心思路、实现步骤、成功标准、可能挑战
3. 难度：easy/medium/hard
4. 预计天数：3-14天
5. 标签：2-4个相关技术标签

输出格式：
TITLE: [标题]
DESCRIPTION:
[详细描述]
DIFFICULTY: [难度]
DAYS: [天数]
TAGS: [标签1, 标签2, ...]"""


def _get_repo_prompt(item):
    return f"""基于以下开源项目，设计一个学习/实验想法：

标题: {item['title']}
描述: {item['summary']}

要求：
1. 标题简洁（20字以内）
2. 描述包含：实验目标、具体任务、预期产出、学习价值
3. 难度：easy/medium/hard
4. 预计天数：2-7天
5. 标签：2-4个相关技术标签

输出格式：
TITLE: [标题]
DESCRIPTION:
[详细描述]
DIFFICULTY: [难度]
DAYS: [天数]
TAGS: [标签1, 标签2, ...]"""


def _get_news_prompt(item):
    return f"""基于以下技术资讯，设计一个探索性实验：

标题: {item['title']}
内容: {item['summary']}

要求：
1. 标题简洁（20字以内）
2. 描述包含：背景与问题、验证思路、实验设计、价值输出
3. 难度：easy/medium/hard
4. 预计天数：3-7天
5. 标签：2-4个相关技术标签

输出格式：
TITLE: [标题]
DESCRIPTION:
[详细描述]
DIFFICULTY: [难度]
DAYS: [天数]
TAGS: [标签1, 标签2, ...]"""


def _parse_idea_response(text, item):
    """解析 AI 响应"""
    try:
        import re
        title_match = re.search(r'TITLE:\s*([^\n]+)', text)
        desc_match = re.search(r'DESCRIPTION:\s*([\s\S]+?)(?=DIFFICULTY:|$)', text)
        diff_match = re.search(r'DIFFICULTY:\s*(easy|medium|hard)', text, re.I)
        days_match = re.search(r'DAYS:\s*(\d+)', text)
        tags_match = re.search(r'TAGS:\s*([^\n]+)', text)
        
        title = title_match.group(1).strip() if title_match else f"实验: {item['title'][:30]}"
        description = desc_match.group(1).strip() if desc_match else item.get("summary", "")
        difficulty = (diff_match.group(1).lower() if diff_match else "medium")
        days = int(days_match.group(1)) if days_match else 7
        tags = [t.strip() for t in tags_match.group(1).split(",")] if tags_match else item.get("category", [])[:3]
        
        return {
            "title": title,
            "description": description,
            "difficulty": difficulty,
            "days": days,
            "tags": tags
        }
    except Exception as e:
        print(f"Parse error: {e}")
        return None


def _create_fallback_idea(item, date):
    """创建备用想法"""
    source_type = item.get("source_type", "news")
    
    if source_type == "arxiv":
        return {
            "content_id": item["id"],
            "title": f"复现: {item['title'][:40]}",
            "description": f"【论文复现】基于论文核心方法进行小规模复现实验。\n\n论文要点:\n{item.get('summary', '')[:300]}...\n\n建议步骤:\n1. 理解论文核心算法\n2. 实现简化版本\n3. 在示例数据上验证\n4. 记录复现过程和差异",
            "difficulty": "hard",
            "estimated_days": 14,
            "tags": item.get("category", [])[:3],
            "status": "pending",
            "priority": item.get("relevance_score", 0),
            "briefing_date": date,
            "source_type": source_type,
            "source_title": item["title"],
            "source_url": item["url"]
        }
    elif source_type in ["repo", "github"]:
        return {
            "content_id": item["id"],
            "title": f"探索: {item['title'][:40]}",
            "description": f"【工具探索】深度试用并分析该开源项目。\n\n项目介绍:\n{item.get('summary', '')[:300]}...\n\n建议任务:\n1. 安装并运行示例\n2. 阅读核心源码\n3. 尝试自定义修改\n4. 写学习笔记或教程",
            "difficulty": "easy",
            "estimated_days": 3,
            "tags": item.get("category", [])[:3],
            "status": "pending",
            "priority": item.get("relevance_score", 0),
            "briefing_date": date,
            "source_type": source_type,
            "source_title": item["title"],
            "source_url": item["url"]
        }
    else:
        return {
            "content_id": item["id"],
            "title": f"验证: {item['title'][:40]}",
            "description": f"【趋势验证】基于该资讯的技术趋势进行验证实验。\n\n资讯要点:\n{item.get('summary', '')[:300]}...\n\n验证思路:\n1. 提炼关键技术点\n2. 构建验证原型\n3. 对比测试\n4. 输出结论报告",
            "difficulty": "medium",
            "estimated_days": 5,
            "tags": item.get("category", [])[:3],
            "status": "pending",
            "priority": item.get("relevance_score", 0),
            "briefing_date": date,
            "source_type": source_type,
            "source_title": item["title"],
            "source_url": item["url"]
        }


# ============== 实验相关 ==============

class CreateExperimentRequest(BaseModel):
    title: str
    description: str = ""
    status: str = "planning"
    idea_id: Optional[str] = None
    target_days: Optional[int] = None
    tech_stack: List[str] = []


@router.get("")
async def list_experiments(status: Optional[str] = Query(None)):
    """获取实验列表"""
    experiments = get_experiments(status)
    return {"experiments": experiments}


@router.get("/{exp_id}")
async def get_experiment(exp_id: str):
    """获取单个实验"""
    exp = get_experiment_by_id(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.post("")
async def create_exp(request: CreateExperimentRequest):
    """创建实验"""
    exp = create_experiment(request.dict())
    return exp


@router.put("/{exp_id}")
async def update_exp(exp_id: str, request: dict):
    """更新实验"""
    exp = update_experiment(exp_id, request)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.delete("/{exp_id}")
async def remove_exp(exp_id: str):
    """删除实验"""
    success = delete_experiment(exp_id)
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"message": "Experiment deleted"}


# ============== 实验日志 ==============

@router.get("/{exp_id}/logs")
async def list_logs(exp_id: str):
    """获取实验日志"""
    logs = get_experiment_logs(exp_id)
    return {"logs": logs}


@router.post("/{exp_id}/logs")
async def create_log(exp_id: str, request: dict):
    """添加实验日志"""
    content = request.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Content required")
    log = add_experiment_log(exp_id, content)

    # 如果需要更新状态
    if request.get("status"):
        update_experiment(exp_id, {"status": request["status"]})

    return log


@router.post("/{exp_id}/ideas")
async def generate_concept_for_experiment(exp_id: str, request: dict):
    """为选定实验生成完整的产品思路 (Markdown)，并缓存到实验记录中"""
    exp = get_experiment_by_id(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    content = request.get("content", "") or exp.get("description", "")
    if not content:
        raise HTTPException(status_code=400, detail="Experiment description/content required")

    prompt = f"""你是一位经验丰富的产品经理和创业顾问。基于以下实验初步描述，帮我进行深度产品头脑风暴，输出一份完整的【产品思路与实施草案】。

实验/想法描述:
{content}

请输出完整的 Markdown 格式报告，包含以下章节：
1. 💡 **一句话产品定位**：这款产品的本质是什么，解决什么问题。
2. 🎯 **目标用户与核心痛点**：谁会最需要它？他们目前最痛的点是什么？
3. ⚙️ **核心功能定义**：3-5个最关键的功能方向。
4. 🛠️ **技术栈建议**：推荐的前端/后端/AI组件选型及理由。
5. 💰 **商业价值与变现潜力**：能带来什么业务价值或如何变现？
6. 🗺️ **MVP 实施路径**：从 0 到 1 的开发计划（分为3-4个阶段，每阶段注明预计天数）。
7. ⚠️ **最大风险与破局点**：最容易失败的地方在哪里，如何防范。
8. 🤖 **Vibe Coding 启动提示词**：一段可直接粘贴给 AI 编程助手（Claude/Cursor）的 prompt，描述要构建的产品和 MVP 范围。

仅输出 Markdown 格式的报告正文，不要包含多余的客套话。"""

    from services.storage import update_experiment_by_id
    from datetime import datetime as _dt

    try:
        markdown_result = (await chat_async([{"role": "user", "content": prompt}])).strip()

        # 持久化到实验记录
        update_experiment_by_id(exp_id, {
            "product_concept": {
                "content": markdown_result,
                "generated_at": _dt.now().isoformat(),
            }
        })

        return {"ideas": markdown_result, "cached": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成产品思路失败: {str(e)[:200]}")
