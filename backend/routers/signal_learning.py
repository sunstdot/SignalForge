"""参考链接学习 API：提交链接 → 分析价值特征 → 试找类似 → 学习结果参与后续任务。"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import signal_learning as learning

router = APIRouter()


class CreateReferenceRequest(BaseModel):
    url: str
    user_reason: str = ""   # 为什么觉得有用
    user_wants: str = ""    # 希望继续看到什么


class UpdateReferenceRequest(BaseModel):
    user_reason: Optional[str] = None
    user_wants: Optional[str] = None


class FeedbackRequest(BaseModel):
    index: int
    verdict: str  # matched | topic_only | irrelevant


def _require_safe_url(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="url must be a valid http or https URL")
    return url.strip()


@router.get("/references")
async def list_references():
    """查看全部参考样本（含停用的）。"""
    return {"references": learning.load_references()}


@router.get("/preferences")
async def get_preferences():
    """查看当前生效的偏好（可检查、可追溯）。"""
    return learning.effective_preferences()


@router.get("/references/{reference_id}")
async def get_reference(reference_id: str):
    reference = learning.get_reference_by_id(reference_id)
    if not reference:
        raise HTTPException(status_code=404, detail="reference not found")
    return reference


@router.post("/references", status_code=201)
async def create_reference(body: CreateReferenceRequest):
    """提交参考链接：读取内容 → 提取价值特征 → 保存样本 → 立即试找类似信息。

    返回结构区分：样本保存 / 内容分析 / 学习生效 / 试找结果 / 检索失败。
    """
    url = _require_safe_url(body.url)

    fetched = await learning.fetch_reference_content(url)
    record = learning.create_reference_record(
        url=url,
        user_reason=body.user_reason,
        user_wants=body.user_wants,
        title=fetched.get("title") or url,
        content_snippet=fetched.get("content") or "",
    )

    analysis = await learning.analyze_reference_content(
        title=record.get("title") or "",
        content=record.get("content_snippet") or "",
        user_reason=body.user_reason,
        user_wants=body.user_wants,
    )

    if analysis.get("ok"):
        # 分析成功后，把分析结果与正文状态写回样本，并让偏好生效。
        analysis_status = "partial" if not fetched.get("fetch_ok") else "complete"
        learning.update_reference_record(record["id"], {
            "analysis": {k: v for k, v in analysis.items() if k != "ok"},
            "analysis_status": analysis_status,
            "fetch_status": "ok" if fetched.get("fetch_ok") else fetched.get("reason") or "unknown",
        })
        preferences = learning.refresh_preferences()
    else:
        # 抓取失败或分析失败：保留缺失状态，不伪装成学习成功。
        learning.update_reference_record(record["id"], {
            "analysis_status": "fetch_failed" if not fetched.get("fetch_ok") else "analysis_failed",
            "fetch_status": fetched.get("fetch_ok") and "ok" or (fetched.get("reason") or "unknown"),
        })
        preferences = learning.effective_preferences()

    record = learning.get_reference_by_id(record["id"])

    similar = None
    if analysis.get("ok"):
        similar = await learning.find_similar_for_reference(record["id"], limit=3)
        # 用户未填写原因时，明确标注系统推断，不伪装成用户已表达的偏好。
        if not body.user_reason.strip():
            similar["inferred_reason"] = True

    return {
        "sample_saved": True,
        "sample_id": record["id"],
        "fetch_ok": fetched.get("fetch_ok"),
        "fetch_reason": fetched.get("reason"),
        "analysis_complete": analysis.get("ok", False),
        "analysis_error": analysis.get("error", ""),
        "learning_active": analysis.get("ok", False),
        "reference": record,
        "preferences": preferences,
        "similar": similar,
    }


@router.post("/references/{reference_id}/update")
async def update_reference(reference_id: str, body: UpdateReferenceRequest):
    """修改用户填写的原因/期望，并重新分析（用户填写的原因优先于系统推测）。"""
    reference = learning.get_reference_by_id(reference_id)
    if not reference:
        raise HTTPException(status_code=404, detail="reference not found")

    updates = {}
    if body.user_reason is not None:
        updates["user_reason"] = body.user_reason.strip()
    if body.user_wants is not None:
        updates["user_wants"] = body.user_wants.strip()
    if updates:
        learning.update_reference_record(reference_id, updates)

    updated = learning.get_reference_by_id(reference_id)
    analysis = await learning.analyze_reference_content(
        title=updated.get("title") or "",
        content=updated.get("content_snippet") or "",
        user_reason=updated.get("user_reason") or "",
        user_wants=updated.get("user_wants") or "",
    )
    if analysis.get("ok"):
        learning.update_reference_record(reference_id, {
            "analysis": {k: v for k, v in analysis.items() if k != "ok"},
            "analysis_status": "complete",
        })
    learning.refresh_preferences()
    return learning.get_reference_by_id(reference_id)


@router.post("/references/{reference_id}/disable")
async def disable_reference(reference_id: str):
    """停用一条学习结果；后续任务使用更新后的偏好，其他样本支持的偏好不受影响。"""
    reference = learning.set_reference_status(reference_id, "disabled")
    if not reference:
        raise HTTPException(status_code=404, detail="reference not found")
    learning.refresh_preferences()
    return {"ok": True, "reference": reference}


@router.post("/references/{reference_id}/enable")
async def enable_reference(reference_id: str):
    """撤销停用。"""
    reference = learning.set_reference_status(reference_id, "active")
    if not reference:
        raise HTTPException(status_code=404, detail="reference not found")
    learning.refresh_preferences()
    return {"ok": True, "reference": reference}


@router.delete("/references/{reference_id}")
async def delete_reference(reference_id: str):
    """撤销（删除）一条参考样本。"""
    references = learning.load_references()
    remaining = [r for r in references if r.get("id") != reference_id]
    if len(remaining) == len(references):
        raise HTTPException(status_code=404, detail="reference not found")
    learning.save_references(remaining)
    learning.refresh_preferences()
    return {"ok": True}


@router.post("/references/{reference_id}/find-similar")
async def find_similar(reference_id: str):
    """重新试找类似内容（最多 3 条），返回推荐原因与原始链接。"""
    reference = learning.get_reference_by_id(reference_id)
    if not reference:
        raise HTTPException(status_code=404, detail="reference not found")
    return await learning.find_similar_for_reference(reference_id, limit=3)


@router.post("/references/{reference_id}/feedback")
async def feedback(reference_id: str, body: FeedbackRequest):
    """对试找结果提供反馈（符合预期 / 主题相似但价值不同 / 不相关），用于修正偏好。"""
    reference = learning.record_feedback(reference_id, body.index, body.verdict)
    if not reference:
        raise HTTPException(status_code=404, detail="reference not found")
    return {"ok": True, "feedback": reference.get("feedback")}
