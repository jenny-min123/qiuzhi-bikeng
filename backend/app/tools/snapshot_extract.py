"""从工商截图 OCR 文本中抽取快照字段。

只做「候选抽取」，不自动保存：OCR 可能把标签、值、相邻字段混在一起，
前端 / 录入脚本必须让用户核对后才能写入快照。

有坐标信息时（OCR blocks），按「标签 -> 右侧值」的表格位置配对，能处理
企查查这类多列表格；没有坐标时退回按行文本匹配。
"""

from __future__ import annotations

import re
from datetime import date

from .company_names import extract_company_names
from .snapshot_store import parse_date

_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "company": ("企业名称", "公司名称", "企业全称"),
    "credit_code": ("统一社会信用代码", "社会信用代码", "信用代码"),
    "legal_representative": ("法定代表人", "法人代表"),
    "founded_at": ("成立日期", "成立时间"),
    "registration_status": ("登记状态", "经营状态", "企业状态"),
    "registered_capital": ("注册资本",),
    "paid_in_capital": ("实缴资本",),
    "organization_code": ("组织机构代码",),
    "business_registration_no": ("工商注册号", "注册号"),
    "taxpayer_id": ("纳税人识别号", "纳税人识别码"),
    "company_type": ("企业类型", "公司类型"),
    "business_term": ("营业期限", "经营期限"),
    "taxpayer_qualification": ("纳税人资质",),
    "insured_count": ("参保人数", "社保人数", "参保职工人数"),
    "employee_count": ("员工人数", "人员规模", "员工总数"),
    "approval_date": ("核准日期",),
    "region": ("所属地区", "所属区域"),
    "registration_authority": ("登记机关",),
    "industry": ("国标行业", "所属行业"),
    "english_name": ("英文名", "英文名称"),
    "registered_address": ("注册地址", "住所", "企业地址"),
    "mailing_address": ("通信地址", "通讯地址"),
    "business_scope": ("经营范围", "业务范围"),
    "official_domain": ("官网", "网址", "网站"),
}
_ALL_LABELS = tuple(
    sorted({label for labels in _FIELD_LABELS.values() for label in labels}, key=len, reverse=True)
)
_STATUS_PATTERN = re.compile(r"存续|在业|开业|在营|注销|吊销|迁出|停业|清算|撤销")
_CREDIT_CODE_PATTERN = re.compile(r"[0-9A-Z]{18}")
_DOMAIN_PATTERN = re.compile(r"(?:https?://)?([A-Za-z0-9][A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_NOISE_TAIL = re.compile(r"[①-⑳√✓]+$")
_REPORT_YEAR = re.compile(r"[（(]\d{4}年报[）)]")
_REQUIRED_LABELS = {
    "company": "公司全称",
    "founded_at": "成立日期",
    "registered_address": "注册地址",
    "insured_count": "参保人数",
    "business_scope": "经营范围",
    "registration_status": "登记状态",
}
_TEXT_FALLBACK_FIELDS = (
    "company",
    "credit_code",
    "founded_at",
    "registration_status",
    "registered_address",
    "insured_count",
    "business_scope",
)


# ---------------------------------------------------------------- 通用清洗


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _clean_value(value: str) -> str:
    value = value.strip().strip("：:，,。；;| ")
    return value


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None
    value = _NOISE_TAIL.sub("", value.strip())
    return value.strip() or None


def _clean_status(value: str | None) -> str | None:
    match = _STATUS_PATTERN.search(value or "")
    return match.group(0) if match else _clean_text(value)


def _clean_representative(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"(?:登)?关联企业.*$", "", value)
    return re.sub(r"\s+", "", value) or None


def _clean_english_name(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"[（(]自动翻译[）)]", "", value)
    return _clean_text(value)


def _clean_mailing_address(value: str | None) -> str | None:
    if not value:
        return None
    return _clean_text(_REPORT_YEAR.sub("", value))


def _clean_scope(value: str | None) -> str | None:
    value = _clean_text(value)
    if not value:
        return None
    # OCR 在多行单元格折行处可能插入空格，中文之间直接拼回去
    value = re.sub(r"(?<=[一-鿿])\s+(?=[一-鿿])", "", value)
    return value[:1000]


def _clean_company(value: str | None, text: str) -> str | None:
    value = _clean_text(value)
    if value and any(suffix in value for suffix in ("公司", "集团", "工作室", "事务所", "研究院")):
        value = re.split(r"附近企业|同地址企业", value)[0].strip()
        return value or None
    names = extract_company_names(text)
    return names[0] if names else value


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


# ---------------------------------------------------------------- 文本兜底


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


def _extract_from_text(lines: list[str], text: str) -> dict:
    credit = _CREDIT_CODE_PATTERN.search(text)
    return {
        "company": _clean_company(
            _extract_field(lines, _FIELD_LABELS["company"], max_follow=1), text
        ),
        "credit_code": credit.group(0) if credit else None,
        "legal_representative": _clean_representative(
            _extract_field(lines, _FIELD_LABELS["legal_representative"], max_follow=1)
        ),
        "founded_at": _parse_iso_date(
            _extract_field(lines, _FIELD_LABELS["founded_at"], max_follow=1), text
        ),
        "registration_status": _clean_status(
            _extract_field(lines, _FIELD_LABELS["registration_status"], max_follow=1)
        ),
        "registered_capital": _clean_text(
            _extract_field(lines, _FIELD_LABELS["registered_capital"], max_follow=1)
        ),
        "paid_in_capital": _clean_text(
            _extract_field(lines, _FIELD_LABELS["paid_in_capital"], max_follow=1)
        ),
        "organization_code": _clean_text(
            _extract_field(lines, _FIELD_LABELS["organization_code"], max_follow=1)
        ),
        "business_registration_no": _clean_text(
            _extract_field(lines, _FIELD_LABELS["business_registration_no"], max_follow=1)
        ),
        "taxpayer_id": _clean_text(
            _extract_field(lines, _FIELD_LABELS["taxpayer_id"], max_follow=1)
        ),
        "company_type": _clean_text(
            _extract_field(lines, _FIELD_LABELS["company_type"], max_follow=1)
        ),
        "business_term": _clean_text(
            _extract_field(lines, _FIELD_LABELS["business_term"], max_follow=1)
        ),
        "taxpayer_qualification": _clean_text(
            _extract_field(lines, _FIELD_LABELS["taxpayer_qualification"], max_follow=1)
        ),
        "insured_count": _parse_int(
            _extract_field(lines, _FIELD_LABELS["insured_count"], max_follow=1)
        ),
        "employee_count": _parse_int(
            _extract_field(lines, _FIELD_LABELS["employee_count"], max_follow=1)
        ),
        "approval_date": _parse_iso_date(
            _extract_field(lines, _FIELD_LABELS["approval_date"], max_follow=1), text
        ),
        "region": _clean_text(
            _extract_field(lines, _FIELD_LABELS["region"], max_follow=1)
        ),
        "registration_authority": _clean_text(
            _extract_field(lines, _FIELD_LABELS["registration_authority"], max_follow=1)
        ),
        "industry": _clean_text(
            _extract_field(lines, _FIELD_LABELS["industry"], max_follow=1)
        ),
        "english_name": _clean_english_name(
            _extract_field(lines, _FIELD_LABELS["english_name"], max_follow=1)
        ),
        "registered_address": _clean_text(
            _extract_field(lines, _FIELD_LABELS["registered_address"], max_follow=2)
        ),
        "mailing_address": _clean_mailing_address(
            _extract_field(lines, _FIELD_LABELS["mailing_address"], max_follow=2)
        ),
        "business_scope": _extract_business_scope(lines),
        "official_domain": _parse_domain(lines),
    }


def _extract_business_scope(lines: list[str]) -> str | None:
    value = _extract_field(lines, _FIELD_LABELS["business_scope"], max_follow=8)
    return _clean_scope(value)


def _parse_domain(lines: list[str]) -> str | None:
    value = _extract_field(lines, _FIELD_LABELS["official_domain"], max_follow=1)
    match = _DOMAIN_PATTERN.search(value or "")
    return match.group(1) if match else None


# ---------------------------------------------------------------- 坐标配对


def _overlap(a: dict, b: dict) -> float:
    ay0, ay1 = a["bbox"][1], a["bbox"][3]
    by0, by1 = b["bbox"][1], b["bbox"][3]
    return max(0.0, min(ay1, by1) - max(ay0, by0))


def _center_y(block: dict) -> float:
    return (block["bbox"][1] + block["bbox"][3]) / 2


def _find_labels(blocks: list[dict]) -> tuple[dict[str, dict], set[int]]:
    label_blocks: dict[str, dict] = {}
    label_ids: set[int] = set()
    for key, labels in _FIELD_LABELS.items():
        best: tuple[int, dict] | None = None
        for block in blocks:
            text = _normalize_line(block["text"])
            for label in labels:
                if text == label or (text.startswith(label) and len(text) <= len(label) + 2):
                    if best is None or len(text) < best[0]:
                        best = (len(text), block)
                    break
        if best:
            label_blocks[key] = best[1]
            label_ids.add(id(best[1]))
    return label_blocks, label_ids


def _blocks_for_label(
    field: str, label: dict, blocks: list[dict], label_ids: set[int]
) -> list[dict]:
    _, ly0, lx1, ly1 = label["bbox"]
    center = _center_y(label)
    right = [
        block
        for block in blocks
        if id(block) not in label_ids and block["bbox"][0] >= lx1 + 8
    ]
    if not right:
        return []

    if field == "business_scope":
        # 经营范围的值是多行大单元格，标签垂直居中，首行可能在标签上方
        near = [block for block in right if abs(_center_y(block) - center) <= 70]
        if not near:
            return []
        column = min(block["bbox"][0] for block in near)
        chosen = [block for block in near if abs(block["bbox"][0] - column) <= 45]
    else:
        strict = [block for block in right if _overlap(block, label) > 0]
        pool = strict or [block for block in right if abs(_center_y(block) - center) <= 55]
        if not pool:
            return []
        nearest = min(pool, key=lambda block: (block["bbox"][0], abs(_center_y(block) - center)))
        column = nearest["bbox"][0]
        chosen = [
            block
            for block in right
            if abs(block["bbox"][0] - column) <= 45
            and ly0 - 16 <= _center_y(block) <= ly1 + 16
        ]

    # 同一行的块 y0 可能差一两像素，先按行聚合再按从左到右
    chosen.sort(key=lambda block: (round(_center_y(block) / 10), block["bbox"][0]))
    return chosen


def _join_value(field: str, blocks: list[dict]) -> str | None:
    texts = [block["text"].strip() for block in blocks if block["text"].strip()]
    if not texts:
        return None
    # 经营范围跨行处会从词中间断开，直接拼接；其余字段按空格拼
    return "".join(texts) if field == "business_scope" else " ".join(texts)


def _extract_from_blocks(blocks: list[dict], text: str) -> tuple[dict, bool]:
    usable = [
        block
        for block in blocks
        if block.get("text")
        and isinstance(block.get("bbox"), list)
        and len(block["bbox"]) == 4
    ]
    label_blocks, label_ids = _find_labels(usable)
    raw: dict[str, str | None] = {}
    for field, label in label_blocks.items():
        raw[field] = _join_value(field, _blocks_for_label(field, label, usable, label_ids))

    credit = _CREDIT_CODE_PATTERN.search(raw.get("credit_code") or "")
    if not credit:
        credit = _CREDIT_CODE_PATTERN.search(text)
    taxpayer = _CREDIT_CODE_PATTERN.search(raw.get("taxpayer_id") or "")

    approval_raw = _clean_text(raw.get("approval_date"))
    approval_hidden = bool(approval_raw and "VIP" in approval_raw.upper())

    fields = {
        "company": _clean_company(raw.get("company"), text),
        "credit_code": credit.group(0) if credit else None,
        "legal_representative": _clean_representative(raw.get("legal_representative")),
        "founded_at": _parse_iso_date(raw.get("founded_at"), text),
        "registration_status": _clean_status(raw.get("registration_status")),
        "registered_capital": _clean_text(raw.get("registered_capital")),
        "paid_in_capital": _clean_text(raw.get("paid_in_capital")),
        "organization_code": _clean_text(raw.get("organization_code")),
        "business_registration_no": _clean_text(raw.get("business_registration_no")),
        "taxpayer_id": (
            taxpayer.group(0)
            if taxpayer
            else (_clean_text(raw.get("taxpayer_id")) or (credit.group(0) if credit else None))
        ),
        "company_type": _clean_text(raw.get("company_type")),
        "business_term": _clean_text(raw.get("business_term")),
        "taxpayer_qualification": _clean_text(raw.get("taxpayer_qualification")),
        "insured_count": _parse_int(raw.get("insured_count")),
        "employee_count": _parse_int(raw.get("employee_count")),
        "approval_date": None if approval_hidden else _parse_iso_date(raw.get("approval_date"), text),
        "region": _clean_text(raw.get("region")),
        "registration_authority": _clean_text(raw.get("registration_authority")),
        "industry": _clean_text(raw.get("industry")),
        "english_name": _clean_english_name(raw.get("english_name")),
        "registered_address": _clean_text(raw.get("registered_address")),
        "mailing_address": _clean_mailing_address(raw.get("mailing_address")),
        "business_scope": _clean_scope(raw.get("business_scope")),
        "official_domain": None,
    }
    return fields, approval_hidden


# ---------------------------------------------------------------- 入口


def extract_snapshot_fields(text: str, blocks: list[dict] | None = None) -> dict:
    lines = [_normalize_line(line) for line in (text or "").splitlines() if line.strip()]
    text_fields = _extract_from_text(lines, text)

    approval_hidden = False
    if blocks:
        fields, approval_hidden = _extract_from_blocks(blocks, text)
        # 坐标没配对到的关键字段，再用文本规则兜底
        for key in _TEXT_FALLBACK_FIELDS:
            if not fields.get(key) and text_fields.get(key):
                fields[key] = text_fields[key]
        note = "已按截图表格位置配对字段，仍请逐项核对。"
    else:
        fields = text_fields
        note = ""

    missing = [
        label
        for key, label in _REQUIRED_LABELS.items()
        if fields.get(key) in (None, "")
    ]
    warnings = [
        "来源 URL 与查询日期无法从截图可靠识别，请在保存前手工确认。",
        "OCR 与字段抽取都可能出错，请逐项核对后再保存。",
    ]
    if note:
        warnings.append(note)
    if "参保人数" in missing:
        warnings.append("参保人数常见于企业年报或社保信息，截图中可能没有。")
    if fields.get("business_scope"):
        warnings.append("经营范围可能跨行，已尽量合并，请核对是否完整。")
    if approval_hidden:
        warnings.append("核准日期在截图中被 VIP 遮挡，未提取到，请手工填写或跳过。")
    if not fields.get("company"):
        warnings.append("未识别到公司全称，请手工补充。")

    return {
        "text": text,
        "fields": fields,
        "missing_fields": missing,
        "warnings": warnings,
        "suggested_fetched_at": date.today().isoformat(),
    }
