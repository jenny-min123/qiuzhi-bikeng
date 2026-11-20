"""工商信息证据源（可选，V3 3.1「可插拔」原则的权重最高一路）。

两种来源，优先级从高到低：
1. 正式工商 API（企查查 / 天眼查 / 云市场），当前未配置，保留接入位；
2. 人工核验快照 `backend/data/company_snapshots.json`：由用户从国家企业信用
   信息公示系统等公开渠道人工查询后填写，必须带 source_url 与 fetched_at。

快照不是实时数据，报告会明确标注「人工核验快照」。缺少来源字段的记录
一律按未核验处理，不参与评分。
"""

from __future__ import annotations

import json
from datetime import date, datetime

from ..config import settings
from ..tools.company_names import same_subject
from .base import EvidenceProvider, EvidenceResult

_OK_STATUS = {"存续", "在业", "开业", "在营", "正常"}
_REQUIRED_PROVENANCE = ("source_url", "fetched_at")
_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y年%m月")


def _parse_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _load_snapshots() -> dict[str, dict]:
    path = settings.snapshot_path
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    companies = data.get("companies") or {}
    return {
        str(name): facts
        for name, facts in companies.items()
        if isinstance(facts, dict)
    }


def _find_snapshot(company: str) -> tuple[str | None, dict | None]:
    snapshots = _load_snapshots()
    if company in snapshots:
        return company, snapshots[company]
    for name, facts in snapshots.items():
        if same_subject(company, name):
            return name, facts
    return None, None


def _score_snapshot(facts: dict) -> tuple[float, list[str]]:
    penalty = 0.0
    reasons: list[str] = []

    status = str(facts.get("registration_status") or "").strip()
    if status and status not in _OK_STATUS:
        penalty += 20
        reasons.append(f"登记状态为「{status}」")

    insured = facts.get("insured_count")
    if isinstance(insured, (int, float)) and not isinstance(insured, bool):
        if insured <= 0:
            penalty += 20
            reasons.append("参保人数为 0")
        elif insured <= 3:
            penalty += 12
            reasons.append(f"参保人数仅 {int(insured)} 人")
        elif insured < 10:
            penalty += 6
            reasons.append(f"参保人数仅 {int(insured)} 人")

    founded = _parse_date(facts.get("founded_at"))
    if founded:
        years = (date.today() - founded).days / 365.25
        if years < 1:
            penalty += 15
            reasons.append(f"成立不足 1 年（{founded.isoformat()}）")
        elif years < 2:
            penalty += 8
            reasons.append(f"成立不足 2 年（{founded.isoformat()}）")
        elif years < 3:
            penalty += 4
            reasons.append(f"成立不足 3 年（{founded.isoformat()}）")

    return penalty, reasons


def _summary(facts: dict, reasons: list[str]) -> str:
    parts = ["人工核验快照"]
    status = facts.get("registration_status")
    if status:
        parts.append(f"状态：{status}")
    if facts.get("founded_at"):
        parts.append(f"成立：{facts.get('founded_at')}")
    if isinstance(facts.get("insured_count"), (int, float)):
        parts.append(f"参保：{int(facts['insured_count'])} 人")
    if facts.get("registered_address"):
        parts.append(f"注册地址：{facts.get('registered_address')}")
    if reasons:
        parts.append("；".join(reasons))
    return "；".join(parts)


class GongshangProvider(EvidenceProvider):
    name = "工商信息"
    # 快照覆盖成立时间、参保人数、注册地址、经营范围等多个字段，
    # 权重高于单一信号（地图 POI / ICP / 域名）。
    weight = 50.0

    async def fetch(self, company: str) -> EvidenceResult:
        # 正式 API 接入位：配置 GONGSHANG_API_URL / KEY 后在此调用，
        # 再把响应归一化成下方 detail 字段即可，评分与校验逻辑不用改。
        matched_name, facts = _find_snapshot(company)
        if not facts:
            return self.unavailable(
                "未配置工商 API，且人工核验快照中没有该公司的记录"
            )

        missing = [
            field
            for field in _REQUIRED_PROVENANCE
            if not str(facts.get(field) or "").strip()
        ]
        if missing:
            return self.unavailable(
                f"人工快照缺少来源字段：{'、'.join(missing)}，按未核验处理"
            )

        penalty, reasons = _score_snapshot(facts)
        detail = {
            key: facts.get(key)
            for key in (
                "credit_code",
                "founded_at",
                "registered_address",
                "insured_count",
                "employee_count",
                "business_scope",
                "registration_status",
                "official_domain",
                "source_url",
                "fetched_at",
                "note",
            )
            if facts.get(key) not in (None, "")
        }
        detail.update(
            {
                "summary": _summary(facts, reasons),
                "reasons": reasons,
                "link": facts.get("source_url"),
                "snapshot": True,
                "snapshot_company": matched_name,
            }
        )

        return EvidenceResult(
            source="工商信息（人工核验快照）",
            retrieved=True,
            weight=self.weight,
            penalty=penalty,
            evidence_id="ev_gongshang_snapshot",
            detail=detail,
        )
