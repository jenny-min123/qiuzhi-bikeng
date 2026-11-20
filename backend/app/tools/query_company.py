"""query_company：主体查询（缓存 → API → 降级）。

工商数据是可选证据源（V3 3.1）。当前未配置通道时如实返回 retrieved=False，
上层 score_company 会做权重归一化并在报告中标注缺失。
"""

from __future__ import annotations

from dataclasses import asdict

from ..config import settings
from ..db import cache_get, cache_set
from ..providers.gongshang import GongshangProvider


async def query_company(company: str) -> dict:
    company = company.strip()
    if not company:
        return {
            "source": "工商信息",
            "retrieved": False,
            "weight": 25.0,
            "penalty": 0.0,
            "evidence_id": "",
            "detail": {},
            "note": "未提供公司名称",
        }

    key = f"company:{company.lower()}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    result = await GongshangProvider().fetch(company)
    payload = asdict(result)
    ttl = (
        settings.cache_ttl_seconds
        if result.retrieved
        else settings.failed_cache_ttl_seconds
    )
    cache_set(key, payload, ttl)
    return payload
