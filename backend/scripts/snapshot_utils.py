"""人工核验快照的读写与校验工具（被 add_snapshot / validate_snapshots 共用）。"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT = BASE_DIR / "data" / "company_snapshots.json"

REQUIRED_FIELDS = (
    "founded_at",
    "registered_address",
    "insured_count",
    "business_scope",
    "registration_status",
    "source_url",
    "fetched_at",
)
DATE_FIELDS = ("founded_at", "fetched_at")
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y年%m月")


def parse_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def load_snapshot_file(path: Path = SNAPSHOT) -> dict:
    if not path.exists():
        return {"_meta": {}, "companies": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("快照根节点必须是 JSON 对象")
    companies = data.setdefault("companies", {})
    if not isinstance(companies, dict):
        raise ValueError("companies 必须是对象")
    return data


def save_snapshot_file(data: dict, path: Path = SNAPSHOT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)


def validate_record(record: dict) -> list[str]:
    errors: list[str] = []
    missing = [
        field
        for field in REQUIRED_FIELDS
        if record.get(field) in (None, "")
    ]
    if missing:
        errors.append(f"缺少必填字段：{'、'.join(missing)}")

    for field in DATE_FIELDS:
        if record.get(field) and parse_date(record[field]) is None:
            errors.append(f"{field} 不是可识别日期：{record[field]}")

    insured = record.get("insured_count")
    if insured is not None and (
        isinstance(insured, bool) or not isinstance(insured, int) or insured < 0
    ):
        errors.append(f"insured_count 必须是非负整数：{insured!r}")

    employee = record.get("employee_count")
    if employee is not None and (
        isinstance(employee, bool) or not isinstance(employee, int) or employee < 0
    ):
        errors.append(f"employee_count 必须是非负整数：{employee!r}")

    source_url = str(record.get("source_url") or "")
    if source_url and not source_url.startswith(("http://", "https://")):
        errors.append("source_url 必须以 http(s):// 开头")

    status = str(record.get("registration_status") or "")
    if not status:
        errors.append("registration_status 不能为空")

    return errors


def unlocked_rules(record: dict) -> list[str]:
    unlocked = []
    if record.get("insured_count") is not None or record.get("employee_count") is not None:
        unlocked.append("规模")
    if record.get("registered_address"):
        unlocked.append("地址")
    if record.get("founded_at"):
        unlocked.append("时间")
    if record.get("business_scope"):
        unlocked.append("行业")
    if record.get("official_domain"):
        unlocked.append("联系")
    return unlocked
