"""统一 LLM 客户端"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Dict, List

from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _load_env_files() -> None:
    """Load .env from common project locations before reading provider keys."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(path, override=False)


_load_env_files()


def _get_required_api_key(env_name: str, provider: str) -> str:
    api_key = os.getenv(env_name, "").strip()
    if not api_key or api_key.startswith("your_"):
        raise RuntimeError(
            f"Missing {env_name} for {provider}. "
            "Set it in .env or export it before starting the backend."
        )
    return api_key

# ============================================================
# Kimi (Moonshot AI) — 默认 provider
# ============================================================
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
KIMI_DEFAULT_MODEL = "kimi-k3"


def query_kimi_model(
    messages: List[Dict],
    model: str = "",
    timeout: float = 120.0,
) -> Optional[Dict]:
    model_id = model or KIMI_DEFAULT_MODEL
    api_key = _get_required_api_key("KIMI_API_KEY", "Kimi")
    try:
        client = OpenAI(base_url=KIMI_BASE_URL, api_key=api_key, timeout=timeout)
        completion = client.chat.completions.create(model=model_id, messages=messages)
        return {"content": completion.choices[0].message.content, "reasoning_details": None}
    except Exception as e:
        _raise_llm_error("Kimi", model_id, len(messages), e)


# ============================================================
# DeepSeek — 独立端点与凭证（DEEPSEEK_API_KEY）
# ============================================================
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"


def query_deepseek_model(
    messages: List[Dict],
    model: str = "",
    timeout: float = 120.0,
) -> Optional[Dict]:
    model_id = model or DEEPSEEK_DEFAULT_MODEL
    api_key = _get_required_api_key("DEEPSEEK_API_KEY", "DeepSeek")
    try:
        client = OpenAI(base_url=DEEPSEEK_BASE_URL, api_key=api_key, timeout=timeout)
        completion = client.chat.completions.create(model=model_id, messages=messages)
        return {"content": completion.choices[0].message.content, "reasoning_details": None}
    except Exception as e:
        _raise_llm_error("DeepSeek", model_id, len(messages), e)


def _raise_llm_error(provider: str, model_id: str, message_count: int, error: Exception) -> None:
    """记录并原样抛出上游错误。

    早期版本记完日志就 return None，上层只能看到"LLM 返回空响应"，
    真正的原因（欠费、余额不足、限流、模型名写错）全被吞掉，
    排查时只能靠猜。这里保留日志，同时把原因带给调用方。
    """
    logger.exception(
        "%s request failed: model_id=%s message_count=%s error_type=%s error=%s",
        provider, model_id, message_count, type(error).__name__, error,
    )
    raise RuntimeError(f"{provider} 调用失败：{type(error).__name__}: {error}") from error


# ============================================================
# 统一入口
# ============================================================
def chat(
    messages: List[Dict],
    system_prompt: str = "",
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """
    统一调用入口。
    provider: "kimi" | "deepseek"；不传则读 LLM_PROVIDER 环境变量，默认 "kimi"
    model:    不传则使用对应 provider 的默认模型
    """
    provider = (provider or os.getenv("LLM_PROVIDER", "") or "kimi").strip().lower()

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    if provider == "deepseek":
        result = query_deepseek_model(full_messages, model=model)
    else:
        result = query_kimi_model(full_messages, model=model)

    content = (result or {}).get("content") or ""
    if content:
        return content

    raise RuntimeError(f"LLM 返回空响应 provider={provider}（可能超时、token 超限或 API 故障）")


async def chat_async(
    messages: List[Dict],
    system_prompt: str = "",
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """chat() 的异步版本，在线程池中执行，不阻塞事件循环。"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, chat, messages, system_prompt, model, provider
    )
