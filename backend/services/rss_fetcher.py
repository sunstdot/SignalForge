"""RSS 订阅源抓取服务"""
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict
import re


async def fetch_rss_feeds(config: Dict, target_date: str = None) -> List[Dict]:
    """抓取所有配置的 RSS 订阅源，target_date 格式 YYYY-MM-DD"""
    items = []
    subscriptions = config.get("subscriptions", [])

    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for sub in subscriptions:
            try:
                sub_items = await fetch_single_rss(session, sub, target_date=target_date)
                items.extend(sub_items)
                if sub_items:
                    print(f"  ✓ RSS {sub['name']}: {len(sub_items)} items")
                else:
                    print(f"  - RSS {sub['name']}: 0 items (date filter or empty feed)")
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"  ✗ RSS {sub['name']}: {error_msg}")

    # 按 URL 去重（保留每个 URL 第一次出现的条目）
    seen_urls: set = set()
    deduped = []
    for item in items:
        url = item.get("url", "")
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)

    if len(deduped) < len(items):
        print(f"  ℹ RSS dedup: {len(items)} → {len(deduped)} items")

    return deduped


async def fetch_single_rss(session: aiohttp.ClientSession, subscription: Dict, target_date: str = None) -> List[Dict]:
    """抓取单个 RSS 源"""
    url = subscription["url"]

    # 将 rsshub:// 协议转换为实际的 rsshub.app URL
    if url.startswith("rsshub://"):
        url = "https://rsshub.app/" + url[len("rsshub://"):]

    async with session.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TokenBurner/1.0; +https://github.com/tokenburner)"}
    ) as response:
        if response.status != 200:
            raise Exception(f"HTTP {response.status}")

        raw = await response.read()
        # 优先使用响应头中的编码，否则尝试 UTF-8，再回退 latin-1
        charset = response.charset or 'utf-8'
        try:
            xml_text = raw.decode(charset)
        except (UnicodeDecodeError, LookupError):
            xml_text = raw.decode('latin-1')
        return parse_rss_feed(xml_text, subscription, target_date=target_date)


def sanitize_xml(xml: str) -> str:
    """清理 XML 中的问题字符，使其可被解析"""
    # 去除 BOM（字节顺序标记）
    xml = xml.lstrip('\ufeff\ufffe')

    # 移除控制字符（保留 tab, newline, carriage return）
    xml = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', xml)

    # 修复未转义的 & （不破坏已有的 &amp; &lt; 等）
    xml = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', xml)

    return xml


def expand_digest_topics(html: str, issue_item: Dict, subscription: Dict) -> List[Dict]:
    """将聚合日报的 HTML 拆解为多个独立 AI 情报条目。
    处理两类结构：
      1. <p><strong>主题标题</strong></p><ul>...</ul>   （Twitter Recap 风格）
      2. <h2>/<h3> 标题 + <ul>...</ul>                  （Reddit Recap 风格）
    """
    import hashlib, html as _html_mod
    result = []
    issue_url = issue_item["url"]
    issue_date = issue_item["created_at"]
    source_name = subscription["name"]
    category = subscription.get("category", ["ai", "news"])

    # 解码 HTML 实体，去掉标签得到纯文本
    def _text(h: str) -> str:
        t = re.sub(r'<[^>]+>', ' ', _html_mod.unescape(h))
        return re.sub(r'\s+', ' ', t).strip()

    # 提取第一个 <a href="..."> 的 URL（用作更精确的来源链接）
    def _first_link(h: str) -> str:
        m = re.search(r'<a[^>]+href="(https?://[^"]+)"', h)
        return m.group(1) if m else issue_url

    # ── 模式 1：<p><strong>...</strong>[非标签字符]</p> 后紧跟 <ul> ──
    # [^<]+ 限制 strong 内容不含标签，彻底防止跨段落回溯
    pattern1 = re.compile(
        r'<p>\s*<strong>([^<]+)</strong>[^<]*</p>\s*(<ul>.*?</ul>)',
        re.DOTALL | re.IGNORECASE
    )
    # ── 模式 2：<h2>/<h3> 后紧跟 <ul> ──
    pattern2 = re.compile(
        r'<h[23][^>]*>(.*?)</h[23]>\s*(<ul>.*?</ul>)',
        re.DOTALL | re.IGNORECASE
    )

    seen_titles: set = set()

    def _add(title_html: str, body_html: str):
        title = _text(title_html)[:200]
        if not title or title in seen_titles:
            return
        seen_titles.add(title)
        body_text = _text(body_html)[:3000]
        first_url = _first_link(body_html)
        id_base = f"{issue_url}#{title}"
        item_id = f"smolai-{hashlib.md5(id_base.encode()).hexdigest()[:12]}"
        result.append({
            "id": item_id,
            "source": source_name,
            "source_type": "smolai",
            "title": title,
            "url": first_url,
            "original_content": body_text[:500],
            "raw_text": body_text,
            "relevance_score": 0,
            "category": category,
            "published_date": issue_date.strftime("%Y-%m-%d") if isinstance(issue_date, datetime) else str(issue_date)[:10],
            "created_at": issue_date,
        })

    for m in pattern1.finditer(html):
        _add(m.group(1), m.group(2))

    for m in pattern2.finditer(html):
        _add(m.group(1), m.group(2))

    return result


def parse_rss_feed(xml: str, subscription: Dict, target_date: str = None) -> List[Dict]:
    """解析 RSS/Atom feed"""
    items = []
    name = subscription.get("name", "unknown")

    # 清理 XML
    xml = sanitize_xml(xml)

    # 如果响应是 HTML（如重定向到登录页），直接跳过
    if xml.lstrip().startswith(('<!DOCTYPE', '<html', '<!doctype')):
        print(f"  ✗ RSS {name}: received HTML instead of XML (redirect or auth wall)")
        return items

    if not xml.strip():
        print(f"  ✗ RSS {name}: empty response")
        return items

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        print(f"  ✗ RSS {name}: XML parse error: {e}")
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

    is_blog = subscription.get("source_type") in ("blog", "wechat", "investor")
    source_type = subscription.get("source_type")
    expand_topics = subscription.get("expand_topics", False) and source_type != "smolai"

    # 先统一去掉 tzinfo，方便比较
    for item in items:
        created = item["created_at"]
        if hasattr(created, 'tzinfo') and created.tzinfo is not None:
            created = created.replace(tzinfo=None)
        item["created_at"] = created

    # 保留 7 天过滤前的完整条目，供「兜底 fallback」使用：
    # 即使博客很久没更新，也至少补 1 条最近的文章，确保 feed 不为空。
    all_items = list(items)

    # 发布时间超过 7 天的 feed 条目不再进入后续窗口和常规 fallback。
    # 这里必须在 fallback 前过滤，否则低频博客会把很旧的文章补进当天内容。
    seven_days_ago = datetime.now() - timedelta(days=7)
    items = [
        item for item in items
        if not isinstance(item.get("created_at"), datetime)
        or item["created_at"] >= seven_days_ago
    ]

    # 过滤日期：target_date 当天前后 12/36 小时窗口
    if target_date:
        try:
            base = datetime.strptime(target_date, "%Y-%m-%d")
            window_start = base - timedelta(hours=12)
            window_end   = base + timedelta(hours=36)
        except ValueError:
            window_start = window_end = None
    else:
        window_start = window_end = None

    three_days_ago = datetime.now() - timedelta(days=3)
    filtered_items = []

    for item in items:
        try:
            if window_start and window_end:
                if window_start <= item["created_at"] <= window_end:
                    filtered_items.append(item)
            else:
                if item["created_at"] >= three_days_ago:
                    filtered_items.append(item)
        except (TypeError, AttributeError):
            filtered_items.append(item)

    def _apply_fallback(fallback_items: List[Dict], n: int) -> List[Dict]:
        """取最新 n 条，存储日期覆盖为 target_date，保留原始发布日期"""
        sorted_items = sorted(fallback_items, key=lambda x: x["created_at"], reverse=True)
        result = sorted_items[:n]
        if target_date:
            stamp = datetime.strptime(target_date, "%Y-%m-%d")
            for item in result:
                item["created_at"] = stamp
        return result

    # 无任何命中时的通用 fallback：取 7 天内最新 N 条
    if not filtered_items and items:
        fallback_n = 3 if is_blog else (1 if expand_topics else 1)
        filtered_items = _apply_fallback(items, fallback_n)

    # 兜底 fallback：7 天内也没有任何条目（低频博客长期未更新），
    # 则忽略 7 天限制，取整个 feed 里最近更新的 1 条，保证至少返回 1 项。
    if not filtered_items and all_items:
        filtered_items = _apply_fallback(all_items, 1)

    # blog/investor/wechat：无论是否经过 fallback，都把 created_at 统一覆盖为
    # target_date，确保当天运行的内容存入当天文件而非原始发布日期
    if is_blog and target_date and filtered_items:
        stamp = datetime.strptime(target_date, "%Y-%m-%d")
        for item in filtered_items:
            item["created_at"] = stamp

    # expand_topics：把每个 issue 拆解为多个情报条目。
    # Smol AI News 保留 RSS 原始条目，不再拆 topic。
    if expand_topics and filtered_items:
        expanded = []
        for issue in filtered_items:
            html_content = issue.get("_raw_html", "")
            if html_content:
                topics = expand_digest_topics(html_content, issue, subscription)
                expanded.extend(topics if topics else [issue])
            else:
                expanded.append(issue)
        return expanded

    # 普通 RSS 每个源最多 5 条；blog/investor 最多 3 条
    limit = 3 if is_blog else 5
    return filtered_items[:limit]


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

    item: Dict = {
        "id": item_id,
        "source": subscription["name"],
        "source_type": subscription.get("source_type", "rss"),
        "title": title[:200],
        "url": link[:500],
        "original_content": description_clean,
        "raw_text": content_clean,
        "relevance_score": 0,
        "category": subscription.get("category", ["技术资讯"]),
        "published_date": created_at.strftime("%Y-%m-%d"),
        "created_at": created_at,
    }
    # expand_topics 订阅保留原始 HTML 供后续拆解
    if subscription.get("expand_topics"):
        item["_raw_html"] = content
    return item


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
        "source_type": subscription.get("source_type", "rss"),
        "title": title[:200],
        "url": link[:500],
        "original_content": content_clean[:500],
        "raw_text": content_clean,
        "relevance_score": 0,
        "category": subscription.get("category", ["技术资讯"]),
        "published_date": created_at.strftime("%Y-%m-%d"),
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
