"""从工商截图 OCR 文本中抽取快照字段。

只做「候选抽取」，不自动保存：OCR 可能把标签、值、相邻字段混在一起，
前端必须让用户核对后才能写入快照。
"""

from __future__ import annotations

import re
from datetime import date

from .company_names import extract_company_names
from .snapshot_store import parse_date

_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "company": ("企业名称", "公司名称", "企业全称"),
    "credit_code": ("统一社会信用代码", "社会信用代码", "信用代码"),
    "founded_at": ("成立日期", "成立时间"),
    "registration_status": ("登记状态", "经营状态", "企业状态"),
    "registered_address": ("注册地址", "住所", "企业地址"),
    "business_scope": ("经营范围", "业务范围"),
    "insured_count": ("参保人数", "社保人数", "参保职工人数"),
    "employee_count": ("员工人数", "人员规模", "员工总数"),
    "official_domain": ("官网", "网址", "网站"),
}
_ALL_LABELS = tuple(
    sorted({label for labels in _FIELD_LABELS.values() for label in labels}, key=len, reverse=True)
)
_STATUS_PATTERN = re.compile(r"存续|在业|开业|在营|注销|吊销|迁出|停业|清算|撤销")
_CREDIT_CODE_PATTERN = re.compile(r"[0-9A-Z]{18}")
_DOMAIN_PATTERN = re.compile(r"(?:https?://)?([A-Za-z0-9][A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_REQUIRED_LABELS = {
    "company": "公司全称",
    "founded_at": "成立日期",
    "registered_address": "注册地址",
    "insured_count": "参保人数",
    "business_scope": "经营范围",
    "registration_status": "登记状态",
}


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _clean_value(value: str) -> str:
    value = value.strip().strip("：:，,。；;| ")
    return value


def _contains_label(line: str) -> bool:
    return any(label in line for label in _ALL_LABELS)


def _value_after_label(line: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        if label not in line:
            continue
        rest = line.split(label, 1)[1]
        rest = _clean_value(rest.lstrip("：: "))
        if rest:
            return rest
    return None


def _extract_field(
    lines: list[str], labels: tuple[str, ...], max_follow: int = 3
) -> str | None:
    for index, line in enumerate(lines):
        if not any(label in line for label in labels):
            continue
        value = _value_after_label(line, labels)
        if value:
            return value
        collected: list[str] = []
        for following in lines[index + 1 : index + 1 + max_follow]:
            if _contains_label(following):
                break
            collected.append(following)
        if collected:
            return _clean_value(" ".join(collected))
    return None


def _parse_iso_date(value: str | None, text: str) -> str | None:
    if value:
        parsed = parse_date(value)
        if parsed:
            return parsed.isoformat()
        match = re.search(r"(\d{4})\s*[年/-]\s*(\d{1,2})\s*[月/-]\s*(\d{1,2})", value)
        if match:
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
            except ValueError:
                pass
    match = re.search(r"(\d{4})\s*[年/-]\s*(\d{1,2})\s*[月/-]\s*(\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            return None
    return None


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d+)", value.replace(",", ""))
    return int(match.group(1)) if match else None


def _parse_company(lines: list[str], text: str) -> str | None:
    value = _extract_field(lines, _FIELD_LABELS["company"], max_follow=1)
    if value and any(suffix in value for suffix in ("公司", "集团", "工作室", "事务所", "研究院")):
        return value
    names = extract_company_names(text)
    return names[0] if names else None


def _parse_credit_code(lines: list[str], text: str) -> str | None:
    value = _extract_field(lines, _FIELD_LABELS["credit_code"], max_follow=1)
    match = _CREDIT_CODE_PATTERN.search((value or "") + " " + text)
    return match.group(0) if match else None


def _parse_status(lines: list[str]) -> str | None:
    value = _extract_field(lines, _FIELD_LABELS["registration_status"], max_follow=1)
    match = _STATUS_PATTERN.search(value or "")
    return match.group(0) if match else None


def _parse_business_scope(lines: list[str]) -> str | None:
    value = _extract_field(lines, _FIELD_LABELS["business_scope"], max_follow=8)
    if not value:
        return None
    return value[:500]


def _parse_domain(lines: list[str]) -> str | None:
    value = _extract_field(lines, _FIELD_LABELS["official_domain"], max_follow=1)
    match = _DOMAIN_PATTERN.search(value or "")
    return match.group(1) if match else None


def extract_snapshot_fields(text: str) -> dict:
    lines = [_normalize_line(line) for line in (text or "").splitlines() if line.strip()]
    fields = {
        "company": _parse_company(lines, text),
        "credit_code": _parse_credit_code(lines, text),
        "founded_at": _parse_iso_date(
            _extract_field(lines, _FIELD_LABELS["founded_at"], max_follow=1), text
        ),
        "registered_address": _extract_field(
            lines, _FIELD_LABELS["registered_address"], max_follow=2
        ),
        "insured_count": _parse_int(
            _extract_field(lines, _FIELD_LABELS["insured_count"], max_follow=1)
        ),
        "employee_count": _parse_int(
            _extract_field(lines, _FIELD_LABELS["employee_count"], max_follow=1)
        ),
        "business_scope": _parse_business_scope(lines),
        "registration_status": _parse_status(lines),
        "official_domain": _parse_domain(lines),
    }

    missing = [
        label
        for key, label in _REQUIRED_LABELS.items()
        if fields.get(key) in (None, "")
    ]
    warnings = [
        "来源 URL 与查询日期无法从截图可靠识别，请在保存前手工确认。",
        "OCR 与字段抽取都可能出错，请逐项核对后再保存。",
    ]
    if "参保人数" in missing:
        warnings.append("参保人数常见于企业年报或社保信息，截图中可能没有。")
    if fields.get("business_scope"):
        warnings.append("经营范围可能跨行，已尽量合并，请核对是否完整。")
    if not fields.get("company"):
        warnings.append("未识别到公司全称，请手工补充。")

    return {
        "text": text,
        "fields": fields,
        "missing_fields": missing,
        "warnings": warnings,
        "suggested_fetched_at": date.today().isoformat(),
    }
