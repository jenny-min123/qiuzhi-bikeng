"""高德地图 POI 证据源（V3 6.3 / 6.4）。

判法：POI 是否存在、POI 类型是否为住宅区 / 居民楼。
未配置 AMAP_API_KEY 时直接跳过，不产生任何推断。
"""

from __future__ import annotations

from urllib.parse import quote

import httpx

from ..config import settings
from ..tools.company_names import same_subject
from .base import EvidenceProvider, EvidenceResult

_RESIDENTIAL_WORDS = ("住宅", "居民", "小区", "公寓", "宿舍")


class AmapPOIProvider(EvidenceProvider):
    name = "地图POI"
    weight = 20.0

    async def fetch(self, company: str) -> EvidenceResult:
        if not settings.amap_api_key:
            return self.unavailable(
                "未配置 AMAP_API_KEY（高德开放平台），地图 POI 证据跳过"
            )

        params = {
            "key": settings.amap_api_key,
            "keywords": company,
            "citylimit": "false",
            "offset": "5",
            "page": "1",
            "extensions": "base",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://restapi.amap.com/v3/place/text", params=params
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            return self.unavailable(f"高德 POI 查询失败：{exc}")

        if str(data.get("status")) != "1":
            return self.unavailable(f"高德返回错误：{data.get('info')}")

        pois = data.get("pois") or []
        link = f"https://www.amap.com/search?query={quote(company)}"

        if not pois:
            return EvidenceResult(
                source=self.name,
                retrieved=True,
                weight=self.weight,
                penalty=8.0,
                evidence_id="ev_amap",
                detail={
                    "poi_count": 0,
                    "summary": "地图未检索到该主体的 POI",
                    "link": link,
                },
            )

        matched = [
            poi
            for poi in pois
            if same_subject(company, str(poi.get("name") or ""))
        ]
        if not matched:
            return EvidenceResult(
                source=self.name,
                retrieved=False,
                weight=self.weight,
                note=(
                    "高德返回了名称相近但主体不一致的地点，未作为证据"
                    f"（示例：{pois[0].get('name') or '未知'}）"
                ),
                evidence_id="ev_amap",
                detail={"poi_count": 0, "link": link},
            )

        first = matched[0]
        poi_type = str(first.get("type") or "")
        poi_address = str(first.get("address") or "")
        poi_name = str(first.get("name") or "")
        residential = any(w in f"{poi_type}{poi_address}" for w in _RESIDENTIAL_WORDS)

        return EvidenceResult(
            source=self.name,
            retrieved=True,
            weight=self.weight,
            penalty=12.0 if residential else 0.0,
            evidence_id="ev_amap",
            detail={
                "poi_count": len(matched),
                "poi_name": poi_name,
                "poi_type": poi_type,
                "poi_address": poi_address,
                "summary": (
                    "POI 类型为住宅 / 居民区"
                    if residential
                    else f"地图检索到 {len(matched)} 个名称一致的主体 POI"
                ),
                "link": link,
            },
        )
