"""GitHub Trending 抓取服务 - 使用 GitHub Search API"""
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict
import hashlib


async def fetch_github_trending(config: Dict) -> List[Dict]:
    """抓取 GitHub 热门仓库（通过 Search API）"""
    time_range = config.get("timeRange", "daily")
    languages = config.get("languages", ["any"])

    # 计算时间范围
    days_map = {"daily": 1, "weekly": 7, "monthly": 30}
    days = days_map.get(time_range, 1)
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    timeout = aiohttp.ClientTimeout(total=20)
    items = []

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for lang in languages:
            try:
                lang_items = await fetch_repos_by_language(session, lang, since_date)
                items.extend(lang_items)
            except Exception as e:
                print(f"  ✗ GitHub {lang} fetch failed: {e}")

    print(f"  ✓ GitHub: {len(items)} repos")
    return items


async def fetch_repos_by_language(
    session: aiohttp.ClientSession,
    language: str,
    since_date: str
) -> List[Dict]:
    """通过 GitHub Search API 获取热门仓库"""
    query = f"created:>{since_date} stars:>10"
    if language and language != "any":
        query += f" language:{language}"

    async with session.get(
        "https://api.github.com/search/repositories",
        params={
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 15,
        },
        headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TokenBurner/1.0",
        }
    ) as response:
        if response.status == 403:
            raise Exception("GitHub API rate limit exceeded")
        if response.status != 200:
            raise Exception(f"HTTP {response.status}")
        data = await response.json()

    repos = data.get("items", [])
    return [parse_repo(repo) for repo in repos]


def parse_repo(repo: Dict) -> Dict:
    """解析仓库数据"""
    full_name = repo.get("full_name", "")
    description = repo.get("description") or ""
    stars = repo.get("stargazers_count", 0)
    language = repo.get("language") or ""
    topics = repo.get("topics", [])

    title = full_name
    if description:
        title += f" — {description[:80]}"

    content_parts = [description] if description else []
    content_parts.append(f"⭐ {stars:,} stars")
    if language:
        content_parts.append(f"Language: {language}")
    if topics:
        content_parts.append(f"Topics: {', '.join(topics[:5])}")

    content = " | ".join(content_parts)

    category = ["开源项目"]
    if language:
        category.append(language)
    if topics:
        category.extend(topics[:2])

    item_id = f"github-{hashlib.md5(full_name.encode()).hexdigest()[:12]}"

    return {
        "id": item_id,
        "source": "GitHub Trending",
        "source_type": "repo",
        "title": title[:200],
        "url": repo.get("html_url", f"https://github.com/{full_name}"),
        "original_content": content[:500],
        "raw_text": content,
        "relevance_score": 0,
        "category": category[:4],
        "created_at": datetime.now(),
    }
