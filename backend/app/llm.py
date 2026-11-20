"""LLM 客户端封装。

V3 5.1：LLM 不判风险，只做「理解 + 调度 + 归因表达」。
本模块只提供受约束的 JSON 调用；未配置 key 时返回 None，由调用方走
确定性降级路径（regex 抽取 / 规则模板解释）。
"""

from __future__ import annotations

import json
from typing import Any

from .config import settings


def enabled() -> bool:
    return bool(settings.llm_api_key)


def _extract_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        # 去掉 ```json ... ``` 包裹
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


async def chat_json(system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
    """调用 LLM 并解析 JSON。失败返回 None（调用方必须能降级）。"""
    if not enabled():
        return None
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return None

    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=30,
    )
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return _extract_json(content)
    except Exception:
        # 网络错误 / 额度错误 / 返回非 JSON 都按不可用处理
        return None
