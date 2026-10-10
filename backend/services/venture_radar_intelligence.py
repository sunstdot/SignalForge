"""Normalize venture-product-radar candidates into evidence-aware intelligence."""
import re
from urllib.parse import urlparse


STATUS_KEYWORDS = [
    ("cancelled", ("cancelled", "canceled")),
    ("filed", ("filed", "files for", "ipo filing")),
    ("closed", ("closed", "completed")),
    ("in_talks", ("in talks", "considering", "could raise", "seeking funding")),
    ("rumor", ("reportedly", "sources say", "is said to", "said to")),
    ("announced", ("announced", "raises", "raised", "secures", "secured")),
]

EMPTY_VALUES = {"", "not disclosed", "unknown", "n/a", "none", "null"}
OFFICIAL_SOURCE_MARKERS = ("official", "company", "press", "newsroom", "blog", "investor", "regulatory", "sec")
PROVENANCE_FIELDS = (
    "amount_raised",
    "valuation",
    "round",
    "round_type",
    "event_status",
    "published_date",
    "announced_date",
    "filed_date",
    "closed_date",
    "lead_investors",
    "participating_investors",
)
TEMPLATE_ANALYSIS = (
    "需要补充公司背景、产品、客户和市场意义后再判断关注优先级",
    "需要继续核验官方公告、领投方、业务进展",
)


def _clean(value):
    if value is None:
        return ""
    if isinstance(value, dict) and "value" in value:
        return _clean(value.get("value"))
    if isinstance(value, list):
        return "、".join(_clean(item) for item in value if _clean(item))
    text = re.sub(r"<[^>]+>", " ", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return "" if text.lower() in EMPTY_VALUES else text


def _list(value):
    if not value:
        return []
    if isinstance(value, dict) and "value" in value:
        return _list(value.get("value"))
    if isinstance(value, list):
        return [_clean(item) for item in value if _clean(item)]
    text = _clean(value)
    return [text] if text else []


def _urls(raw):
    urls = _list(raw.get("source_urls") or raw.get("source_url") or raw.get("url"))
    for key in PROVENANCE_FIELDS:
        field = raw.get(key)
        if isinstance(field, dict):
            urls.extend(_list(field.get("source_urls")))
    return list(dict.fromkeys(urls))


def _domain(url):
    return urlparse(url).netloc.lower().replace("www.", "")


def _source_lookup(report):
    return {item.get("url"): item for item in report.get("source_links") or [] if isinstance(item, dict) and item.get("url")}


def _source_type(source):
    text = " ".join([
        _clean(source.get("source_type")),
        _clean(source.get("source_tier")),
    ]).lower()
    return text


def _is_official_source(source):
    text = _source_type(source)
    return any(marker in text for marker in OFFICIAL_SOURCE_MARKERS) and "media" not in text


def _is_independent_source(source):
    text = _source_type(source)
    return bool(text) and any(marker in text for marker in ("media", "news", "journal", "publication", "credible", "tier_"))


def _source_counts(urls, report):
    lookup = _source_lookup(report)
    unique_urls = list(dict.fromkeys(urls))
    official = 0
    independent = set()
    for url in unique_urls:
        source = lookup.get(url) or {}
        if _is_official_source(source):
            official += 1
        elif _is_independent_source(source):
            independent.add(_clean(source.get("source_name")) or _domain(url) or url)
    return len(unique_urls), official, len(independent)


def _text(raw, report):
    urls = _urls(raw)
    lookup = _source_lookup(report)
    source_text = " ".join(
        " ".join([_clean(item.get("title")), _clean(item.get("snippet"))])
        for url, item in lookup.items()
        if url in urls
    )
    return " ".join([
        _clean(raw.get("title")),
        _clean(raw.get("market_signal")),
        _clean(raw.get("summary")),
        _clean(raw.get("description")),
        source_text,
    ]).strip()


def _event_status(raw, text):
    explicit = _clean(raw.get("event_status")).lower()
    lowered = text.lower()
    for status in ("in_talks", "rumor"):
        keywords = dict(STATUS_KEYWORDS)[status]
        if any(keyword in lowered for keyword in keywords):
            return status
    if explicit in {"rumor", "in_talks", "filed", "announced", "closed", "cancelled", "unclear"}:
        return explicit
    for status, keywords in STATUS_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return status
    return "unclear"


def _looks_like_valuation(text, value):
    lowered = text.lower()
    if "valuation" not in lowered:
        return False
    if not value:
        return True
    value_text = value.replace(" ", "").lower()
    return value_text in lowered.replace(" ", "") or "$" in value_text


def _valuation_from_text(text):
    match = re.search(r"(\$\d+(?:\.\d+)?\s?[BM](?:\s?[-–]\s?\$?\d+(?:\.\d+)?\s?[BM])?)\s+valuation", text, flags=re.I)
    if not match:
        return ""
    return re.sub(r"\s+", "", match.group(1)).replace("–", "-")


def _field(value, urls, source_types, confidence):
    if isinstance(value, dict) and "value" in value:
        field_value = value.get("value")
        has_value = field_value not in (None, "", [])
        field_confidence = _clean(value.get("confidence")).lower()
        return {
            "value": field_value if has_value else None,
            "source_urls": _list(value.get("source_urls")) if has_value else [],
            "source_types": _list(value.get("source_types")) if has_value else [],
            "confidence": field_confidence if field_confidence in {"high", "medium", "low"} and has_value else "low",
        }
    has_value = value not in (None, "", [])
    return {
        "value": value if has_value else None,
        "source_urls": urls if has_value else [],
        "source_types": source_types if has_value else [],
        "confidence": confidence if has_value else "low",
    }


def _source_types(urls, report):
    lookup = _source_lookup(report)
    return [_clean(lookup.get(url, {}).get("source_type")) or "unknown" for url in urls]


def _clean_company_name(raw_name):
    name = _clean(raw_name)
    name = re.sub(r"\s+(reportedly|is said to|sources say).*$", "", name, flags=re.I)
    name = re.sub(r"\s+in talks to.*$", "", name, flags=re.I)
    name = re.sub(r"\s+considering.*$", "", name, flags=re.I)
    name = re.sub(r"^nuclear startup\s+", "", name, flags=re.I)
    return name.strip(" -.,") or _clean(raw_name)


def _chinese_title(company, status, amount, valuation, round_value):
    status_text = {
        "rumor": "据报出现融资传闻",
        "in_talks": "据报正在洽谈融资",
        "filed": "已提交融资相关文件",
        "announced": "宣布融资",
        "closed": "完成融资",
        "cancelled": "取消融资计划",
        "unclear": "出现融资动态",
    }.get(status, "出现融资动态")
    details = []
    if amount:
        details.append(f"金额 {amount}")
    if valuation:
        label = "目标估值" if status in {"rumor", "in_talks"} else "估值"
        details.append(f"{label} {valuation}")
    if round_value:
        details.append(f"轮次 {round_value}")
    suffix = f"，{'，'.join(details)}" if details else ""
    return f"{company} {status_text}{suffix}".strip()


def _confidence(raw_confidence, official_count, independent_count):
    value = _clean(raw_confidence).lower()
    if official_count > 0 and value in {"", "low"}:
        return "medium"
    if independent_count >= 2 and value == "low":
        return "medium"
    return value if value in {"high", "medium", "low"} else "low"


def _provenance_value(raw, report, key_candidates, fallback=""):
    urls = _urls(raw)
    value = ""
    for key in key_candidates:
        value = _clean(raw.get(key))
        if value:
            break
    return value or fallback, urls, _source_types(urls, report)


def _published_date(raw, report):
    value = _clean(raw.get("published_date"))
    if value:
        return value[:10]
    lookup = _source_lookup(report)
    for url in _urls(raw):
        published = _clean((lookup.get(url) or {}).get("published_at"))
        if published:
            return published[:10]
    return ""


def _analysis(raw):
    values = {
        "what_happened": _clean(raw.get("what_happened") or raw.get("market_signal") or raw.get("summary")),
        "what_changed": _clean(raw.get("what_changed")),
        "why_it_matters": _clean(raw.get("why_it_matters")),
        "market_implication": _clean(raw.get("market_implication")),
        "opportunity_angle": _clean(raw.get("opportunity_angle")),
        "risk_and_uncertainty": _clean(raw.get("risk_and_uncertainty")),
        "next_watch_items": _list(raw.get("next_watch_items")),
    }
    for key in ("why_it_matters", "opportunity_angle"):
        if any(template in values[key] for template in TEMPLATE_ANALYSIS):
            values[key] = ""
    if not any(values[key] for key in ("why_it_matters", "market_implication", "opportunity_angle")):
        values["risk_and_uncertainty"] = values["risk_and_uncertainty"] or "当前证据不足，尚不能判断其市场意义。"
    return values


def _evidence_gaps(raw, amount_value, lead_investors, status, official_count):
    gaps = _list(raw.get("evidence_gaps"))
    if not amount_value:
        gaps.append("funding amount")
    if not lead_investors:
        gaps.append("lead investors")
    if official_count == 0:
        gaps.append("official announcement")
    if status in {"rumor", "in_talks", "unclear"}:
        gaps.append("event status confirmation")
    return list(dict.fromkeys(gaps))


def _enrichment_tasks(entity):
    definitions = (
        ("company_newsroom", "official funding announcement", "company_newsroom", "high"),
        ("amount_classification", "funding amount valuation", "official_or_credible_media", "high"),
        ("lead_investors", "lead investor participating investors", "company_or_investor_announcement", "high"),
        ("event_status", "funding status announced closed filed", "official_or_regulatory_source", "high"),
        ("independent_source", "funding round", "independent_credible_media", "high"),
        ("company_website", "official website", "company_official", "medium"),
        ("investor_announcement", "investor portfolio announcement", "investor_newsroom", "medium"),
        ("company_profile", "founders headquarters business", "company_website_or_credible_profile", "medium"),
        ("previous_round", "previous funding valuation date", "official_or_credible_media", "medium"),
        ("business_update", "products customers revenue business update", "company_newsroom_or_credible_media", "medium"),
    )
    return [
        {
            "entity": entity,
            "field_to_verify": field,
            "query": f'"{entity}" {query_suffix}',
            "expected_source_type": source_type,
            "priority": priority,
        }
        for field, query_suffix, source_type, priority in definitions
    ]


def _same_entity(left, right):
    return _clean_company_name(left).lower() == _clean_company_name(right).lower()


def _company_context(company, report):
    company_record = next(
        (
            item for item in report.get("companies") or []
            if isinstance(item, dict) and _same_entity(item.get("name") or item.get("company_name"), company)
        ),
        {},
    )
    products = [
        item for item in report.get("products") or []
        if isinstance(item, dict) and _same_entity(item.get("company"), company)
    ]
    profile = {
        "website": _clean(company_record.get("website")),
        "country": _clean(company_record.get("country") or company_record.get("location") or company_record.get("headquarters")),
        "founders": _list(company_record.get("founders") or company_record.get("founder")),
        "business": _clean(company_record.get("description") or company_record.get("business")),
        "sector": _clean(company_record.get("sector") or company_record.get("category") or company_record.get("industry")),
        "products": [
            {
                "name": _clean(item.get("name") or item.get("title")),
                "description": _clean(item.get("description") or item.get("tagline") or item.get("what_is_new")),
            }
            for item in products
            if _clean(item.get("name") or item.get("title"))
        ],
    }
    return {key: value for key, value in profile.items() if value not in ("", [], None)}


def _previous_round(raw, company, report):
    current_date = _clean(raw.get("announced_date") or raw.get("closed_date") or raw.get("published_date"))
    candidates = []
    for item in report.get("funding_rounds") or []:
        if not isinstance(item, dict) or item is raw:
            continue
        item_company = item.get("company_name") or item.get("company") or item.get("name")
        if not _same_entity(item_company, company):
            continue
        item_date = _clean(item.get("announced_date") or item.get("closed_date") or item.get("published_date"))
        if current_date and item_date and item_date >= current_date:
            continue
        candidates.append((item_date, item))
    if not candidates:
        return {}
    _, previous = sorted(candidates, key=lambda pair: pair[0], reverse=True)[0]
    return {
        key: value for key, value in {
            "amount_raised": _clean(previous.get("amount_raised") or previous.get("amount")),
            "valuation": _clean(previous.get("valuation")),
            "round": _clean(previous.get("round") or previous.get("round_type")),
            "date": _clean(previous.get("announced_date") or previous.get("closed_date") or previous.get("published_date")),
        }.items() if value
    }


def _scores(raw, source_count, official_count, independent_count, completeness_score, confidence, stage):
    evidence_score = min(100, official_count * 45 + independent_count * 25 + source_count * 5)
    novelty_score = int(raw.get("novelty_score") or 50)
    relevance_score = int(raw.get("relevance_score") or raw.get("signal_score") or 50)
    if stage == "verified":
        actionability_score = max(70, min(100, int((completeness_score + evidence_score) / 2)))
    elif stage == "watchlist":
        actionability_score = min(60, int((completeness_score + evidence_score) / 3))
    else:
        actionability_score = min(35, int((completeness_score + evidence_score) / 4))
    confidence_cap = {"high": 100, "medium": 80, "low": 45}.get(confidence, 35)
    overall = min(confidence_cap, int(evidence_score * 0.3 + completeness_score * 0.25 + novelty_score * 0.15 + relevance_score * 0.15 + actionability_score * 0.15))
    return {
        "evidence_score": evidence_score,
        "completeness_score": completeness_score,
        "novelty_score": novelty_score,
        "relevance_score": relevance_score,
        "actionability_score": actionability_score,
        "overall_signal_score": overall,
    }


def _product_scores(raw, source_count, completeness_score, confidence):
    novelty_score = int(raw.get("novelty_score") or raw.get("signal_score") or 60)
    relevance_score = int(raw.get("relevance_score") or raw.get("signal_score") or 60)
    actionability_score = min(100, max(55, int((completeness_score + relevance_score) / 2)))
    confidence_cap = {"high": 100, "medium": 85, "low": 75}.get(confidence, 65)
    evidence_score = min(100, source_count * 30)
    overall = min(confidence_cap, int(evidence_score * 0.2 + completeness_score * 0.25 + novelty_score * 0.2 + relevance_score * 0.2 + actionability_score * 0.15))
    return {
        "evidence_score": evidence_score,
        "completeness_score": completeness_score,
        "novelty_score": novelty_score,
        "relevance_score": relevance_score,
        "actionability_score": actionability_score,
        "overall_signal_score": overall,
    }


def _completeness(company, status, amount, valuation, round_value, date_value, lead_investors, source_count, analysis):
    score = 0
    score += 20 if company else 0
    score += 15 if status and status != "unclear" else 0
    score += 15 if amount or valuation else 0
    score += 10 if round_value else 0
    score += 10 if date_value else 0
    score += 10 if lead_investors else 0
    score += 10 if source_count else 0
    score += 10 if analysis.get("what_happened") and (analysis.get("why_it_matters") or analysis.get("market_implication") or analysis.get("opportunity_angle")) else 0
    return score


def _product_completeness(product):
    score = 0
    score += 25 if _clean(product.get("name") or product.get("title")) else 0
    score += 15 if _clean(product.get("company")) else 0
    score += 15 if _clean(product.get("description") or product.get("tagline") or product.get("what_is_new")) else 0
    score += 15 if _clean(product.get("product_type") or product.get("category")) else 0
    score += 10 if _clean(product.get("launch_date")) else 0
    score += 10 if _urls(product) else 0
    score += 10 if _clean(product.get("why_it_matters") or product.get("opportunity_angle") or product.get("traction_signals")) else 0
    return score


def _field_has_two_independent_sources(field, report):
    if not isinstance(field, dict) or field.get("value") in (None, "", []):
        return True
    return _source_counts(_list(field.get("source_urls")), report)[2] >= 2


def _stage(confidence, completeness, status, official_count, independent_count, independent_agreement, conflicts):
    if conflicts:
        return "watchlist"
    if confidence == "low":
        return "watchlist"
    if status in {"rumor", "in_talks", "unclear"}:
        return "watchlist"
    if completeness < 70:
        return "watchlist"
    if official_count > 0 or (independent_count >= 2 and independent_agreement):
        return "verified"
    return "candidate"


def normalize_product_launch(raw, report=None):
    report = report or {}
    urls = _urls(raw)
    source_types = _source_types(urls, report)
    source_count, official_count, independent_count = _source_counts(urls, report)
    confidence = _clean(raw.get("confidence")).lower()
    confidence = confidence if confidence in {"high", "medium", "low"} else "low"
    name = _clean(raw.get("name") or raw.get("title"))
    launch_date = _clean(raw.get("launch_date")) or _published_date(raw, report)
    completeness = _product_completeness(raw)
    stage = "verified" if name else "candidate"
    scores = _product_scores(raw, source_count, completeness, confidence)
    description = _clean(raw.get("description") or raw.get("tagline") or raw.get("what_is_new"))
    evidence_gaps = _list(raw.get("evidence_gaps"))
    if not description:
        evidence_gaps.append("product description")

    return {
        "id": f"product-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'unknown'}-{launch_date or 'unknown'}",
        "entity_type": "product_launch",
        "pipeline_stage": stage,
        "name": name,
        "title": name,
        "company": _clean(raw.get("company")),
        "product_type": _clean(raw.get("product_type") or raw.get("category")),
        "platform": _clean(raw.get("platform") or raw.get("launch_channel")),
        "description": description,
        "what_is_new": _clean(raw.get("what_is_new")),
        "traction_signals": _list(raw.get("traction_signals")),
        "target_users": _list(raw.get("target_users")),
        "launch_date": _field(launch_date, urls, source_types, confidence),
        "source_urls": urls,
        "source_count": source_count,
        "official_source_count": official_count,
        "independent_source_count": independent_count,
        "confidence": confidence,
        "evidence_gaps": list(dict.fromkeys(evidence_gaps)),
        "why_it_matters": _clean(raw.get("why_it_matters")),
        "opportunity_angle": _clean(raw.get("opportunity_angle")),
        **scores,
        "raw_candidate": raw,
    }


def normalize_funding_event(raw, report=None):
    report = report or {}
    text = _text(raw, report)
    urls = _urls(raw)
    source_types = _source_types(urls, report)
    source_count, official_count, independent_count = _source_counts(urls, report)
    status = _event_status(raw, text)
    confidence = _confidence(raw.get("confidence"), official_count, independent_count)
    company = _clean_company_name(raw.get("company_name") or raw.get("company") or raw.get("name") or raw.get("title"))

    amount_input = raw.get("amount_raised") if raw.get("amount_raised") is not None else raw.get("amount")
    valuation_input = raw.get("valuation")
    raw_amount = _clean(amount_input)
    raw_valuation = _clean(valuation_input)
    text_valuation = _valuation_from_text(text)
    valuation_value = raw_valuation or text_valuation
    amount_value = raw_amount
    if _looks_like_valuation(text, raw_amount):
        amount_value = ""
        valuation_value = valuation_value or raw_amount

    round_input = raw.get("round") if raw.get("round") is not None else raw.get("round_type")
    round_value = _clean(round_input)
    lead_investors = _list(raw.get("lead_investors") or raw.get("lead_investor"))
    participating = _list(raw.get("participating_investors") or raw.get("investors"))

    published_date = _published_date(raw, report)
    announced_date = _clean(raw.get("announced_date"))
    if status not in {"announced", "closed"}:
        announced_date = ""

    conflicts = list(_list(raw.get("evidence_conflicts")))
    if amount_value and valuation_value and amount_value == valuation_value:
        conflicts.append("amount_raised equals valuation")

    status_input = raw.get("event_status")
    status_field = _field(status_input, urls, source_types, confidence) if _clean(status_input).lower() == status else _field(status, urls, source_types, confidence)
    amount_field = _field(amount_input, urls, source_types, confidence) if amount_value else _field("", urls, source_types, confidence)
    valuation_field = _field(valuation_input, urls, source_types, confidence) if raw_valuation else _field(valuation_value, urls, source_types, confidence)
    round_field = _field(round_input, urls, source_types, confidence)
    announced_field = _field(raw.get("announced_date"), urls, source_types, confidence) if announced_date else _field("", urls, source_types, confidence)
    independent_agreement = all(
        _field_has_two_independent_sources(field, report)
        for field in (status_field, amount_field, valuation_field, round_field, announced_field)
    )
    if official_count == 0 and independent_count >= 2 and not independent_agreement:
        conflicts.append("independent sources do not agree on critical fields")

    profile = _company_context(company, report)
    previous_round = _previous_round(raw, company, report)
    analysis = _analysis(raw)
    if not analysis["what_changed"] and previous_round:
        previous_facts = "、".join(
            value for value in (
                previous_round.get("round"),
                previous_round.get("amount_raised"),
                previous_round.get("valuation"),
                previous_round.get("date"),
            ) if value
        )
        analysis["what_changed"] = f"上一轮可核验信息：{previous_facts}。" if previous_facts else ""
    completeness = _completeness(company, status, amount_value, valuation_value, round_value, announced_date or _clean(raw.get("closed_date") or raw.get("filed_date")), lead_investors, source_count, analysis)
    stage = _stage(confidence, completeness, status, official_count, independent_count, independent_agreement, conflicts)
    scores = _scores(raw, source_count, official_count, independent_count, completeness, confidence, stage)
    gaps = _evidence_gaps(raw, amount_value, lead_investors, status, official_count)
    if not profile.get("business") and not profile.get("products"):
        gaps = list(dict.fromkeys([*gaps, "business update"]))

    event = {
        "id": f"funding-{re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-') or 'unknown'}-{published_date or announced_date or 'unknown'}",
        "entity_type": "funding_event",
        "pipeline_stage": stage,
        "company_name": company,
        "title_zh": _clean(raw.get("title_zh") or raw.get("chinese_title")) or _chinese_title(company, status, amount_value, valuation_value, round_value),
        "title": _clean(raw.get("title") or raw.get("market_signal")) or f"{company} funding signal",
        "event_status": status_field,
        "amount_raised": amount_field,
        "valuation": valuation_field,
        "valuation_type": _field(_clean(raw.get("valuation_type")) or ("target" if status in {"in_talks", "rumor"} and valuation_value else ""), urls, source_types, confidence),
        "currency": _clean(raw.get("currency")) or ("USD" if "$" in (amount_value or valuation_value) else ""),
        "round": round_field,
        "published_date": _field(published_date, urls, source_types, confidence),
        "announced_date": announced_field,
        "filed_date": _field(raw.get("filed_date") if status == "filed" else "", urls, source_types, confidence),
        "closed_date": _field(raw.get("closed_date") if status == "closed" else "", urls, source_types, confidence),
        "lead_investors": _field(raw.get("lead_investors") or raw.get("lead_investor") or [], urls, source_types, confidence),
        "participating_investors": _field(raw.get("participating_investors") or raw.get("investors") or [], urls, source_types, confidence),
        "officially_confirmed": bool(raw.get("officially_confirmed") or official_count > 0),
        "sector_tags": _list(raw.get("sector_tags") or raw.get("sector") or profile.get("sector")),
        "company_profile": profile,
        "previous_round": previous_round,
        "confidence": confidence,
        "source_urls": urls,
        "source_count": source_count,
        "official_source_count": official_count,
        "independent_source_count": independent_count,
        "evidence_conflicts": list(dict.fromkeys(conflicts)),
        "evidence_gaps": gaps,
        "enrichment_tasks": _enrichment_tasks(company) if stage != "verified" else [],
        **analysis,
        **scores,
        "raw_candidate": raw,
    }
    return event


def _dedupe_key(event):
    if event.get("entity_type") == "product_launch":
        name = _clean(event.get("name")).lower()
        date = _clean(event.get("launch_date"))
        return ("product", name, date) if name else None
    if event.get("entity_type") == "funding_event":
        company = _clean(event.get("company_name")).lower()
        status = _clean(event.get("event_status"))
        date = _clean(event.get("announced_date") or event.get("closed_date") or event.get("filed_date") or event.get("published_date"))
        return ("funding", company, status, date) if company else None
    return None


def normalize_report(report):
    product_events = [normalize_product_launch(item, report) for item in report.get("products") or [] if isinstance(item, dict)]
    funding_events = [normalize_funding_event(item, report) for item in report.get("funding_rounds") or [] if isinstance(item, dict)]
    events = product_events + funding_events
    seen = set()
    for event in events:
        key = _dedupe_key(event)
        if not key:
            continue
        if key in seen:
            event["pipeline_stage"] = "rejected"
            event["rejection_reason"] = "duplicate"
            event["actionability_score"] = 0
            event["overall_signal_score"] = 0
        else:
            seen.add(key)
    by_stage = {
        "verified": [item for item in events if item.get("pipeline_stage") == "verified"],
        "watchlist": [item for item in events if item.get("pipeline_stage") == "watchlist"],
        "candidate": [item for item in events if item.get("pipeline_stage") == "candidate"],
        "rejected": [item for item in events if item.get("pipeline_stage") == "rejected"],
    }
    return {
        "events": events,
        "by_stage": by_stage,
        "quality_metrics": build_quality_metrics(events),
        "enrichment_tasks": [task for event in events for task in event.get("enrichment_tasks", [])],
    }


def build_quality_metrics(events):
    total = len(events) or 1
    verified = [item for item in events if item.get("pipeline_stage") == "verified"]
    low = [item for item in events if item.get("confidence") == "low"]
    pending = [item for item in events if item.get("pipeline_stage") == "watchlist"]
    official = [item for item in events if item.get("official_source_count", 0) > 0]
    actionable = [item for item in events if item.get("actionability_score", 0) >= 70]
    avg_completeness = round(sum(item.get("completeness_score", 0) for item in events) / total, 1)
    duplicates = len([item for item in events if item.get("pipeline_stage") == "rejected" and item.get("rejection_reason") == "duplicate"])
    return {
        "verified_ratio": round(len(verified) / total, 2),
        "official_source_coverage": round(len(official) / total, 2),
        "average_completeness_score": avg_completeness,
        "duplicate_rate": round(duplicates / total, 2),
        "low_confidence_ratio": round(len(low) / total, 2),
        "actionable_signal_count": len(actionable),
        "pending_verification_count": len(pending),
    }
