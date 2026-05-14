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
KIMI_DEFAULT_MODEL = "kimi-k2.5"


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
        logger.exception(
            "Kimi request failed: model_id=%s message_count=%s error_type=%s error=%s",
            model_id, len(messages), type(e).__name__, e,
        )
        return None


# ============================================================
# DeepSeek — 用于商业机会 & 研发效能机会分析
# ============================================================
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-pro"


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
        logger.exception(
            "DeepSeek request failed: model_id=%s message_count=%s error_type=%s error=%s",
            model_id, len(messages), type(e).__name__, e,
        )
        return None


# ============================================================
# 统一入口
# ============================================================
def chat(
    messages: List[Dict],
    system_prompt: str = "",
    model: Optional[str] = None,
    provider: str = "kimi",
) -> str:
    """
    统一调用入口。
    provider: "kimi"（默认）| "deepseek"
    model:    不传则使用对应 provider 的默认模型
    """
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    if provider == "deepseek":
        result = query_deepseek_model(full_messages, model=model or DEEPSEEK_DEFAULT_MODEL)
    else:
        result = query_deepseek_model(full_messages, model=model or DEEPSEEK_DEFAULT_MODEL)

    content = (result or {}).get("content") or ""
    if content:
        return content

    raise RuntimeError(f"LLM 返回空响应 provider={provider}（可能超时、token 超限或 API 故障）")


async def chat_async(
    messages: List[Dict],
    system_prompt: str = "",
    model: Optional[str] = None,
    provider: str = "kimi",
) -> str:
    """chat() 的异步版本，在线程池中执行，不阻塞事件循环。"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, chat, messages, system_prompt, model, provider
    )
