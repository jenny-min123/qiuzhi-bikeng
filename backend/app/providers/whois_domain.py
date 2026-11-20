"""域名年龄证据源（V3 6.2：域名注册时间最难伪造）。

域名来自 app/data/company_alias.json 的 domains 映射。
映射为空或 python-whois 未安装时跳过，不猜测域名。
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from functools import lru_cache

from ..config import settings
from .base import EvidenceProvider, EvidenceResult


@lru_cache(maxsize=1)
def _domains() -> dict[str, str]:
    if not settings.alias_path.exists():
        return {}
    try:
        with settings.alias_path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    domains = data.get("domains") or {}
    return {str(k): str(v) for k, v in domains.items()}


def _lookup_domain(company: str) -> str | None:
    domains = _domains()
    if company in domains:
        return domains[company]
    for name, domain in domains.items():
        if name and (name in company or company in name):
            return domain
    return None


def _query_whois(domain: str) -> dict:
    import whois  # python-whois，可选依赖

    record = whois.whois(domain)
    created = record.get("creation_date")
    if isinstance(created, list):
        created = created[0] if created else None
    if isinstance(created, datetime):
        created_date = created.date()
    elif isinstance(created, date):
        created_date = created
    else:
        created_date = None
    return {"domain": domain, "creation_date": created_date}


class WhoisDomainProvider(EvidenceProvider):
    name = "域名年龄"
    weight = 15.0

    async def fetch(self, company: str) -> EvidenceResult:
        domain = _lookup_domain(company)
        if not domain:
            return self.unavailable(
                "未在 company_alias.json 中找到该公司域名，域名年龄证据跳过"
            )
        try:
            info = await asyncio.to_thread(_query_whois, domain)
        except ImportError:
            return self.unavailable("python-whois 未安装，域名年龄证据跳过")
        except Exception as exc:
            return self.unavailable(f"WHOIS 查询失败：{exc}")

        created_date = info.get("creation_date")
        if created_date is None:
            return self.unavailable(f"WHOIS 未返回 {domain} 的注册日期")

        age_years = (date.today() - created_date).days / 365.25
        if age_years < 1:
            penalty = 12.0
            summary = f"域名 {domain} 注册不足 1 年（{created_date}）"
        elif age_years < 2:
            penalty = 6.0
            summary = f"域名 {domain} 注册不足 2 年（{created_date}）"
        else:
            penalty = 0.0
            summary = f"域名 {domain} 已注册约 {age_years:.1f} 年"

        return EvidenceResult(
            source=self.name,
            retrieved=True,
            weight=self.weight,
            penalty=penalty,
            evidence_id="ev_whois",
            detail={
                "domain": domain,
                "creation_date": created_date.isoformat(),
                "age_years": round(age_years, 2),
                "summary": summary,
                "link": f"https://who.is/whois/{domain}",
            },
        )
