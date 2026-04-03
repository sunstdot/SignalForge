"""AI 模型平台抓取服务 - HuggingFace, CivitAI 等"""
import aiohttp
from datetime import datetime
from typing import List, Dict
import hashlib


async def fetch_model_platforms(config: Dict) -> List[Dict]:
    """抓取所有模型平台数据"""
    items = []
    platforms = config.get("platforms", [])

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for platform in platforms:
            try:
                ptype = platform.get("type", "")
                if ptype == "huggingface":
                    result = await fetch_huggingface_models(session, platform)
                elif ptype == "huggingface_papers":
                    result = await fetch_huggingface_papers(session, platform)
                elif ptype == "civitai":
                    result = await fetch_civitai_models(session, platform)
                else:
                    continue
                items.extend(result)
                if result:
                    print(f"  ✓ {platform['name']}: {len(result)} items")
            except Exception as e:
                print(f"  ✗ {platform['name']}: {str(e)[:80]}")

    return items


async def fetch_huggingface_models(session: aiohttp.ClientSession, platform: Dict) -> List[Dict]:
    """抓取 HuggingFace Trending Models"""
    url = platform.get("url", "https://huggingface.co/api/models")
    params = platform.get("params", {})
    limit = params.get("limit", 10)

    async with session.get(
        url,
        params={"sort": "trendingScore", "direction": "-1", "limit": limit},
        headers={"User-Agent": "TokenBurner/1.0"}
    ) as response:
        if response.status != 200:
            raise Exception(f"HTTP {response.status}")
        data = await response.json()

    items = []
    for model in data[:limit]:
        model_id = model.get("modelId") or model.get("id", "unknown")
        pipeline_tag = model.get("pipeline_tag", "")
        downloads = model.get("downloads", 0)
        likes = model.get("likes", 0)

        desc_parts = []
        if pipeline_tag:
            desc_parts.append(f"Task: {pipeline_tag}")
        if downloads:
            desc_parts.append(f"Downloads: {downloads:,}")
        if likes:
            desc_parts.append(f"Likes: {likes:,}")
        description = " | ".join(desc_parts) if desc_parts else model_id

        item_id = f"hf-model-{hashlib.md5(model_id.encode()).hexdigest()[:12]}"

        items.append({
            "id": item_id,
            "source": "HuggingFace Models",
            "source_type": "model",
            "title": f"🤗 {model_id}",
            "url": f"https://huggingface.co/{model_id}",
            "original_content": description,
            "raw_text": description,
            "relevance_score": 0,
            "category": platform.get("category", ["ai", "models"]),
            "created_at": datetime.now(),
        })

    return items


async def fetch_huggingface_papers(session: aiohttp.ClientSession, platform: Dict) -> List[Dict]:
    """抓取 HuggingFace Daily Papers"""
    url = platform.get("url", "https://huggingface.co/api/daily_papers")
    params = platform.get("params", {})
    limit = params.get("limit", 10)

    async with session.get(
        url,
        params={"limit": limit},
        headers={"User-Agent": "TokenBurner/1.0"}
    ) as response:
        if response.status != 200:
            raise Exception(f"HTTP {response.status}")
        data = await response.json()

    items = []
    for paper in data[:limit]:
        paper_info = paper.get("paper", paper)
        title = paper_info.get("title", "Untitled")
        paper_id = paper_info.get("id", "")
        summary = paper_info.get("summary", "")[:1000]
        upvotes = paper.get("numUpvotes", paper_info.get("upvotes", 0))

        item_id = f"hf-paper-{hashlib.md5((paper_id or title).encode()).hexdigest()[:12]}"

        items.append({
            "id": item_id,
            "source": "HuggingFace Papers",
            "source_type": "paper",
            "title": title[:200],
            "url": f"https://huggingface.co/papers/{paper_id}" if paper_id else "",
            "original_content": summary[:500],
            "raw_text": summary,
            "relevance_score": 0,
            "category": platform.get("category", ["ai", "papers"]),
            "created_at": datetime.now(),
        })

    return items


async def fetch_civitai_models(session: aiohttp.ClientSession, platform: Dict) -> List[Dict]:
    """抓取 CivitAI 热门模型"""
    url = platform.get("url", "https://civitai.com/api/v1/models")
    params = platform.get("params", {})
    limit = params.get("limit", 10)

    async with session.get(
        url,
        params={
            "sort": params.get("sort", "Newest"),
            "period": params.get("period", "Day"),
            "limit": limit,
            "nsfw": "false",
        },
        headers={"User-Agent": "TokenBurner/1.0"}
    ) as response:
        if response.status != 200:
            raise Exception(f"HTTP {response.status}")
        data = await response.json()

    items_list = data.get("items", [])
    items = []

    for model in items_list[:limit]:
        name = model.get("name", "Untitled")
        model_type = model.get("type", "")
        model_id = model.get("id", 0)
        stats = model.get("stats", {})
        downloads = stats.get("downloadCount", 0)
        rating = stats.get("rating", 0)
        description = model.get("description", "") or ""

        desc = f"Type: {model_type} | Downloads: {downloads:,} | Rating: {rating:.1f}"

        item_id = f"civitai-{model_id}"

        items.append({
            "id": item_id,
            "source": "CivitAI",
            "source_type": "model",
            "title": f"🎨 {name} ({model_type})",
            "url": f"https://civitai.com/models/{model_id}",
            "original_content": desc,
            "raw_text": (desc + "\n" + description[:500]) if description else desc,
            "relevance_score": 0,
            "category": platform.get("category", ["ai", "models", "image-generation"]),
            "created_at": datetime.now(),
        })

    return items
