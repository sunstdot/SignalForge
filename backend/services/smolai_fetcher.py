"""Smol AI News 抓取服务"""
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict
import re


async def fetch_smolai_news(config: Dict) -> List[Dict]:
    """抓取 Smol AI News"""
    items = []
    max_issues = config.get("maxIssues", 3)
    
    # Smol AI News 是一个 newsletter，我们模拟抓取最近几期
    base_url = "https://smol.ai/news"
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            # 尝试获取 Smol AI News 的内容
            # 由于这是 newsletter，我们可能需要从其他渠道获取
            # 这里简化处理，返回示例数据或从 RSS 获取
            
            # 如果有直接的 RSS feed
            rss_url = "https://smol.ai/news/rss.xml"
            try:
                async with session.get(rss_url) as response:
                    if response.status == 200:
                        # 解析 RSS
                        from .rss_fetcher import parse_rss_feed
                        xml_text = await response.text()
                        subscription = {
                            "name": "Smol AI News",
                            "url": rss_url,
                            "category": ["AI", "newsletter"]
                        }
                        items = parse_rss_feed(xml_text, subscription)
            except:
                pass
            
            # 如果没有获取到，使用备用方法
            if not items:
                items = await fetch_smolai_alternative(session, max_issues)
                
        except Exception as e:
            print(f"  ✗ Smol AI News fetch failed: {e}")
    
    print(f"  ✓ Smol AI News: {len(items)} issues")
    return items


async def fetch_smolai_alternative(session: aiohttp.ClientSession, max_issues: int) -> List[Dict]:
    """备用方法获取 Smol AI News"""
    items = []
    
    # 尝试从他们的网站抓取
    try:
        async with session.get("https://smol.ai/news") as response:
            if response.status == 200:
                html = await response.text()
                # 提取新闻内容
                items = parse_smolai_html(html, max_issues)
    except Exception as e:
        print(f"Alternative fetch error: {e}")
    
    return items


def parse_smolai_html(html: str, max_issues: int) -> List[Dict]:
    """解析 Smol AI News HTML"""
    items = []
    
    # 这里需要根据实际 HTML 结构来解析
    # 简化处理：提取标题和链接
    
    # 使用正则提取文章
    pattern = r'<article[^>]*>.*?<h[1-6][^>]*>(.*?)</h[1-6]>.*?<a[^>]*href="([^"]*)"[^>]*>.*?</article>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    
    for i, (title, link) in enumerate(matches[:max_issues]):
        # 清理标题
        title = re.sub(r'<[^>]+>', '', title).strip()
        
        # 确保链接完整
        if not link.startswith("http"):
            link = f"https://smol.ai{link}"
        
        item_id = f"smolai-{datetime.now().strftime('%Y%m%d')}-{i}"
        
        items.append({
            "id": item_id,
            "source": "Smol AI News",
            "source_type": "newsletter",
            "title": title[:200],
            "url": link,
            "original_content": "",
            "raw_text": "",
            "relevance_score": 0,
            "category": ["AI", "newsletter", "工具"],
            "created_at": datetime.now() - timedelta(days=i)
        })
    
    return items
