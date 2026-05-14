"""GitHub Trending 抓取服务 - 直接抓取 GitHub Trending 页面"""
import re
import aiohttp
from datetime import datetime
from typing import List, Dict
import hashlib


TRENDING_URL = "https://github.com/trending"


async def fetch_github_trending(config: Dict) -> List[Dict]:
    """抓取 GitHub Trending 页面（今日趋势，按 star 增速排）"""
    time_range = config.get("timeRange", "daily")  # daily / weekly / monthly
    since_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
    since = since_map.get(time_range, "daily")

    timeout = aiohttp.ClientTimeout(total=20)
    items = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        try:
            async with session.get(
                TRENDING_URL,
                params={"since": since},
            ) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                html = await response.text()

            items = parse_trending_html(html)
        except Exception as e:
            print(f"  ✗ GitHub Trending scrape failed: {e}")

    print(f"  ✓ GitHub: {len(items)} repos")
    return items


def parse_trending_html(html: str) -> List[Dict]:
    """从 GitHub Trending 页面 HTML 中解析仓库列表"""
    items = []

    # 每个仓库在 <article class="Box-row"> 里
    articles = re.findall(r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>', html, re.DOTALL)

    for article in articles:
        try:
            item = parse_article(article)
            if item:
                items.append(item)
        except Exception:
            continue

    return items


def parse_article(article: str) -> Dict:
    """解析单个仓库 article 块"""
    # full_name: <h2 ...><a href="/owner/repo"
    name_match = re.search(r'<h2[^>]*>.*?<a[^>]+href="/([^"]+)"', article, re.DOTALL)
    if not name_match:
        return None
    full_name = name_match.group(1).strip().strip('/')
    if full_name.count('/') != 1:
        return None

    # description
    desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>\s*(.*?)\s*</p>', article, re.DOTALL)
    description = ""
    if desc_match:
        description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()

    # stars total
    stars = 0
    stars_match = re.search(r'href="/' + re.escape(full_name) + r'/stargazers"[^>]*>\s*<[^>]+>\s*([\d,]+)', article)
    if stars_match:
        stars = int(stars_match.group(1).replace(',', ''))

    # stars today / this period
    stars_today = ""
    today_match = re.search(r'([\d,]+)\s+stars?\s+today', article, re.IGNORECASE)
    if today_match:
        stars_today = today_match.group(1).replace(',', '')

    # language
    language = ""
    lang_match = re.search(
        r'itemprop="programmingLanguage"[^>]*>\s*(.*?)\s*<',
        article, re.DOTALL
    )
    if lang_match:
        language = lang_match.group(1).strip()

    # build content
    title = full_name
    if description:
        title += f" — {description[:80]}"

    content_parts = []
    if description:
        content_parts.append(description)
    if stars:
        content_parts.append(f"⭐ {stars:,} stars")
    if stars_today:
        content_parts.append(f"🔥 {stars_today} stars today")
    if language:
        content_parts.append(f"Language: {language}")

    content = " | ".join(content_parts)

    category = ["开源项目"]
    if language:
        category.append(language)

    item_id = f"github-{hashlib.md5(full_name.encode()).hexdigest()[:12]}"

    return {
        "id": item_id,
        "source": "GitHub Trending",
        "source_type": "repo",
        "title": title[:200],
        "url": f"https://github.com/{full_name}",
        "original_content": content[:500],
        "raw_text": content,
        "relevance_score": 0,
        "category": category[:4],
        "published_date": datetime.now().strftime("%Y-%m-%d"),
        "created_at": datetime.now(),
    }
