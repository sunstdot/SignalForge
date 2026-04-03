"""RSS 订阅源抓取服务"""
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict
import re


async def fetch_rss_feeds(config: Dict) -> List[Dict]:
    """抓取所有配置的 RSS 订阅源"""
    items = []
    subscriptions = config.get("subscriptions", [])
    
    timeout = aiohttp.ClientTimeout(total=15)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for sub in subscriptions:
            try:
                sub_items = await fetch_single_rss(session, sub)
                items.extend(sub_items)
                if sub_items:
                    print(f"  ✓ RSS {sub['name']}: {len(sub_items)} items")
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"  ✗ RSS {sub['name']}: {error_msg}")
    
    return items


async def fetch_single_rss(session: aiohttp.ClientSession, subscription: Dict) -> List[Dict]:
    """抓取单个 RSS 源"""
    url = subscription["url"]
    
    async with session.get(
        url,
        headers={"User-Agent": "TokenBurner/1.0 RSS Reader"}
    ) as response:
        if response.status != 200:
            raise Exception(f"HTTP {response.status}")
        
        xml_text = await response.text()
        return parse_rss_feed(xml_text, subscription)


def sanitize_xml(xml: str) -> str:
    """清理 XML 中的问题字符，使其可被解析"""
    # 移除控制字符（保留 tab, newline, carriage return）
    xml = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', xml)

    # 修复未转义的 & （不破坏已有的 &amp; &lt; 等）
    xml = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', xml)

    return xml


def parse_rss_feed(xml: str, subscription: Dict) -> List[Dict]:
    """解析 RSS/Atom feed"""
    items = []
    
    # 清理 XML
    xml = sanitize_xml(xml)
    
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        print(f"XML parse error: {e}")
        return items
    
    # 确定命名空间
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    
    # RSS 2.0 格式
    channel = root.find(".//channel")
    if channel is not None:
        for item_elem in channel.findall("item"):
            item = parse_rss_item(item_elem, subscription, ns)
            if item:
                items.append(item)
    
    # Atom 格式
    entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    if entries:
        for entry in entries:
            item = parse_atom_entry(entry, subscription)
            if item:
                items.append(item)
    
    # 过滤最近 3 天的内容
    three_days_ago = datetime.now() - timedelta(days=3)
    filtered_items = []

    for item in items:
        created = item["created_at"]
        # 统一为 naive datetime 进行比较
        if hasattr(created, 'tzinfo') and created.tzinfo is not None:
            created = created.replace(tzinfo=None)
        try:
            if created >= three_days_ago:
                # 存储时统一为 naive
                item["created_at"] = created
                filtered_items.append(item)
        except TypeError:
            filtered_items.append(item)
    
    # 限制每个源最多 5 条
    return filtered_items[:5]


def parse_rss_item(item_elem: ET.Element, subscription: Dict, ns: Dict) -> Dict:
    """解析单个 RSS item"""
    title = item_elem.findtext("title", "Untitled").strip()
    link = item_elem.findtext("link", "").strip()
    description = item_elem.findtext("description", "").strip()
    pub_date = item_elem.findtext("pubDate", "")
    
    # 获取内容
    content_encoded = item_elem.find("content:encoded", ns)
    if content_encoded is not None and content_encoded.text:
        content = content_encoded.text
    else:
        content = description
    
    # 解析日期
    created_at = parse_date(pub_date) or datetime.now()
    
    # 生成 ID
    id_base = link or title
    import hashlib
    item_id = f"rss-{subscription['name'].replace(' ', '-').lower()[:20]}-{hashlib.md5(id_base.encode()).hexdigest()[:12]}"
    
    # 清理 HTML
    content_clean = strip_html(content)[:3000]
    description_clean = strip_html(description)[:500]
    
    return {
        "id": item_id,
        "source": subscription["name"],
        "source_type": "rss",
        "title": title[:200],
        "url": link[:500],
        "original_content": description_clean,
        "raw_text": content_clean,
        "relevance_score": 0,
        "category": subscription.get("category", ["技术资讯"]),
        "created_at": created_at
    }


def parse_atom_entry(entry_elem: ET.Element, subscription: Dict) -> Dict:
    """解析 Atom entry"""
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    
    title = entry_elem.findtext("atom:title", "Untitled", ns).strip()
    
    # 获取链接
    link_elem = entry_elem.find("atom:link", ns)
    link = ""
    if link_elem is not None:
        link = link_elem.get("href", "")
    
    # 获取内容
    content_elem = entry_elem.find("atom:content", ns)
    summary_elem = entry_elem.find("atom:summary", ns)
    
    if content_elem is not None and content_elem.text:
        content = content_elem.text
    elif summary_elem is not None and summary_elem.text:
        content = summary_elem.text
    else:
        content = ""
    
    # 发布日期
    published = entry_elem.findtext("atom:published", "", ns) or \
                entry_elem.findtext("atom:updated", "", ns)
    created_at = parse_date(published) or datetime.now()
    
    # 生成 ID
    id_base = link or title
    import hashlib
    entry_id = f"atom-{subscription['name'].replace(' ', '-').lower()[:20]}-{hashlib.md5(id_base.encode()).hexdigest()[:12]}"
    
    content_clean = strip_html(content)[:3000]
    
    return {
        "id": entry_id,
        "source": subscription["name"],
        "source_type": "rss",
        "title": title[:200],
        "url": link[:500],
        "original_content": content_clean[:500],
        "raw_text": content_clean,
        "relevance_score": 0,
        "category": subscription.get("category", ["技术资讯"]),
        "created_at": created_at
    }


def parse_date(date_str: str) -> datetime:
    """解析各种日期格式"""
    if not date_str:
        return datetime.now()
    
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    
    # 清理日期字符串
    date_str = date_str.strip()
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # 尝试 ISO 格式
    try:
        from dateutil import parser
        return parser.isoparse(date_str)
    except:
        pass
    
    return datetime.now()


def strip_html(html: str) -> str:
    """移除 HTML 标签"""
    if not html:
        return ""
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', html)
    # 合并空白
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
