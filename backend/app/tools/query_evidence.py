"""query_evidence：并行调用所有已注册证据源，聚合成证据集合。

V3 6.1：任一 Provider 拿不到就跳过；失败结果短暂缓存，成功结果缓存 24h。
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from .. import db
from ..config import settings
from ..providers.amap_poi import AmapPOIProvider
from ..providers.base import EvidenceProvider, EvidenceResult
from ..providers.gongshang import GongshangProvider
from ..providers.icp_record import ICPRecordProvider
from ..providers.platform_auth import PlatformAuthProvider
from ..providers.social_sentiment import SocialSentimentProvider
from ..providers.whois_domain import WhoisDomainProvider

PROVIDERS: tuple[EvidenceProvider, ...] = (
    AmapPOIProvider(),
    ICPRecordProvider(),
    WhoisDomainProvider(),
    PlatformAuthProvider(),
    SocialSentimentProvider(),
    GongshangProvider(),
)


# Provider 行为变更时递增，避免旧缓存污染结果
CACHE_VERSION = "2"


async def _fetch_cached(provider: EvidenceProvider, company: str) -> EvidenceResult:
    key = f"evidence:{CACHE_VERSION}:{provider.name}:{company.strip().lower()}"
    cached = db.cache_get(key)
    if cached is not None:
        try:
            return EvidenceResult(**cached)
        except TypeError:
            pass  # 缓存结构变更时忽略旧缓存

    try:
        result = await provider.fetch(company)
    except Exception as exc:
        result = provider.unavailable(f"{provider.name} 查询异常：{exc}")

    ttl = (
        settings.cache_ttl_seconds
        if result.retrieved
        else settings.failed_cache_ttl_seconds
    )
    db.cache_set(key, asdict(result), ttl)
    return result


async def query_evidence(company: str | None) -> list[EvidenceResult]:
    if not company or not company.strip():
        return []
    return list(
        await asyncio.gather(*(_fetch_cached(p, company) for p in PROVIDERS))
    )
