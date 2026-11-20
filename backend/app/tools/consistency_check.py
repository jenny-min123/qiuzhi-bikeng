"""consistency_check：JD—主体一致性校验（9 类规则，第一创新点）。

原则（V3 4.3 / 7.3）：
- 只在「JD 宣称」与「主体事实」两侧都有数据时判定；
- 缺一侧就标记为 not_evaluable，绝不硬猜；
- 主体名不同字号 → 大胆判不同；相同字号 → 只提示，需用户确认；
- severity=critical 的项不参与加权，由 build_report 一票否决。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable

from ..providers.base import EvidenceResult
from ..schemas import JDInfo

# 9 类校验项（V3 4.3 表格），categories 用于报告展示与实验统计
CONSISTENCY_RULES: tuple[tuple[str, str], ...] = (
    ("scale", "规模"),
    ("address", "地址"),
    ("industry", "行业"),
    ("subject", "主体"),
    ("time", "时间"),
    ("salary", "薪资"),
    ("business", "业务"),
    ("contact", "联系"),
    ("qualification", "资质"),
)

_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_INDUSTRY_GROUPS: dict[str, tuple[str, ...]] = {
    "技术研发": ("软件", "开发", "程序", "算法", "数据", "网络", "计算机", "互联网", "人工智能", "测试", "运维", "前端", "后端"),
    "教育培训": ("教育", "培训", "咨询", "教学", "课程", "讲师"),
    "医疗健康": ("医疗", "医药", "护理", "医院", "药店", "生物", "健康", "医师", "药师"),
    "建筑工程": ("建筑", "工程", "施工", "装饰", "装修", "建材", "监理"),
    "物流运输": ("物流", "运输", "仓储", "快递", "货运", "配送"),
    "餐饮住宿": ("餐饮", "食品", "酒店", "住宿", "厨师", "客房", "前台"),
    "销售运营": ("销售", "贸易", "零售", "批发", "电商", "运营", "客服", "市场", "门店"),
    "传媒设计": ("传媒", "广告", "文化", "视频", "剪辑", "设计", "摄影", "新媒体"),
    "生产制造": ("制造", "生产", "加工", "机械", "设备", "仪表", "装配"),
    "安保物业": ("安保", "保安", "物业", "清洁", "家政"),
    "财务金融": ("金融", "财务", "会计", "投资", "保险", "出纳"),
    "人力行政": ("人力资源", "招聘", "行政", "文员", "助理", "人事"),
}
_FREE_MAIL = {
    "qq.com",
    "163.com",
    "126.com",
    "sina.com",
    "foxmail.com",
    "gmail.com",
    "outlook.com",
    "hotmail.com",
}
_COMPANY_SUFFIX = re.compile(
    r"(有限责任公司|股份有限公司|有限公司|集团公司|集团|工作室|研究院|事务所)$"
)


def _facts(evidence: list[EvidenceResult]) -> dict:
    merged: dict = {}
    for item in evidence:
        if item.retrieved:
            merged.update(item.detail or {})
    return merged


def _mismatch(
    category: str,
    jd_claim: str | None,
    subject_fact: str,
    severity: str,
    penalty: float,
    explanation: str,
    jd_span: tuple[int, int] | None = None,
) -> dict:
    return {
        "category": category,
        "jd_claim": jd_claim,
        "jd_span": jd_span,
        "subject_fact": subject_fact,
        "severity": severity,
        "penalty": penalty,
        "explanation": explanation,
    }


def _headcount(value: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(万)?\s*(?:人|名)", value or "")
    if not match:
        return None
    number = float(match.group(1))
    return number * 10000 if match.group(2) else number


def _rule_scale(jd: JDInfo, facts: dict) -> list[dict] | None:
    claimed = _headcount(jd.claimed_headcount or "")
    actual = facts.get("insured_count") or facts.get("employee_count")
    if claimed is None or not isinstance(actual, (int, float)) or actual <= 0:
        return None
    fact_text = f"公开参保 / 员工人数约 {int(actual)} 人"
    if claimed > actual * 2 and claimed - actual >= 10:
        return [
            _mismatch(
                "规模",
                jd.claimed_headcount,
                fact_text,
                "high",
                15.0,
                f"JD 宣称规模为「{jd.claimed_headcount}」，公开数据为{fact_text}，存在规模虚标可能。",
            )
        ]
    if claimed > actual * 1.5:
        return [
            _mismatch(
                "规模",
                jd.claimed_headcount,
                fact_text,
                "medium",
                8.0,
                f"JD 宣称规模「{jd.claimed_headcount}」高于公开数据（{fact_text}），建议核实。",
            )
        ]
    return []


def _cities(text: str) -> set[str]:
    return set(re.findall(r"[一-龥]{2,6}?市", text))


def _districts(text: str) -> set[str]:
    return set(re.findall(r"[一-龥]{2,6}?(?:区|县)", text))


def _rule_address(jd: JDInfo, facts: dict) -> list[dict] | None:
    jd_address = jd.visit_address
    fact_address = facts.get("registered_address") or facts.get("poi_address")
    if not jd_address or not fact_address:
        return None

    jd_cities, fact_cities = _cities(jd_address), _cities(str(fact_address))
    jd_districts, fact_districts = _districts(jd_address), _districts(str(fact_address))

    if jd_cities and fact_cities and not (jd_cities & fact_cities):
        return [
            _mismatch(
                "地址",
                jd_address,
                f"公开地址：{fact_address}",
                "high",
                15.0,
                "JD 到访地址与公开注册 / 地图地址不在同一城市，建议核实实际办公地址。",
            )
        ]
    if jd_districts and fact_districts and not (jd_districts & fact_districts):
        return [
            _mismatch(
                "地址",
                jd_address,
                f"公开地址：{fact_address}",
                "medium",
                8.0,
                "JD 到访地址与公开注册 / 地图地址不在同一区域，建议核实。",
            )
        ]
    if not (jd_cities or jd_districts or fact_cities or fact_districts):
        return None
    return []


def _claim_years(text: str) -> int | None:
    match = re.search(
        r"(?:深耕|成立|经营|从事)[^\n。；]{0,10}?([一二三四五六七八九十\d]{1,3})\s*余?年",
        text or "",
    )
    if not match:
        return None
    raw = match.group(1)
    if raw.isdigit():
        return int(raw)
    digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if raw == "十":
        return 10
    if "十" in raw:
        tens, _, ones = raw.partition("十")
        return (digits.get(tens, 1) if tens else 1) * 10 + (digits.get(ones, 0) if ones else 0)
    return digits.get(raw)


def _parse_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y年%m月"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _rule_time(jd: JDInfo, facts: dict) -> list[dict] | None:
    claimed_years = _claim_years(jd.text)
    founded = _parse_date(facts.get("founded_at") or facts.get("established_date"))
    if claimed_years is None or founded is None:
        return None
    actual_years = (date.today() - founded).days / 365.25
    if claimed_years >= 3 and actual_years * 2 < claimed_years:
        return [
            _mismatch(
                "时间",
                f"声称经营约 {claimed_years} 年",
                f"公开成立日期：{founded.isoformat()}（约 {actual_years:.1f} 年）",
                "high",
                12.0,
                "JD 宣称的经营年限明显长于公开成立时间，存在包装痕迹。",
            )
        ]
    return []


def _normalize_name(name: str) -> str:
    return _COMPANY_SUFFIX.sub("", re.sub(r"\s+", "", name or ""))


def _rule_subject(jd: JDInfo, facts: dict) -> list[dict] | None:
    signing_party = facts.get("signing_party")
    if not jd.company or not signing_party:
        return None
    if _normalize_name(jd.company) == _normalize_name(str(signing_party)):
        return []
    return [
        _mismatch(
            "主体",
            jd.company,
            f"签约方：{signing_party}",
            "critical",
            0.0,
            "招聘方与签约方不是同一主体，这是招转培的典型特征。建议：不要签字、不要下载任何 App、不要转账。",
        )
    ]


def _rule_contact(jd: JDInfo, facts: dict) -> list[dict] | None:
    official_domain = facts.get("domain") or facts.get("official_domain")
    if not official_domain:
        return None
    official_domain = str(official_domain).lower()
    for match in _EMAIL_PATTERN.finditer(jd.text):
        email_domain = match.group(0).split("@", 1)[1].lower()
        if email_domain in _FREE_MAIL:
            return [
                _mismatch(
                    "联系",
                    match.group(0),
                    f"官网域名：{official_domain}",
                    "medium",
                    6.0,
                    "招聘方使用个人邮箱而非企业域名邮箱，建议核实联系人身份。",
                    jd_span=match.span(),
                )
            ]
        if email_domain != official_domain and not email_domain.endswith(
            "." + official_domain
        ):
            return [
                _mismatch(
                    "联系",
                    match.group(0),
                    f"官网域名：{official_domain}",
                    "medium",
                    6.0,
                    "招聘邮箱域名与公开官网域名不一致，建议核实联系人身份。",
                    jd_span=match.span(),
                )
            ]
    return []


def _industry_groups(text: str) -> set[str]:
    return {
        group
        for group, keywords in _INDUSTRY_GROUPS.items()
        if any(keyword in text for keyword in keywords)
    }


def _rule_industry(jd: JDInfo, facts: dict) -> list[dict] | None:
    """岗位方向与经营范围是否匹配（需要工商经营范围）。"""
    position = jd.position
    business_scope = facts.get("business_scope")
    if not position or not business_scope:
        return None

    position_groups = _industry_groups(position)
    scope_groups = _industry_groups(str(business_scope))
    if not position_groups or not scope_groups:
        return None
    if position_groups & scope_groups:
        return []

    return [
        _mismatch(
            "行业",
            f"岗位：{position}",
            f"经营范围：{business_scope}",
            "medium",
            8.0,
            "岗位方向（" + "、".join(sorted(position_groups)) + "）未体现在经营范围（"
            + "、".join(sorted(scope_groups)) + "）中，建议核实岗位是否真实。",
        )
    ]


def _not_evaluable(jd: JDInfo, facts: dict) -> list[dict] | None:
    """薪资 / 业务 / 资质：需要市场中位薪资、主营业务标签、行业许可等数据。"""
    return None


_EVALUATORS: dict[str, Callable[[JDInfo, dict], list[dict] | None]] = {
    "scale": _rule_scale,
    "address": _rule_address,
    "industry": _rule_industry,
    "subject": _rule_subject,
    "time": _rule_time,
    "salary": _not_evaluable,
    "business": _not_evaluable,
    "contact": _rule_contact,
    "qualification": _not_evaluable,
}


def consistency_check(jd: JDInfo, evidence: list[EvidenceResult]) -> dict:
    facts = _facts(evidence)
    mismatches: list[dict] = []
    evaluated: list[str] = []
    not_evaluable: list[str] = []

    for key, category in CONSISTENCY_RULES:
        try:
            result = _EVALUATORS[key](jd, facts)
        except Exception:
            result = None
        if result is None:
            not_evaluable.append(category)
            continue
        evaluated.append(category)
        mismatches.extend(result)

    for index, item in enumerate(mismatches, start=1):
        item["evidence_id"] = f"cc_{index:03d}"

    critical = [m for m in mismatches if m["severity"] == "critical"]
    return {
        "mismatches": mismatches,
        "critical": critical,
        "rules_evaluated": evaluated,
        "rules_not_evaluable": not_evaluable,
    }
