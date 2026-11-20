"""人工核验快照的共享存储层。

被 GongshangProvider、/company-snapshots 接口、scripts/* 共用，保证三处
使用同一套字段校验与原子写入逻辑。
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime
from pathlib import Path

from ..config import settings
from .company_names import same_subject

REQUIRED_FIELDS = (
    "founded_at",
    "registered_address",
    "insured_count",
    "business_scope",
    "registration_status",
    "source_url",
    "fetched_at",
)
DATE_FIELDS = ("founded_at", "approval_date", "fetched_at")
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


def _path(path: Path | None = None) -> Path:
    return path or settings.snapshot_path


def load_snapshot_file(path: Path | None = None) -> dict:
    target = _path(path)
    if not target.exists():
        return {"_meta": {}, "companies": {}}
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("快照根节点必须是 JSON 对象")
    companies = data.setdefault("companies", {})
    if not isinstance(companies, dict):
        raise ValueError("companies 必须是对象")
    return data


def save_snapshot_file(data: dict, path: Path | None = None) -> None:
    target = _path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # Windows 下杀毒 / 索引服务可能短暂占用目标文件，重试几次
    for attempt in range(3):
        try:
            os.replace(tmp, target)
            return
        except PermissionError:
            if attempt == 2:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.1)


def validate_record(record: dict) -> list[str]:
    errors: list[str] = []
    missing = [
        field for field in REQUIRED_FIELDS if record.get(field) in (None, "")
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

    if not str(record.get("registration_status") or "").strip():
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


def find_snapshot(
    company: str, path: Path | None = None
) -> tuple[str | None, dict | None]:
    companies = load_snapshot_file(path).get("companies") or {}
    if company in companies:
        return company, companies[company]
    for name, facts in companies.items():
        if same_subject(company, name):
            return name, facts
    return None, None


def upsert_record(
    company: str,
    record: dict,
    path: Path | None = None,
    force: bool = False,
) -> tuple[str, list[str]]:
    """返回 (action, similar_names)。action: 新增 / 更新 / conflict。"""
    data = load_snapshot_file(path)
    companies = data.setdefault("companies", {})

    if company in companies:
        action = "更新"
        similar: list[str] = []
    else:
        similar = [name for name in companies if same_subject(company, name)]
        if similar and not force:
            return "conflict", similar
        action = "新增"

    companies[company] = record
    save_snapshot_file(data, path)
    return action, similar


def remove_record(
    company: str, path: Path | None = None
) -> tuple[bool, list[str]]:
    data = load_snapshot_file(path)
    companies = data.setdefault("companies", {})
    if company not in companies:
        return False, [name for name in companies if same_subject(company, name)]
    del companies[company]
    save_snapshot_file(data, path)
    return True, []
