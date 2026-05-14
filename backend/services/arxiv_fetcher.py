"""arXiv 论文抓取服务"""
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict


async def fetch_arxiv_papers(config: Dict) -> List[Dict]:
    """抓取 arXiv 论文"""
    items = []
    categories = config.get("categories", ["cs.AI", "cs.CL", "cs.LG"])
    max_results = config.get("maxResults", 20)

    # 构建分类查询，直接取最新论文（按提交日期降序）
    cat_query = " OR ".join([f"cat:{cat}" for cat in categories])

    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query={cat_query}"
        f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"arXiv API error: {response.status}")
                
                xml_text = await response.text()
                items = parse_arxiv_feed(xml_text)
                print(f"  ✓ arXiv: {len(items)} papers")
        except Exception as e:
            print(f"  ✗ arXiv fetch failed: {e}")
    
    return items


def parse_arxiv_feed(xml_text: str) -> List[Dict]:
    """解析 arXiv Atom feed"""
    items = []
    
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"Parse error: {e}")
        return items
    
    # arXiv 使用 Atom 命名空间
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    
    for entry in root.findall("atom:entry", ns):
        try:
            # 获取 ID
            id_elem = entry.find("atom:id", ns)
            arxiv_id = id_elem.text.split("/")[-1] if id_elem is not None else ""
            
            # 获取标题
            title_elem = entry.find("atom:title", ns)
            title = title_elem.text.strip() if title_elem is not None else "Untitled"
            
            # 获取摘要
            summary_elem = entry.find("atom:summary", ns)
            summary = summary_elem.text.strip() if summary_elem is not None else ""
            
            # 获取链接
            link = f"https://arxiv.org/abs/{arxiv_id}"
            pdf_link = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            
            # 获取作者
            authors = []
            for author_elem in entry.findall("atom:author", ns):
                name_elem = author_elem.find("atom:name", ns)
                if name_elem is not None:
                    authors.append(name_elem.text)
            
            # 获取分类
            categories = []
            for cat_elem in entry.findall("atom:category", ns):
                term = cat_elem.get("term", "")
                if term:
                    categories.append(term)
            
            # 获取发布日期
            published_elem = entry.find("atom:published", ns)
            if published_elem is not None:
                try:
                    created_at = datetime.fromisoformat(published_elem.text.replace("Z", "+00:00"))
                except:
                    created_at = datetime.now()
            else:
                created_at = datetime.now()
            
            # 生成唯一 ID
            item_id = f"arxiv-{arxiv_id}"
            
            items.append({
                "id": item_id,
                "source": "arXiv",
                "source_type": "arxiv",
                "title": title[:200],
                "url": link,
                "original_content": summary[:1000],
                "raw_text": summary[:5000],
                "relevance_score": 0,
                "category": categories[:3] if categories else ["AI", "论文"],
                "created_at": created_at,
                "metadata": {
                    "authors": authors[:5],
                    "pdf_url": pdf_link,
                    "arxiv_id": arxiv_id
                }
            })
        except Exception as e:
            print(f"Parse entry error: {e}")
            continue
    
    return items
